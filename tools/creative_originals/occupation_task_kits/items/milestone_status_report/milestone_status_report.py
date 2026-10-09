"""Milestone status report: slippage, a red, amber or green status per milestone and plain status lines.

Slip is the forecast (or actual) date minus the baseline date in calendar days. An open milestone is green below the
amber threshold, amber from it, red from the red threshold, and overdue when its baseline has passed with no actual
date and no forecast after the report date. A milestone whose forecast falls before a predecessor's forecast or
actual date is flagged as a dependency conflict. The overall status is the worst open status. A pure function of
its JSON input; the command line reads standard input and writes standard output.
"""
from __future__ import annotations

from kit_schema import KitRefusal, check, parse_date, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "duplicate_id": "two milestones share an id",
    "unknown_dependency": "a milestone depends on an id that is not listed",
    "invalid_date": "a date is not a real YYYY-MM-DD calendar date",
    "actual_in_future": "an actual completion date is after the report date",
    "thresholds_out_of_order": "the red threshold is not above the amber threshold",
}
INPUT_SCHEMA = {
    "type": "object", "required": ["as_of", "milestones"], "additionalProperties": False,
    "properties": {
        "as_of": {"type": "string", "description": "report date, YYYY-MM-DD"},
        "milestones": {"type": "array", "minItems": 1, "maxItems": 2000, "description":
                       "milestones with a baseline date and, when known, a forecast or actual date, an owner and "
                       "predecessor ids",
                       "items": {"type": "object", "required": ["id", "name", "baseline_date"],
                                 "additionalProperties": False,
                                 "properties": {"id": {"type": "string", "minLength": 1},
                                                "name": {"type": "string", "minLength": 1},
                                                "baseline_date": {"type": "string"},
                                                "forecast_date": {"type": "string"},
                                                "actual_date": {"type": "string"}, "owner": {"type": "string"},
                                                "depends_on": {"type": "array", "items": {"type": "string"}}}}},
        "amber_slip_days": {"type": "integer", "minimum": 1, "maximum": 365,
                            "description": "slip in days that makes an open milestone amber (default 5)"},
        "red_slip_days": {"type": "integer", "minimum": 2, "maximum": 730,
                          "description": "slip in days that makes an open milestone red (default 15)"},
    },
}
STATUSES = (COMPLETE_ON_TIME, COMPLETE_LATE, GREEN, AMBER, RED, OVERDUE) = (
    "complete_on_time", "complete_late", "green", "amber", "red", "overdue")
OUTPUT_SCHEMA = {
    "type": "object", "required": ["as_of", "overall", "counts", "milestones", "lines"],
    "properties": {
        "as_of": {"type": "string", "format": "date"},
        "overall": {"enum": ["green", "amber", "red", "complete"], "description": "worst status of open milestones"},
        "counts": {"type": "object", "description": "milestones per status"},
        "milestones": {"type": "array", "description": "one row per milestone in input order",
                       "items": {"type": "object", "required": ["id", "status", "slip_days", "dependency_conflict"],
                                 "properties": {"id": {"type": "string"}, "status": {"enum": list(STATUSES)},
                                                "slip_days": {"type": ["integer", "null"]},
                                                "days_until_due": {"type": ["integer", "null"]},
                                                "dependency_conflict": {"type": "boolean"}}}},
        "lines": {"type": "array", "items": {"type": "string"},
                  "description": "one plain sentence per milestone that is not complete on time"},
    },
}


def _date(text: str, label: str):
    value = parse_date(text)
    if value is None:
        raise KitRefusal("invalid_date", f"{label}: {text}")
    return value


def classify(milestone: dict, as_of, amber: int, red: int) -> tuple:
    """(status, slip in days or None, days until the expected date or None)."""
    baseline = _date(milestone["baseline_date"], milestone["id"])
    if "actual_date" in milestone:
        actual = _date(milestone["actual_date"], milestone["id"])
        if actual > as_of:
            raise KitRefusal("actual_in_future", milestone["id"])
        slip = (actual - baseline).days
        return (COMPLETE_LATE if slip > 0 else COMPLETE_ON_TIME), slip, None
    forecast = _date(milestone["forecast_date"], milestone["id"]) if "forecast_date" in milestone else baseline
    if forecast < as_of or (forecast == baseline and baseline < as_of):
        return OVERDUE, (as_of - baseline).days, (forecast - as_of).days
    slip = (forecast - baseline).days
    status = RED if slip >= red else AMBER if slip >= amber else GREEN
    return status, slip, (forecast - as_of).days


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    as_of = _date(payload["as_of"], "as_of")
    amber, red = payload.get("amber_slip_days", 5), payload.get("red_slip_days", 15)
    if red <= amber:
        raise KitRefusal("thresholds_out_of_order", f"amber {amber}, red {red}")
    milestones = payload["milestones"]
    ids = [row["id"] for row in milestones]
    if len(set(ids)) != len(ids):
        raise KitRefusal("duplicate_id", "milestone ids repeat")
    known = set(ids)
    for row in milestones:
        for dependency in row.get("depends_on", []):
            if dependency not in known:
                raise KitRefusal("unknown_dependency", f"{row['id']} depends on {dependency}")
    by_id = {row["id"]: row for row in milestones}

    def expected(row):
        text = row.get("actual_date") or row.get("forecast_date") or row["baseline_date"]
        return _date(text, row["id"])

    rows, lines, counts = [], [], {status: 0 for status in STATUSES}
    for row in milestones:
        status, slip, until = classify(row, as_of, amber, red)
        conflict = any(expected(by_id[dependency]) > expected(row) for dependency in row.get("depends_on", []))
        counts[status] += 1
        rows.append({"id": row["id"], "status": status, "slip_days": slip, "days_until_due": until,
                     "dependency_conflict": conflict})
        owner = f" Owner: {row['owner']}." if row.get("owner") else ""
        if status == OVERDUE:
            lines.append(f"{row['id']} {row['name']}: overdue, baseline {row['baseline_date']} passed with no "
                         f"completion or later forecast.{owner}")
        elif status in (GREEN, AMBER, RED) and (slip or conflict):
            offset = f"{slip} days after baseline" if slip >= 0 else f"{-slip} days before baseline"
            lines.append(f"{row['id']} {row['name']}: forecast {expected(row).isoformat()}, {offset} "
                         f"({status}).{owner}")
        elif status == COMPLETE_LATE:
            lines.append(f"{row['id']} {row['name']}: completed {row['actual_date']}, {slip} days late.")
        if conflict:
            lines.append(f"{row['id']} {row['name']}: forecast is earlier than a predecessor's date; one of the "
                         "two dates is wrong.")
    open_statuses = [row["status"] for row in rows if not row["status"].startswith("complete")]
    if not open_statuses:
        overall = "complete"
    elif any(status in (RED, OVERDUE) for status in open_statuses):
        overall = RED
    elif AMBER in open_statuses:
        overall = AMBER
    else:
        overall = GREEN
    return {"as_of": as_of.isoformat(), "overall": overall, "counts": counts, "milestones": rows, "lines": lines}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
