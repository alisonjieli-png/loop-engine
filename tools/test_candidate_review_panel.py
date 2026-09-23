"""Checks for the review panel: the envelope that decides one candidate at a time.

The panel runs the deterministic pre-checks, chooses eligible reviewers in the
declared order, asks them within a declared budget, validates every answer
against the exact bytes it was asked about, and applies the approval rule.
Every check here uses fixture reviewers, so no model is called:

```text
What the panel must guarantee
├── Approval
│   ├── three approvals from three families, none of them the producer's, approve
│   ├── two approvals from one family never make a quorum, and no call is spent
│   │   when the eligible families cannot reach one
│   ├── the producer's family is never asked
│   └── one written rejection keeps the item a candidate, with its reasons
├── Before any call
│   ├── a pre-check refusal ends the item with no reviewer asked
│   ├── a scripted fixture reviewer is never asked outside a fixture run
│   └── no model call happens without explicit model call authority
├── Answers
│   ├── an answer about other bytes is not counted
│   ├── a rejection without a cited criterion or a written reason, an approval
│   │   with a blocking finding, or an answer with unknown keys is not counted
│   ├── an answer of any shape, such as a criterion written as a list or text
│   │   nested past the JSON reader's limit, is recorded as invalid, never raised
│   └── an answer that is not counted, or a failed call, is replaced by a
│       reviewer of a family not yet heard
├── Budget
│   ├── a call ceiling and a token ceiling stop the run before the next call
│   ├── a rate limit pauses for a bounded, recorded time and then retries
│   ├── a spent allowance stops every reviewer that shares it for the run
│   └── unknown usage stays unknown and is charged at its reservation
└── Cursor
    ├── a stopped run, run again, asks only the reviewers still missing
    ├── a ledger whose last line was not completed is refused
    ├── a finished run, run again, makes no call
    ├── a call that was dispatched and never completed is not repeated
    ├── a run identity the ledger already holds is refused, so a dispatch that
    │   never completed can never take the name of a later completed call
    └── changed bytes are a new review subject
```

Mutant controls replace one guard at a time and show that its known-wrong case
then passes, so each case is held by the guard it names.
"""
from __future__ import annotations

import copy
import dataclasses
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from candidate_review import configuration as config  # noqa: E402
from candidate_review import engines  # noqa: E402
from candidate_review import panel as panel_module  # noqa: E402
from candidate_review import reviewers  # noqa: E402
from candidate_review import verdicts  # noqa: E402
from candidate_review.catalogue import StarterCatalogue  # noqa: E402
from candidate_review.ledger import ReviewLedger  # noqa: E402
from candidate_review.prompt import build_prompt  # noqa: E402
from candidate_review.records import CandidateReviewError, digest  # noqa: E402
from candidate_review.reviewers.fixture import FixtureReviewer  # noqa: E402

ROOT = HERE.parent
CATALOGUE = ROOT / "examples/29_intelligence_service/starter-catalogue"
RESOURCES = HERE / "candidate_review" / "resources"
PANEL_RECORD = json.loads((RESOURCES / "panel.json").read_text(encoding="utf-8"))
SHEET = (CATALOGUE / "REVIEW.md").read_text(encoding="utf-8")
BASE = config.PanelConfiguration.from_dict(PANEL_RECORD)
CRITERIA = config.compile_criteria(json.loads((RESOURCES / "criteria.json").read_text()), SHEET)
PRODUCERS = config.ProducerDeclaration.from_dict(
    json.loads((RESOURCES / "producer-starter-catalogue.json").read_text()), SHEET, BASE.families)
INSTRUCTIONS = config.load_instructions(RESOURCES / "REVIEWER-INSTRUCTIONS.md")
DATA = StarterCatalogue.load(CATALOGUE, ROOT)
FIRST, SECOND = "review_shared_state_for_ordering_defects", "measure_before_optimising"
LICENCE_UNKNOWN = "check_a_table_join_before_trusting_it"
#: One fixture reviewer per family, in declared order. The producer's family comes first,
#: so a panel that forgot the exclusion would ask it before anyone else.
FAMILIES = ("anthropic", "zhipu", "deepseek", "openai", "alibaba", "minimax")


def _installation(name: str, family: str, quota_group: str = "") -> dict:
    return {"record_type": config.INSTALLATION_RECORD, "installation_id": name, "engine_kind": "fixture",
            "family": family, "model": "fixture-" + name, "quota_group": quota_group or "group-" + name,
            "lens": config.LENSES[0], "enabled": True, "disabled_reason": "", "settings": {}}


def _configuration(installations: list, **policy) -> config.PanelConfiguration:
    value = copy.deepcopy(PANEL_RECORD)
    value["installations"] = installations
    value["policy"].update(policy)
    return config.PanelConfiguration.from_dict(value)


def _request(identity: str = FIRST, body: "bytes | None" = None):
    request = DATA.request(identity, PRODUCERS.producer_for(identity), CRITERIA, INSTRUCTIONS.sha256)
    return request if body is None else request.replaced(body=body)


def answer(prompt, decision=verdicts.APPROVE, *, digest=None, findings=None, reasons="", extra=None) -> str:
    """A well formed reviewer answer about the bytes the prompt names, unless told otherwise."""
    if findings is None:
        findings = ([{"criterion_id": "read_as_a_customer", "blocking": True, "text": "A step is wrong."}]
                    if decision == verdicts.REJECT else
                    [{"criterion_id": "read_as_a_customer", "blocking": False, "text": "Read as a customer."}])
    value = {"body_sha256": digest or prompt.body_sha256, "decision": decision, "findings": findings,
             "reasons": reasons or ("The third step would corrupt data." if decision == verdicts.REJECT
                                    else "Every criterion is met.")}
    value.update(extra or {})
    return json.dumps(value)


