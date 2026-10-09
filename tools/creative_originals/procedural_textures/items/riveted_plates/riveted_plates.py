"""Riveted metal plates: hull, tank or airframe panels with rivet rows and streaks (standard library only).

The tile is a grid of plates; each plate sits at its own small height, so every seam shows a step as in lapped
plating, and each takes its own tone. Rivets run in rows just inside every plate edge, as domed heads (or nearly
flush heads for airframes). Rust or dirt streaks run down from each rivet: every column is swept downward with a
fading trail, twice around so the trail wraps. Paint wears through on rivet heads and plate edges.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "riveted_plates"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.12, 1.0]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "plates_across", "type": "int", "default": 2, "minimum": 1, "maximum": 8,
     "meaning": "Plates across the tile."},
    {"name": "plate_rows", "type": "int", "default": 2, "minimum": 1, "maximum": 8,
     "meaning": "Plate rows down the tile."},
    {"name": "rivets_per_edge", "type": "int", "default": 9, "minimum": 2, "maximum": 30,
     "meaning": "Rivets along each plate edge."},
    {"name": "rivet_size", "type": "float", "default": 0.012, "minimum": 0.003, "maximum": 0.03,
     "meaning": "Rivet head radius in texture units."},
    {"name": "rivet_height", "type": "float", "default": 0.8, "minimum": 0.05, "maximum": 1.0,
     "meaning": "Rivet head height (low values give flush rivets)."},
    {"name": "paint", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Paint coverage (0 bare metal plates)."},
    {"name": "streaks", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Rust or dirt streaks below the rivets."},
    {"name": "plate_variation", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Tone difference between plates."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.0,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Grey painted ship hull plating with rust streaks.", "values": {}},
    "steampunk_brass": {"description": "Bare brass plates with copper rivets.",
                        "values": {"paint": 0.0, "streaks": 0.15, "plates_across": 3, "plate_rows": 2,
                                   "rivets_per_edge": 7, "rivet_size": 0.015}},
    "airframe": {"description": "Aluminium aircraft skin with flush rivets.",
                 "values": {"paint": 0.0, "rivet_height": 0.12, "rivet_size": 0.005, "rivets_per_edge": 18,
                            "streaks": 0.1, "plates_across": 3, "plate_rows": 4, "plate_variation": 0.6}},
    "rusty_tank": {"description": "Dark iron tank with heavy rust runs.",
                   "values": {"paint": 0.4, "streaks": 0.9, "plate_variation": 0.6}},
}
#: Plate metal, rivet metal, paint, streak colour per preset (sRGB).
PALETTES = {
    "default": ("#9ea3a8", "#a3a8ad", "#6f767c", "#7a3e1d"),
    "steampunk_brass": ("#d4ae5c", "#d79a6c", "#6f767c", "#5d4524"),
    "airframe": ("#cfd3d6", "#bcc1c5", "#9aa0a6", "#4e4a42"),
    "rusty_tank": ("#6e6f70", "#77787a", "#3c4a3e", "#7f3c18"),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The riveted plate maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    plate_rgb, rivet_rgb, paint_rgb, streak_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    count = width * height
    across, down = p["plates_across"], p["plate_rows"]
    rng = tk.Rng(seed, 1)
    plates = [(rng.uniform(-1.0, 1.0), rng.uniform(-1.0, 1.0)) for _ in range(across * down)]
    rivets = [0.0] * count
    size = p["rivet_size"]
    per_edge = p["rivets_per_edge"]
    margin = max(size * 2.2, 0.012)
    for j in range(down):
        for i in range(across):
            left, top = i / across, j / down
            plate_w, plate_h = 1.0 / across, 1.0 / down
            spots = []
            for k in range(per_edge):
                f = (k + 0.5) / per_edge
                spots += [(left + margin, top + f * plate_h), (left + plate_w - margin, top + f * plate_h),
                          (left + f * plate_w, top + margin), (left + f * plate_w, top + plate_h - margin)]
            for su, sv in spots:
                tk.stamp(rivets, width, height, su % 1.0, sv % 1.0, size, size,
                         lambda s, t: math.sqrt(max(0.0, 1.0 - s * s - t * t)) if s * s + t * t < 1.0 else None)
    keep = math.exp(-1.0 / (0.12 * height))
    trails = [0.0] * count
    for x in range(width):
        column = rivets[x::width]
        trail, values = 0.0, [0.0] * height
        for _round in range(2):
            for y in range(height):
                trail = max(column[y], trail * keep)
                values[y] = trail
        trails[x::width] = values
    streak_noise = tk.fbm(width, height, 48, 2, tk.hash_u32(seed, 2), cells_y=3)
    mottle = tk.fbm(width, height, 4, 4, tk.hash_u32(seed, 3))
    wear_noise = tk.fbm(width, height, 20, 3, tk.hash_u32(seed, 4))
    pixel = 1.0 / min(width, height)
    paint, streaks, variation = p["paint"], p["streaks"], p["plate_variation"]
    red, green, blue, heights, rough, metallic = [], [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        j = min(int(v * down), down - 1)
        local_v = v * down - j
        base = y * width
        for x in range(width):
            index = base + x
            u = (x + 0.5) / width
            i = min(int(u * across), across - 1)
            local_u = u * across - i
            tone, lift = plates[j * across + i]
            edge = min(local_u / across, (1.0 - local_u) / across, local_v / down, (1.0 - local_v) / down)
            seam = 1.0 - tk.smoothstep(0.0, pixel * 1.5, edge)
            rivet = rivets[index]
            head = 1.0 if rivet > 0.0 else 0.0
            worn = tk.smoothstep(0.2, 0.6, wear_noise[index] + 0.6 * head * rivet + 0.4 * (1.0 - min(edge * 40, 1.0)))
            coat = paint * (1.0 - worn * 0.85)
            bare = rivet_rgb if head else plate_rgb
            bare = [c * (1.0 + 0.1 * variation * tone + 0.05 * mottle[index]) for c in bare]
            colour = [b + (pc * (1.0 + 0.08 * variation * tone + 0.06 * mottle[index]) - b) * coat
                      for b, pc in zip(bare, paint_rgb)]
            run = streaks * max(0.0, trails[index] - rivet) * (0.4 + 0.6 * (streak_noise[index] + 0.5))
            colour = [c + (sc - c) * min(0.8, run) for c, sc in zip(colour, streak_rgb)]
            colour = [c * (1.0 - 0.5 * seam) for c in colour]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            level = 0.45 + 0.04 * lift - 0.15 * seam + 0.35 * p["rivet_height"] * rivet + 0.01 * mottle[index]
            heights.append(level)
            metal_share = (1.0 - coat) * (1.0 - min(0.8, run))
            metallic.append(metal_share)
            rough.append(metal_share * (0.35 + 0.05 * mottle[index]) + (1.0 - metal_share) * (0.55 + 0.3 * run))
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.012, roughness=rough,
                     metallic=metallic, ao_radius=0.01, ao_strength=0.9, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
