"""Create one verified saved-run bundle for Studio browser acceptance."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from loop_engine.core.run_history import RunHistory, bind_product_outcome
from loop_engine.loop.recursive_loop import LoopLedger


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-dir", required=True, type=Path)
    args = parser.parse_args()
    runs_dir = args.runs_dir.resolve()
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_id = "studio-browser-fixture"
    ledger = LoopLedger()
    ledger.record(loop_id="loop1", event="init",
                  goal="Create and verify a Studio fixture.",
                  framework="five_step", power="light",
                  relationship_kind="starting")
    ledger.record(loop_id="loop1", event="run_step", step="act",
                  mode="deterministic", output="artifact created",
                  confidence=1.0, accepted=True)
    ledger.record(loop_id="loop1", event="run_step", step="verify",
                  mode="deterministic", output="artifact verified",
                  confidence=1.0, accepted=True)
    ledger.record(loop_id="loop1", event="terminal", reason="done")
    history = RunHistory.from_ledger(ledger.events, run_id=run_id)
    history.commit()
    history.save(str(runs_dir))
    workspace = runs_dir / "fixture-workspace"
    workspace.mkdir()
    artifact = workspace / "result.txt"
    artifact.write_text("verified Studio result\n", encoding="utf-8")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    bind_product_outcome(str(runs_dir), run_id, {
        "record_type": "solve_outcome/v3", "run_id": run_id,
        "terminal_code": "COMPLETED_VERIFIED",
        "status": "COMPLETED_VERIFIED", "solved": True,
        "summary": "Verified Studio browser fixture.", "failure_code": "",
        "verification": {"passed": True, "verdict": "accept"},
        "artifacts": [{
            "path": str(artifact), "media_type": "text/plain",
            "byte_count": artifact.stat().st_size, "digest": digest,
            "verified": True, "format_valid": True,
        }],
        "workspace": str(workspace), "limitations": [],
        "next_action": "Inspect the verified artifact.",
        "graph_digest": "b" * 64,
        "selected_canvas": {
            "mermaid": "flowchart TD\n  A[solution.component] --> B[result]",
            "loop_graph": {"vertices": [{
                "vertex_id": "solution.component", "purpose": "component",
                "operation_ref": "fixture.write", "selected_mode": "deterministic",
            }]},
        },
    })
    print(json.dumps({"run_id": run_id, "runs_dir": str(runs_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
