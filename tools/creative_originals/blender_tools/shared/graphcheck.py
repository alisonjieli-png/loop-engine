"""Checks for the plain-data descriptions the Blender tools return, with the standard library only.

The tool cores describe node trees, keyframe channels, objects, drivers, bones and settings as lists and
dictionaries. These functions find structural problems in them before Blender ever sees them, and return
(code, detail) pairs; an empty list means the description is well formed.
"""
from __future__ import annotations

import json
import math
import re

#: The output node each kind of node tree must have, with at least one linked input.
OUTPUT_NODES = {"material": ("ShaderNodeOutputMaterial",), "world": ("ShaderNodeOutputWorld",),
                "light": ("ShaderNodeOutputLight",), "compositor": ("NodeGroupOutput", "CompositorNodeComposite"),
                "geometry": ("NodeGroupOutput",), "shader_group": ("NodeGroupOutput",)}
NODE_TYPE = re.compile(r"^(ShaderNode|CompositorNode|GeometryNode|FunctionNode|NodeGroup|Node)[A-Za-z0-9]*$")
INTERPOLATIONS = ("CONSTANT", "LINEAR", "BEZIER", "SINE", "QUAD", "CUBIC", "QUART", "QUINT", "EXPO", "CIRC",
                  "BACK", "BOUNCE", "ELASTIC")
#: Names a driver may use and still be a simple expression, which Blender evaluates without running Python.
SIMPLE_FUNCTIONS = frozenset({"sin", "cos", "tan", "asin", "acos", "atan", "atan2", "sqrt", "pow", "exp", "log",
                              "floor", "ceil", "abs", "min", "max", "radians", "degrees", "fmod", "pi", "frame"})
EXPECTATION_KEYS = frozenset({"objects", "materials", "worlds", "node_groups", "images", "collections", "scene",
                              "samples", "counts", "compositor", "simulate", "texts"})
# The types a parameter declaration may name in "type": one constant each, and all of them in PARAMETER_TYPES.
PARAMETER_TYPE_INT = "int"
PARAMETER_TYPE_FLOAT = "float"
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_CHOICE = "choice"
PARAMETER_TYPE_STRING = "string"
PARAMETER_TYPE_VECTOR = "vector"
PARAMETER_TYPES = (PARAMETER_TYPE_INT, PARAMETER_TYPE_FLOAT, PARAMETER_TYPE_BOOL, PARAMETER_TYPE_CHOICE,
                   PARAMETER_TYPE_STRING, PARAMETER_TYPE_VECTOR)


