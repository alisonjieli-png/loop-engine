"""Rain on glass: droplets, running trails with beads and misted condensation, tileable maps with alpha (standard
library).

Droplets come in three size classes, each jittered inside the cells of its own grid with a chance per cell, so
small drops are many and large ones few. Each is a flattened dome (a power of 1 - r^2, slightly taller than wide
because water sags) painted into the height field with a maximum, so touching drops merge. Running drops leave
trails: a meandering vertical path (a random walk across the tile width as it runs down) painted as a thin wet
streak, with the running drop at its lower end and small beads left behind along it. A misting layer of tiny
condensation is fractal noise that the trails and large drops have wiped clear.

The normal map carries the drop bulges for refraction in a glass shader; the albedo alpha is low on clear glass,
higher on drops and highest on mist, for use as an overlay on a window.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "rain_on_glass"
MAPS = [
    {"name": "albedo", "channels": 4, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.15, 1.0]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.0, 0.8]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "drops", "type": "float", "default": 0.7, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Density of droplets."},
    {"name": "drop_size", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 2.0,
     "meaning": "Size of droplets and trails."},
    {"name": "trails", "type": "int", "default": 5, "minimum": 0, "maximum": 30,
     "meaning": "Running drops that leave trails down the glass."},
    {"name": "beading", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Beads left behind along the trails."},
    {"name": "mist", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Fine condensation misting the glass, wiped clear by trails and large drops."},
    {"name": "relief", "type": "float", "default": 1.0, "minimum": 0.3, "maximum": 2.0,
     "meaning": "Strength of the drop bulges in the normal map."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Steady rain: mixed droplets and a few trails with beads.", "values": {}},
    "drizzle": {"description": "Fine drizzle: many small drops and no trails.",
                "values": {"drops": 0.9, "drop_size": 0.6, "trails": 0}},
    "downpour": {"description": "Downpour: large merging drops and many long trails.",
                 "values": {"drops": 0.8, "drop_size": 1.6, "trails": 18, "beading": 0.8}},
    "misted": {"description": "Misted window: condensation wiped into clear streaks by running drops.",
               "values": {"drops": 0.35, "trails": 12, "mist": 0.9, "beading": 0.3}},
}
#: Per preset: glass tint, drop shadow tint, mist colour (sRGB) and the clear glass alpha.
PALETTES = {
    "default": ("#b8c8d0", "#4a5a64", "#e8eef0", 0.06),
    "drizzle": ("#c0ccd2", "#56646c", "#eaeef0", 0.05),
    "downpour": ("#a8bcc8", "#3c4c58", "#e4ecf0", 0.08),
    "misted": ("#c8d2d6", "#5a666c", "#f0f2f2", 0.06),
}
#: Droplet classes: grid cells across, smallest and largest radius (texture units) and the chance per cell.
DROP_CLASSES = ((44, 0.0016, 0.0035, 0.75), (18, 0.0035, 0.008, 0.6), (7, 0.008, 0.017, 0.5))


def _dome(s: float, t: float):
    d2 = s * s + t * t
    if d2 >= 1.0:
        return None
    return (1.0 - d2) ** 0.65


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The rain maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    glass_hex, shadow_hex, mist_hex, glass_alpha = PALETTES[preset]
    count = width * height
    smallest = 0.45 / min(width, height)
    size = p["drop_size"]
    rng = tk.Rng(seed, 0x2A1)
    drops = [0.0] * count
    wiped = [0.0] * count

    def drop(u: float, v: float, radius: float) -> None:
        # a drop smaller than about half a pixel is drawn at that size with its height scaled down
        lift = radius / 0.01 * min(1.0, radius / smallest)
        radius = max(radius, smallest)
        tk.stamp(drops, width, height, u, v, radius, radius * 1.1,
                 lambda s, t: None if s * s + t * t >= 1.0 else lift * (1.0 - s * s - t * t) ** 0.65,
                 mode=tk.MODE_MAX)
        if radius > 0.006:
            tk.stamp(wiped, width, height, u, v, 1.6 * radius, 1.6 * radius, _dome, mode=tk.MODE_MAX)

    for cells, low, high, chance in DROP_CLASSES:
        for cell in range(cells * cells):
            if rng.chance(chance * p["drops"]):
                u = (cell % cells + 0.1 + 0.8 * rng.random()) / cells
                v = (cell // cells + 0.1 + 0.8 * rng.random()) / cells
                drop(u, v, size * (low + (high - low) * rng.random() ** 2))
    trail = [0.0] * count
    for _ in range(p["trails"]):
        u, v = rng.random(), rng.random()
        width_trail = size * rng.uniform(0.0022, 0.0042)
        steps = rng.integer(12, 40)
        path = [(u, v)]
        for _step in range(steps):
            u += rng.gauss(0.0, 0.0035)
            v += 0.02
            path.append((u, v))
            if rng.chance(0.25 * p["beading"]):
                drop(u + rng.gauss(0.0, 0.001), v - 0.01, width_trail * rng.uniform(0.9, 1.5))
        tk.draw_path(trail, width, height, path, max(width_trail, smallest), 1.0, profile=lambda d: 1.0 - d * d)
        tk.draw_path(wiped, width, height, path, max(2.2 * width_trail, smallest), 1.0)
        drop(path[-1][0], path[-1][1] + 0.6 * width_trail, 2.3 * width_trail)
    mist_amount = p["mist"]
    haze = tk.fbm(width, height, 5, 4, tk.hash_u32(seed, 2))
    beads = tk.value_noise(width, height, 120, 120, tk.hash_u32(seed, 3))
    glass, shadow, mist_colour = tk.hex_rgb(glass_hex), tk.hex_rgb(shadow_hex), tk.hex_rgb(mist_hex)
    top = max(drops) or 1.0
    heights = [0.15 + 0.7 * d / top for d in drops]
    steep, facing = [], []
    scale = min(width, height) / 256.0
    for y in range(height):
        row = heights[y * width:(y + 1) * width]
        above = heights[((y - 1) % height) * width:((y - 1) % height + 1) * width]
        below = heights[((y + 1) % height) * width:((y + 1) % height + 1) * width]
        for l, r, a, b in zip(row[-1:] + row[:-1], row[1:] + row[:1], above, below):
            gx, gy = (r - l) * scale, (b - a) * scale
            steep.append(min(1.0, 4.0 * math.hypot(gx, gy)))
            # light from the upper left: slopes rising toward it are lit, the far side of a drop is shaded
            facing.append(max(-1.0, min(1.0, 6.0 * (0.6 * -gx + 0.8 * -gy))))
    red, green, blue, alpha, rough = [], [], [], [], []
    for index in range(count):
        wet = tk.smoothstep(0.0, 0.05, drops[index] / top)
        fog = mist_amount * tk.smoothstep(0.25, 0.75, 0.5 + 0.5 * haze[index] + 0.25 * mist_amount)
        fog *= (1.0 - wiped[index]) * (0.75 + 0.25 * beads[index])
        rim = wet * steep[index]
        light = wet * facing[index]
        colour = [g + (s - g) * 0.85 * rim for g, s in zip(glass, shadow)]
        colour = [c + ((1.0 - c) * light if light > 0.0 else c * 0.5 * light) for c in colour]
        colour = [c + (m - c) * fog for c, m in zip(colour, mist_colour)]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        alpha.append(min(0.95, glass_alpha + 0.4 * wet + 0.4 * rim + 0.3 * abs(light) + 0.6 * fog
                         + 0.12 * trail[index]))
        rough.append(0.02 + 0.03 * (1.0 - wet) + 0.55 * fog)
        heights[index] += 0.05 * trail[index] + 0.04 * fog * beads[index]
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, alpha=alpha, heights=heights, depth=0.012 * p["relief"],
                     roughness=rough, ao_radius=0.006, ao_strength=0.5, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