def attempt(text: str = "", outcome: str = reviewers.ANSWERED, *, usage=(1000, 100), retry_after=None):
    usage_record = (reviewers.Usage(usage[0], usage[1], source=reviewers.PROVIDER_REPORTED) if usage
                    else reviewers.Usage(None, None, source=reviewers.USAGE_UNKNOWN))
    return reviewers.ReviewerAttempt(outcome=outcome, text=text, usage=usage_record,
                                     physical_model_calls=1, elapsed_seconds=0.5,
                                     retry_after_seconds=retry_after, reported_model="fixture",
                                     route_or_command="fixture", error_detail="")


def approving(prompt, number):
    return attempt(answer(prompt))


def rejecting(prompt, number):
    return attempt(answer(prompt, verdicts.REJECT))


class Harness:
    """A panel over fixture reviewers, a temporary ledger and a recorded clock."""

    def __init__(self, directory, scripts: dict, *, families=FAMILIES, quota_groups=None, **policy):
        quota_groups = quota_groups or {}
        names = list(scripts)
        installations = [_installation(name, family, quota_groups.get(name, ""))
                         for name, family in zip(names, families)]
        self.configuration = _configuration(installations, **policy)
        self.reviewers = {item.installation_id: FixtureReviewer(item, scripts[item.installation_id])
                          for item in self.configuration.installations}
        self.ledger_path = Path(directory) / "ledger.jsonl"
        self.sleeps = []
        self.now = [1_000_000.0]

    def clock(self):
        return self.now[0]

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now[0] += seconds

    def run(self, requests, *, run_id="run-1", call_ceiling=100, token_ceiling=10_000_000, authorized=True):
        panel = panel_module.ReviewPanel(
            self.configuration, CRITERIA, INSTRUCTIONS, self.reviewers,
            engines.build_precheck_engines(self.configuration, only_builtin=True),
            ReviewLedger(self.ledger_path), sleeper=self.sleep, clock=self.clock)
        return panel.run(panel_module.PanelRunRequest(
            run_id=run_id, requests=tuple(requests), population=DATA.population_bodies(),
            call_ceiling=call_ceiling, token_ceiling=token_ceiling, model_calls_authorized=authorized,
            fixture_run=True))

    def calls(self, name):
        return self.reviewers[name].calls


def _only(result, identity=FIRST):
    return next(item for item in result.items if item.identity == identity)


class ApprovalRuleTest(unittest.TestCase):

    def test_three_approvals_from_three_families_approve(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"producer": approving, "a": approving, "b": approving, "c": approving})
            result = harness.run([_request()])
            item = _only(result)
            self.assertEqual(item.outcome, panel_module.APPROVED)
            self.assertEqual(item.rule_applied, panel_module.FAMILY_QUORUM_RULE)
            self.assertEqual(sorted(verdict["reviewer_id"] for verdict in item.verdicts), ["a", "b", "c"])
            self.assertEqual(len(result.calls), 3)

    def test_the_producer_family_is_never_asked(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"producer": approving, "a": approving, "b": approving, "c": approving})
            result = harness.run([_request()])
            self.assertEqual(harness.calls("producer"), [])
            self.assertIn("producer", result.ineligible)
            self.assertEqual(result.ineligible["producer"], panel_module.PRODUCER_FAMILY)

    def test_two_families_cannot_make_a_quorum_and_no_call_is_spent(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a1": approving, "a2": approving, "b": approving},
                              families=("zhipu", "zhipu", "deepseek"))
            result = harness.run([_request()])
            item = _only(result)
            self.assertEqual(item.outcome, panel_module.PANEL_INCOMPLETE)
            self.assertIn(panel_module.NOT_ENOUGH_FAMILIES, item.reasons)
            self.assertEqual(result.calls, [])

    def test_a_same_family_reviewer_fills_in_only_when_a_new_family_remains(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a1": approving, "a2": approving, "b": approving, "c": approving},
                              families=("zhipu", "zhipu", "deepseek", "openai"))
            result = harness.run([_request()])
            item = _only(result)
            self.assertEqual(item.outcome, panel_module.APPROVED)
            self.assertEqual(harness.calls("a2"), [], "a second reviewer of one family adds no family")

    def test_one_rejection_withholds_approval_and_keeps_its_reasons(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"producer": approving, "a": approving, "b": rejecting, "c": approving})
            result = harness.run([_request()])
            item = _only(result)
            self.assertEqual(item.outcome, panel_module.REJECTED)
            self.assertEqual(item.rule_applied, panel_module.REJECTION_RULE)
            rejection = next(verdict for verdict in item.verdicts if verdict["decision"] == verdicts.REJECT)
            self.assertEqual(rejection["reviewer_id"], "b")
            self.assertIn("corrupt data", rejection["reasons"])
            self.assertEqual(len(result.calls), 3, "every planned reviewer is heard, so disagreement is measured")

    def test_the_family_count_is_what_refuses_two_families(self):
        """Mutant control: with the family count replaced by the reviewer count, two families approve."""
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a1": approving, "a2": approving, "b": approving},
                              families=("zhipu", "zhipu", "deepseek"))
            with mock.patch.object(panel_module, "distinct_families", lambda verdicts_, families: len(verdicts_)):
                result = harness.run([_request()])
            self.assertEqual(_only(result).outcome, panel_module.APPROVED)

    def test_the_family_exclusion_is_what_keeps_the_producer_out(self):
        """Mutant control: with the exclusion switched off, the producer's family is asked first."""
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"producer": approving, "a": approving, "b": approving, "c": approving})
            with mock.patch.object(panel_module, "producer_family_excluded", lambda installation, producer: False):
                harness.run([_request()])
            self.assertEqual(len(harness.calls("producer")), 1)

    def test_an_approval_from_the_producer_family_never_counts_toward_the_quorum(self):
        """The decision rule discounts the producer's family even when the selection let it in."""
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"producer": approving, "a": approving, "b": approving},
                              families=("anthropic", "zhipu", "deepseek"))
            with mock.patch.object(panel_module, "producer_family_excluded", lambda installation, producer: False):
                result = harness.run([_request()])
            self.assertEqual(len(harness.calls("producer")), 1, "the selection mutant asked the producer's family")
            item = _only(result)
            self.assertEqual(item.outcome, panel_module.PANEL_INCOMPLETE)
            self.assertIn(panel_module.APPROVALS_BELOW_QUORUM, item.reasons)

    def test_the_decision_rule_is_what_discounts_the_producer_family(self):
        """Mutant control: with the selection and the decision guards both removed, the producer approves."""
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"producer": approving, "a": approving, "b": approving},
                              families=("anthropic", "zhipu", "deepseek"))
            with mock.patch.object(panel_module, "producer_family_excluded", lambda installation, producer: False), \
                    mock.patch.object(panel_module, "counts_toward_approval", lambda family, producer_family: True):
                result = harness.run([_request()])
            self.assertEqual(_only(result).outcome, panel_module.APPROVED)


