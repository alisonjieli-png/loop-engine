"""Cloud layer: cumulus, stratus, cirrus or mackerel sky as a tileable density with alpha (standard library).

Each cloud type is a different density field: cumulus is fractal noise cut at a coverage threshold and eroded by
inverted Worley noise, which leaves billowing cauliflower edges; stratus is broad noise stretched along the tile
width at high coverage; cirrus is noise stretched into long streaks and sheared by a slow warp, then thinned by a
ridged field into wisps; a mackerel sky multiplies cellular puffs by a wave that sets them in rows. Light comes
from a sun direction across the layer: the density is sampled at several steps toward the sun and the optical depth
gives a Beer-Lambert transmittance, so the far sides and thick cores of clouds fall into grey shade while their
sunward edges stay bright.

The albedo carries the lit colour and the alpha the density with soft edges, for a sky plane or dome; height and
normals follow the density, so the layer can also be shaded as a puffy surface.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "cloud_layer"
MAPS = [
    {"name": "albedo", "channels": 4, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.15, 1.0]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.6, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "kind", "type": "int", "default": 0, "minimum": 0, "maximum": 3,
     "meaning": "0 cumulus, 1 stratus, 2 cirrus, 3 mackerel (altocumulus in rows)."},
    {"name": "coverage", "type": "float", "default": 0.45, "minimum": 0.05, "maximum": 1.0,
     "meaning": "Share of the sky covered by cloud."},
    {"name": "cells", "type": "int", "default": 3, "minimum": 1, "maximum": 10,
     "meaning": "Cloud features across the tile."},
    {"name": "billow", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Cauliflower erosion of the cloud edges (cumulus and mackerel)."},
    {"name": "softness", "type": "float", "default": 0.4, "minimum": 0.05, "maximum": 1.0,
     "meaning": "Width of the soft edge between cloud and clear sky."},
    {"name": "sun_angle", "type": "float", "default": 0.375, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Direction the sunlight comes from across the layer, in turns from +U."},
    {"name": "shading", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Self-shadowing: how dark the far sides and thick cores become."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Fair-weather cumulus: separate white heaps with grey shaded sides.", "values": {}},
    "overcast_stratus": {"description": "Overcast stratus: a nearly closed grey sheet with soft thin patches.",
                         "values": {"kind": 1, "coverage": 0.9, "cells": 2, "softness": 0.8, "shading": 0.35}},
    "cirrus_wisps": {"description": "High cirrus: thin bright streaks and hooks across a clear sky.",
                     "values": {"kind": 2, "coverage": 0.35, "cells": 2, "softness": 0.6, "shading": 0.15}},
    "mackerel_sky": {"description": "Mackerel sky: rows of small rounded altocumulus puffs.",
                     "values": {"kind": 3, "coverage": 0.55, "cells": 8, "billow": 0.4, "softness": 0.3}},
    "storm_nimbus": {"description": "Storm: dense dark towering cloud with bright rims, little clear sky.",
                     "values": {"coverage": 0.85, "cells": 2, "billow": 0.8, "shading": 1.0}},
}
#: Per preset: sunlit colour, shadow colour (sRGB) and the shadow density scale.
PALETTES = {
    "default": ("#ffffff", "#8c98aa", 1.0),
    "overcast_stratus": ("#d8dce0", "#8a9098", 0.8),
    "cirrus_wisps": ("#ffffff", "#c8d4e4", 0.6),
    "mackerel_sky": ("#fffaf4", "#a0a8b8", 1.0),
    "storm_nimbus": ("#c0c4cc", "#30363e", 3.2),
}


def _density(kind: int, width: int, height: int, seed: int, cells: int, coverage: float, billow: float) -> list:
    """Cloud density in 0..1 before the soft edge, one field per cloud kind."""
    if kind == 1:
        base = tk.fbm(width, height, cells, 5, tk.hash_u32(seed, 1), cells_y=cells * 2)
        detail = tk.fbm(width, height, cells * 4, 3, tk.hash_u32(seed, 2))
        field = [0.5 + 0.6 * b + 0.12 * d for b, d in zip(base, detail)]
    elif kind == 2:
        shear_u = tk.fbm(width, height, 1, 3, tk.hash_u32(seed, 3))
        shear_v = tk.fbm(width, height, 2, 3, tk.hash_u32(seed, 4))
        streaks = tk.fbm(width, height, cells, 5, tk.hash_u32(seed, 5), cells_y=cells * 8)
        threads = tk.ridged(width, height, cells * 2, 4, tk.hash_u32(seed, 6), cells_y=cells * 16)
        streaks = tk.warp(streaks, width, height, shear_u, shear_v, 0.12)
        threads = tk.warp(threads, width, height, shear_u, shear_v, 0.12)
        field = [0.5 + 0.7 * s - 0.25 + 0.45 * t * t for s, t in zip(streaks, threads)]
    else:
        base = tk.fbm(width, height, cells, 5, tk.hash_u32(seed, 7))
        puffs = tk.voronoi(width, height, cells * 3, cells * 3, tk.hash_u32(seed, 8), jitter=0.9, edges=False)["f1"]
        if kind == 3:
            ripple = tk.fbm(width, height, 2, 3, tk.hash_u32(seed, 9))
            field = []
            for y in range(height):
                v = (y + 0.5) / height
                for x in range(width):
                    index = y * width + x
                    wave = 0.5 + 0.5 * math.sin(math.tau * (cells * v + 0.08 * cells * ripple[index]))
                    puff = max(0.0, 1.0 - (1.2 + billow) * puffs[index])
                    field.append(wave * puff + 0.25 * base[index])
        else:
            field = [0.5 + 0.8 * b + billow * (0.35 - 0.6 * f) for b, f in zip(base, puffs)]
    ordered = sorted(field[::3])
    limit = ordered[min(len(ordered) - 1, int((1.0 - coverage) * len(ordered)))]
    top = ordered[-1]
    span = max(top - limit, 1e-6)
    return [max(0.0, (value - limit) / span) for value in field]


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The cloud maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    lit_hex, shade_hex, thickness = PALETTES[preset]
    density = _density(p["kind"], width, height, seed, p["cells"], p["coverage"], p["billow"])
    soft = p["softness"]
    body = [tk.smoothstep(0.0, 0.15 + 0.6 * soft, d) for d in density]
    sun = math.tau * p["sun_angle"]
    elevation = math.radians(35.0)
    light_x, light_y = math.cos(sun) * math.cos(elevation), math.sin(sun) * math.cos(elevation)
    light_z = math.sin(elevation)
    step_u, step_v = 0.02 * math.cos(sun), 0.02 * math.sin(sun)
    slope = 0.035
    lit_colour, shade_colour = tk.hex_rgb(lit_hex), tk.hex_rgb(shade_hex)
    wisps = tk.fbm(width, height, 24, 3, tk.hash_u32(seed, 10))
    red, green, blue, alpha, heights, rough, occlusion = [], [], [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        for x in range(width):
            index = y * width + x
            u = (x + 0.5) / width
            here = body[index]
            left, right = body[y * width + (x - 1) % width], body[y * width + (x + 1) % width]
            up, down = body[((y - 1) % height) * width + x], body[((y + 1) % height) * width + x]
            nx, ny = -(right - left) * 0.5 * width * slope, -(down - up) * 0.5 * height * slope
            facing = (nx * light_x + ny * light_y + light_z) / math.sqrt(nx * nx + ny * ny + 1.0)
            # sunlight blocked by cloud a little way toward the sun, and the darkening of thick cores
            blocked = tk.sample(body, width, height, u + step_u, v + step_v) + \
                tk.sample(body, width, height, u + 2.0 * step_u, v + 2.0 * step_v)
            light = tk.clamp(0.35 + 1.0 * max(0.0, facing)) * math.exp(
                -p["shading"] * thickness * (0.25 * blocked * (1.0 - 0.5 * here) + 0.35 * here * here))
            colour = [s + (l - s) * light for s, l in zip(shade_colour, lit_colour)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            alpha.append(min(1.0, 1.25 * here * (0.9 + 0.1 * wisps[index])))
            heights.append(0.15 + 0.7 * here + 0.05 * wisps[index] * here)
            rough.append(0.85 + 0.12 * (1.0 - here))
            occlusion.append(0.55 + 0.45 * light)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, alpha=alpha, heights=heights, depth=0.02,
                     roughness=rough, ao=occlusion, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
