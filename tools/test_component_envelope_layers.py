"""Checks for the envelope layers: the shared records and the coverage that every engine slot declares.

The named checks of core.engines.envelope_checks run here as well as in the main self-test, so a tools
shard fails when a guard is removed. Each guard has a known-wrong case beside it; the coverage report is
read from the installed declarations and baseline. Nothing here opens a network connection, starts a
process or calls a model.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))

from loop_engine.core.engines import envelope_checks  # noqa: E402
from loop_engine.core.engines.envelope import COVERAGE_LAYERS  # noqa: E402
from loop_engine.core.engines.envelope_coverage import (  # noqa: E402
    RECORDED_BASELINE_FLOOR, coverage_report, load_envelope_coverage, load_envelope_coverage_baseline)
from loop_engine.core.engines.slots import load_engine_slot_catalog  # noqa: E402


class EnvelopeCheckTests(unittest.TestCase):
    def test_every_named_envelope_check_passes(self):
        report = envelope_checks.self_test()
        failed = [item["test"] + ": " + item["detail"] for item in report["tests"] if not item["passed"]]
        self.assertEqual(failed, [])
        self.assertGreaterEqual(report["total"], 21)

    def test_every_removed_guard_control_is_present(self):
        names = {item["test"] for item in envelope_checks.self_test()["tests"]}
        self.assertTrue({"removed_declared_match_requirement_is_detected", "removed_declaration_join_is_detected",
                         "removed_baseline_ratchet_is_detected"} <= names)


class CoverageTests(unittest.TestCase):
    def test_every_catalogued_slot_declares_every_layer_and_the_report_is_valid(self):
        catalog, coverage = load_engine_slot_catalog(), load_envelope_coverage()
        report = coverage_report()
        self.assertTrue(report["valid"], report["findings"][:5])
        self.assertEqual([slot.slot_id for slot in coverage.slots], [slot.slot_id for slot in catalog.slots])
        self.assertEqual(sum(report["totals"].values()), len(catalog.slots) * len(COVERAGE_LAYERS))

    def test_the_baseline_rows_match_the_catalogue_and_keep_their_floor(self):
        catalog, baseline = load_engine_slot_catalog(), load_envelope_coverage_baseline()
        self.assertEqual(set(baseline.slots), {slot.slot_id for slot in catalog.slots})
        totals = baseline.totals()
        for name, floor in RECORDED_BASELINE_FLOOR.items():
            self.assertGreaterEqual(totals[name], floor, name)

    def test_known_wrong_a_slot_without_declarations_is_reported(self):
        from dataclasses import replace
        coverage = load_envelope_coverage()
        missing = replace(coverage, slots=coverage.slots[:-1])
        report = coverage_report(coverage=missing)
        self.assertIn((coverage.slots[-1].slot_id, "slot_without_envelope_declarations"),
                      {(item["slot_id"], item["code"]) for item in report["findings"]})


if __name__ == "__main__":
    unittest.main()
