"""Paired arm lift: how much a treatment arm of an evaluation changes scores against a baseline arm, item by item.

Each row is one judge's score of one model's answer to one item under one arm. The judges' scores of a (model, arm,
item) are averaged first; then every item a model answered under both arms is a pair, and its lift is the treatment
mean minus the baseline mean. Per model and over all models: paired items, the two arm means over the paired items,
the mean and median lift, and how many pairs improved, worsened or stayed equal. Rows of other arms are ignored and
counted. Arithmetic is exact (fractions) until the result is rounded to six decimals, so a zero lift is never a
rounding accident. A pure function of its JSON input; the command line reads standard input and writes standard
output.
"""
from __future__ import annotations

import fractions
import statistics

from kit_schema import KitRefusal, check, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "same_arm": "the baseline and treatment arms are the same arm",
    "arm_not_found": "no row carries the baseline or the treatment arm",
    "duplicate_grade": "one judge scored one model, arm and item twice",
}
_TEXT = {"type": "string", "minLength": 1}
_STATISTIC = {"type": ["number", "null"]}
_SUMMARY_FIELDS = ["paired_items", "baseline_mean", "treatment_mean", "mean_lift", "median_lift", "improved",
                   "worsened", "unchanged", "share_improved"]
INPUT_SCHEMA = {
    "type": "object", "required": ["rows", "baseline_arm", "treatment_arm"], "additionalProperties": False,
    "properties": {
        "rows": {"type": "array", "minItems": 1, "maxItems": 500000,
                 "description": "one judge's score of one model's answer to one item under one arm",
                 "items": {"type": "object", "required": ["model", "arm", "item", "judge", "score"],
                           "additionalProperties": False,
                           "properties": {"model": _TEXT, "arm": _TEXT, "item": _TEXT, "judge": _TEXT,
                                          "score": {"type": "number"}}}},
        "baseline_arm": {"type": "string", "minLength": 1, "description": "the arm the lift is measured from"},
        "treatment_arm": {"type": "string", "minLength": 1, "description": "the arm the lift is measured to"},
    },
}
_SUMMARY = {
    "type": "object", "required": list(_SUMMARY_FIELDS),
    "properties": {"paired_items": {"type": "integer", "minimum": 0}, "baseline_mean": _STATISTIC,
                   "treatment_mean": _STATISTIC, "mean_lift": _STATISTIC, "median_lift": _STATISTIC,
                   "improved": {"type": "integer", "minimum": 0}, "worsened": {"type": "integer", "minimum": 0},
                   "unchanged": {"type": "integer", "minimum": 0}, "share_improved": _STATISTIC},
}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["baseline_arm", "treatment_arm", "models", "overall", "other_arm_rows"],
    "properties": {
        "baseline_arm": {"type": "string"},
        "treatment_arm": {"type": "string"},
        "models": {"type": "array", "description": "one summary per model, in model name order",
                   "items": {"type": "object",
                             "required": ["model"] + _SUMMARY_FIELDS + ["unpaired_baseline_items",
                                                                         "unpaired_treatment_items"]}},
        "overall": {**_SUMMARY, "description": "every (model, item) pair of every model together"},
        "other_arm_rows": {"type": "integer", "minimum": 0, "description": "rows of arms other than the two compared"},
    },
}


def number(value):
    """A statistic for JSON: rounded to six decimals, an integer when it is whole, None stays None."""
    if value is None:
        return None
    value = round(float(value), 6)
    return int(value) if value.is_integer() else value


def summary(pairs: list) -> dict:
    """The lift summary of (baseline mean, treatment mean) pairs, exact until rounding."""
    lifts = [treatment - baseline for baseline, treatment in pairs]
    count = len(pairs)
    if not count:
        return {"paired_items": 0, "baseline_mean": None, "treatment_mean": None, "mean_lift": None,
                "median_lift": None, "improved": 0, "worsened": 0, "unchanged": 0, "share_improved": None}
    improved = sum(1 for lift in lifts if lift > 0)
    return {"paired_items": count,
            "baseline_mean": number(sum(baseline for baseline, _treatment in pairs) / count),
            "treatment_mean": number(sum(treatment for _baseline, treatment in pairs) / count),
            "mean_lift": number(sum(lifts) / count), "median_lift": number(statistics.median(lifts)),
            "improved": improved, "worsened": sum(1 for lift in lifts if lift < 0),
            "unchanged": sum(1 for lift in lifts if lift == 0), "share_improved": number(fractions.Fraction(improved,
                                                                                                         count))}


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    baseline, treatment = payload["baseline_arm"], payload["treatment_arm"]
    if baseline == treatment:
        raise KitRefusal("same_arm", baseline)
    compared = (baseline, treatment)
    scores, seen, other = {}, set(), 0
    arms = set()
    for row in payload["rows"]:
        key = (row["model"], row["arm"], row["item"], row["judge"])
        if key in seen:
            raise KitRefusal("duplicate_grade", f"model {key[0]}, arm {key[1]}, item {key[2]}, judge {key[3]}")
        seen.add(key)
        arms.add(row["arm"])
        if row["arm"] not in compared:
            other += 1
            continue
        scores.setdefault((row["model"], row["arm"], row["item"]), []).append(fractions.Fraction(row["score"]))
    missing = [arm for arm in compared if arm not in arms]
    if missing:
        raise KitRefusal("arm_not_found", ", ".join(missing))
    means = {key: sum(values) / len(values) for key, values in scores.items()}
    models = sorted({model for model, _arm, _item in means})
    rows, every_pair = [], []
    for model in models:
        base_items = {item for name, arm, item in means if name == model and arm == baseline}
        treated_items = {item for name, arm, item in means if name == model and arm == treatment}
        pairs = [(means[(model, baseline, item)], means[(model, treatment, item)])
                 for item in sorted(base_items & treated_items)]
        every_pair += pairs
        rows.append({"model": model, **summary(pairs), "unpaired_baseline_items": len(base_items - treated_items),
                     "unpaired_treatment_items": len(treated_items - base_items)})
    return {"baseline_arm": baseline, "treatment_arm": treatment, "models": rows, "overall": summary(every_pair),
            "other_arm_rows": other}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
