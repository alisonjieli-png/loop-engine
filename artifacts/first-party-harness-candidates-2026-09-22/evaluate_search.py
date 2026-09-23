"""Evaluate frozen local candidate-search probes; never approve candidates.

Usage:
    python3 evaluate_search.py --root BATCH --probes BATCH/search-probes.json \
        --output BATCH/SEARCH-EVALUATION-NAME.json

An output file must be new, so a failed or earlier attempt is never erased.
The tool calls the local candidate search, not the hosted service.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from search_candidates import CandidateSearchError, search_candidates

PROBE_TYPE = "local_candidate_search_probe/v1"
REPORT_TYPE = "local_candidate_search_evaluation/v1"
SEARCH_TOOL = Path(__file__).resolve().parent / "search_candidates.py"


def _read_json(path: Path) -> tuple[dict, str]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"missing or symlinked file: {path}")
    raw = path.read_bytes()
    if not raw or len(raw) > 100_000:
        raise ValueError(f"empty or overlarge file: {path}")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value, hashlib.sha256(raw).hexdigest()


def evaluate(root: Path, probes_path: Path) -> dict:
    root = root.absolute()
    probes, probes_digest = _read_json(probes_path)
    if probes.get("record_type") != PROBE_TYPE:
        raise ValueError("unsupported local search probe record")
    positive = probes.get("queries")
    negative = probes.get("no_answer_queries")
    if (not isinstance(positive, list) or not positive
            or not isinstance(negative, list) or not negative):
        raise ValueError("positive and no-answer query populations are required")
    expected_names = set()
    positive_results = []
    for row in positive:
        if not isinstance(row, dict) or set(row) != {"query", "expected_name"}:
            raise ValueError("invalid positive probe")
        query, expected = row["query"], row["expected_name"]
        if (not isinstance(query, str) or not query.strip()
                or not isinstance(expected, str) or not expected):
            raise ValueError("empty positive probe")
        if expected in expected_names:
            raise ValueError("a positive expected name appears twice")
        expected_names.add(expected)
        exact = search_candidates(name=expected, root=root)
        if exact["outcome"] != "matches":
            raise ValueError(f"expected candidate absent from frozen batch: {expected}")
        found = search_candidates(query=query, limit=3, root=root)
        names = [item["name"] for item in found["matches"]]
        rank = names.index(expected) + 1 if expected in names else None
        positive_results.append({
            "query": query,
            "expected_name": expected,
            "rank": rank,
            "returned_names": names,
            "outcome": found["outcome"],
        })
    negative_results = []
    for query in negative:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("invalid no-answer probe")
        found = search_candidates(query=query, limit=3, root=root)
        negative_results.append({
            "query": query,
            "no_match": found["outcome"] == "no_match",
            "returned_names": [item["name"] for item in found["matches"]],
        })
    manifest = root / "manifest.json"
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError("candidate manifest missing or symlinked")
    return {
        "record_type": REPORT_TYPE,
        "scope": "local_candidate_batch_only",
        "candidate_approval": "none",
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "batch_root": str(root),
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "search_tool_sha256": hashlib.sha256(SEARCH_TOOL.read_bytes()).hexdigest(),
        "probe_sha256": probes_digest,
        "probe_selection_rule": probes.get("selection_rule", "unknown"),
        "metrics": {
            "positive_queries": len(positive_results),
            "top_one": sum(row["rank"] == 1 for row in positive_results),
            "top_three": sum(row["rank"] is not None for row in positive_results),
            "no_answer_queries": len(negative_results),
            "correct_no_answer": sum(row["no_match"] for row in negative_results),
        },
        "positive_results": positive_results,
        "no_answer_results": negative_results,
        "limitations": "English-language local lexical pilot; one expected item per query; review notes were indexed; no tenant grants, native load, task outcome, or hosted route tested.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--probes", type=Path, required=True)
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
    except (OSError, ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError,
            CandidateSearchError) as error:
        parser.exit(1, f"search evaluation refused: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
