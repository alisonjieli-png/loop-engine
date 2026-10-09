"""Migration deaths and missing: the count behind SDG indicator 10.7.3 from incident records.

Indicator 10.7.3 counts people who died or disappeared in the process of migration towards an international
destination. Each row is one incident with its year, region, the number of dead and the number of missing; a null
count is taken as zero and counted as unreported, so a total never hides a gap. Per (year, region), per year and in
total: incidents, dead, missing, dead and missing together, and incidents whose dead or missing count was not
reported. A pure function of its JSON input; the command line reads standard input and writes standard output.
"""
from __future__ import annotations

from kit_schema import KitRefusal, check, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "negative_count": "a dead or missing count is negative",
    "duplicate_incident": "two rows share an incident id",
}
_COUNT = {"type": ["integer", "null"]}
_TOTALS = ["incidents", "dead", "missing", "dead_and_missing", "unreported_dead", "unreported_missing"]
INPUT_SCHEMA = {
    "type": "object", "required": ["rows"], "additionalProperties": False,
    "properties": {
        "rows": {"type": "array", "minItems": 1, "maxItems": 500000,
                 "description": "one incident: its id, year, region and counts of dead and missing people",
                 "items": {"type": "object", "required": ["incident_id", "year", "region", "dead", "missing"],
                           "additionalProperties": False,
                           "properties": {"incident_id": {"type": "string", "minLength": 1},
                                          "year": {"type": "integer", "minimum": 1900, "maximum": 2200},
                                          "region": {"type": "string", "minLength": 1},
                                          "dead": _COUNT, "missing": _COUNT}}},
    },
}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["by_year_region", "by_year", "total"],
    "properties": {
        "by_year_region": {"type": "array", "description": "totals per year and region, by year then region",
                           "items": {"type": "object", "required": ["year", "region"] + _TOTALS}},
        "by_year": {"type": "array", "description": "totals per year",
                    "items": {"type": "object", "required": ["year"] + _TOTALS}},
        "total": {"type": "object", "required": list(_TOTALS)},
    },
}


def _empty() -> dict:
    return dict.fromkeys(_TOTALS, 0)


def _add(totals: dict, dead, missing) -> None:
    totals["incidents"] += 1
    totals["dead"] += dead or 0
    totals["missing"] += missing or 0
    totals["dead_and_missing"] += (dead or 0) + (missing or 0)
    totals["unreported_dead"] += dead is None
    totals["unreported_missing"] += missing is None


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    seen, by_pair, by_year, total = set(), {}, {}, _empty()
    for row in payload["rows"]:
        if row["incident_id"] in seen:
            raise KitRefusal("duplicate_incident", row["incident_id"])
        seen.add(row["incident_id"])
        dead = None if row["dead"] is None else int(row["dead"])
        missing = None if row["missing"] is None else int(row["missing"])
        if (dead is not None and dead < 0) or (missing is not None and missing < 0):
            raise KitRefusal("negative_count", row["incident_id"])
        year = int(row["year"])
        _add(by_pair.setdefault((year, row["region"]), _empty()), dead, missing)
        _add(by_year.setdefault(year, _empty()), dead, missing)
        _add(total, dead, missing)
    return {"by_year_region": [{"year": year, "region": region, **totals}
                               for (year, region), totals in sorted(by_pair.items())],
            "by_year": [{"year": year, **totals} for year, totals in sorted(by_year.items())], "total": total}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
