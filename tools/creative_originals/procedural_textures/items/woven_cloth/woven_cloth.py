"""Woven cloth from a weave draft: plain, twill, satin, basket and herringbone, tileable PBR maps (standard library).

The tile holds a whole number of warp threads (running down the image) and weft threads (running across). A draft,
a small binary matrix repeated over the threads, says at each crossing whether the warp or the weft lies on top.
The visible thread is drawn with a round cross-section; along its length it dips only where it passes under the
next crossing, so floats in twill and satin stay raised. Twist striations, fuzz, slubs and per-thread colour come
from noise and hashes of the thread index. Thread counts are rounded up to a multiple of the draft size so the
weave repeats exactly.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "woven_cloth"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.92]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.25, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "weave", "type": "int", "default": 0, "minimum": 0, "maximum": 5,
     "meaning": "Draft: 0 plain, 1 2/2 twill, 2 3/1 twill, 3 4/1 satin, 4 2/2 basket, 5 herringbone twill."},
    {"name": "threads", "type": "int", "default": 24, "minimum": 4, "maximum": 96,
     "meaning": "Warp and weft threads across the tile (rounded up to a multiple of the draft size)."},
    {"name": "thread_width", "type": "float", "default": 0.88, "minimum": 0.5, "maximum": 1.0,
     "meaning": "Thread width as a share of the thread spacing; lower values open gaps between threads."},
    {"name": "twist", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Depth of the diagonal twist striations along each thread."},
    {"name": "fuzz", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Loose fibre noise on the thread surface."},
    {"name": "slubs", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Irregular thick and thin stretches and colour changes along the threads."},
    {"name": "sheen", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Lowers roughness on long floats, as in satin."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Natural linen in plain weave with slubs.", "values": {"slubs": 0.5}},
    "denim": {"description": "Indigo warp and white weft in 3/1 twill.",
              "values": {"weave": 2, "threads": 32, "thread_width": 0.95, "twist": 0.7, "fuzz": 0.3, "slubs": 0.4}},
    "wool_twill": {"description": "Charcoal and grey wool in 2/2 twill with soft fuzz.",
                   "values": {"weave": 1, "threads": 28, "fuzz": 0.8, "twist": 0.3}},
    "satin": {"description": "Burgundy 4/1 satin with long glossy floats.",
              "values": {"weave": 3, "threads": 25, "thread_width": 0.98, "twist": 0.15, "fuzz": 0.1,
                         "slubs": 0.0, "sheen": 0.85}},
    "burlap": {"description": "Coarse open jute in plain weave with gaps and hairy fibres.",
               "values": {"threads": 12, "thread_width": 0.7, "twist": 0.8, "fuzz": 1.0, "slubs": 0.8}},
    "basket": {"description": "Off-white cotton in 2/2 basket weave.",
               "values": {"weave": 4, "threads": 24, "twist": 0.4, "fuzz": 0.3}},
    "herringbone": {"description": "Brown and cream wool herringbone twill.",
                    "values": {"weave": 5, "threads": 32, "fuzz": 0.6}},
}
#: Warp colour, weft colour and the gap colour behind the threads, per preset (sRGB).
PALETTES = {
    "default": ("#c9b99a", "#bfae8d", "#5e5444"),
    "denim": ("#2b4675", "#bdb9ae", "#1b2840"),
    "wool_twill": ("#4a4a4c", "#8a8a8c", "#232325"),
    "satin": ("#7a1428", "#5c0f1f", "#2a060d"),
    "burlap": ("#a8875a", "#9a7a4e", "#2e2416"),
    "basket": ("#e6e1d6", "#ddd7ca", "#7d786e"),
    "herringbone": ("#6b5038", "#d8cbb2", "#2d2219"),
}


def _draft(weave: int) -> list:
    """The draft as rows of 0 (weft on top) and 1 (warp on top), indexed [weft j][warp i]."""
    if weave == 0:
        return [[(i + j + 1) % 2 for i in range(2)] for j in range(2)]
    if weave == 1:
        return [[1 if (i - j) % 4 in (0, 1) else 0 for i in range(4)] for j in range(4)]
    if weave == 2:
        return [[1 if (i - j) % 4 in (0, 1, 2) else 0 for i in range(4)] for j in range(4)]
    if weave == 3:
        return [[0 if (2 * i - j) % 5 == 0 else 1 for i in range(5)] for j in range(5)]
    if weave == 4:
        return [[1 if (i // 2 + j // 2) % 2 == 0 else 0 for i in range(4)] for j in range(4)]
    return [[1 if ((i - j) if i < 4 else (i + j + 1)) % 4 in (0, 1) else 0 for i in range(8)] for j in range(4)]


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The cloth maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    warp_rgb, weft_rgb, gap_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    draft = _draft(p["weave"])
    repeat_y, repeat_x = len(draft), len(draft[0])
    across = -(-p["threads"] // repeat_x) * repeat_x
    down = -(-p["threads"] // repeat_y) * repeat_y
    half = p["thread_width"] * 0.5
    rng = tk.Rng(seed, 1)
    warp_tone = [rng.uniform(-1.0, 1.0) for _ in range(across)]
    weft_tone = [rng.uniform(-1.0, 1.0) for _ in range(down)]
    fuzz_noise = tk.fbm(width, height, max(8, across * 2), 2, tk.hash_u32(seed, 2))
    slub_x = tk.value_noise(width, height, across, 6, tk.hash_u32(seed, 3))
    slub_y = tk.value_noise(width, height, 6, down, tk.hash_u32(seed, 4))
    hair = tk.white_noise(width, height, tk.hash_u32(seed, 5))
    twist, fuzz, slubs, sheen = p["twist"], p["fuzz"], p["slubs"], p["sheen"]
    red, green, blue, heights, rough = [], [], [], [], []
    for y in range(height):
        fv = (y + 0.5) / height * down
        j = int(fv) % down
        b = fv - math.floor(fv)
        row = draft[j % repeat_y]
        above = draft[(j - 1) % repeat_y]
        below = draft[(j + 1) % repeat_y]
        base = y * width
        for x in range(width):
            index = base + x
            fu = (x + 0.5) / width * across
            i = int(fu) % across
            a = fu - math.floor(fu)
            warp_top = row[i % repeat_x]
            if warp_top:
                across_thread, along = a, b
                neighbour_before, neighbour_after = above[i % repeat_x], below[i % repeat_x]
                tone, colour, slub = warp_tone[i], warp_rgb, slub_x[index]
            else:
                across_thread, along = b, a
                neighbour_before, neighbour_after = row[(i - 1) % repeat_x], row[(i + 1) % repeat_x]
                neighbour_before, neighbour_after = 1 - neighbour_before, 1 - neighbour_after
                tone, colour, slub = weft_tone[j], weft_rgb, slub_y[index]
            girth = half * (1.0 + 0.25 * slubs * (slub - 0.5))
            offset = abs(across_thread - 0.5)
            if offset >= girth:
                level, cover = 0.05, 0.0
            else:
                section = math.sqrt(1.0 - (offset / girth) ** 2)
                rise = 1.0
                if not neighbour_before:
                    rise *= 0.55 + 0.45 * tk.smoothstep(0.0, 0.45, along)
                if not neighbour_after:
                    rise *= 0.55 + 0.45 * tk.smoothstep(0.0, 0.45, 1.0 - along)
                stripes = 0.5 + 0.5 * math.sin(math.tau * (3.0 * along + 1.6 * across_thread))
                level = 0.15 + 0.75 * section * rise - 0.08 * twist * stripes * section
                cover = tk.smoothstep(0.0, 0.08, girth - offset)
            level += 0.05 * fuzz * fuzz_noise[index]
            shade = (0.84 + 0.2 * level + 0.08 * tone + 0.18 * slubs * (slub - 0.5)
                     - 0.1 * twist * (0.5 + 0.5 * math.sin(math.tau * (3.0 * along + 1.6 * across_thread)))
                     + 0.12 * fuzz * (hair[index] - 0.5))
            thread = [c * shade for c in colour]
            pixel = [g + (t - g) * cover for g, t in zip(gap_rgb, thread)]
            red.append(pixel[0])
            green.append(pixel[1])
            blue.append(pixel[2])
            heights.append(level)
            float_gloss = sheen * cover * (1.0 if neighbour_before and neighbour_after else 0.5)
            rough.append(0.92 - 0.55 * float_gloss + 0.05 * fuzz * hair[index] - 0.04 * (1.0 - cover))
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.35 / max(across, down),
                     roughness=rough, ao_radius=0.5 / max(across, down), ao_strength=1.2, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
