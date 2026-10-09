"""Deterministic builders for the family's glTF fixtures (not packaged; packages carry the files they write).

Every fixture is generated here from geometry written in code, so a reader can see what each known-good file
holds and which single defect each known-wrong copy adds. Running a builder twice writes the same bytes.
"""
from __future__ import annotations

import base64
import copy
import json
import math
import struct
import sys
from pathlib import Path

FAMILY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FAMILY / "shared"))

import gltfio  # noqa: E402

FLOAT, UBYTE, USHORT, UINT = 5126, 5121, 5123, 5125
ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER = 34962, 34963


def f32(value: float) -> float:
    """``value`` rounded to the nearest 32-bit float, so declared min and max equal the stored data."""
    return struct.unpack("<f", struct.pack("<f", value))[0]


def quat_axis_angle(axis, degrees: float) -> list:
    length = math.sqrt(sum(component * component for component in axis))
    half = math.radians(degrees) / 2.0
    scale = math.sin(half) / length
    return [f32(axis[0] * scale), f32(axis[1] * scale), f32(axis[2] * scale), f32(math.cos(half))]


def box_geometry(low, high) -> dict:
    """24 vertices (4 per face, outward normals, 0 to 1 UVs) and 36 counter-clockwise indices."""
    positions, normals, uvs, indices = [], [], [], []
    for axis, u, v in ((0, 1, 2), (1, 2, 0), (2, 0, 1)):
        for sign in (1, -1):
            corners = []
            for cu, cv in ((0, 0), (1, 0), (1, 1), (0, 1)):
                point = [0.0, 0.0, 0.0]
                point[axis] = high[axis] if sign > 0 else low[axis]
                point[u] = (low[u], high[u])[cu]
                point[v] = (low[v], high[v])[cv]
                corners.append((tuple(f32(value) for value in point), (float(cu), float(1 - cv))))
            if sign < 0:
                corners = [corners[0], corners[3], corners[2], corners[1]]
            base = len(positions)
            normal = [0.0, 0.0, 0.0]
            normal[axis] = float(sign)
            for point, uv in corners:
                positions.append(point)
                normals.append(tuple(normal))
                uvs.append(uv)
            indices += [base, base + 1, base + 2, base, base + 2, base + 3]
    return {"positions": positions, "normals": normals, "uvs": uvs, "indices": indices}


def merge(*parts) -> dict:
    merged = {"positions": [], "normals": [], "uvs": [], "indices": []}
    for part in parts:
        offset = len(merged["positions"])
        for key in ("positions", "normals", "uvs"):
            merged[key] += part[key]
        merged["indices"] += [index + offset for index in part["indices"]]
    return merged


def add_primitive(builder: gltfio.BufferBuilder, geometry: dict, material: "int | None" = None,
                  index_type: int = USHORT) -> dict:
    primitive = {"attributes": {
        "POSITION": builder.add(geometry["positions"], FLOAT, "VEC3", ARRAY_BUFFER, bounds=True),
        "NORMAL": builder.add(geometry["normals"], FLOAT, "VEC3", ARRAY_BUFFER),
        "TEXCOORD_0": builder.add(geometry["uvs"], FLOAT, "VEC2", ARRAY_BUFFER)},
        "indices": builder.add([(index,) for index in geometry["indices"]], index_type, "SCALAR",
                               ELEMENT_ARRAY_BUFFER)}
    if material is not None:
        primitive["material"] = material
    return primitive


def add_clip(builder: gltfio.BufferBuilder, document: dict, name: str, channels: list) -> None:
    """channels: (node, path, times, values, interpolation); values are tuples (3 per key for CUBICSPLINE)."""
    animation = {"name": name, "channels": [], "samplers": []}
    for node, path, times, values, interpolation in channels:
        width = {"translation": "VEC3", "rotation": "VEC4", "scale": "VEC3", "weights": "SCALAR"}[path]
        source = builder.add([(f32(time),) for time in times], FLOAT, "SCALAR", bounds=True)
        output = builder.add([tuple(f32(component) for component in value) for value in values], FLOAT, width)
        animation["samplers"].append({"input": source, "output": output, "interpolation": interpolation})
        animation["channels"].append({"sampler": len(animation["samplers"]) - 1, "target": {"node": node, "path": path}})
    document.setdefault("animations", []).append(animation)


