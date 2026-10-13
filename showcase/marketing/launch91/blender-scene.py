"""Import the original embedded GLB, save an editable Blender scene, or reopen it.

Run only for this recipe's trusted generated scene. A separate process loads
factory settings, writes new output paths and never reads customer projects.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import bpy
from mathutils import Vector


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_glb(path):
    body = path.read_bytes()
    if not 20 < len(body) <= 8 * 1024 * 1024:
        raise ValueError("GLB byte bound")
    magic, version, length, json_length, kind = struct.unpack("<5I", body[:20])
    if (magic, version, length, kind) != (0x46546C67, 2, len(body), 0x4E4F534A):
        raise ValueError("GLB header")
    document = json.loads(body[20:20 + json_length])
    if len(document.get("nodes", [])) > 512:
        raise ValueError("GLB object bound")
    for item in (*document.get("buffers", []), *document.get("images", [])):
        if item.get("uri") and not item["uri"].startswith("data:"):
            raise ValueError("External resource refused")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "reopen"))
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source = args.source.resolve(strict=True)
    output, report = args.output.absolute(), args.report.absolute()
    preview = report.with_suffix(".png")
    if any(path.exists() for path in (output, report, preview)):
        raise ValueError("Use new output, report and preview paths")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if args.mode == "build":
        validate_glb(source)
        bpy.ops.import_scene.gltf(filepath=str(source))
        root = next(item for item in bpy.context.scene.objects if item.name.startswith("Baltor_workflow_sculpture"))
        root.rotation_euler.z = 0
        root.keyframe_insert(data_path="rotation_euler", frame=1)
        root.rotation_euler.z = 1.05
        root.keyframe_insert(data_path="rotation_euler", frame=73)
        camera_data = bpy.data.cameras.new("Consumer orbit camera")
        camera = bpy.data.objects.new("Consumer orbit camera", camera_data)
        bpy.context.collection.objects.link(camera)
        camera.location = (10, -14, 9)
        camera.rotation_euler = (Vector((0, 0, 0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
        bpy.context.scene.camera = camera
        camera.data.type = "ORTHO"
        camera.data.ortho_scale = 13
    else:
        if source.suffix != ".blend":
            raise ValueError("Expected the generated Blender project")
        bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 73
    scene.render.fps = 24
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = 960, 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.background_type = "WORLD"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Original dark studio")
    scene.world.color = (.045, .065, .08)
    bpy.ops.file.pack_all()
    meshes = [item for item in scene.objects if item.type == "MESH"]
    root = next(item for item in scene.objects if item.name.startswith("Baltor_workflow_sculpture"))
    scene.frame_set(1)
    first = tuple(root.rotation_euler)
    scene.frame_set(49)
    later = tuple(root.rotation_euler)
    checks = {"native_meshes": len(meshes) >= 10, "actual_animation": first != later,
              "camera": scene.camera is not None, "no_external_images": all(image.source != "FILE" or image.packed_file for image in bpy.data.images)}
    if not all(checks.values()):
        raise ValueError("Native scene qualification failed")
    scene.render.filepath = str(preview)
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), check_existing=True)
    result = {"record_type": "launch_motion_native_scene_check/v1", "mode": args.mode,
              "engine": bpy.app.version_string, "source_sha256": digest(source),
              "output_sha256": digest(output), "preview_sha256": digest(preview),
              "checks": {key: bool(value) for key, value in checks.items()}, "passed": True,
              "meshes": len(meshes), "frames": [1, 73],
              "scope": "Editable original component sculpture with an added native orbit animation. This is a remix component, not an exact reconstruction of the full HTML video composition."}
    with report.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
