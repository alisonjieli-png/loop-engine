"""glTF semantic recovery: read what an asset means from the file alone, then compare it with its specification.

    python3 gltf_semantic_recovery.py ASSET.gltf [--spec SPEC.json]

Recovers the named parts (nodes) and their hierarchy, each part's world box and dimensions in metres at the rest
pose, each part's world pivot (node origin) and materials, the clip list with play lengths, and the nodes that
have no name. With --spec, compares those facts with an asset_specification/v1 document (parts with parents,
dimensions, pivots and materials; the material list; clips with durations) and explains the likely cause of a
dimension mismatch: a unit factor (centimetres, millimetres, inches, feet) or Y and Z swapped (Z-up data written
without conversion). Prints one JSON report; exits 0 when the facts match (or no spec is given), 1 otherwise.
"""
from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

import asset_report
import gltfio

TOOL = "gltf_semantic_recovery"
DEFAULT_TOLERANCE_M = 0.005
DEFAULT_CLIP_TOLERANCE_S = 0.05
UNIT_FACTORS = (("centimetres", 100.0), ("millimetres", 1000.0), ("inches", 1 / 0.0254), ("feet", 1 / 0.3048),
                ("decimetres", 10.0))
FAILURES = ("asset_unreadable", "specification_invalid", "part_missing", "part_ambiguous", "part_parent_mismatch",
            "part_dimensions_mismatch", "part_pivot_mismatch", "part_material_mismatch", "material_missing",
            "clip_missing", "clip_duration_mismatch")


def recover(asset: gltfio.Asset) -> dict:
    """The facts a reader can recover from the asset alone (metres, glTF axes, rest pose)."""
    document, nodes = asset.document, asset.items("nodes")
    matrices = gltfio.world_matrices(document)
    own = gltfio.node_world_bounds(asset)
    parents = gltfio.parents(document)
    materials = asset.items("materials")
    parts = []
    for index, node in enumerate(nodes):
        if index not in matrices:
            continue
        box = own.get(index)
        subtree = gltfio.subtree_bounds(asset, index, per_node=own)
        mesh = node.get("mesh")
        used = []
        if isinstance(mesh, int) and 0 <= mesh < len(asset.items("meshes")):
            for primitive in asset.items("meshes")[mesh].get("primitives", []):
                material = primitive.get("material")
                used.append(materials[material].get("name") if isinstance(material, int)
                            and 0 <= material < len(materials) else None)
        parent = parents.get(index)
        parts.append({
            "index": index, "name": node.get("name"), "path": gltfio.node_path(document, index),
            "parent": nodes[parent].get("name") if parent is not None else None, "parent_index": parent,
            "pivot_m": [matrices[index][row][3] for row in range(3)],
            "dimensions_m": [box[1][axis] - box[0][axis] for axis in range(3)] if box else None,
            "bounds_m": {"min": list(box[0]), "max": list(box[1])} if box else None,
            "subtree_dimensions_m": [subtree[1][axis] - subtree[0][axis] for axis in range(3)] if subtree else None,
            "materials": used})
    clips = [{"name": clip["name"], "start_s": clip["start"], "length_s": clip["end"],
              "channels": len(clip["channels"])} for clip in gltfio.animation_clips(asset)]
    scene = gltfio.scene_bounds(asset)
    return {"parts": parts, "clips": clips,
            "materials": [material.get("name") for material in materials],
            "unnamed_nodes": [part["index"] for part in parts if not part["name"]],
            "scene_dimensions_m": [scene[1][axis] - scene[0][axis] for axis in range(3)] if scene else None}


def dimension_hint(expected: list, found: list, tolerance: float) -> str:
    """A likely cause of a dimension mismatch, or an empty string."""
    ratios = [value / reference for reference, value in zip(expected, found) if reference > 1e-9]
    if ratios and min(ratios) > 0 and max(ratios) / min(ratios) < 1.02:
        ratio = sum(ratios) / len(ratios)
        for name, factor in UNIT_FACTORS:
            if abs(ratio / factor - 1) < 0.02:
                return f"every axis is {factor:g} times the specification: the file was likely written in {name}"
            if abs(ratio * factor - 1) < 0.02:
                return f"every axis is 1/{factor:g} of the specification: metres were likely read as {name}"
    swapped = [found[0], found[2], found[1]]
    if all(abs(a - b) <= tolerance for a, b in zip(expected, swapped)):
        return "Y and Z are swapped: likely Z-up data written into this Y-up file without conversion"
    return ""


def _number_list(value, length: int) -> bool:
    return isinstance(value, list) and len(value) == length and all(
        type(item) in (int, float) and not isinstance(item, bool) for item in value)


def read_specification(spec, report: asset_report.Report) -> "dict | None":
    if not isinstance(spec, dict) or spec.get("record_type") != "asset_specification/v1" \
            or not isinstance(spec.get("parts"), list):
        report.fail("specification_invalid", "spec", "an asset_specification/v1 object with a parts list")
        return None
    for index, part in enumerate(spec["parts"]):
        if not isinstance(part, dict) or not isinstance(part.get("name"), str) or not part["name"]:
            report.fail("specification_invalid", f"parts[{index}]", "each part has a name")
            return None
        for key in ("dimensions_m", "pivot_m"):
            if key in part and not _number_list(part[key], 3):
                report.fail("specification_invalid", f"parts[{index}].{key}", "three numbers")
                return None
    for key in ("clips", "materials"):
        if not isinstance(spec.get(key, []), list):
            report.fail("specification_invalid", key, "a list")
            return None
    return spec


