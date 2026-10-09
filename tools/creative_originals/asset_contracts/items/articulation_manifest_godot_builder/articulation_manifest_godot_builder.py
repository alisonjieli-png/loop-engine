"""Articulation manifest: hinges and sliders bound to named glTF nodes, checked and posed without an engine.

    python3 articulation_manifest_godot_builder.py ASSET.gltf --manifest MANIFEST.json

A glTF file has no joints. An articulation manifest (articulation_manifest/v1) beside it names, for each joint, the
node it moves, its type (hinge or slider), its axis and pivot in the node's own frame at rest, and its limits
(degrees for a hinge, metres for a slider). This tool checks that the manifest binds to the asset (every node exists
exactly once, one joint per node, unit axes, ordered limits) and predicts, by forward kinematics, each moving node's
world transform and world pivot at both limits. godot/articulated_asset.gd applies the same manifest in Godot 4 at run
time; the native evidence shows the two agree.

A joint value v moves its node's local transform from REST to REST * M(v), where M(v) rotates by v degrees about the
axis through the pivot (hinge) or translates v metres along the axis (slider).
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import asset_report
import gltfio

TOOL = "articulation_manifest_godot_builder"
TYPES = {"hinge": 360.0, "slider": 1000.0}
FAILURES = ("asset_unreadable", "manifest_invalid", "joint_type_invalid", "node_missing", "node_ambiguous",
            "node_jointed_twice", "axis_invalid", "pivot_invalid", "limits_invalid", "joint_name_repeated")


def _vector(value, length: int = 3) -> bool:
    return isinstance(value, list) and len(value) == length and all(
        type(item) in (int, float) and math.isfinite(item) for item in value)


def read_manifest(value, document: dict, report: asset_report.Report) -> list:
    """Joints that bind cleanly, as dicts with node index, unit axis, pivot and limits; failures go to the report."""
    if not isinstance(value, dict) or value.get("record_type") != "articulation_manifest/v1" \
            or not isinstance(value.get("joints"), list):
        report.fail("manifest_invalid", "manifest", "an articulation_manifest/v1 object with a joints list")
        return []
    names = [node.get("name") for node in document.get("nodes", [])]
    joints, used_nodes, used_names = [], {}, set()
    for position, joint in enumerate(value["joints"]):
        where = joint.get("name", f"joints[{position}]") if isinstance(joint, dict) else f"joints[{position}]"
        if not isinstance(joint, dict) or not isinstance(joint.get("name"), str) or not joint["name"]:
            report.fail("manifest_invalid", where, "each joint has a name")
            continue
        if joint["name"] in used_names:
            report.fail("joint_name_repeated", where, "joint names are unique")
            continue
        used_names.add(joint["name"])
        if joint.get("type") not in TYPES:
            report.fail("joint_type_invalid", where, f"type is one of {sorted(TYPES)}")
            continue
        matches = [index for index, name in enumerate(names) if name == joint.get("node")]
        if not matches:
            report.fail("node_missing", where, f"no node named {joint.get('node')!r}")
            continue
        if len(matches) > 1:
            report.fail("node_ambiguous", where, f"{len(matches)} nodes are named {joint['node']!r}")
            continue
        if matches[0] in used_nodes:
            report.fail("node_jointed_twice", where, f"node {joint['node']!r} already moves with "
                                                     f"{used_nodes[matches[0]]!r}")
            continue
        axis = joint.get("axis")
        length = math.sqrt(sum(item * item for item in axis)) if _vector(axis) else 0.0
        if length < 1e-9 or abs(length - 1.0) > 1e-3:
            report.fail("axis_invalid", where, f"axis {axis!r} is not a unit vector")
            continue
        pivot = joint.get("pivot", [0.0, 0.0, 0.0])
        if not _vector(pivot):
            report.fail("pivot_invalid", where, f"pivot {pivot!r} is not three finite numbers")
            continue
        limits = joint.get("limits")
        bound = TYPES[joint["type"]]
        if not _vector(limits, 2) or not -bound <= limits[0] < limits[1] <= bound or not \
                limits[0] <= joint.get("rest", 0.0) <= limits[1]:
            report.fail("limits_invalid", where, f"limits {limits!r} must be [lower, upper] with lower < upper, "
                                                 f"within +-{bound:g}, around the rest value")
            continue
        used_nodes[matches[0]] = joint["name"]
        joints.append({"name": joint["name"], "type": joint["type"], "node": matches[0], "node_name": joint["node"],
                       "axis": [item / length for item in axis], "pivot": [float(item) for item in pivot],
                       "limits": [float(limits[0]), float(limits[1])], "rest": float(joint.get("rest", 0.0))})
    return joints


def joint_motion(joint: dict, value: float) -> list:
    """The 4x4 local motion M(value) of one joint."""
    if joint["type"] == "slider":
        return gltfio.compose([component * value for component in joint["axis"]])
    half = math.radians(value) / 2.0
    rotation = [component * math.sin(half) for component in joint["axis"]] + [math.cos(half)]
    pivot = joint["pivot"]
    return gltfio.multiply(gltfio.multiply(gltfio.compose(pivot), gltfio.compose(rotation=rotation)),
                           gltfio.compose([-component for component in pivot]))


def pose(document: dict, joints: list, values: dict) -> dict:
    """Node index -> world matrix with each named joint at its value, clamped to its limits."""
    motions = {}
    for joint in joints:
        value = min(max(values.get(joint["name"], joint["rest"]), joint["limits"][0]), joint["limits"][1])
        motions[joint["node"]] = joint_motion(joint, value)
    nodes, result = document.get("nodes", []), {}
    stack = [(root, gltfio.IDENTITY) for root in reversed(gltfio.scene_roots(document))]
    while stack:
        index, parent = stack.pop()
        if index in result or not 0 <= index < len(nodes):
            continue
        local = gltfio.node_local_matrix(nodes[index])
        if index in motions:
            local = gltfio.multiply(local, motions[index])
        result[index] = gltfio.multiply(parent, local)
        stack.extend((child, result[index]) for child in reversed(nodes[index].get("children", [])))
    return result


def predictions(document: dict, joints: list) -> list:
    """Per joint, the moving node's world matrix (3 rows of 4) and world pivot at the lower and upper limits."""
    rows = []
    for joint in joints:
        row = {"joint": joint["name"], "node": joint["node_name"], "type": joint["type"], "limits": joint["limits"]}
        for label, value in (("lower", joint["limits"][0]), ("upper", joint["limits"][1])):
            matrix = pose(document, joints, {joint["name"]: value})[joint["node"]]
            row[label] = {"world_matrix": [list(line) for line in matrix[:3]],
                          "world_pivot": list(gltfio.transform_point(matrix, joint["pivot"]))}
        rows.append(row)
    return rows


