"""Plaster and stucco wall finishes: knockdown, Venetian trowel and sand float, tileable PBR maps (standard library).

Knockdown: splatter blobs with ragged outlines are stamped onto the wall, then flattened by a trowel, so each blob
becomes a plateau whose top is cut at a common level. Venetian: overlapping trowel swaths, each a long curved
ellipse with its own tone, are laid in layers and burnished, giving a marbled, low-roughness face. Sand float: a
fine sand grain with faint arcs left by the circular float. Paint or lime colour comes from the preset.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "plaster_stucco"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.04, 0.92]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.08, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "style", "type": "int", "default": 0, "minimum": 0, "maximum": 2,
     "meaning": "Finish: 0 knockdown, 1 Venetian trowel, 2 sand float."},
    {"name": "density", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Number of blobs, swaths or float arcs."},
    {"name": "feature_size", "type": "float", "default": 0.05, "minimum": 0.01, "maximum": 0.15,
     "meaning": "Typical blob or swath size in texture units."},
    {"name": "relief", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Height of blobs and ridges."},
    {"name": "tone_variation", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Colour variation between swaths and across the wall."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "White painted knockdown ceiling texture.", "values": {}},
    "venetian_terracotta": {"description": "Burnished terracotta Venetian plaster.",
                            "values": {"style": 1, "density": 0.6, "feature_size": 0.09, "tone_variation": 0.7,
                                       "relief": 0.3}},
    "venetian_grey": {"description": "Cool grey polished Venetian plaster.",
                      "values": {"style": 1, "density": 0.5, "feature_size": 0.07, "tone_variation": 0.5,
                                 "relief": 0.25}},
    "sand_lime": {"description": "Warm lime render with a sand float finish.",
                  "values": {"style": 2, "density": 0.4, "relief": 0.5, "tone_variation": 0.4}},
    "heavy_knockdown": {"description": "Coarse cream knockdown with large flattened blobs.",
                        "values": {"density": 0.8, "feature_size": 0.08, "relief": 0.9}},
}
#: Base colour, second colour (swath or shadow tone) and base roughness per preset (sRGB).
PALETTES = {
    "default": ("#ecebe7", "#dddbd6", 0.85),
    "venetian_terracotta": ("#c27a55", "#9e5639", 0.25),
    "venetian_grey": ("#a9adaf", "#7f8487", 0.2),
    "sand_lime": ("#e6d9c0", "#d1c1a2", 0.9),
    "heavy_knockdown": ("#e9e1cf", "#d8ccb3", 0.85),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The plaster maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    base_hex, second_hex, base_rough = PALETTES[preset]
    base, second = tk.hex_rgb(base_hex), tk.hex_rgb(second_hex)
    count = width * height
    rng = tk.Rng(seed, 1)
    size, relief, variation = p["feature_size"], p["relief"], p["tone_variation"]
    sand = tk.white_noise(width, height, tk.hash_u32(seed, 2))
    cloud = tk.fbm(width, height, 3, 4, tk.hash_u32(seed, 3))
    level = [0.0] * count
    tone = [0.5] * count
    gloss = [0.0] * count
    if p["style"] == 0:
        for _ in range(int(60 + 500 * p["density"])):
            radius = size * rng.uniform(0.3, 1.0)
            wobble = [rng.uniform(0.75, 1.0) for _ in range(7)]
            phase = rng.uniform(0.0, math.tau)

            def blob(s, t, wobble=wobble, phase=phase):
                angle = (math.atan2(t, s) + phase) / math.tau * 7.0 % 7.0
                k = int(angle)
                edge = wobble[k] + (wobble[(k + 1) % 7] - wobble[k]) * (angle - k)
                r = math.sqrt(s * s + t * t) / edge
                return 1.0 - tk.smoothstep(0.75, 1.0, r) if r < 1.0 else None
            tk.stamp(level, width, height, rng.random(), rng.random(), radius, radius * rng.uniform(0.6, 1.0), blob,
                     mode=tk.MODE_MAX, angle=rng.uniform(0.0, math.pi))
        level = [min(v, 0.7) / 0.7 for v in level]
        tone = [0.5 + 0.25 * v for v in level]
    elif p["style"] == 1:
        for layer in range(int(40 + 220 * p["density"])):
            length, breadth = size * rng.uniform(1.2, 2.5), size * rng.uniform(0.3, 0.6)
            shade = rng.random()
            sweep = rng.uniform(-0.6, 0.6)

            def swath(s, t, shade=shade, sweep=sweep):
                bent = t - sweep * s * s
                inside = s * s + bent * bent
                return shade if inside < 1.0 else None
            for index, s, t in tk.ellipse_pixels(width, height, rng.random(), rng.random(), length, breadth,
                                                 rng.uniform(0.0, math.pi)):
                value = swath(s, t)
                if value is not None:
                    edge = 1.0 - (s * s + (t - sweep * s * s) ** 2)
                    cover = 0.45 * tk.smoothstep(0.0, 0.6, edge)
                    tone[index] += (value - tone[index]) * cover
                    level[index] = max(level[index] * 0.9, 0.5 + 0.5 * tk.smoothstep(0.0, 0.05, edge) * 0.4)
                    gloss[index] = max(gloss[index], tk.smoothstep(0.1, 0.7, edge))
    else:
        grains = tk.blur(sand, width, height, 0.5 / min(width, height), passes=1)
        level = [0.5 + 0.8 * (g - 0.5) for g in grains]
        arcs = [0.0] * count
        for _ in range(int(10 + 60 * p["density"])):
            cu, cv = rng.random(), rng.random()
            radius = size * rng.uniform(1.0, 2.5)
            start = rng.uniform(0.0, math.tau)
            points = [(cu + radius * math.cos(start + k * 0.12), cv + radius * math.sin(start + k * 0.12))
                      for k in range(rng.integer(6, 18))]
            tk.draw_path(arcs, width, height, points, 0.0025, rng.uniform(0.3, 0.8))
        level = [v - 0.15 * a for v, a in zip(level, arcs)]
        tone = [0.5 + 0.3 * (g - 0.5) - 0.2 * a for g, a in zip(grains, arcs)]
    red, green, blue, heights, rough = [], [], [], [], []
    for index in range(count):
        mix = 0.5 + (tone[index] - 0.5) * variation * 2.0 + 0.15 * variation * cloud[index]
        mix = 0.0 if mix < 0.0 else 1.0 if mix > 1.0 else mix
        colour = [a + (b - a) * mix for a, b in zip(base, second)]
        colour = [c * (0.97 + 0.06 * sand[index]) for c in colour]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        heights.append(0.3 + 0.4 * relief * level[index] + 0.02 * sand[index])
        rough.append(base_rough - 0.15 * gloss[index] + 0.06 * sand[index])
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.01, roughness=rough,
                     ao_radius=0.01, ao_strength=0.8, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
