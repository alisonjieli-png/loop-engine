"""Build the Blender material of "Cobblestone paving from Voronoi cells": a Principled BSDF fed by the generated PNG maps.

Run inside Blender (checked with Blender 5.2): bpy is imported inside build_material only, so this file imports
anywhere. From Blender's Python console:

    import sys; sys.path.append("/path/to/this/package")
    import blender_material
    material = blender_material.build_material("/path/to/maps")
    bpy.context.object.data.materials.append(material)

From a shell: blender --python blender_material.py -- /path/to/maps
"""
from __future__ import annotations

import sys
from pathlib import Path

IDENTITY = "cobblestone_voronoi"
#: Map names, as the generator writes them into <identity>_<map>.png.
ALBEDO, NORMAL, ROUGHNESS, METALLIC, HEIGHT, AO, EMISSIVE = (
    "albedo", "normal", "roughness", "metallic", "height", "ao", "emissive")
#: The argument that separates Blender's own arguments from this script's (blender --python FILE -- MAPS).
ARGUMENT_SEPARATOR = "--"
#: The maps this material reads and the colour space Blender decodes each with.
COLOUR_SPACES = {"albedo": "sRGB", "normal": "Non-Color", "roughness": "Non-Color", "height": "Non-Color", "ao": "Non-Color"}
#: Normal strength, true displacement (scene units for a tile one unit wide), share of the occlusion map
#: multiplied into the base colour, emission strength, the alpha cut-off (0 keeps the material opaque) and
#: alpha_blend (1 feeds the albedo alpha straight into the BSDF alpha for soft transparency).
SETTINGS = {"normal_strength": 1.0, "displacement_scale": 0.03, "ao_mix": 0.4, "emission_strength": 0.0, "alpha_cutoff": 0.0, "alpha_blend": 0.0}
#: Principled BSDF inputs this material sets to constants.
BSDF_VALUES = {}


def _socket(sockets, identifier: str):
    for socket in sockets:
        if socket.identifier == identifier:
            return socket
    raise KeyError(identifier)


def map_paths(folder) -> dict:
    """The generated map files in ``folder`` keyed by map name; FileNotFoundError names any that are missing."""
    root = Path(folder)
    paths = {name: root / f"{IDENTITY}_{name}.png" for name in COLOUR_SPACES}
    missing = sorted(path.name for path in paths.values() if not path.is_file())
    if missing:
        raise FileNotFoundError(f"{root} lacks {', '.join(missing)}; generate the maps first")
    return paths


def build_material(folder, name: str = "", *, bpy_module=None):
    """Create a material from the maps in ``folder`` and return it; Blender appends .001 when the name exists."""
    if bpy_module is None:
        import bpy as bpy_module
    paths = map_paths(folder)
    material = bpy_module.data.materials.new(name or IDENTITY)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    for node in list(nodes):
        nodes.remove(node)
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (700, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (350, 0)
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    for socket, value in BSDF_VALUES.items():
        bsdf.inputs[socket].default_value = value
    images = {}
    for row, map_name in enumerate(COLOUR_SPACES):
        node = nodes.new("ShaderNodeTexImage")
        node.label = map_name
        node.location = (-650, 360 - 290 * row)
        node.image = bpy_module.data.images.load(str(paths[map_name]), check_existing=True)
        node.image.colorspace_settings.name = COLOUR_SPACES[map_name]
        images[map_name] = node
    colour = images[ALBEDO].outputs["Color"]
    if AO in images and SETTINGS["ao_mix"] > 0.0:
        mix = nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.location = (-150, 360)
        _socket(mix.inputs, "Factor_Float").default_value = SETTINGS["ao_mix"]
        links.new(colour, _socket(mix.inputs, "A_Color"))
        links.new(images[AO].outputs["Color"], _socket(mix.inputs, "B_Color"))
        colour = _socket(mix.outputs, "Result_Color")
    links.new(colour, bsdf.inputs["Base Color"])
    if SETTINGS["alpha_cutoff"] > 0.0:
        cut = nodes.new("ShaderNodeMath")
        cut.operation = "GREATER_THAN"
        cut.location = (-150, 100)
        links.new(images[ALBEDO].outputs["Alpha"], cut.inputs[0])
        cut.inputs[1].default_value = SETTINGS["alpha_cutoff"]
        links.new(cut.outputs["Value"], bsdf.inputs["Alpha"])
    elif SETTINGS["alpha_blend"] > 0.0:
        links.new(images[ALBEDO].outputs["Alpha"], bsdf.inputs["Alpha"])
    for map_name, socket in ((ROUGHNESS, "Roughness"), (METALLIC, "Metallic")):
        if map_name in images:
            links.new(images[map_name].outputs["Color"], bsdf.inputs[socket])
    normal = nodes.new("ShaderNodeNormalMap")
    normal.location = (-150, -300)
    normal.inputs["Strength"].default_value = SETTINGS["normal_strength"]
    links.new(images[NORMAL].outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    displacement = nodes.new("ShaderNodeDisplacement")
    displacement.location = (350, -520)
    displacement.inputs["Midlevel"].default_value = 0.5
    displacement.inputs["Scale"].default_value = SETTINGS["displacement_scale"]
    links.new(images[HEIGHT].outputs["Color"], displacement.inputs["Height"])
    links.new(displacement.outputs["Displacement"], output.inputs["Displacement"])
    material.displacement_method = "DISPLACEMENT"
    if EMISSIVE in images:
        links.new(images[EMISSIVE].outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = SETTINGS["emission_strength"]
    return material


if __name__ == "__main__":
    arguments = sys.argv[sys.argv.index(ARGUMENT_SEPARATOR) + 1:] if ARGUMENT_SEPARATOR in sys.argv else []
    if not arguments:
        raise SystemExit("usage: blender --python blender_material.py -- /path/to/maps")
    print(build_material(arguments[0]).name)
