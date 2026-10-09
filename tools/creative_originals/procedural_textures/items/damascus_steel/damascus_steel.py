"""Damascus (pattern-welded) steel: etched layers in random, ladder, raindrop or chevron patterns (standard library).

A billet of alternating bright and dark steel is forged, cut and ground; the blade face shows where the ground plane
cuts the distorted layer stack, so the visible bands are contour lines of a layer phase. Here the phase is
``layers * v + distortion * D(u, v)``: a whole number of layer pairs down the tile plus a periodic displacement D,
so the pattern repeats. D is a domain-warped fractal for the random pattern (contours fold into loops and eyes),
narrow grooves across the billet for the ladder pattern (bands bend into tongues), smooth dimples on a staggered
grid for the raindrop pattern (concentric rings), and a triangle wave for the chevron pattern; a share of the
random displacement roughens every pattern. The layer kind at a pixel comes from the cosine of the phase against a
slowly varying threshold, so layer thickness varies. Where the bands get finer than about two pixels (from the
analytic phase gradient) the pixel fades to the local share of bright layer instead, so fine layers never alias
into moire. Etching darkens and lowers the dark layers and roughens them; grinding leaves faint lines along the
blade and hand finishing a gentle waviness. The whole surface is metal.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "damascus_steel"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.08, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.08, 0.9]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "pattern", "type": "int", "default": 0, "minimum": 0, "maximum": 3,
     "meaning": "Pattern: 0 random, 1 ladder, 2 raindrop, 3 chevron."},
    {"name": "layers", "type": "int", "default": 24, "minimum": 4, "maximum": 160,
     "meaning": "Layer pairs down the tile (bright and dark layer together)."},
    {"name": "distortion", "type": "float", "default": 4.0, "minimum": 0.0, "maximum": 16.0,
     "meaning": "How far the forging displaces the layers, in layer pairs."},
    {"name": "features", "type": "int", "default": 4, "minimum": 1, "maximum": 16,
     "meaning": "Ladder rungs, raindrop dimples or chevrons across the tile."},
    {"name": "randomness", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of random folding added to the ladder, raindrop and chevron patterns."},
    {"name": "thickness_variation", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How much the bright layers thicken and thin across the blade."},
    {"name": "etch", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Etch depth: contrast and relief between the layer kinds."},
    {"name": "grind_lines", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Fine grinding lines along the blade (across the tile)."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.2,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Random-pattern Damascus with folded contours, medium etch.", "values": {}},
    "ladder": {"description": "Ladder pattern: regular rungs where grooves were cut across the billet.",
               "values": {"pattern": 1, "features": 4, "distortion": 3.0, "layers": 22, "randomness": 0.25}},
    "raindrop": {"description": "Raindrop pattern: concentric rings around drilled dimples.",
                 "values": {"pattern": 2, "features": 4, "distortion": 5.0, "layers": 26, "randomness": 0.2}},
    "chevron": {"description": "Chevron pattern from a restacked billet, light satin etch.",
                "values": {"pattern": 3, "features": 3, "distortion": 5.0, "layers": 14, "etch": 0.55,
                           "randomness": 0.15, "grind_lines": 0.5}},
    "coffee_etch": {"description": "Deep coffee etch: near-black layers and bright nickel lines, fine stack.",
                    "values": {"etch": 1.0, "layers": 48, "distortion": 8.0, "thickness_variation": 0.6,
                               "grind_lines": 0.15}},
}
#: Bright layer, dark etched layer and oxide tint per preset (sRGB), and how much the etch removes metallic response.
PALETTES = {
    "default": ("#d2d4d6", "#4b4e52", "#3a3a3c", 0.15),
    "ladder": ("#d6d8da", "#53565a", "#3d3d40", 0.15),
    "raindrop": ("#cfd2d4", "#484b4f", "#38383b", 0.15),
    "chevron": ("#dcdee0", "#6a6d71", "#505052", 0.1),
    "coffee_etch": ("#c3c4c4", "#1f1e1d", "#17150f", 0.45),
}


def _triangle(t: float) -> float:
    """Periodic triangle wave of period 1: 0 at whole numbers, 1 at halves."""
    f = t - math.floor(t)
    return 1.0 - abs(2.0 * f - 1.0)


def _displacement(pattern: int, u: float, v: float, features: int, dimples: list, radius: float) -> tuple:
    """(D, dD/du, dD/dv) of the pattern-specific displacement at (u, v); D is periodic and about 0 to 1."""
    if pattern == 1:
        # Rungs: narrow smooth grooves across the billet at whole-number positions along u.
        t = u * features
        f = t - math.floor(t) - 0.5
        width = 0.11
        value = math.exp(-(f / width) ** 2)
        return value, value * (-2.0 * f / (width * width)) * features, 0.0
    if pattern == 2:
        # Dimples: smooth Gaussian bumps summed over every dimple within reach (wrapped on the torus).
        total, total_u, total_v = 0.0, 0.0, 0.0
        for cu, cv in dimples:
            du, dv = tk.wrap_delta(u - cu), tk.wrap_delta(v - cv)
            r2 = (du * du + dv * dv) / (radius * radius)
            if r2 < 12.0:
                value = math.exp(-r2)
                scale = -2.0 * value / (radius * radius)
                total, total_u, total_v = total + value, total_u + scale * du, total_v + scale * dv
        return total, total_u, total_v
    if pattern == 3:
        t = u * features
        f = t - math.floor(t)
        slope = 2.0 * features if f < 0.5 else -2.0 * features
        return _triangle(t), slope, 0.0
    return 0.0, 0.0, 0.0


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The Damascus steel maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    bright_hex, dark_hex, oxide_hex, metal_loss = PALETTES[preset]
    bright, dark, oxide = tk.hex_rgb(bright_hex), tk.hex_rgb(dark_hex), tk.hex_rgb(oxide_hex)
    pattern, layers, features = p["pattern"], p["layers"], p["features"]
    amount = p["distortion"]
    random_share = 1.0 if pattern == 0 else p["randomness"]
    pattern_share = 0.0 if pattern == 0 else 1.0
    # A domain-warped fractal for the random folding, with its gradient by wrap-around differences.
    warp_u = tk.fbm(width, height, 3, 3, tk.hash_u32(seed, 1))
    warp_v = tk.fbm(width, height, 3, 3, tk.hash_u32(seed, 2))
    folding = tk.fbm(width, height, 2, 5, tk.hash_u32(seed, 3), gain=0.55)
    folding = tk.warp(folding, width, height, warp_u, warp_v, 0.18)
    low, high = min(folding), max(folding)
    span = max(high - low, 1e-9)
    folding = [(value - low) / span for value in folding]
    threshold = tk.fbm(width, height, 4, 3, tk.hash_u32(seed, 4))
    grind = tk.fbm(width, height, 2, 4, tk.hash_u32(seed, 5), cells_y=96) if p["grind_lines"] > 0.0 else None
    speckle = tk.white_noise(width, height, tk.hash_u32(seed, 6))
    waviness = tk.fbm(width, height, 2, 2, tk.hash_u32(seed, 8))
    rng = tk.Rng(seed, 7)
    dimples = []
    if pattern == 2:
        rows = max(2, 2 * round(features * 0.5 + 0.25))
        for j in range(rows):
            for i in range(features):
                dimples.append(((i + 0.5 * (j % 2) + 0.12 * rng.uniform(-1.0, 1.0)) / features,
                                (j + 0.5 + 0.12 * rng.uniform(-1.0, 1.0)) / rows))
    radius = 0.28 / features
    variation = p["thickness_variation"]
    etch = p["etch"]
    lines = p["grind_lines"]
    tau = 2.0 * math.pi
    red, green, blue, heights, rough, metallic = [], [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        base = y * width
        up = ((y - 1) % height) * width
        down = ((y + 1) % height) * width
        for x in range(width):
            index = base + x
            u = (x + 0.5) / width
            value, dd_u, dd_v = _displacement(pattern, u, v, features, dimples, radius)
            fold = folding[index]
            fold_u = (folding[base + (x + 1) % width] - folding[base + (x - 1) % width]) * width * 0.5
            fold_v = (folding[down + x] - folding[up + x]) * height * 0.5
            phase = layers * v + amount * (pattern_share * value + random_share * fold)
            grad_u = amount * (pattern_share * dd_u + random_share * fold_u)
            grad_v = layers + amount * (pattern_share * dd_v + random_share * fold_v)
            # Cycles per pixel of the band pattern; contrast fades before the bands reach the pixel size.
            cycles = max(abs(grad_u) / width, abs(grad_v) / height)
            contrast = 1.0 - tk.smoothstep(0.22, 0.45, cycles)
            wave = 0.5 + 0.5 * math.cos(tau * phase)
            edge = 0.5 + 0.3 * variation * threshold[index]
            soft = 0.06 + 1.2 * cycles
            layer = tk.smoothstep(edge - soft, edge + soft, wave)
            # The share of a cosine period above the threshold: what an unresolved stack averages to.
            share = math.acos(max(-1.0, min(1.0, 2.0 * edge - 1.0))) / math.pi
            layer = share + (layer - share) * contrast
            darkness = (1.0 - layer) * etch
            colour = [b + (d - b) * darkness for b, d in zip(bright, dark)]
            grain = 0.0
            if grind is not None:
                grain = lines * grind[index]
                colour = [c * (1.0 + 0.06 * grain) for c in colour]
            colour = [c + (o - c) * 0.15 * darkness * speckle[index] for c, o in zip(colour, oxide)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            heights.append(0.5 + 0.35 * etch * (layer - 0.5) + 0.06 * grain + 0.05 * waviness[index])
            rough.append(0.16 + 0.42 * darkness + 0.05 * abs(grain) + 0.03 * speckle[index])
            metallic.append(1.0 - metal_loss * darkness)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.012, roughness=rough,
                     metallic=metallic, ao_radius=0.006, ao_strength=0.6, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
