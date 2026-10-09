"""Rate per 100,000: turn counts of events into rates per population, per group and period and per period.

Several SDG indicators are counts per 100,000 people: road traffic deaths (3.6.1), victims of intentional homicide
(16.1.1), victims of human trafficking (16.2.2), people dead, missing or affected by disasters (11.5.1). Each row
holds a group (a city, a district, an age band), a period, a count and the population the count belongs to. The
rate is count / population x per (100,000 unless the input names another base), exact until it is rounded to six
decimals. Each period also gets its total count, total population and pooled rate. A pure function of its JSON
input; the command line reads standard input and writes standard output.
"""
from __future__ import annotations

import fractions

from kit_schema import KitRefusal, check, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "population_not_positive": "a population is zero or negative",
    "negative_count": "a count is negative",
    "duplicate_group_period": "two rows name the same group and period",
}
#: The base of the rates when the input names none.
DEFAULT_PER = 100000
_TEXT = {"type": "string", "minLength": 1}
INPUT_SCHEMA = {
    "type": "object", "required": ["rows"], "additionalProperties": False,
    "properties": {
        "rows": {"type": "array", "minItems": 1, "maxItems": 200000,
                 "description": "one count of events for one group in one period, with its population",
                 "items": {"type": "object", "required": ["group", "period", "count", "population"],
                           "additionalProperties": False,
                           "properties": {"group": _TEXT, "period": _TEXT, "count": {"type": "number"},
                                          "population": {"type": "number"}}}},
        "per": {"type": "number", "exclusiveMinimum": 0, "description": "the population base of the rate "
                                                                         "(default 100000)"},
    },
}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["per", "rows", "periods"],
    "properties": {
        "per": {"type": "number"},
        "rows": {"type": "array", "description": "each input row with its rate, by period then group",
                 "items": {"type": "object", "required": ["group", "period", "count", "population", "rate"]}},
        "periods": {"type": "array", "description": "per period: groups, total count, total population, pooled rate",
                    "items": {"type": "object", "required": ["period", "groups", "count", "population", "rate"]}},
    },
}


def number(value):
    """A value for JSON: rounded to six decimals, an integer when it is whole."""
    value = round(float(value), 6)
    return int(value) if value.is_integer() else value


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    per = fractions.Fraction(payload.get("per", DEFAULT_PER))
    rows, seen, periods = [], set(), {}
    for row in payload["rows"]:
        key = (row["period"], row["group"])
        if key in seen:
            raise KitRefusal("duplicate_group_period", f"group {row['group']}, period {row['period']}")
        seen.add(key)
        if row["population"] <= 0:
            raise KitRefusal("population_not_positive", f"group {row['group']}, period {row['period']}")
        if row["count"] < 0:
            raise KitRefusal("negative_count", f"group {row['group']}, period {row['period']}")
        count, population = fractions.Fraction(row["count"]), fractions.Fraction(row["population"])
        rows.append((key, {"group": row["group"], "period": row["period"], "count": number(count),
                           "population": number(population), "rate": number(count / population * per)}))
        total = periods.setdefault(row["period"], [0, fractions.Fraction(0), fractions.Fraction(0)])
        total[0] += 1
        total[1] += count
        total[2] += population
    return {"per": number(per), "rows": [row for _key, row in sorted(rows, key=lambda item: item[0])],
            "periods": [{"period": period, "groups": groups, "count": number(count), "population": number(population),
                         "rate": number(count / population * per)}
                        for period, (groups, count, population) in sorted(periods.items())]}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
