"""A small JSON Schema subset validator, the typed refusal and the command line runner every kit shares.

Supported keywords: type, enum, const, properties, required, additionalProperties, items, minItems, maxItems,
uniqueItems, minProperties, maxProperties, minimum, maximum, exclusiveMinimum, exclusiveMaximum, minLength,
maxLength, pattern, format (date, date-time, time), anyOf and $ref to "#/$defs/<name>". Annotation keywords
(title, description, default, examples, $comment, $defs) are accepted and not validated. schema_problems refuses
any other keyword, so a schema cannot ask for validation this module does not perform.

Standard library only. Nothing here reads files, opens connections or starts processes.
"""
from __future__ import annotations

import datetime
import json
import math
import re
import sys

VALIDATED = ("type", "enum", "const", "properties", "required", "additionalProperties", "items", "minItems",
             "maxItems", "uniqueItems", "minProperties", "maxProperties", "minimum", "maximum", "exclusiveMinimum",
             "exclusiveMaximum", "minLength", "maxLength", "pattern", "format", "anyOf", "$ref")
ANNOTATIONS = ("title", "description", "default", "examples", "$comment", "$defs", "$schema", "$id")
TYPES = ("object", "array", "string", "number", "integer", "boolean", "null")
FORMATS = ("date", "date-time", "time")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$")
_DATE_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T([01]\d|2[0-3]):[0-5]\d(:[0-5]\d(\.\d+)?)?(Z|[+-]\d{2}:\d{2})?$")


