"""Checks for the dated panel review record and its strict reader.

The record is written beside ``reviews.json`` and never edits it. The lead
engineer merges its verdicts into the served catalogue through the carry and
manifest tools, so the reader refuses every record that could carry an
approval the panel rule does not support:

```text
Known-wrong records, each refused by the reader
├── an approved row with fewer than three approvals or three families
├── an approved row that one of the producer's family approved
├── an approved row beside a rejection
├── a row put to reviewers whose pre-checks refused or skipped a kind, a row
│   refused before review with no refusing pre-check, and an approved row
│   whose licence the policy does not accept
├── a rejection with no written reason
├── a decision by a reviewer the record does not name
├── one reviewer, or one call, deciding a row twice
├── a decision bound to other bytes than the row names, or naming no call
├── rows that do not name the selected items, an approval reference prefix of
│   another record, and a rejected row under another rule
├── an approved row with no digest, or an approval reference for another row
├── a row with no standing verdict that carries an approval reference
├── a finding under a criterion that does not apply to the row's kind of body
├── an interruption whose dispatch has a completed call
├── a reviewer named with another version than its calls answered with
├── a reviewer named with another installation, engine kind, family or model
│   than its calls were made under, and a call by a reviewer the record
│   does not name
├── a path that is absolute or leaves the repository
├── totals that disagree with the rows
├── another version, an unknown field or a missing field
└── a fixture reviewer, unless the reader was told the run was a fixture run
```

The committed pilot record is then read with the same reader, and every row is
compared with the body in the tree.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from candidate_review import panel as panel_module  # noqa: E402
from candidate_review import review_record  # noqa: E402
from candidate_review import verdicts  # noqa: E402
from candidate_review.records import CandidateReviewError  # noqa: E402

import test_candidate_review_panel as panel_check  # noqa: E402

ROOT = HERE.parent
CATALOGUE = ROOT / "examples/29_intelligence_service/starter-catalogue"
PILOT_RECORD = CATALOGUE / "reviews-panel-2026-09-22.json"


def _fixture_record(scripts: dict, families: tuple, identities=(panel_check.FIRST,)):
    with tempfile.TemporaryDirectory() as directory:
        harness = panel_check.Harness(directory, scripts, families=families)
        result = harness.run([panel_check._request(identity) for identity in identities])
        ledger = panel_check.ReviewLedger(harness.ledger_path)
        return review_record.build_panel_review_record(
            result, ledger, catalogue=panel_check.DATA, configuration=harness.configuration,
            criteria=panel_check.CRITERIA, instructions=panel_check.INSTRUCTIONS, producers=panel_check.PRODUCERS,
            population=review_record.PopulationSelection(
                rule=review_record.SEEDED_HASH_ORDER, seed="fixture-seed", eligible=tuple(identities),
                selected=tuple(identities)),
            recorded_at="2026-09-22", record_path="examples/fixture/reviews-panel-fixture.json",
            fixture_run=True)


APPROVED_RECORD = _fixture_record({"a": panel_check.approving, "b": panel_check.approving,
                                   "c": panel_check.approving}, ("zhipu", "deepseek", "openai"))
REJECTED_RECORD = _fixture_record({"a": panel_check.approving, "b": panel_check.rejecting,
                                   "c": panel_check.approving}, ("zhipu", "deepseek", "openai"))


def _read(value, allow_fixture=True):
    return review_record.read_panel_review_record(value, allow_fixture=allow_fixture)


def _row(record):
    return record["rows"][0]


def _refused(test, record, code, allow_fixture=True):
    with test.assertRaises(CandidateReviewError) as caught:
        _read(record, allow_fixture)
    test.assertEqual(caught.exception.code, code, str(caught.exception))


class ReaderTest(unittest.TestCase):

    def test_the_fixture_records_read_and_record_their_outcomes(self):
        self.assertEqual(_row(_read(APPROVED_RECORD))["outcome"], panel_module.APPROVED)
        self.assertEqual(_row(_read(REJECTED_RECORD))["outcome"], panel_module.REJECTED)
        self.assertEqual(_read(APPROVED_RECORD)["totals"]["approved"], 1)

    def test_an_approval_below_the_quorum_is_refused(self):
        record = copy.deepcopy(APPROVED_RECORD)
        _row(record)["decisions"] = _row(record)["decisions"][:2]
        _refused(self, record, "approval_below_quorum")

    def test_an_approval_by_the_producer_family_is_refused(self):
        """The reviewer and its calls both name the producer's family, so the family rule itself refuses it."""
        record = copy.deepcopy(APPROVED_RECORD)
        producer_family = record["producers"]["default_producer"]["family"]
        record["reviewers"][0]["family"] = producer_family
        for call in record["calls"]:
            if call["installation_id"] == record["reviewers"][0]["reviewer_id"]:
                call["family"] = producer_family
        _refused(self, record, "producer_family_approved")

    def test_an_approval_beside_a_rejection_is_refused(self):
        record = copy.deepcopy(REJECTED_RECORD)
        _row(record)["outcome"] = panel_module.APPROVED
        _row(record)["approval_state"] = review_record.REVIEWED_STATE
        _row(record)["rule_applied"] = panel_module.FAMILY_QUORUM_RULE
        _row(record)["approval_ref"] = record["approval_ref_prefix"] + _row(record)["identity"]
        _refused(self, record, "approval_beside_rejection")

    def test_a_rejection_without_a_reason_is_refused(self):
        record = copy.deepcopy(REJECTED_RECORD)
        for decision in _row(record)["decisions"]:
            if decision["decision"] == verdicts.REJECT:
                decision["reason"] = " "
        _refused(self, record, "rejection_without_reason")

    def test_a_decision_by_an_unnamed_reviewer_is_refused(self):
        record = copy.deepcopy(APPROVED_RECORD)
        _row(record)["decisions"][0]["reviewer_id"] = "someone_else"
        _refused(self, record, "unknown_reviewer")

    def test_a_decision_bound_to_other_bytes_is_refused(self):
        record = copy.deepcopy(APPROVED_RECORD)
        _row(record)["decisions"][0]["body_sha256"] = "e" * 64
        _refused(self, record, "decision_bound_to_other_bytes")

    def test_a_finding_under_a_criterion_of_the_other_kind_is_refused(self):
        """A general practice body is never judged by the criterion for bodies that restate their source."""
        record = copy.deepcopy(REJECTED_RECORD)
        self.assertNotIn("restated_source_grounding", _row(record)["criteria_applied"])
        rejection = next(decision for decision in _row(record)["decisions"] if decision["decision"] == verdicts.REJECT)
        rejection["findings"][0]["criterion_id"] = "restated_source_grounding"
        _refused(self, record, "finding_outside_the_criteria_applied")

    def test_every_row_names_its_kind_and_the_criteria_applied(self):
        row = _row(_read(APPROVED_RECORD))
        self.assertEqual(row["grounding"], "general_practice_beside_cited_source")
        self.assertIn("general_practice_grounding", row["criteria_applied"])

    def test_an_approval_without_its_digest_is_refused(self):
        record = copy.deepcopy(APPROVED_RECORD)
        _row(record)["body_sha256"] = None
        _refused(self, record, "approval_without_digest")

    def test_an_approval_reference_for_another_row_is_refused(self):
        record = copy.deepcopy(APPROVED_RECORD)
        _row(record)["approval_ref"] = record["approval_ref_prefix"] + "another_item"
        _refused(self, record, "approval_ref_inconsistent")

    def test_a_row_without_a_verdict_cannot_carry_an_approval_reference(self):
        record = copy.deepcopy(APPROVED_RECORD)
        _row(record)["outcome"] = panel_module.PANEL_INCOMPLETE
        _row(record)["approval_state"] = review_record.NO_STATE
        _refused(self, record, "approval_ref_inconsistent")

    def test_totals_that_disagree_with_the_rows_are_refused(self):
        record = copy.deepcopy(APPROVED_RECORD)
        record["totals"]["approved"] = 2
        _refused(self, record, "totals_inconsistent")

    def test_another_version_or_an_unknown_or_missing_field_is_refused(self):
        record = copy.deepcopy(APPROVED_RECORD)
        record["record_type"] = "starter_catalogue_panel_review/v2"
        _refused(self, record, "unsupported_record_version")
        record = copy.deepcopy(APPROVED_RECORD)
        record["served"] = True
        _refused(self, record, "unknown_record_fields")
        record = copy.deepcopy(APPROVED_RECORD)
        del _row(record)["rule_applied"]
        _refused(self, record, "missing_record_fields")

    def test_a_fixture_reviewer_is_refused_outside_a_fixture_run(self):
        _refused(self, copy.deepcopy(APPROVED_RECORD), "fixture_reviewer_in_record", allow_fixture=False)

    def test_the_approval_rule_is_what_refuses_a_small_quorum(self):
        """Mutant control: with the rule check replaced by one that always holds, the known-wrong row reads."""
        record = copy.deepcopy(APPROVED_RECORD)
        _row(record)["decisions"] = _row(record)["decisions"][:2]
        with mock.patch.object(review_record, "approval_rule_holds", lambda *arguments: True):
            _read(record)


