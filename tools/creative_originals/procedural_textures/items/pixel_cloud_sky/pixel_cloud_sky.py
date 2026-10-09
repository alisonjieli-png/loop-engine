"""Pixel-art sky with puffy outlined clouds, tiling in both directions (standard library only).

The sky is drawn on a small art grid (``art_pixels`` square): a flat colour broken into faint patches of a second
tone by an ordered Bayer dither of low-frequency noise, so it tiles vertically as well as horizontally. Clouds sit at
Poisson-disc points of the torus. Each cloud is a union of round puffs: a row of small puffs along a flat base and a
few larger puffs heaped above, cut off below the base line. Clouds are painted from the top of the tile to the
bottom, so lower clouds pass in front. A cloud pixel is lit by the puff it lies in: the offset from the puff centre
along a light from the top left picks the highlight, the body or the shade colour, and the two rows above the base
are always in shade. An optional one-pixel outline rings each cloud, and night skies get stars. The art is enlarged
with nearest-neighbour sampling; heights (a dome per puff), normals and occlusion are computed per art pixel.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "pixel_cloud_sky"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.3, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "art_pixels", "type": "int", "default": 32, "minimum": 16, "maximum": 64,
     "meaning": "Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling."},
    {"name": "clouds", "type": "float", "default": 0.7, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of the evenly spread cloud positions that hold a cloud."},
    {"name": "cloud_width", "type": "float", "default": 12.0, "minimum": 6.0, "maximum": 24.0,
     "meaning": "Typical cloud width in art pixels."},
    {"name": "puffiness", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Height of the puffs heaped above the cloud base."},
    {"name": "outline", "type": "int", "default": 1, "minimum": 0, "maximum": 1,
     "meaning": "1 rings each cloud with a one-pixel outline."},
    {"name": "stars", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Density of stars in the open sky."},
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
    "default": {"description": "Blue day sky with white outlined cumulus clouds.", "values": {}},
    "sunset": {"description": "Orange and pink evening sky with violet clouds lit gold from above.",
               "values": {"cloud_width": 16.0, "puffiness": 0.4, "outline": 0}},
    "night": {"description": "Dark navy night sky with grey-blue clouds and stars.",
              "values": {"stars": 0.7, "clouds": 0.45, "puffiness": 0.5}},
    "storm": {"description": "Heavy grey storm clouds filling a dark grey sky.",
              "values": {"clouds": 1.0, "cloud_width": 18.0, "puffiness": 0.9, "outline": 0}},
}
#: Per preset: sky, sky patch, outline, cloud shade, cloud body, cloud highlight, star (sRGB).
PALETTES = {
    "default": ("#4a8fe0", "#5a9dea", "#3a74c0", "#b6cbe6", "#e8f0fa", "#ffffff", "#ffffff"),
    "sunset": ("#e8805a", "#f0966a", "#a0506a", "#8c5a8c", "#c487a8", "#ffd27a", "#fff2c0"),
    "night": ("#0f1630", "#141c3a", "#0a0f22", "#2f3d5e", "#4a5a80", "#7486ac", "#f2f4ff"),
    "storm": ("#4c5560", "#535c68", "#2c323a", "#3a414b", "#5d6672", "#7f8894", "#d0d4da"),
}
#: Roughness of the open sky and of the clouds.
ROUGHNESS = (0.5, 0.95)


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The sky maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    sky, patch, edge, shade, body, highlight, star = (tk.hex_rgb(code) for code in PALETTES[preset])
    art = p["art_pixels"]
    count = art * art
    haze = tk.fbm(art, art, max(2, art // 16), 2, tk.hash_u32(seed, 1))
    colour, heights, rough = [None] * count, [0.1] * count, [ROUGHNESS[0]] * count
    for y in range(art):
        for x in range(art):
            index = y * art + x
            colour[index] = patch if haze[index] + 0.25 * (tk.bayer4(x, y) - 0.5) > 0.25 else sky
            heights[index] = 0.1 + 0.03 * haze[index]
    rng = tk.Rng(seed, 0x5C)
    cloud_width = min(p["cloud_width"], art * 0.7)
    owner = [-1] * count
    clouds = []
    for u, v in tk.poisson_points(min(0.5, max(0.004, 0.75 * cloud_width / art)), tk.hash_u32(seed, 2)):
        if rng.chance(p["clouds"]):
            clouds.append((u * art, v * art))
    clouds.sort(key=lambda row: row[1])
    for number, (cu, base) in enumerate(clouds):
        span = cloud_width * rng.uniform(0.75, 1.15)
        small = max(1.6, span / 6.0)
        puffs = []
        steps = max(2, int(span / (1.4 * small)))
        for k in range(steps + 1):
            puffs.append((cu - span / 2.0 + span * k / steps, base - small * 0.6, small * rng.uniform(0.9, 1.2)))
        for _ in range(1 + round(2 * p["puffiness"])):
            radius = small * (1.3 + 1.3 * p["puffiness"] * rng.random())
            puffs.append((cu + rng.uniform(-0.3, 0.3) * span, base - radius * 0.9, radius))
        top = min(py - r for _px, py, r in puffs)
        inside = {}
        for y in range(int(math.floor(top)) - 1, int(math.ceil(base)) + 1):
            for x in range(int(math.floor(cu - span / 2.0 - 3 * small)), int(math.ceil(cu + span / 2.0 + 3 * small))):
                px, py = x + 0.5, y + 0.5
                if py > base:
                    continue
                best = None
                for qx, qy, radius in puffs:
                    depth = 1.0 - math.hypot(px - qx, py - qy) / radius
                    if depth >= 0.0 and (best is None or depth > best[0]):
                        best = (depth, (px - qx) / radius, (py - qy) / radius)
                if best is not None:
                    inside[(x, y)] = best
        for (x, y), (depth, ox, oy) in inside.items():
            index = (y % art) * art + x % art
            facing = -(ox + oy) * 0.8
            tone = shade if base - (y + 0.5) < 2.0 else highlight if facing > 0.45 else body if facing > -0.35 \
                else shade
            colour[index], rough[index], owner[index] = tone, ROUGHNESS[1], number
            heights[index] = 0.45 + 0.45 * math.sqrt(max(0.0, depth * (2.0 - depth)))
        if p["outline"]:
            for (x, y) in inside:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if (x + dx, y + dy) not in inside:
                        target = ((y + dy) % art) * art + (x + dx) % art
                        if owner[target] != number:
                            colour[target], heights[target], owner[target] = edge, 0.3, number
                            rough[target] = ROUGHNESS[1]
    if p["stars"] > 0.0:
        for u, v in tk.poisson_points(min(0.5, 3.0 / art), tk.hash_u32(seed, 3)):
            x, y = int(u * art), int(v * art)
            index = y * art + x
            if owner[index] < 0 and rng.chance(p["stars"] * 0.5):
                colour[index] = star
                if art >= 32 and rng.chance(0.2):
                    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        target = ((y + dy) % art) * art + (x + dx) % art
                        if owner[target] < 0:
                            colour[target] = tuple(0.5 * a + 0.5 * b for a, b in zip(star, sky))
    red, green, blue = ([c[k] for c in colour] for k in range(3))
    graded = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    albedo = tuple(tk.upscale_nearest(channel, art, art, width, height) for channel in graded)
    normal = tk.upscale_nearest_bytes(tk.normal_map(heights, art, art, p["relief"] * 0.8 / art, directx_normal),
                                      3, art, art, width, height)
    occlusion = [round(value * 8.0) / 8.0 for value in tk.ambient_occlusion(heights, art, art, 2.0 / art, 0.8)]
    return tk.finish(width, height, MAPS, albedo=albedo, heights=tk.upscale_nearest(heights, art, art, width, height),
                     roughness=tk.upscale_nearest(rough, art, art, width, height),
                     ao=tk.upscale_nearest(occlusion, art, art, width, height), normal=normal,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