class KitRefusal(ValueError):
    """A typed refusal: a closed reason code and a short detail. Kits raise only this for bad input."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail

    def to_dict(self) -> dict:
        return {"refused": True, "reason": self.reason, "detail": self.detail}


def _is_type(value, name: str) -> bool:
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "string":
        return isinstance(value, str)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "null":
        return value is None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float) and not math.isfinite(value):
        return False
    if name == "integer":
        return isinstance(value, int) or float(value).is_integer()
    return name == "number"


def parse_date(text: str):
    """A calendar date from YYYY-MM-DD, or None when the text is not one."""
    if not isinstance(text, str) or not _DATE.match(text):
        return None
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        return None


def parse_date_time(text: str):
    """A date and time from ISO 8601 (seconds, fraction and offset optional, Z accepted), or None."""
    if not isinstance(text, str) or not _DATE_TIME.match(text):
        return None
    try:
        return datetime.datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError:
        return None


def parse_time(text: str):
    """Minutes after midnight from HH:MM or HH:MM:SS (seconds dropped), or None when the text is not a time."""
    if not isinstance(text, str) or not _TIME.match(text):
        return None
    return int(text[0:2]) * 60 + int(text[3:5])


def _format_ok(value, name: str) -> bool:
    if name == "date":
        return parse_date(value) is not None
    if name == "date-time":
        return parse_date_time(value) is not None
    return bool(_TIME.match(value))


def _resolve(reference: str, root: dict) -> dict:
    prefix = "#/$defs/"
    if not reference.startswith(prefix) or reference[len(prefix):] not in root.get("$defs", {}):
        raise KitRefusal("schema_invalid", f"unresolvable reference {reference}")
    return root["$defs"][reference[len(prefix):]]


def validate(instance, schema: dict, root: "dict | None" = None, path: str = "$") -> list:
    """Every way ``instance`` breaks ``schema``, as 'path: problem' strings; an empty list means it conforms."""
    root = schema if root is None else root
    if "$ref" in schema:
        return validate(instance, _resolve(schema["$ref"], root), root, path)
    errors = []
    expected = schema.get("type")
    if expected is not None:
        names = expected if isinstance(expected, list) else [expected]
        if not any(_is_type(instance, name) for name in names):
            return [f"{path}: expected {' or '.join(names)}"]
    if "enum" in schema and not any(_same(instance, option) for option in schema["enum"]):
        errors.append(f"{path}: not one of the allowed values")
    if "const" in schema and not _same(instance, schema["const"]):
        errors.append(f"{path}: not the required constant")
    if "anyOf" in schema and not any(not validate(instance, option, root, path) for option in schema["anyOf"]):
        errors.append(f"{path}: matches none of the allowed shapes")
    if isinstance(instance, dict):
        for name in schema.get("required", []):
            if name not in instance:
                errors.append(f"{path}: missing required field {name}")
        properties = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for name, value in instance.items():
            where = f"{path}.{name}"
            if name in properties:
                errors.extend(validate(value, properties[name], root, where))
            elif extra is False:
                errors.append(f"{path}: unexpected field {name}")
            elif isinstance(extra, dict):
                errors.extend(validate(value, extra, root, where))
        if "minProperties" in schema and len(instance) < schema["minProperties"]:
            errors.append(f"{path}: fewer than {schema['minProperties']} fields")
        if "maxProperties" in schema and len(instance) > schema["maxProperties"]:
            errors.append(f"{path}: more than {schema['maxProperties']} fields")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: more than {schema['maxItems']} items")
        if schema.get("uniqueItems"):
            seen = set()
            for item in instance:
                key = json.dumps(item, sort_keys=True)
                if key in seen:
                    errors.append(f"{path}: repeated item")
                    break
                seen.add(key)
        if isinstance(schema.get("items"), dict):
            for index, item in enumerate(instance):
                errors.extend(validate(item, schema["items"], root, f"{path}[{index}]"))
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']} characters")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{path}: longer than {schema['maxLength']} characters")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: does not match the required pattern")
        if "format" in schema and not _format_ok(instance, schema["format"]):
            errors.append(f"{path}: not a valid {schema['format']}")
    if _is_type(instance, "number"):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: below the minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: above the maximum {schema['maximum']}")
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            errors.append(f"{path}: not above {schema['exclusiveMinimum']}")
        if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
            errors.append(f"{path}: not below {schema['exclusiveMaximum']}")
    return errors


def _same(left, right) -> bool:
    return type(left) is type(right) and json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True) \
        or (_is_type(left, "number") and _is_type(right, "number") and left == right)


def schema_problems(schema, root: "dict | None" = None, path: str = "#") -> list:
    """Keywords, types and formats in ``schema`` that this validator does not support; empty when it is usable."""
    if not isinstance(schema, dict):
        return [f"{path}: a schema is an object"]
    root = schema if root is None else root
    problems = [f"{path}: unsupported keyword {key}" for key in schema if key not in VALIDATED + ANNOTATIONS]
    kinds = schema.get("type")
    for kind in (kinds if isinstance(kinds, list) else [kinds] if kinds is not None else []):
        if kind not in TYPES:
            problems.append(f"{path}: unknown type {kind}")
    if "format" in schema and schema["format"] not in FORMATS:
        problems.append(f"{path}: unsupported format {schema['format']}")
    if "$ref" in schema:
        try:
            _resolve(schema["$ref"], root)
        except KitRefusal as refusal:
            problems.append(f"{path}: {refusal.detail}")
    for name, child in schema.get("properties", {}).items():
        problems.extend(schema_problems(child, root, f"{path}/properties/{name}"))
    for key in ("items", "additionalProperties"):
        if isinstance(schema.get(key), dict):
            problems.extend(schema_problems(schema[key], root, f"{path}/{key}"))
    for index, child in enumerate(schema.get("anyOf", [])):
        problems.extend(schema_problems(child, root, f"{path}/anyOf/{index}"))
    for name, child in schema.get("$defs", {}).items():
        problems.extend(schema_problems(child, root, f"{path}/$defs/{name}"))
    return problems


def check(instance, schema: dict, reason: str = "input_invalid") -> None:
    """Refuse ``instance`` with ``reason`` when it breaks ``schema``; the detail names the first problems."""
    errors = validate(instance, schema)
    if errors:
        raise KitRefusal(reason, "; ".join(errors[:6]))


def run_cli(function, argv=None, stdin=None, stdout=None) -> int:
    """Read one JSON document from standard input, run ``function`` on it and write the JSON result.

    Exit status 0 with the result, or 2 with {"refused": true, "reason", "detail"} for a refusal or text that is not
    JSON. "--compact" in ``argv`` writes one line instead of an indented document."""
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    try:
        payload = json.loads(stdin.read())
    except ValueError as error:
        result, code = KitRefusal("input_not_json", str(error)[:200]).to_dict(), 2
    else:
        try:
            result, code = function(payload), 0
        except KitRefusal as refusal:
            result, code = refusal.to_dict(), 2
    indent = None if argv and "--compact" in argv else 1
    stdout.write(json.dumps(result, indent=indent, sort_keys=True, ensure_ascii=False) + "\n")
    return code


__all__ = ["KitRefusal", "validate", "schema_problems", "check", "run_cli", "parse_date", "parse_date_time",
           "parse_time",
           "VALIDATED", "ANNOTATIONS", "TYPES", "FORMATS"]