def material(name: str, colour, metallic: float, roughness: float, texture: "int | None" = None) -> dict:
    pbr = {"baseColorFactor": [f32(value) for value in colour], "metallicFactor": metallic,
           "roughnessFactor": roughness}
    if texture is not None:
        pbr["baseColorTexture"] = {"index": texture}
    return {"name": name, "pbrMetallicRoughness": pbr}


def identity_axes(point):
    return tuple(point)


def z_up_axes(point):
    """A Z-up tool's coordinates written without conversion: glTF (x, y, z) lands at (x, -z, y)."""
    return (point[0], -point[2], point[1])


def door(unit: float = 1.0, axes=identity_axes, clips=("Open", "Close", "HandlePress"), generator: str =
         "asset_contracts fixture builder") -> dict:
    """A door in a frame: DoorFrame (root) > DoorPanel (hinged at its left edge) > DoorHandle, in metres.

    ``unit`` multiplies every length (100 writes centimetres); ``axes`` remaps every point and axis. ``clips`` holds
    names from door_clips() or (name, channels) pairs."""
    def p(x, y, z):
        return tuple(f32(value * unit) for value in axes((x, y, z)))

    def geometry(*boxes):
        parts = []
        for low, high in boxes:
            a, b = p(*low), p(*high)
            parts.append(box_geometry(tuple(min(a[i], b[i]) for i in range(3)), tuple(max(a[i], b[i]) for i in range(3))))
        return merge(*parts)

    document = {"asset": {"version": "2.0", "generator": generator}, "scene": 0,
                "scenes": [{"name": "DoorScene", "nodes": [0]}],
                "materials": [material("PaintedFrame", (0.85, 0.85, 0.8, 1.0), 0.0, 0.6),
                              material("Wood", (0.55, 0.35, 0.2, 1.0), 0.0, 0.8),
                              material("BrushedSteel", (0.7, 0.7, 0.72, 1.0), 1.0, 0.35)]}
    builder = gltfio.BufferBuilder(document)
    frame = geometry(((-0.55, 0.0, -0.075), (-0.45, 2.1, 0.075)), ((0.45, 0.0, -0.075), (0.55, 2.1, 0.075)),
                     ((-0.45, 2.0, -0.075), (0.45, 2.1, 0.075)))
    panel = geometry(((0.0, 0.0, -0.02), (0.9, 2.0, 0.02)))
    handle = geometry(((-0.06, -0.015, 0.0), (0.06, 0.015, 0.04)))
    document["meshes"] = [{"name": "FrameMesh", "primitives": [add_primitive(builder, frame, 0)]},
                          {"name": "PanelMesh", "primitives": [add_primitive(builder, panel, 1)]},
                          {"name": "HandleMesh", "primitives": [add_primitive(builder, handle, 2)]}]
    document["nodes"] = [{"name": "DoorFrame", "mesh": 0, "children": [1]},
                         {"name": "DoorPanel", "mesh": 1, "children": [2], "translation": list(p(-0.45, 0.0, 0.0))},
                         {"name": "DoorHandle", "mesh": 2, "translation": list(p(0.78, 1.0, 0.02))}]
    library = door_clips(axes)
    for clip in clips:
        if isinstance(clip, str):
            add_clip(builder, document, clip, library[clip])
        else:
            add_clip(builder, document, clip[0], clip[1])
    return builder.finish()


