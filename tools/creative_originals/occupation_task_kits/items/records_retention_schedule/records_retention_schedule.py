"""Records retention schedule: compute disposition dates and list records due, due soon, on hold or undated.

A retention schedule maps each record class to a period in years and months, the event that starts the clock
(created, closed or a named event date) and the action at the end (destroy, archive, review). For each record the
helper finds the trigger date, adds the period (a 29 February start lands on 28 February in a non-leap year), and
sets a status: on_hold under a legal hold, trigger_missing when the clock has not started, due when the date has
passed, due_soon inside the review window, otherwise retain. File names can be checked against a naming pattern.
A pure function of its JSON input; the command line reads standard input and writes standard output.
"""
from __future__ import annotations

import calendar
import datetime
import re

from kit_schema import KitRefusal, check, parse_date, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "duplicate_record_class": "two schedule rows share a record class",
    "unknown_record_class": "a record names a class the schedule does not have",
    "duplicate_record_id": "two records share an id",
    "invalid_date": "a date is not a real YYYY-MM-DD calendar date",
    "invalid_pattern": "the naming pattern is not a valid regular expression",
}
INPUT_SCHEMA = {
    "type": "object", "required": ["as_of", "schedule", "records"], "additionalProperties": False,
    "properties": {
        "as_of": {"type": "string", "description": "evaluation date, YYYY-MM-DD"},
        "schedule": {"type": "array", "minItems": 1, "maxItems": 2000, "description":
                     "record classes with retention years and months, the trigger (created, closed, event) and the "
                     "action (destroy, archive, review)",
                     "items": {"type": "object", "required": ["record_class", "trigger", "action"],
                               "additionalProperties": False,
                               "properties": {"record_class": {"type": "string", "minLength": 1},
                                              "years": {"type": "integer", "minimum": 0, "maximum": 200},
                                              "months": {"type": "integer", "minimum": 0, "maximum": 2400},
                                              "trigger": {"enum": ["created", "closed", "event"]},
                                              "action": {"enum": ["destroy", "archive", "review"]},
                                              "citation": {"type": "string"}}}},
        "records": {"type": "array", "minItems": 1, "maxItems": 200000, "description":
                    "records with id, class, created date and when known closed or event date, legal hold and name",
                    "items": {"type": "object", "required": ["id", "record_class", "created"],
                              "additionalProperties": False,
                              "properties": {"id": {"type": "string", "minLength": 1},
                                             "record_class": {"type": "string"}, "created": {"type": "string"},
                                             "closed": {"type": "string"}, "event_date": {"type": "string"},
                                             "legal_hold": {"type": "boolean"}, "file_name": {"type": "string"}}}},
        "review_window_days": {"type": "integer", "minimum": 0, "maximum": 3650,
                               "description": "days ahead that count as due soon (default 90)"},
        "naming_pattern": {"type": "string", "description": "regular expression file names must match"},
    },
}
STATUSES = (ON_HOLD, TRIGGER_MISSING, DUE, DUE_SOON, RETAIN) = (
    "on_hold", "trigger_missing", "due", "due_soon", "retain")
OUTPUT_SCHEMA = {
    "type": "object", "required": ["as_of", "records", "summary", "naming_violations"],
    "properties": {
        "as_of": {"type": "string", "format": "date"},
        "records": {"type": "array", "description": "one row per record in input order",
                    "items": {"type": "object", "required": ["id", "record_class", "status", "action",
                                                             "trigger_date", "disposition_date"],
                              "properties": {"status": {"enum": list(STATUSES)}}}},
        "summary": {"type": "object", "description": "records per status and per action among due records"},
        "naming_violations": {"type": "array", "items": {"type": "string"},
                              "description": "ids whose file name breaks the naming pattern"},
    },
}


def add_period(start: datetime.date, years: int, months: int) -> datetime.date:
    """``start`` plus whole years and months; the day is clipped to the last day of the target month."""
    total = start.month - 1 + months + 12 * years
    year, month = start.year + total // 12, total % 12 + 1
    if year > 9999:
        return datetime.date(9999, 12, 31)
    return datetime.date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


def _date(text, label: str):
    value = parse_date(text)
    if value is None:
        raise KitRefusal("invalid_date", f"{label}: {text}")
    return value


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    as_of = _date(payload["as_of"], "as_of")
    classes = {}
    for row in payload["schedule"]:
        if row["record_class"] in classes:
            raise KitRefusal("duplicate_record_class", row["record_class"])
        classes[row["record_class"]] = row
    pattern = None
    if "naming_pattern" in payload:
        try:
            pattern = re.compile(payload["naming_pattern"])
        except re.error as error:
            raise KitRefusal("invalid_pattern", str(error)) from None
    window = datetime.timedelta(days=payload.get("review_window_days", 90))
    seen, rows, violations = set(), [], []
    counts = {status: 0 for status in STATUSES}
    due_actions = {}
    for record in payload["records"]:
        if record["id"] in seen:
            raise KitRefusal("duplicate_record_id", record["id"])
        seen.add(record["id"])
        rule = classes.get(record["record_class"])
        if rule is None:
            raise KitRefusal("unknown_record_class", f"{record['id']}: {record['record_class']}")
        created = _date(record["created"], record["id"])
        trigger = {"created": created,
                   "closed": _date(record["closed"], record["id"]) if "closed" in record else None,
                   "event": _date(record["event_date"], record["id"]) if "event_date" in record else None}[
            rule["trigger"]]
        disposition = add_period(trigger, rule.get("years", 0), rule.get("months", 0)) if trigger else None
        if record.get("legal_hold"):
            status = ON_HOLD
        elif disposition is None:
            status = TRIGGER_MISSING
        elif disposition <= as_of:
            status = DUE
        elif disposition <= as_of + window:
            status = DUE_SOON
        else:
            status = RETAIN
        counts[status] += 1
        if status == DUE:
            due_actions[rule["action"]] = due_actions.get(rule["action"], 0) + 1
        row = {"id": record["id"], "record_class": record["record_class"], "status": status,
               "action": rule["action"], "trigger_date": trigger.isoformat() if trigger else None,
               "disposition_date": disposition.isoformat() if disposition else None}
        if pattern is not None and "file_name" in record:
            row["naming_ok"] = bool(pattern.fullmatch(record["file_name"]))
            if not row["naming_ok"]:
                violations.append(record["id"])
        rows.append(row)
    return {"as_of": as_of.isoformat(), "records": rows,
            "summary": {"records": len(rows), **counts, "due_by_action": dict(sorted(due_actions.items()))},
            "naming_violations": violations}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
