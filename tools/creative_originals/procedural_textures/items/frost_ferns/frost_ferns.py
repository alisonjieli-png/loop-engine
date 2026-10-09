"""Frost ferns on glass: branching ice crystals over clear glass, tileable maps with alpha (standard library).

Crystals start at well-spaced points (Bridson dart throwing on the torus) and grow as dendrites: a main stem walks
forward with a slight random curl and, at intervals, puts out opposite side branches at about 60 degrees (the
hexagonal habit of ice), which grow the same way at a smaller scale, down to the chosen depth. Branches are shorter
toward the tip of their parent, which gives the feather or fern outline. Every segment is painted as a capsule with
wrap-around into a coverage field; a thin noise haze of rime fills in between. Detail smaller than a pixel at the
output size is skipped, so small outputs stay fast and the layout keeps the same at every size.

Albedo carries alpha: frost is white-blue and nearly opaque, clear glass nearly transparent, for use as an overlay on
a window. Frost is raised and rough; glass is flat and smooth.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "frost_ferns"
MAPS = [
    {"name": "albedo", "channels": 4, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.3, 1.0]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.04, 0.95]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "crystals", "type": "int", "default": 9, "minimum": 2, "maximum": 30,
     "meaning": "Crystal seeds in the tile (about; seeds keep a minimum spacing)."},
    {"name": "size", "type": "float", "default": 0.4, "minimum": 0.08, "maximum": 0.5,
     "meaning": "Length of a main stem in texture units."},
    {"name": "branching", "type": "float", "default": 0.85, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Chance of side branches at each step of a stem or branch."},
    {"name": "levels", "type": "int", "default": 3, "minimum": 1, "maximum": 3,
     "meaning": "Branching depth: 1 bare needles, 2 branches, 3 branches with sub-branches."},
    {"name": "curl", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How much stems wander: 0 straight needles, 1 curling plumes."},
    {"name": "thickness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 2.0,
     "meaning": "Width of the crystal lines."},
    {"name": "haze", "type": "float", "default": 0.25, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Fine rime haze between the crystals."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Fern frost: feathered plumes spreading across a window.", "values": {}},
    "needle_frost": {"description": "Dense straight needles with short spurs crossing at random.",
                     "values": {"crystals": 30, "size": 0.26, "levels": 2, "branching": 0.35, "curl": 0.04,
                                "haze": 0.12, "thickness": 0.8}},
    "feathered": {"description": "Large dense plumes with sub-branches packed edge to edge.",
                  "values": {"crystals": 8, "size": 0.5, "branching": 1.0, "curl": 0.6, "thickness": 1.3,
                             "haze": 0.35}},
    "hoar_haze": {"description": "Heavy rime haze with small sparse crystals, almost fogged over.",
                  "values": {"crystals": 16, "size": 0.14, "branching": 0.5, "levels": 2, "haze": 0.95}},
}
#: Per preset: frost colour, frost shadow colour and glass tint (sRGB), and the glass alpha.
PALETTES = {
    "default": ("#f4fbff", "#9cc4dc", "#a8c8d8", 0.05),
    "needle_frost": ("#f8fcff", "#a8c0d0", "#b0c4cc", 0.04),
    "feathered": ("#eef8ff", "#86b4d4", "#98bcd4", 0.06),
    "hoar_haze": ("#f2f6f8", "#b8c8d0", "#c0ccd2", 0.1),
}
#: Paint strength of a stem and of each branching level.
LEVEL_VALUES = (1.0, 0.86, 0.72, 0.62)


def dendrite_segments(seed: int, crystals: int, size: float, branching: float, levels: int, curl: float) -> list:
    """(u0, v0, u1, v1, radius, level) of every segment of every crystal, in texture units (may run past 0 or 1)."""
    rng = tk.Rng(seed, 0xF0)
    spacing = max(0.004, min(0.5, math.sqrt(0.7 / crystals)))
    segments = []
    for su, sv in tk.poisson_points(spacing, tk.hash_u32(seed, 1)):
        pending = [(su, sv, math.tau * rng.random(), size * rng.uniform(0.65, 1.15), 0, 0.0042)]
        while pending:
            u, v, angle, length, level, radius = pending.pop()
            steps = max(3, int(round(12.0 * length / 0.3)))
            step = length / steps
            for k in range(steps):
                t = k / steps
                angle += curl * rng.gauss(0.0, 0.16 if level == 0 else 0.06)
                nu, nv = u + step * math.cos(angle), v + step * math.sin(angle)
                segments.append((u, v, nu, nv, radius * (1.0 - 0.55 * t), level))
                if level + 1 < levels and k > 0 and rng.chance(branching):
                    child = length * 0.55 * (1.0 - t) ** 0.6
                    if child > 0.006:
                        for side in (1.0, -1.0):
                            spread = math.pi / 3.0 + rng.gauss(0.0, 0.07)
                            pending.append((nu, nv, angle + side * spread, child * rng.uniform(0.8, 1.1),
                                            level + 1, radius * 0.62))
                u, v = nu, nv
    return segments


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The frost maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    frost_hex, shadow_hex, glass_hex, glass_alpha = PALETTES[preset]
    coverage = [0.0] * (width * height)
    pixel = 1.0 / min(width, height)
    for u0, v0, u1, v1, radius, level in dendrite_segments(seed, p["crystals"], p["size"], p["branching"],
                                                            p["levels"], p["curl"]):
        span = math.hypot((u1 - u0) * width, (v1 - v0) * height)
        if level >= 2 and span < 1.0:
            continue
        reach = max(radius * p["thickness"], 0.7 * pixel)
        tk.draw_segment(coverage, width, height, u0, v0, u1, v1, reach, LEVEL_VALUES[level], mode=tk.MODE_MAX)
    glow = tk.blur(coverage, width, height, 0.006, passes=2)
    coverage = [min(1.0, c + 0.45 * g) for c, g in zip(coverage, glow)]
    rime = tk.fbm(width, height, 6, 5, tk.hash_u32(seed, 2))
    grain = tk.white_noise(width, height, tk.hash_u32(seed, 3))
    sparkle = tk.value_noise(width, height, 96, 96, tk.hash_u32(seed, 4))
    haze = p["haze"]
    frost, shadow, glass = tk.hex_rgb(frost_hex), tk.hex_rgb(shadow_hex), tk.hex_rgb(glass_hex)
    red, green, blue, alpha, heights, rough = [], [], [], [], [], []
    for index in range(width * height):
        mist = haze * tk.smoothstep(0.35, 0.85, 0.5 + 0.5 * rime[index] + 0.25 * haze) * (0.55 + 0.45 * grain[index])
        cover = max(coverage[index], 0.7 * mist)
        facet = 0.75 + 0.25 * sparkle[index]
        lit = [s + (f - s) * facet for s, f in zip(shadow, frost)]
        mix = tk.smoothstep(0.0, 0.6, cover)
        colour = [g + (c - g) * mix for g, c in zip(glass, lit)]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        alpha.append(glass_alpha + (0.95 - glass_alpha) * tk.smoothstep(0.0, 0.85, cover))
        heights.append(0.2 + 0.6 * coverage[index] + 0.25 * mist + 0.03 * grain[index])
        rough.append(0.05 + 0.8 * tk.smoothstep(0.0, 0.5, cover))
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, alpha=alpha, heights=heights, depth=0.006,
                     roughness=rough, ao_radius=0.01, ao_strength=0.8, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
