"""Offline regressions for exact candidate bytes and honestly reported reviewer facts."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from candidate_review import prechecks, reviewers
from candidate_review.records import CandidateReviewError
from candidate_review.reviewers import command_line
from test_candidate_review_engines import (
    CODEX_SUCCESS,
    _command,
    _installation,
    _program,
)
from test_candidate_review_panel import (
    Harness,
    _only,
    _request,
    answer,
    approving,
    attempt,
)
from test_candidate_review_prechecks import (
    _builtin_engines,
    _codes,
    _context,
)


class CandidateBodyBindingTest(unittest.TestCase):
    def test_same_length_changed_bytes_are_refused(self):
        request = _request()
        changed = request.replaced(body=request.body.replace(b"Review", b"review", 1))
        self.assertEqual(len(changed.body), len(request.body))
        result = prechecks.run_prechecks(changed, _builtin_engines(), _context())
        self.assertIn("body_digest_mismatch", _codes(result))

    def test_declared_byte_size_must_be_an_exact_nonnegative_integer(self):
        request = _request()
        for wrong in (request.body_size_bytes + 1, None, True, float(request.body_size_bytes), "100"):
            with self.subTest(size=wrong):
                item = request.item
                item["reference"]["size_bytes"] = wrong
                result = prechecks.run_prechecks(request.replaced(item=item), _builtin_engines(), _context())
                self.assertIn("body_size_mismatch", _codes(result))

    def test_missing_malformed_or_changed_digest_is_refused(self):
        request = _request()
        for wrong in (None, "", "0" * 64, True, {"digest": request.body_sha256}):
            with self.subTest(digest=wrong):
                item = request.item
                item["reference"]["digest"] = wrong
                result = prechecks.run_prechecks(request.replaced(item=item), _builtin_engines(), _context())
                self.assertIn("body_digest_mismatch", _codes(result))

    def test_wrong_binding_reaches_no_reviewer_and_reserves_no_calls(self):
        request = _request()
        item = request.item
        item["reference"]["digest"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": approving, "b": approving, "c": approving},
                              families=("zhipu", "deepseek", "openai"))
            result = harness.run([request.replaced(item=item)])
        self.assertEqual(_only(result).outcome, "refused_before_review")
        self.assertEqual(result.calls, [])
        self.assertEqual(result.budget["calls_reserved"], 0)

    def test_valid_binding_still_reaches_the_independent_reviewers(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = Harness(directory, {"a": approving, "b": approving, "c": approving},
                              families=("zhipu", "deepseek", "openai"))
            result = harness.run([_request()])
        self.assertEqual(_only(result).outcome, "approved")
        self.assertEqual(len(result.calls), 3)


class CommandReportedFactsTest(unittest.TestCase):
    def test_claude_nonzero_exit_never_counts_a_success_shaped_response(self):
        expected = _installation("claude_code.bare")
        row = {"is_error": False, "result": "an answer", "duration_api_ms": 10,
               "modelUsage": {expected.model: {}}, "usage": {"output_tokens": 7}}
        result = command_line.read_claude(json.dumps(row), "process ended unexpectedly", 1,
                                          expected, "claude", 0.1)
        self.assertNotEqual(result.outcome, reviewers.ANSWERED)
        self.assertEqual(result.text, "")
        self.assertEqual(result.usage.output_tokens, 7)

    def test_codex_without_identity_reporting_is_unavailable_before_a_review_call(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = _command("codex.gpt-6-sol", _program(Path(directory), "codex", CODEX_SUCCESS),
                              output_protocol="codex_exec_jsonl")
            available = engine.availability()
        self.assertFalse(available.available)
        self.assertEqual(available.reason_code, reviewers.MODEL_IDENTITY_MISMATCH)
        self.assertEqual(available.model_version, {})

    def test_codex_does_not_promote_requested_model_to_reported_identity(self):
        events = [
            {"type": "thread.started", "thread_id": "fixture"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "an answer"}},
            {"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 3}},
        ]
        attempt = command_line.read_codex("\n".join(json.dumps(row) for row in events), "", 0,
                                          _installation("codex.gpt-6-sol"), "codex", 0.1)
        self.assertEqual(attempt.reported_model, "")
        self.assertEqual(attempt.outcome, reviewers.MODEL_IDENTITY_MISMATCH)
        self.assertEqual(attempt.usage.total, 13)
        self.assertIn("answering model", attempt.error_detail)

    def test_claude_missing_usage_stays_unknown_even_when_no_model_used(self):
        row = {"is_error": True, "result": "Not logged in", "duration_api_ms": 0, "modelUsage": {}}
        attempt = command_line.read_claude(json.dumps(row), "", 1, _installation("claude_code.bare"),
                                           "claude", 0.1)
        self.assertEqual(attempt.physical_model_calls, 0)
        self.assertEqual(attempt.usage, reviewers.UNKNOWN_USAGE)

    def test_claude_explicit_zero_usage_remains_reported_zero(self):
        row = {"is_error": True, "result": "Not logged in", "duration_api_ms": 0, "modelUsage": {},
               "usage": {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0,
                         "cache_creation_input_tokens": 0}}
        attempt = command_line.read_claude(json.dumps(row), "", 1, _installation("claude_code.bare"),
                                           "claude", 0.1)
        self.assertEqual(attempt.usage.total, 0)
        self.assertEqual(attempt.usage.source, reviewers.COMMAND_LINE_REPORTED)

    def test_claude_partial_usage_is_not_replaced_with_zeros(self):
        row = {"is_error": True, "result": "Not logged in", "duration_api_ms": 0, "modelUsage": {},
               "usage": {"output_tokens": 7}}
        attempt = command_line.read_claude(json.dumps(row), "", 1, _installation("claude_code.bare"),
                                           "claude", 0.1)
        self.assertIsNone(attempt.usage.input_tokens)
        self.assertEqual(attempt.usage.output_tokens, 7)

    def test_claude_missing_and_mismatched_reported_identity_do_not_count(self):
        expected = _installation("claude_code.bare")
        for models in ({}, {"another-model": {}}, {expected.model: {}, "another-model": {}}):
            with self.subTest(models=models):
                row = {"is_error": False, "result": "an answer", "duration_api_ms": 10, "modelUsage": models}
                attempt = command_line.read_claude(json.dumps(row), "", 0, expected, "claude", 0.1)
                self.assertEqual(attempt.outcome, reviewers.MODEL_IDENTITY_MISMATCH)
                self.assertEqual(attempt.reported_model, ",".join(sorted(models)))

    def test_claude_genuine_reported_identity_is_preserved(self):
        expected = _installation("claude_code.bare")
        row = {"is_error": False, "result": "an answer", "duration_api_ms": 10,
               "modelUsage": {expected.model: {}}}
        attempt = command_line.read_claude(json.dumps(row), "", 0, expected, "claude", 0.1)
        self.assertEqual(attempt.outcome, reviewers.ANSWERED)
        self.assertEqual(attempt.reported_model, expected.model)


class FixedPanelIdentityTest(unittest.TestCase):
    def test_unreported_or_wrong_model_cannot_satisfy_quorum_through_a_swapped_engine(self):
        for wrong in ("", "unexpected-model"):
            def invalid(prompt, number, reported_model=wrong):
                return replace(attempt(answer(prompt)), reported_model=reported_model)

            with self.subTest(reported_model=wrong), tempfile.TemporaryDirectory() as directory:
                harness = Harness(directory, {"a": invalid, "b": invalid, "c": invalid},
                                  families=("zhipu", "deepseek", "openai"))
                try:
                    result = harness.run([_request()])
                except CandidateReviewError as error:
                    self.fail(f"the panel must record the refusal before the ledger rejects an invalid call: {error.code}")
                self.assertNotEqual(_only(result).outcome, "approved")
                self.assertEqual(_only(result).verdicts, [])
                self.assertEqual(result.calls[0]["outcome"], reviewers.MODEL_IDENTITY_MISMATCH)


if __name__ == "__main__":
    unittest.main()
