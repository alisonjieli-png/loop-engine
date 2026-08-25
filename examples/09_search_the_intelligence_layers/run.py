"""Build, categorize, and search the four intelligence layers."""

import os
import time

from loop_engine import LoopLedger
from loop_engine.loop.encapsulate import as_practitioner_loop
from loop_engine.static_architecture.chronicle import Chronicle
from loop_engine.static_architecture.user_intelligence import AdviceStore
from loop_engine.static_architecture.intelligence_layers import (
    build_intelligence_catalog, catalog_summary, query_intelligence)


OUTPUT_DIR = "example-output/intelligence-layers"
RUNS_DIR = os.path.join(OUTPUT_DIR, "runs")
ADVICE_PATH = os.path.join(OUTPUT_DIR, "user-advice.jsonl")


def add_previous_run():
    ledger = LoopLedger()
    as_practitioner_loop(
        "validate customer records before import",
        lambda: {"valid": 247, "quarantined": 3},
        ledger=ledger,
    )
    run_id = (time.strftime("customer-import-%Y%m%d-%H%M%S-")
              + f"{time.time_ns() % 1_000_000_000:09d}")
    chronicle = Chronicle.from_ledger(ledger.events, run_id=run_id)
    chronicle.commit(); chronicle.save(RUNS_DIR)


def main():
    os.makedirs(RUNS_DIR, exist_ok=True)
    add_previous_run()
    AdviceStore(ADVICE_PATH).leave_advice(
        "Quarantine rows with an invalid country code instead of dropping them.",
        scope="task", target="customer-import", guidance_type="instruction",
        strength="instruction", timing="before_verification")

    catalog = build_intelligence_catalog(runs_dir=RUNS_DIR,
                                         advice_path=ADVICE_PATH)
    summary = catalog_summary(catalog)
    print("FOUR INTELLIGENCE LAYERS")
    for layer in summary["layers"]:
        groups = ", ".join(f"{name}={count}" for name, count
                           in layer["category_groups"].items()) or "none"
        print(f"  {layer['public_label']:<38} {layer['items']:>4}  {groups}")

    result = query_intelligence(
        "validate customer records and quarantine invalid country codes",
        catalog, mode="lexical", top_n=3)
    print("\nTOP MATCHES")
    for hit in result["hits"][:8]:
        c = hit["classification"]
        print(f"  {hit['public_label']:<38} {c['category_group']:<12} "
              f"{hit['record_id']}  {hit['title'][:70]}")
    print("\nCandidate Context records are excluded from this normal search.")
    print("\nRuntime Memory is separate. It holds temporary notes only for the "
          "current run.")


if __name__ == "__main__":
    main()
