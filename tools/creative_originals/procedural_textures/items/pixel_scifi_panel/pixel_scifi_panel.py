"""Pixel-art sci-fi hull panels: seams, rivets, vents, grilles, hazard stripes and glowing lights, tileable.

The tile is one module of plating on a small art grid (``art_pixels`` square): a grid of ``panels`` by ``panels``
cells, each split once or twice more at random into smaller plates, so the module mixes large and small panels and
repeats cleanly at the tile edges, as modular plating does. Every plate owns the seam on its top and left edge, its
next row and column are a lit bevel and its last row and column a shadow bevel. Each plate then gets one detail: a
plain face with corner rivets, a stack of vent slits, a grille of holes, a glowing light strip, a cluster of
indicator lights, or diagonal hazard stripes. Plates are metallic in the metallic map; lights are glass and appear in
the emissive map. The art is enlarged with nearest-neighbour sampling; heights, normals and occlusion are computed
per art pixel. Standard library only.
"""
from __future__ import annotations

import sys

import texkit as tk

IDENTITY = "pixel_scifi_panel"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.98]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.1, 1.0]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
    {"name": "emissive", "channels": 3, "colour_space": "srgb", "convention": "gltf_emissive"},
]
PARAMETERS = [
    {"name": "art_pixels", "type": "int", "default": 32, "minimum": 16, "maximum": 64,
     "meaning": "Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling."},
    {"name": "panels", "type": "int", "default": 2, "minimum": 1, "maximum": 4,
     "meaning": "Main panel cells across the tile before subdivision."},
    {"name": "subdivision", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Chance that a panel is split into smaller plates."},
    {"name": "lights", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of plates carrying a light strip or indicator lights."},
    {"name": "vents", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of plates carrying vent slits or a grille."},
    {"name": "hazard", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of plates painted with diagonal hazard stripes."},
    {"name": "rivets", "type": "int", "default": 1, "minimum": 0, "maximum": 1,
     "meaning": "1 puts rivets in the corners of plain plates."},
    {"name": "relief", "type": "float", "default": 1.0, "minimum": 0.2, "maximum": 2.0,
     "meaning": "Strength of the per-pixel normal map."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo and the lights in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Grey space-station plating with cyan light strips.", "values": {}},
    "clean_lab": {"description": "White laboratory panels with blue lights and few vents.",
                  "values": {"vents": 0.15, "lights": 0.45, "subdivision": 0.4}},
    "rusty_industrial": {"description": "Dark brown industrial plating with amber lights and hazard stripes.",
                         "values": {"hazard": 0.3, "vents": 0.45, "lights": 0.2, "panels": 3}},
    "alien_hull": {"description": "Violet-black alien hull with green glowing seams of light.",
                   "values": {"lights": 0.6, "vents": 0.2, "rivets": 0, "subdivision": 0.8}},
}
#: Per preset: seam, plate shadow, plate, plate light, bevel highlight, vent dark, light glass, light glow,
#: indicator colours, hazard stripe colours (sRGB), and plate roughness.
PALETTES = {
    "default": (("#16181d", "#3f444e", "#59606c", "#6b7380", "#8d96a4", "#22252b", "#2c6e7c", "#7ff4ff"),
                ("#7ff4ff", "#ff5a4a", "#ffd04a"), ("#d8b02a", "#202022"), 0.4),
    "clean_lab": (("#7c8796", "#b9c2ce", "#d3dae3", "#e2e7ee", "#f4f7fb", "#5d6672", "#2f5c9c", "#8ac8ff"),
                  ("#8ac8ff", "#7dff9c", "#ffb44a"), ("#e0b32e", "#3a3a3e"), 0.3),
    "rusty_industrial": (("#140f0c", "#3d2c22", "#55402f", "#664e3a", "#82684f", "#1d1612", "#7a4a12", "#ffb347"),
                         ("#ffb347", "#ff4a2a", "#9cff5a"), ("#e3a92a", "#1a1716"), 0.6),
    "alien_hull": (("#0c0612", "#2a1d38", "#3a2a4c", "#48365c", "#5f4a78", "#130c1b", "#1f6a3a", "#7dff8f"),
                   ("#7dff8f", "#e46bff", "#6bf3ff"), ("#7dff8f", "#0c0612"), 0.3),
}
#: Detail kinds a plate can carry.
DETAILS = (PLAIN, VENT, GRILLE, STRIP, INDICATORS, HAZARD) = range(6)


def _plates(rng, art: int, panels: int, subdivision: float) -> list:
    """Plate rectangles (x0, y0, x1, y1) in art pixels: a panel grid, each cell split up to twice."""
    bounds = [round(k * art / panels) for k in range(panels + 1)]
    pending = [(bounds[i], bounds[j], bounds[i + 1], bounds[j + 1], 2) for j in range(panels) for i in range(panels)]
    plates = []
    while pending:
        x0, y0, x1, y1, depth = pending.pop()
        wide, tall = x1 - x0, y1 - y0
        if depth and rng.chance(subdivision) and max(wide, tall) >= 10:
            if wide >= tall:
                cut = x0 + rng.integer(5, wide - 5)
                pending += [(x0, y0, cut, y1, depth - 1), (cut, y0, x1, y1, depth - 1)]
            else:
                cut = y0 + rng.integer(5, tall - 5)
                pending += [(x0, y0, x1, cut, depth - 1), (x0, cut, x1, y1, depth - 1)]
        else:
            plates.append((x0, y0, x1, y1))
    return plates


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The panel maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    codes, indicator_codes, hazard_codes, plate_rough = PALETTES[preset]
    seam, shadow, plate, light, highlight, vent, glass, glow = (tk.hex_rgb(code) for code in codes)
    indicators = [tk.hex_rgb(code) for code in indicator_codes]
    stripe_a, stripe_b = (tk.hex_rgb(code) for code in hazard_codes)
    art = p["art_pixels"]
    count = art * art
    rng = tk.Rng(seed, 0x5F)
    panels = min(p["panels"], art // 8)
    dark = (0.0, 0.0, 0.0)
    colour, emit = [plate] * count, [dark] * count
    heights, rough, metal = [0.6] * count, [plate_rough] * count, [1.0] * count

    def put(x: int, y: int, shade, level: float, roughness: float, metallic: float, light_colour=dark) -> None:
        index = (y % art) * art + x % art
        colour[index], heights[index], rough[index], metal[index], emit[index] = (shade, level, roughness, metallic,
                                                                                   light_colour)

    for x0, y0, x1, y1 in _plates(rng, art, panels, p["subdivision"]):
        draw = rng.random()
        if draw < p["lights"]:
            detail = STRIP if rng.chance(0.6) else INDICATORS
        elif draw < p["lights"] + p["vents"]:
            detail = VENT if rng.chance(0.6) else GRILLE
        elif draw < p["lights"] + p["vents"] + p["hazard"]:
            detail = HAZARD
        else:
            detail = PLAIN
        for y in range(y0, y1):
            for x in range(x0, x1):
                if x == x0 or y == y0:
                    put(x, y, seam, 0.1, 0.7, 0.3)
                elif x == x0 + 1 or y == y0 + 1:
                    put(x, y, highlight, 0.56, plate_rough, 1.0)
                elif x == x1 - 1 or y == y1 - 1:
                    put(x, y, shadow, 0.52, plate_rough, 1.0)
                elif detail == HAZARD:
                    band = ((x + y) // 3) % 2
                    put(x, y, stripe_a if band else stripe_b, 0.6, 0.55, 0.0)
        inner = (x0 + 3, y0 + 3, x1 - 2, y1 - 2)
        if inner[2] - inner[0] < 2 or inner[3] - inner[1] < 2:
            continue
        if detail == PLAIN and p["rivets"]:
            for x, y in ((inner[0] - 1, inner[1] - 1), (inner[2], inner[1] - 1), (inner[0] - 1, inner[3]),
                         (inner[2], inner[3])):
                if x0 + 1 < x < x1 - 1 and y0 + 1 < y < y1 - 1:
                    put(x, y, highlight, 0.68, 0.3, 1.0)
                    put(x + 1, y + 1, shadow, 0.55, plate_rough, 1.0)
        elif detail == VENT:
            for y in range(inner[1], inner[3], 2):
                for x in range(inner[0], inner[2]):
                    put(x, y, vent, 0.3, 0.8, 0.6)
        elif detail == GRILLE:
            for y in range(inner[1], inner[3], 2):
                for x in range(inner[0] + (y // 2) % 2, inner[2], 2):
                    put(x, y, vent, 0.28, 0.8, 0.6)
        elif detail == STRIP:
            across = inner[2] - inner[0] >= inner[3] - inner[1]
            middle = (inner[1] + inner[3]) // 2 if across else (inner[0] + inner[2]) // 2
            span = range(inner[0], inner[2]) if across else range(inner[1], inner[3])
            for along in span:
                for offset in (-1, 0, 1):
                    x, y = (along, middle + offset) if across else (middle + offset, along)
                    if offset:
                        put(x, y, vent, 0.45, 0.6, 0.5)
                    else:
                        put(x, y, glow, 0.5, 0.15, 0.0, glow)
        elif detail == INDICATORS:
            dots = min(3, (inner[2] - inner[0]) // 2)
            for k in range(dots):
                x, y = inner[0] + 2 * k, inner[1]
                lamp = indicators[rng.integer(0, len(indicators) - 1)]
                put(x, y, lamp, 0.62, 0.15, 0.0, lamp)
                put(x, y + 1, glass, 0.5, 0.3, 0.0)
    red, green, blue = ([c[k] for c in colour] for k in range(3))
    graded = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    albedo = tuple(tk.upscale_nearest(channel, art, art, width, height) for channel in graded)
    shine = tk.grade(tuple([e[k] for e in emit] for k in range(3)), p["hue_shift"], 1.0, 1.0)
    emissive = tuple(tk.upscale_nearest(channel, art, art, width, height) for channel in shine)
    normal = tk.upscale_nearest_bytes(tk.normal_map(heights, art, art, p["relief"] * 1.4 / art, directx_normal),
                                      3, art, art, width, height)
    occlusion = [round(value * 8.0) / 8.0 for value in tk.ambient_occlusion(heights, art, art, 1.5 / art, 1.0)]
    return tk.finish(width, height, MAPS, albedo=albedo, heights=tk.upscale_nearest(heights, art, art, width, height),
                     roughness=tk.upscale_nearest(rough, art, art, width, height),
                     metallic=tk.upscale_nearest(metal, art, art, width, height),
                     ao=tk.upscale_nearest(occlusion, art, art, width, height), normal=normal, emissive=emissive,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