class BeforeAnyCallTest(unittest.TestCase):

    def test_a_pre_check_refusal_asks_no_reviewer(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": approving, "b": approving, "c": approving},
                              families=("zhipu", "deepseek", "openai"))
            result = harness.run([_request(LICENCE_UNKNOWN)])
            item = _only(result, LICENCE_UNKNOWN)
            self.assertEqual(item.outcome, panel_module.REFUSED_BEFORE_REVIEW)
            self.assertTrue(item.prechecks.refused)
            self.assertEqual(result.calls, [])
            self.assertEqual(ReviewLedger(harness.ledger_path).dispatches(), [])

    def test_a_fixture_reviewer_is_never_asked_outside_a_fixture_run(self):
        """A scripted reviewer answers only in a run declared a fixture run, so it can never decide a real item."""
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": approving, "b": approving, "c": approving},
                              families=("zhipu", "deepseek", "openai"))
            panel = panel_module.ReviewPanel(
                harness.configuration, CRITERIA, INSTRUCTIONS, harness.reviewers,
                engines.build_precheck_engines(harness.configuration, only_builtin=True),
                ReviewLedger(harness.ledger_path), sleeper=harness.sleep, clock=harness.clock)
            result = panel.run(panel_module.PanelRunRequest(
                run_id="real", requests=(_request(),), population=DATA.population_bodies(), call_ceiling=100,
                token_ceiling=10_000_000, model_calls_authorized=True, fixture_run=False))
            self.assertEqual([len(harness.calls(name)) for name in ("a", "b", "c")], [0, 0, 0])
            self.assertEqual(set(result.ineligible.values()), {panel_module.FIXTURE_OUTSIDE_FIXTURE_RUN})
            self.assertEqual(_only(result).outcome, panel_module.PANEL_INCOMPLETE)

    def test_no_model_call_without_explicit_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": approving, "b": approving, "c": approving},
                              families=("zhipu", "deepseek", "openai"))
            result = harness.run([_request()], authorized=False)
            self.assertEqual(result.calls, [])
            self.assertEqual(result.stop_reason, panel_module.MODEL_CALLS_NOT_AUTHORIZED)
            self.assertEqual(_only(result).outcome, panel_module.NOT_STARTED)
            self.assertFalse(_only(result).prechecks.refused, "the pre-checks still ran and are reported")


