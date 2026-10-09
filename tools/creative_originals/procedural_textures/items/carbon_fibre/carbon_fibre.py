"""Carbon fibre composite: 2x2 twill, plain weave or forged carbon under clear coat (standard library only).

Woven styles lay tows (flat bundles of fibres) on a grid: a draft decides which tow is on top at each crossing,
2x2 twill or plain. A tow carries fine fibre lines along its own direction, a rounded cross-section and darker ends
where it dives under; tows running across the tile reflect differently from tows running down it, the anisotropic
sheen that makes carbon weave visible. Forged carbon is chopped fibre pressed flat: Voronoi patches, each with its
own fibre direction, measured from the patch nucleus on the torus so patches crossing the tile edge stay continuous.
A glossy clear coat gives low roughness; carbon is not metallic.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "carbon_fibre"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.01, 0.8]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.05, 0.8]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "style", "type": "int", "default": 0, "minimum": 0, "maximum": 2,
     "meaning": "Construction: 0 2x2 twill, 1 plain weave, 2 forged (chopped fibre)."},
    {"name": "tows_across", "type": "int", "default": 16, "minimum": 4, "maximum": 64,
     "meaning": "Tows across the tile (rounded up to a multiple of the weave repeat); forged patches scale with it."},
    {"name": "sheen", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Brightness difference between tow directions."},
    {"name": "clear_coat", "type": "float", "default": 0.85, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Gloss of the clear coat (0 dry matte weave, 1 deep gloss)."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Black 2x2 twill carbon under gloss clear coat.", "values": {}},
    "plain_weave": {"description": "Plain-weave carbon with wide tows.", "values": {"style": 1, "tows_across": 12}},
    "forged": {"description": "Forged carbon with marbled chopped-fibre patches.",
               "values": {"style": 2, "tows_across": 10, "sheen": 0.8}},
    "kevlar_hybrid": {"description": "Yellow aramid and black carbon tows in twill.",
                      "values": {"tows_across": 12, "sheen": 0.5}},
    "matte_dry": {"description": "Uncoated dry twill with a matte finish.", "values": {"clear_coat": 0.1}},
}
#: Tow colours (down, across) per preset (sRGB) and whether the colours alternate tow by tow (a hybrid weave of
#: two fibres) instead of following the direction.
PALETTES = {
    "default": ("#2a2c30", "#141518", False),
    "plain_weave": ("#2a2c30", "#141518", False),
    "forged": ("#303237", "#111214", False),
    "kevlar_hybrid": ("#c99a1e", "#151618", True),
    "matte_dry": ("#36383c", "#1d1e21", False),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The carbon fibre maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    down_hex, across_hex, alternate = PALETTES[preset]
    down_rgb, across_rgb = tk.hex_rgb(down_hex), tk.hex_rgb(across_hex)
    style, sheen = p["style"], p["sheen"]
    gloss = p["clear_coat"]
    speck = tk.white_noise(width, height, tk.hash_u32(seed, 1))
    red, green, blue, heights, rough = [], [], [], [], []
    if style == 2:
        cells = p["tows_across"]
        points = tk.cell_points(cells, cells, tk.hash_u32(seed, 2), 1.0)
        patches = tk.voronoi(width, height, cells, cells, points=points)
        angles = [tk.hash_float(k, seed, 3) * math.pi for k in range(cells * cells)]
        tones = [tk.hash_float(k, seed, 4) for k in range(cells * cells)]
        for y in range(height):
            v = (y + 0.5) / height
            base = y * width
            for x in range(width):
                index = base + x
                u = (x + 0.5) / width
                cell = patches["cell"][index]
                du = tk.wrap_delta(u - points[0][cell] / cells)
                dv = tk.wrap_delta(v - points[1][cell] / cells)
                angle = angles[cell]
                across = -du * math.sin(angle) + dv * math.cos(angle)
                fibre = 0.5 + 0.5 * math.cos(math.tau * across * cells * 22.0)
                shine = sheen * (0.5 + 0.5 * math.cos(2.0 * angle)) * (0.6 + 0.4 * tones[cell])
                border = 1.0 - tk.smoothstep(0.0, 0.03, patches["edge"][index])
                mix = min(1.0, 0.15 + 0.7 * shine + 0.1 * fibre)
                colour = [a + (b - a) * (1.0 - mix) for a, b in zip(down_rgb, across_rgb)]
                colour = [c * (0.92 + 0.08 * fibre) * (1.0 - 0.3 * border) for c in colour]
                red.append(colour[0])
                green.append(colour[1])
                blue.append(colour[2])
                heights.append(0.5 + 0.03 * fibre - 0.05 * border)
                rough.append(0.08 + 0.55 * (1.0 - gloss) + 0.04 * speck[index])
    else:
        repeat = 4 if style == 0 else 2
        tows = -(-p["tows_across"] // repeat) * repeat
        for y in range(height):
            fv = (y + 0.5) / height * tows
            j = int(fv) % tows
            b = fv - math.floor(fv)
            base = y * width
            for x in range(width):
                index = base + x
                fu = (x + 0.5) / width * tows
                i = int(fu) % tows
                a = fu - math.floor(fu)
                if style == 0:
                    down_on_top = (i - j) % 4 in (0, 1)
                    before = (i - j + 1) % 4 in (0, 1)
                    after = (i - j - 1) % 4 in (0, 1)
                else:
                    down_on_top = (i + j) % 2 == 0
                    before = after = not down_on_top
                if down_on_top:
                    across_tow, along = a, b
                    dips = (not before, not after)
                    colour_pick = down_rgb if not alternate or i % 2 == 0 else across_rgb
                    shine = sheen
                else:
                    across_tow, along = b, a
                    dips = (after, before)
                    colour_pick = across_rgb if not alternate or j % 2 == 0 else down_rgb
                    shine = 0.0
                section = math.sqrt(max(0.0, 1.0 - (2.0 * across_tow - 1.0) ** 2))
                rise = 1.0
                if dips[0]:
                    rise *= 0.6 + 0.4 * tk.smoothstep(0.0, 0.3, along)
                if dips[1]:
                    rise *= 0.6 + 0.4 * tk.smoothstep(0.0, 0.3, 1.0 - along)
                fibre = 0.5 + 0.5 * math.cos(math.tau * across_tow * 9.0)
                tone = (0.75 + 0.25 * section) * rise * (0.94 + 0.06 * fibre)
                colour = [c * tone * (1.0 + 0.9 * shine * section) for c in colour_pick]
                red.append(colour[0])
                green.append(colour[1])
                blue.append(colour[2])
                heights.append(0.35 + 0.4 * section * rise + 0.02 * fibre)
                rough.append(0.08 + 0.55 * (1.0 - gloss) + 0.04 * speck[index] + 0.05 * (1.0 - rise))
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.002 + 0.06 / p["tows_across"],
                     roughness=rough, ao_radius=0.3 / p["tows_across"], ao_strength=0.6, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