def _record_with_an_interrupted_dispatch():
    """A fixture run in which one earlier dispatch to reviewer "a" never received its call row."""
    with tempfile.TemporaryDirectory() as directory:
        harness = panel_check.Harness(directory, {"a": panel_check.approving, "b": panel_check.approving,
                                                  "c": panel_check.approving, "d": panel_check.approving},
                                      families=("zhipu", "deepseek", "openai", "alibaba"))
        request = panel_check._request()
        installation = harness.configuration.installation("a")
        prompt = panel_check.build_prompt(request, installation, panel_check.INSTRUCTIONS)
        panel_check.ReviewLedger(harness.ledger_path).dispatch({
            "record_type": panel_module.DISPATCH_RECORD, "run_id": "run-0", "sequence": 1,
            "review_key": panel_module.review_key(installation, request, prompt), "installation_id": "a",
            "identity": request.identity, "body_sha256": request.body_sha256,
            "request_sha256": request.request_sha256, "dispatched_at": "2026-09-22T00:00:00Z"})
        result = harness.run([request])
        ledger = panel_check.ReviewLedger(harness.ledger_path)
        return review_record.build_panel_review_record(
            result, ledger, catalogue=panel_check.DATA, configuration=harness.configuration,
            criteria=panel_check.CRITERIA, instructions=panel_check.INSTRUCTIONS, producers=panel_check.PRODUCERS,
            population=review_record.PopulationSelection(
                rule=review_record.EXPLICIT_LIST, seed="", eligible=(request.identity,),
                selected=(request.identity,)),
            recorded_at="2026-09-22", record_path="examples/fixture/reviews-panel-fixture.json",
            fixture_run=True)


