"""Layered sandstone: strata, cross-bedding and weathering pits, tileable PBR maps (standard library only).

Strata are bands of uneven thickness running across the tile; their boundaries wave with low-frequency noise. Each
stratum takes a colour from the preset's sequence and a hardness, and soft strata are eroded back so the harder
ones stand proud. Inside the strata, cross-bedding laminae run at an incline whose direction alternates between
strata: the lamina phase is a whole number of cycles along u and v, so it repeats with the tile. Optional honeycomb
weathering (tafoni) sinks small rounded pits.
"""
from __future__ import annotations

import math
import sys
from bisect import bisect_right

import texkit as tk

IDENTITY = "sandstone_strata"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.03, 0.88]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.6, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "strata", "type": "int", "default": 9, "minimum": 2, "maximum": 30,
     "meaning": "Strata across the tile height."},
    {"name": "thickness_variation", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How unequal the strata are in thickness."},
    {"name": "waviness", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How much the strata boundaries wave."},
    {"name": "cross_bedding", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Visibility of the inclined laminae inside the strata."},
    {"name": "erosion", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How far soft strata are worn back behind hard ones."},
    {"name": "honeycomb", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Honeycomb weathering pits (tafoni)."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Desert red and cream banded sandstone.", "values": {}},
    "buff": {"description": "Pale buff building sandstone with faint bedding.",
             "values": {"strata": 6, "cross_bedding": 0.3, "erosion": 0.2, "thickness_variation": 0.3}},
    "tafoni_coast": {"description": "Coastal sandstone with honeycomb weathering.",
                     "values": {"honeycomb": 0.85, "erosion": 0.4, "strata": 7}},
    "swirled": {"description": "Strongly cross-bedded orange and white dune sandstone.",
                "values": {"strata": 5, "cross_bedding": 1.0, "waviness": 0.9, "erosion": 0.3}},
    "grey_flagstone": {"description": "Grey-green layered sandstone with thin beds.",
                       "values": {"strata": 16, "thickness_variation": 0.8, "erosion": 0.7, "waviness": 0.2}},
}
#: Colour sequence of the strata per preset (sRGB), repeated as needed.
PALETTES = {
    "default": ["#b8643a", "#d99a6c", "#c27a4b", "#e8c9a4", "#a85634", "#d48a5c", "#efd8b8"],
    "buff": ["#d9c29a", "#cdb48a", "#e2cfab", "#c8ad83", "#ddc8a2"],
    "tafoni_coast": ["#c9a27a", "#b88d63", "#d6b48d", "#a97f58", "#c39a70"],
    "swirled": ["#d27f43", "#efe0c8", "#e09a5e", "#f3e6d0", "#c46f39"],
    "grey_flagstone": ["#7d8079", "#6c6f68", "#8d9088", "#5f625c", "#979a92"],
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The sandstone maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    colours = [tk.hex_rgb(code) for code in PALETTES[preset]]
    count = p["strata"]
    rng = tk.Rng(seed, 1)
    sizes = [1.0 + p["thickness_variation"] * rng.uniform(-0.8, 1.6) for _ in range(count)]
    total = sum(sizes)
    bounds = [0.0]
    for size in sizes:
        bounds.append(bounds[-1] + size / total)
    layers = [{"colour": colours[rng.integer(0, len(colours) - 1)], "hard": rng.random(),
               "slope": rng.choice((-3, -2, 2, 3)), "tone": rng.uniform(-1.0, 1.0)} for _ in range(count)]
    wave = tk.fbm(width, height, 2, 4, tk.hash_u32(seed, 2), cells_y=1)
    wobble = tk.fbm(width, height, 6, 3, tk.hash_u32(seed, 3))
    grains = tk.white_noise(width, height, tk.hash_u32(seed, 4))
    mottle = tk.fbm(width, height, 8, 4, tk.hash_u32(seed, 5))
    pits = [1.0] * (width * height)
    if p["honeycomb"] > 0.0:
        cells = tk.voronoi(width, height, 14, 14, tk.hash_u32(seed, 6), jitter=0.9, edges=True)
        pits = [tk.smoothstep(0.0, 0.18, e) for e in cells["edge"]]
    waviness, cross, erosion, honeycomb = p["waviness"], p["cross_bedding"], p["erosion"], p["honeycomb"]
    laminae = 12 * count
    red, green, blue, heights, rough = [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        base = y * width
        for x in range(width):
            index = base + x
            u = (x + 0.5) / width
            position = (v + 0.06 * waviness * wave[index] + 0.004 * wobble[index]) % 1.0
            k = min(bisect_right(bounds, position) - 1, count - 1)
            layer = layers[k]
            within = (position - bounds[k]) / (bounds[k + 1] - bounds[k])
            lamina = 0.5 + 0.5 * math.sin(math.tau * (laminae * v + layer["slope"] * 4 * u)
                                          + 2.0 * wobble[index])
            edge = min(within, 1.0 - within)
            boundary = 1.0 - tk.smoothstep(0.0, 0.08, edge)
            tone = 1.0 + 0.08 * layer["tone"] + 0.1 * cross * (lamina - 0.5) + 0.06 * mottle[index] \
                + 0.08 * (grains[index] - 0.5) - 0.12 * boundary
            pit = 1.0 - pits[index]
            colour = [c * tone * (1.0 - 0.35 * pit * honeycomb) for c in layer["colour"]]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            recess = erosion * (1.0 - layer["hard"]) * 0.35
            level = 0.75 - recess - 0.1 * erosion * boundary + 0.03 * cross * lamina + 0.02 * grains[index] \
                - 0.45 * honeycomb * pit
            heights.append(level)
            rough.append(0.86 + 0.08 * grains[index] + 0.04 * boundary)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.03, roughness=rough,
                     ao_radius=0.025, ao_strength=1.2, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
