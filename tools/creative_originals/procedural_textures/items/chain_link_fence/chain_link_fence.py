"""Chain-link fence mesh with alpha openings: tileable PBR maps from the standard library only.

Two families of wires run along the diagonals, u + v and u - v, a whole number of meshes across the tile, which
makes the diamond openings and keeps the mesh periodic. Distances to the nearest wire of each family give round
wire profiles. At every crossing one family passes over the other, alternating like a weave: the upper wire rises
and the lower one dips as they approach the crossing, which reads as the twisted knuckles of chain link. Albedo
alpha is 1 on wire and 0 in the openings, anti-aliased over a pixel.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "chain_link_fence"
MAPS = [
    {"name": "albedo", "channels": 4, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.03, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.15, 1.0]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "meshes_across", "type": "int", "default": 6, "minimum": 2, "maximum": 24,
     "meaning": "Diamond openings across the tile."},
    {"name": "wire", "type": "float", "default": 0.06, "minimum": 0.02, "maximum": 0.2,
     "meaning": "Wire diameter as a share of the mesh spacing."},
    {"name": "knuckle", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How far wires rise and dip at the crossings."},
    {"name": "coating", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Vinyl coating (0 bare galvanized metal, 1 coated)."},
    {"name": "rust", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Rust along the wires."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.0,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Galvanized steel chain link.", "values": {}},
    "green_vinyl": {"description": "Green vinyl-coated chain link with thicker wire.",
                    "values": {"coating": 1.0, "wire": 0.09}},
    "rusty": {"description": "Old rusty chain link, fine mesh.",
              "values": {"rust": 0.85, "meshes_across": 9}},
    "black_heavy": {"description": "Black coated heavy-gauge mesh with large openings.",
                    "values": {"coating": 1.0, "wire": 0.12, "meshes_across": 4, "knuckle": 0.8}},
}
#: Metal, coating and rust colours per preset (sRGB).
PALETTES = {
    "default": ("#b9bdc1", "#2f6b3a", "#7f3d1b"),
    "green_vinyl": ("#b9bdc1", "#2c6a37", "#7f3d1b"),
    "rusty": ("#a3a7aa", "#2f6b3a", "#7a3a19"),
    "black_heavy": ("#b9bdc1", "#1f2123", "#7f3d1b"),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The chain-link maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    metal, coat_rgb, rust_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    n = p["meshes_across"]
    radius = p["wire"] * 0.5 / n
    pixel = 1.0 / min(width, height)
    rust_field = tk.fbm(width, height, 12, 3, tk.hash_u32(seed, 1))
    grain = tk.fbm(width, height, 48, 2, tk.hash_u32(seed, 2))
    root = math.sqrt(2.0)
    knuckle, coating, rust = p["knuckle"], p["coating"], p["rust"]
    red, green, blue, alpha, heights, rough, metallic = [], [], [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        base = y * width
        for x in range(width):
            index = base + x
            u = (x + 0.5) / width
            a = (u + v) * n
            b = (u - v) * n
            ka, kb = math.floor(a + 0.5), math.floor(b + 0.5)
            da = abs(a - ka) / (n * root)
            db = abs(b - kb) / (n * root)
            on_top_a = (ka + kb) % 2 == 0
            near_crossing_a = 1.0 - tk.smoothstep(0.0, 0.35 / (n * root), db)
            near_crossing_b = 1.0 - tk.smoothstep(0.0, 0.35 / (n * root), da)
            best, best_section = -1.0, 0.0
            for distance, top, near in ((da, on_top_a, near_crossing_a), (db, not on_top_a, near_crossing_b)):
                if distance < radius + pixel:
                    section = math.sqrt(max(0.0, 1.0 - min(1.0, distance / radius) ** 2))
                    surface = 0.45 + 0.3 * section + knuckle * 0.25 * near * (1.0 if top else -1.0)
                    if surface > best:
                        best, best_section = surface, section
            solid = 0.0 if best < 0.0 else tk.smoothstep(-pixel, pixel, radius - min(da, db))
            rusty = rust * tk.smoothstep(-0.2, 0.3, rust_field[index])
            tone = 0.6 + 0.4 * best_section
            colour = [c + (k - c) * coating for c, k in zip(metal, coat_rgb)]
            colour = [(c + (r - c) * rusty) * tone * (0.95 + 0.08 * grain[index]) for c, r in zip(colour, rust_rgb)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            alpha.append(solid)
            heights.append(max(best, 0.0) * solid)
            metal_share = (1.0 - coating) * (1.0 - rusty)
            metallic.append(metal_share)
            rough.append(metal_share * 0.4 + (1.0 - metal_share) * (0.55 + 0.35 * rusty) + 0.05 * grain[index])
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, alpha=alpha, heights=heights, depth=0.12 / n,
                     roughness=rough, metallic=metallic, ao_radius=0.2 / n, ao_strength=0.8,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
