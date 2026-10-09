"""Asset specification schema: validate an asset_specification/v1 document and build a blockout asset from it.

    python3 asset_specification_schema.py SPEC.json [--blockout OUT.gltf]

An asset specification says what a 3D asset must be before anyone models it: named parts with parents, real
dimensions, centres, pivots and materials; joints with axes and limits; clips; behaviors. schema.json is the JSON
Schema (draft 2020-12) any validator can use. This tool applies it with the standard library and adds the rules a
schema cannot express: unique names, parents that exist and form no cycle, joints on existing parts with unit axes
and ordered limits that fit the joint type, clip targets and behavior references that exist, and materials that are
declared. With --blockout it writes a placeholder glTF: one box per part at its centre and size, node origins at the
pivots, the declared materials, and for each revolute or prismatic joint one clip per non-zero limit
(<joint>_lower, <joint>_upper) that moves the part from the modelled pose (joint value 0) to that limit in one second.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import asset_report
import gltfio
import schema_lite

TOOL = "asset_specification_schema"
SCHEMA = json.loads((Path(__file__).resolve().parent / "schema.json").read_text(encoding="utf-8"))
FAILURES = ("specification_unreadable", "schema_violation", "part_name_repeated", "parent_unknown", "parent_cycle",
            "joint_part_unknown", "joint_part_repeated", "joint_axis_zero", "joint_axis_not_unit",
            "joint_limits_invalid", "clip_name_repeated", "clip_target_unknown", "behavior_reference_unknown",
            "material_name_repeated", "material_unknown")
FLOAT, USHORT = 5126, 5123


def validate(spec) -> asset_report.Report:
    """Schema and cross-reference rules for one specification value."""
    report = asset_report.Report(TOOL, spec.get("asset", "") if isinstance(spec, dict) else "")
    errors = schema_lite.validate(spec, SCHEMA)
    for error in errors[:40]:
        report.fail("schema_violation", error["path"], f"{error['keyword']}: {error['message']}")
    if errors:
        return report
    parts = {part["name"]: part for part in spec["parts"]}
    _repeated(report, [part["name"] for part in spec["parts"]], "part_name_repeated")
    for part in spec["parts"]:
        if part.get("parent") is not None and part["parent"] not in parts:
            report.fail("parent_unknown", part["name"], f"parent {part['parent']!r} is not a part")
    _cycles(report, parts)
    materials = [material["name"] for material in spec.get("materials", [])]
    _repeated(report, materials, "material_name_repeated")
    if "materials" in spec:
        for part in spec["parts"]:
            wanted = part.get("material", [])
            for material in wanted if isinstance(wanted, list) else [wanted]:
                if material not in materials:
                    report.fail("material_unknown", part["name"], f"material {material!r} is not declared")
    joints = spec.get("joints", [])
    _repeated(report, [joint["part"] for joint in joints], "joint_part_repeated")
    for joint in joints:
        _check_joint(report, joint, parts)
    clips = spec.get("clips", [])
    _repeated(report, [clip["name"] for clip in clips], "clip_name_repeated")
    for clip in clips:
        for target in clip.get("targets", []):
            if target["part"] not in parts:
                report.fail("clip_target_unknown", clip["name"], f"target part {target['part']!r} is not a part")
    joint_names, clip_names = {joint["name"] for joint in joints}, {clip["name"] for clip in clips}
    for behavior in spec.get("behaviors", []):
        for key, known in (("joint", joint_names), ("clip", clip_names)):
            if key in behavior and behavior[key] not in known:
                report.fail("behavior_reference_unknown", behavior["name"], f"{key} {behavior[key]!r} is not declared")
    roots = [part["name"] for part in spec["parts"] if part.get("parent") is None]
    if len(roots) > 1:
        report.warn("several_roots", "parts", f"{len(roots)} parts have no parent: {roots[:6]}")
    report.facts = {"parts": len(parts), "roots": roots, "joints": [joint["name"] for joint in joints],
                    "clips": sorted(clip_names), "materials": materials, "depth": _depth(parts)}
    return report


def _repeated(report: asset_report.Report, names: list, code: str) -> None:
    for name in sorted({name for name in names if names.count(name) > 1}):
        report.fail(code, name, f"declared {names.count(name)} times")


def _cycles(report: asset_report.Report, parts: dict) -> None:
    for name in parts:
        seen, current = set(), name
        while current is not None and current in parts and current not in seen:
            seen.add(current)
            current = parts[current].get("parent")
        if current == name:
            report.fail("parent_cycle", name, "following parents returns to this part")


def _depth(parts: dict) -> int:
    deepest = 0
    for name in parts:
        depth, current, seen = 0, parts[name].get("parent"), {name}
        while current in parts and current not in seen:
            seen.add(current)
            depth += 1
            current = parts[current].get("parent")
        deepest = max(deepest, depth)
    return deepest


def _check_joint(report: asset_report.Report, joint: dict, parts: dict) -> None:
    name, kind = joint["name"], joint["type"]
    if joint["part"] not in parts:
        report.fail("joint_part_unknown", name, f"part {joint['part']!r} is not a part")
    length = math.sqrt(sum(value * value for value in joint["axis"]))
    if length < 1e-9:
        report.fail("joint_axis_zero", name, "the axis has no direction")
    elif abs(length - 1.0) > 1e-3:
        report.fail("joint_axis_not_unit", name, f"axis length {length:.6f}")
    wanted = {"revolute": "limits_deg", "prismatic": "limits_m"}.get(kind)
    present = [key for key in ("limits_deg", "limits_m") if key in joint]
    if wanted and present != [wanted]:
        report.fail("joint_limits_invalid", name, f"a {kind} joint declares {wanted} and no other limits")
    elif not wanted and present:
        report.fail("joint_limits_invalid", name, f"a {kind} joint declares no limits")
    elif wanted:
        lower, upper = joint[wanted]
        if not lower < upper:
            report.fail("joint_limits_invalid", name, f"lower {lower} is not below upper {upper}")
        elif "rest" in joint and not lower <= joint["rest"] <= upper:
            report.fail("joint_limits_invalid", name, f"rest {joint['rest']} is outside [{lower}, {upper}]")


def _axis_angle(axis, degrees: float) -> tuple:
    length = math.sqrt(sum(value * value for value in axis))
    half = math.radians(degrees) / 2.0
    return tuple(value / length * math.sin(half) for value in axis) + (math.cos(half),)


def blockout(spec: dict) -> dict:
    """A placeholder glTF document realising a valid specification (modelled pose, no rotations)."""
    parts = spec["parts"]
    index = {part["name"]: position for position, part in enumerate(parts)}
    materials = spec.get("materials", [])
    material_index = {material["name"]: position for position, material in enumerate(materials)}
    document = {"asset": {"version": "2.0", "generator": f"{TOOL} blockout"}, "scene": 0,
                "scenes": [{"name": spec["asset"], "nodes": [index[part["name"]] for part in parts
                                                             if part.get("parent") is None]}],
                "materials": [{"name": material["name"], "pbrMetallicRoughness": {
                    "baseColorFactor": material.get("base_color", [0.8, 0.8, 0.8, 1.0]),
                    "metallicFactor": material.get("metallic", 0.0), "roughnessFactor": material.get("roughness", 0.8)}}
                    for material in materials],
                "nodes": [], "meshes": []}
    builder = gltfio.BufferBuilder(document)
    for part in parts:
        pivot = part.get("pivot_m", part.get("center_m", [0.0, 0.0, 0.0]))
        parent = part.get("parent")
        parent_pivot = [0.0, 0.0, 0.0] if parent is None else parts[index[parent]].get(
            "pivot_m", parts[index[parent]].get("center_m", [0.0, 0.0, 0.0]))
        node = {"name": part["name"], "translation": [pivot[axis] - parent_pivot[axis] for axis in range(3)]}
        children = [index[other["name"]] for other in parts if other.get("parent") == part["name"]]
        if children:
            node["children"] = children
        if "dimensions_m" in part:
            center = part.get("center_m", pivot)
            low = [center[axis] - pivot[axis] - part["dimensions_m"][axis] / 2 for axis in range(3)]
            high = [center[axis] - pivot[axis] + part["dimensions_m"][axis] / 2 for axis in range(3)]
            primitive = _box(builder, low, high)
            wanted = part.get("material")
            first = wanted[0] if isinstance(wanted, list) else wanted
            if first in material_index:
                primitive["material"] = material_index[first]
            document["meshes"].append({"name": part["name"] + "Mesh", "primitives": [primitive]})
            node["mesh"] = len(document["meshes"]) - 1
        document["nodes"].append(node)
    for joint in spec.get("joints", []):
        if joint["type"] not in ("revolute", "prismatic"):
            continue
        node = index[joint["part"]]
        rest = document["nodes"][node]["translation"]
        limits = joint["limits_deg"] if joint["type"] == "revolute" else joint["limits_m"]
        for label, limit in (("lower", limits[0]), ("upper", limits[1])):
            if limit == 0:
                continue
            times = builder.add([(0.0,), (0.5,), (1.0,)], FLOAT, "SCALAR", bounds=True)
            steps = (0.0, limit / 2, limit)
            if joint["type"] == "revolute":
                values = [_axis_angle(joint["axis"], angle) for angle in steps]
                path, kind = "rotation", "VEC4"
            else:
                values = [tuple(rest[axis] + joint["axis"][axis] * offset for axis in range(3)) for offset in steps]
                path, kind = "translation", "VEC3"
            output = builder.add(values, FLOAT, kind)
            document.setdefault("animations", []).append({
                "name": f"{joint['name']}_{label}", "samplers": [{"input": times, "output": output}],
                "channels": [{"sampler": 0, "target": {"node": node, "path": path}}]})
    return builder.finish()


def _box(builder: gltfio.BufferBuilder, low, high) -> dict:
    positions, normals, indices = [], [], []
    for axis, u, v in ((0, 1, 2), (1, 2, 0), (2, 0, 1)):
        for sign in (1, -1):
            corners = []
            for cu, cv in ((0, 0), (1, 0), (1, 1), (0, 1)):
                point = [0.0, 0.0, 0.0]
                point[axis] = high[axis] if sign > 0 else low[axis]
                point[u], point[v] = (low[u], high[u])[cu], (low[v], high[v])[cv]
                corners.append(tuple(point))
            if sign < 0:
                corners = [corners[0], corners[3], corners[2], corners[1]]
            base = len(positions)
            positions += corners
            normals += [tuple(float(sign) if index == axis else 0.0 for index in range(3))] * 4
            indices += [base, base + 1, base + 2, base, base + 2, base + 3]
    return {"attributes": {"POSITION": builder.add(positions, FLOAT, "VEC3", 34962, bounds=True),
                           "NORMAL": builder.add(normals, FLOAT, "VEC3", 34962)},
            "indices": builder.add([(value,) for value in indices], USHORT, "SCALAR", 34963)}


def check(spec_path, blockout_path=None) -> asset_report.Report:
    report = asset_report.Report(TOOL, Path(spec_path).name)
    spec = asset_report.read_json_file(spec_path, report, "specification_unreadable")
    if spec is None:
        return report
    result = validate(spec)
    result.subject = Path(spec_path).name
    if blockout_path is not None and result.as_dict()["ok"]:
        Path(blockout_path).write_text(gltfio.dumps(blockout(spec)), encoding="utf-8")
        result.facts["blockout"] = Path(blockout_path).name
    return result


def run(argv: list) -> dict:
    parser = argparse.ArgumentParser(prog=TOOL, description=__doc__.split("\n\n")[0])
    parser.add_argument("spec", help="an asset_specification/v1 JSON file")
    parser.add_argument("--blockout", help="write a placeholder .gltf realising a valid specification")
    arguments = parser.parse_args(argv)
    return check(arguments.spec, arguments.blockout).as_dict()


def main(argv=None) -> int:
    return asset_report.emit(run(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    sys.exit(main())
