"""Checks for the envelope layers: the shared records, every slot's coverage, and the documents that state them.

The named checks of core.engines.envelope_checks run here as well as in the main self-test, so a tools
shard fails when a guard is removed. The document checks read what the installed package cannot: every
LE-LAYER statement of the functional component standard has exactly one key word and its Maps to,
Enforced by and Today lines, every check it calls existing resolves, the decision record names every
layer and only statements that exist, and its coverage totals match the installed declarations. Each
guard has a known-wrong case beside it. Nothing here opens a network connection, starts a process or
calls a model.
"""
from __future__ import annotations

import re
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


STANDARD = REPOSITORY / "docs" / "architecture" / "FUNCTIONAL-COMPONENT-STANDARD.md"
DECISION = REPOSITORY / "docs" / "architecture" / "ADR-COMPONENT-ENVELOPE-LAYERS.md"
#: The key words of the standard, longest first so that MUST NOT is read as one word.
KEY_WORDS = re.compile(r"\b(MUST NOT|MUST|SHOULD NOT|SHOULD)\b")
EXISTING_CHECK = re.compile(r"existing `([a-z_][a-z0-9_.]*:[a-z][a-z0-9_]*)`")
STATE_WORDS = ("holds", "partly", "fails", "designed", "not built")


def layer_statements(text: str) -> dict:
    """Each LE-LAYER statement of the standard: identifier -> its block, up to the next heading."""
    parts = re.split(r"^#### (LE-LAYER-\d{3})\n", text, flags=re.M)
    statements = {}
    for identifier, block in zip(parts[1::2], parts[2::2]):
        statements[identifier] = re.split(r"^#{2,4} ", block, flags=re.M)[0]
    return statements


def statement_problems(statements: dict, resolves) -> list:
    """What breaks the standard's own format (LE-RULE-001 and LE-RULE-002) in one set of statements."""
    problems = []
    for position, (identifier, block) in enumerate(statements.items(), start=1):
        if identifier != f"LE-LAYER-{position:03d}":
            problems.append(f"{identifier}: identifiers run in order from LE-LAYER-001")
        body = block.split("\n- ", 1)[0]
        words = KEY_WORDS.findall(body)
        if len(words) != 1:
            problems.append(f"{identifier}: {len(words)} key words")
        for label in ("\n- Maps to: ", "\n- Enforced by: ", "\n- Today: "):
            if label not in block:
                problems.append(f"{identifier}: no {label.strip()}")
        if words and words[0].startswith("SHOULD") and "\n- Set aside when: " not in block:
            problems.append(f"{identifier}: a recommendation without Set aside when")
        today = block.split("\n- Today: ", 1)[-1]
        if not today.startswith(STATE_WORDS):
            problems.append(f"{identifier}: Today starts with no state word")
        problems += [f"{identifier}: {reference} does not resolve" for reference in EXISTING_CHECK.findall(block)
                     if not resolves(reference)]
    return problems


class DocumentTests(unittest.TestCase):
    def setUp(self):
        from loop_engine.core.engines.slot_index import current_join_sources
        self.resolves = current_join_sources().resolve_check
        self.statements = layer_statements(STANDARD.read_text(encoding="utf-8"))

    def test_every_layer_statement_follows_the_standards_own_format(self):
        self.assertEqual(len(self.statements), 28)
        self.assertEqual(statement_problems(self.statements, self.resolves), [])

    def test_known_wrong_statements_are_refused(self):
        good = self.statements["LE-LAYER-001"]
        planted = {
            "LE-LAYER-001": good.replace("MUST apply", "MUST and SHOULD apply"),
            "LE-LAYER-002": good.split("\n- Today: ")[0],
            "LE-LAYER-003": good.replace("the_envelope_layers_keep_their_declared_order", "no_such_envelope_check"),
            "LE-LAYER-005": good.replace("- Today: partly", "- Today: mostly"),
        }
        problems = " | ".join(statement_problems(planted, self.resolves))
        for expected in ("LE-LAYER-001: 2 key words", "LE-LAYER-002: no - Today:",
                         "core.engines.envelope_checks:no_such_envelope_check does not resolve",
                         "LE-LAYER-005: identifiers run in order", "LE-LAYER-005: Today starts with no state word"):
            self.assertIn(expected, problems)

    def test_every_envelope_check_the_standard_cites_is_one_the_self_test_runs(self):
        names = {item["test"] for item in envelope_checks.self_test()["tests"]}
        cited = {reference.split(":", 1)[1] for block in self.statements.values()
                 for reference in EXISTING_CHECK.findall(block) if reference.startswith("core.engines.envelope_checks:")}
        self.assertTrue(cited)
        self.assertEqual(sorted(cited - names), [])

    def test_the_decision_record_names_every_layer_and_only_statements_that_exist(self):
        decision = DECISION.read_text(encoding="utf-8")
        for layer in COVERAGE_LAYERS:
            self.assertIn(f"`{layer}`", decision)
        named = set(re.findall(r"LE-LAYER-\d{3}", decision))
        self.assertTrue(named)
        self.assertEqual(sorted(named - set(self.statements)), [])
        self.assertIn("FUNCTIONAL-COMPONENT-STANDARD.md#14-envelope-layers-around-every-functional-engine", decision)

    def test_the_decision_records_coverage_totals_match_the_installed_declarations(self):
        totals = coverage_report()["totals"]
        decision = DECISION.read_text(encoding="utf-8")
        row = (f"| All {sum(totals.values())} declarations of {len(load_engine_slot_catalog().slots)} slots | "
               f"{totals['full']} | {totals['partial']} | {totals['none']} | {totals['not_applicable']} |")
        self.assertIn(row, decision)


if __name__ == "__main__":
    unittest.main()
