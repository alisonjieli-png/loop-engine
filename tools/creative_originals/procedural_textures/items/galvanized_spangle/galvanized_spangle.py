"""Galvanized steel spangle: zinc crystals with feathered dendrites, tileable PBR maps (standard library only).

Hot-dip zinc freezes into large flat crystals (spangles). Each crystal is a cell of a jittered Voronoi diagram with
its own orientation, which changes how much light it sends back: here each cell takes its own brightness and
roughness. Inside a crystal, dendrites grow from the nucleus: stripes along the crystal's own axis plus a herringbone
of side branches, computed in coordinates relative to the nucleus (wrapped on the torus, so crystals crossing the
tile edge stay continuous). Weathering adds dull white zinc corrosion, the only non-metal part.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "galvanized_spangle"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.3, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.1, 1.0]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "crystals_across", "type": "int", "default": 5, "minimum": 2, "maximum": 24,
     "meaning": "Spangle crystals across the tile."},
    {"name": "contrast", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Brightness difference between crystals."},
    {"name": "dendrites", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Visibility of the feathered dendrite pattern inside crystals."},
    {"name": "white_rust", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Dull white zinc corrosion."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.0,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Fresh galvanized sheet with large bright spangles.", "values": {}},
    "minimized": {"description": "Minimized spangle: small, low-contrast crystals.",
                  "values": {"crystals_across": 16, "contrast": 0.25, "dendrites": 0.2}},
    "weathered": {"description": "Old galvanized steel, dull with white rust.",
                  "values": {"white_rust": 0.7, "contrast": 0.35}},
    "bold_spangle": {"description": "Very large, high-contrast crystals with strong feathering.",
                     "values": {"crystals_across": 3, "contrast": 0.9, "dendrites": 0.9}},
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The galvanized maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    cells = p["crystals_across"]
    points = tk.cell_points(cells, cells, tk.hash_u32(seed, 1), 0.9)
    crystals = tk.voronoi(width, height, cells, cells, points=points)
    rng = tk.Rng(seed, 2)
    traits = [(rng.uniform(-1.0, 1.0), rng.uniform(0.0, math.pi), rng.random()) for _ in range(cells * cells)]
    corrosion = tk.fbm(width, height, 6, 4, tk.hash_u32(seed, 3))
    fine = tk.fbm(width, height, 60, 2, tk.hash_u32(seed, 4))
    contrast, dendrites, white = p["contrast"], p["dendrites"], p["white_rust"]
    red, green, blue, heights, rough, metallic = [], [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        base = y * width
        for x in range(width):
            index = base + x
            u = (x + 0.5) / width
            cell = crystals["cell"][index]
            tone, angle, roughness_pick = traits[cell]
            du = tk.wrap_delta(u - points[0][cell] / cells)
            dv = tk.wrap_delta(v - points[1][cell] / cells)
            along = (du * math.cos(angle) + dv * math.sin(angle)) * cells
            across = (-du * math.sin(angle) + dv * math.cos(angle)) * cells
            spine = 0.5 + 0.5 * math.cos(math.tau * 9.0 * across)
            branches = 0.5 + 0.5 * math.cos(math.tau * 7.0 * (along + 0.6 * abs(across)))
            feather = dendrites * (0.6 * spine * branches + 0.4 * branches)
            border = 1.0 - tk.smoothstep(0.0, 0.03, crystals["edge"][index])
            shade = 0.82 + 0.14 * contrast * tone + 0.06 * feather + 0.03 * fine[index] - 0.08 * border
            grey = [0.78 * shade, 0.8 * shade, 0.82 * shade]
            rusted = white * tk.smoothstep(0.05 - 0.4 * white, 0.3, corrosion[index])
            colour = [g + (0.86 - g) * rusted for g in grey]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            heights.append(0.5 + 0.03 * feather - 0.04 * border + 0.06 * rusted * (fine[index] + 0.5))
            metallic.append(1.0 - rusted)
            rough.append((1.0 - rusted) * (0.22 + 0.3 * contrast * roughness_pick + 0.06 * feather)
                         + rusted * 0.9)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.004, roughness=rough,
                     metallic=metallic, ao_radius=0.01, ao_strength=0.4, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
