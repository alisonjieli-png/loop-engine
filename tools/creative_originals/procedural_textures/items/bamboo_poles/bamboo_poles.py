"""Bamboo: culms side by side with nodes at uneven heights, or split slats, tileable PBR maps.

The poles run down the tile. Their widths vary and are scaled to fill the tile width exactly, so the row of poles
repeats; every pole has a whole number of nodes per tile at jittered heights, so it repeats down the tile too. A
culm is a cylinder in height; at each node it swells into a ridge with the sheath scar just below it and a pale waxy
band above, as on living bamboo. Fibres streak along the culm, and spotted bamboo carries dark mottles. Split slats
are flatter, narrower strips with the same nodes, as in a bamboo blind or mat.
"""
from __future__ import annotations

import math
import sys
from bisect import bisect_right

import texkit as tk

IDENTITY = "bamboo_poles"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.2, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "style", "type": "int", "default": 0, "minimum": 0, "maximum": 1,
     "meaning": "0 round culms side by side, 1 split slats (flatter, narrower strips)."},
    {"name": "poles", "type": "int", "default": 6, "minimum": 2, "maximum": 40,
     "meaning": "Poles or slats across the tile."},
    {"name": "width_variation", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 0.6,
     "meaning": "Spread of pole widths."},
    {"name": "nodes", "type": "int", "default": 2, "minimum": 1, "maximum": 6,
     "meaning": "Nodes per pole down the tile."},
    {"name": "node_ridge", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How strongly each node swells into a ridge."},
    {"name": "streaks", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Fibre streaks and tone along the culms."},
    {"name": "spots", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Dark mottled spots, as on spotted (tortoiseshell) bamboo."},
    {"name": "gap", "type": "float", "default": 0.05, "minimum": 0.0, "maximum": 0.3,
     "meaning": "Dark gap between neighbouring poles, as a share of the pole width."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Dried golden bamboo poles, as in a fence or screen.", "values": {}},
    "green_fresh": {"description": "Living green culms with pale waxy node bands.",
                    "values": {"poles": 5, "nodes": 2, "node_ridge": 0.75, "streaks": 0.35, "gap": 0.12}},
    "black_bamboo": {"description": "Black bamboo: dark purple-black culms with lighter nodes.",
                     "values": {"poles": 7, "nodes": 3, "streaks": 0.3, "width_variation": 0.2}},
    "split_mat": {"description": "Split bamboo slats in a mat or blind, nodes staggered.",
                  "values": {"style": 1, "poles": 24, "nodes": 3, "width_variation": 0.15, "gap": 0.08,
                             "node_ridge": 0.45}},
    "spotted_brown": {"description": "Spotted tortoiseshell bamboo with dark mottles.",
                      "values": {"poles": 6, "spots": 0.7, "nodes": 2}},
}
#: Culm colour, node band colour, spot colour, gap colour and culm roughness per preset.
PALETTES = {
    "default": ("#c9a865", "#a07e45", "#5a3a1a", "#2a1e10", 0.42),
    "green_fresh": ("#6f9a3c", "#c9d2a8", "#3c5a1e", "#14200a", 0.35),
    "black_bamboo": ("#2a2226", "#6a5a52", "#121012", "#0a0808", 0.3),
    "split_mat": ("#c8a46a", "#9a7a46", "#5a3a1a", "#3a2a16", 0.5),
    "spotted_brown": ("#b89660", "#8a6a3e", "#4a2c14", "#24180c", 0.38),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The bamboo maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    culm_code, node_code, spot_code, gap_code, culm_rough = PALETTES[preset]
    culm_rgb, node_rgb = tk.hex_rgb(culm_code), tk.hex_rgb(node_code)
    spot_rgb, gap_rgb = tk.hex_rgb(spot_code), tk.hex_rgb(gap_code)
    slats = p["style"] == 1
    poles, nodes = p["poles"], p["nodes"]
    rng = tk.Rng(seed, 0xBA)
    raw = [1.0 + p["width_variation"] * rng.uniform(-1.0, 1.0) for _ in range(poles)]
    total = sum(raw)
    starts = [0.0]
    for value in raw:
        starts.append(starts[-1] + value / total)
    node_rows, tones = [], []
    for _ in range(poles):
        offset = rng.random()
        node_rows.append(sorted(((k + 0.5 + 0.55 * rng.uniform(-0.5, 0.5)) / nodes + offset) % 1.0
                                for k in range(nodes)))
        tones.append(rng.uniform(-1.0, 1.0))
    mean_width = 1.0 / poles
    ridge_width = 0.05 * mean_width * (0.6 if slats else 1.0) + 0.002
    gap = p["gap"]
    limit = max(4, min(width, height) // 2)
    streak_field = tk.value_noise(width, height, min(limit, poles * 14), 5, tk.hash_u32(seed, 1))
    tone_field = tk.fbm(width, height, max(2, poles), 3, tk.hash_u32(seed, 2), cells_y=4)
    spot_field = tk.fbm(width, height, min(limit, poles * 6), 3, tk.hash_u32(seed, 3), cells_y=min(limit, 10))
    columns = []
    for x in range(width):
        u = (x + 0.5) / width
        pole = min(bisect_right(starts, u) - 1, poles - 1)
        across = (u - starts[pole]) / (starts[pole + 1] - starts[pole])
        columns.append((pole, across))
    ridge, streaks, spots = p["node_ridge"], p["streaks"], p["spots"]
    heights, red, green, blue, rough = [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        base = y * width
        rings = []
        for pole in range(poles):
            signed = min((tk.wrap_delta(v - node) for node in node_rows[pole]), key=abs)
            rings.append((ridge * math.exp(-(signed / ridge_width) ** 2),
                          math.exp(-((signed - 0.9 * ridge_width) / (0.25 * ridge_width)) ** 2),
                          math.exp(-((signed + 2.2 * ridge_width) / (1.1 * ridge_width)) ** 2)))
        for x in range(width):
            index = base + x
            pole, across = columns[x]
            centred = 2.0 * across - 1.0
            edge = 1.0 - abs(centred)
            open_gap = gap * 0.5
            if edge < open_gap:
                heights.append(0.0)
                red.append(gap_rgb[0])
                green.append(gap_rgb[1])
                blue.append(gap_rgb[2])
                rough.append(0.9)
                continue
            inner = min(1.0, (abs(centred)) / (1.0 - open_gap))
            profile = 1.0 - inner ** 4 if slats else math.sqrt(max(0.0, 1.0 - inner * inner))
            swell, scar, band = rings[pole]
            level = 0.15 + 0.7 * profile + 0.12 * swell * profile - 0.05 * scar * profile
            level += 0.015 * streaks * (streak_field[index] - 0.5)
            heights.append(level)
            shade = (0.78 + 0.22 * profile + 0.14 * streaks * (streak_field[index] - 0.5)
                     + 0.06 * streaks * tone_field[index] + 0.05 * tones[pole])
            colour = [c * shade for c in culm_rgb]
            colour = [c + (n - c) * (0.75 * band + 0.5 * swell) for c, n in zip(colour, node_rgb)]
            mottle = spots * tk.smoothstep(0.08, 0.28, spot_field[index])
            colour = [c + (s - c) * mottle for c, s in zip(colour, spot_rgb)]
            colour = [c * (1.0 - 0.45 * scar) for c in colour]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            rough.append(culm_rough + 0.12 * streaks * streak_field[index] + 0.2 * scar + 0.1 * band
                         + 0.1 * (1.0 - profile))
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.4 * mean_width * (0.5 if slats
                     else 1.0), roughness=rough, ao_radius=0.3 * mean_width, ao_strength=1.0,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
