"""Shift roster builder: assign staff to shifts within skills, availability, weekly hours and rest limits.

Shifts are filled in start order. For each open position the eligible person with the fewest hours assigned so far
is chosen (ties by id), so work spreads evenly. A person is eligible when they hold the shift's skill, are not
unavailable that date, have no overlapping shift, keep the minimum rest before and after, stay within their weekly
hour limit (ISO week of the shift start) and within their shift count limit. The method is greedy and explains every
gap; it does not search for an optimal roster. A pure function of its JSON input; the command line reads standard
input and writes standard output.
"""
from __future__ import annotations

import datetime

from kit_schema import KitRefusal, check, parse_date, parse_time, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "duplicate_id": "two shifts or two staff members share an id",
    "invalid_date_or_time": "a date is not a real calendar date or a time is not HH:MM",
    "shift_too_long": "a shift lasts more than 24 hours or no time at all",
}
INPUT_SCHEMA = {
    "type": "object", "required": ["shifts", "staff"], "additionalProperties": False,
    "properties": {
        "shifts": {"type": "array", "minItems": 1, "maxItems": 3000, "description":
                   "shifts with a date, start and end (an end at or before the start ends the next day), the number "
                   "of people required and an optional skill",
                   "items": {"type": "object", "required": ["id", "date", "start", "end", "required"],
                             "additionalProperties": False,
                             "properties": {"id": {"type": "string", "minLength": 1}, "date": {"type": "string"},
                                            "start": {"type": "string"}, "end": {"type": "string"},
                                            "required": {"type": "integer", "minimum": 1, "maximum": 100},
                                            "skill": {"type": "string"}}}},
        "staff": {"type": "array", "minItems": 1, "maxItems": 2000, "description":
                  "people with skills, a weekly hour limit, optional unavailable dates and a shift count limit",
                  "items": {"type": "object", "required": ["id", "max_hours_per_week"], "additionalProperties": False,
                            "properties": {"id": {"type": "string", "minLength": 1}, "name": {"type": "string"},
                                           "skills": {"type": "array", "items": {"type": "string"}},
                                           "max_hours_per_week": {"type": "number", "minimum": 0, "maximum": 168},
                                           "max_shifts": {"type": "integer", "minimum": 0},
                                           "unavailable_dates": {"type": "array", "items": {"type": "string"}}}}},
        "min_rest_hours": {"type": "number", "minimum": 0, "maximum": 48,
                           "description": "minimum hours between two shifts of one person (default 10)"},
    },
}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["assignments", "unfilled", "hours", "filled_share"],
    "properties": {
        "assignments": {"type": "array", "description": "staff ids per shift, in shift start order",
                        "items": {"type": "object", "required": ["shift", "staff"],
                                  "properties": {"shift": {"type": "string"},
                                                 "staff": {"type": "array", "items": {"type": "string"}}}}},
        "unfilled": {"type": "array", "description": "shifts short of people, with the count and the main blocker",
                     "items": {"type": "object", "required": ["shift", "missing", "blockers"],
                               "properties": {"shift": {"type": "string"}, "missing": {"type": "integer"},
                                              "blockers": {"type": "object"}}}},
        "hours": {"type": "array", "description": "assigned hours and shifts per person, in input order",
                  "items": {"type": "object", "required": ["staff", "hours", "shifts"],
                            "properties": {"staff": {"type": "string"}, "hours": {"type": "number"},
                                           "shifts": {"type": "integer"}}}},
        "filled_share": {"type": "number", "description": "positions filled divided by positions required"},
    },
}


def shift_window(shift: dict) -> tuple:
    """(start, end) as datetimes; an end at or before the start belongs to the next day."""
    day, start, end = parse_date(shift["date"]), parse_time(shift["start"]), parse_time(shift["end"])
    if day is None or start is None or end is None:
        raise KitRefusal("invalid_date_or_time", shift["id"])
    begin = datetime.datetime.combine(day, datetime.time()) + datetime.timedelta(minutes=start)
    finish = datetime.datetime.combine(day, datetime.time()) + datetime.timedelta(minutes=end)
    if finish <= begin:
        finish += datetime.timedelta(days=1)
    if finish - begin > datetime.timedelta(hours=24):
        raise KitRefusal("shift_too_long", shift["id"])
    return begin, finish


def blocker(person: dict, shift: dict, window: tuple, state: dict, rest: datetime.timedelta) -> str:
    """Why ``person`` cannot take ``shift`` now, or an empty string when they can."""
    begin, finish = window
    hours = (finish - begin).total_seconds() / 3600
    if shift.get("skill") and shift["skill"] not in person.get("skills", []):
        return "missing_skill"
    if shift["date"] in person.get("unavailable_dates", []):
        return "unavailable"
    for other_begin, other_finish in state["windows"]:
        if begin < other_finish + rest and other_begin < finish + rest:
            return "overlap_or_rest"
    week = begin.isocalendar()[:2]
    if state["week_hours"].get(week, 0.0) + hours > person["max_hours_per_week"] + 1e-9:
        return "weekly_hours"
    if "max_shifts" in person and len(state["windows"]) >= person["max_shifts"]:
        return "shift_limit"
    return ""


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    shifts, staff = payload["shifts"], payload["staff"]
    for label, rows in (("shift", shifts), ("staff", staff)):
        ids = [row["id"] for row in rows]
        if len(set(ids)) != len(ids):
            raise KitRefusal("duplicate_id", f"repeated {label} id")
    for person in staff:
        if any(parse_date(text) is None for text in person.get("unavailable_dates", [])):
            raise KitRefusal("invalid_date_or_time", person["id"])
    rest = datetime.timedelta(hours=payload.get("min_rest_hours", 10))
    windows = {shift["id"]: shift_window(shift) for shift in shifts}
    ordered = sorted(shifts, key=lambda shift: (windows[shift["id"]][0], shifts.index(shift)))
    state = {person["id"]: {"windows": [], "week_hours": {}, "hours": 0.0} for person in staff}
    assignments, unfilled, filled = [], [], 0
    for shift in ordered:
        window = windows[shift["id"]]
        hours = (window[1] - window[0]).total_seconds() / 3600
        chosen, blockers = [], {}
        for _position in range(shift["required"]):
            candidates = []
            for person in staff:
                if person["id"] in chosen:
                    continue
                reason = blocker(person, shift, window, state[person["id"]], rest)
                if reason:
                    continue
                candidates.append((state[person["id"]]["hours"], person["id"]))
            if not candidates:
                break
            _hours, person_id = min(candidates)
            chosen.append(person_id)
            record = state[person_id]
            record["windows"].append(window)
            week = window[0].isocalendar()[:2]
            record["week_hours"][week] = record["week_hours"].get(week, 0.0) + hours
            record["hours"] += hours
        if len(chosen) < shift["required"]:
            for person in staff:
                if person["id"] not in chosen:
                    reason = blocker(person, shift, window, state[person["id"]], rest) or "already_assigned"
                    blockers[reason] = blockers.get(reason, 0) + 1
            unfilled.append({"shift": shift["id"], "missing": shift["required"] - len(chosen),
                             "blockers": dict(sorted(blockers.items()))})
        filled += len(chosen)
        assignments.append({"shift": shift["id"], "staff": chosen})
    total = sum(shift["required"] for shift in shifts)
    hours = [{"staff": person["id"], "hours": round(state[person["id"]]["hours"], 2),
              "shifts": len(state[person["id"]]["windows"])} for person in staff]
    return {"assignments": assignments, "unfilled": unfilled, "hours": hours,
            "filled_share": round(filled / total, 4)}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
