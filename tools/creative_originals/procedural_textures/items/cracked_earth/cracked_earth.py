"""Cracked earth: dried mud plates, curled edges and salt-flat ridges, tileable PBR maps (standard library only).

Plates are cells of a Voronoi diagram on the torus. With ``edge_relief`` below zero the cell borders open as cracks
whose width wanders with noise, and plate edges curl up as mud shrinks; a finer Voronoi adds shallow secondary
cracks inside the plates. With ``edge_relief`` above zero the borders rise into ridges instead, as salt crust does
on a dry lake. Dust, grit and the occasional pebble finish the surface.
"""
from __future__ import annotations

import sys

import texkit as tk

IDENTITY = "cracked_earth"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.03, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.3, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "plates_across", "type": "int", "default": 6, "minimum": 2, "maximum": 20,
     "meaning": "Plates across the tile."},
    {"name": "crack_width", "type": "float", "default": 0.07, "minimum": 0.01, "maximum": 0.25,
     "meaning": "Crack (or ridge) width in plate widths."},
    {"name": "edge_relief", "type": "float", "default": -0.8, "minimum": -1.0, "maximum": 1.0,
     "meaning": "Border profile: negative opens cracks with curled plate edges, positive raises salt ridges."},
    {"name": "curl", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How far plate edges lift beside the cracks."},
    {"name": "secondary_cracks", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Shallow finer cracks inside the plates."},
    {"name": "moisture", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Damp darkening and lower roughness in patches."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Dry tan clay plates with open cracks and curled edges.", "values": {}},
    "dark_mud": {"description": "Dark drying mud with narrow cracks and damp patches.",
                 "values": {"plates_across": 9, "crack_width": 0.04, "curl": 0.3, "moisture": 0.6}},
    "desert_pan": {"description": "Pale desert pan with wide cracks and many small plates.",
                   "values": {"plates_across": 12, "crack_width": 0.1, "curl": 0.7, "secondary_cracks": 0.8}},
    "salt_flat": {"description": "White salt crust in polygons with raised ridges.",
                  "values": {"plates_across": 5, "edge_relief": 0.8, "crack_width": 0.1, "curl": 0.0,
                             "secondary_cracks": 0.3}},
}
#: Plate colour, crack interior colour and dust colour per preset (sRGB).
PALETTES = {
    "default": ("#b48d63", "#4a3626", "#c9a57c"),
    "dark_mud": ("#6b5640", "#2b2118", "#7f6a52"),
    "desert_pan": ("#d2b48f", "#6e5038", "#dfc7a6"),
    "salt_flat": ("#e9e6df", "#b8b2a6", "#f5f3ef"),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The cracked earth maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    plate_rgb, crack_rgb, dust_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    plates = p["plates_across"]
    main = tk.voronoi(width, height, plates, plates, tk.hash_u32(seed, 1), jitter=0.95)
    finer = tk.voronoi(width, height, plates * 3, plates * 3, tk.hash_u32(seed, 2), jitter=0.95)["edge"]
    wobble = tk.fbm(width, height, plates * 4, 3, tk.hash_u32(seed, 3))
    dust = tk.fbm(width, height, 16, 3, tk.hash_u32(seed, 4))
    damp = tk.fbm(width, height, 3, 4, tk.hash_u32(seed, 5))
    grit = tk.white_noise(width, height, tk.hash_u32(seed, 6))
    relief, curl = p["edge_relief"], p["curl"]
    half = p["crack_width"] * 0.5
    pixel = plates / min(width, height)
    secondary, moisture = p["secondary_cracks"], p["moisture"]
    red, green, blue, heights, rough = [], [], [], [], []
    for index in range(width * height):
        cell = main["cell"][index]
        local = half * (0.6 + 0.8 * (wobble[index] + 0.5))
        inside = main["edge"][index] - local
        border = 1.0 - tk.smoothstep(-pixel, pixel, inside)
        near = 1.0 - tk.smoothstep(0.0, 0.12, max(inside, 0.0))
        fine = secondary * (1.0 - tk.smoothstep(0.0, 0.025, finer[index])) * (1.0 - border)
        plate_level = 0.62 + 0.04 * tk.hash_float(cell, seed, 7) + 0.03 * dust[index]
        if relief < 0.0:
            plate_level += 0.18 * curl * near
            level = plate_level + (0.1 - plate_level) * border * -relief - 0.12 * fine
        else:
            level = plate_level + 0.3 * relief * (1.0 - tk.smoothstep(0.0, local * 1.5 + 0.02, main["edge"][index]))
            level -= 0.05 * fine
        heights.append(level)
        wet = moisture * tk.smoothstep(0.0, 0.3, damp[index])
        tone = 0.92 + 0.12 * tk.hash_float(cell, seed, 8) + 0.08 * (grit[index] - 0.5)
        colour = [d + (pl - d) * (0.6 + 0.4 * tk.smoothstep(-0.2, 0.3, dust[index])) for pl, d in
                  zip(plate_rgb, dust_rgb)]
        colour = [c * tone * (1.0 - 0.35 * wet) for c in colour]
        dark_amount = border if relief < 0.0 else 0.0
        colour = [c + (k - c) * max(dark_amount, 0.6 * fine) for c, k in zip(colour, crack_rgb)]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        rough.append(0.92 - 0.35 * wet + 0.05 * grit[index] - 0.04 * border)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.025, roughness=rough,
                     ao_radius=0.02, ao_strength=1.2, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
