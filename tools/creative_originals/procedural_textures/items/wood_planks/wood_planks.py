"""Wood floor planks: tileable PBR maps with staggered joints and growth-ring grain (standard library only).

Boards run across the tile in rows; each row has its own random joint offset, so butt joints stagger and the floor
repeats. Each board is a slice of a log: the distance from a virtual pith axis, inclined slightly to the board,
gives the growth rings, so flat-sawn boards show cathedral arches and boards cut near the pith show straight grain.
Noise warps the rings, fine streaks stretched along the board add pores, and optional knots bend the rings around
a dark core. Every board takes its own tone, pith position and incline from a hash of its index.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "wood_planks"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.12, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "board_rows", "type": "int", "default": 5, "minimum": 2, "maximum": 16,
     "meaning": "Rows of boards across the tile height."},
    {"name": "boards_per_row", "type": "int", "default": 2, "minimum": 1, "maximum": 6,
     "meaning": "Boards end to end in each row across the tile width."},
    {"name": "gap", "type": "float", "default": 0.004, "minimum": 0.0005, "maximum": 0.02,
     "meaning": "Width of the joints between boards in texture units."},
    {"name": "ring_density", "type": "float", "default": 30.0, "minimum": 5.0, "maximum": 80.0,
     "meaning": "Growth rings per texture unit of distance from the pith."},
    {"name": "ring_contrast", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Darkness of the late-wood bands."},
    {"name": "knots", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Chance of a knot on each board."},
    {"name": "board_variation", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spread of tone between boards."},
    {"name": "gloss", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Finish from raw or weathered (0) to lacquered (1)."},
    {"name": "weathering", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Raised grain, greying and end checks from exposure."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Oiled oak boards with fine cathedral grain.", "values": {}},
    "walnut": {"description": "Dark lacquered walnut, wide boards, subtle rings.",
               "values": {"board_rows": 4, "ring_density": 22.0, "ring_contrast": 0.35, "gloss": 0.85,
                          "knots": 0.05}},
    "knotty_pine": {"description": "Yellow pine with strong rings and frequent knots.",
                    "values": {"ring_density": 18.0, "ring_contrast": 0.75, "knots": 0.75, "gloss": 0.35,
                               "board_rows": 5, "boards_per_row": 1}},
    "weathered_grey": {"description": "Sun-bleached grey deck boards with raised grain and checks.",
                       "values": {"weathering": 0.9, "gloss": 0.0, "gap": 0.009, "ring_contrast": 0.7,
                                  "board_rows": 6, "boards_per_row": 2}},
    "white_oak_strip": {"description": "Narrow pale strips of lacquered white oak.",
                        "values": {"board_rows": 10, "boards_per_row": 3, "ring_density": 40.0, "gloss": 0.75,
                                   "ring_contrast": 0.3, "gap": 0.0025}},
}
#: Early-wood colour, late-wood colour, knot colour, joint colour per preset (sRGB).
PALETTES = {
    "default": ("#b58a5a", "#7f5934", "#4a2f18", "#2a1c10"),
    "walnut": ("#6b4a33", "#3f2a1c", "#25170e", "#160e08"),
    "knotty_pine": ("#d9b47a", "#a87436", "#5c3615", "#3a2a18"),
    "weathered_grey": ("#a49c90", "#6f685f", "#4a4540", "#262421"),
    "white_oak_strip": ("#d3b98f", "#a58660", "#5f4529", "#3a2c1c"),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The plank maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    early, late, knot_rgb, joint_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    rows, per_row = p["board_rows"], p["boards_per_row"]
    board_height, board_length = 1.0 / rows, 1.0 / per_row
    rng = tk.Rng(seed, 1)
    offsets = [rng.random() for _ in range(rows)]
    boards = []
    for _ in range(rows * per_row):
        knot = rng.chance(p["knots"])
        boards.append({"pith": rng.uniform(-1.6, 2.6) * board_height, "depth": rng.uniform(0.05, 1.4) * board_height,
                       "incline": rng.uniform(-0.12, 0.12), "start": rng.uniform(0.0, 0.3), "tone": rng.uniform(-1, 1),
                       "knot": (rng.uniform(0.15, 0.85) * board_length, rng.uniform(0.25, 0.75) * board_height,
                                rng.uniform(0.25, 0.5) * board_height) if knot else None})
    warp = tk.fbm(width, height, 3, 4, tk.hash_u32(seed, 2), cells_y=6)
    pores = tk.fbm(width, height, 4, 3, tk.hash_u32(seed, 3), cells_y=96)
    figure = tk.fbm(width, height, 2, 3, tk.hash_u32(seed, 4), cells_y=12)
    speck = tk.white_noise(width, height, tk.hash_u32(seed, 5))
    density = p["ring_density"]
    contrast, variation, weathering = p["ring_contrast"], p["board_variation"], p["weathering"]
    half_gap = p["gap"] * 0.5
    pixel = 1.0 / min(width, height)
    red, green, blue, heights, rough = [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        r = min(int(v * rows), rows - 1)
        t = v - r * board_height
        edge_t = min(t, board_height - t)
        base = y * width
        for x in range(width):
            index = base + x
            position = ((x + 0.5) / width - offsets[r] * board_length) % 1.0
            k = min(int(position / board_length), per_row - 1)
            s = position - k * board_length
            edge_s = min(s, board_length - s)
            board = boards[r * per_row + k]
            lateral = t - board["pith"]
            depth = board["depth"] + board["incline"] * (s + board["start"])
            radius = math.sqrt(lateral * lateral + depth * depth)
            knot_dark = 0.0
            if board["knot"] is not None:
                ks, kt, size = board["knot"]
                ds, dt = (s - ks) / (size * 1.8), (t - kt) / size
                near = ds * ds + dt * dt
                radius += 0.35 * size * math.exp(-near * 1.5)
                knot_dark = math.exp(-near * 9.0)
            rings = radius * density + 0.6 * warp[index] + 0.15 * figure[index]
            phase = rings - math.floor(rings)
            band = tk.smoothstep(0.55, 0.9, phase) * (1.0 - tk.smoothstep(0.9, 1.0, phase))
            lateness = min(1.0, contrast * band + 0.25 * contrast * (pores[index] + 0.5) * band)
            colour = [a + (b - a) * lateness for a, b in zip(early, late)]
            tone = 1.0 + 0.16 * variation * board["tone"] + 0.08 * pores[index] + 0.04 * (speck[index] - 0.5)
            colour = [c * tone for c in colour]
            if knot_dark > 0.0:
                colour = [c + (kc - c) * min(1.0, knot_dark * 1.4) for c, kc in zip(colour, knot_rgb)]
            if weathering > 0.0:
                grey = 0.299 * colour[0] + 0.587 * colour[1] + 0.114 * colour[2]
                colour = [c + (grey * 1.05 - c) * weathering * 0.75 for c in colour]
            inside = min(edge_s, edge_t) - half_gap
            joint = tk.smoothstep(-pixel, pixel, inside)
            bevel = tk.smoothstep(0.0, 0.006, inside)
            colour = [jc + (c - jc) * joint for c, jc in zip(colour, joint_rgb)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            check = weathering * max(0.0, -pores[index] - 0.25) * 1.5 * (1.0 - tk.smoothstep(0.0, 0.08, edge_s))
            surface = 0.78 + 0.04 * board["tone"] * variation - 0.06 * weathering * lateness * -1.0 \
                - 0.03 * weathering * (1.0 - lateness) + 0.015 * pores[index] - 0.3 * check
            heights.append(0.15 + (surface - 0.15) * bevel)
            gloss = p["gloss"] * (1.0 - weathering)
            rough.append(joint * (0.85 - 0.6 * gloss + 0.08 * lateness * (1.0 - gloss) + 0.04 * speck[index])
                         + (1.0 - joint) * 0.95)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.01, roughness=rough,
                     ao_radius=0.012, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
