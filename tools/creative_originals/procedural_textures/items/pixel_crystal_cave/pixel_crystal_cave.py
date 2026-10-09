"""Pixel-art crystal cave wall: lumpy lit rock with glowing faceted crystal clusters, emissive, tileable.

The rock is a periodic height field on a small art grid (``art_pixels`` square), lit from the top left: the slope
along the light picks one of four rock tones, so the wall reads as lumpy stone, with darker tones in the hollows.
Crystal clusters sit at Poisson-disc points spread over the torus; each cluster is a few crystals, every crystal a
pencil-shaped polygon (a prism with a pointed tip) leaning out from the cluster's foot. A pixel inside a crystal is
shaded by the side of the crystal axis it lies on (a lit face and a dark face), the lit edge takes the highlight,
the tip a white glint, and the outermost ring a dark outline. Rock near a crystal picks up a dithered glow halo.
The emissive map holds the crystals and their halo. The art is enlarged with nearest-neighbour sampling; heights,
normals and occlusion are computed per art pixel. Standard library only.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "pixel_crystal_cave"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.98]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.05, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
    {"name": "emissive", "channels": 3, "colour_space": "srgb", "convention": "gltf_emissive"},
]
PARAMETERS = [
    {"name": "art_pixels", "type": "int", "default": 32, "minimum": 16, "maximum": 64,
     "meaning": "Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling."},
    {"name": "clusters", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of the evenly spread cluster positions that hold crystals."},
    {"name": "crystals", "type": "int", "default": 3, "minimum": 1, "maximum": 5,
     "meaning": "Crystals in each cluster."},
    {"name": "crystal_length", "type": "float", "default": 7.0, "minimum": 3.0, "maximum": 12.0,
     "meaning": "Typical crystal length in art pixels."},
    {"name": "glow", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Strength of the glow halo on the rock around the crystals."},
    {"name": "lumps", "type": "int", "default": 4, "minimum": 2, "maximum": 8,
     "meaning": "Size of the rock lumps: noise cells across the tile."},
    {"name": "relief", "type": "float", "default": 1.0, "minimum": 0.2, "maximum": 2.0,
     "meaning": "Strength of the per-pixel normal map."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo and the glow in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Amethyst clusters glowing violet in dark purple-grey rock.", "values": {}},
    "ice_blue": {"description": "Long pale-blue ice crystals in cold blue-grey rock.",
                 "values": {"crystal_length": 9.0, "crystals": 4, "glow": 0.45}},
    "emerald": {"description": "Short green emeralds scattered in brown-black rock.",
                "values": {"crystal_length": 5.0, "crystals": 2, "clusters": 0.8, "glow": 0.5}},
    "fire_ruby": {"description": "Red-orange crystals with a strong warm glow in charred rock.",
                  "values": {"glow": 1.0, "crystals": 3, "lumps": 6}},
}
#: Per preset: rock tones dark to light, crystal outline, crystal dark face, crystal light face, crystal edge,
#: glint, glow colour (sRGB).
PALETTES = {
    "default": (("#14101c", "#231c30", "#332a44", "#463c5a"), "#2a0f40", "#6a2fa8", "#a65ce8", "#d6a6ff", "#ffffff",
                "#b46cff"),
    "ice_blue": (("#0e141c", "#1a2532", "#283848", "#3a4e62"), "#123048", "#3a86b8", "#7cc6ec", "#c6efff",
                 "#ffffff", "#8ad8ff"),
    "emerald": (("#120e0a", "#211912", "#30261c", "#433628"), "#0a3018", "#1f8a44", "#46c46e", "#a6f2b8",
                "#ffffff", "#5ae08a"),
    "fire_ruby": (("#120a08", "#21130f", "#311c16", "#45281e"), "#3a0808", "#b8240f", "#f05a1f", "#ffb46a",
                  "#fff2c6", "#ff6a2a"),
}
#: Roughness of rock and crystal.
ROUGHNESS = (0.92, 0.08)


def _crystal(foot_u: float, foot_v: float, angle: float, length: float, half_width: float) -> list:
    """Polygon (art pixel coordinates) of a pencil-shaped crystal: a prism from its foot to a pointed tip."""
    du, dv = math.cos(angle), math.sin(angle)
    nu, nv = -dv, du
    shoulder = length - 1.4 * half_width
    return [(foot_u - nu * half_width, foot_v - nv * half_width),
            (foot_u - nu * half_width + du * shoulder, foot_v - nv * half_width + dv * shoulder),
            (foot_u + du * length, foot_v + dv * length),
            (foot_u + nu * half_width + du * shoulder, foot_v + nv * half_width + dv * shoulder),
            (foot_u + nu * half_width, foot_v + nv * half_width)]


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The cave maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    rock_codes, outline_code, dark_code, light_code, edge_code, glint_code, glow_code = PALETTES[preset]
    rock = [tk.hex_rgb(code) for code in rock_codes]
    outline, dark, light, edge, glint, glow = (tk.hex_rgb(code) for code in (outline_code, dark_code, light_code,
                                                                             edge_code, glint_code, glow_code))
    art = p["art_pixels"]
    count = art * art
    lumps = min(p["lumps"], art // 4)
    field = tk.fbm(art, art, lumps, 2, tk.hash_u32(seed, 1))
    colour, emit = [None] * count, [(0.0, 0.0, 0.0)] * count
    heights, rough = [0.0] * count, [ROUGHNESS[0]] * count
    for y in range(art):
        for x in range(art):
            index = y * art + x
            left = field[y * art + (x - 1) % art]
            up = field[((y - 1) % art) * art + x]
            slope = ((field[index] - left) + (field[index] - up)) * art / (2.0 * lumps)
            level = 1.5 + 1.4 * slope + 0.9 * field[index] + 0.3 * (tk.bayer4(x, y) - 0.5)
            tone = max(0, min(3, int(math.floor(level))))
            colour[index], heights[index] = rock[tone], 0.35 + 0.2 * field[index]
    rng = tk.Rng(seed, 0xC7)
    distance_to_crystal = [9.0] * count
    length = min(p["crystal_length"], art * 0.3)
    for u, v in tk.poisson_points(min(0.5, max(0.004, 1.3 * length / art)), tk.hash_u32(seed, 2)):
        if not rng.chance(p["clusters"]):
            continue
        foot_u, foot_v = u * art, v * art + 0.4 * length
        shapes = []
        for _ in range(p["crystals"]):
            angle = -0.5 * math.pi + rng.uniform(-0.75, 0.75)
            size = length * rng.uniform(0.6, 1.1)
            shapes.append((size, _crystal(foot_u + rng.uniform(-1.5, 1.5), foot_v, angle, size,
                                          max(1.3, size * rng.uniform(0.22, 0.3))), angle))
        shapes.sort(key=lambda row: -row[0])
        reach = int(length * 1.3) + 3
        for size, polygon, angle in shapes:
            axis_u, axis_v = math.cos(angle), math.sin(angle)
            for dy in range(-reach - int(length), reach):
                for dx in range(-reach, reach + 1):
                    x, y = int(foot_u) + dx, int(foot_v) + dy
                    px, py = x + 0.5, y + 0.5
                    distance = tk.polygon_distance(px, py, polygon)
                    index = (y % art) * art + x % art
                    if distance > 0.0:
                        distance_to_crystal[index] = min(distance_to_crystal[index], distance)
                        continue
                    side = (px - foot_u) * -axis_v + (py - foot_v) * axis_u
                    along = (px - foot_u) * axis_u + (py - foot_v) * axis_v
                    if distance > -0.55:
                        shade = outline
                    elif along > size - 1.6:
                        shade = glint
                    elif side < 0.0:
                        shade = edge if distance > -1.6 else light
                    else:
                        shade = dark
                    colour[index], rough[index] = shade, ROUGHNESS[1]
                    heights[index] = 0.6 + 0.3 * min(1.0, along / max(size, 1.0))
                    strength = 0.55 if shade is outline else 1.0
                    emit[index] = tuple(strength * c for c in shade)
                    distance_to_crystal[index] = 0.0
    if p["glow"] > 0.0:
        for y in range(art):
            for x in range(art):
                index = y * art + x
                gap = distance_to_crystal[index]
                near = 0.0 < gap < 1.3
                far = 1.3 <= gap < 2.6 and tk.bayer4(x, y) < 0.5 * p["glow"]
                if near or far:
                    mix = 0.45 * p["glow"] if near else 0.25 * p["glow"]
                    colour[index] = tuple((1.0 - mix) * a + mix * b for a, b in zip(colour[index], glow))
                    emit[index] = tuple((0.4 if near else 0.2) * p["glow"] * c for c in glow)
    red, green, blue = ([c[k] for c in colour] for k in range(3))
    graded = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    albedo = tuple(tk.upscale_nearest(channel, art, art, width, height) for channel in graded)
    shine = tk.grade(tuple([e[k] for e in emit] for k in range(3)), p["hue_shift"], 1.0, 1.0)
    emissive = tuple(tk.upscale_nearest(channel, art, art, width, height) for channel in shine)
    normal = tk.upscale_nearest_bytes(tk.normal_map(heights, art, art, p["relief"] * 1.2 / art, directx_normal),
                                      3, art, art, width, height)
    occlusion = [round(value * 8.0) / 8.0 for value in tk.ambient_occlusion(heights, art, art, 1.5 / art, 1.0)]
    return tk.finish(width, height, MAPS, albedo=albedo, heights=tk.upscale_nearest(heights, art, art, width, height),
                     roughness=tk.upscale_nearest(rough, art, art, width, height),
                     ao=tk.upscale_nearest(occlusion, art, art, width, height), normal=normal, emissive=emissive,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
