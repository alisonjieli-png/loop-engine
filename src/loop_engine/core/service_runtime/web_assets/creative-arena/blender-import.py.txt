"""Import an exported arena or character, save a .blend, and render one frame.

Run with an installed Blender:
    blender --background --python blender-import.py -- scene.glb output.blend frame.png
Input and output paths must be supplied explicitly. Existing outputs are refused.
"""
import argparse
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("project", type=Path)
    parser.add_argument("frame", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source = args.source.resolve(strict=True)
    if source.suffix.lower() != ".glb":
        parser.error("source must be a GLB file")
    if args.project.exists() or args.frame.exists():
        parser.error("choose new output paths; existing files are not overwritten")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world = bpy.data.worlds.new("Arena world")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (.08, .16, .18, 1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = .65
    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    if not meshes:
        raise ValueError("the GLB contains no mesh")
    corners = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    low = Vector(tuple(min(v[i] for v in corners) for i in range(3)))
    high = Vector(tuple(max(v[i] for v in corners) for i in range(3)))
    center = (low + high) / 2
    extent = max(high - low)
    camera_data = bpy.data.cameras.new("Render camera")
    camera = bpy.data.objects.new("Render camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = center + Vector((extent * .75, -extent * 1.05, extent * .8))
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.lens = 44
    scene.camera = camera
    light_data = bpy.data.lights.new("Render key", "AREA")
    light_data.energy = 1600 if extent > 5 else 450
    light_data.shape = "DISK"
    light_data.size = max(extent * .5, 3)
    light = bpy.data.objects.new("Render key", light_data)
    scene.collection.objects.link(light)
    light.location = center + Vector((extent * .3, -extent * .4, extent))
    light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    scene.frame_set(1)
    scene.render.filepath = str(args.frame.resolve())
    bpy.ops.wm.save_as_mainfile(filepath=str(args.project.resolve()))
    bpy.ops.render.render(write_still=True)
    print(f"Imported {len(meshes)} meshes and {len(bpy.data.actions)} animation actions.")


if __name__ == "__main__":
    main()
