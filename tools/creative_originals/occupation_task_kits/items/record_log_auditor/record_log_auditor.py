"""Record log auditor: check an operational log for missing fields, order, repeated ids, sequence and time gaps.

An operational log (shift log, maintenance log, sample register, travel log) is a list of records with a timestamp.
Per group (for example per site or machine) the helper reports records missing required fields, timestamps that
cannot be read, records out of time order, repeated ids, gaps and repeats in a numeric sequence field, and missing
days or hours against an expected interval, optionally over a declared period. Coverage is the share of expected
day or hour slots that hold at least one record. A pure function of its JSON input; the command line reads
standard input and writes standard output.
"""
from __future__ import annotations

import datetime

from kit_schema import KitRefusal, check, parse_date, parse_date_time, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "field_absent": "the timestamp, id, sequence or group field appears in no record",
    "invalid_period": "the period dates are not real dates or end before they start",
}
INPUT_SCHEMA = {
    "type": "object", "required": ["records", "timestamp_field"], "additionalProperties": False,
    "properties": {
        "records": {"type": "array", "minItems": 1, "maxItems": 200000, "items": {"type": "object"},
                    "description": "log records as objects"},
        "timestamp_field": {"type": "string", "minLength": 1,
                            "description": "field holding a YYYY-MM-DD date or an ISO 8601 date and time"},
        "required_fields": {"type": "array", "items": {"type": "string"}, "maxItems": 100,
                            "description": "fields every record must fill"},
        "id_field": {"type": "string", "description": "field whose values must not repeat"},
        "sequence_field": {"type": "string", "description": "integer field expected to rise by 1 per group"},
        "group_field": {"type": "string", "description": "field that splits the log, such as site or machine"},
        "expected_interval": {"enum": ["day", "hour"], "description": "one record expected per day or per hour"},
        "period": {"type": "object", "required": ["start", "end"], "additionalProperties": False,
                   "properties": {"start": {"type": "string"}, "end": {"type": "string"}},
                   "description": "YYYY-MM-DD range the log should cover, inclusive"},
        "max_issues": {"type": "integer", "minimum": 1, "maximum": 10000,
                       "description": "issues listed (default 200); counts are always complete"},
    },
}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["summary", "issues", "coverage"],
    "properties": {
        "summary": {"type": "object", "description": "counts per issue kind and overall coverage share"},
        "issues": {"type": "array", "description": "first issues with record index (0-based), group, kind, detail",
                   "items": {"type": "object", "required": ["record", "group", "kind", "detail"]}},
        "coverage": {"type": "array", "description": "per group: first and last time, expected and present slots",
                     "items": {"type": "object", "required": ["group", "records", "expected_slots",
                                                              "present_slots", "share"]}},
    },
}
KINDS = ("missing_field", "unreadable_timestamp", "out_of_order", "duplicate_id", "sequence_gap",
         "sequence_repeat", "time_gap")


def moment(value) -> "datetime.datetime | None":
    text = str(value) if value is not None else ""
    day = parse_date(text)
    if day is not None:
        return datetime.datetime.combine(day, datetime.time())
    stamp = parse_date_time(text)
    if stamp is None:
        return None
    if stamp.tzinfo is not None:
        stamp = stamp.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return stamp


def slot(stamp: datetime.datetime, interval: str):
    return stamp.date() if interval == "day" else stamp.replace(minute=0, second=0, microsecond=0)


