from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

# Second-pass changes are intentionally explicit and source-reviewed; this script never discovers
# or guesses replacements on its own.
ROOT = Path("data")
PATHS = {
    "catalog": ROOT / "tools.json",
    "lifecycle": ROOT / "tool-lifecycle.json",
    "verified": ROOT / "verified-facts.json",
    "recommender": ROOT / "recommender.json",
    "fit": ROOT / "recommender-fit.json",
    "quality": ROOT / "catalog-quality.json",
    "round2": ROOT / "catalog-audit-round2.json",
}


def load(key: str):
    return json.loads(PATHS[key].read_text(encoding="utf-8"))


def dump(key: str, value) -> None:
    PATHS[key].write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def upsert_quality(records: list[dict], record: dict) -> None:
    name = record["name"]
    for index, existing in enumerate(records):
        if existing.get("name") == name:
            records[index] = record
            return
    records.append(record)


def main() -> None:
    catalog = load("catalog")
    lifecycle = load("lifecycle")
    verified = load("verified")
    recommender = load("recommender")
    fit = load("fit")
    quality = load("quality")
    changes = load("round2")

    reviewed_at = changes["reviewedAt"]
    quality_records = quality.setdefault("tools", [])
    removed = 0
    already_removed = 0
    updated = 0

    def locate(name: str) -> int | None:
        for index, row in enumerate(catalog):
            if row[0] == name:
                return index
        return None

    def quality_record(name: str) -> dict | None:
        for record in quality_records:
            if record.get("name") == name:
                return record
        return None

    for item in changes.get("remove", []):
        name = item["name"]
        index = locate(name)
        if index is None:
            existing = quality_record(name)
            if not existing or existing.get("decision") != "rejected":
                raise SystemExit(
                    f"round-2 audit tool is absent from catalog without a rejected quality record: {name}"
                )
            # Idempotent reruns are expected after the workflow has already applied a reviewed removal.
            already_removed += 1
            continue

        row = catalog.pop(index)
        lifecycle.get("tools", {}).pop(name, None)
        verified.get("tools", {}).pop(name, None)
        recommender.get("profiles", {}).pop(name, None)
        fit.pop(name, None)
        upsert_quality(
            quality_records,
            {
                "name": name,
                "officialUrl": row[5],
                "evidenceUrls": item["evidenceUrls"],
                "reviewedAt": reviewed_at,
                "userValue": item["reason"],
                "decision": "rejected",
                "reason": item["reason"],
            },
        )
        removed += 1

    for item in changes.get("update", []):
        name = item["name"]
        new_url = item["url"]
        if not valid_url(new_url):
            raise SystemExit(f"invalid round-2 URL for {name}: {new_url}")
        index = locate(name)
        if index is None:
            raise SystemExit(f"round-2 update references unknown catalog tool: {name}")
        catalog[index][5] = new_url
        upsert_quality(
            quality_records,
            {
                "name": name,
                "officialUrl": new_url,
                "evidenceUrls": item["evidenceUrls"],
                "reviewedAt": reviewed_at,
                "userValue": item["userValue"],
                "decision": "accepted",
            },
        )
        updated += 1

    names = [row[0] for row in catalog]
    urls = [row[5].rstrip("/").casefold() for row in catalog]
    if len(names) != len(set(names)):
        duplicates = sorted({name for name in names if names.count(name) > 1})
        raise SystemExit(f"round-2 audit produced duplicate names: {duplicates}")
    if len(urls) != len(set(urls)):
        duplicates = sorted({url for url in urls if urls.count(url) > 1})
        raise SystemExit(f"round-2 audit produced duplicate URLs: {duplicates}")

    quality_records.sort(key=lambda item: (item.get("decision") != "accepted", item.get("name", "").casefold()))
    quality["lastAuditRound2At"] = reviewed_at
    quality["lastAuditRound2Summary"] = {
        "removed": len(changes.get("remove", [])),
        "updated": len(changes.get("update", [])),
    }

    dump("catalog", catalog)
    dump("lifecycle", lifecycle)
    dump("verified", verified)
    dump("recommender", recommender)
    dump("fit", fit)
    dump("quality", quality)

    print(
        "Applied second-pass catalog fixes: "
        f"removed_now={removed} already_removed={already_removed} updated={updated}"
    )
    print(f"Catalog now contains {len(catalog)} entries")


if __name__ == "__main__":
    main()