def compare(facts: dict, spec: dict, report: asset_report.Report) -> None:
    tolerance = spec.get("tolerance_m", DEFAULT_TOLERANCE_M)
    by_name = {}
    for part in facts["parts"]:
        by_name.setdefault(part["name"], []).append(part)
    names = [name for name in by_name if name]
    for expected in spec["parts"]:
        name, limit = expected["name"], expected.get("tolerance_m", tolerance)
        found = by_name.get(name, [])
        if not found:
            close = difflib.get_close_matches(name, names, n=3, cutoff=0.6)
            report.fail("part_missing", name, f"no node named {name!r}; {len(facts['unnamed_nodes'])} unnamed nodes"
                        + (f"; similar names: {close}" if close else ""))
            continue
        if len(found) > 1:
            report.fail("part_ambiguous", name, f"{len(found)} nodes share the name")
            continue
        part = found[0]
        if "parent" in expected and expected["parent"] != part["parent"]:
            report.fail("part_parent_mismatch", name, f"specified parent {expected['parent']!r}, file has "
                                                      f"{part['parent']!r}")
        if "dimensions_m" in expected:
            measured = part["subtree_dimensions_m"] if expected.get("measure") == "subtree" else part["dimensions_m"]
            if measured is None:
                report.fail("part_dimensions_mismatch", name, "the part has no mesh to measure")
            elif any(abs(a - b) > limit for a, b in zip(expected["dimensions_m"], measured)):
                hint = dimension_hint(expected["dimensions_m"], measured, limit)
                report.fail("part_dimensions_mismatch", name,
                            f"specified {expected['dimensions_m']} m, measured {[round(v, 4) for v in measured]} m"
                            + (f"; {hint}" if hint else ""))
        if "pivot_m" in expected and any(abs(a - b) > limit for a, b in zip(expected["pivot_m"], part["pivot_m"])):
            report.fail("part_pivot_mismatch", name, f"specified {expected['pivot_m']}, file has "
                                                     f"{[round(v, 4) for v in part['pivot_m']]}")
        if "material" in expected:
            wanted = expected["material"] if isinstance(expected["material"], list) else [expected["material"]]
            if sorted(map(str, wanted)) != sorted(map(str, part["materials"])):
                report.fail("part_material_mismatch", name, f"specified {wanted}, file has {part['materials']}")
    present = set(facts["materials"])
    for material in spec.get("materials", []):
        material_name = material.get("name") if isinstance(material, dict) else material
        if material_name not in present:
            report.fail("material_missing", str(material_name), f"materials in the file: {sorted(map(str, present))}")
    clips = {clip["name"]: clip for clip in facts["clips"]}
    for clip in spec.get("clips", []):
        if not isinstance(clip, dict) or clip.get("name") not in clips:
            report.fail("clip_missing", str(clip.get("name") if isinstance(clip, dict) else clip),
                        f"clips in the file: {sorted(clips)}")
            continue
        if "duration_s" in clip:
            found = clips[clip["name"]]["length_s"]
            if abs(found - clip["duration_s"]) > clip.get("tolerance_s", DEFAULT_CLIP_TOLERANCE_S):
                report.fail("clip_duration_mismatch", clip["name"], f"specified {clip['duration_s']} s, file plays "
                                                                    f"{round(found, 4)} s")


def check(asset_path, spec_path=None) -> asset_report.Report:
    report = asset_report.Report(TOOL, Path(asset_path).name)
    try:
        asset = gltfio.load(asset_path)
        facts = recover(asset)
    except gltfio.GltfError as error:
        report.fail("asset_unreadable", Path(asset_path).name, f"{error.reason} {error.detail}")
        return report
    report.facts = facts
    if facts["unnamed_nodes"]:
        report.warn("unnamed_nodes", "nodes", f"{len(facts['unnamed_nodes'])} nodes have no name; their meaning "
                                              "cannot be recovered from the file")
    for clip in facts["clips"]:
        if clip["start_s"] > 1e-6:
            report.warn("clip_starts_late", clip["name"], f"first key at {clip['start_s']} s; engines hold it from 0")
    if spec_path is not None:
        spec = asset_report.read_json_file(spec_path, report, "specification_invalid")
        if spec is not None and read_specification(spec, report) is not None:
            compare(facts, spec, report)
    return report


def run(argv: list) -> dict:
    parser = argparse.ArgumentParser(prog=TOOL, description=__doc__.split("\n\n")[0])
    parser.add_argument("asset", help="a .gltf or .glb file")
    parser.add_argument("--spec", help="an asset_specification/v1 JSON file to compare with")
    arguments = parser.parse_args(argv)
    return check(arguments.asset, arguments.spec).as_dict()


def main(argv=None) -> int:
    return asset_report.emit(run(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    sys.exit(main())