def door_clips(axes=identity_axes) -> dict:
    """The door's standard clips as add_clip channel lists: Open and Close turn the panel (node 1) about the up
    axis by 90 degrees in 1.2 s; HandlePress turns the handle (node 2) about the depth axis by -30 and back."""
    up, depth = axes((0.0, 1.0, 0.0)), axes((0.0, 0.0, 1.0))
    return {
        "Open": [(1, "rotation", [0.0, 0.6, 1.2], [quat_axis_angle(up, 0), quat_axis_angle(up, 45),
                                                    quat_axis_angle(up, 90)], "LINEAR")],
        "Close": [(1, "rotation", [0.0, 0.6, 1.2], [quat_axis_angle(up, 90), quat_axis_angle(up, 45),
                                                     quat_axis_angle(up, 0)], "LINEAR")],
        "HandlePress": [(2, "rotation", [0.0, 0.2, 0.4], [quat_axis_angle(depth, 0), quat_axis_angle(depth, -30),
                                                           quat_axis_angle(depth, 0)], "LINEAR")]}


def tiny_png(width: int = 4, height: int = 4) -> bytes:
    """A small RGBA checker image, written with zlib and struct only."""
    import zlib
    rows = b""
    for y in range(height):
        rows += b"\x00" + b"".join(bytes((200, 60, 40, 255)) if (x + y) % 2 else bytes((240, 220, 180, 255))
                                   for x in range(width))

    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))


def skinned_strip() -> dict:
    """A two-bone bending strip with a skin, a sparse morph target tab, a textured material, and three clips
    using LINEAR, STEP and CUBICSPLINE samplers."""
    document = {"asset": {"version": "2.0", "generator": "asset_contracts fixture builder"}, "scene": 0,
                "scenes": [{"name": "StripScene", "nodes": [0, 3]}],
                "samplers": [{"magFilter": 9728, "minFilter": 9728, "wrapS": 33071, "wrapT": 33071}],
                "images": [{"name": "Checker", "uri": "data:image/png;base64," + base64.b64encode(tiny_png()).decode()}],
                "textures": [{"sampler": 0, "source": 0}],
                "materials": [material("StripRubber", (1.0, 1.0, 1.0, 1.0), 0.0, 0.9, texture=0),
                              material("TabPlastic", (0.2, 0.4, 0.9, 1.0), 0.0, 0.5)]}
    builder = gltfio.BufferBuilder(document)
    positions, normals, uvs, joints, weights = [], [], [], [], []
    for row in range(3):
        for column in range(2):
            positions.append((f32(column * 0.1 - 0.05), f32(row * 0.5), 0.0))
            normals.append((0.0, 0.0, 1.0))
            uvs.append((float(column), f32(row / 2.0)))
            joints.append((0, 1, 0, 0))
            weights.append((1.0, 0.0, 0.0, 0.0) if row == 0 else (0.5, 0.5, 0.0, 0.0) if row == 1 else (0.0, 1.0, 0.0, 0.0))
    indices = [0, 1, 3, 0, 3, 2, 2, 3, 5, 2, 5, 4]
    strip = {"attributes": {"POSITION": builder.add(positions, FLOAT, "VEC3", ARRAY_BUFFER, bounds=True),
                            "NORMAL": builder.add(normals, FLOAT, "VEC3", ARRAY_BUFFER),
                            "TEXCOORD_0": builder.add(uvs, FLOAT, "VEC2", ARRAY_BUFFER),
                            "JOINTS_0": builder.add(joints, UBYTE, "VEC4", ARRAY_BUFFER),
                            "WEIGHTS_0": builder.add(weights, FLOAT, "VEC4", ARRAY_BUFFER)},
             "indices": builder.add([(index,) for index in indices], USHORT, "SCALAR", ELEMENT_ARRAY_BUFFER),
             "material": 0}
    tab = box_geometry((-0.05, 0.0, -0.01), (0.05, 0.05, 0.01))
    tab_primitive = add_primitive(builder, tab, 1)
    # Sparse morph target: only the four top vertices of the +Y face move up by 3 cm.
    moved = sorted(index for index, point in enumerate(tab["positions"]) if point[1] > 0.04)[:4]
    sparse_indices = builder.add([(index,) for index in moved], USHORT, "SCALAR")
    sparse_values = builder.add([(0.0, f32(0.03), 0.0)] * len(moved), FLOAT, "VEC3")
    document["accessors"].append({
        "componentType": FLOAT, "count": len(tab["positions"]), "type": "VEC3", "min": [0.0, 0.0, 0.0],
        "max": [0.0, f32(0.03), 0.0], "sparse": {
            "count": len(moved),
            "indices": {"bufferView": document["accessors"][sparse_indices]["bufferView"], "componentType": USHORT},
            "values": {"bufferView": document["accessors"][sparse_values]["bufferView"]}}})
    tab_primitive["targets"] = [{"POSITION": len(document["accessors"]) - 1}]
    inverse_binds = [(1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0),
                     (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, -0.5, 0.0, 1.0)]
    document["skins"] = [{"name": "StripSkin", "joints": [1, 2], "skeleton": 1,
                          "inverseBindMatrices": builder.add(inverse_binds, FLOAT, "MAT4")}]
    document["meshes"] = [{"name": "StripMesh", "primitives": [strip]},
                          {"name": "TabMesh", "primitives": [tab_primitive], "weights": [0.0],
                           "extras": {"targetNames": ["Raise"]}}]
    document["nodes"] = [{"name": "StripRig", "children": [1, 4]},
                         {"name": "StripBone0", "children": [2]},
                         {"name": "StripBone1", "translation": [0.0, 0.5, 0.0]},
                         {"name": "Tab", "mesh": 1, "translation": [0.3, 0.0, 0.0]},
                         {"name": "Strip", "mesh": 0, "skin": 0}]
    bend = [quat_axis_angle((0, 0, 1), 0), quat_axis_angle((0, 0, 1), 30), quat_axis_angle((0, 0, 1), 0)]
    cubic = []
    for rotation in bend:
        cubic += [(0.0, 0.0, 0.0, 0.0), tuple(rotation), (0.0, 0.0, 0.0, 0.0)]
    add_clip(builder, document, "Bend", [(2, "rotation", [0.0, 0.5, 1.0], cubic, "CUBICSPLINE")])
    add_clip(builder, document, "Raise", [(3, "weights", [0.0, 0.25, 0.5], [(0.0,), (1.0,), (0.0,)], "STEP")])
    add_clip(builder, document, "Slide", [(3, "translation", [0.0, 1.0], [(0.3, 0.0, 0.0), (0.3, 0.0, 0.2)],
                                           "LINEAR")])
    return builder.finish()


