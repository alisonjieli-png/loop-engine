"""Read and write glTF 2.0 assets with the Python standard library alone.

A glTF asset is JSON that describes scenes, nodes, meshes, materials, skins and animations, plus binary
buffers that hold the numbers. This module reads the JSON (a .gltf file, or the JSON chunk of a .glb),
resolves every buffer (an embedded base64 data URI, a file next to the asset, or the binary chunk of a
.glb), decodes accessors into Python numbers, and computes node transforms, bounding boxes, triangle
counts and animation clip facts. It also writes a .gltf with its buffer embedded, for tools that convert
assets.

Reading never trusts the file. Every offset, stride and count is checked before a byte is read, and a
problem is raised as GltfError with a closed reason code. A buffer that cannot be resolved does not stop
the load: it is recorded in ``Asset.problems`` so a validator can report it.

Conventions are glTF's: right-handed, +Y up, the front of an asset faces +Z, lengths in metres, rotations
as unit quaternions (x, y, z, w). A matrix here is a list of four rows; glTF stores matrices column-major
and ``node_local_matrix`` converts.
"""
from __future__ import annotations

import base64
import json
import math
import struct
from pathlib import Path
from urllib.parse import unquote

#: componentType code: (struct letter, bytes, name).
COMPONENT_TYPES = {5120: ("b", 1, "BYTE"), 5121: ("B", 1, "UNSIGNED_BYTE"), 5122: ("h", 2, "SHORT"),
                   5123: ("H", 2, "UNSIGNED_SHORT"), 5125: ("I", 4, "UNSIGNED_INT"), 5126: ("f", 4, "FLOAT")}
TYPE_COMPONENTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}
#: The matrix types whose columns glTF may pad: every matrix column starts on a four-byte boundary.
PADDED_MATRIX_TYPES = (MAT2, MAT3) = ("MAT2", "MAT3")
#: Divisors that map normalized integers to [0, 1] or [-1, 1].
NORMALIZED_DIVISORS = {5120: 127.0, 5121: 255.0, 5122: 32767.0, 5123: 65535.0, 5125: 4294967295.0}
GLB_MAGIC, GLB_JSON, GLB_BIN = b"glTF", 0x4E4F534A, 0x004E4942
#: Largest asset file and largest accessor this reader decodes; larger inputs are refused, not truncated.
MAXIMUM_FILE_BYTES = 512 * 1024 * 1024
MAXIMUM_ELEMENTS = 32 * 1024 * 1024
IDENTITY = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
PRIMITIVE_MODES = {0: "POINTS", 1: "LINES", 2: "LINE_LOOP", 3: "LINE_STRIP", 4: "TRIANGLES", 5: "TRIANGLE_STRIP",
                   6: "TRIANGLE_FAN"}


class GltfError(ValueError):
    """A glTF input that cannot be read. ``reason`` is a closed code; the message adds detail."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason, self.detail = reason, detail


class Asset:
    """One loaded asset: the JSON document, one bytes object (or None) per buffer, and load problems."""

    def __init__(self, document: dict, buffers: list, path: "Path | None" = None, problems: "list | None" = None,
                 container: str = "gltf") -> None:
        self.document, self.buffers, self.path = document, buffers, path
        self.problems = problems if problems is not None else []
        self.container = container

    def items(self, key: str) -> list:
        """The top-level array ``key`` (nodes, meshes, ...), or an empty list."""
        value = self.document.get(key, [])
        return value if isinstance(value, list) else []


def strict_json(text: str) -> object:
    """JSON that refuses repeated keys and non-finite numbers, the way the glTF schema reads it."""
    def pairs(entries):
        keys = [key for key, _value in entries]
        if len(keys) != len(set(keys)):
            raise GltfError("json_duplicate_key", ", ".join(sorted({key for key in keys if keys.count(key) > 1}))[:120])
        return dict(entries)

    def constant(name):
        raise GltfError("json_non_finite_number", name)

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except json.JSONDecodeError as error:
        raise GltfError("json_invalid", f"line {error.lineno} column {error.colno}: {error.msg}") from None


def decode_data_uri(uri: str) -> bytes:
    """The bytes of a base64 data URI (data:<media type>;base64,<payload>)."""
    header, separator, payload = uri.partition(",")
    if not separator or not header.startswith("data:") or not header.endswith(";base64"):
        raise GltfError("data_uri_invalid", header[:60])
    try:
        return base64.b64decode(payload, validate=True)
    except ValueError:
        raise GltfError("data_uri_invalid", "the base64 payload does not decode") from None


def resolve_uri(base: "Path | None", uri: str) -> Path:
    """The file a relative URI names, confined to the asset's folder. Absolute paths and schemes are refused."""
    if not isinstance(uri, str) or not uri:
        raise GltfError("uri_invalid", repr(uri)[:60])
    if base is None:
        raise GltfError("uri_without_base", uri[:60])
    if ":" in uri.split("/", 1)[0] or uri.startswith(("/", "\\")):
        raise GltfError("uri_not_relative", uri[:60])
    decoded = unquote(uri)
    if "\\" in decoded:
        raise GltfError("uri_backslash", uri[:60])
    parts = decoded.split("/")
    if any(part == ".." for part in parts):
        raise GltfError("uri_escapes_folder", uri[:60])
    return Path(base) / Path(*[part for part in parts if part not in ("", ".")])


