from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path("data")
PATHS = {
    "catalog": ROOT / "tools.json",
    "lifecycle": ROOT / "tool-lifecycle.json",
    "verified": ROOT / "verified-facts.json",
    "recommender": ROOT / "recommender.json",
    "fit": ROOT / "recommender-fit.json",
    "quality": ROOT / "catalog-quality.json",
    "batch": ROOT / "catalog-quality-review-batch.json",
}


def load(key: str):
    return json.loads(PATHS[key].read_text(encoding="utf-8"))


def dump(key: str, value) -> None:
    PATHS[key].write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def norm_url(value: str) -> str:
    return value.rstrip("/").casefold()


def valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def upsert_quality(records: list[dict], record: dict) -> None:
    for index, existing in enumerate(records):
        if existing.get("name") == record["name"]:
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
    batch = load("batch")

    reviewed_at = batch["reviewedAt"]
    batch_id = batch["batchId"]
    records = quality.setdefault("tools", [])

    def locate(name: str) -> int | None:
        for index, row in enumerate(catalog):
            if row[0] == name:
                return index
        return None

    def quality_record(name: str) -> dict | None:
        for record in records:
            if record.get("name") == name:
                return record
        return None

    accepted = updated = removed = already_removed = 0

    for item in batch.get("accept", []):
        name = item["name"]
        index = locate(name)
        if index is None:
            raise SystemExit(f"quality batch accepts unknown active tool: {name}")
        official_url = item["officialUrl"]
        if not valid_url(official_url):
            raise SystemExit(f"invalid official URL for {name}: {official_url}")
        if norm_url(catalog[index][5]) != norm_url(official_url):
            raise SystemExit(
                f"quality review URL mismatch for {name}: catalog={catalog[index][5]} review={official_url}"
            )
        if not item.get("evidenceUrls") or not item.get("userValue"):
            raise SystemExit(f"quality review lacks evidence/user value: {name}")
        upsert_quality(
            records,
            {
                "name": name,
                "officialUrl": official_url,
                "evidenceUrls": item["evidenceUrls"],
                "reviewedAt": reviewed_at,
                "userValue": item["userValue"],
                "decision": "accepted",
            },
        )
        accepted += 1

    for item in batch.get("update", []):
        name = item["name"]
        index = locate(name)
        if index is None:
            raise SystemExit(f"quality batch updates unknown active tool: {name}")
        new_url = item["url"]
        if not valid_url(new_url):
            raise SystemExit(f"invalid updated URL for {name}: {new_url}")
        catalog[index][5] = new_url
        upsert_quality(
            records,
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

    for item in batch.get("remove", []):
        name = item["name"]
        index = locate(name)
        if index is None:
            existing = quality_record(name)
            if existing and existing.get("decision") == "rejected":
                already_removed += 1
                continue
            raise SystemExit(f"quality batch removal missing from catalog without rejected review: {name}")
        row = catalog.pop(index)
        lifecycle.get("tools", {}).pop(name, None)
        verified.get("tools", {}).pop(name, None)
        recommender.get("profiles", {}).pop(name, None)
        fit.pop(name, None)
        upsert_quality(
            records,
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

    names = [row[0] for row in catalog]
    urls = [norm_url(row[5]) for row in catalog]
    if len(names) != len(set(names)):
        raise SystemExit("quality batch produced duplicate tool names")
    if len(urls) != len(set(urls)):
        raise SystemExit("quality batch produced duplicate official URLs")

    records.sort(key=lambda item: (item.get("decision") != "accepted", item.get("name", "").casefold()))
    quality["lastQualityReviewBatchAt"] = reviewed_at
    quality["lastQualityReviewBatch"] = batch_id
    quality["lastQualityReviewBatchSummary"] = {
        "accepted": len(batch.get("accept", [])),
        "updated": len(batch.get("update", [])),
        "removed": len(batch.get("remove", [])),
    }

    for key, value in (
        ("catalog", catalog),
        ("lifecycle", lifecycle),
        ("verified", verified),
        ("recommender", recommender),
        ("fit", fit),
        ("quality", quality),
    ):
        dump(key, value)

    print(
        f"Applied {batch_id}: accepted={accepted} updated={updated} "
        f"removed={removed} already_removed={already_removed}; active={len(catalog)}"
    )


if __name__ == "__main__":
    main()
