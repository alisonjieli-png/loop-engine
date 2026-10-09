"""Ashlar masonry: dressed stone blocks in coursed or broken bond, tileable PBR maps (standard library only).

The tile is a grid of unit cells: rows (courses, each with its own height when coursed) and 32 narrow columns. Blocks
are placed greedily on the torus in row order: each empty cell starts a block of a random length (and, for broken
ashlar, a height of one to three rows) shrunk to the free space, so blocks fill the tile exactly and repeat across
both edges. Every block's face is dressed in one of three styles: rubbed smooth with faint tool lines, a drafted
margin around a rock-faced centre that stands proud of the joints, or bush-hammered stippling.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "ashlar_masonry"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.03, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.35, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "layout", "type": "int", "default": 0, "minimum": 0, "maximum": 1,
     "meaning": "0 coursed ashlar (every block one course high, courses of varying height), 1 broken ashlar "
                "(blocks one to three equal rows high, joints broken in both directions)."},
    {"name": "courses", "type": "int", "default": 5, "minimum": 2, "maximum": 14,
     "meaning": "Rows of blocks across the tile height."},
    {"name": "block_length", "type": "float", "default": 0.3, "minimum": 0.12, "maximum": 0.7,
     "meaning": "Mean block length in tile widths; each block varies by about 40 percent."},
    {"name": "joint_width", "type": "float", "default": 0.006, "minimum": 0.002, "maximum": 0.025,
     "meaning": "Mortar joint width in texture units."},
    {"name": "joint_depth", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How far the mortar sits behind the faces."},
    {"name": "face_style", "type": "int", "default": 0, "minimum": 0, "maximum": 2,
     "meaning": "0 rubbed smooth with faint tool lines, 1 drafted margin around a rock-faced centre, "
                "2 bush-hammered stippling."},
    {"name": "margin", "type": "float", "default": 0.018, "minimum": 0.004, "maximum": 0.05,
     "meaning": "Width of the drafted margin around rock-faced centres, in texture units."},
    {"name": "relief", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How far rock-faced centres stand proud and how rough they are."},
    {"name": "tooling", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Depth of chisel lines on margins and smooth faces."},
    {"name": "weathering", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Eroded arrises, soot and streaks."},
    {"name": "colour_variation", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spread of colour between blocks."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Cream limestone in coursed ashlar, rubbed faces and thin joints.", "values": {}},
    "rockfaced_granite": {"description": "Grey granite in broken ashlar with drafted margins and rock-faced "
                                         "centres.",
                          "values": {"layout": 1, "courses": 6, "block_length": 0.24, "face_style": 1,
                                     "joint_width": 0.008, "relief": 0.8, "weathering": 0.2,
                                     "colour_variation": 0.4}},
    "sandstone_tooled": {"description": "Warm sandstone courses with chiselled faces and bedding streaks.",
                         "values": {"courses": 6, "block_length": 0.36, "tooling": 0.85, "weathering": 0.45,
                                    "colour_variation": 0.7}},
    "bush_hammered": {"description": "Pale limestone broken ashlar with stippled bush-hammered faces.",
                      "values": {"layout": 1, "courses": 7, "block_length": 0.2, "face_style": 2,
                                 "joint_width": 0.005, "weathering": 0.15, "colour_variation": 0.35}},
}
#: Stone colours, mortar, soot, speck colour, speck share, bedding streak strength, stone roughness (sRGB).
PALETTES = {
    "default": (["#d8ccb2", "#cfc2a6", "#e0d5bd", "#c7b99b", "#d4c7ab"], "#b9b1a0", "#5b5448", "#bcae92", 0.02,
                0.05, 0.78),
    "rockfaced_granite": (["#8d8c8a", "#7f7e7c", "#9a9896", "#757472", "#878684"], "#a39f97", "#3a3836",
                          "#3b3a3a", 0.12, 0.0, 0.8),
    "sandstone_tooled": (["#c39a6b", "#b8895a", "#cfa87a", "#a97c50", "#bf9466"], "#c8b89c", "#4d3a2a", "#a07650",
                         0.03, 0.18, 0.84),
    "bush_hammered": (["#e2dccd", "#dbd4c3", "#e8e2d4", "#d3cbb8", "#dfd8c8"], "#cbc5b8", "#6a655b", "#b8b0a0",
                      0.08, 0.0, 0.82),
}
GRID_COLUMNS = 32


def _split(total: int, mean: float, rng, minimum: int = 4) -> list:
    """Random block lengths (in grid columns) that sum to ``total``, each at least ``minimum`` when total allows."""
    lengths, left = [], total
    while True:
        if left < 2 * minimum or left <= round(mean * 1.4):
            lengths.append(left)
            return lengths
        want = min(max(minimum, int(round(mean * rng.uniform(0.6, 1.4)))), left - minimum)
        lengths.append(want)
        left -= want


def _layout(rows: int, broken: bool, block_length: float, seed: int) -> tuple:
    """(row starts, row heights, owner grid, blocks) of the rows x GRID_COLUMNS torus filled with blocks.

    Coursed: every row is split into blocks from its own random offset. Broken: rows are taken in pairs; each pair
    is split into segments that are either one tall block over both rows or two rows split independently, so the
    joints break in both directions. Each block is (first row, first column, rows, columns); owner[row][column] is
    the block covering that cell."""
    rng = tk.Rng(seed, 0xA5)
    if broken:
        heights = [1.0 / rows] * rows
    else:
        raw = [rng.uniform(0.7, 1.3) for _ in range(rows)]
        heights = [value / sum(raw) for value in raw]
    starts = [sum(heights[:k]) for k in range(rows)]
    owner = [[-1] * GRID_COLUMNS for _ in range(rows)]
    blocks = []
    mean = max(3.0, block_length * GRID_COLUMNS)

    def place(row: int, column: int, tall: int, span: int) -> None:
        for r in range(tall):
            for k in range(span):
                owner[(row + r) % rows][(column + k) % GRID_COLUMNS] = len(blocks)
        blocks.append((row, column, tall, span))

    row = 0
    while row < rows:
        offset = rng.integer(0, GRID_COLUMNS - 1)
        if broken and row + 1 < rows:
            column = offset
            for segment in _split(GRID_COLUMNS, mean * 1.3, rng):
                if rng.random() < 0.45 or segment < 6:
                    place(row, column, 2, segment)
                else:
                    for level in (0, 1):
                        position = column
                        for span in _split(segment, mean * 0.8, rng):
                            place(row + level, position, 1, span)
                            position += span
                column += segment
            row += 2
        else:
            column = offset
            for span in _split(GRID_COLUMNS, mean, rng):
                place(row, column, 1, span)
                column += span
            row += 1
    return starts, heights, owner, blocks


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The ashlar maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    stones_hex, mortar_hex, soot_hex, speck_hex, speck_share, bedding, stone_rough = PALETTES[preset]
    stones = [tk.hex_rgb(code) for code in stones_hex]
    mortar_rgb, soot_rgb, speck_rgb = tk.hex_rgb(mortar_hex), tk.hex_rgb(soot_hex), tk.hex_rgb(speck_hex)
    rows = p["courses"]
    starts, row_heights, owner, blocks = _layout(rows, p["layout"] == 1, p["block_length"], tk.hash_u32(seed, 1))
    row_ends = [s + h for s, h in zip(starts, row_heights)]
    extents = []
    for row, column, tall, span in blocks:
        y0 = starts[row]
        extents.append((column / GRID_COLUMNS, span / GRID_COLUMNS, y0, sum(row_heights[(row + k) % rows]
                                                                             for k in range(tall))))
    traits = [tuple(tk.hash_float(seed, 11, b, k) for k in range(6)) for b in range(len(blocks))]
    style, margin, relief, tooling = p["face_style"], p["margin"], p["relief"], p["tooling"]
    weathering, variation = p["weathering"], p["colour_variation"]
    half_joint = p["joint_width"] * 0.5
    rock = tk.fbm(width, height, 12, 5, tk.hash_u32(seed, 2))
    pits = tk.white_noise(width, height, tk.hash_u32(seed, 3))
    erosion = tk.fbm(width, height, 24, 3, tk.hash_u32(seed, 4))
    streaks = tk.fbm(width, height, 6, 4, tk.hash_u32(seed, 5), cells_y=24)
    soot = tk.fbm(width, height, 4, 4, tk.hash_u32(seed, 6))
    joint_level = 0.5 - 0.3 * p["joint_depth"]
    pixel = 1.0 / width
    count = len(stones) - 1
    red, green, blue, heights, rough = [], [], [], [], []
    row_of = []
    for y in range(height):
        v = (y + 0.5) / height
        row = 0
        while row < rows - 1 and v >= row_ends[row]:
            row += 1
        row_of.append(row)
    for y in range(height):
        v = (y + 0.5) / height
        owners = owner[row_of[y]]
        for x in range(width):
            index = y * width + x
            u = (x + 0.5) / width
            block = owners[min(int(u * GRID_COLUMNS), GRID_COLUMNS - 1)]
            x0, bw, y0, bh = extents[block]
            lx = (u - x0) % 1.0
            ly = (v - y0) % 1.0
            dx = min(lx, bw - lx)
            dy = min(ly, bh - ly)
            arris = 0.003 + 0.006 * weathering * max(0.0, erosion[index] + 0.3)
            inside = min(dx, dy) - half_joint
            trait = traits[block]
            t = inside / arris
            profile = 0.0 if t <= 0.0 else 1.0 if t >= 1.0 else math.sqrt(1.0 - (1.0 - t) * (1.0 - t))
            angle = 0.25 * math.pi * (1 if trait[4] > 0.5 else -1)
            along = lx * math.cos(angle) + ly * math.sin(angle)
            lines = math.sin(along * 400.0 + trait[5] * 40.0)
            if style == 1:
                core = tk.smoothstep(margin * 0.6, margin * 1.4, inside)
                face = 0.76 + core * relief * (0.08 + 0.07 * rock[index]) + (1.0 - core) * 0.006 * tooling * lines
                texture_rough = core * relief
            elif style == 2:
                face = 0.78 + 0.012 * (pits[index] - 0.5) * (0.5 + tooling)
                texture_rough = 0.5
            else:
                face = 0.78 + 0.004 * tooling * lines + 0.006 * rock[index]
                texture_rough = 0.1
            face += 0.012 * (trait[1] - 0.5)
            level = joint_level + (face - joint_level) * profile
            heights.append(level)
            cover = tk.smoothstep(-pixel, pixel, inside)
            pick = (trait[0] * variation + 0.5 * (1.0 - variation)) * count
            low = min(int(pick), count - 1)
            f = pick - low
            stone = [a + (b - a) * f for a, b in zip(stones[low], stones[low + 1])]
            tone = 1.0 + bedding * streaks[index] + 0.05 * rock[index] + 0.04 * (pits[index] - 0.5) \
                + 0.06 * texture_rough * rock[index] - 0.06 * (1.0 - profile)
            stone = [c * tone for c in stone]
            if pits[index] < speck_share:
                stone = [c + (s - c) * 0.5 for c, s in zip(stone, speck_rgb)]
            dirt = weathering * tk.clamp(0.6 * max(0.0, soot[index] - 0.05) + 0.3 * (1.0 - profile))
            stone = [c + (s - c) * dirt * 0.6 for c, s in zip(stone, soot_rgb)]
            joint = [c * (0.85 + 0.2 * pits[index]) for c in mortar_rgb]
            colour = [j + (s - j) * cover for j, s in zip(joint, stone)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            block_rough = stone_rough + 0.05 * (trait[2] - 0.5) + 0.1 * texture_rough - 0.12 * (1.0 - texture_rough) \
                * (1.0 - weathering)
            rough.append(0.95 + (block_rough - 0.95) * cover)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.02, roughness=rough,
                     ao_radius=0.02, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
