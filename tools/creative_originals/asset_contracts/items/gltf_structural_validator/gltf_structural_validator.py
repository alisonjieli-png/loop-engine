"""glTF 2.0 structural validator: every reference, range and count a loader relies on.

    python3 gltf_structural_validator.py ASSET.gltf

Reads a .gltf (embedded or sibling buffers) or a .glb and checks buffers, buffer views, accessors (types,
alignment, bounds inside their views, declared min and max against the data), meshes and primitives (attribute
types and counts, index type and range, morph targets), materials, textures, samplers and images, nodes and
scenes (references, one parent per node, no cycles, unit quaternions), skins (joints, inverse bind matrices,
skinning attributes) and animations (sampler references, increasing key times, output types and counts per
interpolation). Prints one JSON report; exits 0 when no rule fails, 1 otherwise.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import asset_report
import gltfio

TOOL = "gltf_structural_validator"
ARRAY_KEYS = ("accessors", "animations", "buffers", "bufferViews", "cameras", "images", "materials", "meshes",
              "nodes", "samplers", "scenes", "skins", "textures")
FLOAT = 5126
#: Allowed (type set, (componentType, normalized) set) for each vertex attribute semantic.
ATTRIBUTE_RULES = {
    "POSITION": ({"VEC3"}, {(FLOAT, False)}),
    "NORMAL": ({"VEC3"}, {(FLOAT, False)}),
    "TANGENT": ({"VEC4"}, {(FLOAT, False)}),
    "TEXCOORD": ({"VEC2"}, {(FLOAT, False), (5121, True), (5123, True)}),
    "COLOR": ({"VEC3", "VEC4"}, {(FLOAT, False), (5121, True), (5123, True)}),
    "JOINTS": ({"VEC4"}, {(5121, False), (5123, False)}),
    "WEIGHTS": ({"VEC4"}, {(FLOAT, False), (5121, True), (5123, True)}),
}
ANIMATION_OUTPUT_TYPES = {"translation": "VEC3", "rotation": "VEC4", "scale": "VEC3", "weights": "SCALAR"}
INTERPOLATIONS = ("LINEAR", "STEP", "CUBICSPLINE")
INDEX_RESTART = {5121: 255, 5123: 65535, 5125: 4294967295}
MAG_FILTERS, MIN_FILTERS = (9728, 9729), (9728, 9729, 9984, 9985, 9986, 9987)
WRAPS = (33071, 33648, 10497)
TEXTURE_SLOTS = (("pbrMetallicRoughness", "baseColorTexture"), ("pbrMetallicRoughness", "metallicRoughnessTexture"),
                 (None, "normalTexture"), (None, "occlusionTexture"), (None, "emissiveTexture"))
FAILURES = ("file_unreadable", "json_invalid", "asset_header_invalid", "asset_version_unsupported",
            "property_type_invalid", "extension_required_not_used", "buffer_invalid", "buffer_unresolved",
            "buffer_length_mismatch", "buffer_reference_invalid", "buffer_view_out_of_range", "byte_stride_invalid",
            "buffer_view_target_invalid", "buffer_view_reference_invalid", "accessor_type_invalid",
            "accessor_count_invalid", "accessor_normalized_invalid", "accessor_misaligned", "accessor_out_of_bounds",
            "accessor_min_max_invalid", "accessor_min_max_mismatch", "accessor_min_max_missing",
            "accessor_value_not_finite", "accessor_reference_invalid", "sparse_invalid", "mesh_primitive_invalid",
            "attribute_type_invalid", "attribute_count_mismatch", "index_type_invalid", "index_out_of_range",
            "index_restart_value", "primitive_mode_invalid", "primitive_count_invalid", "material_reference_invalid",
            "morph_target_invalid", "material_value_invalid", "texture_reference_invalid",
            "sampler_reference_invalid", "sampler_value_invalid", "image_reference_invalid", "image_source_invalid",
            "image_unresolved", "node_reference_invalid", "mesh_reference_invalid", "skin_reference_invalid",
            "camera_reference_invalid", "node_transform_conflict", "node_transform_invalid",
            "node_rotation_not_unit", "node_multiple_parents", "node_cycle", "node_skin_without_mesh",
            "scene_reference_invalid", "scene_node_not_root", "skin_joint_invalid", "skin_inverse_bind_invalid",
            "skin_inverse_bind_count_mismatch", "skin_skeleton_not_ancestor", "skin_attributes_missing",
            "skin_joint_index_out_of_range", "animation_sampler_reference_invalid", "animation_target_invalid",
            "animation_channel_duplicate", "animation_input_invalid", "animation_input_negative",
            "animation_input_not_increasing", "animation_interpolation_invalid", "animation_output_invalid",
            "animation_output_count_mismatch")
#: gltfio load failures reported as file_unreadable; any other load failure is reported as json_invalid.
UNREADABLE_FILE_REASONS = ("file_unreadable", "file_too_large")


def _is_index(value, length: int) -> bool:
    return type(value) is int and 0 <= value < length


def _number(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _numbers(value, length: int) -> bool:
    return isinstance(value, list) and len(value) == length and all(_number(item) for item in value)


class _Context:
    def __init__(self, asset: gltfio.Asset, report: asset_report.Report) -> None:
        self.asset, self.report, self.document = asset, report, asset.document
        self.counts = {key: len(asset.items(key)) for key in ARRAY_KEYS}
        self.readable = set()  # accessors whose data decodes
        self.cache = {}

    def values(self, index: int, normalized: bool = True) -> "list | None":
        if index not in self.readable:
            return None
        key = (index, normalized)
        if key not in self.cache:
            self.cache[key] = gltfio.accessor_values(self.asset, index, normalized)
        return self.cache[key]

    def accessor(self, index: int) -> dict:
        return self.asset.items("accessors")[index]

    def reference(self, value, key: str, code: str, where: str) -> bool:
        if _is_index(value, self.counts[key]):
            return True
        self.report.fail(code, where, f"{value!r} is not an index into {key} ({self.counts[key]} entries)")
        return False


def _check_header(context: _Context) -> None:
    document, report = context.document, context.report
    header = document.get("asset")
    if not isinstance(header, dict) or not isinstance(header.get("version"), str):
        report.fail("asset_header_invalid", "asset", "asset.version is required")
        return
    parts = header["version"].split(".")
    if len(parts) != 2 or not all(part.isdigit() for part in parts) or parts[0] != "2":
        report.fail("asset_version_unsupported", "asset.version", header["version"])
    minimum = header.get("minVersion")
    if minimum is not None and (not isinstance(minimum, str) or minimum.split(".")[0] != "2"):
        report.fail("asset_version_unsupported", "asset.minVersion", repr(minimum))
    for key in ARRAY_KEYS:
        value = document.get(key)
        if value is not None and (not isinstance(value, list) or not all(isinstance(item, dict) for item in value)):
            report.fail("property_type_invalid", key, "must be an array of objects")
    used, required = document.get("extensionsUsed", []), document.get("extensionsRequired", [])
    for name in required if isinstance(required, list) else []:
        if name not in (used if isinstance(used, list) else []):
            report.fail("extension_required_not_used", "extensionsRequired", name)


def _check_buffers(context: _Context) -> None:
    asset, report = context.asset, context.report
    for problem in asset.problems:
        report.fail("buffer_unresolved", f"buffers[{problem['buffer']}]", f"{problem['reason']} {problem['detail']}")
    for index, buffer in enumerate(asset.items("buffers")):
        length = buffer.get("byteLength")
        if type(length) is not int or length < 1:
            report.fail("buffer_invalid", f"buffers[{index}]", "byteLength must be a positive integer")
            continue
        data = asset.buffers[index] if index < len(asset.buffers) else None
        if data is None:
            continue
        if len(data) < length:
            report.fail("buffer_length_mismatch", f"buffers[{index}]", f"declares {length} bytes, holds {len(data)}")
        elif len(data) > length + 3:
            report.warn("buffer_longer_than_declared", f"buffers[{index}]", f"declares {length}, holds {len(data)}")
    for index, view in enumerate(context.asset.items("bufferViews")):
        where = f"bufferViews[{index}]"
        if not context.reference(view.get("buffer"), "buffers", "buffer_reference_invalid", where):
            continue
        offset, length = view.get("byteOffset", 0), view.get("byteLength")
        if type(offset) is not int or offset < 0 or type(length) is not int or length < 1:
            report.fail("buffer_view_out_of_range", where, "byteOffset and byteLength must be integers, length >= 1")
            continue
        declared = context.asset.items("buffers")[view["buffer"]].get("byteLength")
        if type(declared) is int and offset + length > declared:
            report.fail("buffer_view_out_of_range", where, f"ends at {offset + length}, buffer has {declared} bytes")
        stride = view.get("byteStride")
        if stride is not None and (type(stride) is not int or not 4 <= stride <= 252 or stride % 4):
            report.fail("byte_stride_invalid", where, f"byteStride {stride!r} must be 4 to 252 and a multiple of 4")
        if view.get("target") not in (None, 34962, 34963):
            report.fail("buffer_view_target_invalid", where, repr(view.get("target")))


def _check_accessors(context: _Context) -> None:
    asset, report = context.asset, context.report
    views = asset.items("bufferViews")
    for index, accessor in enumerate(asset.items("accessors")):
        where = f"accessors[{index}]"
        component_type, kind, count = accessor.get("componentType"), accessor.get("type"), accessor.get("count")
        if component_type not in gltfio.COMPONENT_TYPES or kind not in gltfio.TYPE_COMPONENTS:
            report.fail("accessor_type_invalid", where, f"componentType {component_type!r}, type {kind!r}")
            continue
        if type(count) is not int or count < 1:
            report.fail("accessor_count_invalid", where, repr(count))
            continue
        if accessor.get("normalized") and component_type in (FLOAT, 5125):
            report.fail("accessor_normalized_invalid", where, "only 8 and 16 bit integers may be normalized")
        size = gltfio.COMPONENT_TYPES[component_type][1]
        view_index = accessor.get("bufferView")
        if view_index is not None:
            if not context.reference(view_index, "bufferViews", "buffer_view_reference_invalid", where):
                continue
            offset = accessor.get("byteOffset", 0)
            view = views[view_index]
            view_offset = view.get("byteOffset", 0)
            if type(offset) is not int or offset < 0 or offset % size or (type(view_offset) is int
                                                                         and (view_offset + offset) % size):
                report.fail("accessor_misaligned", where, f"byteOffset {offset!r} with view offset {view_offset!r} "
                                                          f"is not a multiple of {size}")
                continue
            stride = view.get("byteStride")
            if type(stride) is int and stride % size:
                report.fail("accessor_misaligned", where, f"view stride {stride} is not a multiple of {size}")
                continue
            try:
                gltfio.accessor_layout(asset, index)
            except gltfio.GltfError as error:
                report.fail("accessor_out_of_bounds", where, error.detail or error.reason)
                continue
            buffer_index = view.get("buffer")
            if not _is_index(buffer_index, len(asset.buffers)) or asset.buffers[buffer_index] is None:
                continue
            buffer_bytes = asset.buffers[buffer_index]
            if type(view.get("byteLength")) is not int or view_offset + view["byteLength"] > len(buffer_bytes):
                continue
        try:
            values = gltfio.accessor_values(asset, index, normalized=False)
        except gltfio.GltfError as error:
            code = "sparse_invalid" if error.reason.startswith("sparse") or "sparse" in accessor else \
                "accessor_out_of_bounds"
            report.fail(code, where, f"{error.reason} {error.detail}")
            continue
        context.readable.add(index)
        context.cache[(index, False)] = values
        if component_type == FLOAT and any(not math.isfinite(component) for element in values for component in element):
            report.fail("accessor_value_not_finite", where, "NaN or infinity in the data")
            continue
        _check_min_max(context, index, accessor, values)


def _check_min_max(context: _Context, index: int, accessor: dict, values: list) -> None:
    width = gltfio.TYPE_COMPONENTS[accessor["type"]]
    for key, pick in (("min", min), ("max", max)):
        declared = accessor.get(key)
        if declared is None:
            continue
        if not _numbers(declared, width):
            context.report.fail("accessor_min_max_invalid", f"accessors[{index}].{key}", f"needs {width} numbers")
            continue
        actual = [pick(element[axis] for element in values) for axis in range(width)]
        for axis, (expected, found) in enumerate(zip(declared, actual)):
            tolerance = 1e-5 * max(1.0, abs(found)) if accessor["componentType"] == FLOAT else 0
            if abs(expected - found) > tolerance:
                context.report.fail("accessor_min_max_mismatch", f"accessors[{index}].{key}[{axis}]",
                                    f"declares {expected}, data has {found}")
                break


def _semantic(name: str) -> str:
    return name.split("_", 1)[0] if name.split("_", 1)[0] in ("TEXCOORD", "COLOR", "JOINTS", "WEIGHTS") else name


def _check_meshes(context: _Context) -> None:
    report = context.report
    for mesh_index, mesh in enumerate(context.asset.items("meshes")):
        primitives = mesh.get("primitives")
        if not isinstance(primitives, list) or not primitives:
            report.fail("mesh_primitive_invalid", f"meshes[{mesh_index}]", "primitives must be a non-empty array")
            continue
        target_counts = set()
        for primitive_index, primitive in enumerate(primitives):
            where = f"meshes[{mesh_index}].primitives[{primitive_index}]"
            if not isinstance(primitive, dict) or not isinstance(primitive.get("attributes"), dict) \
                    or not primitive["attributes"]:
                report.fail("mesh_primitive_invalid", where, "attributes must be a non-empty object")
                continue
            vertex_count = _check_attributes(context, primitive["attributes"], where)
            _check_indices(context, primitive, vertex_count, where)
            if "material" in primitive:
                context.reference(primitive["material"], "materials", "material_reference_invalid", where)
            targets = primitive.get("targets", [])
            target_counts.add(len(targets) if isinstance(targets, list) else -1)
            for target_index, target in enumerate(targets if isinstance(targets, list) else []):
                for name, accessor_index in (target.items() if isinstance(target, dict) else []):
                    if context.reference(accessor_index, "accessors", "accessor_reference_invalid",
                                         f"{where}.targets[{target_index}].{name}") and vertex_count is not None \
                            and context.accessor(accessor_index).get("count") != vertex_count:
                        report.fail("morph_target_invalid", f"{where}.targets[{target_index}].{name}",
                                    f"count {context.accessor(accessor_index).get('count')} != {vertex_count}")
        if len(target_counts) > 1:
            report.fail("morph_target_invalid", f"meshes[{mesh_index}]", "primitives differ in morph target count")
        weights = mesh.get("weights")
        if weights is not None and (not isinstance(weights, list) or len(weights) != max(target_counts)):
            report.fail("morph_target_invalid", f"meshes[{mesh_index}].weights", "one weight per morph target")


def _check_attributes(context: _Context, attributes: dict, where: str) -> "int | None":
    report, counts = context.report, {}
    for name, accessor_index in attributes.items():
        if not context.reference(accessor_index, "accessors", "accessor_reference_invalid", f"{where}.{name}"):
            continue
        accessor = context.accessor(accessor_index)
        counts[name] = accessor.get("count")
        rule = ATTRIBUTE_RULES.get(_semantic(name))
        if rule is not None and (accessor.get("type") not in rule[0]
                                 or (accessor.get("componentType"), bool(accessor.get("normalized"))) not in rule[1]):
            report.fail("attribute_type_invalid", f"{where}.{name}",
                        f"{accessor.get('type')} of componentType {accessor.get('componentType')}")
        if name == "POSITION" and ("min" not in accessor or "max" not in accessor):
            report.fail("accessor_min_max_missing", f"{where}.POSITION", "POSITION accessors declare min and max")
    if len(set(counts.values())) > 1:
        report.fail("attribute_count_mismatch", where, ", ".join(f"{key}={value}" for key, value in sorted(counts.items())))
    if "POSITION" not in attributes:
        report.warn("primitive_without_positions", where, "a loader skips a primitive without positions")
    return counts.get("POSITION")


def _check_indices(context: _Context, primitive: dict, vertex_count: "int | None", where: str) -> None:
    report, mode = context.report, primitive.get("mode", 4)
    if mode not in gltfio.PRIMITIVE_MODES:
        report.fail("primitive_mode_invalid", where, repr(mode))
        return
    count = vertex_count
    index = primitive.get("indices")
    if index is not None:
        if not context.reference(index, "accessors", "accessor_reference_invalid", f"{where}.indices"):
            return
        accessor = context.accessor(index)
        if accessor.get("type") != "SCALAR" or accessor.get("componentType") not in INDEX_RESTART \
                or accessor.get("normalized"):
            report.fail("index_type_invalid", f"{where}.indices", f"{accessor.get('type')} of "
                                                                  f"{accessor.get('componentType')}")
            return
        count = accessor.get("count")
        values = context.values(index, normalized=False)
        if values is not None and vertex_count is not None:
            restart = INDEX_RESTART[accessor["componentType"]]
            if any(element[0] == restart for element in values):
                report.fail("index_restart_value", f"{where}.indices", f"holds the restart value {restart}")
            high = max(element[0] for element in values)
            if high >= vertex_count:
                report.fail("index_out_of_range", f"{where}.indices", f"index {high} >= vertex count {vertex_count}")
    if type(count) is int:
        divisor = {4: 3, 1: 2}.get(mode)
        if (divisor and count % divisor) or (mode in (5, 6) and count < 3) or (mode in (2, 3) and count < 2):
            report.fail("primitive_count_invalid", where, f"{count} indices for {gltfio.PRIMITIVE_MODES[mode]}")


def _check_materials(context: _Context) -> None:
    report = context.report
    for index, material in enumerate(context.asset.items("materials")):
        where = f"materials[{index}]"
        pbr = material.get("pbrMetallicRoughness", {})
        pbr = pbr if isinstance(pbr, dict) else {}
        for parent, slot in TEXTURE_SLOTS:
            info = (pbr if parent else material).get(slot)
            if info is None:
                continue
            if not isinstance(info, dict):
                report.fail("texture_reference_invalid", f"{where}.{slot}", "texture info must be an object")
                continue
            context.reference(info.get("index"), "textures", "texture_reference_invalid", f"{where}.{slot}")
            if type(info.get("texCoord", 0)) is not int or info.get("texCoord", 0) < 0:
                report.fail("texture_reference_invalid", f"{where}.{slot}.texCoord", repr(info.get("texCoord")))
        factor = pbr.get("baseColorFactor")
        if factor is not None and (not _numbers(factor, 4) or not all(0 <= value <= 1 for value in factor)):
            report.fail("material_value_invalid", f"{where}.baseColorFactor", "four numbers in [0, 1]")
        for key in ("metallicFactor", "roughnessFactor"):
            value = pbr.get(key)
            if value is not None and (not _number(value) or not 0 <= value <= 1):
                report.fail("material_value_invalid", f"{where}.{key}", repr(value))
        emissive = material.get("emissiveFactor")
        if emissive is not None and (not _numbers(emissive, 3) or not all(0 <= value <= 1 for value in emissive)):
            report.fail("material_value_invalid", f"{where}.emissiveFactor", "three numbers in [0, 1]")
        if material.get("alphaMode", "OPAQUE") not in ("OPAQUE", "MASK", "BLEND"):
            report.fail("material_value_invalid", f"{where}.alphaMode", repr(material.get("alphaMode")))
        cutoff = material.get("alphaCutoff")
        if cutoff is not None and (not _number(cutoff) or cutoff < 0):
            report.fail("material_value_invalid", f"{where}.alphaCutoff", repr(cutoff))
    for index, texture in enumerate(context.asset.items("textures")):
        where = f"textures[{index}]"
        if "sampler" in texture:
            context.reference(texture["sampler"], "samplers", "sampler_reference_invalid", where)
        if "source" in texture:
            context.reference(texture["source"], "images", "image_reference_invalid", where)
        elif not texture.get("extensions"):
            report.warn("texture_without_source", where, "a loader shows no image for this texture")
    for index, sampler in enumerate(context.asset.items("samplers")):
        for key, allowed in (("magFilter", MAG_FILTERS), ("minFilter", MIN_FILTERS), ("wrapS", WRAPS),
                             ("wrapT", WRAPS)):
            if key in sampler and sampler[key] not in allowed:
                report.fail("sampler_value_invalid", f"samplers[{index}].{key}", repr(sampler[key]))
    _check_images(context)


def _check_images(context: _Context) -> None:
    report, asset = context.report, context.asset
    for index, image in enumerate(asset.items("images")):
        where = f"images[{index}]"
        has_uri, has_view = "uri" in image, "bufferView" in image
        if has_uri == has_view:
            report.fail("image_source_invalid", where, "exactly one of uri and bufferView")
            continue
        data = None
        try:
            if has_view:
                if "mimeType" not in image:
                    report.fail("image_source_invalid", where, "an image in a buffer view declares mimeType")
                if context.reference(image["bufferView"], "bufferViews", "buffer_view_reference_invalid", where):
                    data = gltfio.view_bytes(asset, image["bufferView"])
            elif isinstance(image["uri"], str) and image["uri"].startswith("data:"):
                data = gltfio.decode_data_uri(image["uri"])
            else:
                target = gltfio.resolve_uri(asset.path.parent if asset.path else None, image["uri"])
                if not target.is_file():
                    raise gltfio.GltfError("image_file_missing", str(image["uri"])[:80])
                with open(target, "rb") as stream:
                    data = stream.read(16)
        except gltfio.GltfError as error:
            report.fail("image_unresolved", where, f"{error.reason} {error.detail}")
            continue
        if data is not None and not (data.startswith(b"\x89PNG\r\n\x1a\n") or data.startswith(b"\xff\xd8\xff")):
            report.warn("image_format_unrecognized", where, "neither PNG nor JPEG magic bytes")


def _check_nodes(context: _Context) -> None:
    report, nodes = context.report, context.asset.items("nodes")
    parent_of = {}
    for index, node in enumerate(nodes):
        where = f"nodes[{index}]"
        children = node.get("children", [])
        if not isinstance(children, list):
            report.fail("node_reference_invalid", f"{where}.children", "must be an array")
            children = []
        for child in children:
            if not context.reference(child, "nodes", "node_reference_invalid", f"{where}.children"):
                continue
            if child in parent_of and parent_of[child] != index:
                report.fail("node_multiple_parents", f"nodes[{child}]", f"children of {parent_of[child]} and {index}")
            elif child == index:
                report.fail("node_cycle", where, "a node is its own child")
            parent_of.setdefault(child, index)
        _check_transform(context, node, where)
        for key, array, code in (("mesh", "meshes", "mesh_reference_invalid"), ("skin", "skins", "skin_reference_invalid"),
                                 ("camera", "cameras", "camera_reference_invalid")):
            if key in node:
                context.reference(node[key], array, code, f"{where}.{key}")
        if "skin" in node and "mesh" not in node:
            report.fail("node_skin_without_mesh", where, "a skin applies to a mesh on the same node")
        weights = node.get("weights")
        mesh = node.get("mesh")
        if weights is not None and _is_index(mesh, context.counts["meshes"]):
            primitives = context.asset.items("meshes")[mesh].get("primitives") or [{}]
            expected = len(primitives[0].get("targets", [])) if isinstance(primitives[0], dict) else 0
            if not isinstance(weights, list) or len(weights) != expected:
                report.fail("morph_target_invalid", f"{where}.weights", f"needs {expected} weights")
    _check_cycles(context, nodes)
    _check_scenes(context, parent_of)


def _check_transform(context: _Context, node: dict, where: str) -> None:
    report = context.report
    trs = [key for key in ("translation", "rotation", "scale") if key in node]
    if "matrix" in node:
        if trs:
            report.fail("node_transform_conflict", where, "matrix and " + ", ".join(trs))
        if not _numbers(node["matrix"], 16):
            report.fail("node_transform_invalid", f"{where}.matrix", "sixteen finite numbers")
    for key, length in (("translation", 3), ("rotation", 4), ("scale", 3)):
        if key in node and not _numbers(node[key], length):
            report.fail("node_transform_invalid", f"{where}.{key}", f"{length} finite numbers")
    if _numbers(node.get("rotation"), 4):
        length = math.sqrt(sum(value * value for value in node["rotation"]))
        if abs(length - 1.0) > 1e-3:
            report.fail("node_rotation_not_unit", f"{where}.rotation", f"length {length:.6f}")


def _check_cycles(context: _Context, nodes: list) -> None:
    state, reported = {}, set()
    for start in range(len(nodes)):
        if start in state:
            continue
        stack = [(start, iter(_children(nodes, start)))]
        state[start] = "open"
        while stack:
            index, children = stack[-1]
            child = next(children, None)
            if child is None:
                state[index] = "done"
                stack.pop()
            elif state.get(child) == "open" and child not in reported:
                reported.add(child)
                context.report.fail("node_cycle", f"nodes[{child}]", f"reached again from nodes[{index}]")
            elif child not in state:
                state[child] = "open"
                stack.append((child, iter(_children(nodes, child))))


def _children(nodes: list, index: int) -> list:
    children = nodes[index].get("children", [])
    return [child for child in children if _is_index(child, len(nodes)) and child != index] \
        if isinstance(children, list) else []


def _check_scenes(context: _Context, parent_of: dict) -> None:
    report, document = context.report, context.document
    if "scene" in document:
        context.reference(document["scene"], "scenes", "scene_reference_invalid", "scene")
    reachable = set()
    for index, scene in enumerate(context.asset.items("scenes")):
        roots = scene.get("nodes", [])
        if not isinstance(roots, list) or len(set(map(repr, roots))) != len(roots):
            report.fail("scene_reference_invalid", f"scenes[{index}].nodes", "a list of distinct node indices")
            continue
        for root in roots:
            if context.reference(root, "nodes", "scene_reference_invalid", f"scenes[{index}].nodes"):
                if root in parent_of:
                    report.fail("scene_node_not_root", f"scenes[{index}]", f"nodes[{root}] is a child of "
                                                                           f"nodes[{parent_of[root]}]")
                stack = [root]
                while stack:
                    node = stack.pop()
                    if node not in reachable:
                        reachable.add(node)
                        stack.extend(_children(context.asset.items("nodes"), node))
    unreachable = sorted(set(range(context.counts["nodes"])) - reachable)
    if unreachable and context.counts["scenes"]:
        report.warn("node_unreachable", "nodes", f"{len(unreachable)} nodes are in no scene: {unreachable[:10]}")


def _descendants(nodes: list, root: int) -> set:
    found, stack = set(), [root]
    while stack:
        index = stack.pop()
        if index not in found:
            found.add(index)
            stack.extend(_children(nodes, index))
    return found


def _check_skins(context: _Context) -> None:
    report, nodes = context.report, context.asset.items("nodes")
    for index, skin in enumerate(context.asset.items("skins")):
        where = f"skins[{index}]"
        joints = skin.get("joints")
        if not isinstance(joints, list) or not joints or not all(_is_index(joint, len(nodes)) for joint in joints) \
                or len(set(joints)) != len(joints):
            report.fail("skin_joint_invalid", f"{where}.joints", "a non-empty list of distinct node indices")
            continue
        if "skeleton" in skin and context.reference(skin["skeleton"], "nodes", "node_reference_invalid",
                                                    f"{where}.skeleton"):
            below = _descendants(nodes, skin["skeleton"])
            outside = [joint for joint in joints if joint not in below]
            if outside:
                report.fail("skin_skeleton_not_ancestor", where, f"joints {outside[:6]} are not under the skeleton")
        matrices = skin.get("inverseBindMatrices")
        if matrices is not None and context.reference(matrices, "accessors", "accessor_reference_invalid",
                                                      f"{where}.inverseBindMatrices"):
            accessor = context.accessor(matrices)
            if accessor.get("type") != "MAT4" or accessor.get("componentType") != FLOAT:
                report.fail("skin_inverse_bind_invalid", where, "inverse bind matrices are MAT4 floats")
            elif accessor.get("count") != len(joints):
                report.fail("skin_inverse_bind_count_mismatch", where,
                            f"{accessor.get('count')} matrices for {len(joints)} joints")
        for node_index, node in enumerate(nodes):
            if node.get("skin") == index and _is_index(node.get("mesh"), context.counts["meshes"]):
                _check_skinned_mesh(context, node["mesh"], len(joints), f"nodes[{node_index}]")


def _check_skinned_mesh(context: _Context, mesh_index: int, joint_count: int, where: str) -> None:
    for primitive_index, primitive in enumerate(context.asset.items("meshes")[mesh_index].get("primitives", [])):
        attributes = primitive.get("attributes", {}) if isinstance(primitive, dict) else {}
        if "JOINTS_0" not in attributes or "WEIGHTS_0" not in attributes:
            context.report.fail("skin_attributes_missing", f"{where} mesh {mesh_index} primitive {primitive_index}",
                                "a skinned mesh carries JOINTS_0 and WEIGHTS_0")
            continue
        for name in [key for key in attributes if key.startswith("JOINTS_")]:
            values = context.values(attributes[name], normalized=False) if _is_index(
                attributes[name], context.counts["accessors"]) else None
            if values and max(max(element) for element in values) >= joint_count:
                context.report.fail("skin_joint_index_out_of_range", f"{where} {name}",
                                    f"joint {max(max(element) for element in values)} of {joint_count}")


def _check_animations(context: _Context) -> None:
    report, nodes = context.report, context.asset.items("nodes")
    for index, animation in enumerate(context.asset.items("animations")):
        where = f"animations[{index}]"
        samplers, channels = animation.get("samplers"), animation.get("channels")
        if not isinstance(samplers, list) or not isinstance(channels, list) or not samplers or not channels:
            report.fail("animation_sampler_reference_invalid", where, "channels and samplers are non-empty arrays")
            continue
        targets = set()
        for channel_index, channel in enumerate(channels):
            spot = f"{where}.channels[{channel_index}]"
            if not _is_index(channel.get("sampler"), len(samplers)):
                report.fail("animation_sampler_reference_invalid", spot, repr(channel.get("sampler")))
                continue
            target = channel.get("target", {})
            node, path = target.get("node"), target.get("path")
            if path not in ANIMATION_OUTPUT_TYPES or (node is None and not target.get("extensions")) or \
                    (node is not None and not _is_index(node, len(nodes))):
                report.fail("animation_target_invalid", spot, f"node {node!r}, path {path!r}")
                continue
            if node is not None and (node, path) in targets:
                report.fail("animation_channel_duplicate", spot, f"node {node} {path} is animated twice")
            targets.add((node, path))
            _check_sampler(context, samplers[channel["sampler"]], path, node, f"{where}.samplers[{channel['sampler']}]")


def _morph_count(context: _Context, node: "int | None") -> int:
    if node is None:
        return 1
    mesh = context.asset.items("nodes")[node].get("mesh")
    if not _is_index(mesh, context.counts["meshes"]):
        return 0
    primitives = context.asset.items("meshes")[mesh].get("primitives") or [{}]
    return len(primitives[0].get("targets", [])) if isinstance(primitives[0], dict) else 0


def _check_sampler(context: _Context, sampler: dict, path: str, node, where: str) -> None:
    report = context.report
    interpolation = sampler.get("interpolation", "LINEAR")
    if interpolation not in INTERPOLATIONS:
        report.fail("animation_interpolation_invalid", where, repr(interpolation))
        return
    source, output = sampler.get("input"), sampler.get("output")
    if not context.reference(source, "accessors", "accessor_reference_invalid", f"{where}.input") or \
            not context.reference(output, "accessors", "accessor_reference_invalid", f"{where}.output"):
        return
    accessor = context.accessor(source)
    if accessor.get("type") != "SCALAR" or accessor.get("componentType") != FLOAT:
        report.fail("animation_input_invalid", f"{where}.input", "key times are SCALAR floats")
        return
    if "min" not in accessor or "max" not in accessor:
        report.fail("accessor_min_max_missing", f"{where}.input", "animation inputs declare min and max")
    times = context.values(source)
    if times is not None:
        flat = [element[0] for element in times]
        if flat and flat[0] < 0:
            report.fail("animation_input_negative", f"{where}.input", f"first time {flat[0]}")
        if any(later <= earlier for earlier, later in zip(flat, flat[1:])):
            report.fail("animation_input_not_increasing", f"{where}.input", "key times must strictly increase")
    out = context.accessor(output)
    expected_type = ANIMATION_OUTPUT_TYPES[path]
    allowed = {(FLOAT, False)} if path != "rotation" else {(FLOAT, False), (5120, True), (5121, True), (5122, True),
                                                            (5123, True)}
    if path == "weights":
        allowed = allowed | {(5120, True), (5121, True), (5122, True), (5123, True)}
    if out.get("type") != expected_type or (out.get("componentType"), bool(out.get("normalized"))) not in allowed:
        report.fail("animation_output_invalid", f"{where}.output", f"{path} needs {expected_type}, got "
                                                                   f"{out.get('type')} of {out.get('componentType')}")
        return
    if path == "weights" and _morph_count(context, node) == 0:
        report.fail("animation_target_invalid", where, "weights animated on a node whose mesh has no morph targets")
        return
    per_key = (3 if interpolation == "CUBICSPLINE" else 1) * (_morph_count(context, node) if path == "weights" else 1)
    keys = accessor.get("count")
    if type(keys) is int and out.get("count") != keys * per_key:
        report.fail("animation_output_count_mismatch", f"{where}.output",
                    f"{out.get('count')} values for {keys} keys of {interpolation} ({per_key} per key)")
    if interpolation == "CUBICSPLINE" and type(keys) is int and keys < 2:
        report.fail("animation_output_count_mismatch", where, "a cubic spline needs at least two keys")


def _facts(context: _Context) -> dict:
    asset, document = context.asset, context.document
    facts = {"container": asset.container, "counts": dict(context.counts),
             "generator": (document.get("asset") or {}).get("generator") if isinstance(document.get("asset"), dict)
             else None,
             "extensions_used": sorted(document.get("extensionsUsed", []) if isinstance(document.get("extensionsUsed"),
                                                                                      list) else []),
             "node_names": [node.get("name") for node in asset.items("nodes")],
             "mesh_names": [mesh.get("name") for mesh in asset.items("meshes")],
             "material_names": [material.get("name") for material in asset.items("materials")],
             "animation_names": [animation.get("name") for animation in asset.items("animations")]}
    if not context.report.failures:
        facts["triangles"] = sum(gltfio.mesh_triangles(asset, index) for index in range(context.counts["meshes"]))
        bounds = gltfio.scene_bounds(asset)
        facts["scene_bounds"] = {"min": list(bounds[0]), "max": list(bounds[1])} if bounds else None
        facts["animations"] = [{"name": clip["name"], "duration": clip["duration"], "channels": len(clip["channels"])}
                               for clip in gltfio.animation_clips(asset)]
    return facts


def validate(asset: gltfio.Asset, subject: str = "") -> asset_report.Report:
    """Run every structural rule over a loaded asset and return the report."""
    report = asset_report.Report(TOOL, subject)
    context = _Context(asset, report)
    _check_header(context)
    if any(failure["code"] == "property_type_invalid" for failure in report.failures):
        report.facts = {"counts": context.counts}
        return report
    _check_buffers(context)
    _check_accessors(context)
    _check_meshes(context)
    _check_materials(context)
    _check_nodes(context)
    _check_skins(context)
    _check_animations(context)
    report.facts = _facts(context)
    return report


def validate_file(path) -> asset_report.Report:
    """Load ``path`` and validate it; an unreadable or non-JSON file is a failure, not an exception."""
    report = asset_report.Report(TOOL, Path(path).name)
    try:
        asset = gltfio.load(path)
    except gltfio.GltfError as error:
        report.fail("file_unreadable" if error.reason in UNREADABLE_FILE_REASONS else "json_invalid",
                    Path(path).name, f"{error.reason} {error.detail}")
        return report
    return validate(asset, Path(path).name)


def run(argv: list) -> dict:
    parser = argparse.ArgumentParser(prog=TOOL, description=__doc__.split("\n\n")[0])
    parser.add_argument("asset", help="a .gltf or .glb file")
    arguments = parser.parse_args(argv)
    return validate_file(arguments.asset).as_dict()


def main(argv=None) -> int:
    return asset_report.emit(run(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    sys.exit(main())
