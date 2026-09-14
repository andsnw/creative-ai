from pathlib import Path
import unittest

SCRIPT = Path("scripts/audit_catalog_links.py").read_text(encoding="utf-8")
METHOD = Path("docs/CATALOG_AUDIT_METHOD.md").read_text(encoding="utf-8")


class CatalogLinkAuditTests(unittest.TestCase):
    def test_audit_flags_parked_and_shutdown_pages(self):
        self.assertIn("parked-domain", SCRIPT)
        self.assertIn("domain (?:is )?for sale", SCRIPT)
        self.assertIn("shutdown", SCRIPT)
        self.assertIn("farewell", SCRIPT)
        self.assertIn("discontinued", SCRIPT)

    def test_audit_flags_cross_domain_redirects(self):
        self.assertIn("cross-domain-redirect", SCRIPT)
        self.assertIn("registrable_hint(url) != registrable_hint(final_url)", SCRIPT)

    def test_client_errors_are_not_all_treated_as_dead(self):
        self.assertIn("exc.code in {404, 410}", SCRIPT)
        self.assertNotIn("400 <= exc.code < 500", SCRIPT)

    def test_audit_is_reporting_first_not_a_popularity_score(self):
        self.assertIn("A live URL is **not** proof that a tool is good", METHOD)
        self.assertIn("does **not** import third-party popularity numbers", METHOD)
        self.assertIn("Third-party directories are discovery inputs only", METHOD)


if __name__ == "__main__":
    unittest.main()
