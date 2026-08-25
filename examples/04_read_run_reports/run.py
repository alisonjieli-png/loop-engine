"""Run an incident investigation and write readable reports.

Run:
    python3 examples/04_read_run_reports/run.py
"""

import argparse
import os

from loop_engine import LoopLedger
from loop_engine.loop.recursive_loop import Loop, LoopConfig, StepOutcome
from loop_engine.code_nodes.loop_report import (
    report_from_ledger, render_text, write_report)


def incident_run():
    ledger = LoopLedger()
    root = Loop(
        "restore checkout after a payment error spike",
        LoopConfig(framework="custom",
                   custom_steps=("inspect", "diagnose", "mitigate", "verify"),
                   allowable_modes=("deterministic",), power="standard"),
        ledger=ledger,
    )

    def handle(loop, step, context):
        if loop.depth > 0:
            child_output = {
                "inspect": "gateway errors rose from 0.2% to 8.4%",
                "diagnose": "failures start after credential rotation",
                "mitigate": "validated the previous credential in staging",
                "verify": "20 test charges passed",
            }[step]
            return StepOutcome(child_output, mode="deterministic", confidence=0.95)
        if step == "inspect":
            return StepOutcome("checkout failures exceed the alert threshold")
        if step == "diagnose" and "diagnose:child" not in context:
            return StepOutcome("inspect the payment gateway",
                               spawn_goal="check the payment gateway")
        if step == "diagnose":
            return StepOutcome(f"gateway finding: {context['diagnose:child']}")
        if step == "mitigate":
            return StepOutcome("restore the last verified credential")
        return StepOutcome("checkout error rate returned below 0.5%")

    root.run(handler=handle, max_steps=20)
    return ledger


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="example-output/incident-report")
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    ledger = incident_run()
    report = report_from_ledger(ledger.events, run_id="checkout-incident")
    paths = {
        "markdown": os.path.join(args.output_dir, "report.md"),
        "html": os.path.join(args.output_dir, "report.html"),
        "json": os.path.join(args.output_dir, "report.json"),
    }
    for path in paths.values():
        write_report(report, path)

    print(render_text(report))
    print("\nFILES")
    for label, path in paths.items():
        print(f"  {label:<8} {path}")


if __name__ == "__main__":
    main()
