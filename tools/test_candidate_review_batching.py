"""Checks for batched review and the run limits that raise review throughput safely.

Every check uses fixture reviewers, so no model is called:

```text
What batched review and the run limits must guarantee
├── Batch answers
│   ├── one verdict per candidate, in order, each naming its own identity and digest
│   ├── a verdict naming another candidate or other bytes costs only its own candidate
│   └── a list of another length counts for no candidate
├── Batch prompts
│   ├── each candidate's material is exactly what its single prompt holds
│   ├── a candidate keeps its key whichever candidates share the request
│   └── mixed content profiles and repeated candidates are refused
├── Batched panel runs
│   ├── the same reviewer order and approval rule as one item at a time
│   ├── one call per reviewer per batch, recorded once with its usage
│   ├── a candidate whose verdict did not count moves to the next family alone
│   ├── a finished run, run again with other batch companions, makes no call
│   └── a batch that was dispatched and never completed is not repeated
├── Run limits
│   ├── a quota group stops at its own call ceiling while other groups continue
│   ├── an installation that fails the same way too often is asked no more
│   └── below the quorum, each reachable family is asked once only with a written
│       reason, the rule is unchanged, and a later family completes the quorum
│       without asking the others again
└── Ledger
    ├── a batch verdict needs its member row to name a verdict
    └── a batch verdict needs the exact reported model
```

Mutant controls replace one guard at a time and show that its known-wrong case
then passes, so each case is held by the guard it names.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from candidate_review import engines  # noqa: E402
from candidate_review import panel as panel_module  # noqa: E402
from candidate_review import prompt as prompt_module  # noqa: E402
from candidate_review import reviewers  # noqa: E402
from candidate_review import verdicts  # noqa: E402
from candidate_review.ledger import ReviewLedger  # noqa: E402
from candidate_review.records import BATCH_CALL_RECORD, CandidateReviewError  # noqa: E402
from test_candidate_review_panel import (  # noqa: E402
    CRITERIA, DATA, INSTRUCTIONS, Harness, _request, approving, attempt,
)

ITEMS = ("profile_text_column_before_cleaning", "normalize_whitespace_and_unicode_text",
         "restore_capitalisation_of_names", "canonicalize_company_legal_suffixes")
ORDER_LINE = re.compile(r"^(\d+)\. identity (\S+), body_sha256 ([0-9a-f]{64})$", re.MULTILINE)
CRITERION = "read_as_a_customer"


def members_of(prompt) -> list:
    """The (identity, digest) pairs a batch prompt lists, in order."""
    return [(identity, digest) for _position, identity, digest in ORDER_LINE.findall(prompt.user)]


def verdict_row(identity, digest, decision=verdicts.APPROVE) -> dict:
    blocking = decision == verdicts.REJECT
    return {"identity": identity, "body_sha256": digest, "decision": decision,
            "findings": [{"criterion_id": CRITERION, "blocking": blocking,
                          "text": "A step is wrong." if blocking else "Read as a customer."}],
            "reasons": "The third step would corrupt data." if blocking else "Every criterion is met."}


def batch_answer(prompt, decide=lambda identity: verdicts.APPROVE, change=None) -> str:
    rows = [verdict_row(identity, digest, decide(identity)) for identity, digest in members_of(prompt)]
    if change is not None:
        rows = change(rows)
    return json.dumps({"verdicts": rows})


def batch_approving(prompt, number):
    return attempt(batch_answer(prompt))


def batch_rejecting(prompt, number):
    return attempt(batch_answer(prompt, lambda identity: verdicts.REJECT))


def requests(names=ITEMS):
    return [_request(name) for name in names]


def run(harness, items, *, run_id="run-1", batch_sizes=None, call_ceiling=100, **fields):
    panel = panel_module.ReviewPanel(
        harness.configuration, CRITERIA, INSTRUCTIONS, harness.reviewers,
        engines.build_precheck_engines(harness.configuration, only_builtin=True),
        ReviewLedger(harness.ledger_path), sleeper=harness.sleep, clock=harness.clock)
    names = [item.installation_id for item in harness.configuration.installations]
    sizes = {name: 4 for name in names} if batch_sizes is None else batch_sizes
    return panel.run(panel_module.PanelRunRequest(
        run_id=run_id, requests=tuple(items), population=DATA.population_bodies(), call_ceiling=call_ceiling,
        token_ceiling=10_000_000, model_calls_authorized=True, fixture_run=True, batch_sizes=sizes, **fields))


def outcomes(result) -> dict:
    return {item.identity: item.outcome for item in result.items}


class BatchAnswerTest(unittest.TestCase):
    MEMBERS = [("first", "a" * 64, frozenset({CRITERION})), ("second", "b" * 64, frozenset({CRITERION}))]

    def parse(self, rows, **options):
        return verdicts.parse_batch_verdicts(json.dumps({"verdicts": rows}), members=self.MEMBERS, **options)

    def test_one_verdict_per_candidate_in_order(self):
        results, code = self.parse([verdict_row("first", "a" * 64), verdict_row("second", "b" * 64,
                                                                                 verdicts.REJECT)])
        self.assertEqual(code, "")
        self.assertEqual([content.decision for content, _code in results], [verdicts.APPROVE, verdicts.REJECT])

    def test_a_verdict_about_another_candidate_costs_only_its_own(self):
        cases = {"answer_names_other_candidate": verdict_row("second", "a" * 64),
                 "answer_names_other_bytes": verdict_row("first", "b" * 64)}
        for code, wrong in cases.items():
            with self.subTest(code=code):
                results, batch_code = self.parse([wrong, verdict_row("second", "b" * 64)])
                self.assertEqual(batch_code, "")
                self.assertEqual(results[0], (None, code))
                self.assertEqual(results[1][0].decision, verdicts.APPROVE)

    def test_a_list_of_another_length_counts_for_no_candidate(self):
        for rows in ([verdict_row("first", "a" * 64)],
                     [verdict_row("first", "a" * 64), verdict_row("second", "b" * 64),
                      verdict_row("second", "b" * 64)]):
            with self.subTest(length=len(rows)):
                self.assertEqual(self.parse(rows), (None, "batch_verdict_count_mismatch"))

    def test_other_shapes_are_refused(self):
        members = self.MEMBERS
        cases = {"answer_not_json": "not json",
                 "batch_answer_fields_invalid": json.dumps({"verdicts": [], "note": "x"}),
                 "batch_verdicts_not_a_list": json.dumps({"verdicts": {"first": {}}})}
        for code, text in cases.items():
            with self.subTest(code=code):
                self.assertEqual(verdicts.parse_batch_verdicts(text, members=members), (None, code))
        extra = dict(verdict_row("first", "a" * 64), note="x")
        results, _code = self.parse([extra, verdict_row("second", "b" * 64)])
        self.assertEqual(results[0], (None, "answer_fields_unknown"))

    def test_reasoning_before_the_batch_answer_is_read_in_that_format_only(self):
        text = "I read both.\n" + json.dumps({"verdicts": [verdict_row("first", "a" * 64),
                                                          verdict_row("second", "b" * 64)]})
        self.assertEqual(verdicts.parse_batch_verdicts(text, members=self.MEMBERS), (None, "answer_not_json"))
        results, code = verdicts.parse_batch_verdicts(text, members=self.MEMBERS,
                                                      answer_format=verdicts.JSON_AFTER_REASONING)
        self.assertEqual((code, len(results)), ("", 2))

    def test_mutant_without_identity_binding_counts_a_verdict_about_another_candidate(self):
        """Mutant control: with the identity comparison removed, a swapped verdict counts."""
        with mock.patch.object(verdicts, "BIND_TO_MEMBER_IDENTITY", False):
            results, _code = self.parse([verdict_row("second", "a" * 64), verdict_row("second", "b" * 64)])
        self.assertIsNotNone(results[0][0], "the mutant accepted a verdict naming another candidate")

    def test_mutant_without_the_count_rule_counts_a_short_list(self):
        """Mutant control: with the count rule removed, a list that dropped a verdict counts in part."""
        with mock.patch.object(verdicts, "BATCH_COUNT_MUST_MATCH", False):
            results, code = self.parse([verdict_row("first", "a" * 64)])
        self.assertEqual(code, "")
        self.assertIsNotNone(results[0][0], "the mutant counted a verdict from a list of the wrong length")


class BatchPromptTest(unittest.TestCase):
    def installation(self):
        with tempfile.TemporaryDirectory() as directory:
            return Harness(directory, {"a": batch_approving}).configuration.installations[0]

    def test_each_member_holds_exactly_its_single_prompt_material(self):
        installation = self.installation()
        items = requests()
        batch = prompt_module.build_batch_prompt(items, installation, INSTRUCTIONS)
        for request in items:
            single = prompt_module.build_prompt(request, installation, INSTRUCTIONS)
            material = prompt_module.member_parts(request)
            self.assertTrue(single.user.startswith(material), "the single prompt adds only its answer line")
            self.assertIn(material, batch.user)
        self.assertEqual([member.identity for member in batch.members], list(ITEMS))
        self.assertIn("exactly one key, `verdicts`", batch.system, "the batch answer contract is sent")
        self.assertTrue(batch.system.startswith(prompt_module.build_prompt(items[0], installation,
                                                                           INSTRUCTIONS).system))

    def test_a_member_keeps_its_key_whichever_candidates_share_the_request(self):
        installation = self.installation()
        items = requests()
        whole = prompt_module.build_batch_prompt(items, installation, INSTRUCTIONS)
        part = prompt_module.build_batch_prompt(list(reversed(items[1:3])), installation, INSTRUCTIONS)
        keys = {member.identity: member.member_prompt_sha256 for member in whole.members}
        for member in part.members:
            self.assertEqual(member.member_prompt_sha256, keys[member.identity])
        self.assertNotEqual(whole.sha256, part.sha256, "the batch digest still names the whole request")
        single = prompt_module.build_prompt(items[0], installation, INSTRUCTIONS)
        self.assertNotEqual(keys[items[0].identity], single.sha256, "a batch key never equals a single key")

    def test_repeated_candidates_and_sizes_out_of_bounds_are_refused(self):
        installation = self.installation()
        cases = {"batch_repeats_a_candidate": requests(ITEMS[:1]) * 2, "batch_size_invalid": []}
        for code, items in cases.items():
            with self.subTest(code=code), self.assertRaises(CandidateReviewError) as caught:
                prompt_module.build_batch_prompt(items, installation, INSTRUCTIONS)
            self.assertEqual(caught.exception.code, code)


class BatchedPanelTest(unittest.TestCase):
    def test_three_families_approve_in_one_call_each(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"producer": batch_approving, "a": batch_approving,
                                          "b": batch_approving, "c": batch_approving})
            result = run(harness, requests())
        self.assertEqual(set(outcomes(result).values()), {panel_module.APPROVED})
        self.assertEqual(len(result.calls), 3, "one call per reviewer for the whole batch")
        self.assertEqual({call["record_type"] for call in result.calls}, {BATCH_CALL_RECORD})
        self.assertEqual(harness.calls("producer"), [])
        for call in result.calls:
            self.assertEqual([member["outcome"] for member in call["members"]], ["verdict"] * len(ITEMS))
            self.assertEqual(call["usage"]["input_tokens"], 1000, "the call's usage is recorded once")
        self.assertEqual(result.totals()["calls"], 3)

    def test_a_batch_answer_from_another_model_counts_for_no_item(self):
        def another_model(prompt, number):
            return dataclasses.replace(attempt(batch_answer(prompt)), reported_model="another-model")

        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": another_model, "b": batch_approving, "c": batch_approving,
                                          "d": batch_approving}, families=("zhipu", "deepseek", "openai", "alibaba"))
            result = run(harness, requests())
        first = next(call for call in result.calls if call["installation_id"] == "a")
        self.assertEqual(first["outcome"], reviewers.MODEL_IDENTITY_MISMATCH)
        self.assertEqual({member["outcome"] for member in first["members"]}, {"not_answered"})
        self.assertEqual(len(harness.calls("d")), 1, "every item moved to the next family")
        self.assertEqual(set(outcomes(result).values()), {panel_module.APPROVED})

    def test_one_rejection_withholds_approval_in_a_batch(self):
        def one_rejection(prompt, number):
            return attempt(batch_answer(prompt, lambda identity: verdicts.REJECT if identity == ITEMS[1]
                                        else verdicts.APPROVE))

        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": batch_approving, "b": one_rejection, "c": batch_approving},
                              families=("zhipu", "deepseek", "openai"))
            result = run(harness, requests())
        found = outcomes(result)
        self.assertEqual(found[ITEMS[1]], panel_module.REJECTED)
        self.assertEqual({found[name] for name in ITEMS if name != ITEMS[1]}, {panel_module.APPROVED})

    def test_a_candidate_whose_verdict_did_not_count_moves_on_alone(self):
        def swaps_one_digest(prompt, number):
            def change(rows):
                rows[0] = dict(rows[0], body_sha256="0" * 64)
                return rows
            return attempt(batch_answer(prompt, change=change))

        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": swaps_one_digest, "b": batch_approving, "c": batch_approving,
                                          "d": batch_approving}, families=("zhipu", "deepseek", "openai", "alibaba"))
            result = run(harness, requests())
        self.assertEqual(set(outcomes(result).values()), {panel_module.APPROVED})
        self.assertEqual(len(harness.calls("d")), 1)
        self.assertEqual(members_of(harness.calls("d")[0]), [(ITEMS[0], _request(ITEMS[0]).body_sha256)],
                         "only the candidate whose verdict did not count is asked again")
        first = next(call for call in result.calls if call["installation_id"] == "a")
        self.assertEqual(first["members"][0]["outcome"], "invalid_response")
        self.assertEqual(first["members"][0]["error_code"], "answer_names_other_bytes")

    def test_a_list_of_another_length_moves_every_candidate_on(self):
        def drops_one(prompt, number):
            return attempt(batch_answer(prompt, change=lambda rows: rows[:-1]))

        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": drops_one, "b": batch_approving, "c": batch_approving,
                                          "d": batch_approving}, families=("zhipu", "deepseek", "openai", "alibaba"))
            result = run(harness, requests())
        self.assertEqual(set(outcomes(result).values()), {panel_module.APPROVED})
        self.assertEqual(len(members_of(harness.calls("d")[0])), len(ITEMS))
        first = next(call for call in result.calls if call["installation_id"] == "a")
        self.assertEqual(first["error_code"], "batch_verdict_count_mismatch")

    def test_a_finished_run_run_again_with_other_companions_makes_no_call(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": batch_approving, "b": batch_approving, "c": batch_approving},
                              families=("zhipu", "deepseek", "openai"))
            run(harness, requests())
            again = run(harness, requests(ITEMS[1:3]), run_id="run-2")
        self.assertEqual(again.calls, [])
        self.assertEqual(set(outcomes(again).values()), {panel_module.APPROVED})

    def test_an_interrupted_batch_is_not_repeated(self):
        def crashes(prompt, number):
            raise KeyboardInterrupt

        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": crashes, "b": batch_approving, "c": batch_approving},
                              families=("zhipu", "deepseek", "openai"))
            with self.assertRaises(KeyboardInterrupt):
                run(harness, requests())
            harness.reviewers["a"].script = lambda prompt, number: attempt(batch_answer(prompt))
            again = run(harness, requests(), run_id="run-2")
        self.assertEqual(harness.calls("a"), [harness.calls("a")[0]], "the interrupted batch was not asked again")
        self.assertEqual(len(again.interrupted), len(ITEMS))
        self.assertEqual(set(outcomes(again).values()), {panel_module.PANEL_INCOMPLETE})


class RunLimitTest(unittest.TestCase):
    def test_a_quota_group_stops_at_its_own_ceiling(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": approving, "b": approving, "c": approving,
                                          "d": approving}, families=("zhipu", "deepseek", "openai", "alibaba"),
                              quota_groups={"a": "limited"})
            result = run(harness, requests(), batch_sizes={}, quota_group_call_ceilings={"limited": 2})
        self.assertEqual(len(harness.calls("a")), 2)
        self.assertEqual(result.capped_quota_groups, {"limited"})
        self.assertEqual(set(outcomes(result).values()), {panel_module.APPROVED}, "other groups continue")

    def test_mutant_without_the_group_ceiling_asks_past_it(self):
        """Mutant control: with the group ceiling never refusing, the limited group is asked for every item."""
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": approving, "b": approving, "c": approving,
                                          "d": approving}, families=("zhipu", "deepseek", "openai", "alibaba"),
                              quota_groups={"a": "limited"})
            with mock.patch.object(panel_module.ReviewPanel, "_claim_group_call",
                                   staticmethod(lambda installation, run_request, state: True)):
                run(harness, requests(), batch_sizes={}, quota_group_call_ceilings={"limited": 2})
        self.assertEqual(len(harness.calls("a")), len(ITEMS))

    @staticmethod
    def _timing_out(prompt, number):
        return attempt(outcome=reviewers.TIMEOUT, usage=None)

    def test_an_installation_that_fails_the_same_way_too_often_is_asked_no_more(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": self._timing_out, "b": approving, "c": approving,
                                          "d": approving}, families=("zhipu", "deepseek", "openai", "alibaba"))
            result = run(harness, requests(), batch_sizes={}, repeated_failure_limit=2)
        self.assertEqual(len(harness.calls("a")), 2)
        self.assertTrue(result.ineligible["a"].startswith(panel_module.UNUSABLE_DURING_RUN
                                                         + panel_module.REPEATED_FAILURE))
        self.assertEqual(set(outcomes(result).values()), {panel_module.APPROVED})

    def test_mutant_without_the_repeated_failure_limit_asks_for_every_item(self):
        """Mutant control: with failures never tracked, the failing installation is asked for every item."""
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": self._timing_out, "b": approving, "c": approving,
                                          "d": approving}, families=("zhipu", "deepseek", "openai", "alibaba"))
            with mock.patch.object(panel_module.ReviewPanel, "_note_failure",
                                   staticmethod(lambda installation, signature, run_request, state: None)):
                run(harness, requests(), batch_sizes={}, repeated_failure_limit=2)
        self.assertEqual(len(harness.calls("a")), len(ITEMS))

    def test_below_the_quorum_each_reachable_family_is_asked_once_and_the_rule_holds(self):
        reason = "the third family's allowance is spent until a stated date"
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": batch_approving, "b": batch_approving},
                              families=("zhipu", "deepseek"))
            silent = run(harness, requests())
            self.assertEqual(silent.calls, [], "without a written reason no call is spent below the quorum")
            self.assertTrue(all(panel_module.NOT_ENOUGH_FAMILIES in item.reasons for item in silent.items),
                            "each item says why no reviewer was asked")
            collected = run(harness, requests(), run_id="run-2", collect_below_quorum_reason=reason)
            self.assertEqual(len(collected.calls), 2)
            self.assertEqual(set(outcomes(collected).values()), {panel_module.PANEL_INCOMPLETE})
            for name in ("a", "b"):
                harness.reviewers[name].script = lambda prompt, number: (_ for _ in ()).throw(AssertionError(
                    "a family already heard is asked again"))
            third = Harness(directory, {"a": batch_approving, "b": batch_approving, "c": batch_approving},
                            families=("zhipu", "deepseek", "openai"))
            third.reviewers["a"], third.reviewers["b"] = harness.reviewers["a"], harness.reviewers["b"]
            completed = run(third, requests(), run_id="run-3")
        self.assertEqual(set(outcomes(completed).values()), {panel_module.APPROVED})
        self.assertEqual(len(completed.calls), 1, "only the missing family is asked")

    def test_below_the_quorum_a_rejection_still_decides(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": batch_rejecting, "b": batch_approving},
                              families=("zhipu", "deepseek"))
            result = run(harness, requests(), collect_below_quorum_reason="collect while a family is out of reach")
        self.assertEqual(set(outcomes(result).values()), {panel_module.REJECTED})
        self.assertEqual(len(result.calls), 2, "the second family is still asked, for the disagreement record")

    def test_mutant_that_ignores_the_below_quorum_reason_spends_no_call(self):
        """Mutant control: with the reason ignored, nothing is collected while a family is out of reach."""
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": batch_approving, "b": batch_approving},
                              families=("zhipu", "deepseek"))
            with mock.patch.object(panel_module.PanelRunRequest, "below_quorum", property(lambda self: False)):
                result = run(harness, requests(), collect_below_quorum_reason="collect while a family is away")
        self.assertEqual(result.calls, [])


class CommandOptionsTest(unittest.TestCase):
    """The review command's new options: refused when malformed, and no credential without model authority."""

    ROOT = HERE.parent

    def options(self, *extra):
        import review_catalogue_candidates as command
        return command, command._parser().parse_args([
            "--catalogue", str(self.ROOT / "examples/29_intelligence_service/starter-catalogue"),
            "--repository", str(self.ROOT), "--ledger", str(Path(self.directory) / "ledger.jsonl"),
            "--identity", ITEMS[0], "--call-ceiling", "0", "--token-ceiling", "0", *extra])

    def setUp(self):
        self.directory = tempfile.mkdtemp(dir=self.ROOT / "artifacts")
        self.addCleanup(__import__("shutil").rmtree, self.directory, True)

    def test_malformed_options_are_refused_before_any_review(self):
        cases = {"record_batch_calls_unsupported": ["--batch-size", "claude_code.subscription=4", "--record",
                                                    str(Path(self.directory) / "record.json")],
                 "invalid_option": ["--batch-size", "no.such.installation=4"]}
        cases_more = (["--batch-size", "claude_code.subscription=40"], ["--exclude-installation", "codex.gpt-6-sol="],
                      ["--calibrate-only"], ["--quota-group-ceiling", "g=1", "--quota-group-ceiling", "g=2"])
        for code, extra in list(cases.items()) + [("invalid_option", extra) for extra in cases_more]:
            with self.subTest(extra=extra):
                command, options = self.options(*extra)
                with self.assertRaises(CandidateReviewError) as caught:
                    command.run(options)
                self.assertEqual(caught.exception.code, code)

    def test_without_model_authority_no_credential_resolver_reaches_an_engine(self):
        from candidate_review.reviewers import Availability
        command, options = self.options("--exclude-installation", "codex.gpt-6-sol=the allowance is spent")
        contexts = []

        def build(installation, policy, context):
            contexts.append(context)
            engine = mock.Mock()
            engine.availability.return_value = Availability(False, "offline", "", {}, "engine_unavailable")
            return engine

        with mock.patch.object(command, "listed_model_versions", side_effect=AssertionError("no provider listing")), \
                mock.patch.object(command, "_operator_resolver", side_effect=AssertionError("no credential")), \
                mock.patch.object(command.engines, "build_reviewer", side_effect=build):
            summary = command.run(options)
        self.assertTrue(contexts)
        self.assertTrue(all(context.credential_resolver is None for context in contexts))
        self.assertEqual(summary["ineligible"]["codex.gpt-6-sol"], "the allowance is spent")
        self.assertEqual(summary["run_limits"]["excluded_installations"],
                         {"codex.gpt-6-sol": "the allowance is spent"})


