"""Fur pelt: thousands of strands painted along a smooth periodic flow field, tileable PBR maps.

A flow direction is defined everywhere by a periodic noise field around a main lie direction, so the fur combs one
way with gentle swirls. Each strand starts at a root, follows the flow for a few steps and tapers to its tip; roots
gather into clumps whose tips pull together, as wet or thick fur parts into locks. Strands are painted with a
z-buffer and their height rises toward the tip, so every strand lies over the roots of the strands ahead of it. A
strand takes its colour from the coat pattern at its root (solid, tabby stripes, spots or rosettes) and changes
colour along its length (dark root, light band near the tip), the agouti banding of many mammals.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "fur_strands"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.3, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "length", "type": "float", "default": 0.05, "minimum": 0.015, "maximum": 0.12,
     "meaning": "Strand length in texture units."},
    {"name": "thickness", "type": "float", "default": 0.0022, "minimum": 0.001, "maximum": 0.006,
     "meaning": "Strand radius at the root in texture units (drawn at least about a pixel wide)."},
    {"name": "coverage", "type": "float", "default": 3.0, "minimum": 1.5, "maximum": 5.0,
     "meaning": "How many strands cover each point on average; low values show the undercoat."},
    {"name": "swirl", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How far the flow turns away from the main lie direction."},
    {"name": "clumping", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How strongly strand tips gather into locks."},
    {"name": "pattern", "type": "int", "default": 1, "minimum": 0, "maximum": 3,
     "meaning": "Coat pattern: 0 solid, 1 tabby stripes, 2 spots, 3 rosettes (dark rings)."},
    {"name": "banding", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Colour change along each strand: darker root and a light band near the tip."},
    {"name": "gloss", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Sheen of the strands."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Brown tabby cat fur with dark stripes and banded hairs.", "values": {}},
    "leopard_rosettes": {"description": "Short golden pelt with dark rosettes.",
                         "values": {"pattern": 3, "length": 0.035, "swirl": 0.2, "clumping": 0.2,
                                    "banding": 0.25}},
    "black_glossy": {"description": "Short glossy black fur lying flat.",
                     "values": {"pattern": 0, "length": 0.03, "swirl": 0.15, "clumping": 0.1, "gloss": 0.85,
                                "banding": 0.1}},
    "white_fluffy": {"description": "Long white fluffy fur parted into soft locks.",
                     "values": {"pattern": 0, "length": 0.1, "thickness": 0.0028, "swirl": 0.6, "clumping": 0.8,
                                "banding": 0.2, "coverage": 3.5}},
    "dalmatian_spots": {"description": "Short white coat with round black spots.",
                        "values": {"pattern": 2, "length": 0.028, "swirl": 0.25, "clumping": 0.15,
                                   "banding": 0.05}},
}
#: Coat colour, pattern colour, light tip-band colour, undercoat colour per preset (sRGB).
PALETTES = {
    "default": ("#8a6a48", "#2e2116", "#d2b48a", "#3a2a1c"),
    "leopard_rosettes": ("#d4a052", "#2a1c10", "#efd6a0", "#6a4a24"),
    "black_glossy": ("#1e1c1e", "#121012", "#3c383a", "#0c0a0c"),
    "white_fluffy": ("#ece6dc", "#c9c0b2", "#fbf8f2", "#8a8278"),
    "dalmatian_spots": ("#ece8e0", "#1a1818", "#ffffff", "#7a7670"),
}
SEGMENTS = 3


def _coat(pattern: int, u: float, v: float, warp: float, seed: int) -> float:
    """How much of the pattern colour the coat has at (u, v): 0 coat colour, 1 pattern colour."""
    if pattern == 0:
        return 0.0
    if pattern == 1:
        wave = math.sin(math.tau * (1.0 * u + 4.0 * v) + 2.5 * warp)
        return tk.smoothstep(0.35, 0.75, wave)
    cells = 7 if pattern == 2 else 6
    gx, gy = u * cells, v * cells
    i0, j0 = int(math.floor(gx)), int(math.floor(gy))
    nearest = 9.0
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            i, j = i0 + di, j0 + dj
            px = i + 0.2 + 0.6 * tk.hash_float(i % cells, j % cells, seed, 1)
            py = j + 0.2 + 0.6 * tk.hash_float(i % cells, j % cells, seed, 2)
            nearest = min(nearest, math.hypot(gx - px, gy - py) * (1.0 + 0.25 * warp))
    if pattern == 2:
        return 1.0 - tk.smoothstep(0.18, 0.26, nearest)
    ring = 1.0 - tk.smoothstep(0.05, 0.1, abs(nearest - 0.24))
    return ring * 0.95 + (1.0 - tk.smoothstep(0.12, 0.2, nearest)) * 0.25


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The fur maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    coat_rgb, pattern_rgb, tip_rgb, under_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    length, swirl, clumping = p["length"], p["swirl"], p["clumping"]
    banding, gloss, pattern = p["banding"], p["gloss"], p["pattern"]
    radius = max(p["thickness"], 0.55 / min(width, height))
    strands = int(p["coverage"] / (1.6 * radius * length))
    flow = tk.fbm(width, height, 3, 3, tk.hash_u32(seed, 1))
    warp = tk.fbm(width, height, 4, 3, tk.hash_u32(seed, 2))
    rng = tk.Rng(seed, 0xF0)
    lie = rng.uniform(0.0, math.tau)
    count = width * height
    heights = [0.0] * count
    red, green, blue = [under_rgb[0]] * count, [under_rgb[1]] * count, [under_rgb[2]] * count
    rough = [0.95] * count
    clump_cells = max(2, int(round(1.0 / max(length * 0.6, 0.02))))
    clump_tips = [(rng.gauss(0.0, 0.5), rng.gauss(0.0, 0.5)) for _ in range(clump_cells * clump_cells)]
    step = length / SEGMENTS
    for _ in range(strands):
        u, v = rng.random(), rng.random()
        clump = clump_tips[(int(v * clump_cells) % clump_cells) * clump_cells + int(u * clump_cells) % clump_cells]
        shade = rng.uniform(0.85, 1.12)
        lift = rng.uniform(0.0, 0.25)
        share = _coat(pattern, u, v, tk.sample(warp, width, height, u, v), seed)
        base_rgb = [c + (q - c) * share for c, q in zip(coat_rgb, pattern_rgb)]
        band_rgb = [c + (q - c) * share * 0.7 for c, q in zip(tip_rgb, pattern_rgb)]
        points = [(u, v)]
        pu, pv = u, v
        for segment in range(SEGMENTS):
            angle = lie + swirl * math.pi * tk.sample(flow, width, height, pu % 1.0, pv % 1.0)
            du, dv = step * math.cos(angle), step * math.sin(angle)
            pull = clumping * (segment + 1) / SEGMENTS
            du += pull * clump[0] * step * 0.6
            dv += pull * clump[1] * step * 0.6
            pu, pv = pu + du, pv + dv
            points.append((pu, pv))
        for segment in range(SEGMENTS):
            (a_u, a_v), (b_u, b_v) = points[segment], points[segment + 1]
            taper = radius * (1.0 - 0.55 * segment / SEGMENTS)
            for index, d, t in tk.segment_pixels(width, height, a_u, a_v, b_u, b_v, taper):
                along = (segment + t) / SEGMENTS
                if d > 1.0 - 0.45 * along * along:
                    continue
                surface = 0.3 + 0.5 * along + lift + 0.15 * (1.0 - d * d)
                if surface > heights[index]:
                    heights[index] = surface
                    band = banding * math.exp(-((along - 0.78) / 0.12) ** 2)
                    root = banding * (1.0 - tk.smoothstep(0.0, 0.4, along)) * 0.35
                    colour = [b + (t_rgb - b) * band for b, t_rgb in zip(base_rgb, band_rgb)]
                    light = shade * (0.78 + 0.3 * (1.0 - d) - root)
                    red[index], green[index], blue[index] = (c * light for c in colour)
                    rough[index] = 0.8 - 0.45 * gloss * (1.0 - d) + 0.1 * along
    peak = max(heights)
    heights = [value / peak for value in heights]
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.012, roughness=rough,
                     ao_radius=0.008, ao_strength=1.3, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
