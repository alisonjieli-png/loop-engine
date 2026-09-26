"""Checks for tools/measure_paged_listing.py on the eight-item fixture bundle, without the real bundle.

The fixture bundle is published into a temporary service store with the
service's own code and walked over a real loopback socket at a small answer cap
and at the default one. Every walk must return every offered row exactly once,
the unpaged list must be refused at the small cap with the refusal that names
`page_size`, and a root inside this repository is the known-wrong case the tool
must refuse before it writes anything.
"""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

import measure_paged_listing as tool  # noqa: E402
from test_measure_catalogue_serving import write_fixture_bundle  # noqa: E402


class PagedListingMeasurementTest(unittest.TestCase):
    def test_every_walk_returns_every_offered_row_once_under_a_small_cap(self):
        with tempfile.TemporaryDirectory(prefix="paged-measure-") as folder:
            bundle = write_fixture_bundle(Path(folder) / "bundle")
            record = tool.measure(bundle, Path(folder) / "root", caps=(4096, 262_144), page_sizes=(3,))
        paged = [row for row in record["walks"] if row["walk"] != "unpaged"]
        self.assertEqual(record["record_type"], tool.RESULT_RECORD_TYPE)
        self.assertEqual(len(paged), 2 * len(tool.effect_sets()) * 2)
        self.assertTrue(all(row.get("every_row_once") for row in paged), paged)
        small = [row for row in paged if row["cap"] == 4096]
        self.assertTrue(all(row["largest_answer_bytes"] <= 4096 for row in small), small)
        self.assertTrue(any(row["pages"] > 1 for row in small))
        refused = [row for row in record["walks"] if row["walk"] == "unpaged" and row["cap"] == 4096]
        self.assertEqual([(row["status"], row["refused"]) for row in refused], [(413, "response_limit_exceeded")])

    def test_a_root_inside_the_repository_is_refused_before_anything_is_written(self):
        with tempfile.TemporaryDirectory(prefix="paged-measure-") as folder:
            bundle = write_fixture_bundle(Path(folder) / "bundle")
            inside = HERE.parent / "paged-measure-refused-root"
            with self.assertRaises(tool.serving.MeasurementRefused) as refused:
                tool.measure(bundle, inside, caps=(262_144,), page_sizes=(3,))
            self.assertEqual(refused.exception.code, "root_inside_repository")
            self.assertFalse(inside.exists())


if __name__ == "__main__":
    unittest.main()
