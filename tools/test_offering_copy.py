"""Customer offering names agree across pages, account states and generated guides.

The approved terms remain an exact legal record. Billing identifiers and past
provider invoices are not display copy and are not renamed by these checks.
"""
from pathlib import Path
import hashlib
import json
import re
import unittest

from test_homepage_demonstration import read_marked


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "src/loop_engine/core/service_runtime"
ASSETS = RUNTIME / "web_assets"
COMBINED = "Agent Feeds + Harness Files"
RETIRED = re.compile(r"\bBaltor Pro\b|\bone plan\b|refresh(?:ing)? the context", re.I)
FEED_FACTS = ("$4.99 a month", "Free through December 31, 2026 (Eastern)", "No automatic charge", "opt-in", "source collections")
PREVIEW_FACTS = ("local", "overnight", "preview", "limits", "checkpoints", "morning report")
FUTURE_MARKETING = re.compile(r"\bplanned\b|coming soon|in development|being qualified", re.I)


def marketing_views(page):
    """Check all application views, not only the initially visible homepage."""
    return {row["attrs"]["data-view"]: row["text"] for row in read_marked(page)
            if "data-view" in row["attrs"] and row["attrs"]["data-view"] != "terms"}


def retired_copy(text):
    return RETIRED.findall(text)


def feed_price_problems(text):
    text = re.sub(r"\s+", " ", text)
    problems = ["missing " + fact for fact in FEED_FACTS if fact not in text]
    if re.search(r"automatically (?:charged|billed)|free forever|personalized feeds are available now", text, re.I):
        problems.append("unsupported enrollment or availability claim")
    return problems


def overnight_tools_problems(text):
    problems = ["missing " + fact for fact in PREVIEW_FACTS if fact not in text.lower()]
    if re.search(r"hosted supervision|guaranteed results|unlimited model", text, re.I) or FUTURE_MARKETING.search(text):
        problems.append("unqualified hosted feature, result or future promise")
    return problems


