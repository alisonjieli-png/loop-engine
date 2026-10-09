"""Chain mail in the 4-in-1 European weave, with alpha gaps: tileable PBR maps (standard library only).

Rings sit on a staggered grid: every row is offset by half a ring, and rows alternate their tilt. Each ring is an
annulus with a round wire profile whose height also rises across the ring along its tilt, and rings are painted
with a z-buffer, so in every overlap the higher half wins: each ring passes over two neighbours and under two, the
look of interlinked mail. The albedo alpha is 1 on wire and 0 in the gaps. Metal throughout, with darker contact
points where rings touch.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "chain_mail"
MAPS = [
    {"name": "albedo", "channels": 4, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.03, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.1, 1.0]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "rings_across", "type": "int", "default": 8, "minimum": 3, "maximum": 32,
     "meaning": "Rings across the tile in each row."},
    {"name": "wire", "type": "float", "default": 0.17, "minimum": 0.08, "maximum": 0.3,
     "meaning": "Wire thickness as a share of the ring spacing."},
    {"name": "ring_size", "type": "float", "default": 0.62, "minimum": 0.5, "maximum": 0.8,
     "meaning": "Ring outer radius as a share of the ring spacing."},
    {"name": "tilt", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How steeply rows tilt (stronger interlocking)."},
    {"name": "tarnish", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Darkening and dulling of the rings."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.0,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Bright steel mail.", "values": {}},
    "blackened": {"description": "Blackened steel mail, matte.", "values": {"tarnish": 0.7}},
    "brass": {"description": "Brass mail with heavier wire.", "values": {"wire": 0.22, "rings_across": 7}},
    "rusty": {"description": "Rusty iron mail with fine rings.",
              "values": {"tarnish": 0.9, "rings_across": 12, "wire": 0.2}},
}
#: Metal colour, tarnish colour (sRGB) and how much of the metallic response the tarnish removes, per preset.
PALETTES = {
    "default": ("#cfd2d6", "#55575a", 0.3),
    "blackened": ("#9a9ca0", "#1f2022", 0.3),
    "brass": ("#d9b663", "#5a4520", 0.3),
    "rusty": ("#a9a8a4", "#7a3d1c", 1.0),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The chain mail maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    metal_hex, tarnish_hex, scale_loss = PALETTES[preset]
    metal, tarnish_rgb = tk.hex_rgb(metal_hex), tk.hex_rgb(tarnish_hex)
    count = width * height
    columns = p["rings_across"]
    rows = 2 * columns
    spacing_u, spacing_v = 1.0 / columns, 1.0 / rows
    outer = p["ring_size"] * spacing_u
    wire = p["wire"] * spacing_u
    middle = outer - wire * 0.5
    level = [0.0] * count
    shade = [0.0] * count
    rng = tk.Rng(seed, 1)
    tilt = p["tilt"]
    for j in range(rows):
        sign = 1.0 if j % 2 == 0 else -1.0
        for i in range(columns):
            cu = (i + 0.5 * (j % 2) + 0.5) * spacing_u
            cv = (j + 0.5) * spacing_v
            wobble = rng.uniform(-0.04, 0.04)
            for index, s, t in tk.ellipse_pixels(width, height, cu, cv, outer, outer):
                radius = math.sqrt(s * s + t * t) * outer
                offset = abs(radius - middle) / (wire * 0.5)
                if offset >= 1.0:
                    continue
                section = math.sqrt(1.0 - offset * offset)
                lean = sign * tilt * 0.45 * s + wobble
                surface = 0.5 + 0.35 * section + lean
                if surface > level[index]:
                    level[index] = surface
                    shade[index] = section
    grime = tk.fbm(width, height, 6, 3, tk.hash_u32(seed, 2))
    tarnish = p["tarnish"]
    red, green, blue, alpha, heights, rough, metallic = [], [], [], [], [], [], []
    low = min(v for v in level if v > 0.0) if any(level) else 0.0
    for index in range(count):
        solid = 1.0 if level[index] > 0.0 else 0.0
        dull = tarnish * (0.6 + 0.4 * tk.smoothstep(-0.3, 0.3, grime[index]))
        tone = 0.55 + 0.45 * shade[index]
        colour = [(c + (k - c) * dull) * tone for c, k in zip(metal, tarnish_rgb)]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        alpha.append(solid)
        heights.append((level[index] - low * 0.8) if solid else 0.0)
        metallic.append(1.0 - 0.6 * dull * scale_loss)
        rough.append(0.25 + 0.5 * dull + 0.1 * (1.0 - shade[index]))
    peak = max(heights) or 1.0
    heights = [h / peak for h in heights]
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, alpha=alpha, heights=heights, depth=0.15 / columns,
                     roughness=rough, metallic=metallic, ao_radius=0.25 / columns, ao_strength=1.0,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
