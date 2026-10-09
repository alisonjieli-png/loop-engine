"""Corroded metal: rust on steel or verdigris on copper, tileable PBR maps from the standard library only.

A warped fractal mask decides where the oxide grows; how far a pixel lies inside a patch picks the layer (thin
bloom at the rim, thick flaking crust in the middle). Pits are small cells sunk into the crust, and drip streaks
run down from each patch: every column is swept downward with an exponential trail, twice around so the trail
wraps. Bare metal keeps a rolled grain and fine scratches and is the only metallic part of the material.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "metal_corrosion"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.03, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.05, 1.0]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "coverage", "type": "float", "default": 0.45, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of the surface under oxide."},
    {"name": "patch_scale", "type": "int", "default": 3, "minimum": 1, "maximum": 12,
     "meaning": "Noise cells across the tile for the corrosion patches: higher values give smaller patches."},
    {"name": "pitting", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Density and depth of pits in the oxide."},
    {"name": "streaks", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Strength of the oxide stains running down from each patch."},
    {"name": "flaking", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Raised, cracked crust in the thick middle of the patches."},
    {"name": "metal_roughness", "type": "float", "default": 0.35, "minimum": 0.05, "maximum": 0.8,
     "meaning": "Roughness of the bare metal."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Steel plate with orange-brown rust patches and light drip stains.", "values": {}},
    "heavy_rust": {"description": "Steel almost covered in thick flaking rust with deep pits.",
                   "values": {"coverage": 0.85, "pitting": 0.85, "flaking": 0.8, "streaks": 0.3,
                              "patch_scale": 4}},
    "verdigris": {"description": "Copper with blue-green patina and brown oxide rims.",
                  "values": {"coverage": 0.5, "pitting": 0.2, "streaks": 0.8, "flaking": 0.15,
                             "metal_roughness": 0.25, "patch_scale": 4}},
    "light_bloom": {"description": "Mostly bare polished steel with small early rust spots.",
                    "values": {"coverage": 0.18, "patch_scale": 8, "pitting": 0.3, "streaks": 0.25,
                               "flaking": 0.0, "metal_roughness": 0.18}},
}
#: Bare metal colour, rim oxide, middle oxide, thick crust, stain colour per preset (sRGB; metal in linear-ish
#: reflectance terms as glTF expects for metals).
PALETTES = {
    "default": ("#8f9296", "#c0682c", "#8a3d1c", "#5a2716", "#7a4022"),
    "heavy_rust": ("#7d8084", "#b85f27", "#7c3518", "#4a2013", "#6d371d"),
    "verdigris": ("#b87a4f", "#4f3324", "#5b9886", "#93c3ad", "#6aa894"),
    "light_bloom": ("#a7aaae", "#c47a3e", "#94471f", "#64301a", "#8a5230"),
}


def _drip(mask: list, width: int, height: int, keep: float) -> list:
    """Each column swept downward with trail = max(mask, trail * keep), twice around so the trail wraps."""
    out = list(mask)
    for x in range(width):
        column = mask[x::width]
        trail = 0.0
        values = [0.0] * height
        for _round in range(2):
            for y in range(height):
                trail = column[y] if column[y] > trail * keep else trail * keep
                values[y] = trail
        out[x::width] = values
    return out


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The corroded metal maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    metal, rim, middle, crust, stain = (tk.hex_rgb(code) for code in PALETTES[preset])
    scale = p["patch_scale"]
    base = tk.fbm(width, height, scale, 6, tk.hash_u32(seed, 1), gain=0.55)
    warp_u = tk.fbm(width, height, 2, 3, tk.hash_u32(seed, 2))
    warp_v = tk.fbm(width, height, 2, 3, tk.hash_u32(seed, 3))
    base = tk.warp(base, width, height, warp_u, warp_v, 0.04)
    threshold = 0.32 - 0.64 * p["coverage"]
    depth = [v - threshold for v in base]
    patch = [tk.smoothstep(0.0, 0.03, d) for d in depth]
    length = 0.02 + 0.2 * p["streaks"]
    keep = math.exp(-1.0 / (length * height)) if p["streaks"] > 0.0 else 0.0
    streak_noise = tk.fbm(width, height, 24, 3, tk.hash_u32(seed, 4), cells_y=2)
    trail = _drip(patch, width, height, keep) if keep else [0.0] * (width * height)
    pits = tk.voronoi(width, height, 22, 22, tk.hash_u32(seed, 5), jitter=1.0, edges=False)["f1"]
    crack = tk.voronoi(width, height, 14, 14, tk.hash_u32(seed, 6), jitter=0.9)["edge"]
    grain = tk.fbm(width, height, 64, 2, tk.hash_u32(seed, 7), cells_y=4)
    speck = tk.white_noise(width, height, tk.hash_u32(seed, 8))
    mottle = tk.fbm(width, height, 12, 4, tk.hash_u32(seed, 10))
    scratches = [0.0] * (width * height)
    rng = tk.Rng(seed, 9)
    for _ in range(int(14 + 30 * (1.0 - p["coverage"]))):
        u, v = rng.random(), rng.random()
        length = rng.uniform(0.05, 0.25)
        angle = rng.uniform(-0.4, 0.4)
        tk.draw_segment(scratches, width, height, u, v, u + length, v + length * angle, 0.0025, rng.uniform(0.4, 1.0))
    pitting, flaking = p["pitting"], p["flaking"]
    red, green, blue, rough, metallic, heights = [], [], [], [], [], []
    for index in range(width * height):
        d = depth[index]
        cover = patch[index]
        thick = tk.smoothstep(0.02, 0.22, d)
        pit = pitting * (1.0 - tk.smoothstep(0.08, 0.2, pits[index])) * thick
        flake = flaking * thick * tk.smoothstep(0.0, 0.08, crack[index])
        stain_amount = max(0.0, trail[index] - cover) * (0.55 + 0.45 * streak_noise[index]) * p["streaks"]
        bare = [c * (0.92 + 0.12 * grain[index] + 0.1 * scratches[index]) for c in metal]
        bare = [c + (s - c) * min(0.7, stain_amount) for c, s in zip(bare, stain)]
        oxide = [a + (b - a) * tk.smoothstep(0.0, 0.08, d) for a, b in zip(rim, middle)]
        oxide = [a + (b - a) * thick for a, b in zip(oxide, crust)]
        oxide = [c * (0.86 + 0.18 * speck[index] + 0.3 * mottle[index] - 0.35 * pit) for c in oxide]
        colour = [b + (o - b) * cover for b, o in zip(bare, oxide)]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        metal_share = (1.0 - cover) * (1.0 - 0.6 * min(1.0, stain_amount))
        metallic.append(metal_share)
        rough.append(metal_share * (p["metal_roughness"] + 0.08 * grain[index] + 0.25 * stain_amount)
                     + (1.0 - metal_share) * (0.82 + 0.15 * speck[index]))
        heights.append(0.4 + 0.1 * cover + 0.16 * flake + 0.08 * thick * speck[index] - 0.25 * pit
                       - 0.03 * scratches[index] + 0.015 * grain[index])
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.03, roughness=rough,
                     metallic=metallic, ao_radius=0.015, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
