"""Cast concrete: cement mottling, bug holes and formwork imprints, tileable PBR maps (standard library only).

The cement face is a soft mottled grey with fine sand grain. Bug holes (air voids left against the formwork) are
small round pits. The formwork leaves its mark: none (smooth cast), board-formed (horizontal boards with wood grain
pressed into the surface and a small lip at every board joint) or plywood panels (panel seams and a regular grid of
tie holes). Water stains run down from the top of each board or panel: every column is swept downward with a
fading trail, twice around so the trail wraps.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "concrete_cast"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.04, 0.85]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.15, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "formwork", "type": "int", "default": 0, "minimum": 0, "maximum": 2,
     "meaning": "Formwork imprint: 0 smooth, 1 horizontal boards, 2 plywood panels with tie holes."},
    {"name": "panels", "type": "int", "default": 2, "minimum": 1, "maximum": 12,
     "meaning": "Boards (formwork 1) or panel rows and columns (formwork 2) across the tile."},
    {"name": "bug_holes", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Density of small air-void pits."},
    {"name": "mottling", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Strength of the cloudy tone variation."},
    {"name": "stains", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Water stains running down from joints."},
    {"name": "aggregate", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Exposed aggregate: pebbles showing through the cement."},
    {"name": "polish", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Ground and polished finish (0 as cast, 1 polished floor)."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Smooth cast concrete with soft mottling and scattered bug holes.", "values": {}},
    "board_formed": {"description": "Board-formed concrete showing wood grain and board joints.",
                     "values": {"formwork": 1, "panels": 6, "stains": 0.4, "bug_holes": 0.25}},
    "tie_hole_panels": {"description": "Architectural panels with seams and tie holes.",
                        "values": {"formwork": 2, "panels": 2, "mottling": 0.35, "stains": 0.2}},
    "weathered": {"description": "Old dark concrete with heavy stains and exposed grit.",
                  "values": {"stains": 0.9, "mottling": 0.9, "bug_holes": 0.6, "aggregate": 0.3}},
    "polished_floor": {"description": "Ground and polished floor with exposed aggregate.",
                       "values": {"polish": 0.9, "aggregate": 0.8, "bug_holes": 0.1, "stains": 0.0}},
}
#: Light and dark cement, stain colour and aggregate colours per preset (sRGB).
PALETTES = {
    "default": ("#a7a49e", "#8a8781", "#6a665f", ["#7c7a76", "#b3afa8", "#5e5c59"]),
    "board_formed": ("#a29d94", "#867f75", "#5e574e", ["#7c7a76", "#b3afa8", "#5e5c59"]),
    "tie_hole_panels": ("#b8b5b0", "#a09d98", "#77736c", ["#7c7a76", "#b3afa8", "#5e5c59"]),
    "weathered": ("#8a877f", "#6a675f", "#3f3c36", ["#6f6c66", "#9b968d", "#4a4844"]),
    "polished_floor": ("#9c9890", "#8a867e", "#6a665f", ["#3d3b39", "#c9c2b5", "#7a6a58", "#e3ded4", "#5a5d61"]),
}


def _trail(mask: list, width: int, height: int, length: float) -> list:
    keep = math.exp(-1.0 / max(length * height, 1e-6))
    out = [0.0] * (width * height)
    for x in range(width):
        column = mask[x::width]
        trail, values = 0.0, [0.0] * height
        for _round in range(2):
            for y in range(height):
                trail = max(column[y], trail * keep)
                values[y] = trail
        out[x::width] = values
    return out


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The concrete maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    light_hex, dark_hex, stain_hex, stone_hex = PALETTES[preset]
    light, dark, stain_rgb = tk.hex_rgb(light_hex), tk.hex_rgb(dark_hex), tk.hex_rgb(stain_hex)
    stones_rgb = [tk.hex_rgb(code) for code in stone_hex]
    count = width * height
    cloud = tk.normalize(tk.fbm(width, height, 3, 6, tk.hash_u32(seed, 1)))
    sand = tk.white_noise(width, height, tk.hash_u32(seed, 2))
    fine = tk.fbm(width, height, 48, 2, tk.hash_u32(seed, 3))
    rng = tk.Rng(seed, 4)
    pits = [0.0] * count
    for _ in range(int(220 * p["bug_holes"])):
        radius = rng.uniform(0.002, 0.008)
        tk.stamp(pits, width, height, rng.random(), rng.random(), radius, radius * rng.uniform(0.7, 1.0),
                 lambda s, t: 1.0 - (s * s + t * t) if s * s + t * t < 1.0 else None)
    formwork, panels = p["formwork"], p["panels"]
    joints = [0.0] * count
    imprint = [0.0] * count
    if formwork == 1:
        grain = tk.fbm(width, height, 3, 4, tk.hash_u32(seed, 5), cells_y=panels * 10)
        offsets = [rng.uniform(-0.03, 0.03) for _ in range(panels)]
        for y in range(height):
            v = (y + 0.5) / height * panels
            board = min(int(v), panels - 1)
            local = v - board
            edge = min(local, 1.0 - local) / panels
            line = 1.0 - tk.smoothstep(0.0, 0.004, edge)
            for x in range(width):
                index = y * width + x
                joints[index] = line
                rings = math.sin(math.tau * (local * 7.0 + 3.0 * grain[index]))
                imprint[index] = 0.6 * rings + 0.6 * grain[index] + offsets[board] * 10.0
    elif formwork == 2:
        for y in range(height):
            v = (y + 0.5) / height * panels
            local_v = v - math.floor(v)
            for x in range(width):
                u = (x + 0.5) / width * panels
                local_u = u - math.floor(u)
                edge = min(local_u, 1.0 - local_u, local_v, 1.0 - local_v) / panels
                seam = 1.0 - tk.smoothstep(0.0, 0.003, edge)
                hole = 0.0
                for cu in (0.25, 0.75):
                    for cv in (0.2, 0.8):
                        distance = math.hypot((local_u - cu) / panels, (local_v - cv) / panels)
                        if distance < 0.024:
                            hole = max(hole, 1.0 if distance < 0.016 else 0.35 * (1.0 - (distance - 0.016) / 0.008))
                index = y * width + x
                joints[index] = seam
                imprint[index] = -hole
    stain_source = [max(j, 0.3 * max(0.0, -i)) for j, i in zip(joints, imprint)] if formwork else \
        [tk.smoothstep(0.25, 0.4, c) * 0.4 for c in cloud]
    streaks = tk.fbm(width, height, 32, 3, tk.hash_u32(seed, 6), cells_y=2)
    stains = _trail(stain_source, width, height, 0.15) if p["stains"] > 0.0 else [0.0] * count
    aggregate = [-1] * count
    if p["aggregate"] > 0.0:
        cells = tk.voronoi(width, height, 36, 36, tk.hash_u32(seed, 7), jitter=0.9)
        for index in range(count):
            cell = cells["cell"][index]
            if tk.hash_float(cell, seed, 8) < p["aggregate"] * 0.7 and cells["edge"][index] > 0.08:
                aggregate[index] = cell
    mottling, polish = p["mottling"], p["polish"]
    red, green, blue, heights, rough = [], [], [], [], []
    for index in range(count):
        tone = 0.5 + (cloud[index] - 0.5) * mottling
        colour = [d + (l - d) * tone for l, d in zip(light, dark)]
        colour = [c * (0.94 + 0.12 * sand[index] + 0.04 * fine[index]) for c in colour]
        stain = p["stains"] * stains[index] * (0.5 + 0.5 * streaks[index] + 0.25)
        colour = [c + (s - c) * min(0.8, stain) for c, s in zip(colour, stain_rgb)]
        colour = [c * (1.0 - 0.45 * pits[index] - 0.3 * joints[index]) for c in colour]
        if formwork == 1:
            colour = [c * (1.0 + 0.07 * imprint[index]) for c in colour]
        elif formwork == 2:
            colour = [c * (1.0 + 0.45 * imprint[index]) for c in colour]
        level = 0.6 + 0.02 * fine[index] + 0.01 * sand[index] - 0.35 * pits[index]
        if formwork == 1:
            level += 0.03 * imprint[index] - 0.08 * joints[index]
        elif formwork == 2:
            level += 0.4 * imprint[index] - 0.05 * joints[index]
        stone = aggregate[index]
        if stone >= 0:
            pick = stones_rgb[tk.hash_u32(stone, seed, 9) % len(stones_rgb)]
            colour = [c * (0.9 + 0.2 * sand[index]) for c in pick]
            level += 0.04 * (1.0 - polish)
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        heights.append(level)
        rough.append(0.88 - 0.68 * polish + 0.06 * sand[index] + 0.08 * pits[index] - 0.1 * stain * (1.0 - polish))
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.012, roughness=rough,
                     ao_radius=0.01, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
