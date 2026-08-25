"""1 — The smallest real loop: give it a goal, get a result and a receipt.

    python examples/01_hello_loop.py

No API key, no network, no model. The point of this example is that a loop is
the *only* unit of execution: even a one-line piece of work runs inside an
envelope that records what happened.

Run it and you get two things back — the answer, and a ledger you can project
into a report. That pairing is the whole idea: work and its evidence are
produced together, not bolted on afterwards.
"""

from loop_engine import LoopLedger
from loop_engine.loop.encapsulate import as_practitioner_loop
from loop_engine.code_nodes.loop_report import report_from_ledger, render_text


def estimate_delivery_days(order):
    """Ordinary Python. Nothing here knows it is running inside a loop."""
    base = {"standard": 5, "express": 2, "overnight": 1}[order["speed"]]
    return base + (2 if order["international"] else 0)


def main():
    ledger = LoopLedger()

    result = as_practitioner_loop(
        "estimate delivery time for an international express order",
        lambda: estimate_delivery_days({"speed": "express",
                                        "international": True}),
        ledger=ledger)

    print(f"answer         : {result['value']} days")
    print(f"mode           : {result.get('mode', 'deterministic')}")
    print(f"model calls    : {result['model_calls']}")
    print(f"ledger events  : {len(ledger.events)}")
    print()

    # The same run, projected into something readable. Every figure in this
    # report comes from the ledger above — nothing is recomputed.
    print(render_text(report_from_ledger(ledger.events, run_id="hello-loop")))


if __name__ == "__main__":
    main()
