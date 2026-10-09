"""Perforated metal sheet with alpha cut-outs: round, square, slot or hexagonal holes (standard library only).

Holes sit on a whole-number lattice so the sheet repeats: staggered round holes use a hexagonal lattice, the
others a square grid. The hole outline is a distance function in the hole's local coordinates (circle, rounded
square, stadium slot or hexagon); the albedo alpha is 0 inside and 1 on the metal, anti-aliased over a pixel. A
punching burr lifts a thin ring around every hole, and the sheet keeps a rolled grain. Paint, where present, is
dielectric; bare sheet is metal.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "perforated_metal"
MAPS = [
    {"name": "albedo", "channels": 4, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.1, 1.0]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "pattern", "type": "int", "default": 0, "minimum": 0, "maximum": 4,
     "meaning": "Holes: 0 staggered round, 1 straight round, 2 square, 3 slots, 4 hexagonal."},
    {"name": "holes_across", "type": "int", "default": 10, "minimum": 3, "maximum": 48,
     "meaning": "Holes across the tile."},
    {"name": "open_area", "type": "float", "default": 0.55, "minimum": 0.15, "maximum": 0.85,
     "meaning": "Hole size relative to the hole spacing."},
    {"name": "burr", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Raised punching burr around each hole."},
    {"name": "paint", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Paint coverage (0 bare metal, 1 painted)."},
    {"name": "grime", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Dirt and fingerprints on the sheet."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.0,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Stainless sheet with staggered round holes.", "values": {}},
    "square_black": {"description": "Black painted sheet with square holes.",
                     "values": {"pattern": 2, "paint": 1.0, "holes_across": 12, "open_area": 0.6}},
    "slotted_grille": {"description": "Aluminium grille with long slots.",
                       "values": {"pattern": 3, "holes_across": 8, "open_area": 0.5, "burr": 0.2}},
    "hex_speaker": {"description": "Fine hexagonal speaker mesh in dark grey paint.",
                    "values": {"pattern": 4, "holes_across": 19, "open_area": 0.78, "paint": 1.0, "burr": 0.1}},
    "straight_round_brass": {"description": "Brass sheet with round holes in straight rows.",
                             "values": {"pattern": 1, "holes_across": 8, "open_area": 0.45, "grime": 0.3}},
}
#: Metal and paint colours per preset (sRGB).
PALETTES = {
    "default": ("#c9ccd0", "#202224"),
    "square_black": ("#a5a9ad", "#1b1c1e"),
    "slotted_grille": ("#d9dcdf", "#202224"),
    "hex_speaker": ("#9ea2a6", "#3a3c40"),
    "straight_round_brass": ("#d6b465", "#202224"),
}


def _hole_distance(pattern: int, s: float, t: float, size: float) -> float:
    """Signed distance (negative inside) from local coordinates in cell units to the hole outline."""
    if pattern in (0, 1):
        return math.hypot(s, t) - size
    if pattern == 2:
        corner = size * 0.15
        qs, qt = abs(s) - (size - corner), abs(t) - (size - corner)
        return math.hypot(max(qs, 0.0), max(qt, 0.0)) + min(max(qs, qt), 0.0) - corner
    if pattern == 3:
        half_length = size * 1.6
        qs = max(abs(s) - (half_length - size * 0.45), 0.0)
        return math.hypot(qs, t) - size * 0.45
    hexagon = max(abs(t) * 0.8660254 + abs(s) * 0.5, abs(s))
    return hexagon - size


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The perforated sheet maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    metal, paint_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    pattern, columns = p["pattern"], p["holes_across"]
    staggered = pattern in (0, 4)
    rows = tk.hex_rows(columns) if staggered else columns
    size = 0.5 * p["open_area"] if pattern != 3 else 0.32 * p["open_area"]
    grain = tk.fbm(width, height, 4, 3, tk.hash_u32(seed, 1), cells_y=120)
    grime_field = tk.fbm(width, height, 4, 4, tk.hash_u32(seed, 2))
    pixel = columns / min(width, height)
    aspect = rows / columns
    paint, burr, grime = p["paint"], p["burr"], p["grime"]
    red, green, blue, alpha, heights, rough, metallic = [], [], [], [], [], [], []
    for y in range(height):
        fv = (y + 0.5) / height * rows
        j = int(fv) % rows
        base = y * width
        for x in range(width):
            index = base + x
            fu = (x + 0.5) / width * columns
            if staggered:
                shift = 0.5 * (j % 2)
                cu = fu - shift
                i = math.floor(cu)
                s = cu - i - 0.5
                t = (fv - math.floor(fv) - 0.5) / aspect
                # The hexagonal lattice also needs the neighbouring rows: take the nearest of three centres.
                best = (math.hypot(s, t), s, t)
                for dj in (-1, 1):
                    other_shift = 0.5 * ((j + dj) % 2)
                    ou = fu - other_shift
                    os_ = ou - math.floor(ou) - 0.5
                    ot = (fv - math.floor(fv) - 0.5 - dj) / aspect
                    candidate = math.hypot(os_, ot)
                    if candidate < best[0]:
                        best = (candidate, os_, ot)
                _, s, t = best
            else:
                s = fu - math.floor(fu) - 0.5
                t = fv - math.floor(fv) - 0.5
            distance = _hole_distance(pattern, s, t, size)
            solid = tk.smoothstep(-pixel * 0.5, pixel * 0.5, distance)
            ring = burr * max(0.0, 1.0 - abs(distance - 0.04) / 0.04) if distance > 0 else 0.0
            coat = paint
            colour = [c * (0.92 + 0.1 * grain[index]) for c in metal]
            colour = [c + (pc * (0.96 + 0.06 * grain[index]) - c) * coat for c, pc in zip(colour, paint_rgb)]
            dirt = grime * tk.smoothstep(-0.1, 0.35, grime_field[index]) * 0.35
            colour = [c * (1.0 - dirt) for c in colour]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            alpha.append(solid)
            heights.append(0.2 + 0.5 * solid + 0.2 * ring + 0.01 * grain[index])
            metal_share = 1.0 - coat
            metallic.append(metal_share)
            rough.append(metal_share * (0.32 + 0.06 * grain[index] + 0.3 * dirt) + coat * (0.55 + 0.2 * dirt))
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, alpha=alpha, heights=heights, depth=0.06 / columns,
                     roughness=rough, metallic=metallic, ao_radius=0.3 / columns, ao_strength=0.6,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
