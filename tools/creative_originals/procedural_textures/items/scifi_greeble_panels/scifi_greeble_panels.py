"""Science fiction greeble panels: recursive rectangle subdivision with vents, bolts and lights (standard library only).

The tile is split again and again into rectangles, each cut snapped to a 1/32 grid, so the tile edges are always
panel seams and the layout repeats. Every leaf rectangle is a panel with its own level and a bevelled rim; a hash of
the panel picks its detail: plain, grille slots, corner bolts, a light strip or a recessed port. A lookup grid at
the snap resolution finds each pixel's panel in constant time. Lights are carried by the emissive map.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "scifi_greeble_panels"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.92]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.12, 1.0]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
    {"name": "emissive", "channels": 3, "colour_space": "srgb", "convention": "gltf_emissive"},
]
PARAMETERS = [
    {"name": "depth", "type": "int", "default": 5, "minimum": 2, "maximum": 8,
     "meaning": "Subdivision depth: more levels give more, smaller panels."},
    {"name": "split_chance", "type": "float", "default": 0.8, "minimum": 0.3, "maximum": 1.0,
     "meaning": "Chance that a panel above the minimum size splits again."},
    {"name": "seam", "type": "float", "default": 0.004, "minimum": 0.001, "maximum": 0.012,
     "meaning": "Seam half-width in texture units."},
    {"name": "level_variation", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Height difference between panels."},
    {"name": "lights", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of panels with a light strip."},
    {"name": "grilles", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of panels with grille slots."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo and lights in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Grey panelling with cyan light strips.", "values": {}},
    "dense_machinery": {"description": "Deep, dense subdivision with many grilles.",
                        "values": {"depth": 7, "grilles": 0.35, "lights": 0.1, "level_variation": 0.9}},
    "corridor_white": {"description": "Clean white corridor panels with warm light strips.",
                       "values": {"depth": 4, "lights": 0.25, "grilles": 0.1, "level_variation": 0.3}},
    "hazard_dark": {"description": "Dark panels with red lights and heavy seams.",
                    "values": {"seam": 0.007, "lights": 0.2, "grilles": 0.25}},
}
#: Panel colours (two alternates), metal, seam and light colours per preset (sRGB).
PALETTES = {
    "default": ("#8d9298", "#a3a8ad", "#c9ccd0", "#18191c", "#3ad8ff"),
    "dense_machinery": ("#6f7378", "#585c61", "#b9bcc0", "#121315", "#ffb347"),
    "corridor_white": ("#e1e3e5", "#cfd2d5", "#c9ccd0", "#6b6f75", "#ffd8a0"),
    "hazard_dark": ("#2d2f33", "#3a3d42", "#8d9095", "#0b0b0c", "#ff3b30"),
}
GRID = 32


def _subdivide(rng, box: tuple, depth: int, chance: float, out: list) -> None:
    x0, y0, x1, y1 = box
    wide, tall = x1 - x0, y1 - y0
    if depth == 0 or (max(wide, tall) < 2) or (depth < 4 and not rng.chance(chance)):
        out.append(box)
        return
    vertical = wide > tall if wide != tall else rng.chance(0.5)
    span = wide if vertical else tall
    if span < 2:
        out.append(box)
        return
    cut = rng.integer(1, span - 1)
    if vertical:
        _subdivide(rng, (x0, y0, x0 + cut, y1), depth - 1, chance, out)
        _subdivide(rng, (x0 + cut, y0, x1, y1), depth - 1, chance, out)
    else:
        _subdivide(rng, (x0, y0, x1, y0 + cut), depth - 1, chance, out)
        _subdivide(rng, (x0, y0 + cut, x1, y1), depth - 1, chance, out)


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The greeble panel maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    panel_a, panel_b, metal_rgb, seam_rgb, light_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    rng = tk.Rng(seed, 1)
    boxes = []
    _subdivide(rng, (0, 0, GRID, GRID), p["depth"], p["split_chance"], boxes)
    lookup = [0] * (GRID * GRID)
    panels = []
    for number, (x0, y0, x1, y1) in enumerate(boxes):
        for gy in range(y0, y1):
            for gx in range(x0, x1):
                lookup[gy * GRID + gx] = number
        roll = rng.random()
        kind = 1 if roll < p["lights"] else 2 if roll < p["lights"] + p["grilles"] else \
            3 if roll < p["lights"] + p["grilles"] + 0.2 else 4 if roll < p["lights"] + p["grilles"] + 0.3 else 0
        panels.append({"box": (x0 / GRID, y0 / GRID, x1 / GRID, y1 / GRID), "kind": kind,
                       "level": rng.uniform(-1.0, 1.0), "alt": rng.chance(0.4), "tone": rng.uniform(-1.0, 1.0)})
    mottle = tk.fbm(width, height, 6, 3, tk.hash_u32(seed, 2))
    scuff = tk.fbm(width, height, 30, 3, tk.hash_u32(seed, 3))
    seam = p["seam"]
    pixel = 1.0 / min(width, height)
    variation = p["level_variation"]
    red, green, blue, heights, rough, metallic, glow = [], [], [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        gy = min(int(v * GRID), GRID - 1)
        base = y * width
        for x in range(width):
            index = base + x
            u = (x + 0.5) / width
            gx = min(int(u * GRID), GRID - 1)
            panel = panels[lookup[gy * GRID + gx]]
            x0, y0, x1, y1 = panel["box"]
            edge = min(u - x0, x1 - u, v - y0, y1 - v) - seam
            solid = tk.smoothstep(-pixel, pixel, edge)
            rim = tk.smoothstep(0.0, 0.006, edge)
            level = 0.45 + 0.18 * variation * panel["level"]
            local_u = (u - x0) / max(x1 - x0, 1e-9)
            local_v = (v - y0) / max(y1 - y0, 1e-9)
            light, dark, bump = 0.0, 0.0, 0.0
            kind = panel["kind"]
            if kind == 1:
                horizontal = (x1 - x0) >= (y1 - y0)
                across = abs((local_v if horizontal else local_u) - 0.5)
                along = local_u if horizontal else local_v
                if across < 0.12 and 0.12 < along < 0.88:
                    light = tk.smoothstep(0.12, 0.08, across)
            elif kind == 2:
                horizontal = (x1 - x0) < (y1 - y0)
                coordinate = local_v if horizontal else local_u
                slots = 0.5 + 0.5 * math.cos(math.tau * coordinate * max(4, round(12 * max(x1 - x0, y1 - y0))))
                margin = min(local_u, 1 - local_u, local_v, 1 - local_v)
                if margin > 0.12:
                    dark = tk.smoothstep(0.5, 0.8, slots)
            elif kind == 3:
                for cu in (0.1, 0.9):
                    for cv in (0.1, 0.9):
                        distance = math.hypot((local_u - cu) * (x1 - x0), (local_v - cv) * (y1 - y0))
                        if distance < 0.006:
                            bump = max(bump, math.sqrt(1.0 - (distance / 0.006) ** 2))
            elif kind == 4:
                distance = math.hypot((local_u - 0.5) * (x1 - x0), (local_v - 0.5) * (y1 - y0))
                port = min(x1 - x0, y1 - y0) * 0.3
                if distance < port:
                    dark = 0.6 * tk.smoothstep(port, port * 0.8, distance)
                    level -= 0.15 * tk.smoothstep(port, port * 0.8, distance)
            level = level * rim + 0.1 * (1.0 - rim) - 0.08 * dark + 0.06 * bump + 0.005 * mottle[index]
            base_rgb = panel_b if panel["alt"] else panel_a
            colour = [c * (1.0 + 0.05 * panel["tone"] + 0.04 * mottle[index]) for c in base_rgb]
            worn = tk.smoothstep(0.25, 0.45, scuff[index]) * (1.0 - rim + 0.2) * 0.8 + bump
            worn = min(1.0, worn)
            colour = [c + (m - c) * worn for c, m in zip(colour, metal_rgb)]
            colour = [c * (1.0 - 0.7 * dark) for c in colour]
            colour = [s + (c - s) * solid for c, s in zip(colour, seam_rgb)]
            if light > 0.0:
                colour = [c + (0.2 * l - c) * light for c, l in zip(colour, light_rgb)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            heights.append(max(0.0, level) * solid + 0.05 * (1.0 - solid))
            metallic.append(worn * solid)
            rough.append(0.45 - 0.15 * worn + 0.3 * dark + 0.25 * (1.0 - solid) - 0.3 * light)
            glow.append(light)
    emissive = tk.grade(([g * light_rgb[0] for g in glow], [g * light_rgb[1] for g in glow],
                         [g * light_rgb[2] for g in glow]), p["hue_shift"], 1.0, 1.0)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.02, roughness=rough,
                     metallic=metallic, emissive=emissive, ao_radius=0.015, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