def _read_glb(data: bytes) -> tuple:
    if len(data) < 20:
        raise GltfError("glb_truncated", f"{len(data)} bytes")
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    if magic != GLB_MAGIC or version != 2:
        raise GltfError("glb_header_invalid", f"magic {magic!r}, version {version}")
    if length != len(data):
        raise GltfError("glb_length_mismatch", f"header says {length}, file has {len(data)}")
    position, chunks = 12, []
    while position < length:
        if position + 8 > length:
            raise GltfError("glb_truncated", f"chunk header at {position}")
        size, kind = struct.unpack_from("<II", data, position)
        if position + 8 + size > length or size % 4:
            raise GltfError("glb_chunk_invalid", f"chunk at {position} of {size} bytes")
        chunks.append((kind, data[position + 8:position + 8 + size]))
        position += 8 + size
    if not chunks or chunks[0][0] != GLB_JSON:
        raise GltfError("glb_json_chunk_missing")
    binary = chunks[1][1] if len(chunks) > 1 and chunks[1][0] == GLB_BIN else None
    try:
        text = chunks[0][1].decode("utf-8")
    except UnicodeDecodeError:
        raise GltfError("json_not_utf8") from None
    return text, binary


def loads(data: "bytes | str", base: "Path | None" = None, path: "Path | None" = None) -> Asset:
    """An Asset from .gltf text or .glb bytes. ``base`` is the folder relative URIs resolve against."""
    container, binary = "gltf", None
    if isinstance(data, (bytes, bytearray)):
        if bytes(data[:4]) == GLB_MAGIC:
            text, binary = _read_glb(bytes(data))
            container = "glb"
        else:
            try:
                text = bytes(data).decode("utf-8-sig")
            except UnicodeDecodeError:
                raise GltfError("json_not_utf8") from None
    else:
        text = data
    document = strict_json(text)
    if not isinstance(document, dict):
        raise GltfError("json_not_object")
    buffers, problems = [], []
    declared = document.get("buffers", [])
    for index, buffer in enumerate(declared if isinstance(declared, list) else []):
        payload = None
        try:
            if not isinstance(buffer, dict):
                raise GltfError("buffer_invalid", "not an object")
            uri = buffer.get("uri")
            if uri is None:
                if container == "glb" and index == 0 and binary is not None:
                    payload = binary
                else:
                    raise GltfError("buffer_uri_missing", f"buffer {index} has no uri and no GLB binary chunk")
            elif isinstance(uri, str) and uri.startswith("data:"):
                payload = decode_data_uri(uri)
            else:
                target = resolve_uri(base, uri)
                if not target.is_file():
                    raise GltfError("buffer_file_missing", str(uri)[:80])
                if target.stat().st_size > MAXIMUM_FILE_BYTES:
                    raise GltfError("buffer_too_large", str(uri)[:80])
                payload = target.read_bytes()
        except GltfError as error:
            problems.append({"buffer": index, "reason": error.reason, "detail": error.detail})
        buffers.append(payload)
    return Asset(document, buffers, path, problems, container)