class AnswerValidationTest(unittest.TestCase):

    def _replaced_first(self, bad_script):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": bad_script, "b": approving, "c": approving, "d": approving},
                              families=("zhipu", "deepseek", "openai", "alibaba"))
            result = harness.run([_request()])
            item = _only(result)
            first_call = next(call for call in result.calls if call["installation_id"] == "a")
            return item, first_call, harness

    def test_an_answer_about_other_bytes_is_not_counted(self):
        item, call, harness = self._replaced_first(lambda prompt, n: attempt(answer(prompt, digest="f" * 64)))
        self.assertEqual(call["outcome"], panel_module.INVALID_RESPONSE)
        self.assertEqual(call["error_code"], "answer_names_other_bytes")
        self.assertEqual(item.outcome, panel_module.APPROVED)
        self.assertEqual(len(harness.calls("d")), 1, "a reviewer of a new family replaced the uncounted answer")
        self.assertNotIn("a", [verdict["reviewer_id"] for verdict in item.verdicts])

    def test_a_rejection_without_a_blocking_finding_is_not_counted(self):
        _item, call, _harness = self._replaced_first(lambda prompt, n: attempt(answer(prompt, verdicts.REJECT,
                                                                                      findings=[])))
        self.assertEqual(call["error_code"], "rejection_without_blocking_finding")

    def test_a_finding_that_cites_no_known_criterion_is_not_counted(self):
        _item, call, _harness = self._replaced_first(lambda prompt, n: attempt(answer(
            prompt, verdicts.REJECT, findings=[{"criterion_id": "vibes", "blocking": True, "text": "No."}])))
        self.assertEqual(call["error_code"], "finding_cites_unknown_criterion")

    def test_a_finding_that_names_its_criterion_as_a_list_or_object_is_recorded_not_raised(self):
        """Known-wrong case: an answer is untrusted text of any shape. A criterion written as a list or an
        object must be an invalid answer whose call is recorded with its usage, not an error that stops the
        run after the call returned and leaves the call without its call row."""
        for criterion in (["read_as_a_customer"], {"criterion_id": "read_as_a_customer"}):
            with self.subTest(criterion=criterion):
                item, call, harness = self._replaced_first(lambda prompt, n, criterion=criterion: attempt(answer(
                    prompt, verdicts.REJECT, findings=[{"criterion_id": criterion, "blocking": True,
                                                        "text": "No."}])))
                self.assertEqual(call["outcome"], panel_module.INVALID_RESPONSE)
                self.assertEqual(call["error_code"], "finding_invalid")
                self.assertEqual((call["usage"]["input_tokens"], call["usage"]["output_tokens"]), (1000, 100))
                self.assertEqual(item.outcome, panel_module.APPROVED)
                self.assertEqual(len(harness.calls("d")), 1)

    def test_deeply_nested_answer_text_is_recorded_not_raised(self):
        """Known-wrong case: text nested deeper than the JSON reader's recursion limit is not one answer."""
        for answer_format, text in ((verdicts.JSON_ONLY, "[" * 5000),
                                    (verdicts.JSON_AFTER_REASONING, "Reasoning. " + '{"a":' * 5000)):
            with self.subTest(answer_format=answer_format):
                self.assertEqual(verdicts.parse_verdict(text, body_sha256="a" * 64, criteria_ids=frozenset(),
                                                        answer_format=answer_format), (None, "answer_not_json"))
        _item, call, _harness = self._replaced_first(lambda prompt, n: attempt("[" * 5000))
        self.assertEqual((call["outcome"], call["error_code"]), (panel_module.INVALID_RESPONSE, "answer_not_json"))

    def test_a_rejection_without_a_written_reason_is_not_counted(self):
        _item, call, _harness = self._replaced_first(lambda prompt, n: attempt(answer(prompt, verdicts.REJECT,
                                                                                      reasons=" ")))
        self.assertEqual(call["error_code"], "rejection_without_reason")

    def test_an_approval_with_a_blocking_finding_is_not_counted(self):
        _item, call, _harness = self._replaced_first(lambda prompt, n: attempt(answer(
            prompt, findings=[{"criterion_id": "effects_rule", "blocking": True, "text": "Writes are missing."}])))
        self.assertEqual(call["error_code"], "approval_with_blocking_finding")

    def test_an_answer_with_unknown_keys_is_not_counted(self):
        _item, call, _harness = self._replaced_first(lambda prompt, n: attempt(answer(
            prompt, extra={"approved_with_changes": True})))
        self.assertEqual(call["error_code"], "answer_fields_unknown")

    def test_text_that_is_not_one_answer_is_not_counted(self):
        _item, call, _harness = self._replaced_first(lambda prompt, n: attempt("I approve this item."))
        self.assertEqual(call["error_code"], "answer_not_json")

    def test_a_failed_call_is_replaced_by_a_new_family(self):
        item, call, harness = self._replaced_first(lambda prompt, n: attempt("", reviewers.PROVIDER_UNAVAILABLE,
                                                                             usage=None))
        self.assertEqual(call["outcome"], reviewers.PROVIDER_UNAVAILABLE)
        self.assertEqual(item.outcome, panel_module.APPROVED)
        self.assertEqual(len(harness.calls("d")), 1)

    def test_the_digest_binding_is_what_refuses_other_bytes(self):
        """Mutant control: with the digest comparison removed, the answer about other bytes counts."""
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": lambda prompt, n: attempt(answer(prompt, digest="f" * 64)),
                                          "b": approving, "c": approving, "d": approving},
                              families=("zhipu", "deepseek", "openai", "alibaba"))
            with mock.patch.object(verdicts, "BIND_TO_BODY_DIGEST", False):
                result = harness.run([_request()])
            self.assertIn("a", [verdict["reviewer_id"] for verdict in _only(result).verdicts])


