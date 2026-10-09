"""Snow: soft drifts, wind-carved sastrugi and old crusted snow, tileable PBR maps (standard library only).

Fresh snow is a gentle swell of low-frequency noise with fine crystal grain. Glints are tiny stamps placed in
texture space that are brighter and smoother than the snow around them, so they sparkle under a moving light.
Hollows take a cool blue tint, a cheap stand-in for light scattered inside the snowpack. Sastrugi add sharp ridges
from ridged noise stretched across the wind; old snow adds dirt specks, a glazed crust and melt pitting.
"""
from __future__ import annotations

import sys

import texkit as tk

IDENTITY = "snow_fresh"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.3, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.1, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "drift_scale", "type": "int", "default": 3, "minimum": 1, "maximum": 12,
     "meaning": "Noise cells across the tile for the drifts (higher gives smaller drifts)."},
    {"name": "drift_height", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Height of the soft drifts."},
    {"name": "wind_ridges", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Sharp wind-carved ridges (sastrugi)."},
    {"name": "glints", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Density of sparkling crystal glints."},
    {"name": "age", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Old snow: dirt specks, glazed crust and melt pits."},
    {"name": "blue_tint", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Cool tint in the hollows."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Fresh powder with soft drifts and glints.", "values": {}},
    "sastrugi": {"description": "Wind-packed snow carved into sharp ridges.",
                 "values": {"wind_ridges": 0.9, "drift_height": 0.3, "glints": 0.3}},
    "old_crusted": {"description": "Old, dirty snow with an icy crust and melt pits.",
                    "values": {"age": 0.85, "glints": 0.7, "blue_tint": 0.2, "drift_scale": 5}},
    "drift_field": {"description": "Large rolling drifts in deep fresh snow under a cold blue sky.",
                    "values": {"drift_scale": 2, "drift_height": 0.95, "glints": 0.4, "blue_tint": 1.0,
                               "brightness": 0.93}},
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The snow maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    count = width * height
    drifts = tk.normalize(tk.fbm(width, height, p["drift_scale"], 4, tk.hash_u32(seed, 1), gain=0.45))
    crystals = tk.fbm(width, height, 48, 3, tk.hash_u32(seed, 2))
    ridges = tk.ridged(width, height, 3, 3, tk.hash_u32(seed, 3), cells_y=9) if p["wind_ridges"] > 0 else [0.0] * count
    melt = tk.voronoi(width, height, 24, 24, tk.hash_u32(seed, 4), jitter=1.0, edges=False)["f1"] \
        if p["age"] > 0 else [1.0] * count
    dirt_field = tk.fbm(width, height, 6, 4, tk.hash_u32(seed, 5))
    specks = tk.white_noise(width, height, tk.hash_u32(seed, 6))
    glint = [0.0] * count
    rng = tk.Rng(seed, 7)
    for _ in range(int(1500 * p["glints"])):
        radius = rng.uniform(0.0012, 0.003)
        tk.stamp(glint, width, height, rng.random(), rng.random(), radius, radius, lambda s, t: 1.0)
    drift_height, wind, age, tint = p["drift_height"], p["wind_ridges"], p["age"], p["blue_tint"]
    surface = []
    for index in range(count):
        ridge = wind * tk.smoothstep(0.55, 0.95, ridges[index])
        pit = age * (1.0 - tk.smoothstep(0.1, 0.35, melt[index]))
        surface.append(0.3 + 0.45 * drift_height * drifts[index] + 0.25 * ridge + 0.015 * crystals[index]
                       - 0.12 * pit)
    hollows = tk.blur(surface, width, height, 0.03)
    red, green, blue, rough = [], [], [], []
    for index in range(count):
        cavity = max(0.0, hollows[index] - surface[index]) * 12.0 + (1.0 - drifts[index]) * 0.25
        cool = tint * min(1.0, cavity)
        white = 0.9 + 0.04 * crystals[index]
        colour = [white * (1.0 - 0.12 * cool), white * (1.0 - 0.05 * cool), white]
        dirt = age * tk.smoothstep(0.15, 0.4, dirt_field[index]) * (0.35 if specks[index] > 0.9 else 0.12)
        colour = [c * (1.0 - dirt) for c in colour]
        colour[2] -= 0.06 * age
        sparkle = glint[index]
        colour = [c + (0.98 - c) * sparkle for c in colour]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        crust = age * 0.45 * tk.smoothstep(-0.1, 0.2, dirt_field[index])
        rough.append(0.82 - crust - 0.5 * sparkle + 0.05 * crystals[index])
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=surface, depth=0.03, roughness=rough,
                     ao_radius=0.03, ao_strength=0.5, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
