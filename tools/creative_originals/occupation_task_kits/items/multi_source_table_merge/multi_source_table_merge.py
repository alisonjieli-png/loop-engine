"""Multi-source table merge: compile one table from several CSV sources with provenance and conflict flags.

Each source maps its own columns to target fields and has a priority (1 wins). Optional unit multipliers convert a
source's numeric fields before merging (for example grams to kilograms). Rows are matched on the key fields. For
every target field the merged row takes the first non-empty value in priority order and records which source gave
it. When sources give different non-empty values for a field (numbers beyond a relative tolerance, text after
trimming and case folding) the field is listed as a conflict with every value. A pure function of its JSON input;
the command line reads standard input and writes standard output.
"""
from __future__ import annotations

import csv
import io
import math

from kit_schema import KitRefusal, check, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "header_missing": "a source's CSV text has no header row",
    "mapping_column_absent": "a source maps a target field to a column its CSV does not have",
    "key_not_mapped": "a source does not map every key field",
    "unknown_target_field": "a mapping or unit names a field that is not a target field",
    "duplicate_key_in_source": "one source holds two rows with the same key",
    "duplicate_source_name": "two sources share a name",
    "unit_on_text_value": "a unit multiplier applies to a value that is not a number",
}
INPUT_SCHEMA = {
    "type": "object", "required": ["target_fields", "key_fields", "sources"], "additionalProperties": False,
    "properties": {
        "target_fields": {"type": "array", "minItems": 1, "maxItems": 200, "items": {"type": "string"},
                          "uniqueItems": True, "description": "fields of the merged table, in output order"},
        "key_fields": {"type": "array", "minItems": 1, "maxItems": 5, "items": {"type": "string"},
                       "description": "target fields that identify a row across sources"},
        "sources": {"type": "array", "minItems": 1, "maxItems": 20, "description":
                    "sources with a name, CSV text, a priority (1 wins), a mapping of target field to source column "
                    "and optional unit multipliers per target field",
                    "items": {"type": "object", "required": ["name", "csv_text", "priority", "mapping"],
                              "additionalProperties": False,
                              "properties": {"name": {"type": "string", "minLength": 1},
                                             "csv_text": {"type": "string", "maxLength": 5000000},
                                             "priority": {"type": "integer", "minimum": 1, "maximum": 100},
                                             "mapping": {"type": "object", "minProperties": 1,
                                                         "additionalProperties": {"type": "string"}},
                                             "units": {"type": "object",
                                                       "additionalProperties": {"type": "number",
                                                                                "exclusiveMinimum": 0}}}}},
        "numeric_tolerance": {"type": "number", "minimum": 0, "maximum": 1,
                              "description": "relative difference below which numbers agree (default 0)"},
    },
}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["rows", "conflicts", "summary"],
    "properties": {
        "rows": {"type": "array", "description": "merged rows in first-seen key order with values and provenance",
                 "items": {"type": "object", "required": ["values", "provenance", "sources"]}},
        "conflicts": {"type": "array", "description": "fields where sources disagree, with every value",
                      "items": {"type": "object", "required": ["key", "field", "values", "chosen"]}},
        "summary": {"type": "object", "description": "rows per source, keys, conflicts, filled share per field"},
    },
}


def as_number(text: str):
    try:
        value = float(text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def same(left: str, right: str, tolerance: float) -> bool:
    a, b = as_number(left), as_number(right)
    if a is not None and b is not None:
        scale = max(abs(a), abs(b))
        return abs(a - b) <= tolerance * scale if scale else True
    return left.strip().casefold() == right.strip().casefold()


def format_number(value: float) -> str:
    value = round(value, 9)
    return str(int(value)) if value.is_integer() else repr(value)


def read_source(source: dict, targets: list, keys: list) -> dict:
    """Key tuple to {target field: value} for one source, after mapping and units."""
    table = [row for row in csv.reader(io.StringIO(source["csv_text"])) if any(cell.strip() for cell in row)]
    if not table:
        raise KitRefusal("header_missing", source["name"])
    header = [name.strip() for name in table[0]]
    for field, column in source["mapping"].items():
        if field not in targets:
            raise KitRefusal("unknown_target_field", f"{source['name']}: {field}")
        if column not in header:
            raise KitRefusal("mapping_column_absent", f"{source['name']}: {column}")
    for field in source.get("units", {}):
        if field not in targets:
            raise KitRefusal("unknown_target_field", f"{source['name']} units: {field}")
    missing_keys = [key for key in keys if key not in source["mapping"]]
    if missing_keys:
        raise KitRefusal("key_not_mapped", f"{source['name']}: {', '.join(missing_keys)}")
    rows = {}
    for line in table[1:]:
        cells = {name: (line[index].strip() if index < len(line) else "") for index, name in enumerate(header)}
        values = {field: cells[column] for field, column in source["mapping"].items()}
        for field, factor in source.get("units", {}).items():
            if values.get(field):
                number = as_number(values[field])
                if number is None:
                    raise KitRefusal("unit_on_text_value", f"{source['name']}: {field} = {values[field]}")
                values[field] = format_number(number * factor)
        key = tuple(values[name] for name in keys)
        if not all(key):
            continue
        if key in rows:
            raise KitRefusal("duplicate_key_in_source", f"{source['name']}: {'|'.join(key)}")
        rows[key] = values
    return rows


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    targets, keys = payload["target_fields"], payload["key_fields"]
    unknown = [key for key in keys if key not in targets]
    if unknown:
        raise KitRefusal("unknown_target_field", "key " + ", ".join(unknown))
    names = [source["name"] for source in payload["sources"]]
    if len(set(names)) != len(names):
        raise KitRefusal("duplicate_source_name", "source names repeat")
    sources = sorted(payload["sources"], key=lambda source: (source["priority"], names.index(source["name"])))
    tables = [(source["name"], read_source(source, targets, keys)) for source in sources]
    tolerance = payload.get("numeric_tolerance", 0.0)
    order, seen = [], set()
    by_name = dict(tables)
    for source in payload["sources"]:
        for key in by_name[source["name"]]:
            if key not in seen:
                seen.add(key)
                order.append(key)
    rows, conflicts = [], []
    filled = {field: 0 for field in targets}
    for key in order:
        values, provenance, present = {}, {}, []
        for name, table in tables:
            if key in table:
                present.append(name)
        for field in targets:
            offers = [(name, table[key][field]) for name, table in tables
                      if key in table and table[key].get(field, "") != ""]
            if not offers:
                values[field] = ""
                continue
            values[field], provenance[field] = offers[0][1], offers[0][0]
            filled[field] += 1
            if any(not same(offers[0][1], value, tolerance) for _name, value in offers[1:]):
                conflicts.append({"key": dict(zip(keys, key)), "field": field,
                                  "values": [{"source": name, "value": value} for name, value in offers],
                                  "chosen": offers[0][0]})
        rows.append({"values": values, "provenance": provenance, "sources": present})
    summary = {"keys": len(order), "conflicts": len(conflicts),
               "rows_per_source": {name: len(table) for name, table in tables},
               "keys_in_one_source_only": sum(1 for row in rows if len(row["sources"]) == 1),
               "filled_share": {field: round(filled[field] / len(order), 4) if order else 0.0 for field in targets}}
    return {"rows": rows, "conflicts": conflicts, "summary": summary}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