class BudgetTest(unittest.TestCase):

    def test_the_call_ceiling_stops_the_run_before_the_next_call(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": approving, "b": approving, "c": approving},
                              families=("zhipu", "deepseek", "openai"))
            result = harness.run([_request(), _request(SECOND)], call_ceiling=2)
            self.assertEqual(len(result.calls), 2)
            self.assertEqual(result.stop_reason, panel_module.CALL_CEILING_REACHED)
            self.assertEqual(_only(result).outcome, panel_module.PANEL_INCOMPLETE)
            self.assertEqual(_only(result, SECOND).outcome, panel_module.NOT_STARTED)

    def test_the_token_ceiling_stops_the_run_before_the_next_call(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": approving, "b": approving, "c": approving},
                              families=("zhipu", "deepseek", "openai"))
            result = harness.run([_request()], token_ceiling=100)
            self.assertEqual(result.calls, [])
            self.assertEqual(result.stop_reason, panel_module.TOKEN_CEILING_REACHED)

    def test_the_ceiling_is_what_stops_the_run(self):
        """Mutant control: with the budget always allowing, the run passes its declared ceiling."""
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": approving, "b": approving, "c": approving},
                              families=("zhipu", "deepseek", "openai"))
            with mock.patch.object(panel_module.Budget, "reserve", lambda self, tokens: True):
                result = harness.run([_request(), _request(SECOND)], call_ceiling=2)
            self.assertGreater(len(result.calls), 2)

    def test_a_rate_limit_pauses_for_a_bounded_recorded_time_then_retries(self):
        def limited_once(prompt, number):
            return attempt("", reviewers.RATE_LIMITED, usage=None, retry_after=5.0) if number == 1 else \
                attempt(answer(prompt))
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": limited_once, "b": approving, "c": approving},
                              families=("zhipu", "deepseek", "openai"))
            result = harness.run([_request()])
            self.assertEqual(harness.sleeps, [5.0])
            self.assertEqual(len(harness.calls("a")), 2)
            limited = next(call for call in result.calls if call["outcome"] == reviewers.RATE_LIMITED)
            self.assertEqual(limited["pause_seconds_after"], 5.0)
            self.assertEqual(_only(result).outcome, panel_module.APPROVED)

    def test_a_pause_never_exceeds_the_policy(self):
        always_limited = lambda prompt, number: attempt("", reviewers.RATE_LIMITED, usage=None,  # noqa: E731
                                                        retry_after=10_000.0)
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": always_limited, "b": approving, "c": approving, "d": approving},
                              families=("zhipu", "deepseek", "openai", "alibaba"))
            result = harness.run([_request()])
            rate = harness.configuration.policy.rate_limit
            self.assertTrue(all(seconds <= rate.maximum_seconds for seconds in harness.sleeps))
            self.assertLessEqual(sum(harness.sleeps), rate.maximum_total_seconds)
            self.assertEqual(len(harness.calls("a")), 1 + rate.maximum_retries_per_call)
            self.assertEqual(_only(result).outcome, panel_module.APPROVED, "a new family replaced the limited one")

    def test_a_spent_allowance_stops_every_reviewer_that_shares_it(self):
        spent = lambda prompt, number: attempt("", reviewers.USAGE_LIMIT_REACHED, usage=None)  # noqa: E731
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": spent, "b": approving, "c": approving, "d": approving, "e": approving},
                              families=("zhipu", "deepseek", "openai", "alibaba", "minimax"),
                              quota_groups={"a": "shared", "b": "shared"})
            result = harness.run([_request(), _request(SECOND)])
            self.assertEqual(len(harness.calls("a")), 1)
            self.assertEqual(harness.calls("b"), [], "a reviewer on a spent allowance is not asked")
            self.assertIn("shared", result.spent_quota_groups)
            self.assertEqual(_only(result).outcome, panel_module.APPROVED)
            self.assertEqual(_only(result, SECOND).outcome, panel_module.APPROVED)

    def test_a_refused_login_is_asked_once_per_run_not_once_per_item(self):
        """A reviewer that cannot authenticate, or whose model the provider or the route policy refuses, stays
        refused for the rest of the run; asking it again for every item would spend calls on a known failure."""
        for outcome in (reviewers.AUTHENTICATION_UNAVAILABLE, reviewers.MODEL_NOT_FOUND,
                        reviewers.REFUSED_BY_ROUTE_POLICY, reviewers.ENGINE_UNAVAILABLE):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as directory:
                refused = lambda prompt, number, outcome=outcome: attempt("", outcome, usage=(0, 0))  # noqa: E731
                harness = Harness(directory, {"a": refused, "b": approving, "c": approving, "d": approving},
                                  families=("zhipu", "deepseek", "openai", "alibaba"))
                result = harness.run([_request(), _request(SECOND)])
                self.assertEqual(len(harness.calls("a")), 1)
                self.assertEqual(result.ineligible["a"], panel_module.UNUSABLE_DURING_RUN + outcome)
                self.assertEqual(_only(result).outcome, panel_module.APPROVED)
                self.assertEqual(_only(result, SECOND).outcome, panel_module.APPROVED)

    def test_the_run_level_refusal_is_what_stops_repeated_calls(self):
        """Mutant control: with no failure treated as lasting, the refused reviewer is asked for every item."""
        refused = lambda prompt, number: attempt("", reviewers.AUTHENTICATION_UNAVAILABLE, usage=(0, 0))  # noqa: E731
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": refused, "b": approving, "c": approving, "d": approving},
                              families=("zhipu", "deepseek", "openai", "alibaba"))
            with mock.patch.object(panel_module, "LASTING_FAILURES", frozenset()):
                harness.run([_request(), _request(SECOND)])
            self.assertEqual(len(harness.calls("a")), 2)

    def test_unknown_usage_stays_unknown_and_is_charged_at_its_reservation(self):
        silent = lambda prompt, number: attempt(answer(prompt), usage=None)  # noqa: E731
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": silent, "b": approving, "c": approving},
                              families=("zhipu", "deepseek", "openai"))
            result = harness.run([_request()])
            call = next(call for call in result.calls if call["installation_id"] == "a")
            self.assertIsNone(call["usage"]["input_tokens"])
            self.assertEqual(call["usage"]["source"], reviewers.USAGE_UNKNOWN)
            self.assertEqual(call["charge_basis"], panel_module.CHARGED_AT_RESERVATION)
            self.assertGreater(call["charged_tokens"], 0)
            self.assertEqual(result.totals()["calls_with_unknown_usage"], 1)


