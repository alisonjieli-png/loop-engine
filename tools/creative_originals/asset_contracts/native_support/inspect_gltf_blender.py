"""What Blender itself reads from glTF files, written as JSON for the asset_contracts native verifier.

    blender --background --factory-startup --python inspect_gltf_blender.py -- OUTPUT.json FILE...

Each file is imported into an empty factory scene with the default importer settings. Facts are given in glTF
axes (Blender (x, y, z) is glTF (x, -z, y)) at frame 0, so they compare directly with the glTF file.
"""
import json
import sys
import traceback

import bpy
from mathutils import Vector

#: The Blender object types whose geometry and bones the facts describe.
MESH_OBJECT, ARMATURE_OBJECT = "MESH", "ARMATURE"


def gltf_axes(point):
    return [point[0], point[2], -point[1]]


def fcurves(action):
    if hasattr(action, "layers"):
        for layer in action.layers:
            for strip in layer.strips:
                for bag in getattr(strip, "channelbags", []):
                    yield from bag.fcurves
    elif hasattr(action, "fcurves"):
        yield from action.fcurves


def plain(value):
    """An ID property as plain JSON data."""
    if hasattr(value, "to_dict"):
        return {key: plain(item) for key, item in value.items()}
    if hasattr(value, "to_list"):
        return value.to_list()
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    return value


def inspect(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    facts = {"path": path}
    try:
        facts["result"] = sorted(bpy.ops.import_scene.gltf(filepath=path))
    except Exception as error:  # the importer's own refusal is a fact to record
        lines = [line.strip() for line in str(error).splitlines() if line.strip()]
        named = [line for line in lines if line.split(":", 1)[0].endswith(("Error", "Exception"))
                 and not line.startswith(("Error: Python", "RuntimeError: Error"))]
        facts["error"] = (named[-1] if named else lines[-1] if lines else type(error).__name__)[:300]
        facts["trace"] = traceback.format_exc()[-800:]
        return facts
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    scene.frame_set(0)
    objects = []
    bone_shapes = {bone.custom_shape.name for obj in bpy.data.objects if obj.type == ARMATURE_OBJECT
                   for bone in obj.pose.bones if bone.custom_shape is not None}
    for obj in bpy.data.objects:
        row = {"name": obj.name, "type": obj.type, "parent": obj.parent.name if obj.parent else None,
               "parent_bone": obj.parent_bone or None, "data": obj.data.name if obj.data else None,
               "origin": gltf_axes(obj.matrix_world.translation),
               "custom_properties": {key: plain(obj[key]) for key in obj.keys()},
               "matrix_world": [list(line) for line in obj.matrix_world]}
        if obj.type == MESH_OBJECT:
            corners = [gltf_axes(obj.matrix_world @ Vector(corner)) for corner in obj.bound_box]
            row["world_bounds"] = {"min": [min(c[i] for c in corners) for i in range(3)],
                                   "max": [max(c[i] for c in corners) for i in range(3)]}
            mesh = obj.data
            row["triangles"] = sum(len(polygon.vertices) - 2 for polygon in mesh.polygons)
            row["vertices"] = len(mesh.vertices)
            row["materials"] = [slot.material.name if slot.material else None for slot in obj.material_slots]
            row["shape_keys"] = [key.name for key in mesh.shape_keys.key_blocks] if mesh.shape_keys else []
            row["vertex_groups"] = [group.name for group in obj.vertex_groups]
            row["uv_layers"] = [layer.name for layer in mesh.uv_layers]
            row["modifiers"] = [modifier.type for modifier in obj.modifiers]
        row["bone_shape"] = obj.name in bone_shapes
        if obj.type == ARMATURE_OBJECT:
            row["bones"] = [{"name": bone.name, "parent": bone.parent.name if bone.parent else None,
                             "head": gltf_axes(obj.matrix_world @ bone.head_local)} for bone in obj.data.bones]
        objects.append(row)
    facts["objects"] = objects
    facts["materials"] = sorted(material.name for material in bpy.data.materials)
    facts["images"] = sorted(image.name for image in bpy.data.images)
    actions = []
    for action in bpy.data.actions:
        start, end = action.frame_range
        curves = list(fcurves(action))
        actions.append({"name": action.name, "frame_start": start, "frame_end": end, "seconds": (end - start) / fps,
                        "end_seconds": end / fps, "fcurves": len(curves),
                        "paths": sorted({curve.data_path for curve in curves}),
                        "keys": sum(len(curve.keyframe_points) for curve in curves),
                        "slots": [slot.identifier for slot in getattr(action, "slots", [])]})
    facts["actions"] = actions
    facts["fps"] = fps
    return facts


def main():
    arguments = sys.argv[sys.argv.index("--") + 1:]
    results = [inspect(path) for path in arguments[1:]]
    with open(arguments[0], "w", encoding="utf-8") as stream:
        json.dump(results, stream)


main()
