"""Evaluate frozen queries across several candidate batches, without approval.

This local reviewer experiment is not a hosted search benchmark. Output
paths are exclusive so earlier failures remain beside later experiments.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from evaluate_search import PROBE_TYPE, _read_json
from search_all_candidates import CandidateSearchError, inventory, search_all

REPORT_TYPE = "local_multi_batch_candidate_search_evaluation/v1"
TOOL_ROOT = Path(__file__).resolve().parent


def evaluate(roots: list[Path], probe_paths: list[Path]) -> dict:
    if len(roots) != len(probe_paths):
        raise ValueError("supply one frozen probe file per batch root")
    manifests, candidate_count = inventory(roots)
    populations = []
    seen_expected = set()
    top_one = top_three = no_answer = 0
    for root, path in zip(roots, probe_paths, strict=True):
        probe, digest = _read_json(path)
        if probe.get("record_type") != PROBE_TYPE:
            raise ValueError(f"unsupported probe file: {path}")
        positive = probe.get("queries")
        negative = probe.get("no_answer_queries")
        if not isinstance(positive, list) or not isinstance(negative, list):
            raise TypeError(f"missing query population: {path}")
        rows = []
        negatives = []
        for item in positive:
            if not isinstance(item, dict) or set(item) != {"query", "expected_name"}:
                raise ValueError(f"invalid positive query: {path}")
            query, expected = item["query"], item["expected_name"]
            if expected in seen_expected:
                raise ValueError(f"expected candidate repeated across probe files: {expected}")
            seen_expected.add(expected)
            result = search_all(roots=roots, query=query, limit=3)
            names = [card["name"] for card in result["matches"]]
            rank = names.index(expected) + 1 if expected in names else None
            top_one += rank == 1
            top_three += rank is not None
            rows.append({"query": query, "expected_name": expected,
                         "rank": rank, "returned_names": names})
        for query in negative:
            result = search_all(roots=roots, query=query, limit=3)
            no_match = result["outcome"] == "no_match"
            no_answer += no_match
            negatives.append({"query": query, "no_match": no_match,
                              "returned_names": [card["name"] for card in result["matches"]]})
        populations.append({
            "batch_root": str(root.resolve()),
            "probe_path": str(path.resolve()),
            "probe_sha256": digest,
            "selection_rule": probe.get("selection_rule", "unknown"),
            "positive_queries": rows,
            "no_answer_queries": negatives,
            "metrics": {
                "positive": len(rows),
                "top_one": sum(row["rank"] == 1 for row in rows),
                "top_three": sum(row["rank"] is not None for row in rows),
                "no_answer": len(negatives),
                "correct_no_answer": sum(row["no_match"] for row in negatives),
            },
        })
    return {
        "record_type": REPORT_TYPE,
        "scope": "local_candidate_batches_only",
        "approval_state": "none",
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_count": candidate_count,
        "batch_manifests": [{"root": str(root), "sha256": digest}
                            for root, digest in manifests],
        "search_tool_sha256": hashlib.sha256((TOOL_ROOT / "search_candidates.py").read_bytes()).hexdigest(),
        "multi_batch_tool_sha256": hashlib.sha256((TOOL_ROOT / "search_all_candidates.py").read_bytes()).hexdigest(),
        "metrics": {
            "positive": sum(len(pop["positive_queries"]) for pop in populations),
            "top_one": top_one,
            "top_three": top_three,
            "no_answer": sum(len(pop["no_answer_queries"]) for pop in populations),
            "correct_no_answer": no_answer,
        },
        "populations": populations,
        "limitations": "One expected item per English query; first-batch queries were used during development, later batches were independent local probes. Review notes are indexed. No hosted grants, native loads, task outcomes, or customer relevance distribution tested.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, action="append", required=True)
    parser.add_argument("--probes", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = evaluate(args.root, args.probes)
        if args.output.is_symlink():
            raise ValueError("output symlink refused")
        with args.output.open("x", encoding="utf-8") as target:
            json.dump(report, target, indent=2, sort_keys=True, ensure_ascii=False)
            target.write("\n")
        print(json.dumps(report["metrics"], sort_keys=True))
    except (OSError, ValueError, TypeError, CandidateSearchError,
            UnicodeDecodeError, json.JSONDecodeError) as error:
        parser.exit(1, f"multi-batch evaluation refused: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