def load(path) -> Asset:
    """Read a .gltf or .glb file and every buffer it names."""
    path = Path(path)
    try:
        size = path.stat().st_size
    except OSError as error:
        raise GltfError("file_unreadable", f"{path.name}: {type(error).__name__}") from None
    if size > MAXIMUM_FILE_BYTES:
        raise GltfError("file_too_large", f"{size} bytes")
    return loads(path.read_bytes(), base=path.parent, path=path)


def element_size(component_type: int, kind: str) -> int:
    """Bytes one accessor element occupies, including the column padding glTF requires for small matrices."""
    size = COMPONENT_TYPES[component_type][1]
    if kind == MAT2 and size == 1:
        return 8
    if kind == MAT3 and size == 1:
        return 12
    if kind == MAT3 and size == 2:
        return 24
    return TYPE_COMPONENTS[kind] * size


def _column_offsets(component_type: int, kind: str) -> list:
    """Byte offset of every component of one element, honouring matrix column padding."""
    size = COMPONENT_TYPES[component_type][1]
    count = TYPE_COMPONENTS[kind]
    if kind in PADDED_MATRIX_TYPES and element_size(component_type, kind) != count * size:
        rows = 2 if kind == MAT2 else 3
        column_bytes = element_size(component_type, kind) // rows
        return [column * column_bytes + row * size for column in range(rows) for row in range(rows)]
    return [index * size for index in range(count)]


def accessor_layout(asset: Asset, index: int) -> dict:
    """Where accessor ``index`` reads from: buffer, start byte, stride, element size and the bytes it spans.

    Raises GltfError when a reference or a type is invalid or when the span leaves its buffer view."""
    accessors = asset.items("accessors")
    if not isinstance(index, int) or not 0 <= index < len(accessors):
        raise GltfError("accessor_missing", str(index))
    accessor = accessors[index]
    component_type, kind, count = accessor.get("componentType"), accessor.get("type"), accessor.get("count")
    if component_type not in COMPONENT_TYPES or kind not in TYPE_COMPONENTS:
        raise GltfError("accessor_type_invalid", f"accessor {index}: {component_type} {kind}")
    if not isinstance(count, int) or count < 1 or count > MAXIMUM_ELEMENTS:
        raise GltfError("accessor_count_invalid", f"accessor {index}: {count}")
    size = element_size(component_type, kind)
    layout = {"accessor": index, "component_type": component_type, "type": kind, "count": count,
              "element_size": size, "components": TYPE_COMPONENTS[kind], "buffer": None, "start": 0,
              "stride": size, "span": 0, "view": accessor.get("bufferView")}
    if layout["view"] is None:
        return layout
    views = asset.items("bufferViews")
    view_index = layout["view"]
    if not isinstance(view_index, int) or not 0 <= view_index < len(views):
        raise GltfError("buffer_view_missing", f"accessor {index} names view {view_index}")
    view = views[view_index]
    stride = view.get("byteStride") or size
    offset = accessor.get("byteOffset", 0)
    view_offset, view_length = view.get("byteOffset", 0), view.get("byteLength")
    if not all(isinstance(value, int) and value >= 0 for value in (offset, view_offset, view_length, stride)):
        raise GltfError("buffer_view_invalid", f"view {view_index}")
    if stride < size:
        raise GltfError("byte_stride_too_small", f"view {view_index}: stride {stride} < element {size}")
    span = offset + stride * (count - 1) + size
    if span > view_length:
        raise GltfError("accessor_exceeds_view", f"accessor {index} needs {span} bytes, view {view_index} has "
                                                 f"{view_length}")
    layout.update({"buffer": view.get("buffer"), "start": view_offset + offset, "stride": stride, "span": span})
    return layout


def _buffer(asset: Asset, index) -> bytes:
    if not isinstance(index, int) or not 0 <= index < len(asset.buffers):
        raise GltfError("buffer_missing", str(index))
    data = asset.buffers[index]
    if data is None:
        raise GltfError("buffer_unresolved", str(index))
    return data


def view_bytes(asset: Asset, view_index: int) -> bytes:
    """The bytes of one buffer view, after checking it lies inside its buffer."""
    views = asset.items("bufferViews")
    if not isinstance(view_index, int) or not 0 <= view_index < len(views):
        raise GltfError("buffer_view_missing", str(view_index))
    view = views[view_index]
    data = _buffer(asset, view.get("buffer"))
    start, length = view.get("byteOffset", 0), view.get("byteLength")
    if not isinstance(start, int) or not isinstance(length, int) or start < 0 or length < 0 \
            or start + length > len(data):
        raise GltfError("buffer_view_exceeds_buffer", f"view {view_index}")
    return data[start:start + length]


