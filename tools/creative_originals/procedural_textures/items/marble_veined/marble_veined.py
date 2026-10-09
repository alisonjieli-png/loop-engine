"""Veined marble: tileable PBR maps from the standard library only.

Veins are the zero crossings of anisotropic fractal noise: a field stretched along one axis crosses zero along long,
roughly parallel curves that branch now and then, like mineral-filled fractures. The field is warped by smooth noise
and sheared by a whole number of tiles (a shear that maps the torus onto itself), so the veins run diagonally and the
texture still repeats. Line width comes from the distance to the zero crossing (|f| / |grad f|), so veins keep their
width in texture space; a slower noise makes them swell and thin along their length. A second, finer field adds thin
secondary veins, and a soft cloud tints the stone between them. The surface is polished: the height map carries only
slight vein recesses and pits.
"""
from __future__ import annotations

import sys

import texkit as tk

IDENTITY = "marble_veined"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.92]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.04, 0.8]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "vein_spacing", "type": "int", "default": 2, "minimum": 1, "maximum": 8,
     "meaning": "Noise cells across the veins: higher values give more, closer veins."},
    {"name": "vein_direction", "type": "int", "default": 0, "minimum": 0, "maximum": 4,
     "meaning": "Vein run: 0 falling diagonal, 1 rising diagonal, 2 horizontal, 3 vertical, 4 steep diagonal."},
    {"name": "vein_width", "type": "float", "default": 0.008, "minimum": 0.002, "maximum": 0.04,
     "meaning": "Average width of the main veins in texture units."},
    {"name": "flow", "type": "float", "default": 0.06, "minimum": 0.0, "maximum": 0.2,
     "meaning": "Domain warp in texture units: how much the veins meander."},
    {"name": "secondary_veins", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Strength of the thin secondary veins."},
    {"name": "cloudiness", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Soft tonal clouds in the stone between veins."},
    {"name": "polish", "type": "float", "default": 0.85, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Surface finish from honed (0, matte) to polished (1, glossy)."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "White stone with soft grey diagonal veins, polished.", "values": {}},
    "calacatta": {"description": "Warm white stone with bold, widely spaced grey and gold veins.",
                  "values": {"vein_spacing": 1, "vein_width": 0.018, "flow": 0.1, "secondary_veins": 0.35,
                             "vein_direction": 1}},
    "nero": {"description": "Black stone with sharp white veins.",
             "values": {"vein_spacing": 2, "vein_width": 0.005, "flow": 0.07, "secondary_veins": 0.85,
                        "vein_direction": 4, "cloudiness": 0.3}},
    "verde": {"description": "Dark green serpentine marble with pale meandering veins, honed.",
              "values": {"vein_spacing": 4, "vein_width": 0.005, "flow": 0.14, "secondary_veins": 0.9,
                         "polish": 0.35, "vein_direction": 2, "cloudiness": 0.8}},
    "rosso": {"description": "Red-brown marble with cream veins and strong clouds.",
              "values": {"vein_spacing": 3, "vein_width": 0.01, "flow": 0.12, "secondary_veins": 0.6,
                         "cloudiness": 0.9, "vein_direction": 3}},
}
#: Stone ramp (dark to light cloud), main vein colour and secondary vein colour per preset.
PALETTES = {
    "default": ([(0.0, "#d6d5d0"), (0.6, "#eae9e4"), (1.0, "#f5f4f0")], "#6f7175", "#9a9b9e"),
    "calacatta": ([(0.0, "#e0dacf"), (0.6, "#efeae0"), (1.0, "#f8f5ef")], "#6e665a", "#b0955f"),
    "nero": ([(0.0, "#0b0b0d"), (0.6, "#151518"), (1.0, "#212125")], "#ebe9e3", "#bdbbb5"),
    "verde": ([(0.0, "#0e281d"), (0.5, "#1d4432"), (1.0, "#33684c")], "#c4d3be", "#86a38f"),
    "rosso": ([(0.0, "#561d15"), (0.5, "#772f21"), (1.0, "#984833")], "#eadac2", "#c9a78a"),
}
#: Whole-tile shear of v per unit of u for each vein direction (3, vertical, swaps the stretched axis instead).
SHEARS = {0: 1, 1: -1, 2: 0, 3: 0, 4: 2}


def _sheared(field: list, width: int, height: int, shear: int) -> list:
    """Sample a periodic field at (u, v + shear * u): a whole-tile shear maps the torus onto itself."""
    if not shear:
        return field
    offset_v = [shear * (x + 0.5) / width for _y in range(height) for x in range(width)]
    return tk.warp(field, width, height, [0.0] * (width * height), offset_v, 1.0)


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The marble maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    stone, vein_hex, secondary_hex = PALETTES[preset]
    spacing = p["vein_spacing"]
    shear = SHEARS[p["vein_direction"]]
    vertical = p["vein_direction"] == 3
    cells = (spacing, 1) if vertical else (1, spacing)
    fine_cells = (2 * spacing + 1, 2) if vertical else (2, 2 * spacing + 1)
    main = tk.fbm(width, height, cells[0], 4, tk.hash_u32(seed, 1), gain=0.5, cells_y=cells[1])
    thin = tk.fbm(width, height, fine_cells[0], 3, tk.hash_u32(seed, 2), gain=0.5, cells_y=fine_cells[1])
    warp_u = tk.fbm(width, height, 2, 4, tk.hash_u32(seed, 3))
    warp_v = tk.fbm(width, height, 2, 4, tk.hash_u32(seed, 4))
    main = _sheared(tk.warp(main, width, height, warp_u, warp_v, p["flow"]), width, height, shear)
    thin = _sheared(tk.warp(thin, width, height, warp_u, warp_v, p["flow"]), width, height, shear)
    girth = tk.value_noise(width, height, 3, 3, tk.hash_u32(seed, 5))
    fuzz = tk.fbm(width, height, 24, 3, tk.hash_u32(seed, 8))
    pixel = 0.8 / min(width, height)
    vein_width = p["vein_width"]
    near_main = tk.isoline_distance(main, width, height)
    near_thin = tk.isoline_distance(thin, width, height)
    veins = [(0.55 + 0.45 * g) * (1.0 - tk.smoothstep(0.0, max(vein_width * (0.5 + 0.9 * g), pixel),
                                                       d + vein_width * 0.9 * z))
             for d, g, z in zip(near_main, girth, fuzz)]
    halo = [(1.0 - tk.smoothstep(0.0, vein_width * 6.0, d + vein_width * 2.0 * z)) * (0.4 + 0.6 * g)
            for d, g, z in zip(near_main, girth, fuzz)]
    secondary = p["secondary_veins"]
    fine = [secondary * (1.0 - tk.smoothstep(0.0, max(vein_width * 0.35, pixel), d)) for d in near_thin]
    cloud = tk.normalize(tk.fbm(width, height, 3, 6, tk.hash_u32(seed, 6)))
    pits = tk.white_noise(width, height, tk.hash_u32(seed, 7))
    cloudiness = p["cloudiness"]
    base_rgb = tk.ramp([0.5 + (c - 0.5) * cloudiness for c in cloud], stone)
    mixed = tk.mix_rgb(base_rgb, tk.hex_rgb(secondary_hex), [0.8 * f for f in fine])
    mixed = tk.mix_rgb(mixed, tk.hex_rgb(vein_hex), [min(1.0, 0.3 * h + 0.8 * m) for h, m in zip(halo, veins)])
    albedo = tk.grade(mixed, p["hue_shift"], p["saturation"], p["brightness"])
    heights = [0.55 - 0.12 * m - 0.06 * f - (0.08 if r > 0.996 else 0.0) + 0.03 * (c - 0.5)
               for m, f, r, c in zip(veins, fine, pits, cloud)]
    base_rough = 0.06 + 0.5 * (1.0 - p["polish"])
    roughness = [base_rough + 0.05 * m + 0.04 * f + (0.15 if r > 0.996 else 0.0)
                 for m, f, r in zip(veins, fine, pits)]
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.006, roughness=roughness,
                     ao_radius=0.01, ao_strength=0.6, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
