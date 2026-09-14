from __future__ import annotations

import json
from copy import deepcopy
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
    "fixes": ROOT / "catalog-audit-fixes.json",
}


def load(key: str):
    return json.loads(PATHS[key].read_text(encoding="utf-8"))


def dump(key: str, value) -> None:
    PATHS[key].write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def rename_key(mapping: dict, old: str, new: str) -> None:
    if old not in mapping or old == new:
        return
    value = mapping.pop(old)
    if new not in mapping:
        mapping[new] = value


def quality_upsert(records: list[dict], entry: dict) -> None:
    name = entry["name"]
    for index, existing in enumerate(records):
        if existing.get("name") == name:
            records[index] = entry
            return
    records.append(entry)


def is_unresolved(item: dict) -> bool:
    """Keep incomplete/manual-review mappings out of generated public catalog data."""
    return item.get("status") == "unresolved" or item.get("userValue") == "PLACEHOLDER"


def main() -> None:
    catalog = load("catalog")
    lifecycle = load("lifecycle")
    verified = load("verified")
    recommender = load("recommender")
    fit = load("fit")
    quality = load("quality")
    fixes = load("fixes")

    reviewed_at = fixes["reviewedAt"]
    quality_records = quality.setdefault("tools", [])
    removed_names: set[str] = set()
    renamed: dict[str, str] = {}
    corrected = 0
    unresolved: list[str] = []

    def locate(name: str) -> int:
        for idx, row in enumerate(catalog):
            if row[0] == name:
                return idx
        raise SystemExit(f"audit fix references unknown catalog tool: {name}")

    # Removal is deliberately destructive only to public discovery data; the rejection record preserves
    # why the tool disappeared and which evidence was checked.
    for item in fixes.get("remove", []):
        name = item["name"]
        idx = locate(name)
        row = catalog.pop(idx)
        removed_names.add(name)
        lifecycle.get("tools", {}).pop(name, None)
        verified.get("tools", {}).pop(name, None)
        recommender.get("profiles", {}).pop(name, None)
        fit.pop(name, None)
        quality_records[:] = [x for x in quality_records if x.get("name") != name or x.get("decision") == "rejected"]
        quality_upsert(
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

    for item in fixes.get("replace", []):
        old = item["oldName"]
        if is_unresolved(item):
            unresolved.append(old)
            print(f"UNRESOLVED audit mapping left unchanged: {old}")
            continue

        idx = locate(old)
        row = deepcopy(catalog[idx])
        new = item.get("newName", old)
        if item.get("url"):
            if not valid_url(item["url"]):
                raise SystemExit(f"invalid replacement URL for {old}: {item['url']}")
            row[5] = item["url"]
        if item.get("category"):
            row[1] = item["category"]
        if item.get("description"):
            row[2] = item["description"]
        if item.get("why"):
            row[3] = item["why"]
        if item.get("availability"):
            row[4] = item["availability"]
        row[0] = new

        existing_target = next((i for i, candidate in enumerate(catalog) if candidate[0] == new and candidate[0] != old), None)
        if existing_target is not None:
            # Prefer the already-maintained target and remove the superseded alias.
            catalog.pop(idx)
            lifecycle.get("tools", {}).pop(old, None)
            verified.get("tools", {}).pop(old, None)
            recommender.get("profiles", {}).pop(old, None)
            fit.pop(old, None)
        else:
            catalog[idx] = row
            rename_key(lifecycle.get("tools", {}), old, new)
            rename_key(verified.get("tools", {}), old, new)
            rename_key(recommender.get("profiles", {}), old, new)
            rename_key(fit, old, new)
            if old != new:
                renamed[old] = new

        # Replace stale review records under the old name, then mark the current identity as accepted.
        if old != new:
            quality_records[:] = [x for x in quality_records if x.get("name") != old]
        quality_upsert(
            quality_records,
            {
                "name": new,
                "officialUrl": row[5],
                "evidenceUrls": item["evidenceUrls"],
                "reviewedAt": reviewed_at,
                "userValue": item["userValue"],
                "decision": "accepted",
            },
        )
        corrected += 1

    # Keep ordering stable except for renamed identities staying where their predecessors were.
    names = [row[0] for row in catalog]
    if len(names) != len(set(names)):
        duplicates = sorted({x for x in names if names.count(x) > 1})
        raise SystemExit(f"audit fixes produced duplicate names: {duplicates}")

    quality_records.sort(key=lambda x: (x.get("decision") != "accepted", x.get("name", "").casefold()))
    quality["lastAuditFixesAt"] = reviewed_at
    quality["lastAuditFixesSummary"] = {
        "removed": len(removed_names),
        "renamed": len(renamed),
        "reviewedOrCorrected": corrected,
        "unresolved": len(unresolved),
    }
    if unresolved:
        quality["unresolvedAuditMappings"] = sorted(unresolved)
    else:
        quality.pop("unresolvedAuditMappings", None)

    dump("catalog", catalog)
    dump("lifecycle", lifecycle)
    dump("verified", verified)
    dump("recommender", recommender)
    dump("fit", fit)
    dump("quality", quality)

    print(
        f"Applied audit fixes: removed={len(removed_names)} renamed={len(renamed)} "
        f"corrected={corrected} unresolved={len(unresolved)}"
    )
    print(f"Catalog now contains {len(catalog)} entries")


if __name__ == "__main__":
    main()