def check(asset_path, manifest_path) -> asset_report.Report:
    report = asset_report.Report(TOOL, Path(asset_path).name)
    try:
        asset = gltfio.load(asset_path)
        gltfio.world_matrices(asset.document)
    except gltfio.GltfError as error:
        report.fail("asset_unreadable", Path(asset_path).name, f"{error.reason} {error.detail}")
        return report
    value = asset_report.read_json_file(manifest_path, report, "manifest_invalid")
    joints = read_manifest(value, asset.document, report) if value is not None else []
    meshes = gltfio.node_world_bounds(asset)
    for joint in joints:
        below = {index for index in _subtree(asset.document, joint["node"])}
        if not below & set(meshes):
            report.warn("joint_moves_nothing", joint["name"], "no mesh at or below the node")
    report.facts = {"joints": predictions(asset.document, joints)}
    return report


def _subtree(document: dict, root: int) -> list:
    nodes, stack, seen = document.get("nodes", []), [root], []
    while stack:
        index = stack.pop()
        if index not in seen and 0 <= index < len(nodes):
            seen.append(index)
            stack.extend(nodes[index].get("children", []))
    return seen


def run(argv: list) -> dict:
    parser = argparse.ArgumentParser(prog=TOOL, description=__doc__.split("\n\n")[0])
    parser.add_argument("asset", help="the .gltf or .glb the manifest describes")
    parser.add_argument("--manifest", required=True, help="articulation_manifest/v1 JSON")
    arguments = parser.parse_args(argv)
    return check(arguments.asset, arguments.manifest).as_dict()


def main(argv=None) -> int:
    return asset_report.emit(run(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    sys.exit(main())
