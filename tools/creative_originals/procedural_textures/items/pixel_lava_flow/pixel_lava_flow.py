"""Pixel-art lava: dark crust plates over glowing cracks, with an emissive map, tileable (standard library only).

Crust plates are the cells of a Voronoi diagram on a small art grid (``art_pixels`` square); the border distance in
art pixels decides what is molten: the middle of a crack is a pale core, the rest of the crack orange, and a dithered
one-pixel band of dull red rims each plate. ``crust`` shrinks the plates to islands around their seed points, which
turns the cracks into a lava lake where bubbles (a dark ring around a bright pixel) rise. On the crust, pixels whose
left or upper neighbour is molten take the plate's lit edge colour and pixels whose right or lower neighbour is
molten its shadow, so each plate reads as a raised slab. The emissive map holds the glow alone; the albedo keeps
the glowing colours as well, since 2D engines show albedo directly. The art is enlarged with nearest-neighbour
sampling; heights, normals and occlusion are computed per art pixel.
"""
from __future__ import annotations

import sys

import texkit as tk

IDENTITY = "pixel_lava_flow"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.98]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.25, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
    {"name": "emissive", "channels": 3, "colour_space": "srgb", "convention": "gltf_emissive"},
]
PARAMETERS = [
    {"name": "art_pixels", "type": "int", "default": 32, "minimum": 16, "maximum": 64,
     "meaning": "Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling."},
    {"name": "plates", "type": "int", "default": 3, "minimum": 2, "maximum": 8,
     "meaning": "Crust plates across the tile."},
    {"name": "crack_width", "type": "float", "default": 0.9, "minimum": 0.5, "maximum": 3.0,
     "meaning": "Half width of the molten cracks in art pixels."},
    {"name": "crust", "type": "float", "default": 1.0, "minimum": 0.2, "maximum": 1.0,
     "meaning": "Plate size: 1 fills the cells up to the cracks, lower values leave islands in a lava lake."},
    {"name": "bubbles", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Density of bubbles in wide molten areas."},
    {"name": "hot_spots", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Glowing specks on the crust."},
    {"name": "relief", "type": "float", "default": 1.0, "minimum": 0.2, "maximum": 2.0,
     "meaning": "Strength of the per-pixel normal map."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo and the glow in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Black basalt plates over bright orange cracks.", "values": {}},
    "cooling": {"description": "Grey cooling crust with thin dull-red cracks.",
                "values": {"crack_width": 0.55, "hot_spots": 0.05, "plates": 4}},
    "lava_lake": {"description": "A bubbling orange lake with small floating crust islands.",
                  "values": {"crust": 0.45, "bubbles": 0.7, "plates": 3, "hot_spots": 0.4}},
    "toxic_magma": {"description": "Fantasy green-yellow magma under violet crust.",
                    "values": {"crack_width": 1.1, "plates": 3, "hot_spots": 0.3}},
}
#: Per preset: crust shadow, crust, crust light, rim glow, molten, core and bubble ring (sRGB).
PALETTES = {
    "default": ("#1a1414", "#2c2321", "#4a3b35", "#8a1a0c", "#f2620f", "#ffd54a", "#b8380a"),
    "cooling": ("#2a2827", "#3d3a38", "#5c5753", "#5e1610", "#a8280f", "#e2621c", "#7c2010"),
    "lava_lake": ("#1d1514", "#33251f", "#55413a", "#9c2410", "#ff7a14", "#ffe066", "#c9480c"),
    "toxic_magma": ("#1c1424", "#30223d", "#4c3a5e", "#3f6e12", "#8fd61e", "#f2ff7a", "#5a9a14"),
}
#: Emission scale of the rim, molten area, core and hot spots.
GLOW = (0.45, 0.85, 1.0, 0.7)
#: Roughness of crust, rim, molten area and core.
ROUGHNESS = (0.9, 0.7, 0.4, 0.3)


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The lava maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    dark, crust, lit, rim, molten, core, ring = (tk.hex_rgb(code) for code in PALETTES[preset])
    art = p["art_pixels"]
    count = art * art
    plates = min(p["plates"], art // 4)
    cells = tk.voronoi(art, art, plates, plates, tk.hash_u32(seed, 1), jitter=0.8)
    grain = tk.fbm(art, art, max(4, art // 4), 2, tk.hash_u32(seed, 2))
    to_pixels = art / plates
    half = p["crack_width"]
    island = 0.25 + 0.75 * p["crust"]
    # state: 0 crust, 1 rim, 2 molten, 3 core
    state = [0] * count
    for y in range(art):
        for x in range(art):
            index = y * art + x
            border = cells["edge"][index] * to_pixels
            inland = (island - cells["f1"][index]) * to_pixels if island < 1.0 else border
            depth = min(border, inland)
            if depth < half * 0.45:
                state[index] = 3
            elif depth < half:
                state[index] = 2
            elif depth < half + 0.8 and tk.bayer4(x, y) < 0.7:
                state[index] = 1
    colour, glow, heights, rough = [None] * count, [(0.0, 0.0, 0.0)] * count, [0.0] * count, [0.0] * count
    rng = tk.Rng(seed, 0x1A)
    for y in range(art):
        for x in range(art):
            index = y * art + x
            kind = state[index]
            if kind == 0:
                before = state[y * art + (x - 1) % art] >= 2 or state[((y - 1) % art) * art + x] >= 2
                after = state[y * art + (x + 1) % art] >= 2 or state[((y + 1) % art) * art + x] >= 2
                shade = lit if before and not after else dark if after else crust if grain[index] > -0.3 else dark
                colour[index], heights[index], rough[index] = shade, 0.62 + 0.05 * grain[index], ROUGHNESS[0]
                if grain[index] > 0.55 - 0.4 * p["hot_spots"] and rng.chance(p["hot_spots"] * 0.6):
                    colour[index], glow[index] = rim, tuple(GLOW[3] * c for c in rim)
            else:
                shade = (rim, molten, core)[kind - 1]
                colour[index] = shade
                glow[index] = tuple(GLOW[kind - 1] * c for c in shade)
                heights[index] = (0.42, 0.3, 0.26)[kind - 1]
                rough[index] = ROUGHNESS[kind]
    if p["bubbles"] > 0.0:
        for u, v in tk.poisson_points(min(0.5, 4.0 / art), tk.hash_u32(seed, 3)):
            x, y = int(u * art), int(v * art)
            index = y * art + x
            if state[index] < 2 or not rng.chance(p["bubbles"]):
                continue
            if any(state[((y + dy) % art) * art + (x + dx) % art] < 2 for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                continue
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                target = ((y + dy) % art) * art + (x + dx) % art
                colour[target], glow[target], heights[target] = ring, tuple(0.6 * c for c in ring), 0.4
            colour[index], glow[index], heights[index] = core, core, 0.45
    red, green, blue = ([c[k] for c in colour] for k in range(3))
    graded = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    albedo = tuple(tk.upscale_nearest(channel, art, art, width, height) for channel in graded)
    shine = tk.grade(tuple([g[k] for g in glow] for k in range(3)), p["hue_shift"], 1.0, 1.0)
    emissive = tuple(tk.upscale_nearest(channel, art, art, width, height) for channel in shine)
    normal = tk.upscale_nearest_bytes(tk.normal_map(heights, art, art, p["relief"] * 1.4 / art, directx_normal),
                                      3, art, art, width, height)
    occlusion = [round(value * 8.0) / 8.0 for value in tk.ambient_occlusion(heights, art, art, 1.5 / art, 0.8)]
    return tk.finish(width, height, MAPS, albedo=albedo, heights=tk.upscale_nearest(heights, art, art, width, height),
                     roughness=tk.upscale_nearest(rough, art, art, width, height),
                     ao=tk.upscale_nearest(occlusion, art, art, width, height), normal=normal, emissive=emissive,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
