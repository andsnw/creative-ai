import json
import unittest
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / "data" / "tools.json").read_text(encoding="utf-8"))
LIFECYCLE = json.loads((ROOT / "data" / "tool-lifecycle.json").read_text(encoding="utf-8"))
FACTS = json.loads((ROOT / "data" / "verified-facts.json").read_text(encoding="utf-8"))
RECOMMENDER = json.loads((ROOT / "data" / "recommender.json").read_text(encoding="utf-8"))
FIT = json.loads((ROOT / "data" / "recommender-fit.json").read_text(encoding="utf-8"))

ADDED = {
    "Microsoft Copilot", "DeepSeek", "Poe", "Ideogram", "Leonardo AI", "Krea",
    "HeyGen", "Synthesia", "Descript", "Murf", "Activepieces", "Pipedream",
    "Dify", "Jan", "AnythingLLM", "LocalAI", "Cline", "Continue", "CrewAI",
}


class CatalogExpansionTests(unittest.TestCase):
    def test_catalog_has_reached_meaningful_directory_depth(self):
        names = {row[0] for row in CATALOG}
        self.assertGreaterEqual(len(CATALOG), 50)
        self.assertTrue(ADDED.issubset(names))

    def test_new_tools_have_truthful_added_lifecycle_records(self):
        records = LIFECYCLE["tools"]
        for name in ADDED:
            self.assertEqual(records[name]["event"], "added", name)
            timestamp = records[name]["firstTrackedAt"]
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            self.assertIsNotNone(parsed.tzinfo, name)

    def test_selected_new_capabilities_are_backed_by_official_sources(self):
        expected = {
            "DeepSeek": "developer-api",
            "Ideogram": "developer-api",
            "HeyGen": "developer-api",
            "Activepieces": "self-hosting",
            "Dify": "self-hosting",
            "AnythingLLM": "self-hosting",
            "LocalAI": "developer-api",
        }
        for tool, fact_id in expected.items():
            facts = FACTS["tools"][tool]
            fact = next(item for item in facts if item["id"] == fact_id)
            host = urlparse(fact["sourceUrl"]).netloc
            self.assertTrue(host)
            self.assertNotIn("futuretools.io", host)
            self.assertEqual(fact["value"], "available")

    def test_local_first_additions_participate_in_recommender(self):
        for tool in ("Jan", "AnythingLLM", "LocalAI"):
            self.assertIn(tool, RECOMMENDER["profiles"])
            self.assertIn("local", RECOMMENDER["profiles"][tool]["tasks"])
            self.assertIn("privacy", RECOMMENDER["profiles"][tool]["traits"])
            self.assertIn(tool, FIT)
            self.assertIn("local", FIT[tool]["w"])


if __name__ == "__main__":
    unittest.main()