def _finite(value):
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(value)
    if isinstance(value, (list, tuple)):
        return all(_finite(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _finite(item) for key, item in value.items())
    return False


def json_problems(value):
    """A value that JSON cannot carry exactly, or that holds a non-finite number."""
    if not _finite(value):
        return [("value_not_finite_or_not_plain", type(value).__name__)]
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as error:
        return [("value_not_json", str(error)[:80])]
    return []


def tree_problems(tree):
    """Problems of one node tree: {"name", "kind", "nodes": [{"name", "type", ...}], "links": [...]}.

    A link is {"from": [node, output socket], "to": [node, input socket]}. Codes: tree_kind_unknown,
    node_name_repeated, node_type_invalid, link_invalid, link_node_missing, input_linked_twice, link_to_self,
    cycle, output_missing, output_unlinked."""
    found = []
    kind = tree.get("kind")
    if kind not in OUTPUT_NODES:
        found.append(("tree_kind_unknown", kind))
    names = {}
    for node in tree.get("nodes", []):
        name, node_type = node.get("name"), node.get("type")
        if not isinstance(name, str) or not name or name in names:
            found.append(("node_name_repeated", name))
        if not isinstance(node_type, str) or not NODE_TYPE.match(node_type):
            found.append(("node_type_invalid", node_type))
        names[name] = node_type
    targets, edges = set(), {name: set() for name in names}
    for link in tree.get("links", []):
        source, target = link.get("from"), link.get("to")
        if (not isinstance(source, (list, tuple)) or not isinstance(target, (list, tuple)) or len(source) != 2
                or len(target) != 2 or not all(isinstance(part, (str, int)) for part in (*source, *target))):
            found.append(("link_invalid", link))
            continue
        if source[0] not in names or target[0] not in names:
            found.append(("link_node_missing", [source[0], target[0]]))
            continue
        if source[0] == target[0]:
            found.append(("link_to_self", source[0]))
            continue
        key = (target[0], target[1])
        if key in targets:
            found.append(("input_linked_twice", list(key)))
        targets.add(key)
        edges[source[0]].add(target[0])
    remaining = {name: 0 for name in edges}
    for name, after in edges.items():
        for target in after:
            remaining[target] += 1
    ready = [name for name, count in remaining.items() if count == 0]
    visited = 0
    while ready:
        name = ready.pop()
        visited += 1
        for target in edges[name]:
            remaining[target] -= 1
            if remaining[target] == 0:
                ready.append(target)
    if visited != len(edges):
        found.append(("cycle", sorted(name for name, count in remaining.items() if count > 0)[:5]))
    outputs = [name for name, node_type in names.items() if node_type in OUTPUT_NODES.get(kind, ())]
    if not outputs:
        found.append(("output_missing", kind))
    elif not any(target[0] in outputs for target in targets):
        found.append(("output_unlinked", outputs[0]))
    return found


def channel_problems(channels):
    """Problems of keyframe channels: {"target", "data_path", "index", "keys": [[frame, value], ...]}.

    Codes: channel_invalid, keys_missing, key_invalid, frames_not_increasing, interpolation_unknown,
    channel_repeated."""
    found, seen = [], set()
    for number, channel in enumerate(channels):
        if (not isinstance(channel.get("target"), str) or not isinstance(channel.get("data_path"), str)
                or not isinstance(channel.get("index", 0), int)):
            found.append(("channel_invalid", number))
            continue
        key = (channel["target"], channel.get("owner", "object"), channel["data_path"], channel.get("index", 0))
        if key in seen:
            found.append(("channel_repeated", list(key)))
        seen.add(key)
        keys = channel.get("keys")
        if not isinstance(keys, (list, tuple)) or not keys:
            found.append(("keys_missing", number))
            continue
        frames = []
        for pair in keys:
            if (not isinstance(pair, (list, tuple)) or len(pair) != 2
                    or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in pair)):
                found.append(("key_invalid", number))
                break
            frames.append(pair[0])
        if any(later <= earlier for earlier, later in zip(frames, frames[1:])):
            found.append(("frames_not_increasing", number))
        if channel.get("interpolation", "BEZIER") not in INTERPOLATIONS:
            found.append(("interpolation_unknown", channel.get("interpolation")))
    return found


def object_problems(objects):
    """Problems of object descriptions: {"name", "type", "location", "parent", ...}.

    Codes: object_invalid, object_name_repeated, parent_missing, parent_cycle, transform_not_finite."""
    found, parents = [], {}
    for item in objects:
        name = item.get("name") if isinstance(item, dict) else None
        if not isinstance(name, str) or not name or not isinstance(item.get("type"), str):
            found.append(("object_invalid", name))
            continue
        if name in parents:
            found.append(("object_name_repeated", name))
        parents[name] = item.get("parent")
        for key in ("location", "rotation", "scale"):
            if key in item and (len(item[key]) != 3 or not _finite(item[key])):
                found.append(("transform_not_finite", [name, key]))
    for name, parent in parents.items():
        if parent is not None and parent not in parents:
            found.append(("parent_missing", [name, parent]))
    for name in parents:
        chain, current = set(), name
        while current is not None and current in parents:
            if current in chain:
                found.append(("parent_cycle", name))
                break
            chain.add(current)
            current = parents[current]
    return found


def expression_names(expression):
    """Identifiers an expression uses, without string contents."""
    return set(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", re.sub(r"(\"[^\"]*\"|'[^']*')", "", expression)))


