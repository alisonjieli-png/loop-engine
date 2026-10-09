"""Carpet seen from above: cut pile, loop pile, flecked berber or shag, tileable PBR maps (standard library only).

Tufts sit on a jittered grid with a whole number of tufts across and down the tile, so the carpet repeats. A cut-pile
tuft is a domed bundle of yarn ends with its plies twisted into a spiral; a loop is a capsule along its tufting row
with diagonal ply grooves, and rows of loops leave a groove between them; berber uses fat, nubby loops in a flecked
yarn. Shag lays long bent strands over a short base pile, painted with a z-buffer so they cross and cover each other.
Pile shading, the light and dark patches where the pile lies in different directions, comes from smooth noise.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "carpet_pile"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.6, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "pile", "type": "int", "default": 0, "minimum": 0, "maximum": 3,
     "meaning": "0 cut pile (tuft tips), 1 loop pile in rows, 2 berber (fat flecked loops), 3 shag (long strands "
                "over a short pile)."},
    {"name": "tufts", "type": "int", "default": 44, "minimum": 12, "maximum": 96,
     "meaning": "Tufts (or loops) across the tile width; the grid is square, so as many rows run down the tile."},
    {"name": "tuft_size", "type": "float", "default": 0.85, "minimum": 0.5, "maximum": 1.2,
     "meaning": "Tuft or loop thickness relative to the tuft spacing; low values show the backing."},
    {"name": "twist", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Visibility of the twisted plies in each tuft or loop."},
    {"name": "flecks", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of tufts in the fleck colour, as in berber or tweed carpets."},
    {"name": "shading", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Light and dark patches of pile lying in different directions."},
    {"name": "shag_length", "type": "float", "default": 0.07, "minimum": 0.02, "maximum": 0.14,
     "meaning": "Length of the long shag strands in texture units (pile 3 only)."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Beige cut-pile plush carpet with soft shading.", "values": {}},
    "grey_loop": {"description": "Grey commercial loop pile in tight rows.",
                  "values": {"pile": 1, "tufts": 40, "twist": 0.7, "shading": 0.15, "flecks": 0.1}},
    "berber_oat": {"description": "Oatmeal berber: fat nubby loops with dark flecks.",
                   "values": {"pile": 2, "tufts": 26, "tuft_size": 1.0, "flecks": 0.45, "shading": 0.1}},
    "shag_cream": {"description": "Cream shag rug: long tangled strands over a short pile.",
                   "values": {"pile": 3, "tufts": 36, "shading": 0.3, "twist": 0.4}},
    "red_plush": {"description": "Deep red velvet plush with strong pile shading.",
                  "values": {"tufts": 64, "tuft_size": 0.95, "twist": 0.25, "shading": 0.9}},
}
#: Yarn colour, fleck colour and the backing shadow colour per preset (sRGB).
PALETTES = {
    "default": ("#bfae92", "#8f7f66", "#3b3226"),
    "grey_loop": ("#7b7d80", "#4b4d52", "#1e1f22"),
    "berber_oat": ("#d1c4a8", "#6e5c49", "#4a4033"),
    "shag_cream": ("#e3dac7", "#c9bea6", "#5d5446"),
    "red_plush": ("#8c1b22", "#6a1218", "#2a0507"),
}


def _tuft_grid(count: int, seed: int, jitter: float) -> list:
    """Per tuft (row-major): centre offset from the cell centre, height, ply phase and colour draw."""
    rng = tk.Rng(seed, 0xC7)
    return [(jitter * rng.uniform(-0.5, 0.5), jitter * rng.uniform(-0.5, 0.5), rng.uniform(0.78, 1.0),
             rng.uniform(0.0, math.tau), rng.random()) for _ in range(count * count)]


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The carpet maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    yarn_rgb, fleck_rgb, backing_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    pile, n = p["pile"], p["tufts"]
    size, twist, flecks, shading = p["tuft_size"], p["twist"], p["flecks"], p["shading"]
    loops = pile in (1, 2)
    tufts = _tuft_grid(n, seed, 0.12 if loops else 0.35)
    patches = tk.fbm(width, height, 3, 3, tk.hash_u32(seed, 1))
    nub_cells = min(max(4, min(width, height) // 3), n * 3)
    nubs = tk.fbm(width, height, nub_cells, 2, tk.hash_u32(seed, 2))
    radius = 0.62 * size * (1.15 if pile == 2 else 1.0)
    half_along, half_across = 0.62, 0.42 * size * (1.25 if pile == 2 else 1.0)
    base_scale = 0.45 if pile == 3 else 1.0
    count = width * height
    heights = [0.0] * count
    red, green, blue, rough = [0.0] * count, [0.0] * count, [0.0] * count, [0.0] * count
    tau = math.tau
    for y in range(height):
        gy = (y + 0.5) / height * n
        j0 = int(gy)
        for x in range(width):
            gx = (x + 0.5) / width * n
            i0 = int(gx)
            index = y * width + x
            best, owner, shade_mod = 0.0, None, 0.0
            for dj in (-1, 0, 1):
                j = j0 + dj
                row = (j % n) * n
                for di in (-1, 0, 1):
                    i = i0 + di
                    ox, oy, top, phase, draw = tufts[row + i % n]
                    dx = gx - (i + 0.5 + ox)
                    dy = gy - (j + 0.5 + oy)
                    if loops:
                        a, b = dx / half_along, dy / half_across
                        squared = a * a
                        r2 = squared * squared + b * b
                        if r2 >= 1.0:
                            continue
                        dome = math.sqrt(1.0 - r2)
                        grooves = 0.5 + 0.5 * math.cos(tau * (2.2 * dx + 1.4 * dy) + phase)
                    else:
                        r2 = (dx * dx + dy * dy) / (radius * radius)
                        if r2 >= 1.0:
                            continue
                        dome = math.sqrt(1.0 - r2)
                        angle = math.atan2(dy, dx)
                        grooves = 0.5 + 0.5 * math.cos(3.0 * angle + 7.0 * math.sqrt(r2) + phase)
                    level = top * dome * (1.0 - 0.18 * twist * grooves)
                    if level > best:
                        best, owner, shade_mod = level, (draw, top, dx, dy, phase), grooves
            nub = nubs[index]
            if owner is None:
                level = 0.04 + 0.03 * nub
                colour = backing_rgb
                shade = 0.9
            else:
                draw, top, along, across, phase = owner
                level = (0.12 + 0.8 * best + 0.05 * nub * (1.6 if pile == 2 else 1.0)) * base_scale
                fleck = 0.0
                if draw < flecks:
                    if loops:
                        centre = 0.3 * math.sin(phase)
                        spot = math.hypot(along - centre, 1.4 * (across - 0.12 * math.cos(phase)))
                        fleck = 0.85 * (1.0 - tk.smoothstep(0.16, 0.3, spot))
                    else:
                        fleck = 0.55 + 0.35 * shade_mod
                colour = [c + (f - c) * fleck for c, f in zip(yarn_rgb, fleck_rgb)]
                shade = 0.7 + 0.35 * best - 0.16 * twist * shade_mod + 0.06 * (top - 0.9)
            shade *= 1.0 + 0.18 * shading * patches[index]
            heights[index] = level
            red[index] = colour[0] * shade
            green[index] = colour[1] * shade
            blue[index] = colour[2] * shade
            rough[index] = 0.9 + 0.08 * (1.0 - best) - 0.1 * shading * max(0.0, patches[index])
    if pile == 3:
        _shag(heights, red, green, blue, rough, width, height, seed, p, yarn_rgb, fleck_rgb)
    peak = max(heights)
    heights = [value / peak for value in heights]
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    depth = 0.7 / n if pile != 3 else 0.02
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=depth, roughness=rough,
                     ao_radius=0.7 / n if pile != 3 else 0.012, ao_strength=1.3, directx=directx_normal)


def _shag(heights, red, green, blue, rough, width, height, seed, p, yarn_rgb, fleck_rgb) -> None:
    """Paint long bent strands over the short pile with a z-buffer (shag)."""
    rng = tk.Rng(seed, 0x5A)
    length = p["shag_length"]
    strand_radius = max(0.0085 * p["tuft_size"], 0.55 / min(width, height))
    strands = int(2.6 / (length * strand_radius * 2.0))
    flow = rng.uniform(0.0, math.tau)
    for _ in range(strands):
        u, v = rng.random(), rng.random()
        angle = flow + rng.gauss(0.0, 1.1)
        bend = rng.uniform(-0.6, 0.6)
        reach = length * rng.uniform(0.6, 1.25)
        mid_u, mid_v = u + 0.5 * reach * math.cos(angle), v + 0.5 * reach * math.sin(angle)
        end_u, end_v = mid_u + 0.5 * reach * math.cos(angle + bend), mid_v + 0.5 * reach * math.sin(angle + bend)
        base = rng.uniform(0.75, 1.2)
        tone = rng.uniform(0.82, 1.1)
        colour = fleck_rgb if rng.random() < 0.25 + 0.5 * p["flecks"] else yarn_rgb
        phase = rng.uniform(0.0, math.tau)
        for half, (a_u, a_v, b_u, b_v) in enumerate(((u, v, mid_u, mid_v), (mid_u, mid_v, end_u, end_v))):
            for index, d, t in tk.segment_pixels(width, height, a_u, a_v, b_u, b_v, strand_radius):
                along = 0.5 * (half + t)
                surface = base * (1.0 - 0.3 * along) * (1.0 - 0.4 * d * d) + 0.35
                if surface > heights[index]:
                    heights[index] = surface
                    ply = 0.5 + 0.5 * math.cos(math.tau * 9.0 * along + 3.0 * d + phase)
                    shade = tone * (0.72 + 0.3 * (1.0 - d) - 0.12 * p["twist"] * ply)
                    red[index], green[index], blue[index] = (c * shade for c in colour)
                    rough[index] = 0.86 + 0.08 * d


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
