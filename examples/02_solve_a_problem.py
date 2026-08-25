"""2 — Send a real problem to the loop and get a solved artifact back.

    python -m pip install .
    python examples/02_solve_a_problem.py

This is the shape most people want: hand the loop a dataset and a goal, let it
work through the nine-step practitioner cycle, and collect both the artifact
and the evidence.

Still zero model calls. The loop orients on the data, researches an approach
from its own intelligence, decides, acts, verifies, and commits — all on the
deterministic rail. A model is an *escalation* for the steps that need
judgement, not the engine.

The example generates its own small dataset so it runs anywhere.
"""

import os
import tempfile

import numpy as np
import pandas as pd

from loop_engine import LoopLedger
from loop_engine.code_nodes.smoke_ladder import run_smoke_loop
from loop_engine.code_nodes.loop_report import report_from_ledger, render_text


def make_dataset(directory):
    """A small, honest classification problem: does a customer renew?"""
    rng = np.random.default_rng(7)
    n = 900
    df = pd.DataFrame({
        "customer_id": np.arange(n),
        "months_active": rng.integers(1, 60, n),
        "support_tickets": rng.poisson(1.6, n),
        "monthly_spend": rng.gamma(4.0, 25.0, n).round(2),
        "plan": rng.choice(["basic", "pro", "enterprise"], n),
    })
    # a real signal, plus noise — so the score means something
    logit = (0.045 * df["months_active"] - 0.35 * df["support_tickets"]
             + 0.004 * df["monthly_spend"] + (df["plan"] == "enterprise") * 0.8
             + rng.normal(0, 0.7, n) - 1.4)
    df["renewed"] = (logit > 0).astype(int)

    train, test = df.iloc[:700].copy(), df.iloc[700:].copy()
    holdout = test["renewed"].to_numpy()
    test = test.drop(columns=["renewed"])

    paths = {k: os.path.join(directory, f"{k}.csv")
             for k in ("train", "test", "sample")}
    train.to_csv(paths["train"], index=False)
    test.to_csv(paths["test"], index=False)
    pd.DataFrame({"customer_id": test["customer_id"],
                  "renewed": 0}).to_csv(paths["sample"], index=False)
    return paths, holdout


def main():
    with tempfile.TemporaryDirectory() as d:
        paths, holdout = make_dataset(d)
        out_csv = os.path.join(d, "predictions.csv")
        ledger = LoopLedger()

        # THE ONE CALL: a goal in plain English plus where the data lives.
        receipt = run_smoke_loop(
            "predict which customers renew",
            train_csv=paths["train"], test_csv=paths["test"],
            sample_csv=paths["sample"], out_csv=out_csv,
            ledger=ledger)

        trace = receipt.get("trace", {})
        preds = pd.read_csv(out_csv)
        accuracy = (preds["renewed"].to_numpy() == holdout).mean()

        print("=== what the loop produced ===")
        print(f"  predictions   : {len(preds)} rows -> {out_csv}")
        print(f"  estimator     : {trace.get('estimator', 'unknown')}")
        print(f"  engineered    : {trace.get('engineered') or 'none'}")
        print(f"  local cv score: {trace.get('cv_score')}")
        print(f"  holdout acc   : {accuracy:.4f}   <- graded here, "
              "never shown to the loop")
        print()
        print("=== what it cost ===")
        print(f"  model calls   : {len(trace.get('model_calls', []))}")
        print(f"  steps on the deterministic rail: "
              f"{trace.get('code_served_steps')}")
        print()
        print(render_text(report_from_ledger(ledger.events,
                                             run_id="renewal-problem")))


if __name__ == "__main__":
    main()
