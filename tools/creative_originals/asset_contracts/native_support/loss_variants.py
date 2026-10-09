"""Apply one clean-up step to the open loss scene and export it to glTF.

    blender --background SCENE.blend --python loss_variants.py -- MODE OUTPUT.gltf

MODE reference: export with custom properties (export_extras on). default: export with the exporter defaults.
origin: set the Door origin to its geometry, then export with custom properties. join: join the Door into the Frame,
then export with custom properties.
"""
import sys

import bpy

#: The modes that change the scene or the export settings; reference exports the scene as built.
ORIGIN_MODE, JOIN_MODE, DEFAULT_MODE = "origin", "join", "default"


def main():
    mode, output = sys.argv[sys.argv.index("--") + 1:][:2]
    door, frame = bpy.data.objects["Door"], bpy.data.objects["Frame"]
    for obj in bpy.data.objects:
        obj.select_set(False)
    if mode == ORIGIN_MODE:
        door.select_set(True)
        bpy.context.view_layer.objects.active = door
        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY")
    elif mode == JOIN_MODE:
        door.select_set(True)
        frame.select_set(True)
        bpy.context.view_layer.objects.active = frame
        bpy.ops.object.join()
    options = {} if mode == DEFAULT_MODE else {"export_extras": True}
    print("EXPORTED", mode, sorted(bpy.ops.export_scene.gltf(filepath=output, export_format="GLTF_SEPARATE", **options)))


main()
