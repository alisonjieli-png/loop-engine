"""Judge agreement: how closely each pair of judges scores the same answers.

Each row is one judge's score of one model's answer to one item under one arm; a (model, arm, item) is a unit. For
every pair of judges, on the units both scored: how many there are, the mean absolute difference of their scores,
the share of units whose scores differ by at most the tolerance, and Pearson's correlation (null with fewer than
three shared units or when either judge gives every shared unit the same score). Differences are exact (fractions)
until rounding to six decimals. A pure function of its JSON input; the command line reads standard input and writes
standard output.
"""
from __future__ import annotations

import fractions
import itertools
import math

from kit_schema import KitRefusal, check, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "duplicate_grade": "one judge scored one model, arm and item twice",
    "fewer_than_two_judges": "agreement needs at least two judges",
}
#: The tolerance used when the input names none: ten points on a 0 to 100 rubric.
DEFAULT_TOLERANCE = 10
#: Pearson's correlation needs at least this many shared units.
MINIMUM_CORRELATION_UNITS = 3
_TEXT = {"type": "string", "minLength": 1}
_STATISTIC = {"type": ["number", "null"]}
INPUT_SCHEMA = {
    "type": "object", "required": ["rows"], "additionalProperties": False,
    "properties": {
        "rows": {"type": "array", "minItems": 1, "maxItems": 500000,
                 "description": "one judge's score of one model's answer to one item under one arm",
                 "items": {"type": "object", "required": ["model", "arm", "item", "judge", "score"],
                           "additionalProperties": False,
                           "properties": {"model": _TEXT, "arm": _TEXT, "item": _TEXT, "judge": _TEXT,
                                          "score": {"type": "number"}}}},
        "tolerance": {"type": "number", "minimum": 0,
                      "description": "largest score difference counted as agreement (default 10)"},
    },
}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["tolerance", "judges", "pairs"],
    "properties": {
        "tolerance": {"type": "number"},
        "judges": {"type": "array", "description": "each judge with the units it scored, in judge name order",
                   "items": {"type": "object", "required": ["judge", "units"]}},
        "pairs": {"type": "array", "description": "one row per pair of judges, in name order",
                  "items": {"type": "object",
                            "required": ["judge_a", "judge_b", "shared_units", "mean_absolute_difference",
                                         "share_within_tolerance", "pearson_correlation"],
                            "properties": {"shared_units": {"type": "integer", "minimum": 0},
                                           "mean_absolute_difference": _STATISTIC,
                                           "share_within_tolerance": _STATISTIC,
                                           "pearson_correlation": _STATISTIC}}},
    },
}


def number(value):
    """A statistic for JSON: rounded to six decimals, an integer when it is whole, None stays None."""
    if value is None:
        return None
    value = round(float(value), 6)
    return int(value) if value.is_integer() else value


def pearson(left: list, right: list):
    """Pearson's correlation of two equally long lists of fractions, or None when it is undefined."""
    if len(left) < MINIMUM_CORRELATION_UNITS:
        return None
    mean_left, mean_right = sum(left) / len(left), sum(right) / len(right)
    covariance = sum((a - mean_left) * (b - mean_right) for a, b in zip(left, right))
    spread_left = sum((a - mean_left) ** 2 for a in left)
    spread_right = sum((b - mean_right) ** 2 for b in right)
    if not spread_left or not spread_right:
        return None
    return float(covariance) / math.sqrt(float(spread_left) * float(spread_right))


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    tolerance = fractions.Fraction(payload.get("tolerance", DEFAULT_TOLERANCE))
    by_judge = {}
    for row in payload["rows"]:
        unit = (row["model"], row["arm"], row["item"])
        scored = by_judge.setdefault(row["judge"], {})
        if unit in scored:
            raise KitRefusal("duplicate_grade", f"judge {row['judge']}, model {unit[0]}, arm {unit[1]}, "
                                                f"item {unit[2]}")
        scored[unit] = fractions.Fraction(row["score"])
    judges = sorted(by_judge)
    if len(judges) < 2:
        raise KitRefusal("fewer_than_two_judges", ", ".join(judges))
    pairs = []
    for first, second in itertools.combinations(judges, 2):
        shared = sorted(set(by_judge[first]) & set(by_judge[second]))
        left = [by_judge[first][unit] for unit in shared]
        right = [by_judge[second][unit] for unit in shared]
        differences = [abs(a - b) for a, b in zip(left, right)]
        count = len(shared)
        pairs.append({"judge_a": first, "judge_b": second, "shared_units": count,
                      "mean_absolute_difference": number(sum(differences) / count) if count else None,
                      "share_within_tolerance": number(fractions.Fraction(
                          sum(1 for difference in differences if difference <= tolerance), count)) if count else None,
                      "pearson_correlation": number(pearson(left, right))})
    return {"tolerance": number(tolerance), "judges": [{"judge": judge, "units": len(by_judge[judge])}
                                                       for judge in judges], "pairs": pairs}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
