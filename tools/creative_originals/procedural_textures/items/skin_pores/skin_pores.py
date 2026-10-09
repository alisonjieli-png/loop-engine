"""Human skin micro-detail: pores, the furrow network, creases and tone, as tileable PBR maps for characters.

Pores are pits at jittered points of a fine grid with a random size each (some grid cells hold none). Skin furrows
form a polygonal network: the borders of anisotropic cells, more stretched along one direction, as tension lines in
real skin are. Aged skin adds longer creases from ridged noise. Tone carries melanin blotches, redness and optional
freckles; roughness follows oily and dry areas and stays higher in pores and furrows. The relief is small: these maps
are meant as tiling detail over a character's own albedo and normal maps.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "skin_pores"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.03, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.25, 0.9]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "pores", "type": "int", "default": 64, "minimum": 16, "maximum": 160,
     "meaning": "Pore grid cells across the tile (pore spacing)."},
    {"name": "pore_size", "type": "float", "default": 0.3, "minimum": 0.1, "maximum": 0.6,
     "meaning": "Pore radius as a share of the pore spacing."},
    {"name": "pore_depth", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How deep the pores are."},
    {"name": "furrows", "type": "int", "default": 22, "minimum": 6, "maximum": 60,
     "meaning": "Cells of the furrow network across the tile."},
    {"name": "furrow_depth", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Depth of the fine furrow network."},
    {"name": "anisotropy", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How much the furrow cells stretch across the tile (tension lines)."},
    {"name": "creases", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Longer wrinkles of aged skin."},
    {"name": "redness", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Blotchy redness from blood near the surface."},
    {"name": "freckles", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Density of freckles."},
    {"name": "oiliness", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Patches of lower roughness, as oily skin shows."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Medium-toned facial skin: fine pores, a light furrow network, some redness.",
                "values": {}},
    "fair": {"description": "Fair facial skin with fine pores and soft redness.",
             "values": {"redness": 0.35, "pore_depth": 0.45}},
    "deep_tone": {"description": "Deep brown facial skin with fine pores and a soft sheen.",
                  "values": {"redness": 0.1, "oiliness": 0.55, "pore_depth": 0.45}},
    "back_medium": {"description": "Medium-toned back skin: larger, sparser pores, flatter furrows.",
                    "values": {"pores": 40, "pore_size": 0.38, "pore_depth": 0.7, "furrows": 14,
                               "furrow_depth": 0.25, "oiliness": 0.25}},
    "aged": {"description": "Aged fair skin: deep furrows, creases and blotchy tone.",
             "values": {"furrow_depth": 0.85, "creases": 0.8, "anisotropy": 0.65, "redness": 0.45,
                        "oiliness": 0.15, "pores": 52}},
    "freckled": {"description": "Fair freckled skin with light redness.",
                 "values": {"freckles": 0.75, "redness": 0.25, "pores": 72}},
}
#: Base skin, melanin blotch, redness tint and freckle colours per preset (sRGB).
PALETTES = {
    "default": ("#c08a68", "#a06c4c", "#c4705e", "#8a5432"),
    "fair": ("#e2b59a", "#c99472", "#d98a7a", "#a8673e"),
    "deep_tone": ("#7a4e36", "#5e3a26", "#8a4a3a", "#4a2c1a"),
    "back_medium": ("#c8946e", "#a87650", "#c87a64", "#8a5530"),
    "aged": ("#ddb096", "#b88466", "#d67e72", "#9a6040"),
    "freckled": ("#eabea2", "#cf9b78", "#df9284", "#b06a3a"),
}


def _pores(width: int, height: int, cells: int, seed: int, size: float, presence: float = 0.85) -> list:
    """Round pits (or spots) in [0, 1] at jittered grid points, one per cell with probability ``presence`` and a
    random radius each: every pixel checks its 3 x 3 neighbouring cells."""
    rng = tk.Rng(seed, 0x9F)
    points = [(rng.uniform(0.15, 0.85), rng.uniform(0.15, 0.85),
               size * rng.uniform(0.5, 1.3) if rng.chance(presence) else 0.0) for _ in range(cells * cells)]
    out = []
    for y in range(height):
        gy = (y + 0.5) / height * cells
        j0 = int(gy)
        for x in range(width):
            gx = (x + 0.5) / width * cells
            i0 = int(gx)
            pit = 0.0
            for dj in (-1, 0, 1):
                j = j0 + dj
                row = (j % cells) * cells
                for di in (-1, 0, 1):
                    i = i0 + di
                    px, py, radius = points[row + i % cells]
                    if radius <= 0.0:
                        continue
                    dx, dy = gx - (i + px), gy - (j + py)
                    d2 = (dx * dx + dy * dy) / (radius * radius)
                    if d2 < 1.0:
                        depth = 1.0 - d2
                        if depth > pit:
                            pit = depth
            out.append(pit)
    return out


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The skin detail maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    base_rgb, melanin_rgb, red_rgb, freckle_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    pits = _pores(width, height, p["pores"], tk.hash_u32(seed, 1), p["pore_size"])
    across = p["furrows"]
    down = max(2, int(round(across * (1.0 + 1.5 * p["anisotropy"]))))
    network = tk.voronoi(width, height, across, down, tk.hash_u32(seed, 2), jitter=0.9)["edge"]
    warp_u = tk.fbm(width, height, 5, 3, tk.hash_u32(seed, 3))
    warp_v = tk.fbm(width, height, 5, 3, tk.hash_u32(seed, 4))
    network = tk.warp(network, width, height, warp_u, warp_v, 0.35 / across)
    creases = tk.ridged(width, height, 2, 3, tk.hash_u32(seed, 5), cells_y=7)
    creases = tk.warp(creases, width, height, warp_u, warp_v, 0.05)
    limit = max(4, min(width, height) // 2)
    bumps = tk.fbm(width, height, min(limit, across * 3), 2, tk.hash_u32(seed, 6))
    blotch = tk.fbm(width, height, 4, 4, tk.hash_u32(seed, 7))
    mottle = tk.fbm(width, height, min(limit, 14), 3, tk.hash_u32(seed, 12))
    flush = tk.fbm(width, height, 6, 3, tk.hash_u32(seed, 8))
    oil = tk.fbm(width, height, 3, 3, tk.hash_u32(seed, 9))
    freckle_spots = _pores(width, height, 30, tk.hash_u32(seed, 10), 0.27, 0.7 * p["freckles"]) \
        if p["freckles"] > 0.0 else None
    clusters = tk.fbm(width, height, 3, 3, tk.hash_u32(seed, 11))
    pore_depth, furrow_depth, crease_amount = p["pore_depth"], p["furrow_depth"], p["creases"]
    redness, freckles, oiliness = p["redness"], p["freckles"], p["oiliness"]
    furrow_width = 0.06 + 0.04 * furrow_depth
    heights, red, green, blue, rough = [], [], [], [], []
    for index in range(width * height):
        pit = pits[index] * pore_depth
        furrow = (1.0 - tk.smoothstep(0.0, furrow_width, network[index])) * furrow_depth
        crease = tk.smoothstep(0.82, 0.97, creases[index]) * crease_amount
        level = 0.62 + 0.04 * bumps[index] - 0.3 * pit - 0.16 * furrow - 0.3 * crease
        heights.append(level)
        melanin = tk.smoothstep(-0.2, 0.45, blotch[index]) * 0.5
        colour = [b + (m - b) * melanin for b, m in zip(base_rgb, melanin_rgb)]
        colour = [c + (r - c) * redness * tk.smoothstep(-0.1, 0.5, flush[index]) * 0.7
                  for c, r in zip(colour, red_rgb)]
        if freckle_spots is not None:
            spot = tk.smoothstep(0.0, 0.45, freckle_spots[index]) * tk.smoothstep(-0.35, 0.2, clusters[index])
            colour = [c + (f - c) * spot * 0.62 for c, f in zip(colour, freckle_rgb)]
        shade = 1.0 - 0.18 * pit - 0.1 * furrow - 0.15 * crease + 0.03 * bumps[index] + 0.09 * mottle[index]
        red.append(colour[0] * shade)
        green.append(colour[1] * shade)
        blue.append(colour[2] * shade)
        shine = oiliness * tk.smoothstep(-0.1, 0.4, oil[index])
        rough.append(0.58 - 0.22 * shine + 0.12 * pit + 0.08 * furrow + 0.03 * bumps[index] + 0.06 * mottle[index])
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.006, roughness=rough,
                     ao_radius=0.006, ao_strength=0.8, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
