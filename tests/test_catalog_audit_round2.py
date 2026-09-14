import json
from pathlib import Path
import unittest

SPEC = json.loads(Path("data/catalog-audit-round2.json").read_text(encoding="utf-8"))
SCRIPT = Path("scripts/apply_catalog_audit_round2.py").read_text(encoding="utf-8")


class CatalogAuditRound2Tests(unittest.TestCase):
    def test_shutdown_products_are_removed_not_silently_rebranded(self):
        removed = {item["name"] for item in SPEC["remove"]}
        self.assertTrue({"Dora AI", "Roo Code", "Hour One"}.issubset(removed))
        self.assertNotIn("Roomote", json.dumps(SPEC["update"]))

    def test_regard_uses_current_first_party_domain(self):
        updates = {item["name"]: item for item in SPEC["update"]}
        self.assertEqual(updates["Regard"]["url"], "https://regard.com/")
        self.assertNotIn("robinai.com", json.dumps(updates["Regard"]))

    def test_stale_urls_are_replaced_with_current_canonical_sources(self):
        updates = {item["name"]: item["url"] for item in SPEC["update"]}
        expected = {
            "Guru": "https://www.getguru.com/",
            "monday AI": "https://monday.com/",
            "SE Ranking Content Editor": "https://seranking.com/content-editor.html",
            "Tezi": "https://app.tezi.ai/",
            "OpenAI Codex": "https://openai.com/codex/",
        }
        for name, url in expected.items():
            self.assertEqual(updates[name], url)

    def test_round2_updates_all_integrity_metadata(self):
        for key in ("catalog", "lifecycle", "verified", "recommender", "fit", "quality"):
            self.assertIn(f'dump("{key}"', SCRIPT)
        self.assertIn("round-2 audit produced duplicate URLs", SCRIPT)

    def test_every_decision_has_evidence_and_no_placeholder(self):
        for section in ("remove", "update"):
            for item in SPEC[section]:
                self.assertTrue(item.get("evidenceUrls"))
                self.assertNotIn("PLACEHOLDER", json.dumps(item))


if __name__ == "__main__":
    unittest.main()