def _read_elements(data: bytes, start: int, stride: int, count: int, component_type: int, kind: str) -> list:
    letter, size, _name = COMPONENT_TYPES[component_type]
    offsets = _column_offsets(component_type, kind)
    if start < 0 or start + stride * (count - 1) + element_size(component_type, kind) > len(data):
        raise GltfError("accessor_exceeds_buffer", f"{count} elements from byte {start}")
    if offsets == [index * size for index in range(len(offsets))] and stride == len(offsets) * size:
        flat = struct.unpack_from(f"<{count * len(offsets)}{letter}", data, start)
        width = len(offsets)
        return [tuple(flat[position:position + width]) for position in range(0, len(flat), width)]
    unpack = struct.Struct("<" + letter).unpack_from
    return [tuple(unpack(data, start + element * stride + offset)[0] for offset in offsets)
            for element in range(count)]


def accessor_values(asset: Asset, index: int, normalized: bool = True) -> list:
    """Every element of accessor ``index`` as a tuple, sparse substitution applied.

    Integer data marked ``normalized`` becomes floats in [0, 1] or [-1, 1] unless ``normalized`` is False."""
    layout = accessor_layout(asset, index)
    accessor = asset.items("accessors")[index]
    component_type, kind, count = layout["component_type"], layout["type"], layout["count"]
    if layout["view"] is None:
        values = [tuple(0 for _ in range(layout["components"])) for _ in range(count)]
    else:
        views = asset.items("bufferViews")
        view = views[layout["view"]]
        data = _buffer(asset, view.get("buffer"))
        if view.get("byteOffset", 0) + view.get("byteLength", 0) > len(data):
            raise GltfError("buffer_view_exceeds_buffer", f"view {layout['view']}")
        values = _read_elements(data, layout["start"], layout["stride"], count, component_type, kind)
    sparse = accessor.get("sparse")
    if sparse is not None:
        values = _apply_sparse(asset, index, sparse, values, component_type, kind)
    if normalized and accessor.get("normalized") and component_type in NORMALIZED_DIVISORS:
        divisor = NORMALIZED_DIVISORS[component_type]
        values = [tuple(max(value / divisor, -1.0) for value in element) for element in values]
    return values


def _apply_sparse(asset: Asset, index: int, sparse: dict, values: list, component_type: int, kind: str) -> list:
    if not isinstance(sparse, dict):
        raise GltfError("sparse_invalid", f"accessor {index}")
    total, indices, substitutes = sparse.get("count"), sparse.get("indices", {}), sparse.get("values", {})
    if not isinstance(total, int) or not 1 <= total <= len(values):
        raise GltfError("sparse_count_invalid", f"accessor {index}: {total}")
    index_type = indices.get("componentType")
    if index_type not in (5121, 5123, 5125):
        raise GltfError("sparse_index_type_invalid", f"accessor {index}: {index_type}")
    index_data = view_bytes(asset, indices.get("bufferView"))
    positions = [element[0] for element in _read_elements(index_data, indices.get("byteOffset", 0),
                                                           COMPONENT_TYPES[index_type][1], total, index_type, "SCALAR")]
    if any(later <= earlier for earlier, later in zip(positions, positions[1:])) or positions[-1] >= len(values):
        raise GltfError("sparse_indices_invalid", f"accessor {index}: not strictly increasing or out of range")
    value_data = view_bytes(asset, substitutes.get("bufferView"))
    replacements = _read_elements(value_data, substitutes.get("byteOffset", 0), element_size(component_type, kind),
                                  total, component_type, kind)
    values = list(values)
    for position, replacement in zip(positions, replacements):
        values[position] = replacement
    return values


# Transforms ---------------------------------------------------------------------------------------------


def quaternion_matrix(quaternion) -> list:
    """The 3x3 rotation of a unit quaternion (x, y, z, w)."""
    x, y, z, w = (float(value) for value in quaternion)
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def compose(translation=(0.0, 0.0, 0.0), rotation=(0.0, 0.0, 0.0, 1.0), scale=(1.0, 1.0, 1.0)) -> list:
    """The 4x4 matrix T * R * S that a glTF node's translation, rotation and scale describe."""
    rotate = quaternion_matrix(rotation)
    matrix = [[rotate[row][column] * scale[column] for column in range(3)] + [float(translation[row])]
              for row in range(3)]
    return matrix + [[0.0, 0.0, 0.0, 1.0]]


