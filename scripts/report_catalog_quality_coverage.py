from __future__ import annotations

import argparse
import json
from pathlib import Path

CATALOG_PATH = Path("data/tools.json")
QUALITY_PATH = Path("data/catalog-quality.json")


def normalize_url(url: str) -> str:
    return url.rstrip("/").casefold()


def build_report() -> dict:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    quality = json.loads(QUALITY_PATH.read_text(encoding="utf-8"))

    accepted = {
        item["name"]: item
        for item in quality.get("tools", [])
        if item.get("decision") == "accepted"
    }

    reviewed = []
    pending = []
    mismatched = []

    for row in catalog:
        name = row[0]
        url = row[5]
        review = accepted.get(name)
        if review is None:
            pending.append({"name": name, "url": url, "category": row[1]})
            continue

        review_url = review.get("officialUrl", "")
        if normalize_url(review_url) != normalize_url(url):
            mismatched.append(
                {
                    "name": name,
                    "catalogUrl": url,
                    "reviewUrl": review_url,
                }
            )
            continue

        reviewed.append(name)

    pending.sort(key=lambda item: item["name"].casefold())
    mismatched.sort(key=lambda item: item["name"].casefold())

    return {
        "schemaVersion": 1,
        "catalogCount": len(catalog),
        "reviewedActiveCount": len(reviewed),
        "pendingActiveCount": len(pending),
        "urlMismatchCount": len(mismatched),
        "coveragePercent": round((len(reviewed) / len(catalog) * 100), 2) if catalog else 100.0,
        "pending": pending,
        "urlMismatches": mismatched,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Report strict quality-review coverage for the active catalog.")
    parser.add_argument("--output", default="catalog-quality-coverage.json")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero while active catalog entries remain pending or have review URL mismatches.",
    )
    args = parser.parse_args()

    report = build_report()
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("catalogCount", "reviewedActiveCount", "pendingActiveCount", "urlMismatchCount", "coveragePercent")}, sort_keys=True))

    if args.strict and (report["pendingActiveCount"] or report["urlMismatchCount"]):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
