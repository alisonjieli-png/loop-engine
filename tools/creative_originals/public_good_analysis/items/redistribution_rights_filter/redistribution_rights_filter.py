"""Redistribution rights filter: keep the rows whose own rights fields allow the use you plan.

Each row of a corpus carries its licence and its permission flags (public redistribution, training use). A row is
kept when it names a licence, the licence is one of the allowed licences, and the flags the input requires are
true; otherwise it is excluded with the first failing reason, checked in this order: missing licence, licence not
allowed, redistribution not allowed, training not allowed. A missing or null flag is not true. Licences compare
exactly after trimming spaces. A pure function of its JSON input; the command line reads standard input and writes
standard output.
"""
from __future__ import annotations

from kit_schema import KitRefusal, check, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "duplicate_id": "two rows share an id",
}
#: Why a row is excluded, in the order the checks run.
(MISSING_LICENCE, LICENCE_NOT_ALLOWED, REDISTRIBUTION_NOT_ALLOWED, TRAINING_NOT_ALLOWED) = EXCLUSIONS = (
    "missing_licence", "licence_not_allowed", "redistribution_not_allowed", "training_not_allowed")
KEPT = "kept"
_FLAG = {"type": ["boolean", "null"]}
INPUT_SCHEMA = {
    "type": "object", "required": ["rows", "allowed_licences"], "additionalProperties": False,
    "properties": {
        "rows": {"type": "array", "minItems": 1, "maxItems": 500000,
                 "description": "one row per record with its own licence and permission flags",
                 "items": {"type": "object", "required": ["id"],
                           "properties": {"id": {"type": "string", "minLength": 1},
                                          "license": {"type": ["string", "null"]},
                                          "allow_public_redistribution": _FLAG, "allow_training_use": _FLAG}}},
        "allowed_licences": {"type": "array", "minItems": 1, "maxItems": 50, "uniqueItems": True,
                             "items": {"type": "string", "minLength": 1},
                             "description": "licence identifiers a kept row may carry, such as CC-BY-4.0"},
        "require_redistribution": {"type": "boolean", "description": "keep only rows allowing public redistribution "
                                                                     "(default true)"},
        "require_training_use": {"type": "boolean", "description": "keep only rows allowing training use "
                                                                   "(default false)"},
    },
}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["kept", "excluded", "counts"],
    "properties": {
        "kept": {"type": "array", "items": {"type": "string"}, "description": "ids of kept rows, in input order"},
        "excluded": {"type": "array", "description": "excluded rows in input order, each with its first failing reason",
                     "items": {"type": "object", "required": ["id", "reason"],
                               "properties": {"reason": {"enum": list(EXCLUSIONS)}}}},
        "counts": {"type": "object", "required": [KEPT] + list(EXCLUSIONS),
                   "additionalProperties": {"type": "integer", "minimum": 0}},
    },
}


def first_failure(row: dict, allowed: set, redistribution: bool, training: bool):
    """The first reason a row is excluded, or None when it is kept."""
    licence = (row.get("license") or "").strip()
    if not licence:
        return MISSING_LICENCE
    if licence not in allowed:
        return LICENCE_NOT_ALLOWED
    if redistribution and row.get("allow_public_redistribution") is not True:
        return REDISTRIBUTION_NOT_ALLOWED
    if training and row.get("allow_training_use") is not True:
        return TRAINING_NOT_ALLOWED
    return None


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    allowed = {licence.strip() for licence in payload["allowed_licences"]}
    redistribution = payload.get("require_redistribution", True)
    training = payload.get("require_training_use", False)
    kept, excluded, seen = [], [], set()
    counts = dict.fromkeys((KEPT,) + EXCLUSIONS, 0)
    for row in payload["rows"]:
        if row["id"] in seen:
            raise KitRefusal("duplicate_id", row["id"])
        seen.add(row["id"])
        failure = first_failure(row, allowed, redistribution, training)
        if failure is None:
            kept.append(row["id"])
            counts[KEPT] += 1
        else:
            excluded.append({"id": row["id"], "reason": failure})
            counts[failure] += 1
    return {"kept": kept, "excluded": excluded, "counts": counts}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
