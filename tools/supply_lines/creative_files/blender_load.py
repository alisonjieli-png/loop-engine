"""Load a fetched variant of this Baltor creative package into the open Blender scene.

Fetch a variant first (python creative_fetch.py fetch VARIANT FOLDER), then run this file inside Blender:

    blender --python blender_load.py -- FOLDER [VARIANT]
    blender --background --python blender_load.py -- FOLDER [VARIANT]      no window, for a script or a check

or from Blender's Python console, with this package folder on sys.path:

    import blender_load
    blender_load.load("FOLDER", "VARIANT")

An HDRI becomes the world's environment light. A model is imported (glTF, FBX, USD or OBJ) or appended from its
.blend file. A texture or material set becomes a material on a new plane: the material of the package's own .blend
file when the variant has one, otherwise a Principled BSDF built from the colour, roughness, metalness and normal
maps (Blender reads normal maps in the OpenGL convention). The bpy module is imported only when a function runs,
so this file can be read and tested outside Blender.
"""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import sys

MANIFEST = Path(__file__).resolve().parent / "creative.json"
#: The importer for each model file suffix (Blender 4 operators).
MODEL_IMPORTERS = {".gltf": ("import_scene", "gltf"), ".glb": ("import_scene", "gltf"),
                   ".fbx": ("import_scene", "fbx"), ".obj": ("wm", "obj_import"), ".usd": ("wm", "usd_import"),
                   ".usdc": ("wm", "usd_import"), ".usda": ("wm", "usd_import"), ".usdz": ("wm", "usd_import")}
#: The Principled BSDF input each map feeds, and whether the map holds colour or plain data.
MAP_INPUTS = {"diffuse": ("Base Color", False), "roughness": ("Roughness", True), "metalness": ("Metallic", True)}
DEFAULT_PLANE_METRES = 2.0


def read_manifest(path=None) -> dict:
    """The package's creative.json."""
    return json.loads(Path(path or MANIFEST).read_text(encoding="utf-8"))


def chosen_variant(manifest: dict, identifier: "str | None" = None) -> dict:
    """One variant by id, or the default; a ValueError names the variants when the id is not one of them."""
    wanted = identifier or manifest.get("default_variant")
    for row in manifest.get("variants") or ():
        if row.get("id") == wanted:
            return row
    raise ValueError(f"{wanted!r} is not a variant of this package: "
                     f"{', '.join(row['id'] for row in manifest.get('variants') or ())}")


def files_by_role(folder, variant: dict) -> dict:
    """{role: path} of the variant's fetched files (an archive's members in place of the archive); refuse a
    missing file with the fetch command that brings it."""
    found = {}
    for item in variant["files"]:
        for row in (item.get("members") or []) if item.get("unpack") else [item]:
            role = row.get("role") or ""
            if role and role not in found:
                found[role] = Path(folder).joinpath(*PurePosixPath(row["path"]).parts)
    missing = [str(path) for path in found.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"fetch the variant first (python creative_fetch.py fetch {variant['id']} "
                                f"{folder}); missing {missing[0]}")
    return found


def environment(path, strength: float = 1.0):
    """Light the scene with an equirectangular HDRI: the world's Environment Texture into a Background."""
    import bpy
    scene = bpy.context.scene
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    nodes.clear()
    texture = nodes.new("ShaderNodeTexEnvironment")
    texture.image = bpy.data.images.load(str(path), check_existing=True)
    background = nodes.new("ShaderNodeBackground")
    background.inputs["Strength"].default_value = strength
    output = nodes.new("ShaderNodeOutputWorld")
    links.new(texture.outputs["Color"], background.inputs["Color"])
    links.new(background.outputs["Background"], output.inputs["Surface"])
    return world


def import_model(path) -> list:
    """Import a model file into the scene and return the objects it brought."""
    import bpy
    path = Path(path)
    if path.suffix.lower() == ".blend":
        with bpy.data.libraries.load(str(path), link=False) as (source, target):
            target.objects = list(source.objects)
        objects = [item for item in target.objects if item is not None]
        for item in objects:
            bpy.context.scene.collection.objects.link(item)
        return objects
    if path.suffix.lower() not in MODEL_IMPORTERS:
        raise ValueError(f"Blender has no importer here for {path.suffix} files")
    group, operator = MODEL_IMPORTERS[path.suffix.lower()]
    getattr(getattr(bpy.ops, group), operator)(filepath=str(path))
    return list(bpy.context.selected_objects)


def material_from_blend(path):
    """The first material of a .blend file, appended to this file, or None when it holds none."""
    import bpy
    with bpy.data.libraries.load(str(path), link=False) as (source, target):
        target.materials = list(source.materials)
    materials = [item for item in target.materials if item is not None]
    return materials[0] if materials else None


def material_from_maps(files: dict, name: str):
    """A Principled BSDF material from the colour, roughness, metalness and OpenGL normal maps present."""
    import bpy
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes.get("Principled BSDF")

    def image(path, plain_data):
        node = nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(str(path), check_existing=True)
        if plain_data:
            node.image.colorspace_settings.name = "Non-Color"
        return node

    for role, (socket, plain_data) in MAP_INPUTS.items():
        if role in files:
            links.new(image(files[role], plain_data).outputs["Color"], shader.inputs[socket])
    if "normal_gl" in files:
        normal = nodes.new("ShaderNodeNormalMap")
        links.new(image(files["normal_gl"], True).outputs["Color"], normal.inputs["Color"])
        links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    return material


def material_plane(files: dict, name: str, size_metres: float = DEFAULT_PLANE_METRES):
    """A new plane of the given size carrying the package's material."""
    import bpy
    material = material_from_blend(files["blend"]) if "blend" in files else None
    if material is None:
        material = material_from_maps(files, name)
    bpy.ops.mesh.primitive_plane_add(size=size_metres)
    plane = bpy.context.active_object
    plane.data.materials.append(material)
    return plane


def plane_size(manifest: dict) -> float:
    """The asset's own width in metres when the manifest records one (in millimetres), else two metres."""
    dimensions = (manifest.get("asset") or {}).get("dimensions_mm") or []
    width = dimensions[0] if dimensions and isinstance(dimensions[0], (int, float)) else 0
    return width / 1000 if width > 0 else DEFAULT_PLANE_METRES


def load(folder, variant: "str | None" = None, *, manifest: "dict | None" = None):
    """Load one fetched variant into the open scene: the world for an HDRI, objects for a model, a plane with
    the material for a texture or material set."""
    manifest = manifest if manifest is not None else read_manifest()
    chosen = chosen_variant(manifest, variant)
    files = files_by_role(folder, chosen)
    kind = manifest["asset"]["type"]
    if kind == "hdri":
        return environment(files["environment"])
    if kind == "model":
        return import_model(files["model"])
    if kind in ("texture", "material"):
        return material_plane(files, manifest["asset"].get("name") or manifest["job"]["identity"],
                              plane_size(manifest))
    raise ValueError(f"Blender loading is not defined for a {kind}")


def arguments(argv) -> tuple:
    """(folder, variant) from the words after Blender's ``--`` separator."""
    words = argv[argv.index("--") + 1:] if "--" in argv else []
    return (words[0] if words else "."), (words[1] if len(words) > 1 else None)


if __name__ == "__main__":
    load(*arguments(sys.argv))
