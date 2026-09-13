"""Audit a saved complete-solve run without another provider call.

This development report compares returned gateway accounting with canonical
Run History and retains degraded-record diagnostics. It never upgrades the
solver's task verdict or treats matching counts as proof of model quality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from loop_engine.core.run_history import load_saved_run_bundle


ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outcome", type=Path, required=True)
    parser.add_argument("--runs-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    output = args.out.resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise SystemExit("audit output must be a new file inside loop-engine")
    raw = args.outcome.read_bytes()
    outcome = json.loads(raw)
    bundle = load_saved_run_bundle(str(args.runs_dir.resolve()), outcome["run_id"])
    events = bundle.history.event_log
    calls = [event for event in events if event.event_type == "model_invocation"]
    attempts = [attempt for result in outcome["model_usage"] for attempt in result["attempts"]
                if attempt.get("loop_id")]
    ids = [attempt["loop_id"] for attempt in attempts]
    observed_ids = [event.loop_id for event in calls]
    usage_known = all(attempt.get("input_tokens") is not None and attempt.get("output_tokens") is not None
                      for attempt in attempts)
    diagnostics = [{"event_sequence": event.sequence_number, "loop_id": event.loop_id,
                    "diagnostic_code": event.detail.get("diagnostic_code"),
                    "diagnostic": event.detail.get("diagnostic")}
                   for event in events if isinstance(event.detail, dict)
                   and "degraded" in str(event.detail.get("diagnostic_code", ""))]
    checks = {
        "history_chain_intact": bundle.history.verify_chain()["intact"],
        "known_call_count_matches_history": outcome["model_calls_known_subtotal"] == len(calls) == len(attempts),
        "physical_call_identities_match_without_duplicates": len(ids) == len(set(ids))
            and len(observed_ids) == len(set(observed_ids)) and set(ids) == set(observed_ids),
        "all_physical_calls_used_ollama_cloud": bool(attempts)
            and all(attempt["provider"] == "ollama_cloud" for attempt in attempts)
            and all(event.detail.get("provider") == "ollama_cloud" for event in calls),
        "reported_accounting_complete": outcome["model_call_accounting_complete"] is True,
        "all_provider_usage_known": usage_known,
    }
    report = {"record_type": "saved_harness_solve_audit/v1", "run_id": outcome["run_id"],
        "outcome_path": str(args.outcome.resolve()), "outcome_sha256": hashlib.sha256(raw).hexdigest(),
        "runs_directory": str(args.runs_dir.resolve()), "terminal_code": outcome["terminal_code"],
        "solved": outcome["solved"], "physical_model_calls": len(attempts), "history_events": len(events),
        "input_tokens": sum(a["input_tokens"] for a in attempts) if usage_known else None,
        "output_tokens": sum(a["output_tokens"] for a in attempts) if usage_known else None,
        "cost_usd": None, "cost_state": "unknown", "elapsed_seconds": outcome["elapsed_seconds"],
        "checks": checks, "accounting_checks_passed": all(checks.values()),
        "degraded_record_diagnostics": diagnostics,
        "independent_checks": [{"status": item["report"]["status"], "notes": item["report"]["notes"],
                                "report_digest": item["report"].get("report_digest")}
                               for item in outcome["verification"].get("independent_checks", [])],
        "scope": "Saved-run accounting audit, not a task evaluator or full-system benchmark."}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["accounting_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
