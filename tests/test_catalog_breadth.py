import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_catalog_has_at_least_120_tools_and_valid_rows():
    tools = load_json("data/tools.json")
    assert len(tools) >= 120
    assert all(isinstance(row, list) and len(row) == 6 for row in tools)
    assert all(all(isinstance(value, str) and value.strip() for value in row) for row in tools)
    assert all(row[5].startswith(("http://", "https://")) for row in tools)


def test_catalog_has_no_duplicate_names_or_official_urls():
    tools = load_json("data/tools.json")
    names = [row[0].casefold() for row in tools]
    urls = [row[5].rstrip("/").casefold() for row in tools]
    assert len(names) == len(set(names))
    assert len(urls) == len(set(urls))


def test_lifecycle_covers_every_catalog_tool():
    tools = load_json("data/tools.json")
    lifecycle = load_json("data/tool-lifecycle.json")["tools"]
    names = {row[0] for row in tools}
    assert names == set(lifecycle)
    assert all(item["event"] in {"baseline_import", "added"} for item in lifecycle.values())
    assert all(item["firstTrackedAt"].endswith("Z") for item in lifecycle.values())


def test_new_local_first_tools_are_represented_in_recommender():
    profiles = load_json("data/recommender.json")["profiles"]
    for name in ("GPT4All", "llama.cpp", "LibreChat"):
        assert name in profiles
        assert "local" in profiles[name]["tasks"]
        assert "privacy" in profiles[name]["traits"]