class OfferingCopyTests(unittest.TestCase):
    def test_local_overnight_preview_is_visible_with_a_working_setup_guide(self):
        page = (ASSETS / "index.html").read_text()
        tools = [row for row in read_marked(page) if "data-overnight-tools" in row["attrs"]]
        self.assertEqual(len(tools), 3, "home, pricing and overnight must describe the usable local tools")
        for row in tools:
            self.assertEqual(row["attrs"]["data-overnight-tools"], "local")
            self.assertEqual(overnight_tools_problems(row["text"]), [])
        views = marketing_views(page)
        for name in ("home", "pricing", "overnight", "use-cases", "for-designers"):
            self.assertIsNone(FUTURE_MARKETING.search(views[name]), name)
        self.assertIn('href="https://github.com/alisonjieli-png/loop-engine/blob/main/tools/OVERNIGHT-QUEUE.md"', page)
        self.assertTrue((ROOT / "tools/OVERNIGHT-QUEUE.md").is_file())

    def test_preview_guard_rejects_missing_scope_features_and_unqualified_promises(self):
        valid = " ".join(PREVIEW_FACTS)
        self.assertEqual(overnight_tools_problems(valid), [])
        for fact in PREVIEW_FACTS:
            self.assertTrue(overnight_tools_problems(valid.replace(fact, "")), fact)
        for claim in ("Hosted supervision", "Guaranteed results", "Unlimited model calls", "Planned preview", "Coming soon"):
            self.assertTrue(overnight_tools_problems(valid + " " + claim), claim)

    def test_every_application_view_uses_current_customer_names(self):
        views = marketing_views((ASSETS / "index.html").read_text())
        self.assertGreater(len(views), 20)
        self.assertIn("pricing", views)
        self.assertIn("account", views)
        self.assertEqual({name: retired_copy(text) for name, text in views.items()
                          if retired_copy(text)}, {})

    def test_three_offerings_are_named_on_home_and_pricing(self):
        views = marketing_views((ASSETS / "index.html").read_text())
        for name in ("home", "pricing"):
            text = re.sub(r"\s+", " ", views[name])
            for fact in ("Agent Feeds", COMBINED, "Overnight / AFK Work", "Included in Preview", "$29"):
                self.assertIn(fact, text, (name, fact))
            self.assertEqual(feed_price_problems(text), [], name)

    def test_pricing_is_outside_the_hero_and_overnight_has_its_own_card(self):
        rows = read_marked((ASSETS / "index.html").read_text())
        hero = [row for row in rows if row["attrs"].get("data-band") == "hero"]
        self.assertEqual(len(hero), 1)
        self.assertNotIn("a month", hero[0]["text"])
        cards = [row for row in rows if "data-offering" in row["attrs"]]
        expected = ["agent-feeds", "agent-feeds-harness-files", "overnight-afk-work"] * 2
        self.assertEqual([row["attrs"]["data-offering"] for row in cards], expected)
        for row in cards:
            if row["attrs"]["data-offering"] == "overnight-afk-work":
                self.assertIn("No extra charge", row["text"])
                self.assertEqual(overnight_tools_problems(row["text"]), [])

    def test_feed_price_period_consent_and_availability_are_not_optional(self):
        from loop_engine.core.service_runtime.catalogue_feed import page_body
        text = marketing_views('<section data-view="feeds">' + page_body() + '</section>')["feeds"]
        self.assertEqual(feed_price_problems(text), [])
        self.assertIsNone(FUTURE_MARKETING.search(text))
        valid = " ".join(FEED_FACTS)
        for fact in FEED_FACTS:
            self.assertTrue(feed_price_problems(valid.replace(fact, "")), fact)
        for wrong in ("Automatically charged in 2027", "Free forever", "Personalized feeds are available now"):
            self.assertTrue(feed_price_problems(valid + " " + wrong), wrong)

    def test_free_feed_actions_do_not_start_the_existing_paid_library_journey(self):
        for row in read_marked((ASSETS / "index.html").read_text()):
            if row["attrs"].get("data-offering") == "agent-feeds":
                self.assertNotRegex(row["text"], r"\bSubscribe (?:now|for)\b")
        source = (ASSETS / "index.html").read_text()
        cards = re.findall(r'<(?:article|section)[^>]*data-offering="agent-feeds"[^>]*>(.*?)</(?:article|section)>', source, re.S)
        self.assertEqual(len(cards), 2)
        for card in cards:
            self.assertEqual(re.findall(r'href="([^"]+)"', card), ["/feeds"])
            self.assertNotIn("data-access-state", card)

    def test_marketing_does_not_relabel_package_counts_as_files(self):
        views = marketing_views((ASSETS / "index.html").read_text())
        for name in ("home", "use-cases", "about", "setup"):
            self.assertNotRegex(views[name], r"\bpackages?\b", name)
        self.assertNotIn("data-library-count>", (ASSETS / "index.html").read_text())

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
        self.assertIn("Last changed: October 8, 2026", terms[0])
        self.assertNotIn("One plan, Baltor Pro, at $29 a month", terms[0])
        for fact in ("shown before you subscribe", "future purchases and renewals",
                     "billing period you have already paid for", "advance notice",
                     "consent required by law", "requires your explicit opt-in",
                     "cancel from your account page"):
            self.assertIn(fact, terms[0])

    def test_pricing_clause_is_flexible_without_repricing_existing_periods(self):
        terms = (ROOT / "docs/legal/TERMS-OF-SERVICE.md").read_text()
        clause = re.search(r"(?ms)^6\. (.*?)(?=^7\.)", terms).group(1)
        clause = re.sub(r"\s+", " ", clause)
        self.assertNotRegex(clause, r"\$\d|One plan")
        self.assertIn("billing period you have already paid for", clause)
        self.assertIn("before a change to your subscription takes effect", clause)
        self.assertIn("keep access until the end of the paid period", clause)
        # The owner's October 8 approval changes pricing, not the service
        # definition or permission to collect data for hosted execution.
        self.assertIn("Baltor does not run your tasks", terms)
        self.assertIn("to the amount you paid in the three months", terms)

    def test_the_pricing_approval_does_not_rewrite_other_legal_sections(self):
        text = (ROOT / "docs/legal/TERMS-OF-SERVICE.md").read_text()
        untouched = re.sub(r"(?m)^Last changed:.*\n", "", text)
        untouched = re.sub(r"(?ms)^6\..*?(?=^7\.)", "", untouched)
        # Exact remaining bytes of the September 23 approved document at
        # e51c083b, excluding only the authorized price clause and date.
        expected = "10753d7160c3b0961349f4d917aa7ce77f206a1d0b3320ae32b62ce9615a4d20"
        self.assertEqual(hashlib.sha256(untouched.encode()).hexdigest(), expected)
        self.assertNotEqual(hashlib.sha256(untouched.replace(
            "three months", "one month").encode()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
