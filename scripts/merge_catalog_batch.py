#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS_PATH = ROOT / "data" / "tools.json"
LIFECYCLE_PATH = ROOT / "data" / "tool-lifecycle.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_tools(rows):
    body = ",\n".join("  " + json.dumps(row, ensure_ascii=False) for row in rows)
    TOOLS_PATH.write_text("[\n" + body + "\n]\n", encoding="utf-8")


def write_lifecycle(payload):
    lines = ["{"]
    keys = ["schemaVersion", "trackingStartedAt", "sourceCommit", "note"]
    for key in keys:
        lines.append(f'  {json.dumps(key)}: {json.dumps(payload[key], ensure_ascii=False)},')
    lines.append('  "tools": {')
    items = list(payload["tools"].items())
    for index, (name, record) in enumerate(items):
        comma = "," if index < len(items) - 1 else ""
        lines.append(
            "    "
            + json.dumps(name, ensure_ascii=False)
            + ": "
            + json.dumps(record, ensure_ascii=False, separators=(",", ": "))
            + comma
        )
    lines.extend(["  }", "}"])
    LIFECYCLE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_row(row):
    if not isinstance(row, list) or len(row) != 6:
        raise ValueError(f"Every catalog row must contain exactly 6 strings: {row!r}")
    if not all(isinstance(value, str) and value.strip() for value in row):
        raise ValueError(f"Catalog rows may not contain blank/non-string values: {row!r}")
    if not row[5].startswith(("https://", "http://")):
        raise ValueError(f"Official URL must be http(s): {row[0]} -> {row[5]}")


def merge(batch_path: Path):
    tools = load_json(TOOLS_PATH)
    lifecycle = load_json(LIFECYCLE_PATH)
    batch = load_json(batch_path)

    existing_names = {row[0].casefold(): row for row in tools}
    existing_urls = {row[5].rstrip("/").casefold(): row[0] for row in tools}
    batch_names = set()
    batch_urls = set()
    added = []
    skipped_aliases = []

    for row in batch:
        validate_row(row)
        name_key = row[0].casefold()
        url_key = row[5].rstrip("/").casefold()
        if name_key in batch_names:
            raise ValueError(f"Duplicate name inside batch: {row[0]}")
        if url_key in batch_urls:
            raise ValueError(f"Duplicate official URL inside batch: {row[5]}")
        batch_names.add(name_key)
        batch_urls.add(url_key)

        if name_key in existing_names:
            if existing_names[name_key] != row:
                raise ValueError(f"Batch conflicts with maintained row for {row[0]}")
            continue
        if url_key in existing_urls:
            skipped_aliases.append((row[0], existing_urls[url_key]))
            continue

        tools.append(row)
        existing_names[name_key] = row
        existing_urls[url_key] = row[0]
        added.append(row[0])

    for alias, canonical in skipped_aliases:
        print(f"Skipped alias {alias!r}; official URL is already maintained as {canonical!r}.")

    if not added:
        print("Catalog batch already applied; no changes needed.")
        return 0

    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    lifecycle_tools = lifecycle["tools"]
    for name in added:
        if name in lifecycle_tools:
            raise ValueError(f"Lifecycle record already exists for newly added tool: {name}")
        lifecycle_tools[name] = {"firstTrackedAt": timestamp, "event": "added"}

    write_tools(tools)
    write_lifecycle(lifecycle)
    print(f"Added {len(added)} tools at {timestamp}. Catalog now contains {len(tools)} tools.")
    return len(added)


def main():
    parser = argparse.ArgumentParser(description="Merge a reviewed catalog batch into maintained data.")
    parser.add_argument("batch", help="Path to a JSON file containing six-field tool rows")
    args = parser.parse_args()
    batch_path = (ROOT / args.batch).resolve()
    if ROOT not in batch_path.parents:
        raise SystemExit("Batch path must live inside the repository")
    merge(batch_path)


if __name__ == "__main__":
    main()
