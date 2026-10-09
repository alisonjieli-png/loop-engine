"""Cushion moss: clumped mounds of tiny shoots, tileable PBR maps from the standard library only.

Clumps are low-frequency mounds separated by shaded crevices. Each shoot tip is a tiny dome from a fine Voronoi
diagram, roughened by fibre noise, so the surface reads as packed shoots. Colour runs from dark in the crevices to
light at the tips; ``dryness`` browns the tips and ``capsules`` adds spore stalks with small capsules. Everything is
periodic on the torus.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "moss_cushion"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.8]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.5, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "clumps", "type": "int", "default": 4, "minimum": 1, "maximum": 12,
     "meaning": "Noise cells across the tile for the cushion mounds."},
    {"name": "shoots_across", "type": "int", "default": 90, "minimum": 24, "maximum": 220,
     "meaning": "Shoot tips across the tile (higher is finer)."},
    {"name": "mound_height", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Height of the mounds relative to the shoot detail."},
    {"name": "crevices", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Depth and darkness of the gaps between mounds."},
    {"name": "dryness", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Browned, dry tips."},
    {"name": "capsules", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spore stalks with capsules standing above the moss."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Bright green cushion moss.", "values": {}},
    "dry_olive": {"description": "Dry olive-brown moss in summer.",
                  "values": {"dryness": 0.75, "crevices": 0.7, "shoots_across": 70}},
    "sphagnum": {"description": "Red and green bog moss with large soft heads.",
                 "values": {"shoots_across": 45, "clumps": 6, "mound_height": 0.4}},
    "fruiting": {"description": "Green moss with spore stalks and capsules.",
                 "values": {"capsules": 0.8, "shoots_across": 110}},
}
#: Crevice colour, mid colour, tip colour, dry tip colour, capsule colour per preset (sRGB).
PALETTES = {
    "default": ("#1b2e0e", "#4a7a1f", "#9cc24a", "#a08a4a", "#8a4b25"),
    "dry_olive": ("#262414", "#5b5a2a", "#8e8a48", "#a68b55", "#7a4a26"),
    "sphagnum": ("#2a1a12", "#7a3a2a", "#b8a046", "#c08a5a", "#6a2e1e"),
    "fruiting": ("#172a0c", "#3f6e1a", "#8eb842", "#9c8a4a", "#a0522d"),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The moss maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    crevice_rgb, mid_rgb, tip_rgb, dry_rgb, capsule_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    count = width * height
    cushions = tk.voronoi(width, height, p["clumps"] * 2, p["clumps"] * 2, tk.hash_u32(seed, 1), jitter=0.9)
    swell = tk.fbm(width, height, p["clumps"], 3, tk.hash_u32(seed, 7))
    gate = tk.fbm(width, height, p["clumps"] * 2, 3, tk.hash_u32(seed, 8))
    mounds = []
    for e, f, s, g in zip(cushions["edge"], cushions["f1"], swell, gate):
        split = tk.smoothstep(-0.05, 0.2, g)
        border = 1.0 - (1.0 - tk.smoothstep(0.0, 0.3, e)) * split
        mounds.append(min(1.0, max(0.0, border * (0.7 + 0.3 * (1.0 - min(f, 1.0))) + 0.25 * s)))
    shoots = tk.voronoi(width, height, p["shoots_across"], p["shoots_across"], tk.hash_u32(seed, 2), jitter=1.0,
                        edges=False)
    fibres = tk.fbm(width, height, p["shoots_across"], 2, tk.hash_u32(seed, 3))
    tint = tk.fbm(width, height, 6, 3, tk.hash_u32(seed, 4))
    grit = tk.white_noise(width, height, tk.hash_u32(seed, 5))
    mound_height, crevices, dryness = p["mound_height"], p["crevices"], p["dryness"]
    level = []
    for index in range(count):
        dome = max(0.0, 1.0 - shoots["f1"][index] * shoots["f1"][index] * 1.6)
        crevice = crevices * (1.0 - tk.smoothstep(0.0, 0.25, mounds[index]))
        level.append(0.25 + 0.5 * mound_height * mounds[index] + 0.2 * dome + 0.06 * fibres[index]
                     - 0.25 * crevice)
    lift = [0.0] * count
    rng = tk.Rng(seed, 6)
    capsule_tops = [0.0] * count
    for _ in range(int(140 * p["capsules"])):
        u, v = rng.random(), rng.random()
        angle = rng.uniform(0.0, math.tau)
        length = rng.uniform(0.02, 0.045)
        tip_u, tip_v = u + length * math.cos(angle), v + length * math.sin(angle)
        tk.draw_segment(lift, width, height, u, v, tip_u, tip_v, 0.0012, 0.25, profile=lambda d: 1.0)
        tk.stamp(capsule_tops, width, height, tip_u % 1.0, tip_v % 1.0, 0.004, 0.0025,
                 lambda s, t: max(0.0, 1.0 - s * s - t * t), angle=angle)
    peak = max(level)
    red, green, blue, heights, rough = [], [], [], [], []
    for index in range(count):
        relative = level[index] / peak
        colour = [a + (b - a) * min(1.0, relative * 1.3) for a, b in zip(crevice_rgb, mid_rgb)]
        tip = tk.smoothstep(0.55, 0.95, relative)
        tip_colour = [t + (d - t) * dryness for t, d in zip(tip_rgb, dry_rgb)]
        colour = [c + (t - c) * tip for c, t in zip(colour, tip_colour)]
        colour = [c * (0.9 + 0.2 * grit[index] + 0.12 * tint[index]) for c in colour]
        stalk = lift[index]
        cap = capsule_tops[index]
        if stalk > 0.0 or cap > 0.0:
            colour = [c + (k - c) * min(1.0, stalk * 3.0 + cap * 2.0) for c, k in zip(colour, capsule_rgb)]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        heights.append(0.85 * relative + stalk + 0.3 * cap)
        rough.append(0.82 + 0.1 * (1.0 - relative) + 0.06 * grit[index] - 0.12 * cap)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.02, roughness=rough,
                     ao_radius=0.02, ao_strength=1.3, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