def driver_problems(drivers):
    """Problems of driver descriptions; an expression must stay a simple expression.

    Codes: driver_invalid, variable_invalid, expression_not_simple."""
    found = []
    for number, driver in enumerate(drivers):
        expression = driver.get("expression")
        if (not isinstance(driver.get("target"), str) or not isinstance(driver.get("data_path"), str)
                or not isinstance(expression, str) or not expression.strip()):
            found.append(("driver_invalid", number))
            continue
        variables = set()
        for variable in driver.get("variables", []):
            name = variable.get("name", "")
            if not re.match(r"^[A-Za-z_][A-Za-z_0-9]*$", name) or name in SIMPLE_FUNCTIONS:
                found.append(("variable_invalid", [number, name]))
            variables.add(name)
        extra = expression_names(expression) - variables - SIMPLE_FUNCTIONS - {"if", "else", "and", "or", "not"}
        if extra:
            found.append(("expression_not_simple", [number, sorted(extra)]))
    return found


def bone_problems(bones):
    """Problems of armature bones: {"name", "head", "tail", "parent"}. Codes: bone_invalid, bone_name_repeated,
    bone_zero_length, bone_parent_missing."""
    found, names = [], set()
    for bone in bones:
        name = bone.get("name")
        if not isinstance(name, str) or not name or len(bone.get("head", ())) != 3 or len(bone.get("tail", ())) != 3:
            found.append(("bone_invalid", name))
            continue
        if name in names:
            found.append(("bone_name_repeated", name))
        names.add(name)
        if math.dist(bone["head"], bone["tail"]) < 1e-6:
            found.append(("bone_zero_length", name))
    for bone in bones:
        if bone.get("parent") is not None and bone["parent"] not in names:
            found.append(("bone_parent_missing", [bone.get("name"), bone["parent"]]))
    return found


def parameter_problems(parameters):
    """Problems of a parameter declaration list. Codes: parameter_invalid, parameter_repeated,
    default_out_of_range, choice_default_unknown."""
    found, names = [], set()
    for spec in parameters:
        name, kind = spec.get("name"), spec.get("type")
        if (not isinstance(name, str) or not re.match(r"^[a-z][a-z0-9_]*$", name) or kind not in PARAMETER_TYPES
                or not isinstance(spec.get("unit"), str) or not spec.get("description")):
            found.append(("parameter_invalid", name))
            continue
        if name in names:
            found.append(("parameter_repeated", name))
        names.add(name)
        default = spec.get("default")
        if kind in (PARAMETER_TYPE_INT, PARAMETER_TYPE_FLOAT):
            if not spec["minimum"] <= default <= spec["maximum"]:
                found.append(("default_out_of_range", name))
        elif kind == PARAMETER_TYPE_VECTOR:
            if len(default) != 3 or not all(spec["minimum"] <= value <= spec["maximum"] for value in default):
                found.append(("default_out_of_range", name))
        elif kind == PARAMETER_TYPE_CHOICE and default not in spec.get("choices", ()):
            found.append(("choice_default_unknown", name))
    return found


def expectation_problems(expectations):
    """Problems of the expectations a tool declares for the Blender data it creates.

    Codes: expectations_invalid, expectation_key_unknown, object_expectation_invalid, sample_invalid."""
    if not isinstance(expectations, dict) or not expectations:
        return [("expectations_invalid", type(expectations).__name__)]
    found = [("expectation_key_unknown", key) for key in sorted(set(expectations) - EXPECTATION_KEYS)]
    for name, spec in expectations.get("objects", {}).items():
        if not isinstance(name, str) or not isinstance(spec, dict) or not isinstance(spec.get("type"), str):
            found.append(("object_expectation_invalid", name))
    for number, sample in enumerate(expectations.get("samples", [])):
        if (not isinstance(sample.get("frame"), int) or not isinstance(sample.get("path"), str)
                or not isinstance(sample.get("value"), (int, float, list))):
            found.append(("sample_invalid", number))
    return found + json_problems(expectations)


__all__ = ["OUTPUT_NODES", "INTERPOLATIONS", "SIMPLE_FUNCTIONS", "EXPECTATION_KEYS", "PARAMETER_TYPES",
           "PARAMETER_TYPE_INT", "PARAMETER_TYPE_FLOAT", "PARAMETER_TYPE_BOOL", "PARAMETER_TYPE_CHOICE",
           "PARAMETER_TYPE_STRING", "PARAMETER_TYPE_VECTOR",
           "json_problems", "tree_problems", "channel_problems", "object_problems", "expression_names",
           "driver_problems", "bone_problems", "parameter_problems", "expectation_problems"]
