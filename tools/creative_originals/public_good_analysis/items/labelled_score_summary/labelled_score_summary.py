"""Labelled score summary: scores of each arm broken down by one label of the scored items.

Score rows (item, arm, score) are joined with label rows (an item and its label fields, such as category, corridor
or difficulty) on the item, and summarized per (label value, arm) of the one label field the input names: count,
mean, median, minimum and maximum. A label row that lacks the field, or holds null there, puts its item under the
value null. Scores of items without a label row are left out and counted, and so are label rows no score uses. A
pure function of its JSON input; the command line reads standard input and writes standard output.
"""
from __future__ import annotations

import fractions
import json
import statistics

from kit_schema import KitRefusal, check, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "duplicate_label": "two label rows name the same item",
    "label_field_missing": "no label row holds the label field",
}
#: Items listed by name in each of the two unmatched lists; the counts cover all of them.
EXAMPLES_LISTED = 20
_LABEL_VALUE = {"type": ["string", "number", "boolean", "null"]}
_STATISTIC = {"type": "number"}
INPUT_SCHEMA = {
    "type": "object", "required": ["scores", "labels", "label_field"], "additionalProperties": False,
    "properties": {
        "scores": {"type": "array", "minItems": 1, "maxItems": 500000, "description": "one score of one item under one arm",
                   "items": {"type": "object", "required": ["item", "arm", "score"], "additionalProperties": False,
                             "properties": {"item": {"type": "string", "minLength": 1},
                                            "arm": {"type": "string", "minLength": 1},
                                            "score": {"type": "number"}}}},
        "labels": {"type": "array", "minItems": 1, "maxItems": 500000,
                   "description": "one row per item: the item and its label fields",
                   "items": {"type": "object", "required": ["item"],
                             "properties": {"item": {"type": "string", "minLength": 1}},
                             "additionalProperties": _LABEL_VALUE}},
        "label_field": {"type": "string", "minLength": 1, "description": "the label the scores are broken down by"},
    },
}
OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["label_field", "groups", "scores_used", "items_without_label", "items_without_label_examples",
                 "labels_without_scores", "labels_without_scores_examples"],
    "properties": {
        "label_field": {"type": "string"},
        "groups": {"type": "array", "description": "one row per label value and arm, null value first",
                   "items": {"type": "object",
                             "required": ["value", "arm", "count", "mean", "median", "minimum", "maximum"],
                             "properties": {"value": _LABEL_VALUE, "arm": {"type": "string"},
                                            "count": {"type": "integer", "minimum": 1}, "mean": _STATISTIC,
                                            "median": _STATISTIC, "minimum": _STATISTIC, "maximum": _STATISTIC}}},
        "scores_used": {"type": "integer", "minimum": 0},
        "items_without_label": {"type": "integer", "minimum": 0, "description": "distinct scored items with no label row"},
        "items_without_label_examples": {"type": "array", "items": {"type": "string"}},
        "labels_without_scores": {"type": "integer", "minimum": 0, "description": "label rows no score row uses"},
        "labels_without_scores_examples": {"type": "array", "items": {"type": "string"}},
    },
}


def number(value):
    """A statistic for JSON: rounded to six decimals, an integer when it is whole."""
    value = round(float(value), 6)
    return int(value) if value.is_integer() else value


def _order(key: tuple) -> tuple:
    """Null first, then values by type name and text, then arm."""
    value = json.loads(key[0])
    return (value is not None, type(value).__name__, str(value), key[1])


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    field = payload["label_field"]
    labels = {}
    for row in payload["labels"]:
        if row["item"] in labels:
            raise KitRefusal("duplicate_label", row["item"])
        labels[row["item"]] = row
    if not any(field in row for row in labels.values()):
        raise KitRefusal("label_field_missing", field)
    groups, unlabelled, scored = {}, set(), set()
    used = 0
    for row in payload["scores"]:
        scored.add(row["item"])
        label = labels.get(row["item"])
        if label is None:
            unlabelled.add(row["item"])
            continue
        used += 1
        # The value's JSON text is the key, so true and 1 (equal in Python) stay two values.
        groups.setdefault((json.dumps(label.get(field)), row["arm"]), []).append(fractions.Fraction(row["score"]))
    rows = []
    for key in sorted(groups, key=_order):
        values = groups[key]
        rows.append({"value": json.loads(key[0]), "arm": key[1], "count": len(values),
                     "mean": number(sum(values) / len(values)),
                     "median": number(statistics.median(values)), "minimum": number(min(values)),
                     "maximum": number(max(values))})
    unused = sorted(item for item in labels if item not in scored)
    unlabelled_items = sorted(unlabelled)
    return {"label_field": field, "groups": rows, "scores_used": used, "items_without_label": len(unlabelled_items),
            "items_without_label_examples": unlabelled_items[:EXAMPLES_LISTED],
            "labels_without_scores": len(unused), "labels_without_scores_examples": unused[:EXAMPLES_LISTED]}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
