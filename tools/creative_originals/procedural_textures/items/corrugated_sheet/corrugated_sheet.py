"""Corrugated sheet metal: sine or box profile, galvanized or painted, rust streaks and screws (standard library).

The profile runs across the tile (corrugations are vertical): a sine wave or a trapezoidal box rib, with a whole
number of ribs so the sheet repeats. Height follows the profile; dirt collects in the valleys and rust streaks run
down from screw heads and from rusty patches, each column swept downward with a fading trail that wraps. Screw
heads with washers sit on the crests in evenly spaced rows. Galvanized sheet is metal; paint is dielectric and
chips through to the metal.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "corrugated_sheet"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.15, 1.0]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "ribs", "type": "int", "default": 6, "minimum": 2, "maximum": 24,
     "meaning": "Corrugations across the tile."},
    {"name": "profile", "type": "int", "default": 0, "minimum": 0, "maximum": 1,
     "meaning": "Rib shape: 0 sine wave, 1 trapezoidal box rib."},
    {"name": "screw_rows", "type": "int", "default": 1, "minimum": 0, "maximum": 4,
     "meaning": "Rows of screws across the tile (0 for none)."},
    {"name": "paint", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Paint coverage (0 bare galvanized metal, 1 painted)."},
    {"name": "rust", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Rust patches and the streaks below them."},
    {"name": "dirt", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Dirt in the valleys."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.0,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Galvanized sine-wave sheet with light dirt.", "values": {}},
    "barn_red": {"description": "Red painted sheet with faded paint and rust runs.",
                 "values": {"paint": 1.0, "rust": 0.45, "ribs": 7}},
    "rusty_shack": {"description": "Old sheet with heavy rust streaks.",
                    "values": {"rust": 0.9, "dirt": 0.6, "ribs": 5}},
    "box_profile_blue": {"description": "Blue painted box-profile cladding, clean.",
                         "values": {"profile": 1, "paint": 1.0, "rust": 0.0, "dirt": 0.1, "ribs": 4,
                                    "screw_rows": 2}},
}
#: Metal, paint, rust and dirt colours per preset (sRGB).
PALETTES = {
    "default": ("#b9bec2", "#a6342a", "#8a4520", "#4b4538"),
    "barn_red": ("#a7acb0", "#9b2b22", "#8a4520", "#4a3d32"),
    "rusty_shack": ("#9fa4a8", "#7a7f74", "#83401d", "#4a3d2e"),
    "box_profile_blue": ("#b4b9bd", "#2f5f8c", "#8a4520", "#4b4538"),
}


def _profile(phase: float, box: bool) -> float:
    if not box:
        return 0.5 + 0.5 * math.cos(math.tau * phase)
    distance = abs(phase - math.floor(phase + 0.5))
    return 1.0 - tk.smoothstep(0.12, 0.3, distance)


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The corrugated sheet maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    metal, paint_rgb, rust_rgb, dirt_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    count = width * height
    ribs, box = p["ribs"], p["profile"] == 1
    columns = [_profile((x + 0.5) / width * ribs, box) for x in range(width)]
    screws = [0.0] * count
    rows = p["screw_rows"]
    for row in range(rows):
        v = (row + 0.5) / rows
        for rib in range(ribs):
            u = rib / ribs
            tk.stamp(screws, width, height, u % 1.0, v, 0.016 / max(1, ribs / 6), 0.016 / max(1, ribs / 6),
                     lambda s, t: max(0.0, 1.0 - (s * s + t * t)) ** 0.5 if s * s + t * t < 1.0 else None)
    patches = tk.fbm(width, height, 5, 4, tk.hash_u32(seed, 1))
    rust_amount = p["rust"]
    sources = [max(min(1.0, s * 2.0) * rust_amount, rust_amount * tk.smoothstep(0.3 - 0.4 * rust_amount, 0.45, f))
               for s, f in zip(screws, patches)]
    keep = math.exp(-1.0 / (0.25 * height))
    trails = list(sources)
    for x in range(width):
        column = sources[x::width]
        trail, values = 0.0, [0.0] * height
        for _round in range(2):
            for y in range(height):
                trail = max(column[y], trail * keep)
                values[y] = trail
        trails[x::width] = values
    streak_noise = tk.fbm(width, height, 40, 2, tk.hash_u32(seed, 2), cells_y=2)
    grime = tk.fbm(width, height, 6, 3, tk.hash_u32(seed, 3))
    chips = tk.fbm(width, height, 10, 4, tk.hash_u32(seed, 4))
    spangle = tk.voronoi(width, height, 24, 24, tk.hash_u32(seed, 5), jitter=1.0, edges=False)["cell"]
    paint, dirt = p["paint"], p["dirt"]
    red, green, blue, heights, rough, metallic = [], [], [], [], [], []
    for y in range(height):
        base = y * width
        for x in range(width):
            index = base + x
            level = columns[x]
            valley = 1.0 - level
            rusted = min(1.0, max(sources[index], trails[index] * (0.4 + 0.6 * (streak_noise[index] + 0.5))))
            coat = paint * (1.0 - tk.smoothstep(0.25, 0.4, chips[index] + 0.3 * rusted))
            tone = 0.92 + 0.08 * tk.hash_float(spangle[index], seed, 6)
            colour = [m * tone for m in metal]
            colour = [c + (pc * (0.92 + 0.08 * (grime[index] + 0.5)) - c) * coat for c, pc in zip(colour, paint_rgb)]
            colour = [c + (r * (0.8 + 0.3 * (streak_noise[index] + 0.5)) - c) * rusted * 0.85
                      for c, r in zip(colour, rust_rgb)]
            grime_amount = dirt * valley * tk.smoothstep(-0.3, 0.3, grime[index]) * 0.6
            colour = [c + (d - c) * grime_amount for c, d in zip(colour, dirt_rgb)]
            screw = screws[index]
            if screw > 0.0:
                colour = [c + (0.72 * (0.8 + 0.2 * screw) - c) * min(1.0, screw * 3.0) for c in colour]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            heights.append(0.15 + 0.65 * level + 0.15 * screw + 0.02 * rusted)
            metal_share = (1.0 - coat) * (1.0 - rusted * 0.85) * (1.0 - grime_amount)
            metallic.append(metal_share)
            rough.append(metal_share * (0.4 + 0.1 * tone) + (1.0 - metal_share) * (0.6 + 0.3 * rusted))
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.18 / ribs,
                     roughness=rough, metallic=metallic, ao_radius=0.25 / ribs, ao_strength=0.8,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
