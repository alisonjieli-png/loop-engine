"""Axes and units checker and converter for glTF: up axis, handedness and length unit.

    python3 axes_units_converter.py check ASSET.gltf --expect-dimensions X Y Z [--tolerance 0.005]
    python3 axes_units_converter.py convert IN.gltf OUT.gltf --from CONVENTION [--to gltf] [--unit-m 0.01]

glTF is +Y up, right-handed, in metres, with the front of an asset facing +Z. Data written by a Z-up tool without
conversion stands on its back, data from a left-handed tool is mirrored with inside-out triangles, and data modelled
in centimetres is a hundred times too large. `check` measures the scene box and the triangle winding against the
stored normals and names the likely cause: up_axis_mismatch, unit_scale_mismatch, dimensions_mismatch or
winding_inverted. `convert` rewrites a file from one convention and unit into another: every node transform is
conjugated, every point, vector, tangent, inverse bind matrix and animation output is mapped, and triangle winding
is reversed when the change would otherwise turn front faces into back faces.

A convention is an up axis, a forward axis (the way the asset's front faces), a handedness and the winding of front
faces. The asset's right is forward x up in a right-handed convention and up x forward in a left-handed one. A point
moves from source to target coordinates by k * F_target * F_source^T, where F holds right, up and forward as columns
and k is the unit factor. Triangle order is reversed exactly when the change mirrors (negative determinant) and the
two conventions use the same front-face winding, or when it does not mirror and their windings differ.
"""
from __future__ import annotations

import argparse
import copy
import math
import sys
from pathlib import Path

import asset_report
import gltfio

TOOL = "axes_units_converter"
#: name: (up, forward, handedness, front-face winding). gltf is the target of glTF files; z_up_right is Blender's object
#: space; the two left-handed entries describe data whose front faces wind clockwise.
CONVENTIONS = {"gltf": ("+Y", "+Z", "right", "ccw"), "z_up_right": ("+Z", "-Y", "right", "ccw"),
               "y_up_left_cw": ("+Y", "+Z", "left", "cw"), "z_up_left_cw": ("+Z", "+X", "left", "cw")}
UNIT_FACTORS = (("centimetres", 100.0), ("millimetres", 1000.0), ("inches", 1 / 0.0254), ("feet", 1 / 0.3048),
                ("decimetres", 10.0))
FAILURES = ("asset_unreadable", "expectation_invalid", "up_axis_mismatch", "unit_scale_mismatch",
            "dimensions_mismatch", "winding_inverted", "conversion_unsupported")
#: The failure convert_document raises for quantized data; convert reports any other glTF error as asset_unreadable.
CONVERSION_UNSUPPORTED = "conversion_unsupported"
#: How convert_document moves an accessor's values, by the usage _usage finds for it (KEEP when it finds none).
POINT, VECTOR, TANGENT, ROTATION, SCALE, MATRIX, KEEP = (
    "point", "vector", "tangent", "rotation", "scale", "matrix", "keep")
FLOAT = 5126


def axis(name: str) -> list:
    vector = [0.0, 0.0, 0.0]
    vector["XYZ".index(name[1])] = 1.0 if name[0] == "+" else -1.0
    return vector


def cross(a, b) -> list:
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def frame(convention: str) -> list:
    """3x3 matrix (rows) whose columns are the convention's right, up and forward directions."""
    up_name, forward_name, handedness, _winding = CONVENTIONS[convention]
    up, forward = axis(up_name), axis(forward_name)
    right = cross(forward, up) if handedness == "right" else cross(up, forward)
    return [[right[row], up[row], forward[row]] for row in range(3)]


def conversion(source: str, target: str = "gltf", unit_m: float = 1.0, target_unit_m: float = 1.0) -> tuple:
    """(Q, k, flip): the signed axis permutation Q = F_target F_source^T, the unit factor k, and whether triangle
    order must be reversed to keep front faces in front."""
    source_frame, target_frame = frame(source), frame(target)
    q = [[sum(target_frame[row][k] * source_frame[column][k] for k in range(3)) for column in range(3)]
         for row in range(3)]
    flip = (determinant(q) < 0) != (CONVENTIONS[source][3] != CONVENTIONS[target][3])
    return q, unit_m / target_unit_m, flip


