"""Dated popularity is never silently promoted to quality or Baltor adoption."""
import copy
import json
import unittest

from tools import build_top_mcp_page as page


class McpShortlistChecks(unittest.TestCase):
    def setUp(self):
        self.value = json.loads(page.DATA.read_text())

    def test_committed_view_matches_data_and_sources(self):
        self.assertEqual(page.PAGE.read_text(), page.built_page(self.value, page.PAGE.read_text()))
        body = page.render(self.value)
        for row in self.value["items"]:
            self.assertIn(row["docs"], body)
            self.assertIn(f'{row["stars"]:,}', body)
        self.assertIn(self.value["checked_at"], body)

    def test_order_is_stars_with_stable_names_not_paid_placement(self):
        body = page.render(self.value)
        expected = sorted(self.value["items"], key=lambda row: (-row["stars"], row["name"]))
        offsets = [body.index('data-mcp-repository="' + row["repository"] + '"') for row in expected]
        self.assertEqual(offsets, sorted(offsets))

    def test_unknown_or_fabricated_measurements_are_refused(self):
        for value in (None, "many", True, -1):
            changed = copy.deepcopy(self.value)
            changed["items"][0]["stars"] = value
            with self.assertRaises(ValueError):
                page.render(changed)
        changed = {**self.value, "baltor_usage_state": "frequently_used"}
        with self.assertRaises(ValueError):
            page.render(changed)

    def test_archived_repositories_leave_the_shortlist_and_have_no_fake_rank(self):
        changed = copy.deepcopy(self.value)
        changed["items"][0]["archived"] = True
        self.assertNotIn('data-mcp-repository="' + changed["items"][0]["repository"] + '"', page.render(changed))

    def test_html_is_escaped_and_source_cannot_switch_hosts(self):
        changed = copy.deepcopy(self.value)
        changed["items"][0]["name"] = '<img src=x onerror="bad">'
        self.assertNotIn('<img', page.render(changed))
        changed["items"][0]["source"] = "https://unrelated.example.org"
        with self.assertRaises(ValueError):
            page.render(changed)

    def test_failed_refresh_does_not_change_the_saved_snapshot(self):
        original = copy.deepcopy(self.value)
        def fail(*_args, **_kwargs):
            raise TimeoutError()
        with self.assertRaises(TimeoutError):
            page.refresh(self.value, runner=fail)
        self.assertEqual(self.value, original)


if __name__ == "__main__":
    unittest.main()
