"""Known-wrong checks for local multi-batch candidate review search."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from search_all_candidates import CandidateSearchError, inventory, search_all

ROOT = Path(__file__).resolve().parent
WAVE_TWO = ROOT.parent / "first-party-harness-candidates-2026-09-22-wave-2"
WAVE_THREE = ROOT.parent / "first-party-harness-candidates-2026-09-22-wave-3"


class MultiBatchSearchChecks(unittest.TestCase):
    def test_exact_three_batch_inventory_has_distinct_names_and_bytes(self) -> None:
        manifests, count = inventory([ROOT, WAVE_TWO, WAVE_THREE])
        self.assertEqual(count, 68)
        self.assertEqual(len(manifests), 3)

    def test_natural_queries_reach_each_batch_without_returning_bodies(self) -> None:
        cases = (
            ("convert kilograms and grams before adding", "audit-measurement-units"),
            ("what did sales promise that delivery has not scheduled", "carry-a-sales-promise-into-delivery"),
            ("a setup guide uses a key before the reader obtains it", "check-prerequisite-order-in-a-task-guide"),
        )
        for query, expected in cases:
            with self.subTest(query=query):
                result = search_all(roots=[ROOT, WAVE_TWO, WAVE_THREE], query=query)
                self.assertEqual(result["outcome"], "matches")
                self.assertEqual(result["matches"][0]["name"], expected)
                self.assertIn("package_sha256", result["matches"][0])
                self.assertNotIn("body", result["matches"][0])

    def test_unrelated_and_effectful_queries_do_not_gain_matches(self) -> None:
        unrelated = search_all(roots=[ROOT, WAVE_TWO, WAVE_THREE], query="bake rye sourdough")
        self.assertEqual(unrelated["outcome"], "no_match")
        effectful = search_all(roots=[ROOT, WAVE_TWO, WAVE_THREE],
                               query="edit customer stock records", required_effect="file_write")
        self.assertEqual(effectful["outcome"], "no_match")

    def test_changed_batch_bytes_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "batch"
            shutil.copytree(ROOT, copied)
            note = copied / "review-notes" / "audit-measurement-units.md"
            note.write_text(note.read_text(encoding="utf-8") + "Changed.\n", encoding="utf-8")
            with self.assertRaisesRegex(CandidateSearchError, "manifest does not match"):
                search_all(roots=[copied], query="measurement units")

    def test_repeated_candidate_identity_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "batch"
            shutil.copytree(ROOT, copied)
            with self.assertRaisesRegex(CandidateSearchError, "candidate name repeated"):
                inventory([ROOT, copied])


if __name__ == "__main__":
    unittest.main()
