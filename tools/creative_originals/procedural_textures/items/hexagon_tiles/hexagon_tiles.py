"""Hexagonal ceramic tiles on a periodic hex lattice: tileable PBR maps from the standard library only.

The tile holds ``columns`` pointy-top hexagons across and an even number of rows (texkit.hex_rows), so the lattice
repeats in both directions. Each pixel finds its hexagon among the two nearest rows of centres and measures the
distance to the cell border (the vertical sides and the bisectors with the diagonal neighbours). That distance
shapes the grout, the bevel and a pillowed glaze; a colour rule on the lattice (random mix, scattered flowers,
alternating rows or clustered blends) picks each tile's glaze, and noise chips the edges down to the clay body.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "hexagon_tiles"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.03, 0.92]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.04, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "columns", "type": "int", "default": 7, "minimum": 3, "maximum": 26,
     "meaning": "Hexagons across the tile width; the row count is the even number closest to a regular lattice."},
    {"name": "pattern", "type": "int", "default": 0, "minimum": 0, "maximum": 3,
     "meaning": "Colour rule on the lattice: 0 random mix with accents, 1 scattered flowers (an accent centre with "
                "six petals), 2 alternating rows, 3 clustered blend that drifts between the palette colours."},
    {"name": "grout_width", "type": "float", "default": 0.05, "minimum": 0.01, "maximum": 0.2,
     "meaning": "Joint width in hexagon widths (across the flats)."},
    {"name": "grout_depth", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How far the grout sits below the tile faces: 0 flush, 1 deep."},
    {"name": "bevel", "type": "float", "default": 0.06, "minimum": 0.01, "maximum": 0.25,
     "meaning": "Width of the rounded tile edge in hexagon widths."},
    {"name": "pillow", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Dome of the glaze toward the tile centre, as handmade and cushion-edged tiles have."},
    {"name": "glaze_waviness", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Low ripples in the glaze surface that break up reflections."},
    {"name": "chipping", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Chipped tile edges that expose the clay body, 0 none to 1 heavily damaged."},
    {"name": "accent_share", "type": "float", "default": 0.12, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of accent tiles in the random mix, or how densely flowers are scattered."},
    {"name": "colour_variation", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spread of tone between tiles of one colour."},
    {"name": "dirt", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Grime in the grout and along the tile edges."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "White glossy hexagon wall tiles with a few pale grey accents and light grout.",
                "values": {}},
    "black_white_flowers": {"description": "Small white hexagons with scattered flowers: six black petals around a "
                                           "grey centre.",
                            "values": {"columns": 14, "pattern": 1, "grout_width": 0.07, "bevel": 0.08,
                                       "pillow": 0.25, "accent_share": 0.5, "chipping": 0.05,
                                       "colour_variation": 0.2}},
    "terracotta_pavers": {"description": "Large matte terracotta hexagon pavers with wide sandy joints and "
                                         "worn, chipped edges.",
                          "values": {"columns": 5, "grout_width": 0.08, "grout_depth": 0.35, "bevel": 0.04,
                                     "pillow": 0.15, "glaze_waviness": 0.8, "chipping": 0.55,
                                     "accent_share": 0.0, "colour_variation": 0.8, "dirt": 0.45}},
    "mint_rows": {"description": "Glossy mint and white hexagons in alternating rows.",
                  "values": {"columns": 9, "pattern": 2, "grout_width": 0.045, "pillow": 0.55,
                             "colour_variation": 0.3}},
    "ocean_blend": {"description": "Small blue and teal hexagons drifting between shades in clusters.",
                    "values": {"columns": 18, "pattern": 3, "grout_width": 0.06, "bevel": 0.09, "pillow": 0.6,
                               "glaze_waviness": 0.6, "chipping": 0.05, "colour_variation": 0.5}},
}
#: Glaze colours (blend order), accent, petal colour, grout, clay body, edge tint, glaze roughness per preset (sRGB).
PALETTES = {
    "default": (["#eeede8", "#e8e7e1", "#f2f1ec"], "#c9cac8", "#c9cac8", "#b9b5ac", "#d9c7a8", "#b9b6ae", 0.07),
    "black_white_flowers": (["#efeee9", "#e9e8e2", "#f3f2ed"], "#9fa3a8", "#1d1d1f", "#bdbab3", "#d6c9b0",
                            "#a8a59e", 0.09),
    "terracotta_pavers": (["#b5603a", "#a4552f", "#c26e45", "#9a4b2b", "#b9673f"], "#8e4527", "#8e4527",
                          "#b3a58c", "#c47a52", "#7d3f24", 0.82),
    "mint_rows": (["#a9d8c3", "#f1f0ea"], "#86c4aa", "#86c4aa", "#d6d3cb", "#e0cfb2", "#6fa891", 0.06),
    "ocean_blend": (["#1f4f7a", "#2a6f8f", "#3a8f9a", "#5fb0b0", "#1b3d66"], "#bfe3e0", "#bfe3e0", "#cbc8c0",
                    "#d8c6a6", "#123552", 0.05),
}
#: Cube-coordinate steps to the six neighbours of a hexagon (dq, dr).
NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1))


def _offset_neighbour(i: int, j: int, dq: int, dr: int, columns: int, rows: int) -> tuple:
    """The hexagon dq, dr axial steps from (i, j) in odd-row-shifted offset coordinates, wrapped onto the torus."""
    q = i - (j - (j & 1)) // 2 + dq
    r = j + dr
    return (q + (r - (r & 1)) // 2) % columns, r % rows


def _flower_layout(columns: int, rows: int, density: float, seed: int) -> dict:
    """{tile index: 1 for a flower centre, 2 for a petal}: flowers dropped in a seeded order, none touching another."""
    order = list(range(columns * rows))
    rng = tk.Rng(seed, 0xF1)
    for k in range(len(order) - 1, 0, -1):
        m = rng.integer(0, k)
        order[k], order[m] = order[m], order[k]
    roles, blocked = {}, set()
    ring2 = [(dq, dr) for dq in range(-3, 4) for dr in range(-3, 4) if max(abs(dq), abs(dr), abs(dq + dr)) <= 3]
    wanted = max(1, int(round(density * columns * rows / 14.0)))
    for index in order:
        if len(roles) // 7 >= wanted:
            break
        i, j = index % columns, index // columns
        if index in blocked:
            continue
        petals = [_offset_neighbour(i, j, dq, dr, columns, rows) for dq, dr in NEIGHBOURS]
        if any(pi + pj * columns in roles for pi, pj in petals):
            continue
        roles[index] = 1
        for pi, pj in petals:
            roles[pi + pj * columns] = 2
        for dq, dr in ring2:
            ni, nj = _offset_neighbour(i, j, dq, dr, columns, rows)
            blocked.add(ni + nj * columns)
    return roles


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The hexagon tile maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    glazes_hex, accent_hex, petal_hex, grout_hex, body_hex, edge_hex, glaze_rough = PALETTES[preset]
    glazes = [tk.hex_rgb(code) for code in glazes_hex]
    accent, petal = tk.hex_rgb(accent_hex), tk.hex_rgb(petal_hex)
    grout_rgb, body_rgb, edge_rgb = tk.hex_rgb(grout_hex), tk.hex_rgb(body_hex), tk.hex_rgb(edge_hex)
    columns = p["columns"]
    rows = tk.hex_rows(columns)
    spacing = columns / rows
    diagonal = math.sqrt(0.25 + spacing * spacing)
    count = columns * rows
    rng = tk.Rng(seed, 0xA7)
    traits = [(rng.random(), rng.uniform(-1.0, 1.0), rng.uniform(-1.0, 1.0), rng.uniform(-1.0, 1.0), rng.random())
              for _ in range(count)]
    pattern, share, variation = p["pattern"], p["accent_share"], p["colour_variation"]
    blend_field = tk.fbm(4 * columns, 4 * rows, 2, 3, tk.hash_u32(seed, 9), kind=tk.VALUE)
    flowers = _flower_layout(columns, rows, share, tk.hash_u32(seed, 8)) if pattern == 1 else {}
    colours = []
    last = len(glazes) - 1
    for index in range(count):
        trait = traits[index]
        i, j = index % columns, index // columns
        if pattern == 1:
            role = flowers.get(index, 0)
            base = glazes[min(int(trait[4] * len(glazes)), last)]
            colour = accent if role == 1 else petal if role == 2 else base
        elif pattern == 2:
            colour = glazes[j % len(glazes)]
        elif pattern == 3:
            sample = blend_field[(4 * j + 2) * 4 * columns + (4 * i + 2 * (j & 1) + 2) % (4 * columns)]
            position = tk.clamp((sample - 0.25) * 2.0 + 0.25 * (trait[4] - 0.5)) * last
            low = min(int(position), max(last - 1, 0))
            f = position - low if last else 0.0
            colour = tuple(a + (b - a) * f for a, b in zip(glazes[low], glazes[min(low + 1, last)]))
        else:
            colour = accent if trait[0] < share else glazes[min(int(trait[4] * len(glazes)), last)]
        tone = 1.0 + 0.12 * trait[1] * variation
        colours.append(tuple(c * tone for c in colour))
    waves = tk.fbm(width, height, max(2, columns // 2), 3, tk.hash_u32(seed, 2))
    chips = tk.fbm(width, height, columns * 4, 4, tk.hash_u32(seed, 3))
    speck = tk.white_noise(width, height, tk.hash_u32(seed, 4))
    grime = tk.fbm(width, height, max(3, columns), 3, tk.hash_u32(seed, 5))
    half_grout = p["grout_width"] * 0.5
    bevel = p["bevel"]
    chip_reach = p["chipping"] * (0.05 + 0.8 * p["bevel"])
    pillow = p["pillow"]
    waviness = p["glaze_waviness"]
    dirt = p["dirt"]
    grout_level = 0.5 - 0.36 * p["grout_depth"]
    pixel = columns / width
    red, green, blue, heights, rough = [], [], [], [], []
    floor = math.floor
    for y in range(height):
        row_position = (y + 0.5) / height * rows
        first = floor(row_position)
        second = first + 1 if row_position - first >= 0.5 else first - 1
        for x in range(width):
            index = y * width + x
            column_position = (x + 0.5) / width * columns
            best = None
            for j in (first, second):
                shift = 0.5 * (j & 1)
                i = floor(column_position - shift)
                dx = column_position - (i + 0.5 + shift)
                dy = (row_position - (j + 0.5)) * spacing
                d2 = dx * dx + dy * dy
                if best is None or d2 < best[0]:
                    best = (d2, i, j, dx, dy)
            _d2, i, j, dx, dy = best
            tile = (i % columns) + (j % rows) * columns
            ax, ay = abs(dx), abs(dy)
            inside = min(0.5 - ax, diagonal * 0.5 - (0.5 * ax + spacing * ay) / diagonal) - half_grout
            trait = traits[tile]
            t = inside / bevel
            profile = 0.0 if t <= 0.0 else 1.0 if t >= 1.0 else math.sqrt(1.0 - (1.0 - t) * (1.0 - t))
            dome = tk.clamp(inside / 0.4)
            top = 0.8 + 0.05 * pillow * (1.0 - (1.0 - dome) * (1.0 - dome)) + 0.02 * waviness * waves[index] \
                + 0.015 * (trait[2] * dx + trait[3] * dy)
            grout = grout_level + 0.03 * grime[index]
            level = grout + (top - grout) * profile
            carve = chip_reach * max(0.0, chips[index] - 0.05) * 2.5 - inside
            chipped = tk.smoothstep(-pixel, pixel, carve) if inside > -pixel else 0.0
            if chipped > 0.0:
                level = min(level, grout + (top - grout) * (0.55 + 0.1 * chips[index]))
            heights.append(level)
            cover = tk.smoothstep(-pixel, pixel, inside)
            tone = 0.86 + 0.18 * speck[index] - 0.3 * dirt * max(0.0, 0.2 - grime[index])
            colour = [c * tone for c in grout_rgb]
            roughness = 0.93
            if cover > 0.0:
                glaze = colours[tile]
                pooled = (1.0 - tk.smoothstep(0.0, bevel * 1.6, inside)) * 0.55
                shine = 1.0 + 0.03 * waves[index] * waviness + 0.03 * (speck[index] - 0.5)
                edge_dirt = dirt * 0.25 * (1.0 - tk.smoothstep(0.0, bevel * 2.0, inside))
                tile_colour = [(g + (e - g) * pooled) * shine * (1.0 - edge_dirt) for g, e in zip(glaze, edge_rgb)]
                tile_rough = glaze_rough + 0.04 * trait[4] + 0.05 * waviness * abs(waves[index]) \
                    + (0.25 if glaze_rough > 0.5 else 0.1) * (1.0 - profile)
                if chipped > 0.0:
                    body = [c * (0.9 + 0.1 * speck[index]) for c in body_rgb]
                    tile_colour = [a + (b - a) * chipped for a, b in zip(tile_colour, body)]
                    tile_rough += (0.86 - tile_rough) * chipped
                colour = [a + (b - a) * cover for a, b in zip(colour, tile_colour)]
                roughness += (tile_rough - roughness) * cover
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            rough.append(roughness)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.014, roughness=rough,
                     ao_radius=0.02, ao_strength=1.1, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
