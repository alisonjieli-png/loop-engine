"""Build and grade a customer-renewal prediction artifact.

Run:
    python3 examples/02_predict_customer_renewal/run.py

The generated fixture has a hidden holdout so the artifact can be graded
without showing the answers to the loop. The output directory is kept.
"""

import argparse
import os

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
    # A known signal plus noise gives the local grader something meaningful.
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="example-output/customer-renewal")
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    paths, holdout = make_dataset(args.output_dir)
    out_csv = os.path.join(args.output_dir, "predictions.csv")
    ledger = LoopLedger()

    run_result = run_smoke_loop(
        "predict which customers renew",
        train_csv=paths["train"], test_csv=paths["test"],
        sample_csv=paths["sample"], out_csv=out_csv,
        ledger=ledger)

    trace = run_result.get("trace", {})
    preds = pd.read_csv(out_csv)
    accuracy = (preds["renewed"].to_numpy() == holdout).mean()

    print("WHAT THE LOOP PRODUCED")
    print(f"  predictions   : {len(preds)} rows -> {out_csv}")
    print(f"  estimator     : {trace.get('estimator', 'unknown')}")
    print(f"  engineered    : {trace.get('engineered') or 'none'}")
    print(f"  local cv score: {trace.get('cv_score')}")
    print(f"  holdout acc   : {accuracy:.4f} (answers hidden from the loop)")
    print("\nWHAT IT USED")
    print(f"  model calls   : {len(trace.get('model_calls', []))}")
    print(f"  code-served steps: {trace.get('code_served_steps')}")
    print()
    print(render_text(report_from_ledger(ledger.events,
                                         run_id="customer-renewal")))


if __name__ == "__main__":
    main()
