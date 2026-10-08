"""Customer offering names agree across pages, account states and generated guides.

The approved terms remain an exact legal record. Billing identifiers and past
provider invoices are not display copy and are not renamed by these checks.
"""
from pathlib import Path
import json
import re
import unittest

from test_homepage_demonstration import read_marked


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "src/loop_engine/core/service_runtime"
ASSETS = RUNTIME / "web_assets"
COMBINED = "Agent Feeds + Harness Files"
RETIRED = re.compile(r"\bBaltor Pro\b|\bone plan\b|refresh(?:ing)? the context", re.I)


def marketing_views(page):
    """Check all application views, not only the initially visible homepage."""
    return {row["attrs"]["data-view"]: row["text"] for row in read_marked(page)
            if "data-view" in row["attrs"] and row["attrs"]["data-view"] != "terms"}


def retired_copy(text):
    return RETIRED.findall(text)


class OfferingCopyTests(unittest.TestCase):
    def test_every_application_view_uses_current_customer_names(self):
        views = marketing_views((ASSETS / "index.html").read_text())
        self.assertGreater(len(views), 20)
        self.assertIn("pricing", views)
        self.assertIn("account", views)
        self.assertEqual({name: retired_copy(text) for name, text in views.items()
                          if retired_copy(text)}, {})

    def test_both_offerings_are_named_on_home_and_pricing(self):
        views = marketing_views((ASSETS / "index.html").read_text())
        for name in ("home", "pricing"):
            text = re.sub(r"\s+", " ", views[name])
            for fact in ("Agent Feeds", COMBINED, "Free preview", "$29"):
                self.assertIn(fact, text, (name, fact))

    def test_generated_guides_have_no_retired_product_label(self):
        pages = list((ASSETS / "docs").glob("*.html"))
        self.assertGreaterEqual(len(pages), 15)
        self.assertEqual({p.name: retired_copy(p.read_text()) for p in pages
                          if retired_copy(p.read_text())}, {})

    def test_scripted_account_and_download_states_have_current_names(self):
        for filename in ("service.js", "catalogue-browser.js"):
            source = (ASSETS / filename).read_text()
            self.assertNotIn("Baltor Pro", source)
            self.assertNotIn('tag:"One plan"', source)
            self.assertIn(COMBINED, source)

    def test_search_descriptions_and_deck_use_current_names(self):
        site_map = json.loads((RUNTIME / "web_site_map.json").read_text())
        self.assertEqual(retired_copy(json.dumps(site_map)), [])
        self.assertEqual(retired_copy((ASSETS / "deck.html").read_text()), [])

    def test_refusal_names_the_same_offering_without_changing_billing_identity(self):
        from loop_engine.core.service_runtime.http import PLAN_NAME
        self.assertEqual(PLAN_NAME, COMBINED)
        self.assertIn('"baltor_pro"', (ROOT / "tools/setup_stripe_sandbox.py").read_text())

    def test_guard_refuses_old_copy_in_each_marketing_surface(self):
        for text in ("Baltor Pro", "One plan", "refresh the context",
                     "Refresh the context your agent uses"):
            self.assertTrue(retired_copy(text), text)
        page = '<section data-view="terms">Baltor Pro</section><section data-view="pricing">One plan</section>'
        views = marketing_views(page)
        self.assertNotIn("terms", views)
        self.assertTrue(retired_copy(views["pricing"]))

    def test_approved_terms_are_not_silently_rewritten(self):
        page = (ASSETS / "index.html").read_text()
        terms = [row["text"] for row in read_marked(page)
                 if row["attrs"].get("data-view") == "terms"]
        self.assertEqual(len(terms), 1)
        self.assertIn("One plan, Baltor Pro, at $29 a month", terms[0])


if __name__ == "__main__":
    unittest.main()