def node_local_matrix(node: dict) -> list:
    """A node's local matrix from ``matrix`` (column-major) or from translation, rotation and scale."""
    if "matrix" in node:
        values = node["matrix"]
        return [[float(values[column * 4 + row]) for column in range(4)] for row in range(4)]
    return compose(node.get("translation", (0.0, 0.0, 0.0)), node.get("rotation", (0.0, 0.0, 0.0, 1.0)),
                   node.get("scale", (1.0, 1.0, 1.0)))


def multiply(left: list, right: list) -> list:
    """The 4x4 product left * right."""
    return [[sum(left[row][k] * right[k][column] for k in range(4)) for column in range(4)] for row in range(4)]


def transform_point(matrix: list, point) -> tuple:
    """The point (x, y, z) moved by a 4x4 affine matrix."""
    x, y, z = point[0], point[1], point[2]
    return tuple(matrix[row][0] * x + matrix[row][1] * y + matrix[row][2] * z + matrix[row][3] for row in range(3))


def determinant3(matrix: list) -> float:
    """The determinant of the upper-left 3x3 block: negative when the transform mirrors."""
    (a, b, c), (d, e, f), (g, h, i) = (row[:3] for row in matrix[:3])
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def parents(document: dict) -> dict:
    """Child node index -> parent node index. A child claimed by two parents keeps the first."""
    result = {}
    nodes = document.get("nodes", [])
    for parent, node in enumerate(nodes if isinstance(nodes, list) else []):
        for child in node.get("children", []) if isinstance(node, dict) else []:
            if isinstance(child, int) and child not in result:
                result[child] = parent
    return result


def scene_roots(document: dict, scene=None) -> list:
    """Root nodes of ``scene`` (default: the document's scene, else scene 0, else every parentless node)."""
    scenes = document.get("scenes", [])
    if scene is None:
        scene = document.get("scene", 0 if scenes else None)
    if scene is not None and isinstance(scenes, list) and 0 <= scene < len(scenes):
        return [node for node in scenes[scene].get("nodes", []) if isinstance(node, int)]
    claimed = parents(document)
    return [index for index in range(len(document.get("nodes", []))) if index not in claimed]


def world_matrices(document: dict, scene=None) -> dict:
    """Node index -> world matrix for every node reachable from the scene's roots (cycles are cut)."""
    nodes = document.get("nodes", [])
    result, stack = {}, [(root, IDENTITY) for root in reversed(scene_roots(document, scene))]
    while stack:
        index, parent_matrix = stack.pop()
        if not isinstance(index, int) or not 0 <= index < len(nodes) or index in result:
            continue
        result[index] = multiply(parent_matrix, node_local_matrix(nodes[index]))
        for child in reversed(nodes[index].get("children", [])):
            stack.append((child, result[index]))
    return result


def node_path(document: dict, index: int) -> str:
    """The node's name path from its root, joined with '/', using '#<index>' for an unnamed node."""
    claimed, names, seen = parents(document), [], set()
    nodes = document.get("nodes", [])
    while index is not None and index not in seen and 0 <= index < len(nodes):
        seen.add(index)
        names.append(nodes[index].get("name") or f"#{index}")
        index = claimed.get(index)
    return "/".join(reversed(names))


# Geometry -----------------------------------------------------------------------------------------------


def mesh_local_bounds(asset: Asset, mesh_index: int) -> "tuple | None":
    """(minimum, maximum) of the decoded POSITION data of every primitive of a mesh, or None without positions."""
    meshes = asset.items("meshes")
    if not 0 <= mesh_index < len(meshes):
        raise GltfError("mesh_missing", str(mesh_index))
    low, high = [math.inf] * 3, [-math.inf] * 3
    for primitive in meshes[mesh_index].get("primitives", []):
        position = primitive.get("attributes", {}).get("POSITION")
        if position is None:
            continue
        for point in accessor_values(asset, position):
            for axis in range(3):
                low[axis] = min(low[axis], point[axis])
                high[axis] = max(high[axis], point[axis])
    return None if low[0] == math.inf else (tuple(low), tuple(high))


