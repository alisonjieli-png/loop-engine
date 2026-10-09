"""Equal-cohort comparison: score every candidate on the same rows, and report coverage separately.

Candidates often fail to produce a score on some rows (a crash, a timeout, a refusal, an unsupported input). Two
common shortcuts mislead: averaging each candidate over its own rows (a candidate that skips hard rows looks
better) and counting a missing score as zero (a different metric that mixes failure rate into quality). This tool
compares means on the cohort of rows that every candidate scored, and reports separately how much of the declared
universe each candidate covered. A missing score is never turned into a number.

    echo '{"call": "compare_on_common_cohort", "arguments": {"scores": {"a": {"r1": 1, "r2": null}, "b": {"r1": 0, "r2": 1}}}}' | python3 equal_cohort_comparison.py
"""
from __future__ import annotations

import math

import atom_cli
import numerics


def _scores(scores):
    if not isinstance(scores, dict) or len(scores) < 1:
        raise ValueError("scores is an object of candidates, each an object of row id to number or null")
    table = {}
    for candidate, rows in scores.items():
        if not isinstance(rows, dict):
            raise ValueError(f"scores[{candidate!r}] must be an object of row id to number or null")
        table[candidate] = {}
        for row, value in rows.items():
            if value is not None:
                table[candidate][row] = numerics.finite_number(value, f"scores[{candidate!r}][{row!r}]")
    return table


def compare_on_common_cohort(scores, universe=None, higher_is_better=True, reference=None):
    """Means on the rows every candidate scored, coverage of the universe, a ranking and paired differences.

    scores: {candidate: {row_id: number or null}}; null or absent means the candidate has no score for that row.
    universe: the declared row ids (default: every row id that appears); a scored row outside it is refused.
    reference: optional candidate; paired mean differences (candidate minus reference) on the cohort.
    Returns {"cohort", "cohort_size", "comparable", "means", "coverage", "ranking", "excluded_rows",
    "paired_differences"}. With an empty cohort, means are null and the ranking is empty."""
    table = _scores(scores)
    declared = sorted({row for rows in scores.values() for row in rows}) if universe is None else \
        numerics.labels(universe, "universe")
    universe_set = set(declared)
    if len(universe_set) != len(declared):
        raise ValueError("universe row ids must be unique")
    for candidate, rows in scores.items():
        unknown = sorted(set(rows) - universe_set)
        if unknown:
            raise ValueError(f"scores[{candidate!r}] has rows outside the universe: {unknown[:5]}")
    if reference is not None and reference not in table:
        raise ValueError("reference must be one of the candidates")
    cohort = sorted(row for row in universe_set if all(row in rows for rows in table.values()))
    comparable = bool(cohort)
    means = {candidate: (math.fsum(rows[row] for row in cohort) / len(cohort) if comparable else None)
             for candidate, rows in table.items()}
    total = len(declared)
    coverage = {candidate: {"scored": len(rows), "universe": total,
                            "fraction": len(rows) / total if total else None} for candidate, rows in table.items()}
    sign = -1.0 if higher_is_better else 1.0
    ranking = sorted(table, key=lambda candidate: (sign * means[candidate], candidate)) if comparable else []
    excluded = {row: sorted(candidate for candidate, rows in table.items() if row not in rows)
                for row in sorted(universe_set) if row not in cohort}
    paired = None
    if reference is not None:
        paired = {candidate: {"mean_difference": (math.fsum(rows[row] - table[reference][row] for row in cohort)
                                                  / len(cohort)) if comparable else None, "rows": len(cohort)}
                  for candidate, rows in table.items() if candidate != reference}
    return {"cohort": cohort, "cohort_size": len(cohort), "comparable": comparable, "means": means,
            "coverage": coverage, "ranking": ranking, "excluded_rows": excluded, "paired_differences": paired}


FUNCTIONS = {"compare_on_common_cohort": compare_on_common_cohort}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["compare_on_common_cohort", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
