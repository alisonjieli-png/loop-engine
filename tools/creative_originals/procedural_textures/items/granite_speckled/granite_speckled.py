"""Speckled granite: interlocking mineral grains, polished or flamed, tileable PBR maps (standard library only).

Grains are cells of a fine Voronoi diagram on the torus. A hash of each cell picks its mineral from the preset's
mix (feldspar, quartz, dark mica or hornblende), with its own shade; a soft gradient toward the cell centre suggests
cleavage faces. Larger feldspar crystals (phenocrysts) can float in the groundmass. The finish moves from polished
(flat, glossy, only hairline grain boundaries) to flamed (rough, with the hard quartz standing proud).
"""
from __future__ import annotations

import sys

import texkit as tk

IDENTITY = "granite_speckled"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.05, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "grains_across", "type": "int", "default": 40, "minimum": 12, "maximum": 128,
     "meaning": "Mineral grains across the tile (higher is finer)."},
    {"name": "feldspar", "type": "float", "default": 0.55, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of feldspar grains (the main colour)."},
    {"name": "dark_minerals", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 0.6,
     "meaning": "Share of dark mica and hornblende grains; the rest is quartz."},
    {"name": "phenocrysts", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Amount of large blocky feldspar crystals."},
    {"name": "finish", "type": "float", "default": 0.1, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Surface finish from polished (0) through honed to flamed (1)."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Polished grey granite: white feldspar, grey quartz, black mica.", "values": {}},
    "rose": {"description": "Polished pink granite with salmon feldspar and large crystals.",
             "values": {"feldspar": 0.6, "phenocrysts": 0.5, "grains_across": 34}},
    "black_galaxy": {"description": "Polished black stone with sparse bronze flecks.",
                     "values": {"feldspar": 0.06, "dark_minerals": 0.6, "phenocrysts": 0.0, "grains_across": 56}},
    "flamed_grey": {"description": "Flamed grey granite: rough, matte, quartz raised.",
                    "values": {"finish": 1.0, "grains_across": 48}},
    "blue_larvikite": {"description": "Blue-grey stone with large feldspar crystals and a soft sheen.",
                       "values": {"feldspar": 0.75, "dark_minerals": 0.1, "phenocrysts": 0.8, "grains_across": 26,
                                  "finish": 0.25}},
}
#: Feldspar shades, quartz shades and dark mineral shades per preset (sRGB).
PALETTES = {
    "default": (["#d9d6d0", "#c9c5bd", "#e6e3dd"], ["#8c8f93", "#a3a5a8", "#77797c"], ["#1c1c1e", "#2b2a29"]),
    "rose": (["#c48676", "#d29a89", "#b77565"], ["#9d9a98", "#8a8786", "#b1aeac"], ["#1e1b1a", "#2d2725"]),
    "black_galaxy": (["#8a6a3c", "#a07d48", "#6d5430"], ["#2a2a2c", "#333336", "#232325"], ["#0e0e10", "#151517"]),
    "flamed_grey": (["#d3d0ca", "#c3c0b9", "#dfdcd6"], ["#9a9da1", "#adb0b3", "#878a8e"], ["#2b2b2d", "#383735"]),
    "blue_larvikite": (["#5d6670", "#6c7682", "#4f5862"], ["#8c939a", "#7c838a", "#9aa1a8"],
                       ["#1a1c20", "#262a30"]),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The granite maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    feldspar_hex, quartz_hex, dark_hex = PALETTES[preset]
    shades = {0: [tk.hex_rgb(c) for c in feldspar_hex], 1: [tk.hex_rgb(c) for c in quartz_hex],
              2: [tk.hex_rgb(c) for c in dark_hex]}
    grains = p["grains_across"]
    fine = tk.voronoi(width, height, grains, grains, tk.hash_u32(seed, 1), jitter=0.95)
    crystal = [-1.0] * (width * height)
    rng = tk.Rng(seed, 2)
    for _ in range(int(40 * p["phenocrysts"])):
        size = rng.uniform(1.6, 3.2) / grains
        aspect = rng.uniform(0.35, 0.75)
        shade = rng.uniform(0.0, 0.35)
        for index, s, t in tk.ellipse_pixels(width, height, rng.random(), rng.random(), size, size,
                                             rng.uniform(0.0, 3.1416)):
            if abs(s) < 0.92 and abs(t) < aspect and abs(s) + abs(t) < 0.92 + aspect * 0.7:
                crystal[index] = shade + (0.1 if abs(t) < 0.06 else 0.0)
    cloud = tk.fbm(width, height, 3, 4, tk.hash_u32(seed, 3))
    grit = tk.white_noise(width, height, tk.hash_u32(seed, 4))
    feldspar, dark = p["feldspar"], p["dark_minerals"]
    minerals, picks = [], []
    for cell in range(grains * grains):
        roll = tk.hash_float(cell, seed, 5)
        kind = 2 if roll < dark else 0 if roll < dark + feldspar * (1.0 - dark) else 1
        minerals.append(kind)
        picks.append(tk.hash_float(cell, seed, 6))
    finish = p["finish"]
    pixel = grains / min(width, height)
    red, green, blue, heights, rough = [], [], [], [], []
    for index in range(width * height):
        cell = fine["cell"][index]
        kind, pick = minerals[cell], picks[cell]
        inside = crystal[index] >= 0.0
        if inside:
            kind, pick = 0, crystal[index]
        options = shades[kind]
        colour = options[min(int(pick * len(options)), len(options) - 1)]
        facet = 1.0 - 0.12 * min(1.0, fine["f1"][index]) if not inside else 1.02
        tone = facet + 0.05 * cloud[index] + 0.05 * (grit[index] - 0.5)
        boundary = 1.0 - tk.smoothstep(0.0, max(0.04, pixel * 0.6), fine["edge"][index]) if not inside else 0.0
        colour = [c * tone * (1.0 - 0.18 * boundary) for c in colour]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        relief = {0: 0.0, 1: 0.18, 2: -0.08}[kind] * finish
        heights.append(0.5 + relief - 0.06 * boundary * (0.3 + finish) + 0.08 * finish * (grit[index] - 0.5))
        rough.append(0.08 + 0.75 * finish + 0.06 * boundary + 0.08 * finish * grit[index]
                     - (0.03 if kind == 2 else 0.0))
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.004 + 0.01 * finish,
                     roughness=rough, ao_radius=0.01, ao_strength=0.6 + 0.6 * finish, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
