"""Articulation loss checker: an export that kept the meshes but lost what the joints need.

    python3 articulation_loss_checker.py EXPORT.gltf --manifest MANIFEST.json [--reference REFERENCE.gltf]
                                         [--extras required] [--tolerance-m 0.001] [--tolerance-deg 0.5]

The manifest (articulation_manifest/v1) says which node each joint moves, about which axis and pivot in the node's
own frame. Exporters and clean-up steps break that silently while every mesh stays in place: joining parts merges
the moving node into its parent, "origin to geometry" moves the node origin off the hinge, applying rotation turns
the node's frame so the same local axis points elsewhere, flattening the hierarchy detaches a handle from its door,
and a default export leaves out the custom properties that carried the joint record. This tool reports each of
those against the manifest and, when given, a reference export known to be right.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import asset_report
import gltfio

TOOL = "articulation_loss_checker"
FAILURES = ("asset_unreadable", "reference_unreadable", "manifest_invalid", "joint_node_missing",
            "joint_node_ambiguous", "joint_node_without_geometry", "pivot_moved", "joint_axis_changed",
            "joint_parent_changed", "joint_extras_missing", "joint_extras_mismatch")


def read_joints(value, report: asset_report.Report) -> list:
    if not isinstance(value, dict) or value.get("record_type") != "articulation_manifest/v1" \
            or not isinstance(value.get("joints"), list):
        report.fail("manifest_invalid", "manifest", "an articulation_manifest/v1 object with a joints list")
        return []
    joints = []
    for position, joint in enumerate(value["joints"]):
        axis, pivot = (joint.get("axis"), joint.get("pivot", [0.0, 0.0, 0.0])) if isinstance(joint, dict) else (0, 0)
        if not isinstance(joint, dict) or not isinstance(joint.get("node"), str) or not _vector(axis) \
                or not _vector(pivot) or math.sqrt(sum(item * item for item in axis)) < 1e-9:
            report.fail("manifest_invalid", f"joints[{position}]", "each joint has a node, an axis and a pivot")
            continue
        joints.append(joint)
    return joints


def _vector(value) -> bool:
    return isinstance(value, list) and len(value) == 3 and all(type(item) in (int, float) for item in value)


def joint_facts(asset: gltfio.Asset, joint: dict) -> dict:
    """Where one joint ended up in one asset: node presence, parent, world pivot, world axis, extras record."""
    nodes = asset.items("nodes")
    matches = [index for index, node in enumerate(nodes) if node.get("name") == joint["node"]]
    facts = {"node": joint["node"], "present": len(matches) == 1, "count": len(matches)}
    if len(matches) != 1:
        return facts
    index = matches[0]
    matrix = gltfio.world_matrices(asset.document).get(index)
    parent = gltfio.parents(asset.document).get(index)
    below = _subtree(nodes, index)
    facts.update({"index": index, "parent": nodes[parent].get("name") if parent is not None else None,
                  "has_geometry": any(isinstance(nodes[item].get("mesh"), int) for item in below),
                  "extras": nodes[index].get("extras", {}).get("joint") if isinstance(nodes[index].get("extras"),
                                                                                    dict) else None})
    if matrix is not None:
        axis = [sum(matrix[row][k] * joint["axis"][k] for k in range(3)) for row in range(3)]
        length = math.sqrt(sum(item * item for item in axis)) or 1.0
        facts["world_pivot"] = list(gltfio.transform_point(matrix, joint.get("pivot", [0.0, 0.0, 0.0])))
        facts["world_axis"] = [item / length for item in axis]
    return facts


def _subtree(nodes: list, root: int) -> list:
    found, stack = [], [root]
    while stack:
        index = stack.pop()
        if index not in found and 0 <= index < len(nodes):
            found.append(index)
            stack.extend(child for child in nodes[index].get("children", []) if isinstance(child, int))
    return found


def _same_record(found: dict, joint: dict) -> bool:
    for key in ("type", "axis", "pivot", "limits"):
        if key not in joint:
            continue
        expected, actual = joint[key], found.get(key)
        if isinstance(expected, list):
            if not isinstance(actual, list) or len(actual) != len(expected) or any(
                    abs(a - b) > 1e-6 for a, b in zip(actual, expected)):
                return False
        elif actual != expected:
            return False
    return True


def compare(joints: list, export: gltfio.Asset, reference: "gltfio.Asset | None", extras_required: bool,
            tolerance_m: float, tolerance_deg: float, report: asset_report.Report) -> list:
    rows = []
    for joint in joints:
        name = joint.get("name", joint["node"])
        found = joint_facts(export, joint)
        row = {"joint": name, "export": found}
        rows.append(row)
        if found["count"] == 0:
            report.fail("joint_node_missing", name, f"no node named {joint['node']!r}: joined, renamed or deleted")
            continue
        if found["count"] > 1:
            report.fail("joint_node_ambiguous", name, f"{found['count']} nodes are named {joint['node']!r}")
            continue
        if not found["has_geometry"]:
            report.fail("joint_node_without_geometry", name, "no mesh at or below the node: the joint moves nothing")
        if extras_required:
            if found["extras"] is None:
                report.fail("joint_extras_missing", name, "the node's extras carry no joint record (custom properties "
                                                          "not exported?)")
            elif not _same_record(found["extras"], joint):
                report.fail("joint_extras_mismatch", name, f"extras record {found['extras']} differs from the manifest")
        if reference is None:
            continue
        expected = joint_facts(reference, joint)
        row["reference"] = expected
        if not expected["present"] or "world_pivot" not in expected or "world_pivot" not in found:
            continue
        distance = math.dist(expected["world_pivot"], found["world_pivot"])
        if distance > tolerance_m:
            before = [round(value, 4) for value in expected["world_pivot"]]
            after = [round(value, 4) for value in found["world_pivot"]]
            report.fail("pivot_moved", name, f"world pivot moved {distance:.4f} m: {before} -> {after}")
        cosine = max(-1.0, min(1.0, sum(a * b for a, b in zip(expected["world_axis"], found["world_axis"]))))
        angle = math.degrees(math.acos(cosine))
        if angle > tolerance_deg:
            report.fail("joint_axis_changed", name, f"world axis turned {angle:.2f} degrees: "
                                                    f"{[round(v, 4) for v in expected['world_axis']]} -> "
                                                    f"{[round(v, 4) for v in found['world_axis']]}")
        if expected["parent"] != found["parent"]:
            report.fail("joint_parent_changed", name, f"parent {expected['parent']!r} -> {found['parent']!r}: the "
                                                      "part no longer follows its parent")
    return rows


def check(export_path, manifest_path, reference_path=None, extras_required=False, tolerance_m=0.001,
          tolerance_deg=0.5) -> asset_report.Report:
    report = asset_report.Report(TOOL, Path(export_path).name)
    try:
        export = gltfio.load(export_path)
        gltfio.world_matrices(export.document)
    except gltfio.GltfError as error:
        report.fail("asset_unreadable", Path(export_path).name, f"{error.reason} {error.detail}")
        return report
    reference = None
    if reference_path is not None:
        try:
            reference = gltfio.load(reference_path)
        except gltfio.GltfError as error:
            report.fail("reference_unreadable", Path(reference_path).name, f"{error.reason} {error.detail}")
            return report
    value = asset_report.read_json_file(manifest_path, report, "manifest_invalid")
    joints = read_joints(value, report) if value is not None else []
    report.facts = {"joints": compare(joints, export, reference, extras_required, tolerance_m, tolerance_deg, report),
                    "reference": Path(reference_path).name if reference_path else None,
                    "extras_required": extras_required}
    return report


def run(argv: list) -> dict:
    parser = argparse.ArgumentParser(prog=TOOL, description=__doc__.split("\n\n")[0])
    parser.add_argument("export", help="the exported .gltf or .glb")
    parser.add_argument("--manifest", required=True, help="articulation_manifest/v1 JSON")
    parser.add_argument("--reference", help="an export known to keep the joints (for pivot, axis and parent checks)")
    parser.add_argument("--extras", choices=("required", "optional"), default="optional",
                        help="whether each joint node must carry its joint record in extras.joint")
    parser.add_argument("--tolerance-m", type=float, default=0.001)
    parser.add_argument("--tolerance-deg", type=float, default=0.5)
    arguments = parser.parse_args(argv)
    return check(arguments.export, arguments.manifest, arguments.reference, arguments.extras == "required",
                 arguments.tolerance_m, arguments.tolerance_deg).as_dict()


def main(argv=None) -> int:
    return asset_report.emit(run(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    sys.exit(main())
