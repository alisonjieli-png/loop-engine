"""Water caustics: light focused by a wavy surface onto a pool floor or sea bed, tileable maps (standard library).

The water surface is a tileable height field: two fractal gradient noises on lattices of n and n + 1 cells (so
neither lattice's axes show) with a steep spectrum, plus fine ripples. Light falls straight down
and refracts at the surface; for gentle slopes the ray lands displaced against the surface gradient, by an amount
that grows with the water depth (paraxial refraction). A regular grid of four rays per output pixel is traced to the
floor and every ray adds its energy to the four floor pixels around its landing point (bilinear splatting with
wrap-around), so the floor brightness is the ray density: bright where curved crests focus light into lines and
knots, dim where troughs spread it. Because the surface, the ray grid and the landing points all wrap, the caustic
pattern tiles.

The emissive map holds the focused light; albedo, height and roughness describe the floor under it: glazed pool
tiles with grout, rippled sand, rough rock or a plain grey card for a light cookie.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "water_caustics"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.03, 0.92]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.1, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
    {"name": "emissive", "channels": 3, "colour_space": "srgb", "convention": "gltf_emissive"},
]
PARAMETERS = [
    {"name": "wave_cells", "type": "int", "default": 3, "minimum": 1, "maximum": 8,
     "meaning": "Main wave features across the tile; more cells give a finer caustic web."},
    {"name": "focus", "type": "float", "default": 0.55, "minimum": 0.05, "maximum": 1.0,
     "meaning": "Water depth times refraction strength: low gives soft blotches, high sharp folded lines."},
    {"name": "ripples", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Fine ripples on the surface that break the web into smaller cells."},
    {"name": "light", "type": "float", "default": 0.8, "minimum": 0.1, "maximum": 1.0,
     "meaning": "Brightness of the focused light in the emissive map."},
    {"name": "floor", "type": "int", "default": 0, "minimum": 0, "maximum": 3,
     "meaning": "Floor under the water: 0 pool tiles, 1 rippled sand, 2 rough rock, 3 plain grey card."},
    {"name": "tiles_across", "type": "int", "default": 8, "minimum": 2, "maximum": 24,
     "meaning": "Pool tiles across the tile (floor 0)."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo and the light in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Swimming pool: sharp bright web over pale blue glazed tiles.", "values": {}},
    "sandy_shallows": {"description": "Tropical shallows: turquoise light over rippled sand, finer web.",
                       "values": {"floor": 1, "wave_cells": 4, "focus": 0.7, "ripples": 0.45}},
    "deep_reef": {"description": "Deeper water: soft, dim blue caustics over dark rock.",
                  "values": {"floor": 2, "wave_cells": 2, "focus": 0.3, "light": 0.5, "ripples": 0.15}},
    "light_cookie": {"description": "High-contrast caustic light on a plain grey card, for projecting as light.",
                     "values": {"floor": 3, "focus": 0.85, "light": 1.0, "ripples": 0.25}},
}
#: Per preset: floor colour, second floor colour (grout, ripple trough or rock vein) and the light colour (sRGB).
PALETTES = {
    "default": ("#86bfd0", "#4f7f8e", "#e8fbff"),
    "sandy_shallows": ("#d8c49a", "#b09a70", "#c8fff0"),
    "deep_reef": ("#3a4a50", "#20282c", "#80b8ff"),
    "light_cookie": ("#6a6a6a", "#5a5a5a", "#ffffff"),
}


def _gradient(field: list, width: int, height: int) -> tuple:
    """Wrap-around central differences in field units per texture unit."""
    gx, gy = [], []
    for y in range(height):
        row = field[y * width:(y + 1) * width]
        above = field[((y - 1) % height) * width:((y - 1) % height + 1) * width]
        below = field[((y + 1) % height) * width:((y + 1) % height + 1) * width]
        right, left = row[1:] + row[:1], row[-1:] + row[:-1]
        gx.extend([(r - l) * 0.5 * width for r, l in zip(right, left)])
        gy.extend([(b - a) * 0.5 * height for b, a in zip(below, above)])
    return gx, gy


def caustic_density(surface: list, width: int, height: int, displacement: float) -> list:
    """Floor brightness under a height field: rays land displaced by -displacement * gradient (texture units) and
    are splatted bilinearly with wrap-around, four rays per pixel. 1.0 is the brightness of undisturbed light."""
    gx, gy = _gradient(surface, width, height)
    accumulator = [0.0] * (width * height)
    scale_x, scale_y = -displacement * width, -displacement * height
    floor = math.floor
    for y in range(height):
        down = ((y + 1) % height) * width
        base = y * width
        for x in range(width):
            index = base + x
            right = base + (x + 1) % width
            corner = down + (x + 1) % width
            below = down + x
            for ox, oy, ax, ay in ((0.0, 0.0, gx[index], gy[index]),
                                   (0.5, 0.0, 0.5 * (gx[index] + gx[right]), 0.5 * (gy[index] + gy[right])),
                                   (0.0, 0.5, 0.5 * (gx[index] + gx[below]), 0.5 * (gy[index] + gy[below])),
                                   (0.5, 0.5, 0.25 * (gx[index] + gx[right] + gx[below] + gx[corner]),
                                    0.25 * (gy[index] + gy[right] + gy[below] + gy[corner]))):
                px = x + ox + scale_x * ax
                py = y + oy + scale_y * ay
                x0, y0 = floor(px), floor(py)
                fx, fy = px - x0, py - y0
                i0, i1 = x0 % width, (x0 + 1) % width
                r0, r1 = (y0 % height) * width, ((y0 + 1) % height) * width
                accumulator[r0 + i0] += (1.0 - fx) * (1.0 - fy)
                accumulator[r0 + i1] += fx * (1.0 - fy)
                accumulator[r1 + i0] += (1.0 - fx) * fy
                accumulator[r1 + i1] += fx * fy
    # a light [1 2 1] filter across rows and columns removes the splatting grain
    out = []
    for y in range(height):
        row = accumulator[y * width:(y + 1) * width]
        out.extend([0.0625 * (l + r) + 0.125 * c for l, c, r in zip(row[-1:] + row[:-1], row, row[1:] + row[:1])])
    final = []
    for y in range(height):
        row = out[y * width:(y + 1) * width]
        above = out[((y - 1) % height) * width:((y - 1) % height + 1) * width]
        below = out[((y + 1) % height) * width:((y + 1) % height + 1) * width]
        final.extend([0.5 * c + 0.25 * (a + b) for a, c, b in zip(above, row, below)])
    return final


def _floor(kind: int, width: int, height: int, seed: int, tiles: int) -> tuple:
    """(mix toward the second floor colour, height, roughness) of the floor type."""
    grain = tk.fbm(width, height, 16, 3, tk.hash_u32(seed, 21))
    mix, heights, rough = [], [], []
    if kind == 0:
        pixel = 1.0 / min(width, height)
        joint = 0.035
        for y in range(height):
            fy = ((y + 0.5) / height * tiles) % 1.0
            dy = min(fy, 1.0 - fy) / tiles
            for x in range(width):
                fx = ((x + 0.5) / width * tiles) % 1.0
                edge = min(min(fx, 1.0 - fx) / tiles, dy)
                inside = tk.smoothstep(joint / tiles - pixel, joint / tiles + pixel, edge)
                n = grain[y * width + x]
                mix.append(1.0 - inside + 0.08 * n)
                heights.append(0.35 + 0.45 * tk.smoothstep(0.0, 0.12 / tiles, edge) + 0.02 * n)
                rough.append(0.85 - 0.6 * inside + 0.04 * n)
    elif kind == 1:
        warp = tk.fbm(width, height, 3, 3, tk.hash_u32(seed, 22))
        for y in range(height):
            for x in range(width):
                n = grain[y * width + x]
                phase = 9.0 * ((x + 0.5) / width + 0.35 * (y + 0.5) / height) + 1.6 * warp[y * width + x]
                ripple = 0.5 + 0.5 * math.sin(math.tau * phase)
                mix.append(0.6 * (1.0 - ripple) + 0.2 * n)
                heights.append(0.3 + 0.45 * ripple + 0.08 * n)
                rough.append(0.88 + 0.06 * n)
    elif kind == 2:
        rock = tk.ridged(width, height, 5, 5, tk.hash_u32(seed, 23))
        for index in range(width * height):
            n = grain[index]
            mix.append(0.8 * (1.0 - rock[index]) + 0.15 * n)
            heights.append(0.15 + 0.75 * rock[index] + 0.05 * n)
            rough.append(0.72 + 0.12 * n)
    else:
        for index in range(width * height):
            n = grain[index]
            mix.append(0.5 + 0.5 * n)
            heights.append(0.5 + 0.3 * n)
            rough.append(0.8 + 0.1 * n)
    return mix, heights, rough


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The caustic maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    floor_hex, second_hex, light_hex = PALETTES[preset]
    cells = p["wave_cells"]
    surface = tk.fbm(width, height, cells, 3, tk.hash_u32(seed, 1), gain=0.3)
    other = tk.fbm(width, height, cells + 1, 2, tk.hash_u32(seed, 3), gain=0.3)
    surface = [s + 0.5 * o for s, o in zip(surface, other)]
    if p["ripples"] > 0.0:
        fine = tk.fbm(width, height, 4 * cells, 2, tk.hash_u32(seed, 2), gain=0.3)
        surface = [s + 0.06 * p["ripples"] * f for s, f in zip(surface, fine)]
    density = caustic_density(surface, width, height, p["focus"] * 0.16 / (cells * cells))
    light_colour = tk.hex_rgb(light_hex)
    strength = p["light"]
    glow = [strength * min(1.0, max(0.0, d - 0.7) * 0.5) ** 0.8 for d in density]
    emissive = tuple([c * g for g in glow] for c in light_colour)
    mix, heights, rough = _floor(p["floor"], width, height, seed, p["tiles_across"])
    albedo = tk.mix_rgb(tk.hex_rgb(floor_hex), tk.hex_rgb(second_hex), [tk.clamp(m) for m in mix])
    albedo = tk.grade(albedo, p["hue_shift"], p["saturation"], p["brightness"])
    emissive = tk.grade(emissive, p["hue_shift"], 1.0, 1.0)
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.012, roughness=rough,
                     emissive=emissive, ao_radius=0.02, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
