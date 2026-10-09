"""Validate JSON values against the JSON Schema subset the asset contracts use, with the standard library only.

The asset contracts publish JSON Schema (draft 2020-12) documents so any harness can validate manifests with its
own validator. Package tests run without third-party libraries, so this module implements the keywords those
schemas use: type, enum, const, properties, required, additionalProperties, patternProperties, items, minItems,
maxItems, uniqueItems, minimum, maximum, exclusiveMinimum, exclusiveMaximum, minLength, maxLength, pattern,
minProperties, allOf, anyOf, oneOf, not and local $ref into $defs. Annotation keywords (title, description,
default, examples, $comment, $schema, $id, format) carry no constraint here. Any other keyword is refused by
``unsupported_keywords`` instead of being ignored, so a schema cannot rely on a rule this validator skips.
"""
from __future__ import annotations

import json
import re

CONSTRAINTS = {"type", "enum", "const", "properties", "required", "additionalProperties", "patternProperties",
               "items", "minItems", "maxItems", "uniqueItems", "minimum", "maximum", "exclusiveMinimum",
               "exclusiveMaximum", "minLength", "maxLength", "pattern", "minProperties", "allOf", "anyOf", "oneOf",
               "not", "$ref", "$defs"}
ANNOTATIONS = {"title", "description", "default", "examples", "$comment", "$schema", "$id", "format"}
SUBSCHEMA_MAPS = ("properties", "patternProperties", "$defs")
SUBSCHEMA_LISTS = ("allOf", "anyOf", "oneOf")
SUBSCHEMAS = ("additionalProperties", "items", "not")


def unsupported_keywords(schema, path: str = "$") -> list:
    """Every keyword in ``schema`` (recursively) that this validator does not implement."""
    found = []
    if isinstance(schema, bool):
        return found
    if not isinstance(schema, dict):
        return [f"{path}: a schema is an object or a boolean"]
    for key, value in schema.items():
        if key not in CONSTRAINTS | ANNOTATIONS:
            found.append(f"{path}.{key}")
        elif key in SUBSCHEMA_MAPS and isinstance(value, dict):
            for name, child in value.items():
                found += unsupported_keywords(child, f"{path}.{key}.{name}")
        elif key in SUBSCHEMA_LISTS and isinstance(value, list):
            for index, child in enumerate(value):
                found += unsupported_keywords(child, f"{path}.{key}[{index}]")
        elif key in SUBSCHEMAS:
            found += unsupported_keywords(value, f"{path}.{key}")
    return found


def _type_matches(value, name: str) -> bool:
    if name == "null":
        return value is None
    if name == "boolean":
        return isinstance(value, bool)
    if name == "integer":
        return (type(value) is int) or (type(value) is float and value.is_integer())
    if name == "number":
        return type(value) in (int, float)
    if name == "string":
        return isinstance(value, str)
    if name == "array":
        return isinstance(value, list)
    if name == "object":
        return isinstance(value, dict)
    raise ValueError(f"unknown type {name}")


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _resolve(reference: str, root: dict):
    if not reference.startswith("#/"):
        raise ValueError(f"only local references are supported: {reference}")
    node = root
    for part in reference[2:].split("/"):
        node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def validate(instance, schema, root=None, path: str = "$") -> list:
    """Every violation as {"path", "keyword", "message"}; an empty list means the instance is valid."""
    root = schema if root is None else root
    if schema is True:
        return []
    if schema is False:
        return [{"path": path, "keyword": "false", "message": "no value is allowed here"}]
    errors = []

    def fail(keyword: str, message: str) -> None:
        errors.append({"path": path, "keyword": keyword, "message": message})

    if "$ref" in schema:
        errors += validate(instance, _resolve(schema["$ref"], root), root, path)
    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_matches(instance, name) for name in names):
            fail("type", f"expected {'/'.join(names)}")
            return errors
    if "enum" in schema and _canonical(instance) not in {_canonical(item) for item in schema["enum"]}:
        fail("enum", f"{instance!r} is not one of {schema['enum']}"[:200])
    if "const" in schema and _canonical(instance) != _canonical(schema["const"]):
        fail("const", f"must equal {schema['const']!r}"[:200])
    if type(instance) in (int, float) and not isinstance(instance, bool):
        for keyword, broken in (("minimum", lambda limit: instance < limit), ("maximum", lambda limit: instance > limit),
                                ("exclusiveMinimum", lambda limit: instance <= limit),
                                ("exclusiveMaximum", lambda limit: instance >= limit)):
            if keyword in schema and broken(schema[keyword]):
                fail(keyword, f"{instance} violates {keyword} {schema[keyword]}")
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            fail("minLength", f"shorter than {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            fail("maxLength", f"longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            fail("pattern", f"{instance!r} does not match {schema['pattern']}"[:200])
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            fail("minItems", f"fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            fail("maxItems", f"more than {schema['maxItems']} items")
        if schema.get("uniqueItems") and len({_canonical(item) for item in instance}) != len(instance):
            fail("uniqueItems", "items repeat")
        if "items" in schema:
            for index, item in enumerate(instance):
                errors += validate(item, schema["items"], root, f"{path}[{index}]")
    if isinstance(instance, dict):
        for name in schema.get("required", []):
            if name not in instance:
                fail("required", f"missing {name}")
        if "minProperties" in schema and len(instance) < schema["minProperties"]:
            fail("minProperties", f"fewer than {schema['minProperties']} properties")
        properties, patterns = schema.get("properties", {}), schema.get("patternProperties", {})
        for name, value in instance.items():
            matched = False
            if name in properties:
                matched = True
                errors += validate(value, properties[name], root, f"{path}.{name}")
            for pattern, child in patterns.items():
                if re.search(pattern, name):
                    matched = True
                    errors += validate(value, child, root, f"{path}.{name}")
            if not matched and "additionalProperties" in schema:
                extra = schema["additionalProperties"]
                if extra is False:
                    errors.append({"path": f"{path}.{name}", "keyword": "additionalProperties",
                                   "message": "property not allowed"})
                elif isinstance(extra, dict):
                    errors += validate(value, extra, root, f"{path}.{name}")
    for child in schema.get("allOf", []):
        errors += validate(instance, child, root, path)
    if "anyOf" in schema and not any(not validate(instance, child, root, path) for child in schema["anyOf"]):
        fail("anyOf", "matches none of the alternatives")
    if "oneOf" in schema:
        matches = sum(1 for child in schema["oneOf"] if not validate(instance, child, root, path))
        if matches != 1:
            fail("oneOf", f"matches {matches} alternatives, not exactly one")
    if "not" in schema and not validate(instance, schema["not"], root, path):
        fail("not", "matches a forbidden schema")
    return errors


__all__ = ["CONSTRAINTS", "ANNOTATIONS", "unsupported_keywords", "validate"]
