"""CRT phosphor mask: aperture grille, delta shadow mask or slot mask with scanlines, glowing RGB subpixels.

Three tube types, each a different arrangement of red, green and blue phosphor:

- aperture grille: continuous vertical stripes, R G B across each triad, crossed by two thin damper wire shadows;
- shadow mask: round dots on a triangular (delta) lattice, rows offset by half a dot, coloured
  (i + 2 * (j mod 2)) mod 3 so every triangle of neighbouring dots holds one dot of each colour;
- slot mask: stripes broken into short slots, with alternate triads shifted half a slot.

Every subpixel has a soft Gaussian profile; the electron beam adds scanlines, a Gaussian brightness profile across
each line. The picture on the screen is either flat white or a smooth procedural colour image, sampled per
subpixel. Triad, row and scanline counts are whole numbers across the tile, so the mask repeats exactly.

The emissive map is the lit screen; the albedo is the unlit phosphor layer, grey dots on a black matrix.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "crt_phosphor_mask"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.6]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.1, 0.9]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
    {"name": "emissive", "channels": 3, "colour_space": "srgb", "convention": "gltf_emissive"},
]
PARAMETERS = [
    {"name": "mask", "type": "int", "default": 0, "minimum": 0, "maximum": 2,
     "meaning": "0 aperture grille stripes, 1 delta shadow mask dots, 2 slot mask."},
    {"name": "triads_across", "type": "int", "default": 16, "minimum": 6, "maximum": 160,
     "meaning": "Red, green and blue triads across the tile."},
    {"name": "scanlines", "type": "int", "default": 16, "minimum": 4, "maximum": 240,
     "meaning": "Scanlines down the tile."},
    {"name": "scan_strength", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How dark the gaps between scanlines are."},
    {"name": "picture", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Blend from a flat white screen (0) to a colourful procedural picture (1)."},
    {"name": "spot", "type": "float", "default": 0.6, "minimum": 0.1, "maximum": 1.0,
     "meaning": "Size of each phosphor spot within its cell, with soft falloff."},
    {"name": "glow", "type": "float", "default": 0.9, "minimum": 0.1, "maximum": 1.0,
     "meaning": "Brightness of the lit phosphors in the emissive map."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo and the light in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Aperture grille: continuous RGB stripes with soft scanlines.", "values": {}},
    "shadow_mask_delta": {"description": "Delta shadow mask: round RGB dots in triangles, fine pitch.",
                          "values": {"mask": 1, "triads_across": 12, "scanlines": 20, "scan_strength": 0.3}},
    "slot_mask": {"description": "Slot mask: short staggered RGB slots, as on many consumer sets.",
                  "values": {"mask": 2, "triads_across": 14, "scanlines": 14}},
    "arcade_low_res": {"description": "Low-resolution arcade monitor: coarse slots, deep scanlines, a picture.",
                       "values": {"mask": 2, "triads_across": 8, "scanlines": 8, "scan_strength": 0.9,
                                  "picture": 1.0, "spot": 0.7}},
}
#: Heights (texture v) of the two damper wires that steady an aperture grille; their shadows cross the stripes.
DAMPER_HEIGHTS = (1.0 / 3.0, 2.0 / 3.0)
#: Phosphor primaries as emitted colours (sRGB), and the unlit phosphor and matrix colours (sRGB).
PHOSPHORS = ("#ff3018", "#34ff40", "#3050ff")
UNLIT = {"default": ("#5a5c60", "#0c0c0e"), "shadow_mask_delta": ("#606266", "#121214"),
         "slot_mask": ("#585a5e", "#0e0e10"), "arcade_low_res": ("#4c4e52", "#08080a")}


def delta_colour(i: int, j: int) -> int:
    """Phosphor colour (0 red, 1 green, 2 blue) of dot i in row j of a delta lattice whose odd rows are offset by
    half a dot: every triangle of neighbouring dots holds one of each colour."""
    return (i + 2 * (j % 2)) % 3


def _picture(width: int, height: int, seed: int) -> tuple:
    field = tk.fbm(width, height, 2, 4, tk.hash_u32(seed, 1))
    second = tk.fbm(width, height, 3, 3, tk.hash_u32(seed, 2))
    rgb = tk.ramp([0.5 + 0.8 * f for f in field], [(0.0, "#2040ff"), (0.25, "#10c0e0"), (0.45, "#ffffff"),
                                                   (0.6, "#ffd020"), (0.8, "#ff3060"), (1.0, "#8020c0")])
    shade = [0.75 + 0.5 * s for s in second]
    return tuple([min(1.0, c * s) for c, s in zip(channel, shade)] for channel in rgb)


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The CRT mask maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    phosphor_hex, matrix_hex = UNLIT[preset]
    unlit, matrix = tk.hex_rgb(phosphor_hex), tk.hex_rgb(matrix_hex)
    primaries = [tk.hex_rgb(code) for code in PHOSPHORS]
    mask, triads, lines = p["mask"], p["triads_across"], p["scanlines"]
    spot, glow, scan = p["spot"], p["glow"], p["scan_strength"]
    image = _picture(width, height, seed)
    mix = p["picture"]
    dots_across = 3 * triads
    rows = max(2, 2 * round(dots_across / math.sqrt(3.0) / 2.0))
    slot_rows = triads
    aspect = dots_across / rows
    sigma = 0.12 + 0.18 * spot
    grain = tk.white_noise(width, height, tk.hash_u32(seed, 3))
    red, green, blue, e_red, e_green, e_blue, heights, rough = [], [], [], [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        line = v * lines - math.floor(v * lines) - 0.5
        beam = 1.0 - scan * (1.0 - math.exp(-(line / 0.32) ** 2))
        for x in range(width):
            u = (x + 0.5) / width
            index = y * width + x
            if mask == 1:
                ry = v * rows - 0.5
                best, colour_index = 9.0, 0
                for j in (math.floor(ry), math.floor(ry) + 1):
                    offset = 0.5 * (j % 2)
                    rx = u * dots_across - offset - 0.5
                    for i in (math.floor(rx), math.floor(rx) + 1):
                        du, dv = rx - i, (ry - j) * aspect
                        distance = du * du + dv * dv
                        if distance < best:
                            best, colour_index = distance, delta_colour(i % dots_across, j % rows)
                strength = math.exp(-best / (2.0 * sigma * sigma * 1.6))
            else:
                t = u * dots_across
                column = math.floor(t)
                colour_index = int(column) % 3
                across = t - column - 0.5
                strength = math.exp(-(across * across) / (2.0 * sigma * sigma))
                if mask == 2:
                    triad = int(column) // 3
                    sv = v * slot_rows + 0.5 * (triad % 2)
                    along = sv - math.floor(sv) - 0.5
                    strength *= tk.smoothstep(0.5, 0.36, abs(along))
                else:
                    damper = min(abs(tk.wrap_delta(v - level)) for level in DAMPER_HEIGHTS)
                    strength *= tk.smoothstep(0.0, 0.006, damper)
            shown = image[colour_index][index] * mix + (1.0 - mix)
            level = 1.7 * glow * strength * beam * shown
            primary = primaries[colour_index]
            e_red.append(min(1.0, level * primary[0]))
            e_green.append(min(1.0, level * primary[1]))
            e_blue.append(min(1.0, level * primary[2]))
            tint = [m + (c - m) * strength for m, c in zip(matrix, unlit)]
            tint = [c * (0.92 + 0.12 * grain[index]) + 0.04 * strength * (q - 0.5) for c, q in zip(tint, primary)]
            red.append(tint[0])
            green.append(tint[1])
            blue.append(tint[2])
            heights.append(0.4 + 0.35 * strength + 0.02 * grain[index])
            rough.append(0.45 + 0.25 * strength + 0.04 * grain[index])
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    emissive = tk.grade((e_red, e_green, e_blue), p["hue_shift"], 1.0, 1.0)
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.12 / dots_across,
                     roughness=rough, emissive=emissive, ao_radius=0.5 / dots_across, ao_strength=0.6,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
