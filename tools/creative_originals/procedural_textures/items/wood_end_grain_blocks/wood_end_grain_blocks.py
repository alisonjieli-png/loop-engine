"""End-grain wood blocks (butcher block): tileable PBR maps from the standard library only.

The tile is a grid of square blocks, every other row offset by ``stagger``. Each block is a cross-section of a
small log: growth rings are circles around a pith point that may lie inside the block or beyond its edge (then only
arcs show), warped by noise. Medullary rays are thin radial streaks, and a few radial checks crack outward from the
pith. Glue lines separate the blocks; each block has its own tone and pith from a hash of its index.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "wood_end_grain_blocks"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.88]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.2, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "blocks_across", "type": "int", "default": 4, "minimum": 1, "maximum": 12,
     "meaning": "Blocks across the tile (rows down the tile match, so blocks stay square)."},
    {"name": "stagger", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 0.5,
     "meaning": "Offset of every other row in block widths (alternation repeats cleanly with an even block count)."},
    {"name": "ring_density", "type": "float", "default": 45.0, "minimum": 10.0, "maximum": 120.0,
     "meaning": "Growth rings per texture unit of radius."},
    {"name": "ring_contrast", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Darkness of the late-wood rings."},
    {"name": "rays", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Visibility of the radial medullary rays."},
    {"name": "checks", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Radial drying cracks from the pith."},
    {"name": "glue_line", "type": "float", "default": 0.003, "minimum": 0.0005, "maximum": 0.012,
     "meaning": "Width of the glue joints in texture units."},
    {"name": "block_variation", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spread of tone between blocks."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Oiled maple end grain in a straight grid.", "values": {}},
    "walnut_staggered": {"description": "Dark walnut blocks with staggered rows and subtle rings.",
                         "values": {"stagger": 0.5, "ring_contrast": 0.4, "ring_density": 55.0, "checks": 0.15}},
    "mixed_hardwood": {"description": "Maple, cherry and walnut blocks mixed, oiled.",
                       "values": {"blocks_across": 6, "block_variation": 1.0, "stagger": 0.25}},
    "rough_pine": {"description": "Weathered pine log ends with wide rings and deep checks.",
                   "values": {"blocks_across": 2, "ring_density": 22.0, "ring_contrast": 0.8, "checks": 0.9,
                              "rays": 0.15, "glue_line": 0.008}},
}
#: Species (early wood, late wood) per preset and the glue colour (sRGB); a block picks one species at random,
#: so a preset with several species mixes them (maple, cherry and walnut in mixed_hardwood).
MAPLE, CHERRY, WALNUT = ("#cfa878", "#9c7146"), ("#a8613f", "#7a3f26"), ("#6e4c34", "#45301f")
PALETTES = {
    "default": ([MAPLE], "#3d2a18"),
    "walnut_staggered": ([WALNUT], "#1a120b"),
    "mixed_hardwood": ([MAPLE, CHERRY, WALNUT], "#2b1d11"),
    "rough_pine": ([("#c8a46c", "#8a5c2c")], "#2a1d10"),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The end-grain maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    species_choices, glue_hex = PALETTES[preset]
    glue = tk.hex_rgb(glue_hex)
    blocks = p["blocks_across"]
    size = 1.0 / blocks
    rng = tk.Rng(seed, 1)
    traits = []
    for _ in range(blocks * blocks):
        species = species_choices[rng.integer(0, len(species_choices) - 1)] if len(species_choices) > 1 \
            else species_choices[0]
        angle_count = rng.integer(2, 4)
        traits.append({"pith": (rng.uniform(-0.6, 1.6) * size, rng.uniform(-0.6, 1.6) * size),
                       "tone": rng.uniform(-1.0, 1.0), "early": tk.hex_rgb(species[0]),
                       "late": tk.hex_rgb(species[1]),
                       "checks": [rng.uniform(0.0, math.tau) for _ in range(angle_count)],
                       "reach": rng.uniform(0.35, 0.9) * size})
    warp = tk.fbm(width, height, blocks * 3, 4, tk.hash_u32(seed, 2))
    fibre = tk.white_noise(width, height, tk.hash_u32(seed, 3))
    mottle = tk.fbm(width, height, blocks * 2, 3, tk.hash_u32(seed, 4))
    density, contrast = p["ring_density"], p["ring_contrast"]
    rays, checks, variation = p["rays"], p["checks"], p["block_variation"]
    half_glue = p["glue_line"] * 0.5
    pixel = 1.0 / min(width, height)
    red, green, blue, heights, rough = [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        r = min(int(v * blocks), blocks - 1)
        local_v = v - r * size
        shift = (r % 2) * p["stagger"]
        base = y * width
        for x in range(width):
            index = base + x
            position = ((x + 0.5) / width / size - shift) % blocks
            c = min(int(position), blocks - 1)
            local_u = (position - c) * size
            trait = traits[r * blocks + c]
            du, dv = local_u - trait["pith"][0], local_v - trait["pith"][1]
            radius = math.sqrt(du * du + dv * dv)
            angle = math.atan2(dv, du)
            rings = radius * density + 0.8 * warp[index]
            phase = rings - math.floor(rings)
            band = tk.smoothstep(0.6, 0.92, phase) * (1.0 - tk.smoothstep(0.92, 1.0, phase))
            ray = rays * tk.smoothstep(0.93, 1.0, math.cos(angle * 90.0 + 6.0 * warp[index])) \
                * tk.smoothstep(0.0, 0.04, radius)
            crack = 0.0
            if checks > 0.0 and radius < trait["reach"]:
                for theta in trait["checks"]:
                    gap = abs(math.atan2(math.sin(angle - theta), math.cos(angle - theta))) * radius
                    width_here = checks * 0.004 * (1.0 - radius / trait["reach"])
                    if gap < width_here:
                        crack = max(crack, 1.0 - gap / width_here)
            colour = [a + (b - a) * contrast * band for a, b in zip(trait["early"], trait["late"])]
            tone = 1.0 + 0.14 * variation * trait["tone"] + 0.06 * mottle[index] + 0.06 * (fibre[index] - 0.5) \
                + 0.18 * ray
            colour = [k * tone * (1.0 - 0.75 * crack) for k in colour]
            edge = min(local_u, size - local_u, local_v, size - local_v) - half_glue
            joint = tk.smoothstep(-pixel, pixel, edge)
            colour = [g + (k - g) * joint for k, g in zip(colour, glue)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            surface = 0.8 - 0.03 * band - 0.012 * fibre[index] - 0.45 * crack + 0.02 * trait["tone"] * variation
            heights.append(0.4 + (surface - 0.4) * joint)
            rough.append(0.62 + 0.12 * band + 0.08 * fibre[index] + 0.2 * crack + (1.0 - joint) * 0.2)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.006, roughness=rough,
                     ao_radius=0.01, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
