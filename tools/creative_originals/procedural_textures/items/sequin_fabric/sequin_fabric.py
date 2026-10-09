"""Sequin fabric: overlapping metallic discs in offset rows, each tilted its own way, tileable PBR maps.

Sequins sit in rows with a whole number of sequins across and rows down the tile; odd rows shift by half a sequin,
so the discs pack like scales and the pattern repeats. Every pixel looks at the nine nearest sequins and shows the
one on top: a row covers the upper part of the row below it, and within a row each sequin covers its left
neighbour. A sequin slopes up toward its free lower edge, is slightly dished, carries a random tilt and has a hole in
the middle where the backing fabric and thread show. The tilts make neighbouring sequins catch light differently;
holographic sequins also turn their colour with the tilt direction, as a diffraction foil does.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "sequin_fabric"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.08, 1.0]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "rows", "type": "int", "default": 18, "minimum": 6, "maximum": 40,
     "meaning": "Rows of sequins down the tile; as many sequins run across each row."},
    {"name": "size", "type": "float", "default": 1.35, "minimum": 1.0, "maximum": 1.8,
     "meaning": "Sequin diameter as a multiple of the row spacing: the overlap between neighbours."},
    {"name": "tilt", "type": "float", "default": 0.45, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Random tilt of each sequin, which makes them sparkle differently."},
    {"name": "hole", "type": "float", "default": 0.16, "minimum": 0.0, "maximum": 0.35,
     "meaning": "Radius of the centre hole as a share of the sequin radius (0 for no hole)."},
    {"name": "cup", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How dished (cupped) each sequin is."},
    {"name": "rainbow", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Holographic foil: colour turning with each sequin's tilt direction and across its face."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Gold sequins packed like scales on black mesh.", "values": {}},
    "silver_party": {"description": "Silver sequins with strong random tilts for a lot of sparkle.",
                     "values": {"tilt": 0.75, "cup": 0.3}},
    "holographic": {"description": "Holographic foil sequins whose colour changes with the tilt.",
                    "values": {"rainbow": 1.0, "tilt": 0.6, "rows": 20}},
    "black_gunmetal": {"description": "Small gunmetal sequins lying flat in tight rows.",
                       "values": {"rows": 28, "tilt": 0.2, "size": 1.25, "cup": 0.2}},
    "paillettes_rose": {"description": "Large rose-gold paillettes with small holes and a wide overlap.",
                        "values": {"rows": 8, "size": 1.6, "hole": 0.08, "tilt": 0.35, "cup": 0.6}},
}
#: Sequin colour, backing fabric colour, thread colour, sequin roughness and metallic level per preset.
PALETTES = {
    "default": ("#e2b450", "#151416", "#2a2420", 0.18, 1.0),
    "silver_party": ("#d7d9dd", "#1c1d21", "#8a8c90", 0.14, 1.0),
    "holographic": ("#d9dbe0", "#202024", "#9a9ca0", 0.12, 1.0),
    "black_gunmetal": ("#5a5c62", "#0e0e10", "#1a1a1c", 0.22, 1.0),
    "paillettes_rose": ("#e3a98f", "#3a2a2a", "#6a4a40", 0.2, 1.0),
}


def _hue_rgb(hue: float) -> tuple:
    """A saturated colour for a hue in turns (piecewise linear HSV wheel, value 1, saturation 1)."""
    h = (hue % 1.0) * 6.0
    sector = int(h) % 6
    f = h - math.floor(h)
    return ((1.0, f, 0.0), (1.0 - f, 1.0, 0.0), (0.0, 1.0, f), (0.0, 1.0 - f, 1.0), (f, 0.0, 1.0),
            (1.0, 0.0, 1.0 - f))[sector]


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The sequin fabric maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    code, fabric_code, thread_code, sequin_rough, metal = PALETTES[preset]
    sequin_rgb, fabric_rgb, thread_rgb = tk.hex_rgb(code), tk.hex_rgb(fabric_code), tk.hex_rgb(thread_code)
    n = p["rows"]
    radius = 0.5 * p["size"]
    hole = p["hole"]
    tilt, cup, rainbow = p["tilt"], p["cup"], p["rainbow"]
    rng = tk.Rng(seed, 0x5E)
    discs = []
    for _ in range(n * n):
        angle = rng.uniform(0.0, math.tau)
        amount = tilt * rng.uniform(0.2, 1.0)
        discs.append((amount * math.cos(angle), amount * math.sin(angle), rng.uniform(-1.0, 1.0),
                      angle / math.tau + 0.15 * rng.uniform(-1.0, 1.0)))
    weave = tk.fbm(width, height, min(max(4, min(width, height) // 2), n * 6), 2, tk.hash_u32(seed, 2))
    count = width * height
    heights, red, green, blue, rough, metallic = [0.0] * count, [], [], [], [], []
    for y in range(height):
        gy = (y + 0.5) / height * n
        j0 = int(gy)
        for x in range(width):
            gx = (x + 0.5) / width * n
            index = y * width + x
            chosen = None
            for dj in (-1, 0, 1):
                j = j0 + dj
                shift = 0.5 * (j % 2)
                i0 = int(math.floor(gx - shift))
                for di in (1, 0, -1):
                    i = i0 + di
                    dx = gx - (i + 0.5 + shift)
                    dy = gy - (j + 0.5)
                    r2 = (dx * dx + dy * dy) / (radius * radius)
                    if r2 < 1.0:
                        chosen = (dx / radius, dy / radius, r2, (j % n) * n + i % n)
                        break
                if chosen is not None:
                    break
            if chosen is None:
                heights[index] = 0.05 + 0.05 * weave[index]
                shade = 0.8 + 0.3 * weave[index]
                red.append(fabric_rgb[0] * shade)
                green.append(fabric_rgb[1] * shade)
                blue.append(fabric_rgb[2] * shade)
                rough.append(0.85)
                metallic.append(0.0)
                continue
            sx, sy, r2, key = chosen
            tx, ty, tone, hue = discs[key]
            r = math.sqrt(r2)
            if r < hole:
                heights[index] = 0.12
                red.append(thread_rgb[0])
                green.append(thread_rgb[1])
                blue.append(thread_rgb[2])
                rough.append(0.8)
                metallic.append(0.0)
                continue
            rim = tk.smoothstep(0.86, 1.0, r)
            heights[index] = (0.5 + 0.2 * sy + 0.05 * sx + 0.22 * (tx * sx + ty * sy) + 0.1 * cup * r2
                              - 0.12 * rim)
            shade = 0.9 + 0.08 * tone - 0.25 * rim
            colour = sequin_rgb
            if rainbow > 0.0:
                foil = _hue_rgb(hue + 0.35 * sx + 0.2 * sy)
                colour = [c + (0.35 + 0.65 * f - c) * rainbow for c, f in zip(sequin_rgb, foil)]
            red.append(colour[0] * shade)
            green.append(colour[1] * shade)
            blue.append(colour[2] * shade)
            rough.append(sequin_rough + 0.06 * (tone + 1.0) + 0.3 * rim)
            metallic.append(metal * (1.0 - 0.6 * rim))
    low, high = min(heights), max(heights)
    heights = [(value - low) / (high - low) for value in heights]
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.18 / n, roughness=rough,
                     metallic=metallic, ao_radius=0.25 / n, ao_strength=0.9, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
