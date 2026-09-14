import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_quality_manifest_uses_official_evidence_and_catalog_identity():
    tools = load_json("data/tools.json")
    quality = load_json("data/catalog-quality.json")
    by_name = {row[0]: row for row in tools}

    assert quality["schemaVersion"] == 1
    assert quality["policy"] == "docs/CATALOG_QUALITY_POLICY.md"
    reviews = quality["tools"]
    assert len(reviews) >= 25

    seen = set()
    for review in reviews:
        name = review["name"]
        assert name not in seen
        seen.add(name)
        assert name in by_name
        assert review["decision"] == "accepted"
        assert review["officialUrl"] == by_name[name][5]
        assert review["userValue"].strip()
        assert review["evidenceUrls"]
        assert all(url.startswith(("https://", "http://")) for url in review["evidenceUrls"])
        date.fromisoformat(review["reviewedAt"])


def test_quality_ui_has_reviewed_filter_and_transparent_pending_state():
    tools_html = (ROOT / "tools.html").read_text(encoding="utf-8")
    quality_html = (ROOT / "quality.html").read_text(encoding="utf-8")

    assert 'data-view="reviewed"' in tools_html
    assert "catalog-quality.json" in tools_html
    assert "Official-source reviewed" in tools_html
    assert "no vote or popularity ranking" in tools_html

    assert "Official-source reviewed" in quality_html or "OFFICIAL-SOURCE REVIEW" in quality_html
    assert "Pending audit" in quality_html
    assert "not a popularity ranking or paid placement" in quality_html
    assert "catalog-quality.json" in quality_html


def test_submission_requires_user_value_and_first_party_evidence():
    submit = (ROOT / "submit.html").read_text(encoding="utf-8")
    assert 'id="userValue" required' in submit
    assert 'id="evidence" required' in submit
    assert "first-party" in submit
    assert "Third-party directories" in submit