def buffer_bytes(document: dict) -> bytearray:
    return bytearray(gltfio.decode_data_uri(document["buffers"][0]["uri"]))


def set_buffer(document: dict, data: bytes) -> None:
    document["buffers"][0]["uri"] = "data:application/octet-stream;base64," + base64.b64encode(bytes(data)).decode()


def patch_scalar(document: dict, accessor: int, element: int, value) -> dict:
    """A copy of ``document`` whose scalar accessor element ``element`` holds ``value`` in the buffer."""
    document = copy.deepcopy(document)
    data = buffer_bytes(document)
    row = document["accessors"][accessor]
    view = document["bufferViews"][row["bufferView"]]
    letter, size, _name = gltfio.COMPONENT_TYPES[row["componentType"]]
    struct.pack_into("<" + letter, data, view.get("byteOffset", 0) + row.get("byteOffset", 0) + element * size, value)
    set_buffer(document, data)
    return document


def write(path: Path, document: dict) -> None:
    """Write a .gltf fixture; asset.generator names the item that owns it, so items never share fixture bytes."""
    document = copy.deepcopy(document)
    owner = path.parent.parent.name if path.parent.name == "fixtures" else path.parent.parent.parent.name
    if isinstance(document.get("asset"), dict) and "generator" in document["asset"]:
        document["asset"]["generator"] = f"asset_contracts fixture builder for {owner}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(gltfio.dumps(document), encoding="utf-8")


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def accessor_of(document: dict, mesh: int, attribute: str, primitive: int = 0) -> int:
    row = document["meshes"][mesh]["primitives"][primitive]
    return row["indices"] if attribute == "indices" else row["attributes"][attribute]


