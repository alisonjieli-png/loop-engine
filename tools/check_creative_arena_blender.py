"""Reopen an exported .blend in a fresh Blender Python process and inspect it.

Run with Blender's Python module installed, or Blender --background --python
this_file.py -- PROJECT.blend NEW_REPORT.json. No model or network is used.
"""
import argparse
import json
from pathlib import Path
import sys

import bpy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("report", type=Path)
    arguments = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    args = parser.parse_args(arguments)
    if args.report.exists():
        parser.error("choose a new report path")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.open_mainfile(filepath=str(args.project.resolve(strict=True)))
    rigs = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    missing_images = [image.name for image in bpy.data.images
                      if image.source == "FILE" and not image.packed_file
                      and not Path(bpy.path.abspath(image.filepath)).is_file()]
    def pose(frame):
        bpy.context.scene.frame_set(frame)
        return [round(value, 6) for rig in rigs for bone in rig.pose.bones
                for row in bone.matrix for value in row]
    start, later = pose(1), pose(12)
    checks = {"scene_meshes": len(meshes) > 0, "hero_and_enemies": len(rigs) >= 4,
              "animation_actions": len(bpy.data.actions) >= 16,
              "animated_pose_changes": start != later,
              "no_missing_images": not missing_images, "render_camera": bpy.context.scene.camera is not None}
    report = {"record_type": "creative_arena_blender_reopen/v1", "blender": bpy.app.version_string,
              "checks": checks, "meshes": len(meshes), "rigs": len(rigs),
              "actions": len(bpy.data.actions), "missing_images": missing_images,
              "passed": all(checks.values())}
    with args.report.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
