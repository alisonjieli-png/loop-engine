"""Service request resolution times: how long a city takes to close 311 requests, per category.

Each row is one request with its category, when it was opened and when it was closed (null while still open). Per
category and over all requests: requests, closed, still open, closed before opened (a data error, left out of the
times and counted), the median and the 90th percentile (nearest rank) of hours to close, and the share closed within
the target hours (72 unless the input names another target). Timestamps are ISO 8601 (a date, or a date and time
with optional seconds, fraction and offset; Z is UTC) or US style MM/DD/YYYY hh:mm[:ss] with an optional AM or PM.
A timestamp with an offset is converted to UTC; one without is taken as written. A pure function of its JSON
input; the command line reads standard input and writes standard output.
"""
from __future__ import annotations

import datetime
import fractions
import math
import re
import statistics

from kit_schema import KitRefusal, check, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "timestamp_unreadable": "a timestamp is neither ISO 8601 nor MM/DD/YYYY hh:mm:ss AM/PM",
    "duplicate_id": "two requests share an id",
}
#: The target when the input names none: three days.
DEFAULT_TARGET_HOURS = 72
#: The percentile reported beside the median, by the nearest-rank method.
PERCENTILE = fractions.Fraction(9, 10)
SECONDS_PER_HOUR = 3600
_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,6}))?)?)?"
                  r"(Z|[+-]\d{2}:?\d{2})?")
_US = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})(?: (\d{1,2}):(\d{2})(?::(\d{2}))?(?: ?([AaPp])[Mm])?)?")
_AFTERNOON = "p"
_UTC_MARK = "Z"
_STATISTIC = {"type": ["number", "null"]}
_SUMMARY = ["requests", "closed", "still_open", "closed_before_opened", "median_hours", "p90_hours",
            "share_closed_within_target"]
INPUT_SCHEMA = {
    "type": "object", "required": ["rows"], "additionalProperties": False,
    "properties": {
        "rows": {"type": "array", "minItems": 1, "maxItems": 500000,
                 "description": "one service request: its id, category, opened time and closed time or null",
                 "items": {"type": "object", "required": ["id", "category", "opened", "closed"],
                           "additionalProperties": False,
                           "properties": {"id": {"type": "string", "minLength": 1},
                                          "category": {"type": "string", "minLength": 1},
                                          "opened": {"type": "string", "minLength": 1},
                                          "closed": {"type": ["string", "null"]}}}},
        "target_hours": {"type": "number", "exclusiveMinimum": 0,
                         "description": "hours within which a request counts as closed on time (default 72)"},
    },
}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["target_hours", "categories", "overall"],
    "properties": {
        "target_hours": {"type": "number"},
        "categories": {"type": "array", "description": "one summary per category, in category order",
                       "items": {"type": "object", "required": ["category"] + _SUMMARY}},
        "overall": {"type": "object", "required": list(_SUMMARY),
                    "properties": {"median_hours": _STATISTIC, "p90_hours": _STATISTIC,
                                   "share_closed_within_target": _STATISTIC}},
    },
}


def number(value):
    """A statistic for JSON: rounded to six decimals, an integer when it is whole, None stays None."""
    if value is None:
        return None
    value = round(float(value), 6)
    return int(value) if value.is_integer() else value


def parse_timestamp(text: str) -> datetime.datetime:
    """A naive datetime from an ISO 8601 or a US style timestamp; an offset is applied, giving UTC."""
    text = text.strip()
    try:
        match = _ISO.fullmatch(text)
        if match:
            year, month, day, hour, minute, second, fraction, offset = match.groups()
            moment = datetime.datetime(int(year), int(month), int(day), int(hour or 0), int(minute or 0),
                                       int(second or 0), int((fraction or "0").ljust(6, "0")))
            if offset and offset != _UTC_MARK:
                sign = -1 if offset.startswith("-") else 1
                digits = offset[1:].replace(":", "")
                moment -= sign * datetime.timedelta(hours=int(digits[:2]), minutes=int(digits[2:]))
            return moment
        match = _US.fullmatch(text)
        if match:
            month, day, year, hour, minute, second, half = match.groups()
            hour = int(hour or 0)
            if half is not None:
                if not 1 <= hour <= 12:
                    raise ValueError("a 12-hour clock runs from 1 to 12")
                hour = hour % 12 + (12 if half.lower() == _AFTERNOON else 0)
            return datetime.datetime(int(year), int(month), int(day), hour, int(minute or 0), int(second or 0))
    except ValueError:
        pass
    raise KitRefusal("timestamp_unreadable", text[:60])


def hours_between(opened: datetime.datetime, closed: datetime.datetime) -> fractions.Fraction:
    delta = closed - opened
    seconds = fractions.Fraction(delta.days * 86400 + delta.seconds) + fractions.Fraction(delta.microseconds,
                                                                                          1000000)
    return seconds / SECONDS_PER_HOUR


def summary(requests: int, still_open: int, backwards: int, hours: list, target) -> dict:
    ordered = sorted(hours)
    closed = len(ordered)
    rank = math.ceil(PERCENTILE * closed) if closed else 0
    return {"requests": requests, "closed": closed, "still_open": still_open, "closed_before_opened": backwards,
            "median_hours": number(statistics.median(ordered)) if closed else None,
            "p90_hours": number(ordered[rank - 1]) if closed else None,
            "share_closed_within_target": number(fractions.Fraction(sum(1 for value in ordered if value <= target),
                                                                     closed)) if closed else None}


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    target = fractions.Fraction(payload.get("target_hours", DEFAULT_TARGET_HOURS))
    seen, groups = set(), {}
    for row in payload["rows"]:
        if row["id"] in seen:
            raise KitRefusal("duplicate_id", row["id"])
        seen.add(row["id"])
        group = groups.setdefault(row["category"], {"requests": 0, "still_open": 0, "backwards": 0, "hours": []})
        group["requests"] += 1
        opened = parse_timestamp(row["opened"])
        if row["closed"] is None:
            group["still_open"] += 1
            continue
        closed = parse_timestamp(row["closed"])
        if closed < opened:
            group["backwards"] += 1
            continue
        group["hours"].append(hours_between(opened, closed))
    categories = [{"category": name, **summary(group["requests"], group["still_open"], group["backwards"],
                                                group["hours"], target)} for name, group in sorted(groups.items())]
    overall = summary(sum(group["requests"] for group in groups.values()),
                      sum(group["still_open"] for group in groups.values()),
                      sum(group["backwards"] for group in groups.values()),
                      [value for group in groups.values() for value in group["hours"]], target)
    return {"target_hours": number(target), "categories": categories, "overall": overall}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
