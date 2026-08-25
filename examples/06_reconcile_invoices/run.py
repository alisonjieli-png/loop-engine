"""Reconcile invoices with nested loops and visible retries.

    python3 examples/06_reconcile_invoices/run.py

Nothing in the previous examples is special. The nine-step practitioner cycle
is a *template*, and the tabular adapter is *one domain*. This example builds a
loop for a completely different job: reconciling invoices: with its own step
names, its own stop condition, and its own nested sub-loops.

No model and no data science.
"""

from loop_engine import LoopLedger
from loop_engine.loop.recursive_loop import Loop, LoopConfig, StepOutcome
from loop_engine.loop.encapsulate import as_component_loop
from loop_engine.code_nodes.loop_report import report_from_ledger, render_text


# ---------------------------------------------------------------- your domain
INVOICES = [
    {"id": "INV-1001", "amount": 4820.00, "vendor": "Northwind"},
    {"id": "INV-1002", "amount": 1195.50, "vendor": "Contoso"},
    {"id": "INV-1003", "amount": 9900.00, "vendor": "Fabrikam"},
]
PAYMENTS = [
    {"ref": "INV-1001", "paid": 4820.00},
    {"ref": "INV-1002", "paid": 1000.00},        # short-paid
    # INV-1003 has no payment at all
]


def find_payment(invoice_id):
    return next((p for p in PAYMENTS if p["ref"] == invoice_id), None)


# ------------------------------------------------------- your loop definition
def reconcile_one(invoice, ledger, parent):
    """One invoice, as its own loop nested under the run.

    THE STOP CONDITION IS A REAL CHOICE, and getting it wrong is quiet. This
    loop has three steps that must all run, so it uses `run_to_completion`.
    Written first with `success_once`, it stopped after `fetch`: one
    successful ITERATION is one step: and every invoice came back "unknown"
    with no error anywhere. See `lookup_with_retries` below for the shape
    `success_once` is actually for."""
    config = LoopConfig(
        framework="custom",
        custom_steps=("fetch", "compare", "classify"),
        allowable_modes=("deterministic",),      # never calls a model
        preferred_modes=("deterministic",),
        stop_condition="run_to_completion",
        power="light")

    loop = parent.spawn(f"reconcile {invoice['id']}", config=config)
    found = {}

    def handle(loop, step, context):
        if step == "fetch":
            found["payment"] = find_payment(invoice["id"])
            return StepOutcome(output=str(found["payment"]),
                               mode="deterministic", confidence=1.0)
        if step == "compare":
            p = found.get("payment")
            found["delta"] = (0.0 if p is None
                              else round(invoice["amount"] - p["paid"], 2))
            return StepOutcome(output=f"delta={found['delta']}",
                               mode="deterministic", confidence=1.0)
        # classify
        p, delta = found.get("payment"), found.get("delta")
        if p is None:
            verdict = "unpaid"
        elif delta == 0:
            verdict = "settled"
        else:
            verdict = f"short by {delta:.2f}"
        found["verdict"] = verdict
        return StepOutcome(output=verdict, mode="deterministic",
                           confidence=1.0)

    while not loop.is_terminal:
        loop.run_next_iteration(handler=handle)
    return found.get("verdict", "unknown")


def lookup_with_retries(vendor, ledger, parent):
    """The shape `success_once` IS for: try until something works.

    A flaky lookup either succeeds or is worth another attempt. There is no
    "completion" to run to: the first success is the whole goal. That is a
    loop, and saying so lets the runtime count the attempts instead of hiding
    them in a while-loop nobody can see."""
    config = LoopConfig(
        framework="custom", custom_steps=("attempt",),
        allowable_modes=("deterministic",), preferred_modes=("deterministic",),
        stop_condition="success_once", power="light")

    loop = parent.spawn(f"look up {vendor}", config=config)
    state = {"tries": 0}

    def handle(loop, step, context):
        state["tries"] += 1
        # a flaky directory: the first two attempts fail, the third works
        ok = state["tries"] >= 3
        return StepOutcome(
            output=f"{vendor} found on attempt {state['tries']}" if ok
            else "directory timed out",
            mode="deterministic", confidence=1.0 if ok else 0.0, failed=not ok)

    while not loop.is_terminal:
        loop.run_next_iteration(handler=handle)
    return state["tries"]


def main():
    ledger = LoopLedger()

    root = Loop(
        "reconcile the month's invoices",
        LoopConfig(framework="custom",
                   custom_steps=("reconcile", "summarize", "verify"),
                   allowable_modes=("deterministic",), power="standard"),
        ledger=ledger)

    results = {}
    for invoice in INVOICES:
        results[invoice["id"]] = reconcile_one(invoice, ledger, root)

    # A plain helper wrapped as a loop too: so the summary step is as
    # inspectable as the work steps, rather than invisible glue.
    summary = as_component_loop(
        "summarise the reconciliation",
        lambda: {v: sum(1 for r in results.values() if r.startswith(v.split()[0]))
                 for v in ("settled", "unpaid", "short")},
        parent=root, ledger=ledger)["value"]

    tries = lookup_with_retries("Fabrikam", ledger, root)

    def root_handler(loop, step, context):
        if step == "reconcile":
            return StepOutcome(f"reconciled {len(results)} invoices")
        if step == "summarize":
            return StepOutcome(str(summary))
        return StepOutcome("all invoice outcomes have an explicit status")

    root.run(handler=root_handler, max_steps=5)

    print("=== reconciliation ===")
    for inv_id, verdict in results.items():
        print(f"  {inv_id}  {verdict}")
    print()
    print(f"  summary: {summary}")
    print(f"  vendor lookup succeeded after {tries} attempts "
          "(stop_condition='success_once')")
    print()
    print(render_text(report_from_ledger(ledger.events,
                                         run_id="invoice-reconciliation")))
    print()
    print("Two things to notice in that tree:")
    print("  * each invoice is a real nested loop with its own steps, not a")
    print("    for-loop hidden inside a function, which is why it appears at all;")
    print("  * the vendor lookup ran several iterations of one step until one")
    print("    succeeded, and the report counts them. A while-loop would have")
    print("    hidden exactly the retries you would want to know about.")


if __name__ == "__main__":
    main()
