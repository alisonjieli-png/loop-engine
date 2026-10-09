"""Opus vermiculatum mosaic: rows of small tesserae that follow the outlines of round motifs, tileable PBR maps.

Motifs are discs scattered on the torus. A pixel takes the nearest motif by signed distance phi = |p - c| - R, and
the tesserae are laid in rings of that motif: ring k holds the points with k * s <= phi < (k + 1) * s for the
tessera size s, and is cut into a whole number of tesserae by angle, so every ring closes on itself. Rings inside a
motif fill it, the first rings outside outline it, and the rest form the background, whose rows from neighbouring
motifs meet along irregular seams as in hand-laid mosaic. Every tessera is shrunk by a random amount on each side,
tilted a little and coloured from the design with its own jitter; gold smalti backgrounds are metallic.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "mosaic_tesserae"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.92]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.05, 1.0]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "motifs", "type": "int", "default": 5, "minimum": 1, "maximum": 16,
     "meaning": "Round motifs scattered over the tile."},
    {"name": "motif_size", "type": "float", "default": 0.09, "minimum": 0.03, "maximum": 0.2,
     "meaning": "Mean motif radius in tile widths."},
    {"name": "tessera_size", "type": "float", "default": 0.02, "minimum": 0.008, "maximum": 0.05,
     "meaning": "Side of one tessera in tile widths."},
    {"name": "grout_width", "type": "float", "default": 0.14, "minimum": 0.04, "maximum": 0.35,
     "meaning": "Joint between tesserae as a share of the tessera size."},
    {"name": "irregularity", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Random trimming and tilt of each tessera, as hand-cut pieces have."},
    {"name": "outline_rows", "type": "int", "default": 1, "minimum": 0, "maximum": 3,
     "meaning": "Rings of outline colour around each motif."},
    {"name": "relief", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Uneven heights of the tesserae in the bedding mortar."},
    {"name": "gloss", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0,
     "meaning": "0 matte stone tesserae, 1 glossy glass smalti."},
    {"name": "colour_variation", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spread of tone between tesserae of one colour."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Roman stone mosaic: cream background rows around ochre and red motifs with dark "
                               "outlines.", "values": {}},
    "gold_smalti": {"description": "Byzantine glass smalti: metallic gold background rows around blue and green "
                                   "motifs.",
                    "values": {"motifs": 7, "motif_size": 0.07, "tessera_size": 0.018, "gloss": 0.85,
                               "relief": 0.6, "outline_rows": 2}},
    "sea_rings": {"description": "Teal and blue rings rippling around small white motifs, no outline.",
                  "values": {"motifs": 9, "motif_size": 0.035, "tessera_size": 0.016, "outline_rows": 0,
                             "gloss": 0.5, "colour_variation": 0.6}},
    "earth_stone": {"description": "Large matte stone tesserae in earth tones with wide joints.",
                    "values": {"motifs": 3, "motif_size": 0.14, "tessera_size": 0.032, "grout_width": 0.2,
                               "irregularity": 0.8, "relief": 0.5, "gloss": 0.05, "colour_variation": 0.7}},
}
#: Background colours, outline colour, motif colours, grout colour, metallic background flag per preset (sRGB).
PALETTES = {
    "default": (["#e3d6bd", "#d9caae", "#ebe0ca"], "#3a2f28", ["#b5662f", "#9c3b2a", "#c9963f"], "#bdb2a0", 0.0),
    "gold_smalti": (["#c9a24a", "#d8b45a", "#b8913c"], "#1f2f5a", ["#2b4f9a", "#1f7a5c", "#3c63b0", "#8a2a3a"],
                    "#a69a86", 1.0),
    "sea_rings": (["#2f7f8f", "#3a92a0", "#256c80", "#2d5f8f", "#4aa1a8"], "#173f5a", ["#eef0ea", "#dfe8e6"],
                  "#c8c7bf", 0.0),
    "earth_stone": (["#a88c6c", "#94795b", "#b59b7a"], "#4a3a2c", ["#7a4a32", "#5f6a4a", "#c2a070"], "#b4a68f",
                    0.0),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The mosaic maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    background_hex, outline_hex, motif_hex, grout_hex, metallic_background = PALETTES[preset]
    background = [tk.hex_rgb(code) for code in background_hex]
    motif_colours = [tk.hex_rgb(code) for code in motif_hex]
    outline_rgb, grout_rgb = tk.hex_rgb(outline_hex), tk.hex_rgb(grout_hex)
    rng = tk.Rng(seed, 0x6D)
    size = p["tessera_size"]
    motifs = []
    spacing = max(0.06, 0.6 / math.sqrt(p["motifs"]))
    candidates = tk.poisson_points(min(0.5, spacing), tk.hash_u32(seed, 1))
    for k in range(p["motifs"]):
        cu, cv = candidates[k % len(candidates)]
        if k >= len(candidates):
            cu, cv = rng.random(), rng.random()
        radius = max(size * 1.5, p["motif_size"] * rng.uniform(0.7, 1.3))
        motifs.append((cu, cv, radius, rng.random()))
    half_grout = 0.5 * p["grout_width"]
    irregularity, relief, gloss, variation = p["irregularity"], p["relief"], p["gloss"], p["colour_variation"]
    outline_rows = p["outline_rows"]
    mortar = tk.fbm(width, height, 12, 3, tk.hash_u32(seed, 2))
    speck = tk.white_noise(width, height, tk.hash_u32(seed, 3))
    pixel = 1.0 / (size * width)
    tau = 2.0 * math.pi
    twists, tesserae = {}, {}
    red, green, blue, heights, rough, metal = [], [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        for x in range(width):
            index = y * width + x
            u = (x + 0.5) / width
            best = None
            for m, (cu, cv, radius, _tone) in enumerate(motifs):
                du, dv = tk.wrap_delta(u - cu), tk.wrap_delta(v - cv)
                distance = math.sqrt(du * du + dv * dv)
                phi = distance - radius
                if best is None or phi < best[0]:
                    best = (phi, m, du, dv, distance)
            phi, m, du, dv, distance = best
            radius = motifs[m][2]
            ring = math.floor(phi / size)
            across = phi / size - ring
            ring_radius = max(radius + (ring + 0.5) * size, 0.5 * size)
            pieces = max(1, int(round(tau * ring_radius / size)))
            angle = (math.atan2(dv, du) / tau) % 1.0
            twist = twists.get((m, ring))
            if twist is None:
                twist = twists[(m, ring)] = tk.hash_float(seed, m, ring, 7)
            position = (angle * pieces + twist) % pieces
            slot = int(position)
            along = position - slot
            trait = tesserae.get((m, ring, slot))
            if trait is None:
                code = tk.hash_u32(seed, m, ring, slot)
                trait = tesserae[(m, ring, slot)] = tuple(tk.hash_float(code, k) for k in range(11))
            trims = [0.12 * irregularity * trait[k] for k in range(4)]
            arc = tau * max(distance, 1e-6) / pieces / size
            side_a = (along - trims[0]) * arc
            side_b = (1.0 - along - trims[1]) * arc
            side_c = across - trims[2]
            side_d = 1.0 - across - trims[3]
            inside = (min(side_a, side_b) if pieces > 1 else 1.0)
            inside = min(inside, side_c, side_d) - half_grout
            if ring_radius <= 0.5 * size:
                inside = min(side_c, side_d) - half_grout + 0.5
            tilt_u = (trait[5] - 0.5) * relief
            tilt_v = (trait[6] - 0.5) * relief
            lift = 0.03 * relief * (trait[7] - 0.5)
            t = inside / 0.12
            profile = 0.0 if t <= 0.0 else 1.0 if t >= 1.0 else math.sqrt(1.0 - (1.0 - t) * (1.0 - t))
            top = 0.8 + lift + 0.03 * (tilt_u * (along - 0.5) + tilt_v * (across - 0.5))
            bed = 0.45 + 0.03 * mortar[index]
            level = bed + (top - bed) * profile
            heights.append(level)
            jitter = 1.0 + 0.14 * (trait[8] - 0.5) * 2.0 * variation
            metal_value = 0.0
            if ring < 0:
                colour = motif_colours[int(motifs[m][3] * len(motif_colours)) % len(motif_colours)]
                depth = tk.clamp(-(ring + 0.5) * size / radius)
                shade = (0.82 + 0.3 * depth) * (1.0 - 0.05 * ((-ring) % 2))
                colour = [c * shade for c in colour]
            elif ring < outline_rows:
                colour = outline_rgb
            else:
                colour = background[int(trait[9] * len(background)) % len(background)]
                metal_value = metallic_background
            colour = [c * jitter * (1.0 + 0.04 * (speck[index] - 0.5)) for c in colour]
            cover = tk.smoothstep(-pixel, pixel, inside)
            joint = [c * (0.85 + 0.25 * speck[index] + 0.05 * mortar[index]) for c in grout_rgb]
            colour = [g + (c - g) * cover for g, c in zip(joint, colour)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            tile_rough = 0.08 + 0.75 * (1.0 - gloss) + 0.06 * trait[10] + 0.15 * (1.0 - profile)
            rough.append(0.95 + (tile_rough - 0.95) * cover)
            metal.append(metal_value * cover)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.008, roughness=rough,
                     metallic=metal, ao_radius=0.01, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
