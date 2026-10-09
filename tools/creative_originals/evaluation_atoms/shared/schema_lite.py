"""A strict validator for the JSON Schema subset the evaluation atom contracts use (draft 2020-12 keywords).

Supported keywords: type, enum, const, properties, required, additionalProperties, propertyNames, minProperties,
maxProperties, items, minItems, maxItems, uniqueItems, minLength, maxLength, pattern, minimum, maximum,
exclusiveMinimum, exclusiveMaximum, oneOf, anyOf, allOf, not, $ref (local "#/$defs/NAME" only) and $defs, plus the
annotations $schema, $id, $comment, title, description, examples and default. A schema that uses any other keyword
is refused by ``check_schema``, so a contract cannot rely on a rule this validator would silently skip.

``validate(instance, schema)`` returns a list of "path: message" strings; an empty list means the instance conforms.
"""
from __future__ import annotations

import json
import math
import re

KEYWORDS = frozenset({"type", "enum", "const", "properties", "required", "additionalProperties", "propertyNames",
                      "minProperties", "maxProperties", "items", "minItems", "maxItems", "uniqueItems", "minLength",
                      "maxLength", "pattern", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "oneOf",
                      "anyOf", "allOf", "not", "$ref", "$defs"})
ANNOTATIONS = frozenset({"$schema", "$id", "$comment", "title", "description", "examples", "default"})
TYPES = (OBJECT, ARRAY, STRING, NUMBER, INTEGER, BOOLEAN, NULL) = (
    "object", "array", "string", "number", "integer", "boolean", "null")


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _is_type(value, kind):
    if kind == OBJECT:
        return isinstance(value, dict)
    if kind == ARRAY:
        return isinstance(value, list)
    if kind == STRING:
        return isinstance(value, str)
    if kind == BOOLEAN:
        return isinstance(value, bool)
    if kind == NULL:
        return value is None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float) and not math.isfinite(value):
        return False
    return kind == NUMBER or isinstance(value, int) or value.is_integer()


def _equal(left, right):
    return _canonical(left) == _canonical(right) and (isinstance(left, bool) == isinstance(right, bool))


def check_schema(schema, root=None, path="#"):
    """Raise ValueError when ``schema`` uses a keyword or a $ref outside the supported subset."""
    root = schema if root is None else root
    if isinstance(schema, bool):
        return
    if not isinstance(schema, dict):
        raise ValueError(f"{path}: a schema is an object or a boolean")
    unknown = set(schema) - KEYWORDS - ANNOTATIONS
    if unknown:
        raise ValueError(f"{path}: unsupported keywords {sorted(unknown)}")
    kinds = schema.get("type")
    if kinds is not None:
        for kind in ([kinds] if isinstance(kinds, str) else kinds):
            if kind not in TYPES:
                raise ValueError(f"{path}: unknown type {kind!r}")
    if "$ref" in schema:
        _resolve(root, schema["$ref"])
    for key in ("properties", "$defs"):
        for name, child in schema.get(key, {}).items():
            check_schema(child, root, f"{path}/{key}/{name}")
    for key in ("items", "additionalProperties", "propertyNames", "not"):
        if key in schema:
            check_schema(schema[key], root, f"{path}/{key}")
    for key in ("oneOf", "anyOf", "allOf"):
        for index, child in enumerate(schema.get(key, [])):
            check_schema(child, root, f"{path}/{key}/{index}")
    if "pattern" in schema:
        re.compile(schema["pattern"])


def _resolve(root, reference):
    prefix = "#/$defs/"
    if not isinstance(reference, str) or not reference.startswith(prefix):
        raise ValueError(f"only local references {prefix}NAME are supported, got {reference!r}")
    name = reference[len(prefix):]
    if name not in root.get("$defs", {}):
        raise ValueError(f"unresolved reference {reference}")
    return root["$defs"][name]


def _errors(instance, schema, root, path, depth):
    if depth > 64:
        return [f"{path}: schema nesting is too deep"]
    if schema is True:
        return []
    if schema is False:
        return [f"{path}: no value is allowed here"]
    errors = []
    if "$ref" in schema:
        errors += _errors(instance, _resolve(root, schema["$ref"]), root, path, depth + 1)
    kinds = schema.get("type")
    if kinds is not None:
        kinds = [kinds] if isinstance(kinds, str) else kinds
        if not any(_is_type(instance, kind) for kind in kinds):
            return errors + [f"{path}: expected {' or '.join(kinds)}"]
    if "const" in schema and not _equal(instance, schema["const"]):
        errors.append(f"{path}: must equal {_canonical(schema['const'])}")
    if "enum" in schema and not any(_equal(instance, option) for option in schema["enum"]):
        errors.append(f"{path}: must be one of {_canonical(schema['enum'])}")
    if isinstance(instance, dict):
        for name in schema.get("required", []):
            if name not in instance:
                errors.append(f"{path}: missing required property {name!r}")
        properties = schema.get("properties", {})
        for name, value in instance.items():
            if name in properties:
                errors += _errors(value, properties[name], root, f"{path}/{name}", depth + 1)
            elif "additionalProperties" in schema:
                extra = schema["additionalProperties"]
                if extra is False:
                    errors.append(f"{path}: property {name!r} is not allowed")
                elif extra is not True:
                    errors += _errors(value, extra, root, f"{path}/{name}", depth + 1)
            if "propertyNames" in schema:
                errors += _errors(name, schema["propertyNames"], root, f"{path}/{name}(name)", depth + 1)
        if "minProperties" in schema and len(instance) < schema["minProperties"]:
            errors.append(f"{path}: needs at least {schema['minProperties']} properties")
        if "maxProperties" in schema and len(instance) > schema["maxProperties"]:
            errors.append(f"{path}: allows at most {schema['maxProperties']} properties")
    if isinstance(instance, list):
        if "items" in schema:
            for index, value in enumerate(instance):
                errors += _errors(value, schema["items"], root, f"{path}/{index}", depth + 1)
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: needs at least {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: allows at most {schema['maxItems']} items")
        if schema.get("uniqueItems") and len({_canonical(value) for value in instance}) != len(instance):
            errors.append(f"{path}: items must be unique")
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: needs at least {schema['minLength']} characters")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{path}: allows at most {schema['maxLength']} characters")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: does not match {schema['pattern']!r}")
    if _is_type(instance, NUMBER):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: must be at least {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: must be at most {schema['maximum']}")
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            errors.append(f"{path}: must be greater than {schema['exclusiveMinimum']}")
        if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
            errors.append(f"{path}: must be less than {schema['exclusiveMaximum']}")
    for child in schema.get("allOf", []):
        errors += _errors(instance, child, root, path, depth + 1)
    if "anyOf" in schema and not any(not _errors(instance, child, root, path, depth + 1) for child in schema["anyOf"]):
        errors.append(f"{path}: matches none of the anyOf alternatives")
    if "oneOf" in schema:
        matching = sum(1 for child in schema["oneOf"] if not _errors(instance, child, root, path, depth + 1))
        if matching != 1:
            errors.append(f"{path}: matches {matching} of the oneOf alternatives, expected exactly 1")
    if "not" in schema and not _errors(instance, schema["not"], root, path, depth + 1):
        errors.append(f"{path}: must not match the 'not' schema")
    return errors


def validate(instance, schema):
    """Every violation of ``schema`` by ``instance`` as "path: message" text; empty when it conforms."""
    check_schema(schema)
    return _errors(instance, schema, schema, "#", 0)


__all__ = ["KEYWORDS", "ANNOTATIONS", "TYPES", "check_schema", "validate"]
