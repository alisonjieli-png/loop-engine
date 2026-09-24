"""Summarize one generation run's journal: every call with its outcome.

Reads the run folder's journal and prints one row per completed call (model,
usage, outcome and the admission record), then totals. It reads records only;
it never calls a provider or changes a file.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def summarize(run: Path) -> dict:
    config = json.loads((run / "run.json").read_text(encoding="utf-8"))
    rows, dispatched = [], 0
    for line in (run / "journal.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["kind"] == "dispatch":
            dispatched += 1
            continue
        data = row["data"]
        admission = data["response_admission"] or {}
        rows.append({"method_id": row["method_id"], "attempt": row["attempt"], "status": data["status"],
                     "error_code": data["error_code"], "reported_model": data["reported_model"],
                     "input_tokens": data["input_tokens"], "output_tokens": data["output_tokens"],
                     "elapsed_seconds": data["elapsed_seconds"],
                     "admitted": admission.get("admitted"), "admission_strategy": admission.get("strategy"),
                     "admission_failure": admission.get("failure_code"),
                     "package_digest": data["package_digest"]})
    admitted = sum(1 for row in rows if row["admitted"])
    prepared = sum(1 for row in rows if row["status"] == "candidate_prepared")
    return {"run": run.name, "model": config["model"], "producer_family": config["producer_family"],
            "draft_format": config["draft_format"], "call_ceiling": config["call_ceiling"],
            "dispatches": dispatched, "completions": len(rows), "admitted": admitted, "prepared": prepared,
            "admission_rate": f"{admitted}/{len(rows)}" if rows else "0/0",
            "known_input_tokens": sum(row["input_tokens"] for row in rows if row["input_tokens"] is not None),
            "known_output_tokens": sum(row["output_tokens"] for row in rows if row["output_tokens"] is not None),
            "calls_with_unknown_usage": sum(1 for row in rows
                                            if row["input_tokens"] is None or row["output_tokens"] is None),
            "usage_complete": all(row["input_tokens"] is not None and row["output_tokens"] is not None for row in rows),
            "elapsed_seconds": round(sum(row["elapsed_seconds"] for row in rows), 1), "calls": rows}


if __name__ == "__main__":
    print(json.dumps(summarize(Path(sys.argv[1])), indent=1))
