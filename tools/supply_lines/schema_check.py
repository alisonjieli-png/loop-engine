"""A small JSON Schema validator: drafts 4, 6, 7, 2019-09 and 2020-12, local references only.

Usage: python schema_check.py SCHEMA.json INSTANCE.json   (prints each error; exit status 1 when any)
In code: errors(instance, schema) -> list of error texts; valid(instance, schema) -> bool.
Formats are annotations and are not checked; a pattern Python cannot compile is not checked.
"""
import json
import math
import re
import sys
from urllib.parse import unquote

LEGACY_DRAFTS = ("draft-03", "draft-04", "draft-06", "draft-07")


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def equal(left, right):
    """JSON equality: a boolean is never a number, 1 equals 1.0, and containers compare member by member."""
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(equal(a, b) for a, b in zip(left, right))
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(equal(left[key], right[key]) for key in left)
    return type(left) is type(right) and left == right


def is_type(value, kind):
    if kind == "integer":
        return (isinstance(value, int) and not isinstance(value, bool)) or (
            isinstance(value, float) and value.is_integer())
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "string":
        return isinstance(value, str)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "null":
        return value is None
    if kind == "array":
        return isinstance(value, list)
    if kind == "object":
        return isinstance(value, dict)
    return True


class Validator:
    def __init__(self, root):
        self.root = root
        marker = str(root.get("$schema", "")) if isinstance(root, dict) else ""
        self.legacy = any(draft in marker for draft in LEGACY_DRAFTS)
        self.anchors = {}
        self.patterns = {}
        self._index(root)

    def _index(self, node):
        if isinstance(node, dict):
            for key in ("$anchor", "$id", "id"):
                value = node.get(key)
                if isinstance(value, str) and value.startswith("#") and len(value) > 1:
                    self.anchors[value[1:]] = node
                elif key == "$anchor" and isinstance(value, str):
                    self.anchors[value] = node
            for value in node.values():
                self._index(value)
        elif isinstance(node, list):
            for value in node:
                self._index(value)

    def resolve(self, reference):
        if reference in ("#", ""):
            return self.root
        if reference.startswith("#/"):
            node = self.root
            for part in reference[2:].split("/"):
                part = unquote(part).replace("~1", "/").replace("~0", "~")
                if isinstance(node, list) and part.isdigit():
                    node = node[int(part)]
                elif isinstance(node, dict) and part in node:
                    node = node[part]
                else:
                    raise LookupError(reference)
            return node
        if reference.startswith("#") and reference[1:] in self.anchors:
            return self.anchors[reference[1:]]
        raise LookupError(reference)

    def pattern(self, text):
        if text not in self.patterns:
            try:
                self.patterns[text] = re.compile(text)
            except re.error:
                self.patterns[text] = None
        return self.patterns[text]

    def errors(self, instance, schema, path="$", depth=0):
        if schema is True or schema == {} or depth > 64:
            return []
        if schema is False:
            return [f"{path}: no value is allowed here"]
        if not isinstance(schema, dict):
            return []
        found = []
        reference = schema.get("$ref", schema.get("$recursiveRef", schema.get("$dynamicRef")))
        if isinstance(reference, str):
            found += self.errors(instance, self.resolve(reference), path, depth + 1)
            if self.legacy and "$ref" in schema:
                return found
        kinds = schema.get("type")
        if kinds is not None:
            kinds = [kinds] if isinstance(kinds, str) else list(kinds)
            if not any(is_type(instance, kind) for kind in kinds):
                return found + [f"{path}: expected {' or '.join(map(str, kinds))}"]
        if "enum" in schema and not any(equal(instance, item) for item in schema["enum"]):
            found.append(f"{path}: not one of the allowed values")
        if "const" in schema and not equal(instance, schema["const"]):
            found.append(f"{path}: not the constant value")
        if is_type(instance, "number"):
            found += self._number(instance, schema, path)
        if isinstance(instance, str):
            found += self._string(instance, schema, path)
        if isinstance(instance, list):
            found += self._array(instance, schema, path, depth)
        if isinstance(instance, dict):
            found += self._object(instance, schema, path, depth)
        for part in schema.get("allOf", ()) or ():
            found += self.errors(instance, part, path, depth + 1)
        if "anyOf" in schema and not any(not self.errors(instance, part, path, depth + 1) for part in schema["anyOf"]):
            found.append(f"{path}: matches none of anyOf")
        if "oneOf" in schema:
            matches = sum(1 for part in schema["oneOf"] if not self.errors(instance, part, path, depth + 1))
            if matches != 1:
                found.append(f"{path}: matches {matches} of oneOf, not exactly one")
        if "not" in schema and not self.errors(instance, schema["not"], path, depth + 1):
            found.append(f"{path}: matches a schema it must not")
        if "if" in schema:
            if not self.errors(instance, schema["if"], path, depth + 1):
                if "then" in schema:
                    found += self.errors(instance, schema["then"], path, depth + 1)
            elif "else" in schema:
                found += self.errors(instance, schema["else"], path, depth + 1)
        return found

    def _number(self, value, schema, path):
        found = []
        step = schema.get("multipleOf")
        if isinstance(step, (int, float)) and step > 0:
            quotient = value / step
            if not math.isclose(quotient, round(quotient), rel_tol=0, abs_tol=1e-9):
                found.append(f"{path}: not a multiple of {step}")
        maximum, minimum = schema.get("maximum"), schema.get("minimum")
        exclusive_maximum, exclusive_minimum = schema.get("exclusiveMaximum"), schema.get("exclusiveMinimum")
        if isinstance(maximum, (int, float)) and not isinstance(maximum, bool):
            if value > maximum or (exclusive_maximum is True and value >= maximum):
                found.append(f"{path}: above the maximum {maximum}")
        if isinstance(minimum, (int, float)) and not isinstance(minimum, bool):
            if value < minimum or (exclusive_minimum is True and value <= minimum):
                found.append(f"{path}: below the minimum {minimum}")
        if isinstance(exclusive_maximum, (int, float)) and not isinstance(exclusive_maximum, bool) and \
                value >= exclusive_maximum:
            found.append(f"{path}: not below {exclusive_maximum}")
        if isinstance(exclusive_minimum, (int, float)) and not isinstance(exclusive_minimum, bool) and \
                value <= exclusive_minimum:
            found.append(f"{path}: not above {exclusive_minimum}")
        return found

    def _string(self, value, schema, path):
        found = []
        if isinstance(schema.get("maxLength"), int) and len(value) > schema["maxLength"]:
            found.append(f"{path}: longer than {schema['maxLength']}")
        if isinstance(schema.get("minLength"), int) and len(value) < schema["minLength"]:
            found.append(f"{path}: shorter than {schema['minLength']}")
        if isinstance(schema.get("pattern"), str):
            compiled = self.pattern(schema["pattern"])
            if compiled is not None and not compiled.search(value):
                found.append(f"{path}: does not match {schema['pattern']}")
        return found

    def _array(self, value, schema, path, depth):
        found = []
        prefix = schema.get("prefixItems")
        items = schema.get("items")
        if isinstance(items, list):  # tuple validation before 2020-12
            prefix, items = items, schema.get("additionalItems")
        count = len(prefix) if isinstance(prefix, list) else 0
        for index, item in enumerate(value):
            part = prefix[index] if index < count else items
            if part is not None:
                found += self.errors(item, part, f"{path}[{index}]", depth + 1)
        if isinstance(schema.get("maxItems"), int) and len(value) > schema["maxItems"]:
            found.append(f"{path}: more than {schema['maxItems']} items")
        if isinstance(schema.get("minItems"), int) and len(value) < schema["minItems"]:
            found.append(f"{path}: fewer than {schema['minItems']} items")
        if schema.get("uniqueItems") is True:
            for index, item in enumerate(value):
                if any(equal(item, other) for other in value[:index]):
                    found.append(f"{path}: items are not unique")
                    break
        if "contains" in schema:
            matches = sum(1 for item in value if not self.errors(item, schema["contains"], path, depth + 1))
            least = schema.get("minContains", 1)
            if matches < least:
                found.append(f"{path}: contains too few matching items")
            if isinstance(schema.get("maxContains"), int) and matches > schema["maxContains"]:
                found.append(f"{path}: contains too many matching items")
        return found

    def _object(self, value, schema, path, depth):
        found = []
        if isinstance(schema.get("maxProperties"), int) and len(value) > schema["maxProperties"]:
            found.append(f"{path}: more than {schema['maxProperties']} properties")
        if isinstance(schema.get("minProperties"), int) and len(value) < schema["minProperties"]:
            found.append(f"{path}: fewer than {schema['minProperties']} properties")
        required = schema.get("required")
        if isinstance(required, list):
            found += [f"{path}: lacks {name}" for name in required if isinstance(name, str) and name not in value]
        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        patterns = schema.get("patternProperties") if isinstance(schema.get("patternProperties"), dict) else {}
        for name, item in value.items():
            where = f"{path}.{name}"
            matched = False
            if name in properties:
                matched = True
                found += self.errors(item, properties[name], where, depth + 1)
            for text, part in patterns.items():
                compiled = self.pattern(text)
                if compiled is not None and compiled.search(name):
                    matched = True
                    found += self.errors(item, part, where, depth + 1)
            if not matched and "additionalProperties" in schema:
                found += self.errors(item, schema["additionalProperties"], where, depth + 1)
            if "propertyNames" in schema:
                found += self.errors(name, schema["propertyNames"], f"{where} (name)", depth + 1)
        dependencies = dict(schema.get("dependencies") or {})
        dependencies.update(schema.get("dependentRequired") or {})
        dependencies.update(schema.get("dependentSchemas") or {})
        for name, rule in dependencies.items():
            if name not in value:
                continue
            if isinstance(rule, list):
                found += [f"{path}: {name} needs {other}" for other in rule if other not in value]
            else:
                found += self.errors(value, rule, path, depth + 1)
        return found


def errors(instance, schema):
    return Validator(schema).errors(instance, schema)


def valid(instance, schema):
    return not errors(instance, schema)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python schema_check.py SCHEMA.json INSTANCE.json")
    problems = errors(load(sys.argv[2]), load(sys.argv[1]))
    for problem in problems:
        print(problem)
    sys.exit(1 if problems else 0)
