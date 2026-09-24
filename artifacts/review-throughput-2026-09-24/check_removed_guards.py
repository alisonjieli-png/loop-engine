"""Removed-guard controls for the review engines, batched review and run limits of S-6.63.

Each control removes one guard from a scratch checkout, a detached worktree of
this checkout's commit that the script creates and removes again, and runs the
named checks there; this checkout is never changed. A control is detected when
the named checks pass on the real source and fail with the guard removed, and
the file is restored to its committed bytes after each control. No model is
called: every check uses fixture reviewers, fake programs or a fixture
transport.

    python artifacts/review-throughput-2026-09-24/check_removed_guards.py \\
        --output artifacts/review-throughput-2026-09-24/removed-guards-DATE.json
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable
RECORD_TYPE = "removed_guard_controls/v1"
ENGINES = "tools.test_candidate_review_engines.CommandLineEngineTest."
BINDING = "tools.test_candidate_review_binding_engine.BindingEngineTest."
GENERATOR = "tools.test_generate_original_native_provider_binding.ProviderBindingTest."
BATCH = "tools.test_candidate_review_batching."
ADAPTER = "tools.test_native_proposals_from_overnight_candidates.AdapterTest."

#: (name, file under tools/, exact text removed, replacement, checks that must fail without it)
CONTROLS = (
    ("codex session model must be the pinned model", "candidate_review/reviewers/command_line.py",
     "    if model != installation.model:\n", "    if False:\n",
     [ENGINES + "test_codex_session_record_that_disagrees_or_is_missing_is_refused"]),
    ("codex session record must name its thread once", "candidate_review/reviewers/command_line.py",
     "    if headers != [thread_id]:\n", "    if False:\n",
     [ENGINES + "test_codex_session_record_that_disagrees_or_is_missing_is_refused"]),
    ("codex session protocol refuses --ephemeral", "candidate_review/reviewers/command_line.py",
     "        if protocol == CODEX_SESSION_PROTOCOL and EPHEMERAL in self.arguments:\n",
     "        if False:\n", [ENGINES + "test_session_protocol_needs_the_record_and_a_pinned_model"]),
    ("a model-reporting protocol needs the pinned model", "candidate_review/reviewers/command_line.py",
     "        if protocol in MODEL_PINNED_PROTOCOLS and not model_pinned(self.arguments):\n",
     "        if False:\n", [ENGINES + "test_session_protocol_needs_the_record_and_a_pinned_model"]),
    ("a binding must declare the purpose it is used for", "generate_original_native_candidates.py",
     "    if purpose not in settings.purposes:\n", "    if False:\n",
     [GENERATOR + "test_a_binding_serves_only_the_purposes_it_declares",
      BINDING + "test_refusals_before_the_credential_is_read"]),
    ("the binding engine keeps the allocation within the measured capacity", "candidate_review/reviewers/binding.py",
     "        if binding.capability.declared_maximum is None or binding.capability.declared_maximum < allocation:\n",
     "        if False:\n", [BINDING + "test_refusals_before_the_credential_is_read"]),
    ("a batch answer must come from the pinned model", "candidate_review/panel.py",
     "            if attempt.outcome == ANSWERED and not answering_model_matches(installation, attempt):\n"
     "                attempt = replace(attempt, outcome=MODEL_IDENTITY_MISMATCH, text=\"\",\n"
     "                                  error_detail=\"reviewer_answering_model_mismatch\")\n"
     "            results, error_code = None, \"\"\n",
     "            results, error_code = None, \"\"\n",
     [BATCH + "BatchedPanelTest.test_a_batch_answer_from_another_model_counts_for_no_item"]),
    ("no call below the quorum without a written reason", "candidate_review/panel.py",
     "            if not every and not below and distinct_families([item.installation_id for item in candidates],\n",
     "            if False and distinct_families([item.installation_id for item in candidates],\n",
     [BATCH + "RunLimitTest.test_below_the_quorum_each_reachable_family_is_asked_once_and_the_rule_holds"]),
    ("a batch verdict needs its member row to name a verdict", "candidate_review/ledger.py",
     "        return (member is not None and member[\"outcome\"] == \"verdict\"\n",
     "        return (member is not None\n",
     [BATCH + "BatchLedgerTest.test_a_batch_verdict_needs_its_member_to_name_a_verdict_and_the_exact_model"]),
    ("a batch call with a verdict needs the exact reported model", "candidate_review/ledger.py",
     "        if row[\"record_type\"] == BATCH_CALL_RECORD and any(member[\"outcome\"] == \"verdict\" for member in members) \\\n",
     "        if False and any(member[\"outcome\"] == \"verdict\" for member in members) \\\n",
     [BATCH + "BatchLedgerTest.test_a_batch_verdict_needs_its_member_to_name_a_verdict_and_the_exact_model"]),
    ("a record with batch calls cannot be written as the dated review record", "review_catalogue_candidates.py",
     "    if options.record and any(size > 1 for size in batch_sizes.values()):\n",
     "    if False:\n", [BATCH + "CommandOptionsTest.test_malformed_options_are_refused_before_any_review"]),
    ("without model authority no credential resolver reaches an engine", "review_catalogue_candidates.py",
     "credential_resolver=_operator_resolver() if options.authorize_model_calls else None)",
     "credential_resolver=_operator_resolver())",
     [BATCH + "CommandOptionsTest.test_without_model_authority_no_credential_resolver_reaches_an_engine"]),
    ("the adapter reads only a committed attribution", "native_proposals_from_overnight_candidates.py",
     "    if not listed.strip() or _git(repository, \"show\", f\"{revision}:{relative}/attribution.json\") != attribution_raw:\n",
     "    if False:\n", [ADAPTER + "test_an_uncommitted_attribution_is_refused"]),
    ("the adapter leaves out bytes changed after attribution", "native_proposals_from_overnight_candidates.py",
     "        if digest(raw) != row[\"sha256\"]:\n", "        if False:\n",
     [ADAPTER + "test_proposals_convert_placed_kinds_and_leave_out_the_rest_with_reasons"]),
)


def scratch_root(directory: Path, revision: str) -> Path:
    """A detached worktree of the commit under test; it makes no branch."""
    root = directory / "checkout"
    subprocess.run(["git", "-C", str(ROOT), "worktree", "add", "--quiet", "--detach", str(root), revision],
                   check=True, capture_output=True, text=True)
    return root


def run_checks(root: Path, names) -> dict:
    environment = {"HOME": os.environ.get("HOME", ""), "PATH": "/usr/local/bin:/usr/bin:/bin",
                   "LANG": "C.UTF-8", "PYTHONPATH": "src:tools", "PYTHONDONTWRITEBYTECODE": "1",
                   "TMPDIR": os.environ.get("TMPDIR", tempfile.gettempdir())}
    finished = subprocess.run([PYTHON, "-m", "unittest", *names], cwd=root, env=environment, capture_output=True,
                              text=True, timeout=900, check=False)
    summary = [line for line in finished.stderr.splitlines() if line.startswith(("Ran ", "OK", "FAILED"))]
    return {"passed": finished.returncode == 0, "summary": summary}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args(argv)
    revision = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    rows = []
    with tempfile.TemporaryDirectory(prefix="removed-guards-") as directory:
        root = scratch_root(Path(directory), revision)
        try:
            rows = [control(root, *row) for row in CONTROLS]
        finally:
            subprocess.run(["git", "-C", str(ROOT), "worktree", "remove", "--force", str(root)], check=False,
                           capture_output=True, text=True)
    record = {"record_type": RECORD_TYPE, "revision": revision,
              "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
              "controls": rows, "detected": sum(1 for row in rows if row.get("detected")), "total": len(rows)}
    options.output.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"detected": record["detected"], "total": record["total"]}))
    return 0 if record["detected"] == record["total"] else 1


def control(root: Path, name, relative, before, after, checks) -> dict:
    """One guard removed, its checks run with and without it, and the file restored."""
    path = root / "tools" / relative
    source = path.read_text(encoding="utf-8")
    if source.count(before) != 1:
        return {"control": name, "file": "tools/" + relative, "error": "the guard text is not unique"}
    real = run_checks(root, checks)
    path.write_text(source.replace(before, after), encoding="utf-8")
    try:
        removed = run_checks(root, checks)
    finally:
        path.write_text(source, encoding="utf-8")
    return {"control": name, "file": "tools/" + relative, "checks": checks,
            "passes_with_the_guard": real["passed"], "fails_without_the_guard": not removed["passed"],
            "detected": real["passed"] and not removed["passed"],
            "with_guard": real["summary"], "without_guard": removed["summary"]}


if __name__ == "__main__":
    raise SystemExit(main())
