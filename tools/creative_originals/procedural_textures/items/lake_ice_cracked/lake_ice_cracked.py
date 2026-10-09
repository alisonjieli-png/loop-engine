"""Cracked lake ice: clear dark ice with white fracture planes, trapped bubbles and skate scratches (standard library).

Long fractures are jagged polylines that wander across the tile and wrap around its edges; each is drawn as a bright
core line plus a wider, fainter sheet offset to one side, which reads as a crack plane seen slanting down into
clear ice. A polygonal network of thinner cracks comes from the borders of a Worley diagram, broken up by noise.
Bubbles are small rings jittered inside the cells of a grid; methane "pancakes" are stacks of soft white discs with
small offsets. Bubbles smaller than about half a pixel at the output size are left out. Skate scratches are long
shallow arcs cut into the surface. Ice colour runs from near-black clear ice
to milky white ice by a fractal noise field.

The cracks and bubbles are inside the ice, so they change only the colour; scratches and a faint undulation are the
surface, so they also shape the height, normals and roughness.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "lake_ice_cracked"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.03, 0.8]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "fractures", "type": "int", "default": 6, "minimum": 0, "maximum": 20,
     "meaning": "Long fracture lines wandering across the tile."},
    {"name": "network", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Polygonal network of thin cracks between ice plates."},
    {"name": "plates", "type": "int", "default": 5, "minimum": 2, "maximum": 16,
     "meaning": "Plates across the tile for the crack network."},
    {"name": "bubbles", "type": "float", "default": 0.45, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Scattered small air bubbles."},
    {"name": "pancakes", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Stacks of flat white methane bubbles."},
    {"name": "scratches", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Skate scratches cut into the surface."},
    {"name": "milkiness", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of white, cloudy snow ice against clear black ice."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Black ice: clear dark ice with white fracture planes and scattered bubbles.",
                "values": {}},
    "methane_bubbles": {"description": "Clear ice full of stacked white methane bubbles, few cracks.",
                        "values": {"fractures": 2, "network": 0.0, "bubbles": 0.6, "pancakes": 0.95,
                                   "scratches": 0.05}},
    "skating_rink": {"description": "Milky outdoor rink ice criss-crossed by skate scratches.",
                     "values": {"fractures": 2, "network": 0.1, "bubbles": 0.15, "pancakes": 0.0,
                                "scratches": 0.95, "milkiness": 0.7}},
    "pressure_cracked": {"description": "Blue ice broken into plates by a dense crack network and fractures.",
                         "values": {"fractures": 12, "network": 0.9, "plates": 7, "bubbles": 0.25,
                                    "pancakes": 0.0, "scratches": 0.0, "milkiness": 0.3}},
}
#: Bubbles sit one at most per cell of a BUBBLE_CELLS x BUBBLE_CELLS grid, jittered inside the cell.
BUBBLE_CELLS = 28
#: Per preset: clear ice, milky ice, crack white and bubble white (sRGB).
PALETTES = {
    "default": ("#071820", "#6f8c9a", "#e6f2f6", "#dce8ee"),
    "methane_bubbles": ("#0a1e26", "#62808e", "#e0eef2", "#f2f8fa"),
    "skating_rink": ("#1c3440", "#a6bcc6", "#eaf2f4", "#dce6ea"),
    "pressure_cracked": ("#0a2c40", "#5a90b0", "#e8f6fc", "#d8eaf2"),
}


def _polyline(rng, u: float, v: float, angle: float, length: float, jag: float) -> list:
    steps = max(4, int(length / 0.025))
    step = length / steps
    points = [(u, v)]
    for _ in range(steps):
        angle += rng.gauss(0.0, jag)
        u, v = u + step * math.cos(angle), v + step * math.sin(angle)
        points.append((u, v))
    return points


def _ring(s: float, t: float):
    d = math.sqrt(s * s + t * t)
    if d >= 1.0:
        return None
    return 0.55 + 0.45 * tk.smoothstep(0.45, 0.9, d) - 0.35 * tk.smoothstep(0.9, 1.0, d)


def _disc(s: float, t: float):
    d2 = s * s + t * t
    if d2 >= 1.0:
        return None
    return 0.42 * (1.0 - d2 * d2)


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The ice maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    clear_hex, milky_hex, crack_hex, bubble_hex = PALETTES[preset]
    count = width * height
    pixel = 1.0 / min(width, height)
    rng = tk.Rng(seed, 0x1CE)
    cracks = [0.0] * count
    sheets = [0.0] * count
    for _ in range(p["fractures"]):
        angle = math.tau * rng.random()
        line = _polyline(rng, rng.random(), rng.random(), angle, rng.uniform(0.45, 1.1), 0.14)
        side = 1.0 if rng.chance(0.5) else -1.0
        offset = rng.uniform(0.004, 0.01)
        sheet = [(u - side * offset * math.sin(angle), v + side * offset * math.cos(angle)) for u, v in line]
        tk.draw_path(sheets, width, height, sheet, max(0.009, 1.5 * pixel), 0.45)
        tk.draw_path(cracks, width, height, line, max(0.0013, 0.6 * pixel), 1.0)
        for _branch in range(rng.integer(1, 4)):
            u, v = line[rng.integer(1, len(line) - 2)]
            twig = _polyline(rng, u, v, angle + rng.choice((-1.0, 1.0)) * rng.uniform(0.5, 1.2),
                             rng.uniform(0.05, 0.18), 0.2)
            tk.draw_path(cracks, width, height, twig, max(0.001, 0.55 * pixel), 0.8)
    if p["network"] > 0.0:
        cells = tk.voronoi(width, height, p["plates"], p["plates"], tk.hash_u32(seed, 1), jitter=0.85)
        breaks = tk.fbm(width, height, 2 * p["plates"], 3, tk.hash_u32(seed, 2))
        reach = 0.012 + 0.6 * pixel * p["plates"]
        for index in range(count):
            line = 1.0 - tk.smoothstep(0.0, reach, cells["edge"][index])
            keep = tk.smoothstep(0.55 - 0.6 * p["network"], 0.8 - 0.6 * p["network"], 0.5 + 0.5 * breaks[index])
            cracks[index] = max(cracks[index], 0.85 * line * keep)
            sheets[index] = max(sheets[index], 0.25 * keep * (1.0 - tk.smoothstep(0.0, 4.0 * reach,
                                                                                  cells["edge"][index])))
    bubbles = [0.0] * count
    if p["bubbles"] > 0.0:
        for cell in range(BUBBLE_CELLS * BUBBLE_CELLS):
            if rng.chance(p["bubbles"]):
                u = (cell % BUBBLE_CELLS + 0.15 + 0.7 * rng.random()) / BUBBLE_CELLS
                v = (cell // BUBBLE_CELLS + 0.15 + 0.7 * rng.random()) / BUBBLE_CELLS
                radius = 0.0025 + 0.007 * rng.random() ** 2.5
                if radius * min(width, height) >= 0.4:
                    tk.stamp(bubbles, width, height, u, v, radius, radius, _ring, mode=tk.MODE_MAX)
    if p["pancakes"] > 0.0:
        for u, v in tk.poisson_points(0.11, tk.hash_u32(seed, 4)):
            if rng.chance(p["pancakes"]):
                for layer in range(rng.integer(3, 7)):
                    radius = rng.uniform(0.008, 0.026) * (1.0 - 0.08 * layer)
                    tk.stamp(bubbles, width, height, u + rng.gauss(0.0, 0.006), v + rng.gauss(0.0, 0.006),
                             radius, radius * rng.uniform(0.8, 1.0), _disc, mode=tk.MODE_ADD,
                             angle=math.tau * rng.random())
    scratch = [0.0] * count
    for _ in range(int(round(p["scratches"] * 40))):
        cu, cv, bend = rng.random(), rng.random(), rng.uniform(0.25, 0.9)
        start, sweep = math.tau * rng.random(), rng.uniform(0.2, 0.7) * rng.choice((-1.0, 1.0))
        arc = [(cu + bend * math.cos(start + sweep * k / 12.0), cv + bend * math.sin(start + sweep * k / 12.0))
               for k in range(13)]
        tk.draw_path(scratch, width, height, arc, max(0.0009, 0.5 * pixel), rng.uniform(0.4, 1.0))
    milk = tk.fbm(width, height, 3, 5, tk.hash_u32(seed, 5))
    swell = tk.fbm(width, height, 4, 3, tk.hash_u32(seed, 6))
    grain = tk.fbm(width, height, 32, 2, tk.hash_u32(seed, 7))
    clear, milky = tk.hex_rgb(clear_hex), tk.hex_rgb(milky_hex)
    crack_white, bubble_white = tk.hex_rgb(crack_hex), tk.hex_rgb(bubble_hex)
    threshold = 1.0 - 1.4 * p["milkiness"]
    red, green, blue, heights, rough = [], [], [], [], []
    for index in range(count):
        cloud = tk.smoothstep(threshold - 0.35, threshold + 0.35, 0.5 + 0.5 * milk[index] + 0.1 * grain[index])
        colour = [c + (m - c) * cloud for c, m in zip(clear, milky)]
        crack = max(cracks[index], 0.75 * sheets[index])
        colour = [c + (w - c) * 0.92 * crack for c, w in zip(colour, crack_white)]
        bubble = min(1.0, bubbles[index])
        colour = [c + (w - c) * 0.9 * bubble for c, w in zip(colour, bubble_white)]
        cut = scratch[index]
        colour = [c + (w - c) * 0.35 * cut for c, w in zip(colour, crack_white)]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        heights.append(0.6 + 0.05 * swell[index] + 0.01 * grain[index] - 0.18 * cut - 0.06 * cracks[index])
        rough.append(0.05 + 0.03 * (0.5 + 0.5 * grain[index]) + 0.35 * cut + 0.25 * cloud * p["milkiness"])
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.01, roughness=rough,
                     ao_radius=0.01, ao_strength=0.8, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
