"""Summarize the pilot's trial records into results/summary.json and print the report tables.

It reads only results/trials/*.json and results/ledger.jsonl. Every attempt is
listed. Attempts with a provider failure are shown and left out of the per-arm
comparison, as the frozen design says. Usage: python3 summarize.py
"""
from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
TASK_ORDER = ("a-cachetools-tlru", "b-dotenv-backslash", "c-spaceship-titanic")


def secondary(record):
    score = record["score"]
    if record["task"] == "a-cachetools-tlru":
        hidden = score.get("hidden_tlru") or {}
        return {"name": "TLRUCache tests passed of 34", "value": hidden.get("passed", 0)}
    if record["task"] == "b-dotenv-backslash":
        parser = score.get("hidden_parser_tests") or {}
        return {"name": "upstream parser tests passed of 56", "value": parser.get("passed", 0)}
    return {"name": "held-out accuracy", "value": score.get("accuracy")}


def cached_tokens(ledger, step_id):
    """Cached input tokens from the provider's own usage object in the ledger. The trial records' field
    `cached_input_tokens` says "not reported by the provider", which is wrong: the runner kept only three usage
    fields, while the ledger holds the whole usage object, including prompt_tokens_details.cached_tokens."""
    total = missing = 0
    for line in ledger:
        if line.get("trial_id") == step_id and line.get("event") == "completed":
            details = (line.get("usage_reported") or {}).get("prompt_tokens_details") or {}
            if isinstance(details.get("cached_tokens"), int):
                total += details["cached_tokens"]
            else:
                missing += 1
    return total, missing


def row(record, ledger):
    requests = record["model_requests"]
    cached, cached_missing = cached_tokens(ledger, record["meter_step_id"])
    events = record["events"]
    baltor = record.get("baltor") or {}
    return {
        "attempt_id": record["attempt_id"], "plan_index": record["plan_index"], "task": record["task"],
        "arm": record["arm"], "repetition": record["repetition"], "accepted": record["accepted"],
        "secondary": secondary(record), "physical_requests": requests["physical"],
        "refused_requests": requests["refused"], "prompt_tokens": requests["usage_totals"].get("prompt_tokens"),
        "completion_tokens": requests["usage_totals"].get("completion_tokens"),
        "requests_missing_usage": requests["requests_missing_usage"],
        "cached_prompt_tokens": cached, "requests_missing_cached_count": cached_missing,
        "mean_prompt_tokens_per_request": round(requests["usage_totals"].get("prompt_tokens", 0)
                                                / requests["physical"]) if requests["physical"] else None,
        "elapsed_seconds": record["elapsed_total_seconds"],
        "setup_seconds": (record.get("setup") or {}).get("elapsed_seconds"),
        "provider_seconds": round(requests["provider_elapsed_ms"] / 1000, 1),
        "stopped_by_runner": record["harness"]["stopped_by_runner"], "exit_status": record["harness"]["exit_status"],
        "tool_counts": events["tool_counts"], "tool_calls": sum(events["tool_counts"].values()),
        "baltor_searches": len(baltor.get("searches") or []), "baltor_reads": len(baltor.get("reads") or []),
        "baltor_skill_loads": sum(1 for load in baltor.get("skill_loads") or [] if load.get("name") == "baltor-library"),
        "baltor_client_commands": len(baltor.get("client_commands") or []),
        "baltor_abstained": baltor.get("abstained_from_baltor") if record["arm"] == "baltor" else None,
        "wrong_file_incidents": len(record["wrong_file_incidents"]),
        "changed_files": sorted(record["workspace_changes"]),
        "provider_failure_seen": record["provider_failure_seen"],
        "outcomes": requests["outcomes"],
    }


def main():
    records = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((RESULTS / "trials").glob("*.json"))]
    ledger = [json.loads(line) for line in (RESULTS / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if line]
    rows = sorted((row(record, ledger) for record in records), key=lambda item: (item["plan_index"], item["attempt_id"]))
    counted = [item for item in rows if not item["provider_failure_seen"]]
    by_cell = defaultdict(list)
    for item in counted:
        by_cell[(item["task"], item["arm"])].append(item)
    cells = []
    for task in TASK_ORDER:
        for arm in ("none", "baltor"):
            items = by_cell.get((task, arm), [])
            values = [item["secondary"]["value"] for item in items if item["secondary"]["value"] is not None]
            cells.append({"task": task, "arm": arm, "attempts": len(items),
                          "accepted": sum(item["accepted"] for item in items),
                          "secondary_name": items[0]["secondary"]["name"] if items else None,
                          "secondary_values": values,
                          "physical_requests": [item["physical_requests"] for item in items],
                          "prompt_tokens": [item["prompt_tokens"] for item in items],
                          "completion_tokens": [item["completion_tokens"] for item in items],
                          "cached_prompt_tokens": [item["cached_prompt_tokens"] for item in items],
                          "elapsed_seconds": [item["elapsed_seconds"] for item in items],
                          "mean_prompt_tokens_per_request": round(statistics.mean(
                              item["mean_prompt_tokens_per_request"] for item in items)) if items else None,
                          "baltor_abstentions": sum(1 for item in items if item["baltor_abstained"]),
                          "cap_stops": sum(1 for item in items if item["stopped_by_runner"] == "request_cap_reached"),
                          "wrong_file_incidents": sum(item["wrong_file_incidents"] for item in items)})
    sent = [line for line in ledger if line.get("event") == "sent"]
    summary = {"record_type": "comparison_pilot_summary/v1", "attempts": rows, "cells": cells,
               "ledger": {"physical_requests": len(sent),
                          "by_arm": dict(Counter(line.get("arm") for line in sent)),
                          "refused": sum(1 for line in ledger if line.get("event") == "refused"),
                          "outcomes": dict(Counter(line.get("outcome") for line in ledger
                                                   if line.get("event") == "completed")),
                          "requests_missing_usage": sum(1 for line in ledger if line.get("event") == "completed"
                                                        and not line.get("usage"))},
               "ceiling": 300}
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print("| Order | Attempt | Accepted | Secondary | Requests | Input tokens (cached) | Output tokens | Seconds | Stop | Baltor use |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for item in rows:
        use = "" if item["arm"] == "none" else ("abstained" if item["baltor_abstained"] else
                                                f"{item['baltor_searches']} searches, {item['baltor_reads']} reads")
        print(f"| {item['plan_index']} | {item['attempt_id']} | {'yes' if item['accepted'] else 'no'} | "
              f"{item['secondary']['value']} | {item['physical_requests']} | {item['prompt_tokens']:,} ({item['cached_prompt_tokens']:,}) | "
              f"{item['completion_tokens']:,} | {item['elapsed_seconds']:.0f} | {item['stopped_by_runner'] or 'finished'} | {use} |")
    print()
    for cell in cells:
        print(cell["task"], cell["arm"], "accepted", cell["accepted"], "of", cell["attempts"], cell["secondary_values"],
              "requests", cell["physical_requests"], "tokens", cell["prompt_tokens"], "cached", cell["cached_prompt_tokens"],
              "per request",
              cell["mean_prompt_tokens_per_request"], "seconds", cell["elapsed_seconds"])
    print(json.dumps(summary["ledger"]))


if __name__ == "__main__":
    main()
