"""Checks for reviewer calibration: known-wrong and known-good items asked before real candidates.

```text
What calibration must guarantee
├── The committed set
│   ├── each item is its base body with exactly the declared changes
│   ├── the item record names the new bytes' digest and size
│   └── every item passes the deterministic pre-checks, so its defect reaches the reviewers
├── A malformed set is refused
│   ├── a replacement that does not occur exactly once in its base body
│   └── a known-wrong item that plants no defect or names none
├── Evaluation
│   ├── approving a known-wrong item excludes the reviewer from the real run
│   ├── no verdict on a known-wrong item excludes it too
│   └── rejecting the known-good item is a recorded false refusal, not an exclusion
└── An excluded reviewer is never asked about a real candidate, and the reason is recorded
```

A mutant control removes the false-approval rule and shows that a reviewer who
approved a known-wrong item would then be trusted.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from candidate_review import calibration  # noqa: E402
from candidate_review import engines  # noqa: E402
from candidate_review import panel as panel_module  # noqa: E402
from candidate_review import prechecks  # noqa: E402
from candidate_review import verdicts  # noqa: E402
from candidate_review.records import CandidateReviewError  # noqa: E402

import test_candidate_review_panel as panel_check  # noqa: E402

RESOURCES = HERE / "candidate_review" / "resources"
SET_RECORD = json.loads((RESOURCES / "calibration-set.json").read_text(encoding="utf-8"))


def _set(value=None):
    return calibration.CalibrationSet.from_dict(value or SET_RECORD, panel_check.CRITERIA.ids)


def _requests(value=None):
    return _set(value).requests(panel_check.DATA, panel_check.PRODUCERS, panel_check.CRITERIA,
                                panel_check.INSTRUCTIONS.sha256)


class CommittedSetTest(unittest.TestCase):

    def test_each_item_is_its_base_body_with_exactly_the_declared_changes(self):
        for item, request in _requests():
            with self.subTest(item=item.identity):
                base = panel_check.DATA.body_bytes(item.base_identity).decode("utf-8")
                expected = base
                for find, replace in item.replacements:
                    expected = expected.replace(find, replace)
                self.assertEqual(request.body_text, expected)
                if item.expected_decision == verdicts.REJECT:
                    self.assertTrue(item.replacements or item.reference_overrides)
                else:
                    self.assertEqual(request.body, panel_check.DATA.body_bytes(item.base_identity))

    def test_the_item_record_names_the_new_bytes(self):
        for item, request in _requests():
            with self.subTest(item=item.identity):
                reference = request.item["reference"]
                self.assertEqual(reference["identity"], item.identity)
                self.assertEqual(reference["digest"], request.body_sha256)
                self.assertEqual(reference["size_bytes"], request.body_size_bytes)
                for name, value in item.reference_overrides.items():
                    self.assertEqual(reference[name], value)

    def test_every_item_reaches_the_reviewers(self):
        """The planted defects are questions of meaning: the deterministic pre-checks pass every item."""
        built = engines.build_precheck_engines(panel_check.BASE, only_builtin=True)
        population = _set().population(panel_check.DATA.population_bodies())
        for item, request in _requests():
            with self.subTest(item=item.identity):
                outcome = prechecks.run_prechecks(request, built,
                                                  prechecks.PrecheckContext(panel_check.BASE.policy, population))
                self.assertFalse(outcome.refused, outcome.reasons)

    def test_each_item_names_a_criterion_that_applies_to_its_kind(self):
        for item, request in _requests():
            with self.subTest(item=item.identity):
                self.assertIn(item.criterion_id, request.applicable_criteria_ids)

    def test_the_set_holds_known_wrong_items_and_a_known_good_control(self):
        decisions = [item.expected_decision for item in _set().items]
        self.assertGreaterEqual(decisions.count(verdicts.REJECT), 3)
        self.assertGreaterEqual(decisions.count(verdicts.APPROVE), 1)


class MalformedSetTest(unittest.TestCase):

    def test_a_replacement_that_does_not_occur_exactly_once_is_refused(self):
        value = copy.deepcopy(SET_RECORD)
        value["items"][0]["replacements"][0]["find"] = "a sentence that is in no body"
        with self.assertRaises(CandidateReviewError) as caught:
            _requests(value)
        self.assertEqual(caught.exception.code, "calibration_replacement_not_unique")

    def test_a_known_wrong_item_must_plant_and_name_its_defect(self):
        value = copy.deepcopy(SET_RECORD)
        value["items"][0]["replacements"] = []
        with self.assertRaises(CandidateReviewError) as caught:
            _set(value)
        self.assertEqual(caught.exception.code, "invalid_calibration_set")
        value = copy.deepcopy(SET_RECORD)
        value["items"][0]["defect"] = " "
        with self.assertRaises(CandidateReviewError):
            _set(value)

    def test_a_criterion_of_the_other_kind_of_body_is_refused(self):
        value = copy.deepcopy(SET_RECORD)
        value["items"][0]["criterion_id"] = "restated_source_grounding"
        with self.assertRaises(CandidateReviewError) as caught:
            _requests(value)
        self.assertEqual(caught.exception.code, "calibration_criterion_not_applicable")

    def test_only_declared_fields_may_be_overridden(self):
        value = copy.deepcopy(SET_RECORD)
        value["items"][2]["reference_overrides"] = {"license": "MIT"}
        with self.assertRaises(CandidateReviewError):
            _set(value)


def _calibration_run(scripts, families):
    with tempfile.TemporaryDirectory() as directory:
        harness = panel_check.Harness(directory, scripts, families=families)
        chosen = _set()
        requests = [request for _item, request in _requests()]
        panel = panel_module.ReviewPanel(
            harness.configuration, panel_check.CRITERIA, panel_check.INSTRUCTIONS, harness.reviewers,
            engines.build_precheck_engines(harness.configuration, only_builtin=True),
            panel_check.ReviewLedger(harness.ledger_path), sleeper=harness.sleep, clock=harness.clock)
        result = panel.run(panel_module.PanelRunRequest(
            run_id="calibration", requests=tuple(requests),
            population=chosen.population(panel_check.DATA.population_bodies()), call_ceiling=100,
            token_ceiling=10_000_000, model_calls_authorized=True, fixture_run=True,
            ask_every_eligible_reviewer=True))
        return calibration.evaluate(chosen, result), result, harness


def _expected_answer(prompt, number):
    expected = {item.identity: item.expected_decision for item in _set().items}
    return panel_check.attempt(panel_check.answer(prompt, expected[prompt.identity]))


def _approves_everything(prompt, number):
    return panel_check.attempt(panel_check.answer(prompt, verdicts.APPROVE))


def _rejects_everything(prompt, number):
    return panel_check.attempt(panel_check.answer(prompt, verdicts.REJECT))


class EvaluationTest(unittest.TestCase):

    def test_every_eligible_reviewer_is_asked_about_every_item(self):
        report, result, _harness = _calibration_run(
            {"good": _expected_answer, "lenient": _approves_everything, "strict": _rejects_everything},
            ("zhipu", "deepseek", "openai"))
        self.assertEqual(len(result.calls), 3 * len(SET_RECORD["items"]))

    def test_approving_a_known_wrong_item_excludes_the_reviewer(self):
        report, _result, _harness = _calibration_run(
            {"good": _expected_answer, "lenient": _approves_everything, "strict": _rejects_everything},
            ("zhipu", "deepseek", "openai"))
        self.assertEqual(report["installations"]["good"]["status"], "qualified")
        self.assertEqual(report["installations"]["lenient"]["status"], calibration.FAILED_CALIBRATION)
        self.assertEqual(len(report["installations"]["lenient"]["false_approvals"]), 3)
        self.assertEqual(report["installations"]["strict"]["status"], "qualified")
        self.assertEqual(len(report["installations"]["strict"]["false_refusals"]), 1)
        self.assertEqual(report["excluded"], {"lenient": calibration.FAILED_CALIBRATION})

    def test_no_verdict_on_a_known_wrong_item_excludes_the_reviewer(self):
        silent = lambda prompt, number: panel_check.attempt("not an answer")  # noqa: E731
        report, _result, _harness = _calibration_run({"good": _expected_answer, "silent": silent},
                                                      ("zhipu", "deepseek"))
        self.assertEqual(report["installations"]["silent"]["status"], calibration.CALIBRATION_INCOMPLETE)
        self.assertIn("silent", report["excluded"])

    def test_an_eligible_reviewer_the_calibration_never_reached_is_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = panel_check.Harness(directory, {"good": _expected_answer, "late": _expected_answer},
                                          families=("zhipu", "deepseek"))
            chosen = _set()
            panel = panel_module.ReviewPanel(
                harness.configuration, panel_check.CRITERIA, panel_check.INSTRUCTIONS, harness.reviewers,
                engines.build_precheck_engines(harness.configuration, only_builtin=True),
                panel_check.ReviewLedger(harness.ledger_path), sleeper=harness.sleep, clock=harness.clock)
            result = panel.run(panel_module.PanelRunRequest(
                run_id="calibration", requests=tuple(request for _item, request in _requests()),
                population=chosen.population(panel_check.DATA.population_bodies()), call_ceiling=1,
                token_ceiling=10_000_000, model_calls_authorized=True, fixture_run=True,
                ask_every_eligible_reviewer=True))
            report = calibration.evaluate(chosen, result)
        self.assertEqual(harness.calls("late"), [])
        self.assertEqual(report["installations"]["late"]["status"], calibration.CALIBRATION_INCOMPLETE)
        self.assertEqual(report["excluded"], {"good": calibration.CALIBRATION_INCOMPLETE,
                                              "late": calibration.CALIBRATION_INCOMPLETE})

    def test_the_false_approval_rule_is_what_excludes_a_lenient_reviewer(self):
        """Mutant control: without the false-approval rule, the lenient reviewer would be trusted."""
        with mock.patch.object(calibration, "REJECT", "a decision nobody gives"):
            report, _result, _harness = _calibration_run({"lenient": _approves_everything}, ("zhipu",))
        self.assertEqual(report["installations"]["lenient"]["status"], "qualified")

    def test_an_excluded_reviewer_is_never_asked_about_a_real_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = panel_check.Harness(directory, {"lenient": panel_check.approving, "a": panel_check.approving,
                                                      "b": panel_check.approving, "c": panel_check.approving},
                                          families=("zhipu", "deepseek", "openai", "alibaba"))
            panel = panel_module.ReviewPanel(
                harness.configuration, panel_check.CRITERIA, panel_check.INSTRUCTIONS, harness.reviewers,
                engines.build_precheck_engines(harness.configuration, only_builtin=True),
                panel_check.ReviewLedger(harness.ledger_path), sleeper=harness.sleep, clock=harness.clock)
            result = panel.run(panel_module.PanelRunRequest(
                run_id="pilot", requests=(panel_check._request(),), population=panel_check.DATA.population_bodies(),
                call_ceiling=100, token_ceiling=10_000_000, model_calls_authorized=True, fixture_run=True,
                excluded_installations={"lenient": calibration.FAILED_CALIBRATION}))
            self.assertEqual(harness.calls("lenient"), [])
            self.assertEqual(result.ineligible["lenient"], calibration.FAILED_CALIBRATION)
            self.assertEqual(result.items[0].outcome, panel_module.APPROVED)


if __name__ == "__main__":
    unittest.main()
