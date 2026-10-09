"""Furrowed tree bark: tileable PBR maps from the standard library only, with the trunk axis running down the tile.

Three structures: plates (pine, oak) are tall Voronoi cells, warped so the furrows between them wander; interlaced
ridges (ash, old oak) come from ridged noise stretched along the trunk, which splits and rejoins in a diamond net;
stringy bark (cedar, redwood) is many thin fibre strips. Fibres stretched along the trunk texture every surface,
cross-checks break the plates, and lichen and moss settle on the plates and in the furrows.
"""
from __future__ import annotations

import sys

import texkit as tk

IDENTITY = "bark_furrowed"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.8]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.55, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "pattern", "type": "int", "default": 0, "minimum": 0, "maximum": 2,
     "meaning": "Bark structure: 0 plates, 1 interlaced ridges, 2 stringy fibres."},
    {"name": "ridges_across", "type": "int", "default": 6, "minimum": 2, "maximum": 16,
     "meaning": "Plates or ridges across the tile width."},
    {"name": "plate_length", "type": "int", "default": 1, "minimum": 1, "maximum": 6,
     "meaning": "Plate rows down the tile (fewer rows give longer plates)."},
    {"name": "furrow_depth", "type": "float", "default": 0.7, "minimum": 0.1, "maximum": 1.0,
     "meaning": "Depth of the furrows between plates or ridges."},
    {"name": "furrow_width", "type": "float", "default": 0.12, "minimum": 0.02, "maximum": 0.4,
     "meaning": "Width of the furrows, in plate widths."},
    {"name": "cross_checks", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Horizontal cracks breaking the plates."},
    {"name": "flakes", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Layered flaking inside the plates: stepped rims parallel to the plate edge."},
    {"name": "lichen", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Pale lichen patches on the plates."},
    {"name": "moss", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Moss in the furrows."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Grey-brown oak-like plates with deep furrows and some lichen.", "values": {}},
    "pine_plates": {"description": "Reddish pine plates with dark furrows and flaky checks.",
                    "values": {"ridges_across": 5, "plate_length": 2, "furrow_width": 0.08, "cross_checks": 0.6,
                               "lichen": 0.0, "flakes": 0.9}},
    "ash_ridges": {"description": "Grey interlaced ridges in a diamond net.",
                   "values": {"pattern": 1, "ridges_across": 8, "furrow_depth": 0.6, "lichen": 0.3}},
    "cedar_stringy": {"description": "Red-brown stringy fibres in long strips.",
                      "values": {"pattern": 2, "ridges_across": 10, "furrow_depth": 0.45, "cross_checks": 0.0,
                                 "lichen": 0.0}},
    "mossy_old": {"description": "Old dark bark with moss filling the furrows.",
                  "values": {"moss": 0.85, "lichen": 0.4, "furrow_width": 0.16, "ridges_across": 7}},
}
#: Plate colour, furrow colour, lichen colour and moss colour per preset (sRGB).
PALETTES = {
    "default": ("#6c635b", "#2a231e", "#9ea58e", "#4d6326"),
    "pine_plates": ("#94573a", "#2b201b", "#a3a68f", "#4f6428"),
    "ash_ridges": ("#7d7870", "#36302b", "#a7ad99", "#526628"),
    "cedar_stringy": ("#7c4632", "#3c2219", "#9d9a86", "#4e6227"),
    "mossy_old": ("#4f4741", "#1f1a16", "#93a084", "#44641f"),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The bark maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    plate_rgb, furrow_rgb, lichen_rgb, moss_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    across, rows = p["ridges_across"], p["plate_length"]
    warp_u = tk.fbm(width, height, 3, 3, tk.hash_u32(seed, 1), cells_y=2)
    warp_v = tk.fbm(width, height, 3, 3, tk.hash_u32(seed, 2), cells_y=2)
    pattern = p["pattern"]
    ids = [0] * (width * height)
    plate_edge = [1.0] * (width * height)
    if pattern == 0:
        cells = tk.voronoi(width, height, across, rows, tk.hash_u32(seed, 3), jitter=0.85)
        amount = 0.25 / across
        edge = tk.warp(cells["edge"], width, height, warp_u, warp_v, amount)
        ids = [cells["cell"][(round(y + amount * height * warp_v[y * width + x]) % height) * width
                             + round(x + amount * width * warp_u[y * width + x]) % width]
               for y in range(height) for x in range(width)]
        ridge = [tk.smoothstep(0.0, p["furrow_width"], e) for e in edge]
        plate_edge = edge
    elif pattern == 1:
        crest = tk.ridged(width, height, across, 3, tk.hash_u32(seed, 3), gain=0.45, cells_y=max(1, rows // 2))
        crest = tk.warp(crest, width, height, warp_u, warp_v, 0.3 / across)
        ridge = [tk.smoothstep(0.35 + p["furrow_width"], 0.85, c) for c in crest]
    else:
        strips = tk.fbm(width, height, across * 2, 3, tk.hash_u32(seed, 3), cells_y=1)
        strips = tk.warp(strips, width, height, warp_u, warp_v, 0.1 / across)
        ridge = [tk.smoothstep(-0.1 - p["furrow_width"], 0.25, s) for s in strips]
    fibres = tk.fbm(width, height, across * 6, 3, tk.hash_u32(seed, 4), cells_y=3)
    checks_field = tk.voronoi(width, height, max(2, across // 2), rows * 6, tk.hash_u32(seed, 5), jitter=0.8)["edge"]
    checks_field = tk.warp(checks_field, width, height, warp_v, warp_u, 0.02)
    patches = tk.fbm(width, height, 5, 4, tk.hash_u32(seed, 6))
    grit = tk.white_noise(width, height, tk.hash_u32(seed, 7))
    rng = tk.Rng(seed, 8)
    tones = [rng.uniform(-1.0, 1.0) for _ in range(across * rows)]
    depth, cross, lichen, moss = p["furrow_depth"], p["cross_checks"], p["lichen"], p["moss"]
    flakes = p["flakes"]
    red, green, blue, heights, rough = [], [], [], [], []
    for index in range(width * height):
        top = ridge[index]
        check = cross * (1.0 - tk.smoothstep(0.0, 0.05, checks_field[index])) * top
        steps = plate_edge[index] * 7.0 + 0.6 * fibres[index]
        rim = flakes * tk.smoothstep(0.75, 1.0, steps - int(steps)) * top if pattern == 0 else 0.0
        level = 1.0 - depth * (1.0 - top) + 0.16 * fibres[index] - 0.35 * check - 0.12 * rim \
            + 0.04 * flakes * min(plate_edge[index] * 3.0, 1.0) + 0.03 * (grit[index] - 0.5)
        heights.append(0.5 * level + 0.25)
        tone = 1.0 + 0.12 * tones[ids[index] % len(tones)] + 0.4 * fibres[index] + 0.1 * (grit[index] - 0.5)
        colour = [f + (pl - f) * top for pl, f in zip(plate_rgb, furrow_rgb)]
        colour = [c * tone * (1.0 - 0.55 * check) * (1.0 - 0.3 * rim) for c in colour]
        growth = lichen * tk.smoothstep(0.1, 0.35, patches[index] + 0.15 * grit[index]) * top
        if growth > 0.0:
            colour = [c + (l - c) * growth for c, l in zip(colour, lichen_rgb)]
        green_cover = moss * tk.smoothstep(0.35, 0.9, 1.0 - top + 0.3 * patches[index])
        if green_cover > 0.0:
            colour = [c + (m * (0.8 + 0.4 * grit[index]) - c) * green_cover for c, m in zip(colour, moss_rgb)]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        rough.append(0.86 + 0.1 * (1.0 - top) + 0.04 * grit[index] - 0.05 * growth)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.04, roughness=rough,
                     ao_radius=0.03, ao_strength=1.3, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
