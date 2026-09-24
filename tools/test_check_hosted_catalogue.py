"""Known-wrong cases for the homepage digest guard of tools/check_hosted_catalogue.py."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_hosted_catalogue import demonstration_digests, demonstration_mismatches  # noqa: E402

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


if __name__ == "__main__":
    unittest.main()
