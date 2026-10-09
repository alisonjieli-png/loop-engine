"""Earned value status: planned value, earned value, variances, performance indices and forecasts per work package.

For each work package with a budget at completion (BAC), a planned percent and an earned (physical) percent at the
status date and the actual cost to date: PV = BAC x planned, EV = BAC x earned, SV = EV - PV, CV = EV - AC,
SPI = EV / PV, CPI = EV / AC, EAC = BAC / CPI, ETC = EAC - AC, VAC = BAC - EAC and TCPI = (BAC - EV) / (BAC - AC).
An index is null when its denominator is zero, and TCPI is null once the actual cost has reached the budget. Status uses index thresholds. Totals use the summed values. A pure
function of its JSON input; the command line reads standard input and writes standard output.
"""
from __future__ import annotations

from kit_schema import KitRefusal, check, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "duplicate_package_id": "two work packages share an id",
    "thresholds_out_of_order": "the red index threshold is not below the amber threshold",
}
INPUT_SCHEMA = {
    "type": "object", "required": ["work_packages"], "additionalProperties": False,
    "properties": {
        "work_packages": {"type": "array", "minItems": 1, "maxItems": 5000, "description":
                          "packages with budget at completion, planned and earned percent at the status date and "
                          "actual cost to date",
                          "items": {"type": "object", "required": ["id", "budget", "planned_percent",
                                                                   "earned_percent", "actual_cost"],
                                    "additionalProperties": False,
                                    "properties": {"id": {"type": "string", "minLength": 1},
                                                   "name": {"type": "string"},
                                                   "budget": {"type": "number", "exclusiveMinimum": 0},
                                                   "planned_percent": {"type": "number", "minimum": 0,
                                                                       "maximum": 100},
                                                   "earned_percent": {"type": "number", "minimum": 0, "maximum": 100},
                                                   "actual_cost": {"type": "number", "minimum": 0}}}},
        "amber_index": {"type": "number", "exclusiveMinimum": 0, "maximum": 1,
                        "description": "an SPI or CPI below this is amber (default 0.95)"},
        "red_index": {"type": "number", "exclusiveMinimum": 0, "maximum": 1,
                      "description": "an SPI or CPI below this is red (default 0.85)"},
    },
}
_VALUES = {"type": "object", "required": ["bac", "pv", "ev", "ac", "sv", "cv", "spi", "cpi", "eac", "etc", "vac",
                                          "tcpi", "status"],
           "properties": {"status": {"enum": ["green", "amber", "red", "not_started"]}}}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["packages", "total"],
    "properties": {"packages": {"type": "array", "items": _VALUES,
                                "description": "one row per package in input order, with its id"},
                   "total": {**_VALUES, "description": "the same measures for the summed values"}},
}


def ratio(numerator: float, denominator: float):
    return round(numerator / denominator, 4) + 0.0 if abs(denominator) > 1e-12 else None


def measures(bac: float, pv: float, ev: float, ac: float, amber: float, red: float) -> dict:
    spi, cpi = ratio(ev, pv), ratio(ev, ac)
    eac = round(bac / (ev / ac), 2) if ev > 0 and ac > 0 else None
    indices = [index for index in (spi, cpi) if index is not None]
    if pv == 0 and ev == 0 and ac == 0:
        status = "not_started"
    elif any(index < red for index in indices):
        status = "red"
    elif any(index < amber for index in indices):
        status = "amber"
    else:
        status = "green"
    return {"bac": round(bac, 2), "pv": round(pv, 2), "ev": round(ev, 2), "ac": round(ac, 2),
            "sv": round(ev - pv, 2), "cv": round(ev - ac, 2), "spi": spi, "cpi": cpi, "eac": eac,
            "etc": round(eac - ac, 2) if eac is not None else None,
            "vac": round(bac - eac, 2) if eac is not None else None,
            "tcpi": ratio(bac - ev, bac - ac) if bac - ac > 1e-9 else None, "status": status}


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    amber, red = payload.get("amber_index", 0.95), payload.get("red_index", 0.85)
    if red >= amber:
        raise KitRefusal("thresholds_out_of_order", f"red {red} must be below amber {amber}")
    packages = payload["work_packages"]
    ids = [row["id"] for row in packages]
    if len(set(ids)) != len(ids):
        raise KitRefusal("duplicate_package_id", "work package ids repeat")
    rows, sums = [], [0.0, 0.0, 0.0, 0.0]
    for row in packages:
        bac = float(row["budget"])
        pv, ev, ac = bac * row["planned_percent"] / 100, bac * row["earned_percent"] / 100, float(row["actual_cost"])
        rows.append({"id": row["id"], **measures(bac, pv, ev, ac, amber, red)})
        for index, value in enumerate((bac, pv, ev, ac)):
            sums[index] += value
    return {"packages": rows, "total": measures(*sums, amber, red)}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