def determinant(q: list) -> float:
    return gltfio.determinant3([row + [0.0] for row in q])


def _apply(q: list, vector, scale: float = 1.0) -> tuple:
    return tuple(scale * sum(q[row][k] * vector[k] for k in range(3)) for row in range(3))


def _quaternion(q: list, value) -> tuple:
    """The rotation Q R Q^T as a quaternion: the axis is a pseudovector, so it gains det(Q)."""
    sign = 1.0 if determinant(q) > 0 else -1.0
    vector = _apply(q, value[:3], sign)
    return (*vector, value[3])


def _matrix(q: list, k: float, values) -> tuple:
    """Conjugate a column-major 4x4 by M = k Q: M A M^-1."""
    a = [[values[column * 4 + row] for column in range(4)] for row in range(4)]
    m = [[k * q[row][column] for column in range(3)] + [0.0] for row in range(3)] + [[0.0, 0.0, 0.0, 1.0]]
    m_inverse = [[q[column][row] / k for column in range(3)] + [0.0] for row in range(3)] + [[0.0, 0.0, 0.0, 1.0]]
    result = gltfio.multiply(gltfio.multiply(m, a), m_inverse)
    return tuple(result[row][column] for column in range(4) for row in range(4))


def _usage(document: dict) -> dict:
    """Accessor index -> how it transforms: point, vector, tangent, rotation, scale, matrix or keep."""
    usage = {}
    for mesh in document.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            for name, index in primitive.get("attributes", {}).items():
                usage[index] = {"POSITION": POINT, "NORMAL": VECTOR, "TANGENT": TANGENT}.get(name, KEEP)
            for target in primitive.get("targets", []):
                for name, index in target.items():
                    usage[index] = {"POSITION": POINT, "NORMAL": VECTOR, "TANGENT": VECTOR}.get(name, KEEP)
    for skin in document.get("skins", []):
        if "inverseBindMatrices" in skin:
            usage[skin["inverseBindMatrices"]] = MATRIX
    for animation in document.get("animations", []):
        for channel in animation.get("channels", []):
            sampler = animation["samplers"][channel["sampler"]]
            path = channel.get("target", {}).get("path")
            usage[sampler["output"]] = {"translation": POINT, "rotation": ROTATION, "scale": SCALE}.get(path, KEEP)
    return usage


def convert_document(asset: gltfio.Asset, q: list, k: float, flip: bool) -> dict:
    """A new document (one embedded buffer) with every coordinate moved by M = k Q, triangle order reversed when
    ``flip`` is true."""
    source = asset.document
    document = copy.deepcopy(source)
    usage = _usage(source)
    mirrored = determinant(q) < 0
    permutation = [[abs(value) for value in row] for row in q]
    document["bufferViews"], document["accessors"] = [], []
    builder = gltfio.BufferBuilder(document)
    for index, accessor in enumerate(asset.items("accessors")):
        kind = usage.get(index, KEEP)
        values = gltfio.accessor_values(asset, index, normalized=False)
        if kind != KEEP and accessor["componentType"] != FLOAT:
            raise gltfio.GltfError(CONVERSION_UNSUPPORTED, f"accessor {index} holds quantized {kind} data")
        if kind == POINT:
            values = [_apply(q, value, k) for value in values]
        elif kind == VECTOR:
            values = [_apply(q, value) for value in values]
        elif kind == TANGENT:
            values = [(*_apply(q, value[:3]), -value[3] if mirrored else value[3]) for value in values]
        elif kind == ROTATION:
            values = [_quaternion(q, value) for value in values]
        elif kind == SCALE:
            values = [_apply(permutation, value) for value in values]
        elif kind == MATRIX:
            values = [_matrix(q, k, value) for value in values]
        new = builder.add(values, accessor["componentType"], accessor["type"], bounds="min" in accessor
                          or kind == POINT and accessor["type"] == "VEC3",
                          normalized=bool(accessor.get("normalized")))
        for key in ("name", "extras"):
            if key in accessor:
                document["accessors"][new][key] = accessor[key]
    for image in document.get("images", []):
        if "bufferView" in image:
            data = gltfio.view_bytes(asset, image["bufferView"])
            while len(builder.data) % 4:
                builder.data.append(0)
            document["bufferViews"].append({"buffer": 0, "byteOffset": len(builder.data), "byteLength": len(data)})
            builder.data += data
            image["bufferView"] = len(document["bufferViews"]) - 1
    if flip:
        _flip_winding(asset, document, builder)
    for node in document.get("nodes", []):
        if "matrix" in node:
            node["matrix"] = list(_matrix(q, k, node["matrix"]))
            continue
        if "translation" in node:
            node["translation"] = list(_apply(q, node["translation"], k))
        if "rotation" in node:
            node["rotation"] = list(_quaternion(q, node["rotation"]))
        if "scale" in node:
            node["scale"] = list(_apply(permutation, node["scale"]))
    document["asset"] = dict(document.get("asset", {}), generator=f"{TOOL} (from {asset.document.get('asset', {}).get('generator', 'unknown')})")
    return builder.finish()


