"""Split leakage check: groups of related rows that a train, validation and test split cut through.

Rows carry an id, a split and grouping fields (a prompt cluster, a lineage family, a source document). When one
value of a grouping field appears in more than one split, near-copies of a training row can be scored as held-out
rows. For each grouping field: how many values it has, which values cross splits (with the rows they hold in each
split), how many rows those values hold, and how many rows have no value. Leaking is true when any field has a value
in two splits. A pure function of its JSON input; the command line reads standard input and writes standard output.
"""
from __future__ import annotations

from kit_schema import KitRefusal, check, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "duplicate_id": "two rows share an id",
    "group_field_missing": "no row holds a grouping field",
}
#: Leaking values listed per field (sorted); the counts cover all of them.
LEAKS_LISTED = 100
_GROUP_VALUE = {"type": ["string", "number", "boolean", "null"]}
INPUT_SCHEMA = {
    "type": "object", "required": ["rows", "group_fields"], "additionalProperties": False,
    "properties": {
        "rows": {"type": "array", "minItems": 1, "maxItems": 500000,
                 "description": "one row per example: its id, its split and its grouping fields",
                 "items": {"type": "object", "required": ["id", "split"],
                           "properties": {"id": {"type": "string", "minLength": 1},
                                          "split": {"type": "string", "minLength": 1}},
                           "additionalProperties": _GROUP_VALUE}},
        "group_fields": {"type": "array", "minItems": 1, "maxItems": 20, "uniqueItems": True,
                         "items": {"type": "string", "minLength": 1},
                         "description": "the fields whose values must stay inside one split"},
    },
}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["leaking", "rows", "splits", "fields"],
    "properties": {
        "leaking": {"type": "boolean"},
        "rows": {"type": "integer", "minimum": 0},
        "splits": {"type": "object", "description": "rows per split",
                   "additionalProperties": {"type": "integer", "minimum": 0}},
        "fields": {"type": "array", "description": "one row per grouping field, in input order",
                   "items": {"type": "object",
                             "required": ["field", "values", "leaking_values", "rows_in_leaking_values",
                                          "rows_without_value", "leaks", "leaks_truncated"],
                             "properties": {"leaks": {"type": "array", "items": {
                                 "type": "object", "required": ["value", "splits"]}}}}},
    },
}


def _value_key(value) -> tuple:
    return (type(value).__name__, str(value))


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    rows, fields = payload["rows"], payload["group_fields"]
    seen, splits = set(), {}
    for row in rows:
        if row["id"] in seen:
            raise KitRefusal("duplicate_id", row["id"])
        seen.add(row["id"])
        splits[row["split"]] = splits.get(row["split"], 0) + 1
    absent = [field for field in fields if not any(field in row for row in rows)]
    if absent:
        raise KitRefusal("group_field_missing", ", ".join(absent))
    reports, leaking = [], False
    for field in fields:
        by_value, without = {}, 0
        for row in rows:
            value = row.get(field)
            if value is None:
                without += 1
                continue
            counts = by_value.setdefault(_value_key(value), {"value": value, "splits": {}})["splits"]
            counts[row["split"]] = counts.get(row["split"], 0) + 1
        leaks = [entry for _key, entry in sorted(by_value.items()) if len(entry["splits"]) > 1]
        leaking = leaking or bool(leaks)
        reports.append({"field": field, "values": len(by_value), "leaking_values": len(leaks),
                        "rows_in_leaking_values": sum(sum(entry["splits"].values()) for entry in leaks),
                        "rows_without_value": without,
                        "leaks": [{"value": entry["value"], "splits": dict(sorted(entry["splits"].items()))}
                                  for entry in leaks[:LEAKS_LISTED]],
                        "leaks_truncated": len(leaks) > LEAKS_LISTED})
    return {"leaking": leaking, "rows": len(rows), "splits": dict(sorted(splits.items())), "fields": reports}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
