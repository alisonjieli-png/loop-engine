"""Put every action on its own NLA track of the object it animates, so a glTF export writes each as a clip.

    blender --background SCENE.blend --python push_actions_to_nla.py -- OUTPUT.blend

For each action with a slot for an object (or a shape key block), a track named after the action is added with one
strip that plays it, unless a strip already plays it. The active action of every object that now has tracks is
cleared, so the exporter does not also write the playing pose as a separate clip. The result is saved to OUTPUT.blend.
"""
import sys

import bpy

#: The ID types of the action slots pushed to tracks: an object, and a shape key block
#: (bpy.types.ActionSlot.target_id_type).
OBJECT_ID_TYPE, SHAPE_KEY_ID_TYPE = "OBJECT", "KEY"


def owners(action):
    found = []
    for slot in getattr(action, "slots", []):
        if slot.target_id_type == OBJECT_ID_TYPE and slot.name_display in bpy.data.objects:
            found.append(bpy.data.objects[slot.name_display])
        elif slot.target_id_type == SHAPE_KEY_ID_TYPE and slot.name_display in bpy.data.shape_keys:
            found.append(bpy.data.shape_keys[slot.name_display])
    return found


def main():
    output = sys.argv[sys.argv.index("--") + 1]
    pushed = []
    for action in sorted(bpy.data.actions, key=lambda item: item.name):
        for owner in owners(action):
            data = owner.animation_data or owner.animation_data_create()
            if any(strip.action == action for track in data.nla_tracks for strip in track.strips):
                continue
            track = data.nla_tracks.new()
            track.name = action.name
            track.strips.new(action.name, int(action.frame_range[0]), action)
            pushed.append([owner.name, action.name])
    for owner in list(bpy.data.objects) + list(bpy.data.shape_keys):
        if owner.animation_data is not None and len(owner.animation_data.nla_tracks):
            owner.animation_data.action = None
    bpy.ops.wm.save_as_mainfile(filepath=output)
    print("PUSHED", pushed)


main()
