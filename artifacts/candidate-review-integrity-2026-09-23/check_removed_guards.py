"""Run offline regression tests against one removed guard at a time, without editing source."""
from __future__ import annotations

import hashlib
import inspect
import io
import json
import sys
import textwrap
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src")]

from candidate_review import panel, prechecks
from candidate_review.reviewers import command_line


def run_case(name):
    output = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromName("test_candidate_review_integrity." + name)
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    return {"passed": result.wasSuccessful(), "tests_run": result.testsRun,
            "failures": len(result.failures), "errors": len(result.errors), "output": output.getvalue()}


def replacement(module, function, old, new):
    source = textwrap.dedent(inspect.getsource(function))
    if source.count(old) != 1:
        raise ValueError("the mutant must replace exactly one source fragment")
    namespace = dict(module.__dict__)
    exec(compile(source.replace(old, new), "<removed-guard-control>", "exec"), namespace)  # noqa: S102 - fixed local test mutations
    return namespace[function.__name__]


def main():
    cases = [
        ("body_digest", prechecks, prechecks, "body_binding_findings",
         "if type(declared_digest) is not str or declared_digest != request.body_sha256:", "if False:",
         "CandidateBodyBindingTest.test_same_length_changed_bytes_are_refused"),
        ("body_size", prechecks, prechecks, "body_binding_findings",
         "if type(declared_size) is not int or declared_size != request.body_size_bytes:", "if False:",
         "CandidateBodyBindingTest.test_declared_byte_size_must_be_an_exact_nonnegative_integer"),
        ("codex_reported_identity", command_line, command_line, "read_codex",
         ('return ReviewerAttempt(MODEL_IDENTITY_MISMATCH, "", usage, 1, elapsed, None, "", command,\n'
          '                               CODEX_MODEL_UNREPORTED, ONE_TURN)'),
         'return ReviewerAttempt(ANSWERED, text, usage, 1, elapsed, None, installation.model, command, "", ONE_TURN)',
         "CommandReportedFactsTest.test_codex_does_not_promote_requested_model_to_reported_identity"),
        ("claude_unknown_usage", command_line, command_line, "read_claude",
         ('return failed(classify(detail), command, detail.strip()[:300], physical_model_calls=physical,\n'
          '                      elapsed_seconds=elapsed, usage=usage)'),
         ('return failed(classify(detail), command, detail.strip()[:300], physical_model_calls=physical,\n'
          '                      elapsed_seconds=elapsed, usage=Usage(0, 0, source=COMMAND_LINE_REPORTED))'),
         "CommandReportedFactsTest.test_claude_missing_usage_stays_unknown_even_when_no_model_used"),
        ("claude_multiple_models", command_line, command_line, "read_claude",
         "if set(models) != {installation.model}:", "if installation.model not in models:",
         "CommandReportedFactsTest.test_claude_missing_and_mismatched_reported_identity_do_not_count"),
        ("codex_availability", command_line, command_line.CommandLineReviewer, "_probe",
         "if self.reader is read_codex:", "if False:",
         "CommandReportedFactsTest.test_codex_without_identity_reporting_is_unavailable_before_a_review_call"),
        ("claude_process_exit", command_line, command_line, "read_claude",
         'if returncode != 0 or value.get("is_error") is not False:',
         'if value.get("is_error") is not False:',
         "CommandReportedFactsTest.test_claude_nonzero_exit_never_counts_a_success_shaped_response"),
        ("fixed_panel_identity", panel, panel, "answering_model_matches",
         "return type(attempt.reported_model) is str and attempt.reported_model == installation.model",
         "return True",
         "FixedPanelIdentityTest.test_unreported_or_wrong_model_cannot_satisfy_quorum_through_a_swapped_engine"),
    ]
    records = []
    for name, module, owner, method, old, new, test in cases:
        baseline = run_case(test)
        mutated = replacement(module, getattr(owner, method), old, new)
        with mock.patch.object(owner, method, mutated):
            control = run_case(test)
        records.append({"guard": name, "baseline": baseline, "removed_guard": control,
                        "detected": baseline["passed"] and control["failures"] > 0 and control["errors"] == 0})
    when = datetime.now(timezone.utc)
    record = {"created_at": when.isoformat(), "model_calls": 0, "source_mutations": 0,
              "sources": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in (Path(prechecks.__file__), Path(command_line.__file__), Path(panel.__file__),
                                       ROOT / "tools/test_candidate_review_integrity.py")},
              "results": records, "all_detected": all(row["detected"] for row in records)}
    output = Path(__file__).resolve().parent / ("removed-guards-" + when.strftime("%Y%m%dT%H%M%S%f") + ".json")
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(output), "guards": len(records), "all_detected": record["all_detected"]}))
    return 0 if record["all_detected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
