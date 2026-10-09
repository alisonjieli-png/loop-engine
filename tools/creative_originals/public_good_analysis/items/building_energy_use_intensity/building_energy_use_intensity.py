"""Building energy use intensity: site energy per unit of floor area, per building and per property type.

Each row is one building with its property type, gross floor area and annual site energy use. The energy use
intensity (EUI) is site energy / floor area in the units the input names (kBtu per square foot by default, the unit
US benchmarking ordinances publish). Per property type: buildings, the median and the 25th and 75th percentiles
(linear interpolation between closest ranks), the high fence Q3 + 3 x IQR and the buildings above it, which are
worth checking for a data error before they are compared. A pure function of its JSON input; the command line reads
standard input and writes standard output.
"""
from __future__ import annotations

import fractions

from kit_schema import KitRefusal, check, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "floor_area_not_positive": "a floor area is zero or negative",
    "negative_energy": "a site energy use is negative",
    "duplicate_building": "two rows share a building id",
}
#: Units of floor area and energy, and the ones used when the input names none.
AREA_UNITS = ("square_feet", "square_metres")
ENERGY_UNITS = ("kbtu", "kwh")
DEFAULT_AREA_UNIT, DEFAULT_ENERGY_UNIT = AREA_UNITS[0], ENERGY_UNITS[0]
#: The interquartile range multiple of the high fence: 3 marks extreme values, not ordinary spread.
FENCE_MULTIPLE = 3
QUARTILES = (fractions.Fraction(1, 4), fractions.Fraction(1, 2), fractions.Fraction(3, 4))
INPUT_SCHEMA = {
    "type": "object", "required": ["rows"], "additionalProperties": False,
    "properties": {
        "rows": {"type": "array", "minItems": 1, "maxItems": 200000,
                 "description": "one building: its id, property type, gross floor area and annual site energy use",
                 "items": {"type": "object", "required": ["building_id", "property_type", "floor_area", "site_energy"],
                           "additionalProperties": False,
                           "properties": {"building_id": {"type": "string", "minLength": 1},
                                          "property_type": {"type": "string", "minLength": 1},
                                          "floor_area": {"type": "number"}, "site_energy": {"type": "number"}}}},
        "area_unit": {"enum": list(AREA_UNITS), "description": "unit of floor_area (default square_feet)"},
        "energy_unit": {"enum": list(ENERGY_UNITS), "description": "unit of site_energy (default kbtu)"},
    },
}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["energy_unit", "area_unit", "buildings", "property_types"],
    "properties": {
        "energy_unit": {"type": "string"},
        "area_unit": {"type": "string"},
        "buildings": {"type": "array", "description": "each building's EUI, in building id order",
                      "items": {"type": "object", "required": ["building_id", "property_type", "eui"]}},
        "property_types": {"type": "array", "description": "one summary per property type, in name order",
                           "items": {"type": "object",
                                     "required": ["property_type", "buildings", "median", "p25", "p75",
                                                  "high_fence", "high_outliers"],
                                     "properties": {"high_outliers": {"type": "array", "items": {"type": "string"}}}}},
    },
}


def number(value):
    """A value for JSON: rounded to six decimals, an integer when it is whole."""
    value = round(float(value), 6)
    return int(value) if value.is_integer() else value


def percentile(ordered: list, share: fractions.Fraction) -> fractions.Fraction:
    """Linear interpolation between closest ranks of sorted values (position share x (n - 1))."""
    position = share * (len(ordered) - 1)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    seen, buildings, by_type = set(), [], {}
    for row in payload["rows"]:
        if row["building_id"] in seen:
            raise KitRefusal("duplicate_building", row["building_id"])
        seen.add(row["building_id"])
        if row["floor_area"] <= 0:
            raise KitRefusal("floor_area_not_positive", row["building_id"])
        if row["site_energy"] < 0:
            raise KitRefusal("negative_energy", row["building_id"])
        intensity = fractions.Fraction(row["site_energy"]) / fractions.Fraction(row["floor_area"])
        buildings.append({"building_id": row["building_id"], "property_type": row["property_type"],
                          "eui": number(intensity)})
        by_type.setdefault(row["property_type"], []).append((intensity, row["building_id"]))
    summaries = []
    for name, members in sorted(by_type.items()):
        ordered = sorted(value for value, _identity in members)
        p25, median, p75 = (percentile(ordered, share) for share in QUARTILES)
        fence = p75 + FENCE_MULTIPLE * (p75 - p25)
        summaries.append({"property_type": name, "buildings": len(members), "median": number(median),
                          "p25": number(p25), "p75": number(p75), "high_fence": number(fence),
                          "high_outliers": sorted(identity for value, identity in members if value > fence)})
    return {"energy_unit": payload.get("energy_unit", DEFAULT_ENERGY_UNIT),
            "area_unit": payload.get("area_unit", DEFAULT_AREA_UNIT),
            "buildings": sorted(buildings, key=lambda row: row["building_id"]), "property_types": summaries}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
