"""Cork: agglomerated granules or natural cork with lenticels, with pores and pin holes, tileable PBR maps.

Agglomerated cork is two cellular layers on the torus: coarse granules and finer fragments inside them, both warped
so no polygon edges show. Every granule and fragment takes its own tone, and the borders between granules sink into
dark crevices. Natural cork is one continuous mass whose lenticels, the dark breathing channels of the bark, appear
as elongated pores from stretched noise. Fine pores pit both, pin holes punch small dark holes with a raised rim, and
a sealed finish fills the pores, deepens the colour and adds gloss, as on cork floor tiles.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "cork_board"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.25, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "pattern", "type": "int", "default": 0, "minimum": 0, "maximum": 1,
     "meaning": "0 agglomerated granules (boards, tiles), 1 natural cork with lenticels (stoppers, bark slabs)."},
    {"name": "granules", "type": "int", "default": 30, "minimum": 8, "maximum": 72,
     "meaning": "Granules across the tile width (agglomerated cork)."},
    {"name": "fragments", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Visibility of the finer fragments inside the granules."},
    {"name": "gaps", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Depth and darkness of the crevices between granules."},
    {"name": "pores", "type": "float", "default": 0.45, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Density of fine pores (and of lenticels in natural cork)."},
    {"name": "pin_holes", "type": "int", "default": 12, "minimum": 0, "maximum": 60,
     "meaning": "Pin holes punched into the tile."},
    {"name": "tone_variation", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spread of colour between granules."},
    {"name": "sealed", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Varnish: fills pores, deepens the colour and adds gloss."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Notice-board cork: mixed granules with pin holes.", "values": {}},
    "floor_tile": {"description": "Fine sealed cork floor tile with a satin varnish.",
                   "values": {"granules": 40, "fragments": 0.4, "gaps": 0.25, "pin_holes": 0, "sealed": 0.6,
                              "tone_variation": 0.5}},
    "expanded_dark": {"description": "Heat-expanded black cork insulation: coarse dark granules, deep gaps.",
                      "values": {"granules": 18, "gaps": 0.85, "pin_holes": 0, "tone_variation": 0.35,
                                 "pores": 0.3}},
    "natural_stopper": {"description": "Natural cork as in a wine stopper: golden mass with dark lenticels.",
                        "values": {"pattern": 1, "pores": 0.55, "pin_holes": 0, "tone_variation": 0.3}},
}
#: Light granule, dark granule, crevice colour and sealed tint per preset (sRGB).
PALETTES = {
    "default": ("#c49a6a", "#7d5634", "#3a2414", "#a0682e"),
    "floor_tile": ("#c0915c", "#8a5c32", "#4a2c16", "#9a5a22"),
    "expanded_dark": ("#4a3a30", "#1e1814", "#0c0a08", "#2a1e16"),
    "natural_stopper": ("#d2ac78", "#a87c4c", "#4a3018", "#b07a3a"),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The cork maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    light_rgb, dark_rgb, gap_rgb, sealed_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    natural = p["pattern"] == 1
    cells = p["granules"]
    fragments, gaps, pores = p["fragments"], p["gaps"], p["pores"]
    variation, sealed = p["tone_variation"], p["sealed"]
    count = width * height
    limit = max(4, min(width, height) // 2)
    warp_u = tk.fbm(width, height, max(4, cells // 3), 3, tk.hash_u32(seed, 1))
    warp_v = tk.fbm(width, height, max(4, cells // 3), 3, tk.hash_u32(seed, 2))
    rng = tk.Rng(seed, 0xC0)
    if natural:
        mass = tk.fbm(width, height, 6, 4, tk.hash_u32(seed, 3))
        lenticels = tk.value_noise(width, height, min(limit, 40), min(limit, 9), tk.hash_u32(seed, 4))
        lenticels = tk.warp(lenticels, width, height, warp_u, warp_v, 0.03)
        crevice = [0.0] * count
        tone = [0.5 + 0.7 * m for m in mass]
        porous = [tk.smoothstep(0.86 - 0.12 * pores, 0.97 - 0.08 * pores, value) for value in lenticels]
    else:
        coarse = tk.voronoi(width, height, cells, cells, tk.hash_u32(seed, 5), jitter=1.0)
        fine_cells = min(limit, int(cells * 2.4))
        fine = tk.voronoi(width, height, fine_cells, fine_cells, tk.hash_u32(seed, 6), jitter=1.0)
        coarse_tone = [rng.random() for _ in range(cells * cells)]
        fine_tone = [rng.random() for _ in range(fine_cells * fine_cells)]
        edge = tk.warp(coarse["edge"], width, height, warp_u, warp_v, 0.4 / cells)
        edge_fine = tk.warp(fine["edge"], width, height, warp_v, warp_u, 0.4 / fine_cells)
        ids = coarse["cell"]
        fine_ids = fine["cell"]
        crevice = [(1.0 - tk.smoothstep(0.0, 0.07 + 0.08 * gaps, e)) * (0.6 + 0.4 * gaps) for e in edge]
        tone = [(1.0 - 0.45 * fragments) * coarse_tone[a] + 0.45 * fragments * fine_tone[b]
                for a, b in zip(ids, fine_ids)]
        tone = [t - 0.25 * fragments * (1.0 - tk.smoothstep(0.0, 0.06, e)) for t, e in zip(tone, edge_fine)]
        pit_field = tk.value_noise(width, height, min(limit, cells * 4), min(limit, cells * 4), tk.hash_u32(seed, 7))
        porous = [tk.smoothstep(0.86 - 0.1 * pores, 0.98 - 0.06 * pores, value) for value in pit_field]
    grain = tk.fbm(width, height, min(limit, 64), 2, tk.hash_u32(seed, 8))
    holes = [0.0] * count
    rims = [0.0] * count
    hole_radius = 0.006
    for _ in range(p["pin_holes"]):
        cu, cv = rng.random(), rng.random()
        for index, s, t in tk.ellipse_pixels(width, height, cu, cv, hole_radius * 2.2, hole_radius * 2.2):
            r = math.sqrt(s * s + t * t) * 2.2
            if r < 1.0:
                holes[index] = max(holes[index], 1.0 - tk.smoothstep(0.7, 1.0, r))
            elif r < 2.2:
                rims[index] = max(rims[index], 1.0 - tk.smoothstep(1.0, 2.2, r))
    heights, red, green, blue, rough = [], [], [], [], []
    for index in range(count):
        t = 0.5 + (tone[index] - 0.5) * variation
        pit = porous[index] * pores * (1.0 - 0.8 * sealed)
        dip = crevice[index]
        level = 0.6 + 0.05 * grain[index] - 0.35 * dip - 0.25 * pit + 0.06 * rims[index] - 0.5 * holes[index]
        heights.append(level)
        colour = [d + (l - d) * t for l, d in zip(light_rgb, dark_rgb)]
        colour = [c * (0.92 + 0.12 * grain[index]) for c in colour]
        colour = [c + (g - c) * min(1.0, dip * 0.9 + pit * 0.8) for c, g in zip(colour, gap_rgb)]
        colour = [c + (s * (0.75 + 0.5 * c) - c) * 0.45 * sealed for c, s in zip(colour, sealed_rgb)]
        colour = [c * (1.0 - 0.85 * holes[index]) for c in colour]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        rough.append(0.9 - 0.5 * sealed + 0.08 * dip + 0.05 * pit - 0.03 * grain[index])
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.012, roughness=rough,
                     ao_radius=0.012, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
