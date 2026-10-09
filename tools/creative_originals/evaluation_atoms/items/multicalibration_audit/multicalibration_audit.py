"""Multicalibration audit: residual means by prediction bin within every declared group, not only overall.

A predictor can be calibrated on the whole population while over-predicting for one group and under-predicting for
another; the errors cancel in the overall bins. The audit splits rows into prediction bins (equal width on [0, 1]),
and for every declared group and the implicit group "all" reports each cell's mean residual (outcome minus
prediction), its probability mass and whether |residual| exceeds the tolerance. Groups may overlap.

multicalibrate() repairs violations by the patching procedure of multicalibration: repeatedly pick the cell with
the largest |residual| x mass, shift its predictions by the residual (clipped to [0, 1]) and re-bin. Each patch of
a cell with at least minimum_count rows and |residual| > tolerance lowers the squared error by at least
minimum_count x tolerance^2, so the loop ends.

    echo '{"call": "multicalibration_audit", "arguments": {"predictions": [0.5, 0.5, 0.5, 0.5], "outcomes": [1, 1, 0, 0], "groups": {"g": [0, 1]}}}' | python3 multicalibration_audit.py
"""
from __future__ import annotations

import math

import atom_cli
import numerics

ALL = "all"


def _inputs(predictions, outcomes, groups, bins, tolerance, minimum_count):
    p = numerics.vector(predictions, "predictions")
    y = numerics.vector(outcomes, "outcomes", minimum_length=len(p), maximum_length=len(p))
    if any(value < 0 or value > 1 for value in p):
        raise ValueError("predictions must lie in [0, 1]")
    if any(value < 0 or value > 1 for value in y):
        raise ValueError("outcomes must lie in [0, 1]")
    bins = numerics.integer(bins, "bins", minimum=1, maximum=1000)
    tolerance = numerics.finite_number(tolerance, "tolerance")
    if tolerance <= 0:
        raise ValueError("tolerance must be positive")
    minimum_count = numerics.integer(minimum_count, "minimum_count", minimum=1)
    declared = {ALL: list(range(len(p)))}
    if groups is not None:
        if not isinstance(groups, dict):
            raise ValueError("groups is an object of group name to row indices")
        for name, rows in groups.items():
            if name == ALL:
                raise ValueError("the group name 'all' is reserved")
            indices = [numerics.integer(row, f"groups[{name!r}]", minimum=0, maximum=len(p) - 1) for row in rows]
            if len(set(indices)) != len(indices) or not indices:
                raise ValueError(f"groups[{name!r}] must list distinct row indices")
            declared[name] = indices
    return p, y, declared, bins, tolerance, minimum_count


def _cells(p, y, declared, bins, tolerance, minimum_count):
    total = len(p)
    rows = []
    for name in [ALL] + sorted(key for key in declared if key != ALL):
        by_bin = {}
        for index in declared[name]:
            by_bin.setdefault(min(int(math.floor(p[index] * bins)), bins - 1), []).append(index)
        for position in sorted(by_bin):
            members = by_bin[position]
            residual = math.fsum(y[i] - p[i] for i in members) / len(members)
            mass = len(members) / total
            rows.append({"group": name, "bin": position, "bin_range": [position / bins, (position + 1) / bins],
                         "count": len(members), "mean_prediction": math.fsum(p[i] for i in members) / len(members),
                         "mean_outcome": math.fsum(y[i] for i in members) / len(members), "residual": residual,
                         "mass": mass, "weighted_violation": abs(residual) * mass,
                         "violation": len(members) >= minimum_count and abs(residual) > tolerance,
                         "_members": members})
    return rows


def _report(rows, tolerance):
    public = [{key: value for key, value in row.items() if key != "_members"} for row in rows]
    violations = [row for row in public if row["violation"]]
    overall = [row for row in public if row["group"] == ALL]
    return {"cells": public, "violations": violations,
            "max_abs_residual": max(abs(row["residual"]) for row in public),
            "max_weighted_violation": max(row["weighted_violation"] for row in public),
            "calibrated_overall": all(abs(row["residual"]) <= tolerance for row in overall),
            "multicalibrated": not violations}


def multicalibration_audit(predictions, outcomes, groups=None, bins=10, tolerance=0.05, minimum_count=1):
    """Residual means by bin for the implicit group "all" and every declared group.

    predictions and outcomes in [0, 1]; groups: {name: [row indices]} (groups may overlap); bins: equal-width bins
    on [0, 1] (a prediction of exactly 1 joins the last bin); tolerance > 0; minimum_count: smallest cell checked.
    Returns {"cells", "violations", "max_abs_residual", "max_weighted_violation", "calibrated_overall",
    "multicalibrated"}."""
    p, y, declared, bins, tolerance, minimum_count = _inputs(predictions, outcomes, groups, bins, tolerance,
                                                             minimum_count)
    return _report(_cells(p, y, declared, bins, tolerance, minimum_count), tolerance)


def multicalibrate(predictions, outcomes, groups=None, bins=10, tolerance=0.05, minimum_count=1, max_rounds=1000):
    """Patch predictions until no cell violates the tolerance (or max_rounds is reached).

    Returns {"predictions" (adjusted), "rounds", "patches": [{"group", "bin", "shift"}], "audit" (after)}."""
    p, y, declared, bins, tolerance, minimum_count = _inputs(predictions, outcomes, groups, bins, tolerance,
                                                             minimum_count)
    max_rounds = numerics.integer(max_rounds, "max_rounds", minimum=1, maximum=100000)
    adjusted, patches = list(p), []
    for _round in range(max_rounds):
        rows = [row for row in _cells(adjusted, y, declared, bins, tolerance, minimum_count) if row["violation"]]
        if not rows:
            break
        worst = max(rows, key=lambda row: (row["weighted_violation"], row["group"] == ALL, -row["bin"]))
        for index in worst["_members"]:
            adjusted[index] = min(1.0, max(0.0, adjusted[index] + worst["residual"]))
        patches.append({"group": worst["group"], "bin": worst["bin"], "shift": worst["residual"]})
    audit = _report(_cells(adjusted, y, declared, bins, tolerance, minimum_count), tolerance)
    return {"predictions": adjusted, "rounds": len(patches), "patches": patches, "audit": audit}


FUNCTIONS = {"multicalibration_audit": multicalibration_audit, "multicalibrate": multicalibrate}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["ALL", "multicalibration_audit", "multicalibrate", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
