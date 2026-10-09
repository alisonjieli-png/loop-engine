"""Quilted and tufted fabric: diamond, square or channel quilting with puffed panels, stitches and buttons.

Seams are straight line families with integer phase slopes (n_u * u + n_v * v = k), so every seam closes on the torus
and the quilt tiles. Each panel is a pillow: its height is the product of a rounded profile of the normalized distance
to the seams of each family, which leaves the seams pulled down to the backing and the panel centres full. Stitches
are dashes along each seam, spaced by the phase of the crossing family so they repeat too. Deep buttons can sit at
the seam crossings (tufting), the fabric crinkles near the seams, and a fine weave adds texture to cloth presets.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "quilted_fabric"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.92]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.15, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "pattern", "type": "int", "default": 0, "minimum": 0, "maximum": 2,
     "meaning": "0 diamond quilting (two diagonal seam families), 1 square grid, 2 horizontal channels."},
    {"name": "cells", "type": "int", "default": 5, "minimum": 1, "maximum": 16,
     "meaning": "Quilted panels across the tile width (diamonds, squares, or for channels the channel count down "
                "the tile)."},
    {"name": "aspect", "type": "float", "default": 1.4, "minimum": 0.5, "maximum": 2.5,
     "meaning": "Panels down the tile per panel across; above 1 the diamonds are taller than wide."},
    {"name": "puff", "type": "float", "default": 0.6, "minimum": 0.1, "maximum": 1.0,
     "meaning": "How full the panels are between the seams."},
    {"name": "stitches", "type": "int", "default": 9, "minimum": 0, "maximum": 30,
     "meaning": "Stitches along one panel edge; 0 hides the seams' stitching (tufting folds)."},
    {"name": "buttons", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Size of the buttons pulled deep into the seam crossings, as in deep-buttoned upholstery."},
    {"name": "wrinkles", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Crinkles of the fabric gathered near the seams."},
    {"name": "sheen", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Gloss of taut panel tops: 0 matte cotton, 1 shiny nylon or satin."},
    {"name": "weave", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Fine woven texture of the cover fabric."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Cream cotton bedspread in diamond quilting with visible stitches.", "values": {}},
    "puffer_channel": {"description": "Black nylon puffer-jacket channels, glossy and crinkled.",
                       "values": {"pattern": 2, "cells": 6, "puff": 0.9, "stitches": 0, "wrinkles": 0.8,
                                  "sheen": 0.85, "weave": 0.1}},
    "square_satin": {"description": "Blush satin in a square grid with fine stitching.",
                     "values": {"pattern": 1, "cells": 6, "aspect": 1.0, "puff": 0.5, "stitches": 14,
                                "wrinkles": 0.4, "sheen": 0.6, "weave": 0.2}},
    "chesterfield": {"description": "Deep-buttoned oxblood leather tufting: full diamonds, buttons, no stitches.",
                     "values": {"cells": 4, "aspect": 1.3, "puff": 1.0, "stitches": 0, "buttons": 0.8,
                                "wrinkles": 0.5, "sheen": 0.45, "weave": 0.0}},
    "moving_blanket": {"description": "Navy workwear quilting: small diamonds with contrast stitching.",
                       "values": {"cells": 9, "aspect": 1.0, "puff": 0.35, "stitches": 7, "wrinkles": 0.2,
                                  "weave": 0.9}},
}
#: Fabric colour, stitch thread colour and button colour per preset (sRGB).
PALETTES = {
    "default": ("#e7e0d0", "#d8cfbb", "#d2c9b5"),
    "puffer_channel": ("#24262b", "#30333a", "#24262b"),
    "square_satin": ("#e3b8b0", "#f2d9d2", "#d9a9a0"),
    "chesterfield": ("#5c1a17", "#5c1a17", "#3f100e"),
    "moving_blanket": ("#2c3c66", "#c9b27a", "#2c3c66"),
}


def _seam_frames(pattern: int, cells: int, rows: int) -> tuple:
    """Two seam families as (phase slope u, phase slope v, perpendicular scale); a None family has no seams."""
    if pattern == 0:
        norm = math.hypot(cells, rows)
        return (cells, rows, 1.0 / norm), (cells, -rows, 1.0 / norm)
    if pattern == 1:
        return (cells, 0, 1.0 / cells), (0, rows, 1.0 / rows)
    return None, (0, rows, 1.0 / rows)


def _pillow(t: float) -> float:
    """Rounded panel profile across a half panel: 0 at the seam, 1 at the panel middle."""
    return 1.0 - (1.0 - t) ** 2.6


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The quilted fabric maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    fabric_rgb, thread_rgb, button_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    pattern, cells = p["pattern"], p["cells"]
    rows = max(1, int(round(cells * p["aspect"])))
    if pattern == 2:
        cells, rows = 1, max(1, p["cells"])
    first, second = _seam_frames(pattern, cells, rows)
    stitches, puff, buttons, wrinkles = p["stitches"], p["puff"], p["buttons"], p["wrinkles"]
    sheen, weave = p["sheen"], p["weave"]
    panel = min(first[2] if first else 1.0, second[2])
    seam_half = max(0.006, 0.05 * panel) if stitches else max(0.004, 0.03 * panel)
    seam_t = seam_half / (0.5 * panel)
    button_radius = (0.07 + 0.08 * buttons) * panel
    limit = max(4, min(width, height) // 3)
    crinkle_cells = min(limit, max(6, 4 * max(cells, rows)))
    crinkles = tk.ridged(width, height, crinkle_cells, 3, tk.hash_u32(seed, 1))
    lumps = tk.fbm(width, height, max(2, 2 * max(cells, rows)), 3, tk.hash_u32(seed, 2))
    threads = 160
    weave_fade = weave * tk.smoothstep(2.5, 5.0, min(width, height) / threads)
    tones = tk.fbm(width, height, 3, 3, tk.hash_u32(seed, 3))
    tau = math.tau
    heights, red, green, blue, rough = [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        for x in range(width):
            u = (x + 0.5) / width
            index = y * width + x
            ta, along_a = 1.0, 0.0
            if first is not None:
                phase = first[0] * u + first[1] * v
                fa = phase - math.floor(phase)
                ta = 2.0 * min(fa, 1.0 - fa)
            phase_b = second[0] * u + second[1] * v
            fb = phase_b - math.floor(phase_b)
            tb = 2.0 * min(fb, 1.0 - fb)
            if first is not None:
                along_a = phase_b
                along_b = phase
            else:
                along_b = 4.0 * u
            closeness = 1.0 - min(ta, tb)
            level = puff * _pillow(ta) * _pillow(tb) + 0.06 * puff * lumps[index]
            level += wrinkles * 0.07 * puff * closeness ** 2 * crinkles[index]
            colour, gloss = fabric_rgb, sheen * tk.smoothstep(0.3, 0.9, ta * tb)
            on_thread = 0.0
            if stitches:
                for t_value, along in ((ta, along_a), (tb, along_b)):
                    if t_value < seam_t:
                        dash = along * stitches
                        dash -= math.floor(dash)
                        if dash < 0.6:
                            profile = 1.0 - t_value / seam_t
                            on_thread = max(on_thread, profile)
            if on_thread > 0.0:
                level = max(level, 0.05 + 0.08 * on_thread)
                colour = [c + (s - c) * min(1.0, on_thread * 2.0) for c, s in zip(colour, thread_rgb)]
            if buttons > 0.0 and first is not None:
                da = 0.5 * ta * first[2]
                db = 0.5 * tb * second[2]
                r = math.hypot(da, db) / button_radius
                if r < 1.0:
                    level = 0.04 + 0.32 * buttons * math.sqrt(1.0 - r * r)
                    colour = button_rgb
                    gloss = sheen * 0.8
                elif r < 2.2:
                    level *= tk.smoothstep(1.0, 2.2, r)
            fibre = 0.0
            if weave_fade > 0.0:
                fibre = 0.5 + 0.25 * (math.cos(tau * threads * u) + math.cos(tau * threads * v))
                level += 0.015 * weave_fade * fibre
            heights.append(level)
            shade = 0.86 + 0.14 * level / max(puff, 0.1) + 0.05 * tones[index] - 0.06 * weave_fade * fibre
            red.append(colour[0] * shade)
            green.append(colour[1] * shade)
            blue.append(colour[2] * shade)
            rough.append(0.86 - 0.62 * gloss + 0.05 * weave_fade * fibre + 0.07 * closeness * closeness
                         + 0.03 * tones[index] + 0.04 * on_thread)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.55 * panel, roughness=rough,
                     ao_radius=0.35 * panel, ao_strength=1.1, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
