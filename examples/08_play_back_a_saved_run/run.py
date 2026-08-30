"""Record a nested run, then play back the saved Run History without rerunning."""

import argparse
import os
import time

from loop_engine import LoopLedger
from loop_engine.loop.recursive_loop import Loop, LoopConfig, StepOutcome
from loop_engine.core.run_history import RunHistory
from loop_engine.code_nodes.run_playback import playback
from loop_engine.code_nodes.loop_report import report_from_run, write_report


def record_run(runs_dir):
    ledger = LoopLedger()
    starting_loop = Loop(
        "check inventory before the morning shipment",
        LoopConfig(framework="custom",
                   custom_steps=("load", "check", "route", "verify"),
                   allowable_modes=("deterministic",), power="standard"),
        ledger=ledger,
    )

    def handler(loop, step, context):
        if loop.depth > 0:
            return StepOutcome(f"{step}: warehouse count confirmed")
        if step == "check" and "check:spawned" not in context:
            return StepOutcome("confirm warehouse stock",
                               spawn_goal="confirm warehouse stock")
        if step == "route":
            return StepOutcome("hold SKU-442; release the other 18 orders")
        return StepOutcome(f"{step}: complete")

    starting_loop.run(handler=handler, max_steps=20)
    run_id = (time.strftime("inventory-%Y%m%d-%H%M%S-")
              + f"{time.time_ns() % 1_000_000_000:09d}")
    run_history = RunHistory.from_ledger(ledger.events, run_id=run_id)
    run_history.commit()
    run_history.save(runs_dir)
    return run_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-dir", default="example-output/runs")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--studio-port", type=int, default=8765)
    args = parser.parse_args()
    os.makedirs(args.runs_dir, exist_ok=True)
    run_id = args.run_id or record_run(args.runs_dir)
    run_history = RunHistory.load(args.runs_dir, run_id)
    chain = run_history.verify_chain()
    if not chain["intact"]:
        raise SystemExit(f"saved chain is broken at {chain['broken_at']}")

    print(f"PLAYBACK: {run_id} ({chain['events']} events, chain intact)")
    for line in playback(run_history.event_log):
        print(line)

    report = report_from_run(args.runs_dir, run_id)
    report_path = os.path.join(args.runs_dir, run_id, "report.html")
    write_report(report, report_path)
    print(f"\nStatic report: {report_path}")
    print("Interactive playback:")
    print(f"  loop-engine studio --port {args.studio_port} "
          f"--runs-dir {args.runs_dir}")
    if args.studio_port:
        print(f"  http://127.0.0.1:{args.studio_port}/app/runs/"
              f"{run_id}/playback")
    else:
        print("  Studio prints the selected local address.")


if __name__ == "__main__":
    main()
