import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATEGORY = (ROOT / "category.html").read_text(encoding="utf-8")
INDEX = (ROOT / "categories.html").read_text(encoding="utf-8")
CSS = (ROOT / "styles" / "discovery-hub.css").read_text(encoding="utf-8")


class RichCategoryPageTests(unittest.TestCase):
    def test_category_index_opens_rich_category_page(self):
        self.assertIn('category.html?category=${encodeURIComponent(cat)}&lang=${lang}', INDEX)
        self.assertIn("richer category page", INDEX)

    def test_category_page_loads_maintained_and_verified_sources(self):
        for token in (
            'fetch("data/tools.json"',
            'fetch("data/recommender.json"',
            'fetch("data/recommender-fit.json"',
            'fetch("data/verified-facts.json"',
        ):
            self.assertIn(token, CATEGORY)

    def test_category_page_exposes_useful_non_popularity_views(self):
        for token in ("Free-friendly", "Open source", "Local / private fit", "Officially verified capabilities"):
            self.assertIn(token, CATEGORY)
        self.assertIn("without popularity ranking", CATEGORY)
        self.assertIn("Missing facts stay unknown", CATEGORY)
        self.assertNotIn("Top rated", CATEGORY)
        self.assertNotIn("Most popular", CATEGORY)

    def test_verified_capabilities_are_fact_driven(self):
        self.assertIn('f?.id==="self-hosting"', CATEGORY)
        self.assertIn('["developer-api","inference-api"]', CATEGORY)
        self.assertIn('f?.value==="available"', CATEGORY)

    def test_local_view_uses_recommender_metadata(self):
        self.assertIn('p.tasks?.includes("local")', CATEGORY)
        self.assertIn('p.traits?.includes("privacy")', CATEGORY)

    def test_category_page_is_bilingual_rtl_and_responsive(self):
        self.assertIn('document.documentElement.dir=lang==="ar"?"rtl":"ltr"', CATEGORY)
        self.assertIn("استكشف", CATEGORY)
        self.assertIn("@media(max-width:680px)", CSS)
        self.assertIn(".category-tool-grid", CSS)
        self.assertIn(".subset-grid", CSS)


if __name__ == "__main__":
    unittest.main()