def _flip_winding(asset: gltfio.Asset, document: dict, builder: gltfio.BufferBuilder) -> None:
    """Reverse every triangle (strips and fans become lists) so front faces stay front faces."""
    for mesh_index, mesh in enumerate(asset.items("meshes")):
        for primitive_index, primitive in enumerate(mesh.get("primitives", [])):
            if primitive.get("mode", 4) not in (4, 5, 6):
                continue
            triangles = gltfio.triangles(asset, primitive)
            flipped = [(index,) for a, b, c in triangles for index in (a, c, b)]
            target = document["meshes"][mesh_index]["primitives"][primitive_index]
            target["indices"] = builder.add(flipped, 5125, "SCALAR", 34963)
            target["mode"] = 4


def winding_agreement(asset: gltfio.Asset) -> "float | None":
    """Share of triangles whose winding normal points the same way as their stored vertex normals."""
    agree = total = 0
    for mesh in asset.items("meshes"):
        for primitive in mesh.get("primitives", []):
            attributes = primitive.get("attributes", {})
            if "NORMAL" not in attributes or primitive.get("mode", 4) not in (4, 5, 6):
                continue
            positions = gltfio.accessor_values(asset, attributes["POSITION"])
            normals = gltfio.accessor_values(asset, attributes["NORMAL"])
            for a, b, c in gltfio.triangles(asset, primitive):
                edge1 = [positions[b][i] - positions[a][i] for i in range(3)]
                edge2 = [positions[c][i] - positions[a][i] for i in range(3)]
                face = cross(edge1, edge2)
                stored = [normals[a][i] + normals[b][i] + normals[c][i] for i in range(3)]
                dot = sum(face[i] * stored[i] for i in range(3))
                if dot != 0:
                    total += 1
                    agree += dot > 0
    return agree / total if total else None


def diagnose(dimensions: list, expected: list, tolerance: float, report: asset_report.Report) -> None:
    if all(abs(a - b) <= tolerance for a, b in zip(dimensions, expected)):
        return
    swapped = [dimensions[0], dimensions[2], dimensions[1]]
    if all(abs(a - b) <= tolerance for a, b in zip(swapped, expected)):
        report.fail("up_axis_mismatch", "scene", f"measured {[round(v, 4) for v in dimensions]} m; Y and Z are "
                                                 "swapped: Z-up data in a Y-up file (convert --from z_up_right)")
        return
    ratios = [found / wanted for found, wanted in zip(dimensions, expected) if wanted > 1e-9]
    if ratios and min(ratios) > 0 and max(ratios) / min(ratios) < 1.02:
        ratio = sum(ratios) / len(ratios)
        for name, factor in UNIT_FACTORS:
            for value, label in ((factor, f"{name}"), (1 / factor, f"metres read as {name}")):
                if abs(ratio / value - 1) < 0.02:
                    report.fail("unit_scale_mismatch", "scene", f"measured {[round(v, 4) for v in dimensions]} m, "
                                                                f"{ratio:g} times the expectation: {label} "
                                                                f"(convert --unit-m {1 / value:g})")
                    return
    report.fail("dimensions_mismatch", "scene", f"measured {[round(v, 4) for v in dimensions]} m, expected "
                                                f"{expected} m")


