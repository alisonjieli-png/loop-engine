"""Build the animation export trap scene: a framed door with two actions, only one of them playing.

    blender --background --factory-startup --python build_trap_scene.py -- OUTPUT.blend

Frame (root) and Door (child, origin on its hinge edge) are boxes in metres, Z up. Action Open turns the door from
0 to 90 degrees about Z over frames 0 to 24; action Close turns it back. Close is the playing action; Open is kept
by a fake user only, the state a scene is in after an artist animates Open and then starts a new action.
"""
import math
import sys

import bpy
from mathutils import Matrix


def box(name, size, offset):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name + "Mesh"
    obj.data.transform(Matrix.Translation(offset) @ Matrix.Diagonal((*size, 1.0)))
    return obj


def main():
    output = sys.argv[sys.argv.index("--") + 1]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    frame = box("Frame", (1.1, 0.15, 2.1), (0.0, 0.0, 1.05))
    door = box("Door", (0.9, 0.04, 2.0), (0.45, 0.0, 1.0))
    door.location = (-0.45, 0.0, 0.0)
    door.parent = frame
    door.animation_data_create()
    for name, start, end in (("Open", 0.0, 90.0), ("Close", 90.0, 0.0)):
        action = bpy.data.actions.new(name)
        door.animation_data.action = action
        door.rotation_euler = (0.0, 0.0, math.radians(start))
        door.keyframe_insert("rotation_euler", frame=0)
        door.rotation_euler = (0.0, 0.0, math.radians(end))
        door.keyframe_insert("rotation_euler", frame=24)
    bpy.data.actions["Open"].use_fake_user = True
    door.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=output)


main()
