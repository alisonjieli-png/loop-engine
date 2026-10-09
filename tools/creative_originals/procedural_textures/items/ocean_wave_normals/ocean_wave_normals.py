"""Ocean wave normals: a tileable sea surface from directional waves with integer wave vectors (standard library).

The surface is a sum of sine waves whose wave vectors are whole numbers of cycles across the tile, so it repeats
exactly. Components are drawn from a directional spectrum: a log-normal band around the peak wavelength times a
cos^s spreading around the wind direction, picked by weighted sampling without replacement (Gumbel top-k) so a seed
chooses which waves exist. Amplitudes fall with the wavenumber like a wind sea. Each wave is evaluated separably
(sin(2 pi (a u + b v) + phase) from per-column and per-row tables), so the cost is one multiply-add per wave and
pixel.

Choppiness moves the surface sideways toward the crests, as Gerstner waves do: the height is resampled at
p - lambda D(p), where D is the horizontal displacement of the same waves, and lambda is chosen from the steepest
compression so the crests sharpen without folding. Where the horizontal compression (the Jacobian of the
displacement) drops, the crest is breaking and foam forms in the albedo and roughness.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "ocean_wave_normals"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.01, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.02, 0.9]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "peak_waves", "type": "int", "default": 4, "minimum": 1, "maximum": 16,
     "meaning": "Cycles of the dominant wavelength across the tile."},
    {"name": "components", "type": "int", "default": 48, "minimum": 8, "maximum": 96,
     "meaning": "Number of sine waves summed."},
    {"name": "wind_angle", "type": "float", "default": 0.1, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Direction the waves travel, in turns from the +U axis."},
    {"name": "spread", "type": "float", "default": 0.45, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Directional spreading: 0 long parallel crests, 1 waves from every direction."},
    {"name": "detail", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Weight of short waves and ripples against the peak band."},
    {"name": "choppiness", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Sideways crest sharpening, 0 smooth sines to 1 nearly breaking."},
    {"name": "foam", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Whitecap foam on the most compressed crests."},
    {"name": "relief", "type": "float", "default": 1.0, "minimum": 0.2, "maximum": 2.5,
     "meaning": "Strength of the normal map relief."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Open sea: a moderate wind sea with sharpened crests and a little foam.", "values": {}},
    "calm_swell": {"description": "Long parallel swell with smooth crests and no foam.",
                   "values": {"peak_waves": 2, "spread": 0.1, "detail": 0.2, "choppiness": 0.1, "foam": 0.0,
                              "components": 32}},
    "choppy_wind": {"description": "Short, steep wind chop from many directions with whitecaps.",
                    "values": {"peak_waves": 6, "spread": 0.7, "detail": 0.7, "choppiness": 0.75, "foam": 0.5,
                               "components": 72}},
    "stormy": {"description": "Heavy grey-green storm sea, near-breaking crests streaked with foam.",
               "values": {"peak_waves": 3, "spread": 0.5, "detail": 0.6, "choppiness": 0.95, "foam": 0.95,
                          "relief": 1.6, "components": 64}},
    "lake_ripples": {"description": "Small isotropic ripples on a brown-green lake.",
                     "values": {"peak_waves": 10, "spread": 1.0, "detail": 0.8, "choppiness": 0.0, "foam": 0.0,
                                "relief": 0.6, "components": 64}},
}
#: Per preset: deep water colour, crest colour (light through thin wave tops) and foam colour (sRGB).
PALETTES = {
    "default": ("#05283a", "#1d6a78", "#e8f2f2"),
    "calm_swell": ("#06304a", "#22738a", "#e8f2f2"),
    "choppy_wind": ("#063040", "#2a7a80", "#eef6f4"),
    "stormy": ("#16282a", "#3a5a52", "#dfe6e2"),
    "lake_ripples": ("#2a3424", "#4a5a3a", "#d8dcd0"),
}


def wave_components(peak: int, count: int, angle: float, spread: float, detail: float, seed: int) -> list:
    """(a, b, amplitude, phase) of the chosen waves: integer wave vectors (cycles across the tile) drawn without
    replacement with probability proportional to the directional spectrum (Gumbel top-k)."""
    reach = min(64, 4 * peak + 2)
    sharpness = 24.0 * (1.0 - spread) ** 2
    wind = math.tau * angle
    rng = tk.Rng(seed, 0x0CE)
    keyed = []
    for b in range(0, reach + 1):
        for a in range(-reach, reach + 1):
            if (b == 0 and a <= 0) or a * a + b * b > reach * reach:
                continue
            length = math.hypot(a, b)
            band = math.exp(-(math.log(length / peak)) ** 2 / (2.0 * (0.32 + 0.35 * detail) ** 2))
            facing = abs(math.cos(math.atan2(b, a) - wind)) ** sharpness
            weight = band * (0.02 + facing) / length ** (1.6 - 0.8 * detail)
            gumbel = -math.log(-math.log(min(max(rng.random(), 1e-12), 1.0 - 1e-12)))
            keyed.append((math.log(weight) + gumbel, a, b, weight))
    keyed.sort(reverse=True)
    chosen = []
    for _key, a, b, weight in keyed[:count]:
        chosen.append((a, b, math.sqrt(weight) / math.hypot(a, b), math.tau * rng.random()))
    return chosen


def _columns(components: list, width: int) -> dict:
    us = [(x + 0.5) / width for x in range(width)]
    columns = {}
    for a, _b, _amp, _phase in components:
        if a not in columns:
            columns[a] = ([math.sin(math.tau * a * u) for u in us], [math.cos(math.tau * a * u) for u in us])
    return columns


def wave_height(components: list, width: int, height: int) -> list:
    """The summed waves sin(2 pi (a u + b v) + phase), evaluated separably: sin(A + B) = sin A cos B + cos A sin B."""
    columns = _columns(components, width)
    out = []
    for y in range(height):
        v = (y + 0.5) / height
        row = [0.0] * width
        for a, b, amplitude, phase in components:
            angle = math.tau * b * v + phase
            sb, cb = amplitude * math.sin(angle), amplitude * math.cos(angle)
            sines, cosines = columns[a]
            row = [h + s * cb + c * sb for h, s, c in zip(row, sines, cosines)]
        out.extend(row)
    return out


def wave_shift(components: list, width: int, height: int) -> tuple:
    """Horizontal (Gerstner) displacement of the same waves: each moves along its own direction by
    amplitude * cos(2 pi (a u + b v) + phase), toward its crests."""
    columns = _columns(components, width)
    shift_x, shift_y = [], []
    for y in range(height):
        v = (y + 0.5) / height
        x_row = [0.0] * width
        y_row = [0.0] * width
        for a, b, amplitude, phase in components:
            angle = math.tau * b * v + phase
            sb, cb = amplitude * math.sin(angle), amplitude * math.cos(angle)
            sines, cosines = columns[a]
            length = math.hypot(a, b)
            ka, kb = a / length, b / length
            along = [c * cb - s * sb for s, c in zip(sines, cosines)]
            x_row = [d + ka * w for d, w in zip(x_row, along)]
            y_row = [d + kb * w for d, w in zip(y_row, along)]
        shift_x.extend(x_row)
        shift_y.extend(y_row)
    return shift_x, shift_y


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The ocean maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    deep_hex, crest_hex, foam_hex = PALETTES[preset]
    components = wave_components(p["peak_waves"], p["components"], p["wind_angle"], p["spread"], p["detail"], seed)
    raw = wave_height(components, width, height)
    # the displacement is smooth, so it is summed at half resolution and enlarged
    half_w, half_h = max(4, (width + 1) // 2), max(4, (height + 1) // 2)
    small_x, small_y = wave_shift(components, half_w, half_h)
    shift_x = tk.resample(small_x, half_w, half_h, width, height)
    shift_y = tk.resample(small_y, half_w, half_h, width, height)
    # divergence of the displacement in texture units: negative where crests compress
    divergence = []
    for y in range(height):
        row_x = shift_x[y * width:(y + 1) * width]
        above = shift_y[((y - 1) % height) * width:((y - 1) % height + 1) * width]
        below = shift_y[((y + 1) % height) * width:((y + 1) % height + 1) * width]
        divergence.extend([0.5 * width * (r - l) + 0.5 * height * (b - a)
                           for r, l, b, a in zip(row_x[1:] + row_x[:1], row_x[-1:] + row_x[:-1], below, above)])
    steepest = -min(divergence)
    chop = p["choppiness"]
    if chop > 0.0 and steepest > 1e-9:
        scale = 0.9 * chop / steepest
        surface = tk.warp(raw, width, height, shift_x, shift_y, -scale)
        compression = [1.0 + scale * d for d in divergence]
    else:
        surface = raw
        compression = [1.0] * (width * height)
    low, high = min(surface), max(surface)
    span = max(high - low, 1e-9)
    heights = [(s - low) / span for s in surface]
    foam_amount = p["foam"]
    streaks = tk.fbm(width, height, 12, 4, tk.hash_u32(seed, 2))
    bubbles = tk.voronoi(width, height, 24, 24, tk.hash_u32(seed, 3), jitter=0.9, edges=False)["f1"]
    deep, crest, white = tk.hex_rgb(deep_hex), tk.hex_rgb(crest_hex), tk.hex_rgb(foam_hex)
    red, green, blue, rough = [], [], [], []
    limit = 0.9 * chop if chop > 0.0 else 1.0
    for index in range(width * height):
        h = heights[index]
        squeeze = (1.0 - compression[index]) / limit
        foam = 0.0
        if foam_amount > 0.0:
            cap = tk.smoothstep(0.8 - 0.45 * foam_amount, 1.0 - 0.15 * foam_amount, squeeze + 0.15 * h)
            texture = tk.smoothstep(0.35, 0.8, 0.5 + 0.5 * streaks[index] + 0.45 * (0.55 - bubbles[index]))
            foam = min(1.0, foam_amount * cap * texture * 1.4)
        lift = 0.5 * tk.smoothstep(0.55, 1.0, h)
        colour = [d + (c - d) * lift for d, c in zip(deep, crest)]
        colour = [c + (f - c) * foam for c, f in zip(colour, white)]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        rough.append(0.05 + 0.04 * (0.5 + 0.5 * streaks[index]) + 0.55 * foam)
        heights[index] = h + 0.04 * foam
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    depth = 0.16 * p["relief"] / p["peak_waves"]
    occlusion = [1.0 - 0.25 * (1.0 - h) ** 2 for h in heights]
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=depth, roughness=rough,
                     ao=occlusion, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
