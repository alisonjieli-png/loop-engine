"""The demonstration record is written from the library, and cannot drift from it.

The known-wrong case is the one that has already cost a release: a packaged body
changes, the library grows, and the digests, sizes, kinds and licences the page
records no longer describe this release. The check must report that drift, and
the write must repair it, and neither may invent an identity, reorder a result,
or add or remove a step.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import record_demonstration_steps as record  # noqa: E402


class DemonstrationRecordTest(unittest.TestCase):
    """What the record holds, and what the writer is forbidden to change."""

    def setUp(self) -> None:
        self.page = record.PAGE.read_text(encoding="utf-8")
        self.items = record.released_items()

    def test_every_recorded_reference_is_in_this_release(self) -> None:
        """A reference the page shows but the release does not hold is a known-wrong page."""
        for identity in re.findall(r'data-demo-item="([a-z0-9_]+)"', self.page):
            self.assertIn(identity, self.items, identity)

    def test_the_record_already_matches_the_release(self) -> None:
        """The standing state: a release whose recorded facts were never written by hand."""
        written, _ = record._rewrite(self.page)
        self.assertEqual(written, self.page)

    def test_a_changed_body_is_reported_and_repaired(self) -> None:
        """The known-wrong case: one recorded digest no longer names this release's bytes."""
        found = re.search(
            r'<li data-demo-item="(?P<identity>[a-z0-9_]+)".*?'
            r'<span data-fact="digest">(?P<value>[0-9a-f]{8,64})',
            self.page, re.DOTALL)
        self.assertIsNotNone(found, "the page records no reference with a digest")
        identity, served = found.group("identity"), str(self.items[found.group("identity")]["digest"])
        planted = self.page[: found.start("value")] + ("0" * 8) + self.page[found.end("value") :]
        written, _ = record._rewrite(planted)
        self.assertNotEqual(written, planted, "a stale digest was not repaired")
        self.assertIn(f'<span data-fact="digest">{served[:8]}', written)

    def test_the_writer_adds_and_removes_no_reference(self) -> None:
        """The writer rewrites facts only. It may not change which references appear."""
        before = re.findall(r'data-demo-item="([a-z0-9_]+)"', self.page)
        after = re.findall(r'data-demo-item="([a-z0-9_]+)"', record._rewrite(self.page)[0])
        self.assertEqual(before, after)

    def test_a_reference_this_release_lacks_is_reported_not_dropped(self) -> None:
        """A recorded reference with no match is a problem to report, never a silent deletion."""
        planted = self.page.replace('data-demo-item="', 'data-demo-item="absent_', 1)
        written, problems = record._rewrite(planted)
        self.assertIn("absent_", written, "the writer deleted a reference instead of reporting it")
        self.assertTrue(problems)

    def test_expected_download_is_generated_from_its_named_packaged_reference(self):
        shown = record._EXPECTED.search(self.page)
        self.assertIsNotNone(shown)
        planted = self.page[:shown.start()] + shown.group().replace(self.items[shown.group("identity")]["digest"], "0" * 64) + self.page[shown.end():]
        corrected, problems = record._rewrite(planted)
        self.assertEqual(problems, [])
        self.assertEqual(corrected, self.page)

    def test_every_scripted_reference_matches_the_same_manifest(self):
        source = record.SCRIPT.read_text()
        rewritten, problems = record._rewrite_script(source)
        self.assertEqual(problems, [])
        self.assertEqual(source, rewritten)
        self.assertEqual(len(record._SCENARIO_REFERENCE.findall(source)), 7)
        first = record._SCENARIO_REFERENCE.search(source)
        planted = source[:first.start()] + first.group().replace(self.items[first.group("identity")]["digest"], "0" * 64) + source[first.end():]
        corrected, problems = record._rewrite_script(planted)
        self.assertEqual(problems, [])
        self.assertEqual(corrected, source)
        self.assertNotEqual(corrected, planted)

    def test_script_writer_preserves_scenario_evidence_choices_and_refuses_unknown_reference(self):
        source = record.SCRIPT.read_text()
        rewritten, _ = record._rewrite_script(source)
        for field in ("evidence_class", "evidence_label", "evidence_href", "evidence_link", "outcome", "query", "chosen"):
            pattern = field + r': [^\n]+'
            self.assertEqual(re.findall(pattern, source), re.findall(pattern, rewritten))
        planted = source.replace('{name: "find_duplicate_records_with_blocking_keys"', '{name: "missing_reference"', 1)
        rewritten, problems = record._rewrite_script(planted)
        self.assertTrue(problems)
        self.assertIn('name: "missing_reference"', rewritten)


if __name__ == "__main__":
    unittest.main()
