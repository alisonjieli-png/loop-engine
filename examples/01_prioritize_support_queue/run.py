"""Prioritize a customer support queue with a deterministic loop.

Run:
    python3 examples/01_prioritize_support_queue/run.py

This example uses no model, network, or external service.
"""

from loop_engine import LoopLedger
from loop_engine.loop.encapsulate import as_practitioner_loop
from loop_engine.code_nodes.loop_report import report_from_ledger, render_text
from loop_engine.code_nodes.public_examples import (
    SUPPORT_TICKETS, prioritize_support_queue)


def main():
    ledger = LoopLedger()
    result = as_practitioner_loop(
        "prioritize the customer support queue",
        lambda: prioritize_support_queue(SUPPORT_TICKETS),
        ledger=ledger,
    )

    print("NEXT SUPPORT WORK")
    for position, ticket in enumerate(result["value"], start=1):
        print(f"{position}. {ticket['id']}  score={ticket['priority_score']:>3}  "
              f"{ticket['summary']}")
    print(f"\nmode: {result.get('mode', 'deterministic')}")
    print(f"model calls: {result['model_calls']}")
    print(f"logged events: {len(ledger.events)}\n")
    print(render_text(report_from_ledger(
        ledger.events, run_id="support-queue-priority")))


if __name__ == "__main__":
    main()
