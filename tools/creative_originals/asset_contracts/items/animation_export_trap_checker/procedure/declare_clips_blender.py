"""Write the clips a .blend holds as animation_declaration/v1, before it is exported to glTF.

    blender --background SCENE.blend --python declare_clips_blender.py -- DECLARATION.json

Every action that has a user or a fake user becomes one declared clip: its name, its play length (the last frame of
its range at the scene frame rate) and its targets (object or bone name, and the glTF path each animated property
becomes). An action that no object currently plays is declared too: an exporter that writes only the playing
action drops it, and the checker reports that.
"""
import json
import re
import sys

import bpy

PATHS = {"location": "translation", "rotation_quaternion": "rotation", "rotation_euler": "rotation",
         "rotation_axis_angle": "rotation", "scale": "scale"}
BONE = re.compile(r'^pose\.bones\["(.+)"\]\.(\w+)$')
SHAPE = re.compile(r'^key_blocks\["(.+)"\]\.value$')
#: The ID type of an action slot that animates a shape key block (bpy.types.ActionSlot.target_id_type).
SHAPE_KEY_ID_TYPE = "KEY"


def channel_groups(action):
    """(slot or None, fcurves) pairs for layered actions (Blender 4.4 and later) and older actions."""
    layers = getattr(action, "layers", None)
    if layers:
        for layer in layers:
            for strip in layer.strips:
                for bag in getattr(strip, "channelbags", []):
                    yield bag.slot, list(bag.fcurves)
    elif hasattr(action, "fcurves"):
        yield None, list(action.fcurves)


def owner_name(slot):
    if slot is None:
        return None
    if slot.target_id_type == SHAPE_KEY_ID_TYPE:
        for obj in bpy.data.objects:
            keys = getattr(obj.data, "shape_keys", None)
            if keys is not None and keys.name == slot.name_display:
                return obj.name
    return slot.name_display


def targets(action):
    found = set()
    for slot, curves in channel_groups(action):
        owner = owner_name(slot)
        for curve in curves:
            bone, shape = BONE.match(curve.data_path), SHAPE.match(curve.data_path)
            if bone and bone.group(2) in PATHS:
                found.add((bone.group(1), PATHS[bone.group(2)]))
            elif shape and owner:
                found.add((owner, "weights"))
            elif curve.data_path in PATHS and owner:
                found.add((owner, PATHS[curve.data_path]))
    return sorted(found)


def main():
    output = sys.argv[sys.argv.index("--") + 1]
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    clips = []
    for action in sorted(bpy.data.actions, key=lambda item: item.name):
        if action.users == 0 and not action.use_fake_user:
            continue
        start, end = action.frame_range
        clips.append({"name": action.name, "duration_s": round(end / fps, 6), "frames": [start, end],
                      "targets": [{"node": node, "path": path} for node, path in targets(action)]})
    declaration = {"record_type": "animation_declaration/v1", "source": bpy.path.basename(bpy.data.filepath),
                   "fps": fps, "clips": clips}
    with open(output, "w", encoding="utf-8") as stream:
        json.dump(declaration, stream, indent=1, sort_keys=True)
    print("DECLARED", json.dumps([clip["name"] for clip in clips]))


main()
