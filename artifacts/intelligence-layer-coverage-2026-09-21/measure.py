"""Measure what the four persistent intelligence layers hold, and what a search returns.

This tool answers three questions with executed evidence instead of a guess:

1. How many items does each of the four layers hold on a fresh installation,
   with no saved runs and no saved user guidance?
2. What does a search of those layers return for a question that is aimed at a
   layer which holds nothing, and what does the response say about that layer?
3. What changes when the candidate coverage pack in ``pack/`` is added, both
   with candidates admitted and at the service default that excludes them?

It creates a temporary empty runs directory and an empty guidance file, so the
"before" numbers are the built-in population and not this workstation's saved
history. It calls no model, reaches no network and writes nothing outside the
report path you name.

    PYTHONPATH=src python \
      artifacts/intelligence-layer-coverage-2026-09-21/measure.py --report PATH
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

from loop_engine import LoopLedger
from loop_engine.core.intelligence_layers import (
    IntelligenceSearchContext, IntelligenceSearchRequest,
    build_intelligence_catalog, catalog_summary, query_intelligence)
from loop_engine.core.store_serve import StoreRecord

PACK_LAYER_KEY = {"runtime_history_solution": "runtime_history_solution_intelligence",
                  "user_feedback": "user_feedback_intelligence"}
#: Questions a paying customer's coding harness would ask. The first four are
#: aimed at the two layers that hold nothing on a fresh installation.
QUESTIONS = (
    "a previous run of this same import that failed and how it was repaired",
    "what went wrong last time and what fixed it",
    "what guidance did the user give about dropping rows",
    "a standing instruction about weakening a check to make the build pass",
    "a reusable solution for deduplicating customer records",
)
TOP_N = 3


def pack_records(pack: Path) -> dict:
    """The candidate pack, projected into the two layers it covers."""
    specifications = json.loads(
        pack.joinpath("specifications.json").read_bytes().decode("utf-8"))
    layers: dict = {"context_intelligence": [], "code_intelligence": [],
                    "runtime_history_solution_intelligence": [],
                    "user_feedback_intelligence": []}
    for row in specifications["specifications"]:
        layers[PACK_LAYER_KEY[row["layer"]]].append(StoreRecord(
            row["id"], "context", row["title"],
            body={"text": row["text"], "lifecycle": "candidate",
                  "category": row["family"], "source_identities": row["sources"]},
            tags=tuple(row["tags"]), tier="experimental",
            source="layer_coverage_candidate_pack"))
    return layers


def searched(catalog: dict, *, include_candidates: bool) -> list:
    """What each customer question returns from this catalog.

    ``unqueried`` and ``unqueried_public`` are recorded beside the hits because
    they are how the response says a layer held nothing. A reader comparing the
    before and after tables needs that field to see that the empty layers were
    named, not silently skipped.

    ``include_candidates`` is recorded with every answer because it decides
    whether a candidate item can be ranked at all. The hosted boundary
    ``saas_routes.intelligence_surface`` leaves it at its ``False`` default.
    """
    answers = []
    for question in QUESTIONS:
        result = query_intelligence(
            IntelligenceSearchRequest(question, catalog, mode="lexical",
                                      top_n=TOP_N,
                                      include_candidates=include_candidates),
            IntelligenceSearchContext(ledger=LoopLedger()))
        excluded = [row["reason"] for row in result["excluded"]]
        answers.append({
            "question": question,
            "include_candidates": result["candidates_included"],
            "unqueried": list(result["unqueried"]),
            "unqueried_public": list(result["unqueried_public"]),
            "excluded_count": len(excluded),
            "excluded_reasons": sorted(set(excluded)),
            "hits": [{"layer": hit["layer"], "record_id": hit["record_id"]}
                     for hit in result["hits"]]})
    return answers


def counts(catalog: dict) -> dict:
    summary = catalog_summary(catalog)
    return {row["layer"]: row["items"] for row in summary["layers"]}


def measure(pack: Path) -> dict:
    """The before and after populations, and what the questions returned."""
    with tempfile.TemporaryDirectory(prefix="layer-coverage-") as directory:
        runs = Path(directory) / "runs"
        runs.mkdir()
        advice = Path(directory) / "user-advice.jsonl"
        before = build_intelligence_catalog(runs_dir=str(runs),
                                            advice_path=str(advice))
        after = {layer: list(records) + list(pack_records(pack)[layer])
                 for layer, records in before.items()}
        return {"record_type": "intelligence_layer_coverage_measurement/v2",
                "population": "built-in package population with an empty runs "
                              "directory and an empty guidance file",
                "search_mode": "lexical", "top_n": TOP_N,
                "before": {
                    "counts": counts(before),
                    "answers": searched(before, include_candidates=True),
                    "answers_at_the_service_default":
                        searched(before, include_candidates=False)},
                "after": {
                    "counts": counts(after),
                    "answers": searched(after, include_candidates=True),
                    "answers_at_the_service_default":
                        searched(after, include_candidates=False)},
                "limits": [
                    "The pack items are candidates. Adding them to this catalog "
                    "is a measurement, not a promotion and not a publication.",
                    "The 'answers' set is measured with include_candidates=True. "
                    "The service default is False, which every hosted call uses; "
                    "'answers_at_the_service_default' is that set, and in it all "
                    "24 pack items are excluded as "
                    "candidate_or_inactive_requires_review and the after answers "
                    "equal the before answers.",
                    "Lexical search over the built catalog. This is a coverage "
                    "measurement, not a relevance benchmark. No score floor is "
                    "applied, so a question whose answer is not in the catalog "
                    "still receives the three best-ranked items.",
                    "No model was called and no network was reached."]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path,
                        help="A new path to write the full report to.")
    arguments = parser.parse_args(argv)
    result = measure(Path(__file__).resolve().parent / "pack")
    if arguments.report is not None:
        with arguments.report.open("w", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
    print(json.dumps({"before": result["before"]["counts"],
                      "after": result["after"]["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
