"""Run the catalogue search measurement and check what it reports.

The example runs the measurement over the starter catalogue and checks four
things a reader would otherwise have to take on trust: the population is the
one the report names, the declared default is better than the deployed search
on the requests held back, the requests this catalogue cannot answer are still
counted, and every failure is named rather than only counted.

No model is called, no network is used and no body is loaded.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import measure  # noqa: E402
from loop_engine.core.harness_intelligence_search import (  # noqa: E402
    DEFAULT_SEARCH_POLICY, SERVED_BEFORE_2026_09_21)


def main():
    catalogue = measure.load_catalogue(measure.DEFAULT_CATALOGUE)
    judgements = measure.load_judgements(measure.DEFAULT_JUDGEMENTS, catalogue)
    held_back = tuple(row for row in judgements if row.split == "held_back")
    checks, notes = [], {}

    # Every item is asked for, and there are more requests than items, so no
    # item is measured by one request alone.
    expected = {name for row in judgements for name in row.relevant}
    checks.append(expected == set(catalogue.items) and len(judgements) > len(catalogue.items))

    baseline = measure.measure(catalogue, held_back, SERVED_BEFORE_2026_09_21,
                               depth=measure.CUT_OFFS[-1])
    current = measure.measure(catalogue, held_back, DEFAULT_SEARCH_POLICY,
                              depth=measure.CUT_OFFS[-1])
    checks.append(current["overall"]["mean_reciprocal_rank"]
                  > baseline["overall"]["mean_reciprocal_rank"])
    checks.append(current["overall"]["recall_at_3"] >= baseline["overall"]["recall_at_3"])

    whole = measure.measure(catalogue, judgements, DEFAULT_SEARCH_POLICY)
    # A request this catalogue cannot answer is counted separately, and a
    # failure names the request and what came back instead of it.
    checks.append(whole["overall"]["unanswerable_queries"] > 0)
    checks.append(all(row["query"] and "returned_first" in row and "expected" in row
                      for row in whole["failed_queries"]))

    notes = {"catalogue_items": len(catalogue.items), "requests": len(judgements),
             "held_back_requests": len(held_back),
             "held_back_mean_reciprocal_rank": {
                 "deployed_search": baseline["overall"]["mean_reciprocal_rank"],
                 "declared_default": current["overall"]["mean_reciprocal_rank"]},
             "match_mode": DEFAULT_SEARCH_POLICY.match_mode,
             "fields_read": list(DEFAULT_SEARCH_POLICY.fields_read),
             "unanswerable_requests_answered": whole["overall"]["answered_confidently"],
             "failed_requests": [row["query"] for row in whole["failed_queries"]]}
    result = {"record_type": "search_quality_example_checks/v1",
              "passed": sum(checks), "total": len(checks), "all_passed": all(checks),
              "external_provider_calls": 0, "provider_qualified": False, **notes}
    print(json.dumps(result, indent=2))
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