def slot_range(first, last, interval: str) -> list:
    step = datetime.timedelta(days=1) if interval == "day" else datetime.timedelta(hours=1)
    slots, current = [], first
    while current <= last and len(slots) <= 100000:
        slots.append(current)
        current += step
    return slots


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    records = payload["records"]
    for key in ("timestamp_field", "id_field", "sequence_field", "group_field"):
        if key in payload and not any(payload[key] in record for record in records):
            raise KitRefusal("field_absent", f"{key} {payload[key]}")
    period = None
    if "period" in payload:
        start, end = parse_date(payload["period"]["start"]), parse_date(payload["period"]["end"])
        if start is None or end is None or end < start:
            raise KitRefusal("invalid_period", "use YYYY-MM-DD with end on or after start")
        period = (start, end)
    interval = payload.get("expected_interval")
    limit = payload.get("max_issues", 200)
    issues, counts = [], {kind: 0 for kind in KINDS}

    def note(index, group, kind, detail):
        counts[kind] += 1
        if len(issues) < limit:
            issues.append({"record": index, "group": group, "kind": kind, "detail": detail})

    groups = {}
    seen_ids = {}
    for index, record in enumerate(records):
        group = str(record.get(payload["group_field"], "")) if "group_field" in payload else "all"
        groups.setdefault(group, []).append(index)
        for name in payload.get("required_fields", []):
            if record.get(name) is None or str(record.get(name)).strip() == "":
                note(index, group, "missing_field", name)
        if "id_field" in payload and record.get(payload["id_field"]) not in (None, ""):
            key = str(record[payload["id_field"]])
            if key in seen_ids:
                note(index, group, "duplicate_id", f"{key} also at record {seen_ids[key]}")
            else:
                seen_ids[key] = index
    coverage = []
    for group, indexes in groups.items():
        stamps = []
        previous = None
        for index in indexes:
            stamp = moment(records[index].get(payload["timestamp_field"]))
            if stamp is None:
                note(index, group, "unreadable_timestamp", str(records[index].get(payload["timestamp_field"])))
                continue
            if previous is not None and stamp < previous:
                note(index, group, "out_of_order", f"{stamp.isoformat()} before {previous.isoformat()}")
            previous = stamp if previous is None or stamp > previous else previous
            stamps.append(stamp)
        if "sequence_field" in payload:
            last_number = None
            for index in indexes:
                value = records[index].get(payload["sequence_field"])
                if isinstance(value, bool) or not isinstance(value, int):
                    continue
                if last_number is not None:
                    if value == last_number:
                        note(index, group, "sequence_repeat", str(value))
                    elif value > last_number + 1:
                        missing = (f"{last_number + 1} missing" if value == last_number + 2
                                   else f"{last_number + 1} to {value - 1} missing")
                        note(index, group, "sequence_gap", missing)
                last_number = value if last_number is None or value > last_number else last_number
        row = {"group": group, "records": len(indexes), "expected_slots": 0, "present_slots": 0, "share": None}
        if stamps:
            row["first"], row["last"] = min(stamps).isoformat(), max(stamps).isoformat()
        if interval and (stamps or period):
            present = sorted({slot(stamp, interval) for stamp in stamps})
            if period:
                first = datetime.datetime.combine(period[0], datetime.time())
                last = datetime.datetime.combine(period[1], datetime.time(23))
            else:
                first, last = min(stamps), max(stamps)
            expected = slot_range(slot(first, interval), slot(last, interval), interval)
            present_set = set(present)
            missing = [value for value in expected if value not in present_set]
            row.update({"expected_slots": len(expected), "present_slots": len(present_set & set(expected)),
                        "share": round(len(present_set & set(expected)) / len(expected), 4) if expected else None})
            runs, start = [], None
            for position, value in enumerate(missing):
                if start is None:
                    start = value
                following = missing[position + 1] if position + 1 < len(missing) else None
                step = datetime.timedelta(days=1) if interval == "day" else datetime.timedelta(hours=1)
                if following is None or following - value != step:
                    runs.append((start, value))
                    start = None
            for begin, end in runs:
                note(None, group, "time_gap", begin.isoformat() if begin == end
                     else f"{begin.isoformat()} to {end.isoformat()}")
        coverage.append(row)
    shares = [row["share"] for row in coverage if row["share"] is not None]
    summary = {"records": len(records), "groups": len(groups), **counts,
               "coverage_share": round(sum(row["present_slots"] for row in coverage)
                                       / sum(row["expected_slots"] for row in coverage), 4) if shares else None}
    return {"summary": summary, "issues": issues, "coverage": coverage}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
