"""Build, categorize, and search the four intelligence layers."""

import os
import tempfile
import time

from loop_engine import LoopLedger
from loop_engine.loop.encapsulate import as_practitioner_loop
from loop_engine.loop.loop_capsule import LoopRef
from loop_engine.static_architecture.run_history import RunHistory
from loop_engine.static_architecture.user_feedback_intelligence import AdviceStore
from loop_engine.static_architecture.intelligence_layers import (
    build_intelligence_catalog, catalog_summary, materialize_intelligence_ref,
    query_intelligence)


def add_runtime_history(runs_dir):
    ledger = LoopLedger()
    as_practitioner_loop(
        "validate customer records before import",
        lambda: {"valid": 247, "quarantined": 3},
        ledger=ledger,
    )
    run_id = (time.strftime("customer-import-%Y%m%d-%H%M%S-")
              + f"{time.time_ns() % 1_000_000_000:09d}")
    run_history = RunHistory.from_ledger(ledger.events, run_id=run_id)
    run_history.commit(); run_history.save(runs_dir)


def main():
    with tempfile.TemporaryDirectory(
            prefix="loop-engine-intelligence-layers-") as output_dir:
        runs_dir = os.path.join(output_dir, "runs")
        advice_path = os.path.join(output_dir, "user-advice.jsonl")
        os.makedirs(runs_dir, exist_ok=True)
        add_runtime_history(runs_dir)
        AdviceStore(advice_path).leave_advice(
            "Quarantine rows with an invalid country code instead of dropping them.",
            scope="task", target="customer-import", guidance_type="instruction",
            strength="instruction", timing="before_verification")

        catalog = build_intelligence_catalog(runs_dir=runs_dir,
                                             advice_path=advice_path)
        summary = catalog_summary(catalog)
        print("FOUR INTELLIGENCE LAYERS")
        for layer in summary["layers"]:
            groups = ", ".join(f"{name}={count}" for name, count
                               in layer["category_groups"].items()) or "none"
            print(f"  {layer['public_label']:<38} {layer['items']:>4}  {groups}")

        access_ledger = LoopLedger()
        result = query_intelligence(
            "validate customer records and quarantine invalid country codes",
            catalog, mode="lexical", top_n=3, ledger=access_ledger)
        print("\nTOP MATCHES")
        for hit in result["hits"][:8]:
            c = hit["classification"]
            print(f"  {hit['public_label']:<38} {c['category_group']:<12} "
                  f"{hit['record_id']}  {hit['title'][:70]}")
        selected = LoopRef.from_dict(result["loop_refs"][0])
        loaded = materialize_intelligence_ref(
            selected, catalog, ledger=access_ledger)
        print("\nSELECTED ITEM")
        print(f"  search loop: {result['query_loop']['loop_id']}")
        print(f"  selected ref: {selected.loop_ref}")
        print(f"  access loop: {loaded['loop_id']}")
        print(f"  value: {str(loaded['value'])[:160]}")
        print(f"  loops recorded: {len(access_ledger.loops())}")
        print("\nCandidate Context records are excluded from this normal search.")
        print("\nRuntime Memory is separate. It holds temporary notes only for the "
              "current run.")


if __name__ == "__main__":
    main()