class CursorTest(unittest.TestCase):

    def test_a_stopped_run_asks_only_the_reviewers_still_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": approving, "b": approving, "c": approving},
                              families=("zhipu", "deepseek", "openai"))
            first = harness.run([_request()], call_ceiling=2)
            self.assertEqual(first.stop_reason, panel_module.CALL_CEILING_REACHED)
            second = harness.run([_request()], run_id="run-2")
            self.assertEqual(_only(second).outcome, panel_module.APPROVED)
            self.assertEqual([len(harness.calls(name)) for name in ("a", "b", "c")], [1, 1, 1])
            self.assertEqual(len(second.calls), 1)

    def test_a_finished_run_run_again_makes_no_call(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": approving, "b": approving, "c": rejecting},
                              families=("zhipu", "deepseek", "openai"))
            first = harness.run([_request()])
            second = harness.run([_request()], run_id="run-2")
            self.assertEqual(second.calls, [])
            self.assertEqual(_only(first).outcome, _only(second).outcome)
            self.assertEqual(_only(first).verdicts, _only(second).verdicts)

    def test_a_dispatched_call_that_never_completed_is_not_repeated(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": approving, "b": approving, "c": approving, "d": approving},
                              families=("zhipu", "deepseek", "openai", "alibaba"))
            request = _request()
            installation = harness.configuration.installation("a")
            key = panel_module.review_key(installation, request, build_prompt(request, installation, INSTRUCTIONS))
            ReviewLedger(harness.ledger_path).dispatch({
                "record_type": panel_module.DISPATCH_RECORD, "run_id": "run-0", "sequence": 1, "review_key": key,
                "installation_id": "a", "identity": request.identity, "body_sha256": request.body_sha256,
                "request_sha256": request.request_sha256, "dispatched_at": "2026-09-22T00:00:00Z"})
            result = harness.run([request])
            self.assertEqual(harness.calls("a"), [])
            self.assertEqual(len(harness.calls("d")), 1)
            self.assertIn(key, result.interrupted)

    def test_a_run_identity_the_ledger_already_holds_is_refused(self):
        """The cursor names a call by its run identity and sequence number, so a second run under one
        identity would give its first call the name of an earlier dispatch."""
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": approving, "b": approving, "c": approving},
                              families=("zhipu", "deepseek", "openai"))
            harness.run([_request()], run_id="resume")
            with self.assertRaises(CandidateReviewError) as caught:
                harness.run([_request(SECOND)], run_id="resume")
            self.assertEqual(caught.exception.code, "run_identity_repeated")
            self.assertEqual([row["run_id"] for row in ReviewLedger(harness.ledger_path).runs()], ["resume"])

    def test_a_ledger_whose_last_line_was_not_completed_is_refused(self):
        """A write stopped part way leaves a line with no line break, and the next append would join it."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            row = {"record_type": panel_module.RUN_RECORD, "run_id": "cut", "started_at": "2026-09-22T00:00:00Z",
                   "policy_sha256": BASE.policy.sha256, "call_ceiling": 1, "token_ceiling": 1, "fixture_run": True,
                   "requests": []}
            path.write_text(json.dumps(row, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            with self.assertRaises(CandidateReviewError) as caught:
                ReviewLedger(path)
            self.assertEqual(caught.exception.code, "ledger_truncated")

    def test_a_ledger_file_that_holds_one_run_identity_twice_is_refused(self):
        """Such a ledger cannot tell two calls of the same name apart, so it is never read as a cursor."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            row = {"record_type": panel_module.RUN_RECORD, "run_id": "resume", "started_at": "2026-09-22T00:00:00Z",
                   "policy_sha256": BASE.policy.sha256, "call_ceiling": 1, "token_ceiling": 1, "fixture_run": True,
                   "requests": []}
            line = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
            path.write_text(line + line, encoding="utf-8")
            with self.assertRaises(CandidateReviewError) as caught:
                ReviewLedger(path)
            self.assertEqual(caught.exception.code, "run_identity_repeated")

    @staticmethod
    def _stopped_run(directory):
        """A ledger in which run "resume" dispatched reviewer "a" for the first item and never completed it."""
        harness = Harness(directory, {"a": approving, "b": approving, "c": approving, "d": approving},
                          families=("zhipu", "deepseek", "openai", "alibaba"))
        request = _request()
        installation = harness.configuration.installation("a")
        key = panel_module.review_key(installation, request, build_prompt(request, installation, INSTRUCTIONS))
        ledger = ReviewLedger(harness.ledger_path)
        ledger.start_run({
            "record_type": panel_module.RUN_RECORD, "run_id": "resume", "started_at": "2026-09-22T00:00:00Z",
            "policy_sha256": harness.configuration.policy.sha256, "call_ceiling": 10, "token_ceiling": 10,
            "fixture_run": True, "requests": [request.request_sha256]})
        ledger.dispatch({
            "record_type": panel_module.DISPATCH_RECORD, "run_id": "resume", "sequence": 1, "review_key": key,
            "installation_id": "a", "identity": request.identity, "body_sha256": request.body_sha256,
            "request_sha256": request.request_sha256, "dispatched_at": "2026-09-22T00:00:01Z"})
        return harness, request, key

    def test_a_reused_run_identity_never_turns_an_interrupted_dispatch_into_a_completed_call(self):
        """Known-wrong case: a stopped run left a dispatch with no call row. A second run under the same
        identity would complete a call with the same name, the ledger would read the dispatch as completed,
        and a later run would ask the same reviewer about the same bytes again."""
        with tempfile.TemporaryDirectory() as directory:
            harness, request, key = self._stopped_run(directory)
            try:
                harness.run([_request(SECOND)], run_id="resume")
            except CandidateReviewError:
                pass
            self.assertTrue(ReviewLedger(harness.ledger_path).interrupted(key))
            result = harness.run([request], run_id="later")
            self.assertEqual(harness.calls("a"), [])
            self.assertIn(key, result.interrupted)

    def test_the_run_identity_check_is_what_keeps_the_dispatch_interrupted(self):
        """Mutant control: with the run identity check removed, the reused identity hides the dispatch and
        the reviewer is asked about the same bytes again."""
        with tempfile.TemporaryDirectory() as directory:
            harness, request, key = self._stopped_run(directory)
            with mock.patch.object(ReviewLedger, "_run_identity_is_new", lambda self, row: None):
                harness.run([_request(SECOND)], run_id="resume")
                self.assertFalse(ReviewLedger(harness.ledger_path).interrupted(key))
                harness.run([request], run_id="later")
            self.assertEqual(len(harness.calls("a")), 2)

    def test_changed_bytes_are_a_new_review_subject(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": approving, "b": approving, "c": approving},
                              families=("zhipu", "deepseek", "openai"))
            harness.run([_request()])
            changed = _request(body=DATA.body_bytes(FIRST).replace(b"## Checks", b"## Checks\n", 1))
            result = harness.run([changed], run_id="run-2")
            self.assertEqual([len(harness.calls(name)) for name in ("a", "b", "c")], [2, 2, 2])
            self.assertEqual(len(result.calls), 3)

    def test_the_ledger_is_what_prevents_a_second_review(self):
        """Mutant control: with the stored verdicts ignored, a second run asks everyone again."""
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": approving, "b": approving, "c": approving},
                              families=("zhipu", "deepseek", "openai"))
            harness.run([_request()])
            with mock.patch.object(ReviewLedger, "verdict", lambda self, key: None):
                second = harness.run([_request()], run_id="run-2")
            self.assertEqual(len(second.calls), 3)


