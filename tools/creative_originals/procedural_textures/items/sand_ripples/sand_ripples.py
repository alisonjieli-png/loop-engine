"""Wind and water sand ripples, with optional dune swells: tileable PBR maps from the standard library only.

Ripples follow a phase that advances a whole number of cycles across the tile along an integer direction, so the
pattern repeats; smooth noise bends the phase so crests curve, fork and merge. The profile is asymmetric: a long
gentle stoss slope and a short steep lee face, as wind or current builds them. Heavy dark minerals collect in the
troughs, crests are paler, and a dune swell of much lower frequency can lie under the ripples. Wet sand is darker
and smoother.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "sand_ripples"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.05, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.2, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "ripples", "type": "int", "default": 12, "minimum": 2, "maximum": 48,
     "meaning": "Ripple crests across the tile along the ripple direction."},
    {"name": "direction", "type": "int", "default": 0, "minimum": 0, "maximum": 3,
     "meaning": "Crest direction: 0 vertical crests, 1 horizontal crests, 2 and 3 the two diagonals."},
    {"name": "meander", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How much crests bend, fork and merge."},
    {"name": "asymmetry", "type": "float", "default": 0.7, "minimum": 0.0, "maximum": 0.95,
     "meaning": "Share of each ripple taken by the gentle slope (0.5 symmetric, higher is wind-built)."},
    {"name": "dune_swell", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Large low dunes under the ripples."},
    {"name": "trough_minerals", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Dark heavy minerals collected in the troughs."},
    {"name": "wetness", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Wet sand: darker and smoother."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Dry beach sand with wind ripples.", "values": {}},
    "tidal_wet": {"description": "Wet tidal flat with symmetric ripples and dark troughs.",
                  "values": {"wetness": 0.8, "asymmetry": 0.5, "ripples": 9, "trough_minerals": 0.8,
                             "meander": 0.7}},
    "desert_dunes": {"description": "Orange desert sand with dune swells and fine ripples.",
                     "values": {"dune_swell": 0.9, "ripples": 24, "direction": 2, "meander": 0.4,
                                "trough_minerals": 0.2}},
    "white_gypsum": {"description": "White gypsum sand with long straight ripples.",
                     "values": {"meander": 0.2, "ripples": 16, "direction": 1, "trough_minerals": 0.1}},
}
#: Crest colour, trough colour and wet colour per preset (sRGB).
PALETTES = {
    "default": ("#dcc59a", "#b89e74", "#8d7652"),
    "tidal_wet": ("#c7b38c", "#8e7c5e", "#6f5f45"),
    "desert_dunes": ("#e0a065", "#c07c45", "#8a5530"),
    "white_gypsum": ("#f1eee7", "#d9d4c9", "#b6b0a3"),
}
DIRECTIONS = {0: (1, 0), 1: (0, 1), 2: (1, 1), 3: (1, -1)}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The sand maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    crest_rgb, trough_rgb, wet_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    a, b = DIRECTIONS[p["direction"]]
    count = p["ripples"]
    bend = tk.fbm(width, height, 3, 4, tk.hash_u32(seed, 1))
    fork = tk.fbm(width, height, 7, 3, tk.hash_u32(seed, 2))
    swell = tk.fbm(width, height, 2, 3, tk.hash_u32(seed, 3))
    grain = tk.white_noise(width, height, tk.hash_u32(seed, 4))
    speckle = tk.fbm(width, height, 64, 2, tk.hash_u32(seed, 5))
    meander, rise = p["meander"], max(0.05, min(0.95, p["asymmetry"]))
    dunes, minerals, wetness = p["dune_swell"], p["trough_minerals"], p["wetness"]
    red, green, blue, heights, rough = [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        base = y * width
        for x in range(width):
            index = base + x
            u = (x + 0.5) / width
            phase = count * (a * u + b * v) + meander * (2.2 * bend[index] + 0.6 * fork[index])
            f = phase - math.floor(phase)
            profile = f / rise if f < rise else (1.0 - f) / (1.0 - rise)
            profile = profile * profile * (3.0 - 2.0 * profile)
            dune = dunes * (0.5 + swell[index])
            level = 0.25 + 0.35 * profile * (1.0 - 0.4 * dunes) + 0.4 * dune + 0.02 * (grain[index] - 0.5)
            heights.append(level)
            trough = (1.0 - profile) ** 3 * minerals
            colour = [t + (c - t) * (0.55 + 0.45 * profile) for c, t in zip(crest_rgb, trough_rgb)]
            colour = [c * (1.0 - 0.45 * trough) * (0.94 + 0.1 * grain[index] + 0.06 * speckle[index])
                      for c in colour]
            colour = [c + (w - c) * wetness * 0.8 for c, w in zip(colour, wet_rgb)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            rough.append(0.92 - 0.55 * wetness + 0.05 * grain[index] - 0.04 * trough)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.012, roughness=rough,
                     ao_radius=0.02, ao_strength=0.7, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