def transformed_bounds(matrix: list, bounds: tuple) -> tuple:
    """The axis-aligned box around the eight corners of ``bounds`` moved by ``matrix``."""
    low, high = bounds
    corners = [transform_point(matrix, (x, y, z)) for x in (low[0], high[0]) for y in (low[1], high[1])
               for z in (low[2], high[2])]
    return (tuple(min(corner[axis] for corner in corners) for axis in range(3)),
            tuple(max(corner[axis] for corner in corners) for axis in range(3)))


def union_bounds(boxes) -> "tuple | None":
    boxes = [box for box in boxes if box is not None]
    if not boxes:
        return None
    return (tuple(min(box[0][axis] for box in boxes) for axis in range(3)),
            tuple(max(box[1][axis] for box in boxes) for axis in range(3)))


def node_world_bounds(asset: Asset, scene=None) -> dict:
    """Node index -> world box of the node's own mesh (not its children), for every mesh node in the scene."""
    matrices, nodes, cache, result = world_matrices(asset.document, scene), asset.items("nodes"), {}, {}
    for index, matrix in matrices.items():
        mesh = nodes[index].get("mesh")
        if not isinstance(mesh, int):
            continue
        if mesh not in cache:
            cache[mesh] = mesh_local_bounds(asset, mesh)
        if cache[mesh] is not None:
            result[index] = transformed_bounds(matrix, cache[mesh])
    return result


def subtree_bounds(asset: Asset, root: int, scene=None, per_node: "dict | None" = None) -> "tuple | None":
    """The world box of every mesh in the subtree under ``root`` (the root included)."""
    per_node = per_node if per_node is not None else node_world_bounds(asset, scene)
    nodes, stack, seen, boxes = asset.items("nodes"), [root], set(), []
    while stack:
        index = stack.pop()
        if index in seen or not 0 <= index < len(nodes):
            continue
        seen.add(index)
        boxes.append(per_node.get(index))
        stack.extend(child for child in nodes[index].get("children", []) if isinstance(child, int))
    return union_bounds(boxes)


def scene_bounds(asset: Asset, scene=None) -> "tuple | None":
    """The world box of every mesh in the scene."""
    return union_bounds(node_world_bounds(asset, scene).values())


def primitive_triangles(asset: Asset, primitive: dict) -> int:
    """Triangles one primitive draws (0 for points and lines)."""
    mode = primitive.get("mode", 4)
    if primitive.get("indices") is not None:
        count = accessor_layout(asset, primitive["indices"])["count"]
    else:
        position = primitive.get("attributes", {}).get("POSITION")
        count = accessor_layout(asset, position)["count"] if position is not None else 0
    if mode == 4:
        return count // 3
    if mode in (5, 6):
        return max(count - 2, 0)
    return 0


def mesh_triangles(asset: Asset, mesh_index: int) -> int:
    return sum(primitive_triangles(asset, primitive)
               for primitive in asset.items("meshes")[mesh_index].get("primitives", []))


def triangles(asset: Asset, primitive: dict) -> list:
    """Vertex index triples of a triangle primitive (lists, strips and fans), in winding order."""
    mode = primitive.get("mode", 4)
    if primitive.get("indices") is not None:
        order = [element[0] for element in accessor_values(asset, primitive["indices"], normalized=False)]
    else:
        order = list(range(accessor_layout(asset, primitive["attributes"]["POSITION"])["count"]))
    if mode == 4:
        return [tuple(order[index:index + 3]) for index in range(0, len(order) - 2, 3)]
    if mode == 5:
        return [(order[i], order[i + 1], order[i + 2]) if i % 2 == 0 else (order[i + 1], order[i], order[i + 2])
                for i in range(len(order) - 2)]
    if mode == 6:
        return [(order[0], order[i], order[i + 1]) for i in range(1, len(order) - 1)]
    return []


# Animation ----------------------------------------------------------------------------------------------


