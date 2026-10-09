"""Encaustic cement tiles: inlaid colour motifs with eightfold (D4) symmetry, tileable PBR maps (standard library).

Each square tile folds its point into one octant of the square (0 <= b <= a <= 1/2 by mirroring |x|, |y| and the
diagonal), so anything drawn once in the octant repeats with the symmetry of the square. A motif is a short list of
layers drawn in order: an eight-point star, discs and rings, petals, nested squares and diamonds, corner quarter
circles and edge half circles. Because every tile is mirror symmetric, the quarter and half circles at its edges
join into whole circles with the neighbouring tiles. Shapes are sized by ``motif_variant``; inlay boundaries are
softened over about a pixel and a half, and the cement face carries pores, faded wear and per-tile tone.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "encaustic_cement_tiles"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.92]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.4, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "tiles_across", "type": "int", "default": 2, "minimum": 1, "maximum": 8,
     "meaning": "Tiles across the tile width (and height)."},
    {"name": "family", "type": "int", "default": 0, "minimum": 0, "maximum": 3,
     "meaning": "Motif family: 0 eight-point star with corner circles, 1 floral with axis and diagonal petals, "
                "2 geometric nested squares and diamonds, 3 rosette inside a border frame."},
    {"name": "motif_variant", "type": "int", "default": 0, "minimum": 0, "maximum": 99,
     "meaning": "Which design of the family: sizes and proportions of its shapes."},
    {"name": "joint_width", "type": "float", "default": 0.006, "minimum": 0.0, "maximum": 0.03,
     "meaning": "Joint between tiles in tile widths."},
    {"name": "edge_softness", "type": "float", "default": 1.5, "minimum": 0.5, "maximum": 4.0,
     "meaning": "Width in pixels over which inlay colours blend at their boundaries."},
    {"name": "wear", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Faded, scuffed patches and slightly chipped tile edges."},
    {"name": "pores", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Small pores and air holes in the cement face."},
    {"name": "colour_variation", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spread of tone between tiles."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Eight-point stars in black and terracotta on cream with ochre corner circles.",
                "values": {}},
    "blue_floral": {"description": "White tiles with cobalt and sky blue petals around a small centre.",
                    "values": {"family": 1, "motif_variant": 7, "wear": 0.2}},
    "geometric_mono": {"description": "Black, white and grey nested squares and diamonds, four tiles per side.",
                       "values": {"family": 2, "tiles_across": 4, "motif_variant": 3, "wear": 0.15,
                                  "pores": 0.3}},
    "rosette_border": {"description": "Faded green, rose and sand rosettes framed by a border band, well worn.",
                       "values": {"family": 3, "motif_variant": 11, "wear": 0.65, "pores": 0.6,
                                  "colour_variation": 0.5}},
}
#: Background and three inlay colours, joint colour per preset (sRGB).
PALETTES = {
    "default": (["#e8dcc3", "#1f1d1c", "#b4553a", "#d39b3a"], "#cbbfa8"),
    "blue_floral": (["#eeebe3", "#1f4f9a", "#78a6d6", "#c9b37a"], "#d3cdc0"),
    "geometric_mono": (["#ece9e2", "#1c1c1e", "#8d8b87", "#c8c4bc"], "#bdb8ae"),
    "rosette_border": (["#e0d2b4", "#5f7f5a", "#b7695f", "#c7a46c"], "#c9bca2"),
}
SQRT2 = math.sqrt(2.0)
#: The shapes a motif layer can be.
LAYER_KINDS = (DISC, RING, STAR, PETAL, SQUARE, DIAMOND, FRAME) = (
    "disc", "ring", "star", "petal", "square", "diamond", "frame")


def fold(x: float, y: float) -> tuple:
    """The point (a, b) with 0 <= b <= a that (x, y) maps to under the eight symmetries of the square."""
    a, b = abs(x), abs(y)
    return (a, b) if a >= b else (b, a)


def _design(family: int, variant: int) -> list:
    """Layers (kind, numbers, colour) of one motif in the folded octant; drawn in order, later layers on top."""
    rng = tk.Rng(variant, 0xE7, family)
    if family == 0:
        outer = rng.uniform(0.3, 0.4)
        return [(STAR, (rng.uniform(0.12, 0.18), outer, rng.uniform(1.5, 3.0)), 1),
                (DISC, (0.0, 0.0, rng.uniform(0.07, 0.11)), 2),
                (RING, (0.0, 0.0, outer + rng.uniform(0.03, 0.05), 0.012), 1),
                (DISC, (0.5, 0.5, rng.uniform(0.12, 0.18)), 3),
                (DISC, (0.5, 0.5, rng.uniform(0.05, 0.08)), 1),
                (DISC, (0.5, 0.0, rng.uniform(0.04, 0.07)), 2)]
    if family == 1:
        reach = rng.uniform(0.18, 0.26)
        return [(PETAL, (0.0, reach, rng.uniform(0.11, 0.16), rng.uniform(0.05, 0.075)), 1),
                (PETAL, (1.0, reach * 0.95, rng.uniform(0.09, 0.13), rng.uniform(0.04, 0.06)), 2),
                (DISC, (0.0, 0.0, rng.uniform(0.06, 0.09)), 3),
                (DISC, (0.0, 0.0, rng.uniform(0.025, 0.04)), 1),
                (PETAL, (1.0, 0.62, rng.uniform(0.07, 0.1), rng.uniform(0.03, 0.045)), 2),
                (DISC, (0.5, 0.0, rng.uniform(0.05, 0.08)), 3)]
    if family == 2:
        steps = [rng.uniform(0.08, 0.14)]
        while steps[-1] < 0.42:
            steps.append(steps[-1] + rng.uniform(0.06, 0.12))
        layers = []
        for k, size in enumerate(reversed(steps)):
            if k % 2 == 0:
                layers.append((SQUARE, (size,), 1 + (k % 3)))
            else:
                layers.append((DIAMOND, (size * 1.25,), 1 + (k % 3)))
        layers.append((SQUARE, (0.5, 0.5, rng.uniform(0.08, 0.13)), 1))
        return layers
    band = rng.uniform(0.035, 0.06)
    return [(FRAME, (0.5 - band, 0.5 - 2.4 * band), 1),
            (DISC, (0.0, 0.0, rng.uniform(0.26, 0.32)), 3),
            (STAR, (rng.uniform(0.12, 0.16), rng.uniform(0.22, 0.27), rng.uniform(1.0, 2.0)), 2),
            (DISC, (0.0, 0.0, rng.uniform(0.06, 0.09)), 1),
            (SQUARE, (0.5, 0.5, rng.uniform(0.07, 0.1)), 2)]


def layer_distance(kind: str, numbers: tuple, a: float, b: float) -> float:
    """Signed distance (negative inside) from the folded point (a, b) to one motif layer, in tile widths."""
    if kind == DISC:
        cx, cy, radius = numbers
        return math.hypot(a - cx, b - cy) - radius
    if kind == RING:
        cx, cy, radius, half_width = numbers
        return abs(math.hypot(a - cx, b - cy) - radius) - half_width
    if kind == STAR:
        inner, outer, sharpness = numbers
        r = math.hypot(a, b)
        theta = math.atan2(b, a)
        return r - (inner + (outer - inner) * abs(math.cos(4.0 * theta)) ** sharpness)
    if kind == PETAL:
        diagonal, reach, length, half_width = numbers
        if diagonal > 0.5:
            along, across = (a + b) / SQRT2, (a - b) / SQRT2
        else:
            along, across = a, b
        return math.hypot((along - reach) * half_width / length, across) - half_width
    if kind == SQUARE:
        if len(numbers) == 1:
            return max(a, b) - numbers[0]
        cx, cy, half = numbers
        return max(abs(a - cx), abs(b - cy)) - half
    if kind == DIAMOND:
        return (a + b - numbers[0]) / SQRT2
    if kind == FRAME:
        outer, inner = numbers
        return max(inner - a, a - outer)
    raise ValueError(f"unknown layer kind {kind!r}")


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The encaustic tile maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    colours_hex, joint_hex = PALETTES[preset]
    colours = [tk.hex_rgb(code) for code in colours_hex]
    joint_rgb = tk.hex_rgb(joint_hex)
    layers = _design(p["family"], p["motif_variant"])
    n = p["tiles_across"]
    half_joint = 0.5 * p["joint_width"]
    soft = p["edge_softness"] * n / width
    wear, pores, variation = p["wear"], p["pores"], p["colour_variation"]
    faded = tk.fbm(width, height, 3, 4, tk.hash_u32(seed, 2))
    scratches = tk.fbm(width, height, 40, 2, tk.hash_u32(seed, 3), cells_y=6)
    chips = tk.fbm(width, height, 10 * n, 3, tk.hash_u32(seed, 4))
    holes = tk.white_noise(width, height, tk.hash_u32(seed, 5))
    surface = tk.fbm(width, height, 6 * n, 3, tk.hash_u32(seed, 6))
    pixel = n / width
    floor = math.floor
    red, green, blue, heights, rough = [], [], [], [], []
    for y in range(height):
        sy = (y + 0.5) / height * n
        j = floor(sy)
        ly = sy - j - 0.5
        for x in range(width):
            index = y * width + x
            sx = (x + 0.5) / width * n
            i = floor(sx)
            lx = sx - i - 0.5
            a, b = fold(lx, ly)
            colour = list(colours[0])
            for kind, numbers, colour_index in layers:
                distance = layer_distance(kind, numbers, a, b)
                coverage = 1.0 - tk.smoothstep(-soft, soft, distance)
                if coverage > 0.0:
                    target = colours[colour_index]
                    colour = [c + (t - c) * coverage for c, t in zip(colour, target)]
            code = tk.hash_u32(seed, i % n, j % n)
            tone = 1.0 + 0.1 * (tk.hash_float(code, 1) - 0.5) * 2.0 * variation + 0.03 * surface[index]
            fade = wear * tk.smoothstep(0.0, 0.5, faded[index]) * 0.35 + wear * 0.15 * max(0.0, scratches[index])
            colour = [(c + (0.86 - c) * fade) * tone for c in colour]
            pit = pores * (1.0 if holes[index] < 0.008 + 0.018 * pores else 0.0)
            if pit > 0.0:
                colour = [c * (1.0 - 0.3 * pit) for c in colour]
            edge = 0.5 - max(abs(lx), abs(ly)) - half_joint - wear * 0.012 * max(0.0, chips[index] + 0.2)
            t = edge / 0.006
            profile = 0.0 if t <= 0.0 else 1.0 if t >= 1.0 else math.sqrt(1.0 - (1.0 - t) * (1.0 - t))
            top = 0.8 + 0.015 * surface[index] + 0.035 * (tk.hash_float(code, 2) - 0.5) - 0.04 * pit
            level = 0.55 + (top - 0.55) * profile
            heights.append(level)
            cover = tk.smoothstep(-pixel, pixel, edge)
            joint = [c * (0.88 + 0.2 * holes[index]) for c in joint_rgb]
            colour = [g + (c - g) * cover for g, c in zip(joint, colour)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            face_rough = 0.72 + 0.12 * fade + 0.05 * surface[index] + 0.1 * pit
            rough.append(0.92 + (face_rough - 0.92) * cover)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.01, roughness=rough,
                     ao_radius=0.012, ao_strength=0.9, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
