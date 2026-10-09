"""Program capacity and budget: participants, staffing, cost, revenue and break-even for a session-based program.

Each session seats the expected participants up to the venue capacity. Staff per session is the larger of the
minimum staff and participants divided by the participants-per-staff ratio, rounded up. Costs are staff hours, fixed
costs per session and per program, and a variable cost per participant; revenue is fees plus a subsidy. Scenarios
override named fields of the base program, so low and high attendance or another venue are compared in one run. A
pure function of its JSON input; the command line reads standard input and writes standard output.
"""
from __future__ import annotations

import math

from kit_schema import KitRefusal, check, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "unknown_scenario_field": "a scenario changes a field the program does not have",
    "duplicate_scenario_name": "two scenarios share a name, or a scenario is named base",
    "scenario_value_invalid": "a scenario sets a field to a value the program schema refuses",
}
_NUMBER = {"type": "number", "minimum": 0, "maximum": 1e9}
_PROGRAM = {
    "type": "object", "additionalProperties": False,
    "required": ["sessions", "hours_per_session", "venue_capacity", "expected_participants", "participants_per_staff",
                 "staff_hourly_rate", "fee_per_participant"],
    "properties": {
        "sessions": {"type": "integer", "minimum": 1, "maximum": 10000},
        "hours_per_session": {"type": "number", "exclusiveMinimum": 0, "maximum": 24},
        "venue_capacity": {"type": "integer", "minimum": 1, "maximum": 100000},
        "expected_participants": {"type": "integer", "minimum": 0, "maximum": 1000000},
        "participants_per_staff": {"type": "number", "exclusiveMinimum": 0, "maximum": 10000},
        "minimum_staff": {"type": "integer", "minimum": 0, "maximum": 10000},
        "staff_hourly_rate": _NUMBER, "fixed_cost_per_session": _NUMBER, "fixed_cost_program": _NUMBER,
        "variable_cost_per_participant": _NUMBER, "fee_per_participant": _NUMBER, "subsidy": _NUMBER,
    },
}
INPUT_SCHEMA = {
    "type": "object", "required": ["program"], "additionalProperties": False,
    "properties": {
        "program": {"$ref": "#/$defs/program", "description":
                    "sessions, hours, venue capacity, expected participants per session, staffing ratio and "
                    "minimum, staff rate, fixed and variable costs, fee and subsidy"},
        "scenarios": {"type": "array", "maxItems": 50, "description": "named overrides of program fields",
                      "items": {"type": "object", "required": ["name", "changes"], "additionalProperties": False,
                                "properties": {"name": {"type": "string", "minLength": 1},
                                               "changes": {"type": "object", "minProperties": 1}}}},
    },
    "$defs": {"program": _PROGRAM},
}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["scenarios"],
    "properties": {"scenarios": {"type": "array", "description": "base first, then each scenario in input order",
                                 "items": {"type": "object", "required": [
                                     "name", "participants_per_session", "turned_away_per_session",
                                     "staff_per_session", "cost", "revenue", "net", "cost_per_participant",
                                     "break_even_fee", "break_even_participants_per_session"]}}},
}


def money(value: float) -> float:
    return round(value + 0.0, 2)


def costs_for(program: dict, participants: int) -> dict:
    """Cost lines for one number of participants per session."""
    sessions = program["sessions"]
    staff = max(program.get("minimum_staff", 0),
                math.ceil(participants / program["participants_per_staff"]) if participants else 0)
    staff_cost = staff * program["hours_per_session"] * program["staff_hourly_rate"] * sessions
    fixed = program.get("fixed_cost_per_session", 0) * sessions + program.get("fixed_cost_program", 0)
    variable = program.get("variable_cost_per_participant", 0) * participants * sessions
    return {"staff": staff, "staff_cost": staff_cost, "fixed": fixed, "variable": variable,
            "total": staff_cost + fixed + variable}


def break_even_participants(program: dict):
    """The smallest participants per session (1 to capacity) whose fees and subsidy cover the cost, or None."""
    for count in range(1, program["venue_capacity"] + 1):
        cost = costs_for(program, count)["total"]
        if program["fee_per_participant"] * count * program["sessions"] + program.get("subsidy", 0) >= cost - 1e-9:
            return count
    return None


def evaluate(name: str, program: dict) -> dict:
    participants = min(program["expected_participants"], program["venue_capacity"])
    cost = costs_for(program, participants)
    total_participants = participants * program["sessions"]
    fees = program["fee_per_participant"] * total_participants
    subsidy = program.get("subsidy", 0)
    return {
        "name": name, "participants_per_session": participants,
        "turned_away_per_session": max(0, program["expected_participants"] - program["venue_capacity"]),
        "staff_per_session": cost["staff"],
        "cost": {"staff": money(cost["staff_cost"]), "fixed": money(cost["fixed"]),
                 "variable": money(cost["variable"]), "total": money(cost["total"])},
        "revenue": {"fees": money(fees), "subsidy": money(subsidy), "total": money(fees + subsidy)},
        "net": money(fees + subsidy - cost["total"]),
        "cost_per_participant": money(cost["total"] / total_participants) if total_participants else None,
        "break_even_fee": money(max(0.0, (cost["total"] - subsidy) / total_participants))
        if total_participants else None,
        "break_even_participants_per_session": break_even_participants(program),
    }


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    base = payload["program"]
    names = ["base"] + [scenario["name"] for scenario in payload.get("scenarios", [])]
    if len(set(names)) != len(names):
        raise KitRefusal("duplicate_scenario_name", "names must be distinct and not base")
    rows = [evaluate("base", base)]
    for scenario in payload.get("scenarios", []):
        unknown = sorted(set(scenario["changes"]) - set(_PROGRAM["properties"]))
        if unknown:
            raise KitRefusal("unknown_scenario_field", f"{scenario['name']}: {', '.join(unknown)}")
        changed = {**base, **scenario["changes"]}
        check(changed, _PROGRAM, reason="scenario_value_invalid")
        rows.append(evaluate(scenario["name"], changed))
    return {"scenarios": rows}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
