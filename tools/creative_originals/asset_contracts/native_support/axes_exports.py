"""Export one door three ways from Blender: +Y up in metres, Z up in metres, and +Y up from a centimetre scene.

    blender --background --factory-startup --python axes_exports.py -- OUTPUT_FOLDER

The door is 0.9 m wide, 2.0 m tall (Blender Z) and 0.04 m deep. yup/door.gltf uses the exporter defaults;
zup/door.gltf turns +Y up off (export_yup=False); cm/door.gltf comes from a scene whose unit scale is 0.01 with the
door modelled 100 units tall, exported with the defaults.
"""
import sys
from pathlib import Path

import bpy
from mathutils import Matrix


def door(size: float) -> None:
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    obj = bpy.context.object
    obj.name = "Door"
    obj.data.name = "DoorMesh"
    obj.data.transform(Matrix.Translation((0.0, 0.0, 1.0 * size))
                       @ Matrix.Diagonal((0.9 * size, 0.04 * size, 2.0 * size, 1.0)))


def main():
    folder = Path(sys.argv[sys.argv.index("--") + 1])
    for name, size, options in (("yup", 1.0, {}), ("zup", 1.0, {"export_yup": False}), ("cm", 100.0, {})):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if name == "cm":
            bpy.context.scene.unit_settings.system = "METRIC"
            bpy.context.scene.unit_settings.scale_length = 0.01
        door(size)
        (folder / name).mkdir(parents=True, exist_ok=True)
        result = bpy.ops.export_scene.gltf(filepath=str(folder / name / "door.gltf"), export_format="GLTF_SEPARATE",
                                           **options)
        print("EXPORTED", name, sorted(result))


main()
