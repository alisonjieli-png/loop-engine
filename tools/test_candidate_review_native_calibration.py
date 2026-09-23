"""Native calibration uses exact complete packages and hides decision labels from reviewers."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "src")]

from candidate_review import (
    calibration,
    native_calibration,
    native_profile,
    panel,
    prechecks,
    review_record,
)
from candidate_review.ledger import ReviewLedger
from candidate_review.prompt import build_prompt
from candidate_review.records import VERDICT_RECORD, CandidateReviewError, digest
from candidate_review.reviewers.fixture import FixtureReviewer
from test_candidate_review_panel import (
    BASE,
    _bound_fixture_script,
    _configuration,
    _installation,
    answer,
    attempt,
)

ROOT = HERE.parent
MANIFEST = HERE / "candidate_review/resources/native-calibration/calibration-set.json"


def loaded():
    criteria, instructions = native_profile.resources()
    chosen = native_calibration.NativeCalibrationSet.load(MANIFEST, ROOT, criteria)
    pairs = chosen.requests(None, None, criteria, instructions.sha256)
    return chosen, pairs, criteria, instructions


def run_fixture(callback, *, reviewer_name="reviewer"):
    chosen, pairs, criteria, instructions = loaded()
    configuration = native_profile.configuration(_configuration([_installation(reviewer_name, "zhipu")]))
    installation = configuration.installations[0]
    with tempfile.TemporaryDirectory() as directory:
        ledger = ReviewLedger(Path(directory) / "ledger.jsonl")
        reviewers = {installation.installation_id: FixtureReviewer(installation, _bound_fixture_script(callback, installation.model))}
        instance = panel.ReviewPanel(configuration, criteria, instructions, reviewers, native_profile.engines(configuration), ledger)
        result = instance.run(panel.PanelRunRequest("native-calibration-test", tuple(request for _, request in pairs),
            chosen.population({}), 5, 1000000, True, fixture_run=True, ask_every_eligible_reviewer=True))
    return calibration.evaluate(chosen, result), result


def decision(prompt, selected, *, usage=(1000, 100)):
    finding = {"criterion_id": "whole_package", "blocking": selected == "reject", "text": "Synthetic calibration decision."}
    return attempt(answer(prompt, selected, findings=[finding]), usage=usage)


def export_evidence(report, result):
    """Complete fixture evidence in the shape the production ledger exporter writes."""
    calls = {(row["run_id"], row["sequence"]): row for row in result.calls}
    verdicts = []
    for item in result.items:
        for row in item.verdicts:
            call = calls[(row["run_id"], row["sequence"])]
            fields = ("run_id", "sequence", "review_key", "installation_id", "family", "identity",
                "body_sha256", "request_sha256", "decision", "reported_model", "request_record_type")
            verdicts.append({"record_type": VERDICT_RECORD, **{name: call[name] for name in fields},
                             "findings": row["findings"], "reasons": row["reasons"]})
    return {**report, "calls": result.calls, "verdicts": verdicts, "interrupted_dispatches": []}


def calibrated_native_record(*, bypass_failed_reviewer=False):
    from test_candidate_review_native import IDENTITY, fixture, load_request
    chosen, pairs, criteria, instructions = loaded()
    labels = {item.identity: item.expected_decision for item in chosen.items}
    configuration = native_profile.configuration(_configuration([
        _installation(name, family) for name, family in (
            ("a-openai", "openai"), ("b-zhipu", "zhipu"), ("c-alibaba", "alibaba"), ("d-minimax", "minimax"))]))
    reviewers = {}
    for item in configuration.installations:
        def scripted(prompt, number, name=item.installation_id):
            selected = "approve" if bypass_failed_reviewer and name == "b-zhipu" else labels.get(prompt.identity, "approve")
            return decision(prompt, selected)
        reviewers[item.installation_id] = FixtureReviewer(item, _bound_fixture_script(scripted, item.model))
    with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as directory:
        ledger = ReviewLedger(Path(directory) / "ledger.jsonl")
        worker = panel.ReviewPanel(configuration, criteria, instructions, reviewers,
                                  native_profile.engines(configuration), ledger)
        measured = worker.run(panel.PanelRunRequest("calibration", tuple(request for _, request in pairs),
            {}, 20, 3000000, True, fixture_run=True, ask_every_eligible_reviewer=True))
        report = calibration.evaluate(chosen, measured)
        fixture(Path(directory) / "candidate")
        catalogue, request, _ = load_request(Path(directory) / "candidate")
        excluded = dict(report["excluded"])
        if bypass_failed_reviewer:
            excluded.pop("b-zhipu")  # Deliberate fixture defect, never production behavior.
        candidate = worker.run(panel.PanelRunRequest("candidate", (request,), catalogue.population_bodies(),
            4, 1000000, True, fixture_run=True, excluded_installations=excluded))
        record = review_record.build_panel_review_record(candidate, ledger, catalogue=catalogue,
            configuration=configuration, criteria=criteria, instructions=instructions,
            producers=catalogue.producer_declaration(configuration.families),
            population=review_record.PopulationSelection(review_record.EXPLICIT_LIST, "", (IDENTITY,), (IDENTITY,)),
            recorded_at="2026-09-23", record_path="artifacts/native-calibrated-fixture.json", fixture_run=True,
            calibration_report=report, calibration_requests=tuple(request.request_sha256 for _, request in pairs))
        if bypass_failed_reviewer:
            record["ineligible_reviewers"].append({"installation_id": "b-zhipu", "reason": calibration.FAILED_CALIBRATION,
                "family": "zhipu", "model": "fixture-b-zhipu", "disabled_reason": ""})
    return record


class NativeCalibrationTest(unittest.TestCase):
    def test_recomputed_review_key_cannot_hide_a_changed_calibration_prompt(self):
        record = calibrated_native_record()
        call = record["calibration"]["calls"][0]
        call["prompt_sha256"] = "0" * 64
        call["review_key"] = digest({"installation_sha256": call["installation_sha256"],
            "request_sha256": call["request_sha256"], "prompt_sha256": call["prompt_sha256"],
            "record_type": VERDICT_RECORD, "request_record_type": call["request_record_type"]})
        verdict = next(row for row in record["calibration"]["verdicts"]
                       if (row["run_id"], row["sequence"]) == (call["run_id"], call["sequence"]))
        verdict["review_key"] = call["review_key"]
        with self.assertRaises(CandidateReviewError) as caught:
            review_record.read_panel_review_record(record, allow_fixture=True)
        self.assertEqual(caught.exception.code, "calibration_prompt_mismatch")

    def test_complete_native_export_cannot_hide_a_failed_reviewer_by_deleting_both_lists(self):
        record = calibrated_native_record(bypass_failed_reviewer=True)
        self.assertEqual(len(record["calibration"]["installations"]["b-zhipu"]["false_approvals"]), 4)
        self.assertTrue(any(row["reviewer_id"] == "b-zhipu" for row in record["rows"][0]["decisions"]))
        with self.assertRaises(CandidateReviewError):
            review_record.read_panel_review_record(record, allow_fixture=True)
        record["calibration"]["excluded"].pop("b-zhipu")
        record["ineligible_reviewers"] = [row for row in record["ineligible_reviewers"]
                                           if row["installation_id"] != "b-zhipu"]
        with self.assertRaises(CandidateReviewError) as caught:
            review_record.read_panel_review_record(record, allow_fixture=True)
        self.assertEqual(caught.exception.code, "calibration_inconsistent")

    def test_two_phase_export_excludes_unmeasured_producer_family_and_roundtrips(self):
        record = calibrated_native_record()
        checked = review_record.read_panel_review_record(record, allow_fixture=True)
        self.assertEqual(checked["rows"][0]["outcome"], panel.APPROVED)
        self.assertEqual(checked["calibration"]["excluded"], {"a-openai": calibration.CALIBRATION_INCOMPLETE})
        self.assertFalse(any(row["installation_id"] == "a-openai"
                             for row in checked["calls"] + checked["calibration"]["calls"]))
        for change in ("removed_exclusions", "candidate_version", "old_export", "old_calibration", "omitted_installation"):
            wrong = copy.deepcopy(record)
            if change == "removed_exclusions":
                wrong["calibration"]["excluded"] = {}; wrong["ineligible_reviewers"] = []
            elif change == "candidate_version": wrong["reviewers"][0]["engine_version"] = "changed-version"
            elif change == "old_export": wrong["record_type"] = "starter_catalogue_panel_review/v2"
            elif change == "old_calibration": wrong["calibration"]["record_type"] = "candidate_review_calibration_result/v1"
            else: wrong["calibration"]["installations"].pop("b-zhipu")
            with self.subTest(change=change), self.assertRaises(CandidateReviewError):
                review_record.read_panel_review_record(wrong, allow_fixture=True)

    def test_export_rederives_failed_status_when_both_exclusion_lists_are_deleted(self):
        report, result = run_fixture(lambda prompt, number: decision(prompt, "approve"))
        saved = export_evidence(report, result)
        saved["excluded"] = {}
        with self.assertRaises(CandidateReviewError):
            review_record._read_calibration(saved, [])

    def test_export_refuses_control_labels_calls_and_summary_tampering(self):
        chosen, _pairs, _criteria, _instructions = loaded()
        labels = {item.identity: item.expected_decision for item in chosen.items}
        report, result = run_fixture(lambda prompt, number: decision(prompt, labels[prompt.identity]))
        saved = export_evidence(report, result)
        review_record._read_calibration(saved, [])
        for kind in ("set_digest", "label", "missing_call", "duplicate_call", "decision",
                     "invalid_answer", "missing_installation", "unknown_installation", "missing_verdict",
                     "duplicate_verdict", "unknown_criterion", "no_blocking_finding", "wrong_request",
                     "extra_control", "duplicate_control", "no_reported_model"):
            changed = copy.deepcopy(saved)
            if kind == "set_digest": changed["set_sha256"] = "0" * 64
            elif kind == "label":
                changed["items"][0]["expected_decision"] = (
                    "reject" if changed["items"][0]["expected_decision"] == "approve" else "approve")
            elif kind == "missing_call": changed["calls"].pop()
            elif kind == "duplicate_call": changed["calls"].append(copy.deepcopy(changed["calls"][0]))
            elif kind == "decision": changed["calls"][0]["decision"] = "invented"
            elif kind == "invalid_answer": changed["calls"][0]["outcome"] = "invalid_response"
            elif kind == "missing_installation": changed["installations"] = {}
            elif kind == "unknown_installation":
                changed["installations"]["never-measured"] = copy.deepcopy(changed["installations"]["reviewer"])
            elif kind == "missing_verdict": changed["verdicts"].pop()
            elif kind == "duplicate_verdict": changed["verdicts"].append(copy.deepcopy(changed["verdicts"][0]))
            elif kind == "unknown_criterion": changed["verdicts"][0]["findings"][0]["criterion_id"] = "invented"
            elif kind == "no_blocking_finding":
                next(row for row in changed["verdicts"] if row["decision"] == "reject")["findings"] = []
            elif kind == "wrong_request": changed["calls"][0]["request_sha256"] = "0" * 64
            elif kind == "extra_control":
                row = copy.deepcopy(changed["items"][0]); row["identity"] = "extra-control"; changed["items"].append(row)
            elif kind == "duplicate_control": changed["items"].append(copy.deepcopy(changed["items"][0]))
            else: changed["calls"][0]["reported_model"] = ""
            with self.subTest(kind=kind), self.assertRaises(CandidateReviewError):
                review_record._read_calibration(changed, [])

    def test_unavailable_skipped_and_zero_call_installations_are_incomplete(self):
        from types import SimpleNamespace

        from candidate_review.reviewers import Availability
        chosen, _pairs, _criteria, _instructions = loaded()
        result = SimpleNamespace(run_id="no-calls", calls=[], items=[],
            availability={"unavailable": Availability(False, "offline", "", {}, "engine_unavailable"),
                          "zero-calls": Availability(True, "", "fixture", {}, "")},
            ineligible={"unavailable": "engine_unavailable", "producer": "producer_family", "disabled": "disabled"})
        report = calibration.evaluate(chosen, result)
        self.assertEqual(report["excluded"], {name: calibration.CALIBRATION_INCOMPLETE
            for name in ("unavailable", "zero-calls", "producer", "disabled")})

    def test_missing_benign_control_verdict_stays_incomplete(self):
        chosen, _pairs, _criteria, _instructions = loaded()
        labels = {item.identity: item.expected_decision for item in chosen.items}
        report, _result = run_fixture(lambda prompt, number: attempt("not a verdict")
            if labels[prompt.identity] == "approve" else decision(prompt, "reject"))
        self.assertEqual(report["excluded"], {"reviewer": calibration.CALIBRATION_INCOMPLETE})

    def test_export_refuses_changed_native_control_identity_and_unknown_item_versions(self):
        chosen, _pairs, _criteria, _instructions = loaded()
        labels = {item.identity: item.expected_decision for item in chosen.items}
        report, result = run_fixture(lambda prompt, number: decision(prompt, labels[prompt.identity]))
        good = export_evidence(report, result)
        review_record._read_calibration(good, [])
        for kind in ("digest", "version"):
            changed = copy.deepcopy(good)
            if kind == "digest": changed["calls"][0]["body_sha256"] = "0" * 64
            else: changed["items"][0]["record_type"] = "candidate_native_review_calibration_item/v999"
            with self.subTest(kind=kind), self.assertRaises(CandidateReviewError):
                review_record._read_calibration(changed, [])

    def test_export_refuses_a_candidate_decision_from_a_failed_calibration_reviewer(self):
        from test_candidate_review_record import APPROVED_RECORD
        report, result = run_fixture(lambda prompt, number: decision(prompt, "approve"), reviewer_name="a")
        record = copy.deepcopy(APPROVED_RECORD)
        record["calibration"] = export_evidence(report, result)
        record["ineligible_reviewers"].append({"installation_id": "a", "reason": calibration.FAILED_CALIBRATION,
                                              "family": "zhipu", "model": "fixture-a", "disabled_reason": ""})
        with self.assertRaises(CandidateReviewError) as caught:
            review_record.read_panel_review_record(record, allow_fixture=True)
        self.assertIn(caught.exception.code, ("excluded_calibration_reviewer_decided", "calibration_profile_mismatch"))

    def test_native_cli_uses_native_controls_without_any_unauthorized_provider_call(self):
        import review_catalogue_candidates as command
        from candidate_review.reviewers import Availability
        from test_candidate_review_native import fixture
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as directory:
            fixture(directory); root = Path(directory)
            options = command._parser().parse_args(["--content-profile", "native-original", "--calibrate",
                "--catalogue", directory, "--repository", str(ROOT), "--ledger", str(root / "ledger.jsonl"),
                "--count", "1", "--seed", "native-calibration-test", "--call-ceiling", "0", "--token-ceiling", "0",
                "--record", str(root / "record.json"), "--recorded-at", "2026-09-23"])
            engine = mock.Mock(); engine.availability.return_value = Availability(False, "offline", "", {}, "engine_unavailable")
            with mock.patch.object(command, "listed_model_versions", side_effect=AssertionError("no provider listing")), \
                    mock.patch.object(command.engines, "build_reviewer", return_value=engine):
                summary = command.run(options)
            record = json.loads((root / "record.json").read_text())
        self.assertEqual(summary["calibration"]["totals"]["items"], 5)
        self.assertEqual(len(record["calibration"]["items"]), 5)
        self.assertTrue(all(item["record_type"] == native_calibration.NATIVE_CALIBRATION_ITEM
                            for item in record["calibration"]["items"]))
        engine.review.assert_not_called()

    def test_failed_native_reviewer_is_excluded_from_the_following_real_candidate_phase(self):
        from test_candidate_review_native import fixture, load_request
        chosen, pairs, criteria, instructions = loaded()
        labels = {item.identity: item.expected_decision for item in chosen.items}
        configuration = native_profile.configuration(_configuration([
            _installation(name, family) for name, family in zip(("bad", "good1", "good2", "good3"),
                                                                ("zhipu", "deepseek", "alibaba", "minimax"))]))
        reviewers = {}
        for installation in configuration.installations:
            def scripted(prompt, number, name=installation.installation_id):
                selected = "approve" if name == "bad" else labels.get(prompt.identity, "approve")
                return decision(prompt, selected)
            reviewers[installation.installation_id] = FixtureReviewer(installation, _bound_fixture_script(scripted, installation.model))
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as directory:
            instance = panel.ReviewPanel(configuration, criteria, instructions, reviewers, native_profile.engines(configuration),
                                        ReviewLedger(Path(directory) / "ledger.jsonl"))
            calibration_result = instance.run(panel.PanelRunRequest("calibration", tuple(r for _, r in pairs), {},
                20, 3000000, True, fixture_run=True, ask_every_eligible_reviewer=True))
            evaluated = calibration.evaluate(chosen, calibration_result)
            fixture(Path(directory) / "candidate")
            catalogue, request, _instructions = load_request(Path(directory) / "candidate")
            before = len(reviewers["bad"].calls)
            result = instance.run(panel.PanelRunRequest("candidate", (request,), catalogue.population_bodies(),
                3, 1000000, True, fixture_run=True, excluded_installations=evaluated["excluded"]))
        self.assertEqual(len(reviewers["bad"].calls), before)
        self.assertEqual(result.ineligible["bad"], calibration.FAILED_CALIBRATION)
        self.assertEqual(result.items[0].outcome, panel.APPROVED)

    def test_controls_are_complete_bound_packages_and_labels_never_enter_prompts(self):
        chosen, pairs, _criteria, instructions = loaded()
        self.assertEqual(len(pairs), 5)
        self.assertEqual(sum(item.expected_decision == "approve" for item, _ in pairs), 1)
        for item, request in pairs:
            prompt = build_prompt(request, BASE.installations[0], instructions)
            self.assertEqual(request.body_sha256, chosen.package_digests[item.identity])
            self.assertNotIn(item.defect, prompt.user + prompt.system)
            self.assertNotIn('"expected_decision"', prompt.user)
            self.assertNotIn('"criterion_id": "' + item.criterion_id + '"', json.dumps(request.item))
            self.assertEqual(len(request.files), 8)

    def test_all_controls_reach_semantic_review_instead_of_static_refusal(self):
        chosen, pairs, _criteria, _instructions = loaded()
        config = native_profile.configuration(BASE)
        engines = native_profile.engines(config)
        for item, request in pairs:
            with self.subTest(item=item.identity):
                outcome = prechecks.run_prechecks(request, engines, prechecks.PrecheckContext(config.policy, chosen.population({})))
                self.assertFalse(outcome.refused, outcome.to_dict())

    def test_approving_any_known_wrong_control_excludes_the_reviewer(self):
        report, result = run_fixture(lambda prompt, number: decision(prompt, "approve"))
        status = report["installations"]["reviewer"]
        self.assertEqual(status["status"], calibration.FAILED_CALIBRATION)
        self.assertEqual(len(status["false_approvals"]), 4)
        self.assertEqual(report["excluded"], {"reviewer": calibration.FAILED_CALIBRATION})
        self.assertEqual(len(result.calls), 5)

    def test_correct_decisions_qualify_only_this_small_control_set(self):
        chosen, _pairs, _criteria, _instructions = loaded()
        labels = {item.identity: item.expected_decision for item in chosen.items}
        report, _result = run_fixture(lambda prompt, number: decision(prompt, labels[prompt.identity]))
        self.assertEqual(report["installations"]["reviewer"]["status"], "qualified")
        self.assertEqual(report["excluded"], {})
        self.assertIn("does not estimate", report["limits"])

    def test_false_refusal_invalid_answers_and_unknown_usage_stay_distinct(self):
        chosen, _pairs, _criteria, _instructions = loaded()
        good = next(item.identity for item in chosen.items if item.expected_decision == "approve")
        wrong = next(item.identity for item in chosen.items if item.expected_decision == "reject")
        def scripted(prompt, number):
            if prompt.identity == wrong:
                return attempt("not JSON", usage=None)
            return decision(prompt, "reject", usage=None)
        report, result = run_fixture(scripted)
        status = report["installations"]["reviewer"]
        self.assertEqual(status["false_refusals"], [good])
        self.assertEqual(status["known_wrong_without_a_verdict"], [wrong])
        self.assertEqual(status["false_approvals"], [])
        self.assertEqual(status["status"], calibration.CALIBRATION_INCOMPLETE)
        self.assertEqual(result.totals()["calls_with_unknown_usage"], 5)
        self.assertEqual(sum(call["outcome"] == "invalid_response" for call in result.calls), 1)

    def test_starter_calibration_record_is_not_reinterpreted_as_native(self):
        with self.assertRaises(CandidateReviewError):
            native_calibration.NativeCalibrationSet.load(HERE / "candidate_review/resources/calibration-set.json", ROOT,
                                                        native_profile.resources()[0])

    def test_control_digest_mutation_is_refused(self):
        value = json.loads(MANIFEST.read_text())
        value["items"][0]["package_digest"] = "0" * 64
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as directory:
            path = Path(directory) / "controls.json"; path.write_text(json.dumps(value))
            with self.assertRaises(CandidateReviewError):
                native_calibration.NativeCalibrationSet.load(path, ROOT, native_profile.resources()[0])

    def test_unknown_versions_and_unknown_label_fields_are_refused(self):
        for change in ("version", "field"):
            with self.subTest(change=change), tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as directory:
                value = json.loads(MANIFEST.read_text())
                if change == "version": value["record_type"] = "candidate_native_review_calibration_set/v999"
                else: value["items"][0]["approve_anyway"] = True
                path = Path(directory) / "controls.json"; path.write_text(json.dumps(value))
                with self.assertRaises(CandidateReviewError):
                    native_calibration.NativeCalibrationSet.load(path, ROOT, native_profile.resources()[0])


if __name__ == "__main__":
    unittest.main()
