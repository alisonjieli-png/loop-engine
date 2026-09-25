"""Known-wrong cases for the homepage and demonstration page digest guards of tools/check_hosted_catalogue.py."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_hosted_catalogue import demonstration_digests, demonstration_mismatches, demonstration_page_digests  # noqa: E402

PAGE = ('<li data-demo-item="split_address_lines_into_components" class="is-chosen"><span>split</span>'
        '<span data-fact="digest">53dc74e3</span>…</li>'
        '<li data-demo-item="find_duplicate_records_with_blocking_keys"><span data-fact="digest">34da79f4</span></li>')
SERVED = {"split_address_lines_into_components": "53dc74e3" + "0" * 56,
          "find_duplicate_records_with_blocking_keys": "34da79f4" + "1" * 56}


class DemonstrationDigestTests(unittest.TestCase):
    def test_the_page_reader_finds_each_item_with_its_own_digest(self):
        self.assertEqual(demonstration_digests(PAGE), {"split_address_lines_into_components": "53dc74e3",
                                                      "find_duplicate_records_with_blocking_keys": "34da79f4"})

    def test_matching_digests_leave_nothing_to_report(self):
        self.assertEqual(demonstration_mismatches(demonstration_digests(PAGE), SERVED), {})

    def test_known_wrong_a_page_printing_a_digest_the_service_does_not_serve_is_reported(self):
        # Release 24 on September 24, 2026: the page printed the new anchor's digest while the
        # service still served the previous catalogue release.
        served = {**SERVED, "split_address_lines_into_components": "e3baf9a4" + "0" * 56}
        self.assertEqual(demonstration_mismatches(demonstration_digests(PAGE), served),
                         {"split_address_lines_into_components": {"shown": "53dc74e3", "served": "e3baf9a4"}})

    def test_known_wrong_an_item_the_service_does_not_serve_is_reported(self):
        served = {"find_duplicate_records_with_blocking_keys": SERVED["find_duplicate_records_with_blocking_keys"]}
        self.assertIn("split_address_lines_into_components",
                      demonstration_mismatches(demonstration_digests(PAGE), served))

    def test_known_wrong_a_page_without_the_demonstration_names_nothing(self):
        self.assertEqual(demonstration_digests("<main>no demonstration</main>"), {})


ONE_PAGE = ('<main>\n    <section data-view="home">' + PAGE + '</section>\n'
            '    <section data-view="demo" hidden><li data-demo-item="profile_text_column_before_cleaning" class="is-chosen">'
            '<span data-fact="digest">3274cbf5</span></li></section>\n    <section data-view="pricing" hidden>'
            '<li data-demo-item="invented_item"><span data-fact="digest">00000000</span></li></section>\n</main>')


class ViewDigestTests(unittest.TestCase):
    def test_each_view_is_read_on_its_own(self):
        self.assertEqual(demonstration_page_digests(ONE_PAGE, "home"), demonstration_digests(PAGE))
        self.assertEqual(demonstration_page_digests(ONE_PAGE, "demo"), {"profile_text_column_before_cleaning": "3274cbf5"})

    def test_known_wrong_a_page_without_the_view_names_nothing(self):
        # A deployed page that lost the demonstration view must not borrow the homepage's items.
        self.assertEqual(demonstration_page_digests(ONE_PAGE.replace('data-view="demo"', 'data-view="retired"'), "demo"), {})

    def test_known_wrong_an_item_of_the_next_view_is_not_read_as_the_demonstration(self):
        self.assertNotIn("invented_item", demonstration_page_digests(ONE_PAGE, "demo"))

    def test_every_demonstration_page_is_checked_on_its_own(self):
        from check_hosted_catalogue import DEMONSTRATION_PAGES, PLANNED_CHECKS
        self.assertEqual([view for _address, view in DEMONSTRATION_PAGES], ["demo", "demo-kaggle"])
        self.assertEqual(PLANNED_CHECKS, 9)
        kaggle = ONE_PAGE.replace('data-view="demo" hidden', 'data-view="demo-kaggle" hidden')
        self.assertEqual(demonstration_page_digests(kaggle, "demo-kaggle"), {"profile_text_column_before_cleaning": "3274cbf5"})
        # KNOWN_WRONG: the view of the other demonstration is not read as this one.
        self.assertEqual(demonstration_page_digests(kaggle, "demo"), {})


APPROVED = ["split_address_lines_into_components", "find_duplicate_records_with_blocking_keys"]


class SearchTierTests(unittest.TestCase):
    """Since the first Community catalogue release (September 25, 2026) a search also returns Community items."""

    def test_verified_and_labelled_community_hits_leave_nothing_to_report(self):
        from check_hosted_catalogue import unapproved_verified_hits, unlabelled_other_hits
        self.assertEqual(unapproved_verified_hits(APPROVED[:1], APPROVED), [])
        hits = [(APPROVED[0], "verified", "Verified"), ("audio_aggregation_agentic_task", "community", "Community")]
        self.assertEqual(unlabelled_other_hits(hits, APPROVED), [])

    def test_known_wrong_a_verified_only_search_returning_an_unapproved_item_is_reported(self):
        from check_hosted_catalogue import unapproved_verified_hits
        self.assertEqual(unapproved_verified_hits([APPROVED[0], "audio_aggregation_agentic_task"], APPROVED),
                         ["audio_aggregation_agentic_task"])

    def test_known_wrong_an_unapproved_hit_labelled_verified_is_reported(self):
        from check_hosted_catalogue import unlabelled_other_hits
        self.assertEqual(unlabelled_other_hits([("invented_item", "verified", "Verified")], APPROVED), ["invented_item"])

    def test_known_wrong_a_community_hit_without_its_label_is_reported(self):
        from check_hosted_catalogue import unlabelled_other_hits
        self.assertEqual(unlabelled_other_hits([("audio_aggregation_agentic_task", "community", None)], APPROVED),
                         ["audio_aggregation_agentic_task"])
        self.assertEqual(unlabelled_other_hits([("audio_aggregation_agentic_task", None, None)], APPROVED),
                         ["audio_aggregation_agentic_task"])


if __name__ == "__main__":
    unittest.main()
