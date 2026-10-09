"""Camouflage patterns printed on twill fabric: woodland, digital, tiger stripe, desert and splinter (standard library).

Every pattern is a stack of colour layers over a base colour; a pixel takes the colour of the topmost layer whose
field exceeds that layer's threshold, and thresholds come from quantiles of the field, so each layer covers a set
share of the cloth whatever the seed. The fields differ by pattern: woodland uses domain-warped fractal noise for
blobs and a ridged field for thin dark branches; digital samples the same kind of fields once per square cell of a
grid and perturbs cells near the edges, which gives stepped, pixelated blobs; tiger stripe stretches the noise
lattice along the tile width; desert adds small round spots from a Worley diagram; splinter colours Worley cells
whole, which leaves straight-edged shards, and overlays short vertical rain dashes.

The cloth is a twill-like weave: diagonal ridges at a whole number of threads across the tile shape the height,
normals and a slight darkening in the grooves, and the printed layers sit a hair above the base.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "camouflage_patterns"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.03, 0.85]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.5, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "pattern", "type": "int", "default": 0, "minimum": 0, "maximum": 4,
     "meaning": "0 woodland blobs and branches, 1 digital pixels, 2 tiger stripes, 3 desert with spots, 4 splinter "
                "with rain dashes."},
    {"name": "blobs", "type": "int", "default": 4, "minimum": 2, "maximum": 12,
     "meaning": "Pattern features across the tile; larger values give smaller shapes."},
    {"name": "pixels_across", "type": "int", "default": 64, "minimum": 16, "maximum": 160,
     "meaning": "Square cells across the tile for the digital pattern."},
    {"name": "ragged", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Raggedness of the shape edges (domain warping)."},
    {"name": "threads", "type": "int", "default": 96, "minimum": 24, "maximum": 240,
     "meaning": "Twill threads across the tile."},
    {"name": "weave", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Strength of the twill texture in colour and relief."},
    {"name": "fading", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Washed-out wear that pales the print in patches."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Woodland: khaki ground with brown and green blobs and black branches.", "values": {}},
    "digital_pixels": {"description": "Digital woodland: the same layering stepped into small square pixels.",
                       "values": {"pattern": 1, "blobs": 5, "pixels_across": 72}},
    "tiger_stripe": {"description": "Tiger stripe: long ragged horizontal stripes over a pale green ground.",
                     "values": {"pattern": 2, "blobs": 3, "ragged": 0.7}},
    "desert_spots": {"description": "Three-colour desert with soft blobs and small dark and white rock spots.",
                     "values": {"pattern": 3, "blobs": 3, "ragged": 0.35}},
    "splinter_rain": {"description": "Splinter: straight-edged shards in three colours under short rain dashes.",
                      "values": {"pattern": 4, "blobs": 6, "ragged": 0.2, "threads": 120}},
}
#: Per preset: base colour then layer colours, bottom to top (sRGB), and each layer's share of the cloth.
PALETTES = {
    "default": (["#8c8158", "#5f4a30", "#3e5232", "#1e1e1a"], [0.45, 0.4, 0.14]),
    "digital_pixels": (["#8a8a62", "#5e5a3c", "#3c4c30", "#22241e"], [0.45, 0.4, 0.15]),
    "tiger_stripe": (["#7d8a5a", "#465436", "#1f241a"], [0.45, 0.28]),
    "desert_spots": (["#c8b28a", "#9a7a56", "#6e5a42"], [0.42, 0.25]),
    "splinter_rain": (["#a39a78", "#5c6a44", "#6a4e36"], [0.35, 0.3]),
}
RAIN_COLOUR = "#3a4a2c"
SPOT_COLOURS = ("#2e2620", "#e4dccb")


def _threshold(field: list, share: float) -> float:
    """The value above which ``share`` of the field lies (from every fifth sample)."""
    sample = sorted(field[::5])
    return sample[min(len(sample) - 1, max(0, int((1.0 - share) * len(sample))))]


def _layer_fields(pattern: int, width: int, height: int, seed: int, blobs: int, ragged: float, layers: int) -> list:
    """One continuous field per colour layer; larger values are more likely to be painted."""
    offset_u = tk.fbm(width, height, blobs * 2, 3, tk.hash_u32(seed, 11))
    offset_v = tk.fbm(width, height, blobs * 2, 3, tk.hash_u32(seed, 12))
    fields = []
    for layer in range(layers):
        salt = tk.hash_u32(seed, 20 + layer)
        if pattern == 2:
            field = tk.fbm(width, height, max(1, blobs // 2), 5, salt, cells_y=blobs * 4)
        elif pattern == 0 and layer == layers - 1:
            field = tk.ridged(width, height, blobs + 1, 4, salt)
        else:
            field = tk.fbm(width, height, blobs + layer, 5, salt, gain=0.55)
        fields.append(tk.warp(field, width, height, offset_u, offset_v, 0.07 * ragged))
    return fields


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The camouflage maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    colours, shares = PALETTES[preset]
    colours = [tk.hex_rgb(code) for code in colours]
    pattern, blobs = p["pattern"], p["blobs"]
    count = width * height
    layer_of = [0] * count
    if pattern == 4:
        cells = tk.voronoi(width, height, blobs, blobs, tk.hash_u32(seed, 30), jitter=1.0, edges=False)["cell"]
        picks = [tk.hash_float(seed, 31, cell) for cell in range(blobs * blobs)]
        for index in range(count):
            pick = picks[cells[index]]
            layer_of[index] = 2 if pick < shares[1] else 1 if pick < shares[1] + shares[0] else 0
    else:
        fields = _layer_fields(pattern, width, height, seed, blobs, p["ragged"], len(shares))
        limits = [_threshold(field, share) for field, share in zip(fields, shares)]
        if pattern == 1:
            grid = p["pixels_across"]
            rows = max(1, round(grid * height / width))
            for layer, field in enumerate(fields):
                table = {}
                for j in range(rows):
                    for i in range(grid):
                        value = tk.sample(field, width, height, (i + 0.5) / grid, (j + 0.5) / rows)
                        table[j * grid + i] = value + 0.06 * (tk.hash_float(seed, 40 + layer, i, j) - 0.5)
                for y in range(height):
                    j = min(rows - 1, int((y + 0.5) / height * rows))
                    for x in range(width):
                        i = min(grid - 1, int((x + 0.5) / width * grid))
                        if table[j * grid + i] > limits[layer]:
                            layer_of[y * width + x] = layer + 1
        else:
            for layer, field in enumerate(fields):
                limit = limits[layer]
                for index in range(count):
                    if field[index] > limit:
                        layer_of[index] = layer + 1
    spots = [0] * count
    if pattern == 3:
        cells = tk.voronoi(width, height, blobs * 6, blobs * 6, tk.hash_u32(seed, 50), jitter=0.8, edges=False)
        for index in range(count):
            cell = cells["cell"][index]
            pick = tk.hash_float(seed, 51, cell)
            if pick < 0.3 and cells["f1"][index] < 0.12 + 0.08 * tk.hash_float(seed, 52, cell):
                spots[index] = 1 if pick < 0.18 else 2
    threads = p["threads"]
    weave, fading = p["weave"], p["fading"]
    wear = tk.fbm(width, height, 5, 4, tk.hash_u32(seed, 60))
    fibre = tk.white_noise(width, height, tk.hash_u32(seed, 61))
    rain = tk.hash_u32(seed, 70)
    red, green, blue, heights, rough = [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        for x in range(width):
            index = y * width + x
            u = (x + 0.5) / width
            layer = layer_of[index]
            colour = colours[layer]
            if spots[index]:
                colour = tk.hex_rgb(SPOT_COLOURS[spots[index] - 1])
            if pattern == 4:
                column = int(u * 140.0)
                dash = int(v * 36.0 + 7.0 * tk.hash_float(rain, column)) % 36
                if (u * 140.0) % 1.0 < 0.32 and tk.hash_float(rain, column, dash) < 0.35:
                    colour = tk.hex_rgb(RAIN_COLOUR)
            ridge = 0.5 + 0.5 * math.sin(math.tau * threads * (u + v))
            cross = 0.5 + 0.5 * math.sin(math.tau * threads * (u - v))
            cloth = 0.7 * ridge + 0.3 * cross
            pale = fading * tk.smoothstep(0.1, 0.6, wear[index])
            shade = (1.0 - 0.18 * weave * (1.0 - cloth)) * (0.96 + 0.08 * fibre[index])
            colour = [(c + (0.78 - c) * 0.45 * pale) * shade for c in colour]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            heights.append(0.45 + 0.35 * weave * cloth + 0.03 * (layer > 0) + 0.04 * fibre[index])
            rough.append(0.82 + 0.08 * (1.0 - cloth) + 0.06 * pale - 0.04 * (layer > 0))
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.15 / threads, roughness=rough,
                     ao_radius=0.004, ao_strength=0.6, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
