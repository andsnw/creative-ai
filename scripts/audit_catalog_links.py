from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from html import unescape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

CATALOG_PATH = Path("data/tools.json")
USER_AGENT = "CreativeAI-CatalogAudit/1.0 (+https://github.com/nael5x/creative-ai)"
SUSPICIOUS_PATTERNS = {
    "parked-domain": re.compile(r"\b(domain (?:is )?for sale|buy this domain|premium domain|this domain may be for sale)\b", re.I),
    # Require lifecycle language rather than a bare word such as "shutdown". Active products often
    # mention other services shutting down in comparison/FAQ copy, which must not condemn the product.
    "shutdown": re.compile(
        r"\b(?:we (?:are|'re) shutting down|will be shutting down|has shut down|have shut down|"
        r"this (?:service|product|app) (?:is|has been) (?:discontinued|sunset)|"
        r"service has ended|product has ended|no longer available to (?:new )?users|farewell)\b",
        re.I,
    ),
}


@dataclass
class Result:
    name: str
    url: str
    status: int | None
    final_url: str | None
    ok: bool
    redirect_host_changed: bool
    flags: list[str]
    error: str | None


def host(url: str | None) -> str:
    if not url:
        return ""
    value = (urlparse(url).hostname or "").lower()
    return value[4:] if value.startswith("www.") else value


def registrable_hint(value: str) -> str:
    parts = host(value).split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host(value)


def fetch_one(row: list[str], timeout: float) -> Result:
    name, *_rest, url = row
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5"})
    context = ssl.create_default_context()
    status: int | None = None
    final_url: str | None = None
    body = b""
    error: str | None = None
    try:
        with urlopen(req, timeout=timeout, context=context) as response:
            status = getattr(response, "status", None) or response.getcode()
            final_url = response.geturl()
            body = response.read(180_000)
    except HTTPError as exc:
        status = exc.code
        final_url = exc.geturl()
        try:
            body = exc.read(120_000)
        except Exception:
            body = b""
        # 3xx and common anti-bot/auth responses prove that a server is reachable; they are review
        # signals, not automatic evidence that the product is dead.
        if not (300 <= exc.code < 400) and exc.code not in {401, 403, 405, 429}:
            error = f"HTTP {exc.code}"
    except (URLError, TimeoutError, ssl.SSLError, OSError) as exc:
        error = f"{type(exc).__name__}: {exc}"
    except Exception as exc:  # defensive: this is a reporting utility
        error = f"{type(exc).__name__}: {exc}"

    text = unescape(body.decode("utf-8", errors="ignore"))
    compact = re.sub(r"\s+", " ", text)[:120_000]
    flags = [label for label, pattern in SUSPICIOUS_PATTERNS.items() if pattern.search(compact)]
    changed = bool(final_url and registrable_hint(url) != registrable_hint(final_url))
    if changed:
        flags.append("cross-domain-redirect")
    ok = error is None and (status is None or status < 500)
    return Result(name, url, status, final_url, ok, changed, sorted(set(flags)), error)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Creative AI catalog URLs and flag suspicious destinations.")
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--output", default="catalog-link-audit.json")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on broken or suspicious findings.")
    args = parser.parse_args()

    rows = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    results: list[Result] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(fetch_one, row, args.timeout): row[0] for row in rows}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            marker = "OK" if result.ok and not result.flags else "CHECK"
            print(f"[{marker}] {result.name}: {result.status or '-'} {result.final_url or result.url} {' '.join(result.flags)}")

    results.sort(key=lambda item: item.name.casefold())
    payload = {
        "schemaVersion": 1,
        "catalogCount": len(rows),
        "summary": {
            "healthy": sum(1 for x in results if x.ok and not x.flags),
            "needsReview": sum(1 for x in results if x.flags),
            "broken": sum(1 for x in results if not x.ok),
        },
        "results": [asdict(x) for x in results],
    }
    Path(args.output).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], sort_keys=True))

    if args.strict and any((not x.ok) or x.flags for x in results):
        sys.exit(2)


if __name__ == "__main__":
    main()
