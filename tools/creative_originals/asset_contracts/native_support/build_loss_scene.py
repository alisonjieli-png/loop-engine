"""Build the articulation loss scene: a framed door whose joint record lives in a custom property.

    blender --background --factory-startup --python build_loss_scene.py -- OUTPUT.blend

Frame (root) and Door (child, origin on the hinge edge) are boxes in metres, Z up. Door["joint"] holds the joint
record the glTF export should carry in the node's extras.
"""
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
    door["joint"] = {"name": "door_hinge", "type": "hinge", "axis": [0.0, 1.0, 0.0], "pivot": [0.0, 0.0, 0.0],
                     "limits": [0.0, 95.0]}
    bpy.ops.wm.save_as_mainfile(filepath=output)


main()