def check(path, expected: "list | None" = None, tolerance: float = 0.005) -> asset_report.Report:
    report = asset_report.Report(TOOL, Path(path).name)
    try:
        asset = gltfio.load(path)
        bounds = gltfio.scene_bounds(asset)
        agreement = winding_agreement(asset)
    except gltfio.GltfError as error:
        report.fail("asset_unreadable", Path(path).name, f"{error.reason} {error.detail}")
        return report
    dimensions = [bounds[1][axis] - bounds[0][axis] for axis in range(3)] if bounds else None
    tallest = "XYZ"[dimensions.index(max(dimensions))] if dimensions else None
    report.facts = {"dimensions_m": dimensions, "bounds_m": {"min": list(bounds[0]), "max": list(bounds[1])}
                    if bounds else None, "tallest_axis": tallest, "winding_agreement": agreement}
    if expected is not None:
        if len(expected) != 3 or dimensions is None or any(value < 0 for value in expected):
            report.fail("expectation_invalid", "expect-dimensions", "three non-negative lengths, and a mesh to measure")
        else:
            diagnose(dimensions, expected, tolerance, report)
    if agreement is not None and agreement < 0.5:
        report.fail("winding_inverted", "meshes", f"only {agreement:.0%} of triangles wind with their normals: "
                                                  "mirrored data (convert --from y_up_left_cw) or flipped faces")
    return report


def convert(source_path, target_path, source: str, target: str = "gltf", unit_m: float = 1.0,
            expected: "list | None" = None, tolerance: float = 0.005) -> asset_report.Report:
    report = asset_report.Report(TOOL, Path(source_path).name)
    q, k, flip = conversion(source, target, unit_m)
    try:
        document = convert_document(gltfio.load(source_path), q, k, flip)
    except gltfio.GltfError as error:
        report.fail(CONVERSION_UNSUPPORTED if error.reason == CONVERSION_UNSUPPORTED else "asset_unreadable",
                    Path(source_path).name, f"{error.reason} {error.detail}")
        return report
    Path(target_path).write_text(gltfio.dumps(document), encoding="utf-8")
    result = check(target_path, expected, tolerance)
    result.subject = Path(target_path).name
    result.facts.update({"converted_from": Path(source_path).name, "matrix": q, "unit_factor": k,
                         "mirrored": determinant(q) < 0, "winding_reversed": flip})
    return result


def run(argv: list) -> dict:
    parser = argparse.ArgumentParser(prog=TOOL, description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    checking = commands.add_parser("check", help="measure and diagnose one file")
    checking.add_argument("asset")
    converting = commands.add_parser("convert", help="rewrite a file into another convention and unit")
    converting.add_argument("asset")
    converting.add_argument("output")
    converting.add_argument("--from", dest="source", choices=sorted(CONVENTIONS), default="gltf")
    converting.add_argument("--to", dest="target", choices=sorted(CONVENTIONS), default="gltf")
    converting.add_argument("--unit-m", type=float, default=1.0, help="metres per unit of the source data")
    for command in (checking, converting):
        command.add_argument("--expect-dimensions", type=float, nargs=3, metavar=("X", "Y", "Z"))
        command.add_argument("--tolerance", type=float, default=0.005)
    arguments = parser.parse_args(argv)
    if arguments.command == "check":
        return check(arguments.asset, arguments.expect_dimensions, arguments.tolerance).as_dict()
    return convert(arguments.asset, arguments.output, arguments.source, arguments.target, arguments.unit_m,
                   arguments.expect_dimensions, arguments.tolerance).as_dict()


def main(argv=None) -> int:
    return asset_report.emit(run(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    sys.exit(main())
