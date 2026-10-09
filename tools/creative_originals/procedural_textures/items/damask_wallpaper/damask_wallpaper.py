"""Damask wallpaper: a mirror-symmetric ornament in a half-drop repeat, satin against matte (standard library).

The ornament is grown from a seed on the right half of a cell and mirrored across the vertical axis: a central stem,
a palmette fan of petals at the top, pairs of scrolls that leave the stem and curl tighter and tighter (the curvature
grows along each scroll, so it ends in a spiral), leaves set alternately along every scroll, berries at the scroll
tips and a bud at the base. Strokes are capsules and leaves and petals are ellipses, painted with wrap-around into a
motif mask for every cell of a half-drop lattice (odd columns shifted down half a cell), with a small rosette in
the gaps between neighbours.

As in woven damask, motif and ground can be the same colour and differ only in weave direction: fine stripes run
one way in the motif and across it in the ground, so the motif reads as satin sheen against a matte ground. Other
presets print it in gold on burgundy, flock it in raised velvet on silver, or print it flat in two colours.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "damask_wallpaper"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.03, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.15, 1.0]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "column_pairs", "type": "int", "default": 1, "minimum": 1, "maximum": 4,
     "meaning": "Pairs of motif columns across the tile (the half-drop repeats every two columns)."},
    {"name": "scrolls", "type": "int", "default": 3, "minimum": 1, "maximum": 4,
     "meaning": "Pairs of scrolls leaving the stem."},
    {"name": "petals", "type": "int", "default": 7, "minimum": 3, "maximum": 11,
     "meaning": "Petals in the palmette fan at the top of the motif."},
    {"name": "leafiness", "type": "float", "default": 0.7, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Leaves set along the scrolls."},
    {"name": "stroke", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 2.0,
     "meaning": "Width of the stems and scrolls."},
    {"name": "relief", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Embossed or flocked height of the motif."},
    {"name": "weave", "type": "float", "default": 0.7, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Strength of the crossed weave stripes that set satin motif against matte ground."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Ivory satin damask: tone on tone, the motif shining against a matte ground.",
                "values": {}},
    "burgundy_gold": {"description": "Metallic gold motif printed on matte deep burgundy.",
                      "values": {"weave": 0.15, "relief": 0.2, "scrolls": 2, "petals": 9}},
    "flocked_velvet": {"description": "Raised black velvet flock on a silver sheen ground.",
                       "values": {"relief": 0.9, "weave": 0.3, "stroke": 1.4, "leafiness": 0.9}},
    "teal_print": {"description": "Flat teal print on cream paper, smaller motifs, no weave.",
                   "values": {"column_pairs": 2, "weave": 0.0, "relief": 0.05, "scrolls": 2, "petals": 5}},
}
#: Per preset: ground colour, motif colour (sRGB), ground and motif roughness, motif metallic.
PALETTES = {
    "default": ("#d6c4a0", "#f4ecd8", 0.72, 0.32, 0.0),
    "burgundy_gold": ("#5a1420", "#d0a448", 0.85, 0.3, 1.0),
    "flocked_velvet": ("#b8bcc0", "#1a1618", 0.35, 0.98, 0.0),
    "teal_print": ("#efe7d2", "#2c6e6c", 0.8, 0.7, 0.0),
}


def motif(seed: int, scrolls: int, petals: int, leafiness: float, stroke: float) -> tuple:
    """(segments, ellipses) of one motif in cell units, x from -0.5 to 0.5 and y from -0.5 (top) to 0.5, already
    mirrored: segments are (x0, y0, x1, y1, radius), ellipses (x, y, radius_x, radius_y, angle)."""
    rng = tk.Rng(seed, 0xDA)
    segments, ellipses = [], []
    width = 0.016 * stroke
    segments.append((0.0, 0.44, 0.0, -0.3, width))
    ellipses.append((0.0, 0.03, 0.075, 0.12, math.pi / 2))
    ellipses.append((0.0, 0.4, 0.045, 0.065, math.pi / 2))
    spread = math.radians(rng.uniform(50.0, 70.0))
    for k in range(petals):
        t = k / (petals - 1) - 0.5
        angle = -math.pi / 2 + 2.0 * spread * t
        length = 0.19 * (1.0 - 0.4 * abs(2.0 * t)) * rng.uniform(0.92, 1.05)
        cx, cy = 0.55 * length * math.cos(angle), -0.17 + 0.55 * length * math.sin(angle)
        ellipses.append((cx, cy, 0.55 * length, 0.17 * length, angle))
    ellipses.append((0.0, -0.17, 0.04, 0.04, 0.0))
    right_segments, right_ellipses = [], []
    for k in range(scrolls):
        start_y = 0.32 - 0.5 * (k + 0.5) / scrolls + rng.uniform(-0.02, 0.02)
        angle = math.radians(rng.uniform(-25.0, 25.0))
        curl = -rng.uniform(0.07, 0.11)
        steps = 26
        step = rng.uniform(0.02, 0.025) * (1.0 - 0.12 * k)
        x, y = 0.0, start_y
        for s in range(steps):
            t = s / steps
            angle += curl * (1.0 + 2.5 * t * t)
            nx, ny = x + step * math.cos(angle), y + step * math.sin(angle)
            right_segments.append((x, y, nx, ny, width * (1.0 - 0.55 * t)))
            if 1 < s < steps - 4 and s % 4 == 2 and rng.chance(leafiness):
                leaf = angle + math.radians(rng.uniform(40.0, 70.0))
                length = rng.uniform(0.08, 0.12) * (1.0 - 0.35 * t)
                right_ellipses.append((nx + 0.55 * length * math.cos(leaf), ny + 0.55 * length * math.sin(leaf),
                                       length * 0.55, length * 0.22, leaf))
            x, y = nx, ny
        right_ellipses.append((x, y, 0.016 * stroke, 0.016 * stroke, 0.0))
    segments += right_segments + [(-x0, y0, -x1, y1, r) for x0, y0, x1, y1, r in right_segments]
    ellipses += right_ellipses + [(-x, y, rx, ry, math.pi - a) for x, y, rx, ry, a in right_ellipses]
    rosette = [(-0.5 + 0.035 * math.cos(a), 0.035 * math.sin(a), 0.035, 0.014, a)
               for a in (0.0, math.pi / 2, math.pi, 3 * math.pi / 2)]
    ellipses += rosette
    return segments, ellipses


def _leaf(s: float, t: float):
    d2 = s * s + t * t
    return None if d2 >= 1.0 else math.sqrt(1.0 - d2)


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The damask maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    ground_hex, motif_hex, ground_rough, motif_rough, motif_metal = PALETTES[preset]
    columns = 2 * p["column_pairs"]
    rows = columns
    segments, ellipses = motif(seed, p["scrolls"], p["petals"], p["leafiness"], p["stroke"])
    mask = [0.0] * (width * height)
    pixel = 0.7 / min(width, height)
    for column in range(columns):
        for row in range(rows):
            ox = (column + 0.5) / columns
            oy = (row + 0.5 + 0.5 * (column % 2)) / rows
            for x0, y0, x1, y1, radius in segments:
                tk.draw_segment(mask, width, height, ox + x0 / columns, oy + y0 / rows, ox + x1 / columns,
                                oy + y1 / rows, max(radius / columns, pixel), 1.0,
                                profile=lambda d: 1.0 - d ** 4)
            for x, y, rx, ry, angle in ellipses:
                tk.stamp(mask, width, height, ox + x / columns, oy + y / rows, max(rx / columns, pixel),
                         max(ry / rows, pixel), _leaf, angle=angle)
    soft = tk.blur(mask, width, height, 0.0025, passes=2)
    paper = tk.fbm(width, height, 48, 3, tk.hash_u32(seed, 1))
    grain = tk.white_noise(width, height, tk.hash_u32(seed, 2))
    ground, ink = tk.hex_rgb(ground_hex), tk.hex_rgb(motif_hex)
    threads = 64 * p["column_pairs"]
    weave, relief = p["weave"], p["relief"]
    red, green, blue, heights, rough, metallic = [], [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        across = 0.5 + 0.5 * math.sin(math.tau * threads * v)
        for x in range(width):
            index = y * width + x
            u = (x + 0.5) / width
            along = 0.5 + 0.5 * math.sin(math.tau * threads * u)
            m = tk.smoothstep(0.25, 0.6, mask[index])
            stripe = along * m + across * (1.0 - m)
            shine = 1.0 + weave * (0.06 * m - 0.03) * (2.0 * stripe - 1.0)
            tone = (0.97 + 0.04 * paper[index] + 0.02 * grain[index]) * shine
            colour = [(g + (c - g) * m) * tone for g, c in zip(ground, ink)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            heights.append(0.4 + relief * 0.45 * soft[index] + 0.05 * weave * stripe + 0.03 * paper[index])
            rough.append(ground_rough + (motif_rough - ground_rough) * m + 0.08 * weave * (stripe - 0.5)
                         + 0.03 * grain[index])
            metallic.append(motif_metal * m)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.01, roughness=rough,
                     metallic=metallic, ao_radius=0.01, ao_strength=0.7, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
