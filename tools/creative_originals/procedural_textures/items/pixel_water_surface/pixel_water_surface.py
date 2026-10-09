"""Pixel-art water surface: wave glyphs, sparkles, caustic lines and foam, tileable maps (standard library only).

Water is drawn on a small art grid (``art_pixels`` square): three depth shades come from periodic noise, with an
ordered Bayer dither on the borders. Waves are the classic glyph of pixel-art water, a short light dash over two
darker end pixels, placed by Poisson-disc sampling on the torus so they spread evenly without a visible grid and
wrap around the tile. Sparkles are single bright pixels or small crosses. Shallow water can show a caustic network,
the one-pixel border lines of a Voronoi diagram masked by noise, and rough water can carry foam clusters with
dithered edges. The art is enlarged with nearest-neighbour sampling; heights, normals and occlusion are computed per
art pixel, and roughness stays low on open water.
"""
from __future__ import annotations

import sys

import texkit as tk

IDENTITY = "pixel_water_surface"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.04, 0.95]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "art_pixels", "type": "int", "default": 32, "minimum": 16, "maximum": 64,
     "meaning": "Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling."},
    {"name": "waves", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of the evenly spread wave positions that get a wave glyph."},
    {"name": "wave_length", "type": "int", "default": 3, "minimum": 2, "maximum": 6,
     "meaning": "Length of the light dash of a wave glyph in art pixels."},
    {"name": "sparkles", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Density of bright sparkles."},
    {"name": "caustics", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Coverage of the caustic light network of shallow water."},
    {"name": "foam", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Coverage of foam clusters."},
    {"name": "depth_patches", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Contrast of the deep and shallow patches."},
    {"name": "relief", "type": "float", "default": 1.0, "minimum": 0.2, "maximum": 2.0,
     "meaning": "Strength of the per-pixel normal map."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Open sea blue with white wave glyphs and sparkles.", "values": {}},
    "shallow_lagoon": {"description": "Clear turquoise shallows with a caustic light network.",
                       "values": {"caustics": 0.8, "waves": 0.25, "sparkles": 0.4, "depth_patches": 0.3}},
    "swamp": {"description": "Still murky green water with a few ripples and scum.",
              "values": {"waves": 0.35, "wave_length": 2, "sparkles": 0.05, "foam": 0.35, "depth_patches": 0.7}},
    "rapids": {"description": "Rough grey-blue river water with long waves and foam.",
               "values": {"waves": 1.0, "wave_length": 5, "foam": 0.45, "sparkles": 0.2}},
}
#: Per preset: deep, mid and shallow water, wave shadow, wave light, sparkle, caustic line and foam (sRGB).
PALETTES = {
    "default": ("#16437a", "#1d5a9c", "#2a74b8", "#123766", "#9fd2f0", "#ffffff", "#5fa6dc", "#e9f6fb"),
    "shallow_lagoon": ("#13807c", "#1c9e94", "#2fbcab", "#0f6a68", "#b8f3e6", "#ffffff", "#8ff0de", "#f0fffb"),
    "swamp": ("#2c3a1f", "#38482a", "#475a33", "#212c17", "#8a9c5c", "#c9d79a", "#5f7440", "#a3b26f"),
    "rapids": ("#2f4a5c", "#3d5d72", "#4f7489", "#253a49", "#c4dde8", "#ffffff", "#7fa6ba", "#f2f7f9"),
}
#: Roughness of open water, wave crest, caustic line and foam.
ROUGHNESS = (0.06, 0.12, 0.08, 0.8)


def _at(x: int, y: int, art: int) -> int:
    return (y % art) * art + (x % art)


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The water maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    deep, mid, shallow, trough, crest, sparkle, caustic, foam = (tk.hex_rgb(code) for code in PALETTES[preset])
    shades = (deep, mid, shallow)
    art = p["art_pixels"]
    count = art * art
    depth = tk.fbm(art, art, max(2, art // 12), 2, tk.hash_u32(seed, 1))
    colour, heights, rough = [None] * count, [0.0] * count, [ROUGHNESS[0]] * count
    for y in range(art):
        for x in range(art):
            index = y * art + x
            level = 1.0 + 1.8 * p["depth_patches"] * depth[index] + 0.3 * (tk.bayer4(x, y) - 0.5)
            tone = 0 if level < 0.5 else 2 if level >= 1.5 else 1
            colour[index], heights[index] = shades[tone], 0.36 + 0.03 * tone
    if p["caustics"] > 0.0:
        cells = max(2, art // 6)
        network = tk.voronoi(art, art, cells, cells, tk.hash_u32(seed, 2), jitter=0.85)["edge"]
        mask = tk.fbm(art, art, max(2, art // 10), 2, tk.hash_u32(seed, 3))
        line = 0.55 * cells / art
        for index in range(count):
            if network[index] < line and mask[index] < 2.0 * p["caustics"] - 1.0 + 0.3:
                colour[index], heights[index], rough[index] = caustic, 0.42, ROUGHNESS[2]
    if p["foam"] > 0.0:
        froth = tk.fbm(art, art, max(3, art // 6), 3, tk.hash_u32(seed, 4))
        for y in range(art):
            for x in range(art):
                index = y * art + x
                level = 1.6 * froth[index] + 2.0 * p["foam"] - 1.2 + 0.15 * (tk.bayer4(x, y) - 0.5)
                if level > 0.0:
                    colour[index] = foam if level > 0.15 else crest
                    heights[index], rough[index] = 0.5 + 0.2 * min(level, 0.5), ROUGHNESS[3]
    length = p["wave_length"]
    rng = tk.Rng(seed, 0x3C)
    if p["waves"] > 0.0:
        for u, v in tk.poisson_points(min(0.5, (length + 2.5) / art), tk.hash_u32(seed, 5)):
            if not rng.chance(p["waves"]):
                continue
            x, y = int(u * art), int(v * art)
            for dx in range(length):
                index = _at(x + dx, y, art)
                colour[index], heights[index], rough[index] = crest, 0.5, ROUGHNESS[1]
            for dx in (-1, length):
                index = _at(x + dx, y + 1, art)
                colour[index], heights[index] = trough, 0.3
    for u, v in tk.poisson_points(min(0.5, 5.0 / art), tk.hash_u32(seed, 6)):
        if not rng.chance(p["sparkles"] * 0.5):
            continue
        x, y = int(u * art), int(v * art)
        cross = art >= 32 and rng.chance(0.4)
        points = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)) if cross else ((0, 0),)
        for dx, dy in points:
            index = _at(x + dx, y + dy, art)
            colour[index], heights[index], rough[index] = sparkle if (dx, dy) == (0, 0) else crest, 0.52, ROUGHNESS[1]
    red, green, blue = ([c[k] for c in colour] for k in range(3))
    graded = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    albedo = tuple(tk.upscale_nearest(channel, art, art, width, height) for channel in graded)
    normal = tk.upscale_nearest_bytes(tk.normal_map(heights, art, art, p["relief"] * 1.5 / art, directx_normal),
                                      3, art, art, width, height)
    occlusion = [round(value * 8.0) / 8.0 for value in tk.ambient_occlusion(heights, art, art, 1.5 / art, 0.8)]
    return tk.finish(width, height, MAPS, albedo=albedo, heights=tk.upscale_nearest(heights, art, art, width, height),
                     roughness=tk.upscale_nearest(rough, art, art, width, height),
                     ao=tk.upscale_nearest(occlusion, art, art, width, height), normal=normal,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
