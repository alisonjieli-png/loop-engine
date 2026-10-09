"""Stained glass: coloured panes held in raised lead came, glowing when lit from behind (standard library).

Panes come from one of three layouts: irregular cathedral pieces (the cells of a Worley diagram), diamond quarries
(a lattice turned 45 degrees, n(u + v) and n(u - v), which still repeats because n is whole) or Victorian circles
in squares. Every pane takes a glass colour from the preset's palette by a hash of its index. Glass is not uniform:
streaks run in a direction chosen per pane from whole-number vectors (so they repeat across the tile edge), seed
bubbles are tiny bright specks, and the glass thickness wavers. Lead came is drawn from the exact distance to the
pane borders with a rounded profile and solder blobs where quarry leads cross.

The emissive map is the light coming through the glass, for backlit windows; the albedo is the darker colour the
glass shows when lit from the front. Lead is a dull grey metal, rough and raised; glass is smooth.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "stained_glass"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.05, 0.9]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
    {"name": "emissive", "channels": 3, "colour_space": "srgb", "convention": "gltf_emissive"},
]
PARAMETERS = [
    {"name": "layout", "type": "int", "default": 0, "minimum": 0, "maximum": 2,
     "meaning": "0 irregular cathedral pieces, 1 diamond quarries, 2 circles in squares."},
    {"name": "pieces", "type": "int", "default": 6, "minimum": 2, "maximum": 16,
     "meaning": "Panes across the tile."},
    {"name": "lead_width", "type": "float", "default": 0.06, "minimum": 0.015, "maximum": 0.15,
     "meaning": "Width of the lead came as a share of a pane."},
    {"name": "streaks", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Streaks and density variation in the glass."},
    {"name": "seeds", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Tiny seed bubbles trapped in the glass."},
    {"name": "glow", "type": "float", "default": 0.85, "minimum": 0.1, "maximum": 1.0,
     "meaning": "Brightness of the light through the glass in the emissive map."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo and the light in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Cathedral glass: irregular jewel-coloured pieces in dark lead.", "values": {}},
    "diamond_quarries": {"description": "Leaded diamond panes of pale tinted glass with a few coloured ones.",
                         "values": {"layout": 1, "pieces": 6, "lead_width": 0.05, "streaks": 0.25, "seeds": 0.7}},
    "victorian_circles": {"description": "Ruby circles in amber squares with cobalt accents, Victorian style.",
                          "values": {"layout": 2, "pieces": 4, "lead_width": 0.05}},
    "amber_opalescent": {"description": "Large streaky opalescent amber and green pieces with thin copper foil.",
                         "values": {"pieces": 4, "lead_width": 0.03, "streaks": 0.95, "seeds": 0.1}},
}
#: Per preset: glass colours (sRGB) with weights, came colour (sRGB) and came metallic.
PALETTES = {
    "default": ([("#b01428", 3), ("#1a3caa", 3), ("#e0a020", 2), ("#1f8040", 2), ("#6a2a90", 1),
                 ("#d8e0d0", 1)], "#3a3c40", 0.5),
    "diamond_quarries": ([("#d8e2d4", 6), ("#e6dcb8", 3), ("#c8d8dc", 3), ("#a01c2c", 1), ("#2a4ca8", 1)],
                         "#46484c", 0.5),
    "victorian_circles": ([("#a8102a", 1), ("#d89a28", 1), ("#20409c", 1)], "#38393c", 0.5),
    "amber_opalescent": ([("#d08a24", 3), ("#e8b860", 2), ("#6a8a30", 2), ("#a85a20", 1)], "#7a5030", 0.8),
}
#: Whole-number streak directions, so streaks repeat across the tile edge.
STREAK_DIRECTIONS = ((1, 0), (0, 1), (1, 1), (1, -1), (2, 1), (1, 2), (2, -1), (1, -2))


def _pick(palette: list, value: float) -> tuple:
    total = sum(weight for _code, weight in palette)
    running = 0.0
    for code, weight in palette:
        running += weight / total
        if value < running:
            return tk.hex_rgb(code)
    return tk.hex_rgb(palette[-1][0])


def _layout(kind: int, width: int, height: int, seed: int, pieces: int) -> tuple:
    """(pane index, distance to the pane border in pane widths, joint closeness 0..1) for every pixel."""
    count = width * height
    panes, borders, joints = [0] * count, [0.0] * count, [0.0] * count
    if kind == 0:
        cells = tk.voronoi(width, height, pieces, pieces, tk.hash_u32(seed, 1), jitter=0.95)
        return cells["cell"], cells["edge"], joints
    for y in range(height):
        v = (y + 0.5) / height
        for x in range(width):
            u = (x + 0.5) / width
            index = y * width + x
            if kind == 1:
                a, b = pieces * (u + v), pieces * (u - v)
                da, db = abs(a - math.floor(a + 0.5)), abs(b - math.floor(b + 0.5))
                panes[index] = (int(math.floor(a)) % pieces) * pieces + int(math.floor(b)) % pieces
                borders[index] = min(da, db) * math.sqrt(0.5)
                joints[index] = max(0.0, 1.0 - math.hypot(da, db) / 0.12)
            else:
                cu, cv = u * pieces, v * pieces
                i, j = int(cu) % pieces, int(cv) % pieces
                fx, fy = cu - math.floor(cu), cv - math.floor(cv)
                ring = math.hypot(fx - 0.5, fy - 0.5)
                inside = ring < 0.36
                panes[index] = 2 * (j * pieces + i) + (1 if inside else 0)
                borders[index] = min(fx, 1.0 - fx, fy, 1.0 - fy, abs(ring - 0.36))
    return panes, borders, joints


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The stained glass maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    palette, came_hex, came_metal = PALETTES[preset]
    layout, pieces = p["layout"], p["pieces"]
    panes, borders, joints = _layout(layout, width, height, seed, pieces)
    half = 0.5 * p["lead_width"]
    pixel = pieces / min(width, height)
    colours, directions = {}, {}
    wave = tk.fbm(width, height, 3, 4, tk.hash_u32(seed, 2))
    fine = tk.fbm(width, height, 12, 3, tk.hash_u32(seed, 3))
    bubbles = tk.value_noise(width, height, 128, 128, tk.hash_u32(seed, 4))
    came = tk.hex_rgb(came_hex)
    streak_amount, seed_amount, glow = p["streaks"], p["seeds"], p["glow"]
    red, green, blue, e_red, e_green, e_blue = [], [], [], [], [], []
    heights, rough, metallic = [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        for x in range(width):
            index = y * width + x
            u = (x + 0.5) / width
            pane = panes[index]
            if pane not in colours:
                if layout == 2:
                    # circles take the first colour with an occasional accent in the third; squares the second
                    accent = 2 if tk.hash_float(seed, 6, pane) > 0.8 else 0
                    slot = accent if pane % 2 else 1
                    colours[pane] = tk.hex_rgb(palette[min(slot, len(palette) - 1)][0])
                else:
                    colours[pane] = _pick(palette, tk.hash_float(seed, 5, layout, pane))
                directions[pane] = STREAK_DIRECTIONS[tk.hash_u32(seed, 7, pane) % len(STREAK_DIRECTIONS)]
            glass = colours[pane]
            da, db = directions[pane]
            phase = (da * u + db * v) * 16.0 + 3.0 * wave[index]
            streak = 1.0 + streak_amount * (0.16 * math.sin(math.tau * phase) + 0.3 * fine[index])
            speck = seed_amount * tk.smoothstep(0.9, 0.97, bubbles[index])
            border = borders[index]
            lead = tk.smoothstep(half + 0.6 * pixel, half - 0.6 * pixel, border)
            profile = math.sqrt(max(0.0, 1.0 - (border / half) ** 2)) if border < half else 0.0
            solder = joints[index] if layout == 1 else 0.0
            light = [min(1.0, glow * (c * streak + 0.6 * speck)) * (1.0 - lead) for c in glass]
            front = [0.45 * c * (0.9 + 0.2 * (streak - 1.0)) + 0.3 * speck for c in glass]
            front = [g + (k - g) * lead for g, k in zip(front, came)]
            red.append(front[0])
            green.append(front[1])
            blue.append(front[2])
            e_red.append(light[0])
            e_green.append(light[1])
            e_blue.append(light[2])
            heights.append(0.35 + 0.05 * wave[index] + 0.02 * fine[index] + lead * (0.3 + 0.25 * profile)
                           + 0.15 * solder * lead + 0.03 * speck)
            rough.append(0.08 + 0.04 * (0.5 + 0.5 * fine[index]) + lead * 0.5)
            metallic.append(came_metal * lead)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    emissive = tk.grade((e_red, e_green, e_blue), p["hue_shift"], 1.0, 1.0)
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.03 / pieces, roughness=rough,
                     metallic=metallic, emissive=emissive, ao_radius=0.15 / pieces, ao_strength=0.8,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