class BatchLedgerTest(unittest.TestCase):
    def _ledger_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": batch_approving, "b": batch_approving, "c": batch_approving},
                              families=("zhipu", "deepseek", "openai"))
            run(harness, requests(ITEMS[:2]))
            return [json.loads(line) for line in harness.ledger_path.read_text().splitlines()]

    def _load(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows))
            return ReviewLedger(path)

    def test_a_batch_ledger_reads_back_with_every_verdict(self):
        ledger = self._load(self._ledger_rows())
        self.assertEqual(len(ledger.batch_calls()), 3)
        self.assertEqual(len(ledger.verdicts()), 6)

    def test_a_batch_verdict_needs_its_member_to_name_a_verdict_and_the_exact_model(self):
        rows = self._ledger_rows()
        call = next(index for index, row in enumerate(rows) if row["record_type"] == BATCH_CALL_RECORD)
        changes = {"verdict_without_verified_call": lambda row: row["members"][0].update(outcome="invalid_response"),
                   "reviewer_identity_unverified": lambda row: row.update(reported_model="another-model")}
        for code, change in changes.items():
            with self.subTest(code=code):
                changed = json.loads(json.dumps(rows))
                change(changed[call])
                with self.assertRaises(CandidateReviewError) as caught:
                    self._load(changed)
                self.assertEqual(caught.exception.code, code)


if __name__ == "__main__":
    unittest.main()