def matrix_quaternion(matrix) -> list:
    """The unit quaternion (x, y, z, w) of the rotation in the upper 3x3 of ``matrix`` (scale divided out)."""
    columns = [[matrix[row][column] for row in range(3)] for column in range(3)]
    scales = [math.sqrt(sum(value * value for value in column)) for column in columns]
    m = [[matrix[row][column] / scales[column] for column in range(3)] for row in range(3)]
    trace = m[0][0] + m[1][1] + m[2][2]
    if trace > 0:
        s = math.sqrt(trace + 1.0) * 2
        q = [(m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s, 0.25 * s]
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        q = [0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s, (m[2][1] - m[1][2]) / s]
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        q = [(m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s, (m[0][2] - m[2][0]) / s]
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
        q = [(m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s, (m[1][0] - m[0][1]) / s]
    return [f32(value) for value in q]


def set_trs(node: dict, matrix) -> None:
    """Write ``matrix`` (rotation and translation, unit scale) into a node as translation and rotation."""
    node.pop("matrix", None)
    node.pop("scale", None)
    node["translation"] = [f32(matrix[row][3]) for row in range(3)]
    node["rotation"] = matrix_quaternion(matrix)
    if node["rotation"] == [0.0, 0.0, 0.0, 1.0]:
        del node["rotation"]


def rigid_inverse(matrix) -> list:
    rotation = [[matrix[column][row] for column in range(3)] for row in range(3)]
    translation = [-sum(rotation[row][k] * matrix[k][3] for k in range(3)) for row in range(3)]
    return [rotation[row] + [translation[row]] for row in range(3)] + [[0.0, 0.0, 0.0, 1.0]]


def rewrite_vec3(document: dict, accessor: int, function) -> None:
    """Rewrite a tightly packed float VEC3 accessor in the embedded buffer, updating min and max."""
    data = buffer_bytes(document)
    row = document["accessors"][accessor]
    view = document["bufferViews"][row["bufferView"]]
    start, stride = view.get("byteOffset", 0) + row.get("byteOffset", 0), view.get("byteStride") or 12
    values = []
    for element in range(row["count"]):
        value = tuple(f32(item) for item in function(struct.unpack_from("<3f", data, start + element * stride)))
        struct.pack_into("<3f", data, start + element * stride, *value)
        values.append(value)
    if "min" in row:
        row["min"] = [min(value[axis] for value in values) for axis in range(3)]
        row["max"] = [max(value[axis] for value in values) for axis in range(3)]
    set_buffer(document, data)


def rebase_node(document: dict, index: int, matrix) -> dict:
    """A copy where node ``index`` has its own frame moved by the rigid ``matrix`` (in its local space) while its
    mesh and children stay where they were in the world: what origin-to-geometry or apply-rotation does."""
    document = copy.deepcopy(document)
    node = document["nodes"][index]
    inverse = rigid_inverse(matrix)
    set_trs(node, gltfio.multiply(gltfio.node_local_matrix(node), matrix))
    if isinstance(node.get("mesh"), int):
        for primitive in document["meshes"][node["mesh"]]["primitives"]:
            rewrite_vec3(document, primitive["attributes"]["POSITION"],
                         lambda point: gltfio.transform_point(inverse, point))
            if "NORMAL" in primitive["attributes"]:
                rewrite_vec3(document, primitive["attributes"]["NORMAL"],
                             lambda vector: tuple(sum(inverse[row][k] * vector[k] for k in range(3)) for row in range(3)))
    for child in node.get("children", []):
        set_trs(document["nodes"][child], gltfio.multiply(inverse, gltfio.node_local_matrix(document["nodes"][child])))
    return document