def animation_clips(asset: Asset) -> list:
    """Each animation as name, start, end, duration and channels (node, node name, path, interpolation, keys).

    Times come from the samplers' input accessors; an unreadable input is reported in the clip's problems."""
    nodes, clips = asset.items("nodes"), []
    for index, animation in enumerate(asset.items("animations")):
        samplers, channels, start, end, problems = animation.get("samplers", []), [], math.inf, -math.inf, []
        for channel in animation.get("channels", []):
            target = channel.get("target", {})
            node = target.get("node")
            row = {"node": node, "node_name": nodes[node].get("name") if isinstance(node, int)
                   and 0 <= node < len(nodes) else None, "path": target.get("path"), "keys": 0,
                   "interpolation": None}
            sampler_index = channel.get("sampler")
            if isinstance(sampler_index, int) and 0 <= sampler_index < len(samplers):
                sampler = samplers[sampler_index]
                row["interpolation"] = sampler.get("interpolation", "LINEAR")
                try:
                    times = [element[0] for element in accessor_values(asset, sampler.get("input"))]
                    row["keys"] = len(times)
                    start, end = min(start, min(times)), max(end, max(times))
                except GltfError as error:
                    problems.append(error.reason)
            channels.append(row)
        clips.append({"index": index, "name": animation.get("name") or f"animation_{index}",
                      "start": start if start != math.inf else 0.0, "end": end if end != -math.inf else 0.0,
                      "duration": (end - start) if end != -math.inf else 0.0, "channels": channels,
                      "problems": problems})
    return clips


# Writing ------------------------------------------------------------------------------------------------


class BufferBuilder:
    """Collects binary data for a new asset: each ``add`` appends one buffer view and one accessor."""

    def __init__(self, document: dict) -> None:
        self.document, self.data = document, bytearray()
        document.setdefault("bufferViews", [])
        document.setdefault("accessors", [])

    def add(self, values, component_type: int, kind: str, target: "int | None" = None, bounds: bool = False,
            normalized: bool = False) -> int:
        """Append ``values`` (a list of tuples) as a tightly packed view and accessor; return the accessor index."""
        letter, size, _name = COMPONENT_TYPES[component_type]
        width = TYPE_COMPONENTS[kind]
        if element_size(component_type, kind) != width * size:
            raise GltfError("writer_layout_unsupported", f"{kind} of {COMPONENT_TYPES[component_type][2]}")
        while len(self.data) % 4:
            self.data.append(0)
        flat = [component for element in values for component in element]
        if len(flat) != width * len(values) or not values:
            raise GltfError("writer_values_invalid", f"{len(values)} elements of {kind}")
        start = len(self.data)
        self.data += struct.pack(f"<{len(flat)}{letter}", *flat)
        view = {"buffer": 0, "byteOffset": start, "byteLength": len(self.data) - start}
        if target is not None:
            view["target"] = target
        self.document["bufferViews"].append(view)
        accessor = {"bufferView": len(self.document["bufferViews"]) - 1, "componentType": component_type,
                    "count": len(values), "type": kind}
        if normalized:
            accessor["normalized"] = True
        if bounds:
            accessor["min"] = [min(element[axis] for element in values) for axis in range(width)]
            accessor["max"] = [max(element[axis] for element in values) for axis in range(width)]
        self.document["accessors"].append(accessor)
        return len(self.document["accessors"]) - 1

    def finish(self) -> dict:
        """Attach the collected bytes as buffer 0, embedded as a base64 data URI, and return the document."""
        while len(self.data) % 4:
            self.data.append(0)
        self.document["buffers"] = [{"byteLength": len(self.data), "uri": "data:application/octet-stream;base64,"
                                     + base64.b64encode(bytes(self.data)).decode("ascii")}]
        return self.document


def dumps(document: dict) -> str:
    """Deterministic .gltf text: sorted keys, one-space indent, a final newline."""
    return json.dumps(document, indent=1, sort_keys=True, allow_nan=False) + "\n"


__all__ = ["COMPONENT_TYPES", "TYPE_COMPONENTS", "PRIMITIVE_MODES", "IDENTITY", "GltfError", "Asset", "BufferBuilder",
           "strict_json", "decode_data_uri", "resolve_uri", "loads", "load", "element_size", "accessor_layout", "view_bytes",
           "accessor_values", "quaternion_matrix", "compose", "node_local_matrix", "multiply", "transform_point",
           "determinant3", "parents", "scene_roots", "world_matrices", "node_path", "mesh_local_bounds",
           "transformed_bounds", "union_bounds", "node_world_bounds", "subtree_bounds", "scene_bounds",
           "primitive_triangles", "mesh_triangles", "triangles", "animation_clips", "dumps"]
