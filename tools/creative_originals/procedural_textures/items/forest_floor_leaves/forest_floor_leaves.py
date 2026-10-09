"""Forest floor: fallen leaves, twigs and soil, tileable PBR maps from the standard library only.

Leaves are stamped one after another with a z-buffer, each lying a little higher than the leaves under it, so the
litter stacks. A leaf outline is ovate (widest near the stem) or lobed like oak, with a midrib and side veins drawn
from its local coordinates, and a curl that lifts its edges. Each leaf takes an autumn colour and a decay level;
twigs are thin capsules and the soil between is dark and crumbly. Everything wraps around the tile edges.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "forest_floor_leaves"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.85]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.35, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "leaves", "type": "int", "default": 190, "minimum": 20, "maximum": 1500,
     "meaning": "Number of leaves on the tile."},
    {"name": "leaf_size", "type": "float", "default": 0.065, "minimum": 0.015, "maximum": 0.15,
     "meaning": "Average leaf length (half extent) in texture units."},
    {"name": "lobed", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of lobed (oak-like) leaves; the rest are ovate."},
    {"name": "curl", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How much leaf edges lift."},
    {"name": "decay", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of dark, decaying leaves."},
    {"name": "twigs", "type": "int", "default": 10, "minimum": 0, "maximum": 60,
     "meaning": "Number of twigs on the tile."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Autumn litter of yellow, orange and brown leaves over soil.", "values": {}},
    "oak_brown": {"description": "Dry brown oak leaves, mostly lobed.",
                  "values": {"lobed": 0.9, "decay": 0.5, "leaves": 170, "leaf_size": 0.075}},
    "wet_dark": {"description": "Wet, dark, decaying leaves pressed flat.",
                 "values": {"decay": 0.9, "curl": 0.15, "leaves": 260}},
    "maple_red": {"description": "Fresh red and orange leaves, sparse over soil.",
                  "values": {"leaves": 110, "decay": 0.05, "leaf_size": 0.065, "twigs": 6, "lobed": 0.0}},
}
#: Leaf colours, decayed leaf colour, soil colour, twig colour and leaf roughness per preset (sRGB).
PALETTES = {
    "default": (["#c99a2e", "#d37a26", "#a3542a", "#8c6a34", "#b8862c"], "#4a3524", "#2d241b", "#5a4632", 0.72),
    "oak_brown": (["#8a6234", "#9e7140", "#76522c", "#a88452"], "#4b3626", "#2c231a", "#574330", 0.8),
    "wet_dark": (["#6b4a2a", "#5b3c24", "#7a5531", "#4c3422"], "#2c2018", "#1d1712", "#3d2e22", 0.45),
    "maple_red": (["#c2321f", "#d9541f", "#e08a26", "#a8261b"], "#5a2a1d", "#30261c", "#5d4733", 0.65),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The forest floor maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    leaf_hex, decayed_hex, soil_hex, twig_hex, leaf_rough = PALETTES[preset]
    leaf_colours = [tk.hex_rgb(code) for code in leaf_hex]
    decayed, soil_rgb, twig_rgb = tk.hex_rgb(decayed_hex), tk.hex_rgb(soil_hex), tk.hex_rgb(twig_hex)
    count = width * height
    crumbs = tk.fbm(width, height, 24, 3, tk.hash_u32(seed, 1))
    grit = tk.white_noise(width, height, tk.hash_u32(seed, 2))
    level = [0.05 + 0.04 * c for c in crumbs]
    red = [soil_rgb[0] * (0.85 + 0.3 * g) for g in grit]
    green = [soil_rgb[1] * (0.85 + 0.3 * g) for g in grit]
    blue = [soil_rgb[2] * (0.85 + 0.3 * g) for g in grit]
    rough = [0.95] * count
    rng = tk.Rng(seed, 3)
    number = p["leaves"]
    layer_step = 0.5 / number
    for leaf in range(number):
        cu, cv = rng.random(), rng.random()
        size = p["leaf_size"] * rng.uniform(0.6, 1.4)
        breadth = rng.uniform(0.35, 0.6)
        lobed = rng.random() < p["lobed"]
        rot = rng.uniform(0.0, math.tau)
        colour = leaf_colours[rng.integer(0, len(leaf_colours) - 1)]
        rot_amount = rng.random() < p["decay"]
        if rot_amount:
            colour = [c + (d - c) * rng.uniform(0.5, 0.9) for c, d in zip(colour, decayed)]
        shade = rng.uniform(0.85, 1.12)
        curl = p["curl"] * rng.uniform(0.3, 1.0)
        base = 0.15 + leaf * layer_step
        stem_u, stem_v = cu - size * math.cos(rot), cv - size * math.sin(rot)
        stem_length = size * rng.uniform(0.15, 0.35)
        for index, d, t in tk.segment_pixels(width, height, stem_u, stem_v, stem_u - stem_length * math.cos(rot),
                                             stem_v - stem_length * math.sin(rot), max(0.0012, size * 0.03)):
            if base + 0.02 > level[index]:
                level[index] = base + 0.02
                red[index], green[index], blue[index] = [c * 0.7 for c in colour]
                rough[index] = leaf_rough
        for index, s, t in tk.ellipse_pixels(width, height, cu, cv, size, size * breadth, rot):
            if abs(s) >= 1.0:
                continue
            profile = (1.0 - s * s) ** 0.7 * (1.0 + 0.25 * s)
            if lobed:
                profile *= 0.72 + 0.28 * abs(math.cos(3.5 * math.pi * (s + 1.0)))
            if abs(t) >= profile:
                continue
            across = abs(t) / profile
            surface = base + 0.06 * curl * across * across + 0.02 * (1.0 - across)
            if surface <= level[index]:
                continue
            level[index] = surface
            midrib = 1.0 - tk.smoothstep(0.0, 0.07, abs(t))
            veins = 1.0 - tk.smoothstep(0.0, 0.08, abs(((s + 1.0) * 3.0 - across * 1.6) % 1.0 - 0.5) * 0.4)
            rim = across ** 6
            tone = shade * (1.0 - 0.3 * midrib - 0.12 * veins * (1.0 - midrib) - 0.35 * rim) \
                * (0.92 + 0.12 * grit[index])
            red[index], green[index], blue[index] = [c * tone for c in colour]
            rough[index] = leaf_rough + 0.1 * veins
    for _ in range(p["twigs"]):
        u, v = rng.random(), rng.random()
        angle = rng.uniform(0.0, math.tau)
        length = rng.uniform(0.06, 0.2)
        radius = rng.uniform(0.002, 0.005)
        lift = 0.75 + rng.uniform(0.0, 0.2)
        for index, d, t in tk.segment_pixels(width, height, u, v, u + length * math.cos(angle),
                                             v + length * math.sin(angle), radius):
            surface = lift + 0.05 * math.sqrt(max(0.0, 1.0 - d * d))
            if surface > level[index]:
                level[index] = surface
                tone = 0.7 + 0.35 * math.sqrt(max(0.0, 1.0 - d * d))
                red[index], green[index], blue[index] = [c * tone for c in twig_rgb]
                rough[index] = 0.85
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=level, depth=0.02, roughness=rough,
                     ao_radius=0.02, ao_strength=1.4, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
