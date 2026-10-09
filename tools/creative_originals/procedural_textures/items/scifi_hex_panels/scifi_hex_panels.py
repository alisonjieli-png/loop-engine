"""Science fiction hexagonal hull panels: bevels, insets, vents, lights and glowing seams (standard library only).

Panels are the cells of a hexagonal lattice (texkit.hex_points with an even row count, so the lattice repeats on a
square tile with a slight squash). The distance to the cell border gives a bevelled rim and an inset centre plate;
coordinates relative to the cell centre, wrapped on the torus, place details. A hash of each panel picks its type:
plain, vented (parallel slots), light (a glowing inset) or bolted (six bolts inside the corners). Seams can glow,
which the emissive map carries alone.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "scifi_hex_panels"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.92]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.1, 1.0]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
    {"name": "emissive", "channels": 3, "colour_space": "srgb", "convention": "gltf_emissive"},
]
PARAMETERS = [
    {"name": "hexes_across", "type": "int", "default": 7, "minimum": 3, "maximum": 26,
     "meaning": "Hexagons across the tile (7, 12, 14, 19 or 26 keep them closest to regular)."},
    {"name": "seam_width", "type": "float", "default": 0.05, "minimum": 0.01, "maximum": 0.2,
     "meaning": "Gap between panels, in hexagon widths."},
    {"name": "bevel", "type": "float", "default": 0.08, "minimum": 0.01, "maximum": 0.25,
     "meaning": "Width of the bevelled rim, in hexagon widths."},
    {"name": "light_share", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of panels with a glowing inset."},
    {"name": "vent_share", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of panels with vent slots."},
    {"name": "seam_glow", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Glow inside the seams."},
    {"name": "wear", "type": "float", "default": 0.25, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Scuffed paint on the rims, showing metal."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo and glow in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Light grey hull with cyan panel lights.", "values": {}},
    "dark_reactor": {"description": "Dark panels with orange glowing seams.",
                     "values": {"seam_glow": 0.9, "light_share": 0.05, "vent_share": 0.35}},
    "white_lab": {"description": "Clean white panels with fine seams and few details.",
                  "values": {"seam_width": 0.025, "light_share": 0.08, "vent_share": 0.1, "wear": 0.0,
                             "hexes_across": 12}},
    "military_olive": {"description": "Olive drab armour hexes, bolted and scuffed.",
                       "values": {"light_share": 0.0, "vent_share": 0.15, "wear": 0.7, "bevel": 0.12}},
}
#: Panel paint, metal, seam colour and glow colour per preset (sRGB).
PALETTES = {
    "default": ("#a9adb2", "#c9ccd0", "#222428", "#33d6ff"),
    "dark_reactor": ("#2b2d31", "#7d8084", "#0e0f11", "#ff7a1a"),
    "white_lab": ("#e6e8ea", "#c9ccd0", "#5c6066", "#7ad7ff"),
    "military_olive": ("#4f5537", "#9a9c98", "#1a1b16", "#d9ff7a"),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The hex panel maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    paint_rgb, metal_rgb, seam_rgb, glow_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    columns = p["hexes_across"]
    rows = tk.hex_rows(columns)
    points = tk.hex_points(columns, rows)
    cells = tk.voronoi(width, height, columns, rows, points=points)
    kinds = []
    for k in range(columns * rows):
        roll = tk.hash_float(k, seed, 1)
        kind = 2 if roll < p["light_share"] else 1 if roll < p["light_share"] + p["vent_share"] else \
            3 if roll < p["light_share"] + p["vent_share"] + 0.2 else 0
        kinds.append((kind, tk.hash_float(k, seed, 2), tk.hash_float(k, seed, 3) * math.pi))
    scuffs = tk.fbm(width, height, 24, 3, tk.hash_u32(seed, 4))
    mottle = tk.fbm(width, height, 5, 3, tk.hash_u32(seed, 5))
    pixel = columns / min(width, height)
    half_seam, bevel, wear, seam_glow = p["seam_width"] * 0.5, p["bevel"], p["wear"], p["seam_glow"]
    aspect = columns / rows
    red, green, blue, heights, rough, metallic, glow = [], [], [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        base = y * width
        for x in range(width):
            index = base + x
            u = (x + 0.5) / width
            cell = cells["cell"][index]
            edge = cells["edge"][index]
            kind, tone, angle = kinds[cell]
            du = tk.wrap_delta(u - points[0][cell] / columns) * columns
            dv = tk.wrap_delta(v - points[1][cell] / rows) * rows * aspect
            inside = edge - half_seam
            solid = tk.smoothstep(-pixel * 0.5, pixel * 0.5, inside)
            rim = tk.smoothstep(0.0, bevel, inside)
            inset_edge = inside - bevel * 2.2
            inset = tk.smoothstep(0.0, 0.02, inset_edge)
            level = 0.2 + 0.55 * rim * solid - 0.1 * inset
            detail_dark, light, bolt = 0.0, 0.0, 0.0
            if kind == 1 and inset > 0.5:
                along = du * math.cos(angle) + dv * math.sin(angle)
                slot = 0.5 + 0.5 * math.cos(math.tau * along * 7.0)
                vent = tk.smoothstep(0.55, 0.75, slot) * tk.smoothstep(0.02, 0.06, inset_edge)
                level -= 0.15 * vent
                detail_dark = vent
            elif kind == 2 and inset > 0.0:
                light = tk.smoothstep(0.02, 0.08, inset_edge)
            elif kind == 3:
                for k in range(6):
                    a = k * math.pi / 3.0 + math.pi / 6.0
                    distance = math.hypot(du - 0.3 * math.cos(a), dv - 0.3 * math.sin(a))
                    if distance < 0.05:
                        bolt = max(bolt, math.sqrt(1.0 - (distance / 0.05) ** 2))
                level += 0.12 * bolt
            scuffed = wear * (1.0 - rim + 0.3) * tk.smoothstep(0.1, 0.35, scuffs[index]) * solid
            scuffed = min(1.0, scuffed + bolt * 0.8)
            colour = [c * (1.0 + 0.08 * (tone - 0.5) + 0.04 * mottle[index]) for c in paint_rgb]
            colour = [c + (m - c) * scuffed for c, m in zip(colour, metal_rgb)]
            colour = [c * (1.0 - 0.6 * detail_dark) * (0.85 + 0.15 * rim) for c in colour]
            colour = [s + (c - s) * solid for c, s in zip(colour, seam_rgb)]
            if light > 0.0:
                colour = [c + (0.15 * g - c) * light for c, g in zip(colour, glow_rgb)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            heights.append(level + 0.01 * mottle[index])
            metallic.append(scuffed * solid)
            rough.append(0.5 - 0.2 * scuffed + 0.3 * detail_dark + 0.2 * (1.0 - solid) - 0.35 * light)
            seam_light = seam_glow * (1.0 - solid)
            glow.append(max(light, seam_light))
    glow_r = [g * glow_rgb[0] for g in glow]
    glow_g = [g * glow_rgb[1] for g in glow]
    glow_b = [g * glow_rgb[2] for g in glow]
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    emissive = tk.grade((glow_r, glow_g, glow_b), p["hue_shift"], 1.0, 1.0)
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.15 / columns,
                     roughness=rough, metallic=metallic, emissive=emissive, ao_radius=0.3 / columns,
                     ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