class RecordPathsAndVersionsTest(unittest.TestCase):
    """A committed record names repository paths, and each reviewer's version is the one its calls answered with."""

    def test_every_path_in_the_record_is_relative_to_the_repository(self):
        record = _read(APPROVED_RECORD)
        self.assertEqual(record["instructions"]["path"], "tools/candidate_review/resources/REVIEWER-INSTRUCTIONS.md")
        for path in (record["instructions"]["path"], record["criteria"]["source_path"], record["record_path"],
                     record["catalogue_folder"], record["producers"]["evidence"]["path"],
                     *(row["body_path"] for row in record["rows"])):
            with self.subTest(path=path):
                self.assertFalse(path.startswith("/"))
                self.assertNotIn("..", Path(path).parts)

    def test_an_absolute_path_in_the_record_is_refused(self):
        record = copy.deepcopy(APPROVED_RECORD)
        record["instructions"]["path"] = str(HERE / "candidate_review" / "resources" / "REVIEWER-INSTRUCTIONS.md")
        _refused(self, record, "record_path_not_relative")

    def test_a_reviewer_version_that_its_calls_do_not_name_is_refused(self):
        record = copy.deepcopy(APPROVED_RECORD)
        record["reviewers"][0]["model_version"] = {"digest": "another-version"}
        _refused(self, record, "reviewer_version_disagrees_with_calls")

    def test_a_reviewer_whose_calls_name_two_versions_is_not_one_reviewer(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = panel_check.Harness(directory, {"a": panel_check.approving, "b": panel_check.approving,
                                                      "c": panel_check.approving}, families=("zhipu", "deepseek", "openai"))
            result = harness.run([panel_check._request()])
            ledger = panel_check.ReviewLedger(harness.ledger_path)
            calls = ledger.calls()
            changed = dict(calls[0], model_version={"digest": "another-version"})
            with mock.patch.object(panel_check.ReviewLedger, "calls", lambda self: [changed] + calls):
                with self.assertRaises(CandidateReviewError) as caught:
                    review_record.build_panel_review_record(
                        result, ledger, catalogue=panel_check.DATA, configuration=harness.configuration,
                        criteria=panel_check.CRITERIA, instructions=panel_check.INSTRUCTIONS,
                        producers=panel_check.PRODUCERS, population=review_record.PopulationSelection(
                            rule=review_record.EXPLICIT_LIST, seed="", eligible=(panel_check.FIRST,),
                            selected=(panel_check.FIRST,)),
                        recorded_at="2026-09-22", record_path="examples/fixture/reviews-panel-fixture.json",
                        fixture_run=True)
        self.assertEqual(caught.exception.code, "reviewer_version_changed_during_review")

    def test_review_time_counts_only_the_runs_that_made_calls(self):
        """A later command that only reuses stored verdicts adds no review time to the throughput."""
        calls = [{"run_id": "review", "outcome": "verdict", "physical_model_calls": 1, "charged_tokens": 10,
                  "pause_seconds_after": 0.0, "usage": {"input_tokens": 5, "output_tokens": 5}}]
        runs = [{"record_type": review_record.RUN_END_RECORD, "run_id": "review", "elapsed_seconds": 360.0},
                {"record_type": review_record.RUN_END_RECORD, "run_id": "rewrite", "elapsed_seconds": 90.0}]
        rows = [{"outcome": panel_module.REJECTED, "decisions": [{"decision": verdicts.REJECT}]}]
        totals = review_record._totals(rows, calls, runs, [])
        self.assertEqual(totals["run_seconds"], 360.0)
        self.assertEqual(totals["items_with_a_standing_verdict_per_hour"], 10.0)


class ReviewerIdentityTest(unittest.TestCase):
    """The family that decides the quorum is the family of the calls that gave the decisions.

    A reviewer row names an installation, its engine kind, family and model. Each
    call row names the same four facts as they were when the call was made. When
    the two disagree, the record could count three families while its calls show
    one, or show the producer's family under another name."""

    def test_calls_of_one_family_under_reviewers_of_three_families_are_refused(self):
        record = copy.deepcopy(APPROVED_RECORD)
        for call in record["calls"]:
            call["family"] = "zhipu"
        _refused(self, record, "reviewer_identity_disagrees_with_calls")

    def test_a_call_of_the_producer_family_under_a_reviewer_of_another_family_is_refused(self):
        record = copy.deepcopy(APPROVED_RECORD)
        reviewer = record["reviewers"][0]["reviewer_id"]
        for call in record["calls"]:
            if call["installation_id"] == reviewer:
                call["family"] = record["producers"]["default_producer"]["family"]
        _refused(self, record, "reviewer_identity_disagrees_with_calls")

    def test_calls_under_another_model_or_installation_are_refused(self):
        for field, value in (("model", "another-model"), ("installation_sha256", "f" * 64),
                             ("engine_kind", "command_line")):
            with self.subTest(field=field):
                record = copy.deepcopy(APPROVED_RECORD)
                reviewer = record["reviewers"][0]["reviewer_id"]
                for call in record["calls"]:
                    if call["installation_id"] == reviewer:
                        call[field] = value
                _refused(self, record, "reviewer_identity_disagrees_with_calls")

    def test_a_call_by_an_installation_the_record_does_not_name_is_refused(self):
        record = copy.deepcopy(APPROVED_RECORD)
        record["calls"].append(dict(record["calls"][0], installation_id="unnamed", run_id="run-9"))
        _refused(self, record, "call_without_reviewer")

    def test_one_reviewer_counted_twice_toward_a_quorum_is_refused(self):
        """Known-wrong case: under a policy of four approvals from three families, three reviewers with one
        of them listed twice would read as four approvals."""
        record = copy.deepcopy(APPROVED_RECORD)
        record["policy"].update(minimum_approvals=4, reviewers_per_item=4)
        _row(record)["decisions"].append(copy.deepcopy(_row(record)["decisions"][0]))
        _refused(self, record, "reviewer_decided_twice")

    def test_the_identity_comparison_is_what_refuses_calls_of_one_family(self):
        """Mutant control: with the comparison removed, three families are counted from one family's calls."""
        record = copy.deepcopy(APPROVED_RECORD)
        for call in record["calls"]:
            call["family"] = "zhipu"
        with mock.patch.object(review_record, "_identity", lambda row: ()):
            self.assertEqual(_row(_read(record))["outcome"], panel_module.APPROVED)

    def test_calls_made_under_another_installation_are_not_written_under_the_one_declared_now(self):
        """The builder refuses a reviewer whose calls were made under another installation digest,
        family or model than the configuration declares, as it refuses two model versions."""
        with tempfile.TemporaryDirectory() as directory:
            harness = panel_check.Harness(directory, {"a": panel_check.approving, "b": panel_check.approving,
                                                      "c": panel_check.approving}, families=("zhipu", "deepseek", "openai"))
            result = harness.run([panel_check._request()])
            ledger = panel_check.ReviewLedger(harness.ledger_path)
            calls = ledger.calls()
            earlier = dict(calls[0], family="alibaba", installation_sha256="e" * 64, run_id="run-0")
            with mock.patch.object(panel_check.ReviewLedger, "calls", lambda self: [earlier] + calls):
                with self.assertRaises(CandidateReviewError) as caught:
                    review_record.build_panel_review_record(
                        result, ledger, catalogue=panel_check.DATA, configuration=harness.configuration,
                        criteria=panel_check.CRITERIA, instructions=panel_check.INSTRUCTIONS,
                        producers=panel_check.PRODUCERS, population=review_record.PopulationSelection(
                            rule=review_record.EXPLICIT_LIST, seed="", eligible=(panel_check.FIRST,),
                            selected=(panel_check.FIRST,)),
                        recorded_at="2026-09-22", record_path="examples/fixture/reviews-panel-fixture.json",
                        fixture_run=True)
        self.assertEqual(caught.exception.code, "reviewer_installation_changed_during_review")


def _with_a_refused_licence_precheck(record):
    prechecks = _row(record)["prechecks"]
    prechecks["refused"], prechecks["reasons"] = True, ["licence:licence_not_accepted"]
    licence = next(result for result in prechecks["results"] if result["kind"] == "licence")
    licence["status"], licence["findings"] = "refused", [{"code": "licence_not_accepted", "detail": "GPL-3.0-only"}]
    return record


class PrecheckAndLicenceTest(unittest.TestCase):
    """A row put to reviewers passed every pre-check kind, and an approved row carries an accepted licence.

    The decision rule says the deterministic pre-checks refuse before any reviewer
    is asked, so a row with decisions whose pre-checks refused, or skipped a kind,
    is not a row the panel wrote, and an approval of a licence the policy does not
    accept would let material without a permissive licence into the merge."""

    def test_an_approval_whose_licence_pre_check_refused_is_refused(self):
        _refused(self, _with_a_refused_licence_precheck(copy.deepcopy(APPROVED_RECORD)), "precheck_inconsistent")

    def test_an_approval_without_one_pre_check_kind_is_refused(self):
        for results in ("without the secrets kind", "with no result"):
            with self.subTest(results=results):
                record = copy.deepcopy(APPROVED_RECORD)
                prechecks = _row(record)["prechecks"]
                prechecks["results"] = ([result for result in prechecks["results"] if result["kind"] != "secrets"]
                                        if results == "without the secrets kind" else [])
                _refused(self, record, "precheck_inconsistent")

    def test_pre_check_results_of_another_shape_are_refused(self):
        record = copy.deepcopy(APPROVED_RECORD)
        _row(record)["prechecks"] = {"anything": 1}
        _refused(self, record, "unknown_record_fields")
        record = copy.deepcopy(APPROVED_RECORD)
        _row(record)["prechecks"]["results"][0]["record_type"] = "candidate_precheck_result/v2"
        _refused(self, record, "unsupported_record_version")

    def test_a_refused_flag_that_disagrees_with_the_results_is_refused(self):
        record = copy.deepcopy(APPROVED_RECORD)
        _row(record)["prechecks"]["refused"] = True
        _refused(self, record, "precheck_inconsistent")

    def test_an_approval_of_a_licence_the_policy_does_not_accept_is_refused(self):
        record = copy.deepcopy(APPROVED_RECORD)
        _row(record)["declared_license"] = "GPL-3.0-only"
        _refused(self, record, "approval_licence_not_accepted")

    def test_a_row_refused_before_review_names_a_refusing_pre_check(self):
        refused = _fixture_record({"a": panel_check.approving, "b": panel_check.approving,
                                   "c": panel_check.approving}, ("zhipu", "deepseek", "openai"),
                                  identities=(panel_check.LICENCE_UNKNOWN,))
        self.assertEqual(_row(_read(refused))["outcome"], panel_module.REFUSED_BEFORE_REVIEW)
        record = copy.deepcopy(refused)
        prechecks = _row(record)["prechecks"]
        prechecks["refused"], prechecks["reasons"] = False, []
        for result in prechecks["results"]:
            result["status"], result["findings"] = "passed", []
        _refused(self, record, "precheck_inconsistent")

    def test_the_pre_check_reading_is_what_refuses_a_refused_approval(self):
        """Mutant control: with the pre-check reading removed, the approval beside a refusal reads."""
        record = _with_a_refused_licence_precheck(copy.deepcopy(APPROVED_RECORD))
        with mock.patch.object(review_record, "_read_prechecks", lambda *arguments: None):
            self.assertEqual(_row(_read(record))["outcome"], panel_module.APPROVED)


class RemainingRefusalTest(unittest.TestCase):
    """Refusals of the reader that no other check held: each record here reads when its guard is removed."""

    def test_a_fixture_run_record_is_refused_even_without_a_fixture_reviewer(self):
        record = copy.deepcopy(APPROVED_RECORD)
        for row in record["reviewers"] + record["calls"]:
            row["engine_kind"] = "model_gateway"
        _refused(self, record, "fixture_reviewer_in_record", allow_fixture=False)

    def test_a_fixture_reviewer_is_refused_in_a_record_that_calls_itself_real(self):
        record = copy.deepcopy(APPROVED_RECORD)
        record["fixture_run"] = False
        _refused(self, record, "fixture_reviewer_in_record", allow_fixture=False)

    def test_rows_that_do_not_name_the_selected_items_are_refused(self):
        record = copy.deepcopy(APPROVED_RECORD)
        record["population"]["selected"] = ["another_item"]
        _refused(self, record, "rows_do_not_cover_population")

    def test_an_approval_reference_prefix_of_another_record_is_refused(self):
        record = copy.deepcopy(APPROVED_RECORD)
        record["approval_ref_prefix"] = "examples/fixture/another-record.json#"
        _row(record)["approval_ref"] = record["approval_ref_prefix"] + _row(record)["identity"]
        _refused(self, record, "approval_ref_inconsistent")

    def test_a_decision_that_names_no_call_is_refused(self):
        record = copy.deepcopy(APPROVED_RECORD)
        _row(record)["decisions"][0]["call_ref"] = "run-1#999"
        _refused(self, record, "decision_without_call")

    def test_a_rejected_row_under_another_rule_is_refused(self):
        record = copy.deepcopy(REJECTED_RECORD)
        _row(record)["rule_applied"] = panel_module.FAMILY_QUORUM_RULE
        _refused(self, record, "rejection_inconsistent")


class InterruptedDispatchTest(unittest.TestCase):
    """A call that was dispatched and never completed is part of the record, with its outcome unknown."""

    def test_an_interrupted_dispatch_is_recorded_and_counted(self):
        record = _read(_record_with_an_interrupted_dispatch())
        self.assertEqual([(row["run_id"], row["sequence"], row["installation_id"])
                          for row in record["interrupted_dispatches"]], [("run-0", 1, "a")])
        self.assertEqual(record["totals"]["interrupted_dispatches"], 1)
        self.assertEqual(_row(record)["outcome"], panel_module.APPROVED)
        self.assertNotIn("a", [decision["reviewer_id"] for decision in _row(record)["decisions"]])

    def test_a_dispatch_that_has_a_call_is_not_an_interruption(self):
        record = copy.deepcopy(_record_with_an_interrupted_dispatch())
        call = record["calls"][0]
        record["interrupted_dispatches"].append({
            "record_type": panel_module.DISPATCH_RECORD, "run_id": call["run_id"], "sequence": call["sequence"],
            "review_key": call["review_key"], "installation_id": call["installation_id"],
            "identity": call["identity"], "body_sha256": call["body_sha256"],
            "request_sha256": call["request_sha256"], "dispatched_at": call["started_at"]})
        record["totals"]["interrupted_dispatches"] = 2
        _refused(self, record, "dispatch_not_interrupted")

    def test_an_interruption_the_totals_do_not_count_is_refused(self):
        record = copy.deepcopy(_record_with_an_interrupted_dispatch())
        record["totals"]["interrupted_dispatches"] = 0
        _refused(self, record, "totals_inconsistent")


class SerializationTest(unittest.TestCase):
    """Reviewer text is evidence and is kept exactly; only its serialization avoids retired words and dashes."""

    #: Retired words are assembled here from their parts, so this file holds none of them.
    TEXT = ("Keep the payment " + "Rec" + "eipt. A " + "chron" + "icle of each retry " + chr(0x2014) + " and "
            + " ".join(("what", "is", "next")) + ", " + "What" + "'s next, a " + "chi" + "ld process and a "
            + "stop" + "_condition field.")

    def _record_with_text(self):
        record = copy.deepcopy(REJECTED_RECORD)
        for decision in _row(record)["decisions"]:
            decision["reason"] = self.TEXT
        return record

    def test_the_serialized_record_decodes_to_the_same_record(self):
        record = self._record_with_text()
        payload = review_record.serialized(record)
        self.assertEqual(json.loads(payload.decode("ascii")), record)

    def test_the_serialized_bytes_hold_no_retired_term_and_no_dash(self):
        payload = review_record.serialized(self._record_with_text()).decode("ascii").casefold()
        for term in review_record.retired_terms():
            self.assertNotIn(term.casefold(), payload)
        self.assertNotIn(chr(0x2014), payload)

    def test_the_escaping_is_what_keeps_the_terms_out(self):
        """Mutant control: with no term escaped, the retired word reaches the bytes."""
        with mock.patch.object(review_record, "retired_terms", lambda: ()):
            payload = review_record.serialized(self._record_with_text()).decode("ascii").casefold()
        self.assertIn("receipt", payload)


class CommittedPilotRecordTest(unittest.TestCase):
    """The committed pilot record reads with the strict reader and matches the bodies in the tree."""

    @classmethod
    def setUpClass(cls):
        cls.record = review_record.read_panel_review_record(json.loads(PILOT_RECORD.read_text(encoding="utf-8")))

    def test_the_committed_bytes_are_the_serialized_record(self):
        """The file is ASCII, holds no retired term, and is exactly what the serializer writes."""
        payload = PILOT_RECORD.read_bytes()
        self.assertEqual(payload, review_record.serialized(self.record))
        text = payload.decode("ascii").casefold()
        for term in review_record.retired_terms():
            self.assertNotIn(term.casefold(), text)

    def test_no_fixture_reviewer_decided_anything(self):
        kinds = {reviewer["engine_kind"] for reviewer in self.record["reviewers"]}
        self.assertNotIn("fixture", kinds)

    def test_every_judged_row_names_the_body_in_the_tree(self):
        for row in self.record["rows"]:
            if row["body_sha256"] is None:
                continue
            with self.subTest(identity=row["identity"]):
                body = (CATALOGUE / row["body_path"]).read_bytes()
                self.assertEqual(hashlib.sha256(body).hexdigest(), row["body_sha256"])

    def test_every_approval_meets_the_rule_without_the_producer_family(self):
        family = {reviewer["reviewer_id"]: reviewer["family"] for reviewer in self.record["reviewers"]}
        producer_family = self.record["producers"]["default_producer"]["family"]
        for row in self.record["rows"]:
            if row["outcome"] != panel_module.APPROVED:
                continue
            with self.subTest(identity=row["identity"]):
                approvers = [decision["reviewer_id"] for decision in row["decisions"]
                             if decision["decision"] == verdicts.APPROVE]
                self.assertGreaterEqual(len(approvers), 3)
                self.assertGreaterEqual(len({family[reviewer] for reviewer in approvers}), 3)
                self.assertNotIn(producer_family, {family[reviewer] for reviewer in approvers})
                self.assertFalse([decision for decision in row["decisions"]
                                  if decision["decision"] == verdicts.REJECT])

    def test_the_selection_rule_reproduces_the_selected_items(self):
        population = self.record["population"]
        again = review_record.select_population(population["eligible"], count=len(population["selected"]),
                                                seed=population["seed"])
        self.assertEqual(list(again), population["selected"])

    def test_every_call_names_a_reviewer_and_keeps_unknown_usage_unknown(self):
        reviewers_named = {reviewer["reviewer_id"] for reviewer in self.record["reviewers"]}
        reviewers_named |= {row["installation_id"] for row in self.record["ineligible_reviewers"]}
        for call in self.record["calls"]:
            with self.subTest(call=call["sequence"]):
                self.assertIn(call["installation_id"], reviewers_named)
                for name in ("input_tokens", "output_tokens"):
                    value = call["usage"][name]
                    self.assertTrue(value is None or (type(value) is int and value >= 0))
                if call["usage"]["source"] == "unknown":
                    self.assertIsNone(call["usage"]["input_tokens"])

    def test_the_record_approves_nothing_it_did_not_review(self):
        for row in self.record["rows"]:
            with self.subTest(identity=row["identity"]):
                if row["outcome"] == panel_module.APPROVED:
                    self.assertEqual(row["approval_state"], review_record.REVIEWED_STATE)
                else:
                    self.assertEqual(row["approval_ref"], "")


if __name__ == "__main__":
    unittest.main()