RESTATED = "profile_text_column_before_cleaning"
GENERAL_PRACTICE, RESTATES = "general_practice_beside_cited_source", "restates_cited_source"


class RequestByKindTest(unittest.TestCase):
    """Each reviewer is told the kind of body in the sheet's words and receives only the criteria for it."""

    def _prompt(self, identity):
        request = _request(identity)
        return request, build_prompt(request, BASE.installations[0], INSTRUCTIONS)

    def test_a_general_practice_prompt_names_its_kind_and_only_its_criteria(self):
        request, prompt = self._prompt(FIRST)
        self.assertEqual(request.grounding, GENERAL_PRACTICE)
        self.assertIn(CRITERIA.groundings[GENERAL_PRACTICE], prompt.user)
        self.assertNotIn(CRITERIA.groundings[RESTATES], prompt.user)
        self.assertIn("- general_practice_grounding:", prompt.user)
        self.assertNotIn("restated_source_grounding", prompt.user)
        self.assertEqual(request.applicable_criteria_ids,
                         frozenset(item.criterion_id for item in CRITERIA.applicable(GENERAL_PRACTICE)))

    def test_a_restated_source_prompt_names_its_kind_and_only_its_criteria(self):
        request, prompt = self._prompt(RESTATED)
        self.assertEqual(request.grounding, RESTATES)
        self.assertIn(CRITERIA.groundings[RESTATES], prompt.user)
        self.assertIn("- restated_source_grounding:", prompt.user)
        self.assertNotIn("general_practice_grounding", prompt.user)

    def test_a_finding_that_cites_the_other_kind_criterion_is_not_counted(self):
        misapplied = lambda prompt, number: attempt(answer(prompt, verdicts.REJECT, findings=[{  # noqa: E731
            "criterion_id": "restated_source_grounding", "blocking": True,
            "text": "The steps do not restate the cited file."}]))
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": misapplied, "b": approving, "c": approving, "d": approving},
                              families=("zhipu", "deepseek", "openai", "alibaba"))
            result = harness.run([_request()])
        call = next(call for call in result.calls if call["installation_id"] == "a")
        self.assertEqual(call["error_code"], "finding_cites_unknown_criterion")
        self.assertEqual(_only(result).outcome, panel_module.APPROVED)

    def test_the_request_is_what_withholds_the_other_kind_criterion(self):
        """Mutant control: with every criterion applicable, the misapplied rejection counts."""
        misapplied = lambda prompt, number: attempt(answer(prompt, verdicts.REJECT, findings=[{  # noqa: E731
            "criterion_id": "restated_source_grounding", "blocking": True,
            "text": "The steps do not restate the cited file."}]))
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": misapplied, "b": approving, "c": approving, "d": approving},
                              families=("zhipu", "deepseek", "openai", "alibaba"))
            with mock.patch.object(config, "criterion_applies", lambda criterion, grounding: True):
                result = harness.run([_request()])
        self.assertEqual(_only(result).outcome, panel_module.REJECTED)


