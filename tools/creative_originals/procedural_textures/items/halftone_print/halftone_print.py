"""Halftone print: CMYK, comic, newsprint or duotone dot screens on paper, tileable maps (standard library).

A procedural design (a vivid poster, flat comic regions with black outlines, or a soft grey photograph) is separated
into ink coverages: cyan, magenta and yellow from the colour, black from their common part (grey component
replacement), or a single darkness channel. Each ink is screened on its own rotated square lattice; the lattice
vectors are whole numbers (p, q), so the screen angle is close to the classic one (cyan 15, magenta 75, yellow 0,
black 45 degrees) and the screen still repeats exactly across the tile. A pixel is inked where the coverage exceeds a
round-dot spot function: the share of a lattice cell that lies closer to its centre than the pixel does, taken from a
table over the unit cell, so dots grow as circles and merge into checkerboards past half coverage. Inks multiply
over the paper like transparent process inks; screens are offset a little from each other (misregistration).

Paper has fibres and patchy yellowing; ink sits a hair above the paper and is slightly glossier.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "halftone_print"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.03, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.3, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "lines", "type": "int", "default": 40, "minimum": 8, "maximum": 128,
     "meaning": "Screen lines (dot rows) across the tile."},
    {"name": "design_scale", "type": "int", "default": 2, "minimum": 1, "maximum": 6,
     "meaning": "Features of the printed design across the tile."},
    {"name": "misregister", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Offset between the ink screens, as on a loose press."},
    {"name": "dot_gain", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 0.5,
     "meaning": "Dots printing larger than their coverage, as ink spreads in the paper."},
    {"name": "yellowing", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Age yellowing of the paper in patches."},
    {"name": "fibres", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Visible paper fibres in colour and relief."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Four-colour magazine print of a vivid poster at classic screen angles.", "values": {}},
    "comic_dots": {"description": "Comic print: flat dot tints in large dots with solid black outlines on newsprint.",
                   "values": {"lines": 22, "misregister": 0.5, "yellowing": 0.45, "dot_gain": 0.25}},
    "newsprint_mono": {"description": "Black-only newspaper photograph at 45 degrees on grey, aged paper.",
                       "values": {"lines": 48, "misregister": 0.0, "yellowing": 0.6, "fibres": 0.7}},
    "riso_duotone": {"description": "Two fluorescent inks, pink and teal, coarse dots and loose registration.",
                     "values": {"lines": 28, "misregister": 1.0, "dot_gain": 0.3, "yellowing": 0.05}},
}
#: Per preset: design (0 poster, 1 comic regions, 2 grey photograph), paper colour (sRGB) and the inks as
#: (ink colour sRGB, screen angle in degrees, channel: 0 cyan, 1 magenta, 2 yellow, 3 black, 4 darkness).
PRINTS = {
    "default": (0, "#f4f1e8", [("#00a0dc", 15.0, 0), ("#e0207a", 75.0, 1), ("#f6e000", 0.0, 2),
                                ("#1c1c1e", 45.0, 3)]),
    "comic_dots": (1, "#efe6cc", [("#00a0dc", 15.0, 0), ("#e0207a", 75.0, 1), ("#f6e000", 0.0, 2),
                                   ("#141414", 45.0, 3)]),
    "newsprint_mono": (2, "#dcd8cc", [("#202020", 45.0, 4)]),
    "riso_duotone": (0, "#f2efe6", [("#ff4f9a", 15.0, 1), ("#178f8f", 75.0, 0)]),
}
#: Comic region tints as (cyan, magenta, yellow, black) coverage.
COMIC_TINTS = [(0.0, 0.25, 0.45, 0.0), (0.55, 0.05, 0.0, 0.0), (0.0, 0.0, 0.85, 0.0), (0.0, 0.7, 0.75, 0.0)]


def _spot_table(steps: int = 1024) -> list:
    """The share of a unit lattice cell whose distance to the nearest lattice point is below sqrt(k / steps * 0.5),
    for k = 0 .. steps: the round-dot spot function, by counting a fine grid over the cell."""
    grid = 160
    squares = sorted(((x + 0.5) / grid - 0.5) ** 2 + ((y + 0.5) / grid - 0.5) ** 2
                     for y in range(grid) for x in range(grid))
    table, cursor = [], 0
    total = len(squares)
    for k in range(steps + 1):
        limit = k / steps * 0.5
        while cursor < total and squares[cursor] <= limit:
            cursor += 1
        table.append(cursor / total)
    return table


_SPOT = _spot_table()


def screen_vector(lines: int, angle: float) -> tuple:
    """Whole-number lattice vector (p, q) for a screen of about ``lines`` rows across the tile at ``angle`` degrees."""
    p = round(lines * math.cos(math.radians(angle)))
    q = round(lines * math.sin(math.radians(angle)))
    return (p, q) if (p, q) != (0, 0) else (1, 0)


def _design(kind: int, width: int, height: int, seed: int, scale: int) -> list:
    """Ink coverages (cyan, magenta, yellow, black, darkness) of the printed design, each a field in 0..1."""
    count = width * height
    offset_u = tk.fbm(width, height, scale, 3, tk.hash_u32(seed, 11))
    offset_v = tk.fbm(width, height, scale, 3, tk.hash_u32(seed, 12))
    base = tk.warp(tk.fbm(width, height, scale, 4, tk.hash_u32(seed, 13)), width, height, offset_u, offset_v, 0.12)
    channels = [[0.0] * count for _ in range(5)]
    if kind == 0:
        tone = tk.warp(tk.fbm(width, height, scale + 1, 4, tk.hash_u32(seed, 14)), width, height, offset_v,
                       offset_u, 0.1)
        rgb = tk.ramp([0.5 + 0.9 * b for b in base], [(0.0, "#1a2a6a"), (0.3, "#2a9ad0"), (0.5, "#f4e8c0"),
                                                      (0.68, "#f0a020"), (0.85, "#d02040"), (1.0, "#5a1040")])
        for index in range(count):
            light = 0.85 + 0.3 * tone[index]
            c, m, y = (tk.clamp(1.0 - channel[index] * light) for channel in rgb)
            k = 0.8 * min(c, m, y)
            spare = max(1e-6, 1.0 - k)
            for channel, value in enumerate(((c - k) / spare, (m - k) / spare, (y - k) / spare, k)):
                channels[channel][index] = tk.clamp(value)
            channels[4][index] = tk.clamp(1.0 - (0.2126 * rgb[0][index] + 0.7152 * rgb[1][index] +
                                                0.0722 * rgb[2][index]) * light)
    elif kind == 1:
        levels = (-0.18, 0.05, 0.25)
        outline = [min(values) for values in zip(*(tk.isoline_distance(base, width, height, level)
                                                    for level in levels))]
        pixel = 1.0 / min(width, height)
        for index in range(count):
            value = base[index]
            region = sum(value > level for level in levels)
            for channel, tint in enumerate(COMIC_TINTS[region]):
                channels[channel][index] = tint
            ink = tk.smoothstep(0.0035 + pixel, 0.0035, outline[index])
            channels[3][index] = max(channels[3][index], ink)
            channels[4][index] = 0.3 + 0.4 * ink
    else:
        detail = tk.fbm(width, height, 4 * scale, 4, tk.hash_u32(seed, 15))
        for index in range(count):
            dark = tk.clamp(0.5 + 0.75 * base[index] + 0.18 * detail[index])
            channels[4][index] = dark
            channels[3][index] = dark
    return channels


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The halftone maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    design, paper_hex, inks = PRINTS[preset]
    coverage = _design(design, width, height, seed, p["design_scale"])
    count = width * height
    rng = tk.Rng(seed, 0x4A1)
    gain = p["dot_gain"]
    layers = []
    steps = len(_SPOT) - 1
    for ink_hex, angle, channel in inks:
        pq, qq = screen_vector(p["lines"], angle)
        shift_u = p["misregister"] * rng.uniform(-0.004, 0.004)
        shift_v = p["misregister"] * rng.uniform(-0.004, 0.004)
        spacing = math.hypot(pq, qq)
        soft = 0.7 * spacing / min(width, height)
        field = coverage[channel]
        inked = []
        for y in range(height):
            v = (y + 0.5) / height + shift_v
            row = field[y * width:(y + 1) * width]
            for x in range(width):
                u = (x + 0.5) / width + shift_u
                a, b = pq * u + qq * v, -qq * u + pq * v
                da, db = a - math.floor(a + 0.5), b - math.floor(b + 0.5)
                square = da * da + db * db
                spot = _SPOT[min(steps, int(square * 2.0 * steps))]
                level = row[x]
                level = level + gain * level * (1.0 - level) * 2.0
                edge = 6.3 * math.sqrt(square) * soft + 1e-4
                inked.append(tk.clamp(0.5 + (level - spot) / (2.0 * edge)) if level > 0.002 else 0.0)
        layers.append((tk.hex_rgb(ink_hex), inked))
    fibre = tk.fbm(width, height, 96, 3, tk.hash_u32(seed, 21), cells_y=24)
    blotch = tk.fbm(width, height, 3, 4, tk.hash_u32(seed, 22))
    grain = tk.white_noise(width, height, tk.hash_u32(seed, 23))
    paper = tk.hex_rgb(paper_hex)
    aged = (0.85, 0.74, 0.5)
    red, green, blue, heights, rough = [], [], [], [], []
    for index in range(count):
        yellow = p["yellowing"] * tk.smoothstep(-0.2, 0.5, blotch[index])
        threads = p["fibres"] * (fibre[index] * 0.5 + 0.5)
        base = [c + (a - c) * 0.5 * yellow for c, a in zip(paper, aged)]
        base = [c * (0.97 + 0.05 * threads - 0.03 * p["fibres"] + 0.02 * grain[index]) for c in base]
        total = 0.0
        for ink, inked in layers:
            amount = inked[index]
            total += amount
            base = [c * (1.0 + (i - 1.0) * amount) for c, i in zip(base, ink)]
        red.append(base[0])
        green.append(base[1])
        blue.append(base[2])
        heights.append(0.4 + 0.25 * threads + 0.06 * min(1.0, total) + 0.03 * grain[index])
        rough.append(0.88 - 0.22 * min(1.0, total) + 0.06 * threads)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.004, roughness=rough,
                     ao_radius=0.004, ao_strength=0.5, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
