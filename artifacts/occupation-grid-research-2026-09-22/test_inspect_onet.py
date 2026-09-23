"""Checks for the pinned, licensed occupation opportunity source."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import inspect_onet


class PinnedOccupationSourceChecks(unittest.TestCase):
    def test_exact_source_population_and_selection(self) -> None:
        record = json.loads(inspect_onet.render())
        counts = record["counts"]
        self.assertEqual(counts["source_occupation_rows"], 1016)
        self.assertEqual(counts["source_task_rows"], 18838)
        self.assertEqual(counts["source_task_to_activity_rows"], 24087)
        self.assertEqual(counts["selected_occupations"], 10)
        self.assertEqual(counts["task_rows"], 179)
        self.assertEqual(counts["unique_detailed_work_activity_ids"], 136)
        self.assertEqual(counts["activities_shared_across_selected_occupations"], 36)
        self.assertEqual(len(record["task_references"]), 179)
        self.assertEqual(
            len({(row["occupation_code"], row["task_id"]) for row in record["task_references"]}),
            179,
        )

    def test_changed_source_bytes_are_refused_before_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "source.zip"
            changed.write_bytes(b"not the pinned database")
            with self.assertRaisesRegex(ValueError, "source digest mismatch"):
                inspect_onet.render(changed)


if __name__ == "__main__":
    unittest.main()