def _key_without_prompt(installation, request, prompt):
    return digest({"installation_sha256": installation.sha256, "request_sha256": request.request_sha256})


def _with_one_more_sentence(request, installation, instructions):
    prompt = build_prompt(request, installation, instructions)
    user = prompt.user + "\n\nOne more sentence for the reviewer."
    return dataclasses.replace(prompt, user=user, sha256=digest({"system": prompt.system, "user": user}))


class PromptBindingTest(unittest.TestCase):
    """A verdict is reused only for the exact prompt it answered, so a changed prompt is a new review."""

    def test_a_changed_prompt_is_a_new_review_subject(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": approving, "b": approving, "c": approving},
                              families=("zhipu", "deepseek", "openai"))
            harness.run([_request()])
            with mock.patch.object(panel_module, "build_prompt", _with_one_more_sentence):
                second = harness.run([_request()], run_id="run-2")
            self.assertEqual(len(second.calls), 3)
            self.assertEqual({call["prompt_sha256"] for call in second.calls} &
                             {call["prompt_sha256"] for call in ReviewLedger(harness.ledger_path).calls()
                              if call["run_id"] == "run-1"}, set())

    def test_the_prompt_digest_is_what_makes_a_changed_prompt_a_new_subject(self):
        """Mutant control: with the prompt left out of the review key, the stale verdicts are reused."""
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": approving, "b": approving, "c": approving},
                              families=("zhipu", "deepseek", "openai"))
            with mock.patch.object(panel_module, "review_key", _key_without_prompt):
                harness.run([_request()])
                with mock.patch.object(panel_module, "build_prompt", _with_one_more_sentence):
                    second = harness.run([_request()], run_id="run-2")
            self.assertEqual(second.calls, [])


class AnswerFormatTest(unittest.TestCase):
    """A declared answer format decides how much text may stand before the verdict, and nothing else."""

    CRITERIA_IDS = CRITERIA.ids

    def _verdict(self, prompt_digest="0" * 64):
        return json.dumps({"body_sha256": prompt_digest, "decision": verdicts.APPROVE,
                           "findings": [], "reasons": "Every criterion is met."})

    def test_strict_answers_refuse_text_before_the_verdict(self):
        text = "Let me think about the item first.\n" + self._verdict()
        _content, code = verdicts.parse_verdict(text, body_sha256="0" * 64, criteria_ids=self.CRITERIA_IDS)
        self.assertEqual(code, "answer_not_json")

    def test_an_answer_after_reasoning_is_read_only_when_declared(self):
        text = "The user wants a review. I checked each criterion.\n\n" + self._verdict()
        content, code = verdicts.parse_verdict(text, body_sha256="0" * 64, criteria_ids=self.CRITERIA_IDS,
                                               answer_format=verdicts.JSON_AFTER_REASONING)
        self.assertEqual(code, "")
        self.assertEqual(content.decision, verdicts.APPROVE)

    def test_text_after_the_verdict_is_never_accepted(self):
        text = self._verdict() + "\nActually, I would reject it."
        for answer_format in verdicts.ANSWER_FORMATS:
            with self.subTest(answer_format=answer_format):
                _content, code = verdicts.parse_verdict(text, body_sha256="0" * 64, criteria_ids=self.CRITERIA_IDS,
                                                        answer_format=answer_format)
                self.assertEqual(code, "answer_not_json")

    def test_the_last_object_is_the_verdict_after_reasoning(self):
        earlier = json.dumps({"body_sha256": "0" * 64, "decision": verdicts.REJECT, "findings": [],
                              "reasons": "draft"})
        text = "Draft: " + earlier + "\nFinal:\n" + self._verdict()
        content, code = verdicts.parse_verdict(text, body_sha256="0" * 64, criteria_ids=self.CRITERIA_IDS,
                                               answer_format=verdicts.JSON_AFTER_REASONING)
        self.assertEqual((code, content.decision), ("", verdicts.APPROVE))

    def test_an_unknown_answer_format_is_refused(self):
        _content, code = verdicts.parse_verdict(self._verdict(), body_sha256="0" * 64,
                                                criteria_ids=self.CRITERIA_IDS, answer_format="anything_goes")
        self.assertEqual(code, "answer_format_unknown")

    def test_the_panel_reads_each_engine_with_its_declared_format(self):
        chatty = lambda prompt, number: attempt("I looked at the item.\n" + answer(prompt))  # noqa: E731
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": chatty, "b": approving, "c": approving, "d": approving},
                              families=("zhipu", "deepseek", "openai", "alibaba"))
            harness.reviewers["a"].answer_format = verdicts.JSON_AFTER_REASONING
            result = harness.run([_request()])
            self.assertIn("a", [verdict["reviewer_id"] for verdict in _only(result).verdicts])
            self.assertEqual(harness.calls("d"), [])


class RecordHygieneTest(unittest.TestCase):

    def test_a_secret_in_an_answer_is_never_written(self):
        secret = "sk-" + "S" * 30
        leaky = lambda prompt, number: attempt(answer(prompt, reasons="Fine. The key " + secret + " was seen."))  # noqa: E731
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": leaky, "b": approving, "c": approving},
                              families=("zhipu", "deepseek", "openai"))
            result = harness.run([_request()])
            written = harness.ledger_path.read_text(encoding="utf-8") + json.dumps(result.to_dict())
        self.assertNotIn("S" * 30, written)
        self.assertIn(panel_module.REDACTED, written)


if __name__ == "__main__":
    unittest.main()
