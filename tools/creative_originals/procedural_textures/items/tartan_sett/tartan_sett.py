"""Tartan from a thread-count sett woven in 2/2 twill: tileable plaid cloth maps (standard library).

A sett is a half sequence of colours and thread counts that is reflected at both ends (the first and last colours are
the pivots and appear once per repeat), giving the symmetrical stripe sequence of a tartan. The same sequence is
used for the warp (threads running down the tile, so its colours change across the width) and the weft (threads
running across, colours changing down the height), and the tile holds a whole number of repeats. At every crossing a
2/2 twill decides which thread is on top: the warp where (i - j) mod 4 is 0 or 1, the weft otherwise, so the
visible colour alternates between the two along diagonal lines. Where warp and weft colours differ this gives the
blended, finely hatched squares of tartan, and where they match the solid squares.

Threads have a round cross-section, dip where they pass under the next crossing, carry a slight per-thread colour
variation and a twisted-yarn texture, and wool fuzz softens everything. The twill repeats every four threads, so a
sett whose repeat is not a multiple of four gets its first pivot widened by up to three threads to keep the tile
seamless.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "tartan_sett"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.03, 0.92]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.55, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "repeats", "type": "int", "default": 1, "minimum": 1, "maximum": 4,
     "meaning": "Whole sett repeats across the tile."},
    {"name": "thread_scale", "type": "int", "default": 1, "minimum": 1, "maximum": 3,
     "meaning": "Multiplies every thread count; larger values show finer threads in the same stripes."},
    {"name": "relief", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Height of the yarn and the twill ridges."},
    {"name": "fuzz", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Wool fuzz blurring colours and relief."},
    {"name": "yarn_variation", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Colour variation from thread to thread."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Highland check: navy and green grounds crossed by red with a yellow overcheck.",
                "values": {}},
    "grey_dress": {"description": "Dress sett in white, grey and black with a fine charcoal line.",
                   "values": {"fuzz": 0.35}},
    "autumn_plaid": {"description": "Brown, rust and cream plaid with a narrow orange stripe, soft and fuzzy.",
                     "values": {"fuzz": 0.8, "yarn_variation": 0.5}},
    "buffalo_check": {"description": "Two-colour red and black block check, two repeats across.",
                      "values": {"repeats": 2, "fuzz": 0.7}},
    "madras_bright": {"description": "Bright cotton madras: pink, lime, yellow and sky blue, crisp and smooth.",
                      "values": {"repeats": 2, "fuzz": 0.1, "relief": 0.4, "yarn_variation": 0.6}},
}
#: Invented half setts per preset: (colour sRGB, thread count) from one pivot to the other.
SETTS = {
    "default": [("#1a2440", 6), ("#1f4a2c", 14), ("#1a2440", 4), ("#9c1c22", 16), ("#e8c440", 2)],
    "grey_dress": [("#efece4", 10), ("#8a8c90", 6), ("#1c1c1e", 12), ("#8a8c90", 3), ("#3a3a3e", 2)],
    "autumn_plaid": [("#5a3420", 12), ("#a8481c", 8), ("#e8dcc0", 6), ("#5a3420", 3), ("#e07a20", 2)],
    "buffalo_check": [("#b0181c", 14), ("#141214", 14)],
    "madras_bright": [("#f06aa0", 6), ("#a8d040", 4), ("#f8e060", 3), ("#58b8e8", 7), ("#ffffff", 1)],
}


def sett_threads(half: list, scale: int = 1) -> list:
    """Colour of every thread in one repeat: the half sett, then back again without repeating the pivots."""
    if not half:
        raise ValueError("a sett needs at least one colour")
    forward = [colour for colour, count in half for _ in range(count * scale)]
    back = [colour for colour, count in reversed(half[1:-1]) for _ in range(count * scale)]
    return forward + back


def warp_on_top(i: int, j: int) -> bool:
    """2/2 twill: the warp thread i lies over weft thread j for two crossings in four, shifting one per row."""
    return (i - j) % 4 < 2


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The tartan maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    sequence = sett_threads(SETTS[preset], p["thread_scale"])
    # the twill repeats every four threads, so the first pivot is widened until the repeat is a multiple of four
    sequence = [sequence[0]] * ((-len(sequence)) % 4) + sequence
    threads = len(sequence) * p["repeats"]
    colours = {code: tk.hex_rgb(code) for code in set(sequence)}
    variation = p["yarn_variation"]
    warp_shade = [1.0 + 0.12 * variation * (tk.hash_float(seed, 1, k) - 0.5) for k in range(threads)]
    weft_shade = [1.0 + 0.12 * variation * (tk.hash_float(seed, 2, k) - 0.5) for k in range(threads)]
    fuzz = p["fuzz"]
    fluff = tk.fbm(width, height, 32, 3, tk.hash_u32(seed, 3))
    hairs = tk.white_noise(width, height, tk.hash_u32(seed, 4))
    relief = p["relief"]
    red, green, blue, heights, rough = [], [], [], [], []
    for y in range(height):
        ty = (y + 0.5) / height * threads
        j = int(ty) % threads
        fy = ty - math.floor(ty)
        weft_colour = colours[sequence[j % len(sequence)]]
        for x in range(width):
            index = y * width + x
            tx = (x + 0.5) / width * threads
            i = int(tx) % threads
            fx = tx - math.floor(tx)
            if warp_on_top(i, j):
                across, along = fx, fy
                colour = colours[sequence[i % len(sequence)]]
                shade = warp_shade[i]
                under_before = not warp_on_top(i, j - 1)
                under_after = not warp_on_top(i, j + 1)
                twist = 0.5 + 0.5 * math.sin(math.tau * (3.0 * fy + 1.5 * fx))
            else:
                across, along = fy, fx
                colour = weft_colour
                shade = weft_shade[j]
                under_before = warp_on_top(i - 1, j)
                under_after = warp_on_top(i + 1, j)
                twist = 0.5 + 0.5 * math.sin(math.tau * (3.0 * fx + 1.5 * fy))
            bulge = math.sqrt(max(0.0, 1.0 - (2.0 * across - 1.0) ** 2))
            dip = 0.0
            if under_before:
                dip = max(dip, 1.0 - tk.smoothstep(0.0, 0.35, along))
            if under_after:
                dip = max(dip, 1.0 - tk.smoothstep(0.0, 0.35, 1.0 - along))
            n = fluff[index]
            tone = shade * (0.82 + 0.18 * bulge) * (0.96 + 0.06 * twist) * (1.0 - 0.18 * dip)
            tone *= 1.0 + fuzz * (0.06 * n + 0.04 * (hairs[index] - 0.5))
            red.append(colour[0] * tone)
            green.append(colour[1] * tone)
            blue.append(colour[2] * tone)
            heights.append(0.45 + relief * (0.3 * bulge - 0.25 * dip + 0.05 * twist) + fuzz * 0.06 * n)
            rough.append(0.8 + 0.1 * fuzz + 0.06 * (1.0 - bulge) - 0.04 * twist)
    if fuzz > 0.0:
        soften = tk.blur(heights, width, height, 0.3 / threads, passes=1)
        heights = [h + (s - h) * 0.6 * fuzz for h, s in zip(heights, soften)]
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.35 / threads, roughness=rough,
                     ao_radius=0.6 / threads, ao_strength=0.7, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
