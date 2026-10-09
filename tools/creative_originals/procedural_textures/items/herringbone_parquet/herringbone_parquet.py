"""Herringbone, double herringbone and chevron parquet: tileable PBR maps from the standard library only.

Herringbone is built from rectangular blocks ``ratio`` widths long in an axis-aligned frame Q, where a point lies in
a horizontal block when (Qx - floor(Qy)) mod 2*ratio < ratio and in a vertical block otherwise. The frame is turned
45 degrees, Q = repeats * ratio * (u - v, u + v), so the zigzag runs down the tile and the pattern repeats exactly
on the square. Chevron uses columns of parallelogram boards whose ends are cut along the column lines, slanting up
and down in turn so the boards meet in V shapes. Each block may be split into parallel planks (double or triple
herringbone); grain runs along every plank's own axis: ring lines bent into cathedral arches, finer rings and pores.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "herringbone_parquet"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.12, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "pattern", "type": "int", "default": 0, "minimum": 0, "maximum": 1,
     "meaning": "0 herringbone (square block ends against the next block's side), 1 chevron (ends cut at 45 "
                "degrees so the blocks meet in a straight centre line)."},
    {"name": "ratio", "type": "int", "default": 5, "minimum": 2, "maximum": 8,
     "meaning": "Block length in block widths; chevron uses the nearest even number."},
    {"name": "planks", "type": "int", "default": 1, "minimum": 1, "maximum": 3,
     "meaning": "Planks laid side by side in each block: 1 single, 2 double, 3 triple herringbone or chevron."},
    {"name": "repeats", "type": "int", "default": 2, "minimum": 1, "maximum": 4,
     "meaning": "Times the pattern repeats across the tile; more repeats make smaller blocks."},
    {"name": "joint_width", "type": "float", "default": 0.025, "minimum": 0.0, "maximum": 0.1,
     "meaning": "Gap between planks in plank widths."},
    {"name": "bevel", "type": "float", "default": 0.04, "minimum": 0.0, "maximum": 0.2,
     "meaning": "Width of the bevelled plank edge (a V groove between planks) in plank widths."},
    {"name": "grain_contrast", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Strength of the ring lines and pore streaks."},
    {"name": "figure", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Waviness of the grain lines along each plank."},
    {"name": "colour_variation", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spread of tone between planks."},
    {"name": "gloss", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Finish: 0 matte oil, 1 glossy lacquer."},
    {"name": "wear", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Dull, lighter patches where the finish has worn."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Natural oak blocks in classic herringbone with a satin lacquer.", "values": {}},
    "double_walnut": {"description": "Dark walnut in double herringbone: pairs of narrow planks per block.",
                      "values": {"ratio": 3, "planks": 2, "grain_contrast": 0.6, "figure": 0.6, "gloss": 0.75,
                                 "colour_variation": 0.6}},
    "chevron_ash": {"description": "Pale ash chevron with long boards meeting in a straight centre line.",
                    "values": {"pattern": 1, "ratio": 6, "joint_width": 0.03, "bevel": 0.06, "grain_contrast": 0.4,
                               "figure": 0.25, "colour_variation": 0.35, "gloss": 0.45}},
    "smoked_rustic": {"description": "Smoked, oiled oak herringbone with wide bevels, strong grain and wear.",
                      "values": {"ratio": 4, "joint_width": 0.04, "bevel": 0.12, "grain_contrast": 0.8,
                                 "figure": 0.7, "colour_variation": 0.9, "gloss": 0.1, "wear": 0.5}},
}
#: Plank colours (light to dark), joint colour, ring line colour per preset (sRGB).
PALETTES = {
    "default": (["#c99d68", "#b88b56", "#d4aa76", "#a97c4b", "#c19461"], "#3a2a1c", "#8a5f35"),
    "double_walnut": (["#6b4a33", "#5a3c29", "#7a563b", "#4c3222", "#664530"], "#21160f", "#3a2517"),
    "chevron_ash": (["#dccbb0", "#d2bfa1", "#e3d4bb", "#c9b593", "#d8c6a8"], "#6a5a46", "#b39c78"),
    "smoked_rustic": (["#6e5238", "#5c432d", "#7d6044", "#4d3826", "#6a4e35"], "#1c140d", "#3b2a1b"),
}
SQRT2 = math.sqrt(2.0)


def _noise1(t: float, seed: int) -> float:
    """Smooth 1D value noise in -1..1 with unit lattice spacing."""
    i = math.floor(t)
    f = t - i
    a = tk.hash_float(seed, i) * 2.0 - 1.0
    b = tk.hash_float(seed, i + 1) * 2.0 - 1.0
    return a + (b - a) * tk.fade(f)


def _locate(u: float, v: float, pattern: int, ratio: int, repeats: int):
    """(block key, across 0..1, along in block widths, block length, end distance scale) of texture point (u, v)."""
    if pattern == 0:
        scale = repeats * ratio
        qx, qy = scale * (u - v), scale * (u + v)
        j = math.floor(qy)
        offset = qx - j
        span = 2 * ratio
        if offset % span < ratio:
            group = math.floor(offset / span)
            key = (0, j % scale, group % repeats)
            return key, qy - j, offset % span, ratio, 1.0
        i = math.floor(qx)
        offset = qy - i - 1.0
        group = math.floor(offset / span)
        key = (1, i % scale, group % repeats)
        return key, qx - i, offset % span, ratio, 1.0
    half = max(1, int(round(ratio / 2.0)))
    columns = 2 * repeats
    column_position = u * columns
    column = math.floor(column_position)
    local = column_position - column
    slope = 1.0 if column % 2 == 0 else -1.0
    boards = columns * half
    psi = v * boards - slope * local * half
    board = math.floor(psi)
    key = (2 + (column % 2), column % columns, board % boards)
    return key, psi - board, local * 2.0 * half, 2.0 * half, SQRT2 / 2.0


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The parquet maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    woods_hex, joint_hex, ring_hex = PALETTES[preset]
    woods = [tk.hex_rgb(code) for code in woods_hex]
    joint_rgb, ring_rgb = tk.hex_rgb(joint_hex), tk.hex_rgb(ring_hex)
    pattern, ratio, planks, repeats = p["pattern"], p["ratio"], p["planks"], p["repeats"]
    if pattern == 0:
        plank_width_tex = 1.0 / (repeats * ratio * SQRT2 * planks)
    else:
        half = max(1, int(round(ratio / 2.0)))
        plank_width_tex = 1.0 / (2 * repeats * half * SQRT2 * planks)
    pixel = 1.0 / (plank_width_tex * max(width, height))
    half_joint = p["joint_width"] * 0.5
    bevel = max(p["bevel"], 1e-6)
    contrast, figure, variation = p["grain_contrast"], p["figure"], p["colour_variation"]
    gloss, wear = p["gloss"], p["wear"]
    worn = tk.fbm(width, height, 3, 4, tk.hash_u32(seed, 3))
    speck = tk.white_noise(width, height, tk.hash_u32(seed, 4))
    base_rough = 0.62 - 0.42 * gloss
    traits = {}
    count = len(woods) - 1
    red, green, blue, heights, rough = [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        for x in range(width):
            index = y * width + x
            u = (x + 0.5) / width
            key, across, along, length, end_scale = _locate(u, v, pattern, ratio, repeats)
            position = across * planks
            plank = min(int(position), planks - 1)
            across_p = position - plank
            plank_key = key + (plank,)
            trait = traits.get(plank_key)
            if trait is None:
                code = tk.hash_u32(seed, *plank_key)
                block = tk.hash_u32(seed, *key)
                trait = (tk.hash_float(block, 1), tk.hash_float(code, 2) * 2.0 - 1.0, tk.hash_float(code, 3),
                         1.5 + 2.5 * tk.hash_float(code, 4), tk.hash_float(code, 5), tk.hash_float(code, 6) * 2 - 1,
                         tk.hash_float(code, 7) * 2.0 - 1.0, code)
                traits[plank_key] = trait
            side = min(across_p, 1.0 - across_p)
            end = min(along, length - along) * end_scale * planks
            edge = min(side, end) - half_joint
            t = edge / bevel
            profile = 0.0 if t <= 0.0 else 1.0 if t >= 1.0 else math.sqrt(1.0 - (1.0 - t) * (1.0 - t))
            along_p = along * planks
            reach = along_p / (length * planks) * 2.0 - 1.0 - trait[6] * 0.3
            grain = across_p + figure * trait[5] * 0.9 * reach * reach + 0.3 * trait[6] * reach \
                + 0.05 * figure * _noise1(along_p * 0.45, trait[7])
            lines = math.sin(math.tau * (trait[3] * grain + trait[2]))
            fine = math.sin(math.tau * (3.3 * trait[3] * grain + 2.0 * trait[2]))
            pores = _noise1(grain * 16.0, trait[7] + 2) * (0.6 + 0.4 * _noise1(along_p * 2.5, trait[7] + 3))
            ring = (max(0.0, lines) ** 4 * 0.85 + max(0.0, fine) ** 6 * 0.4) * contrast
            top = 0.82 + 0.03 * trait[5] + 0.02 * trait[6] * (across_p - 0.5) + 0.008 * contrast * pores
            level = 0.42 + (top - 0.42) * profile
            heights.append(level)
            pick = (trait[0] * variation + 0.5 * (1.0 - variation)) * count
            low = min(int(pick), count - 1)
            f = pick - low
            wood = [a + (b - a) * f for a, b in zip(woods[low], woods[low + 1])]
            tone = 1.0 + 0.08 * trait[1] * variation + 0.06 * contrast * pores + 0.03 * (speck[index] - 0.5)
            wood = [(c + (r - c) * ring * 0.7) * tone for c, r in zip(wood, ring_rgb)]
            scuff = wear * tk.smoothstep(0.1, 0.55, worn[index])
            wood = [c + (0.78 - c) * 0.18 * scuff for c in wood]
            cover = tk.smoothstep(-pixel, pixel, edge)
            groove = 1.0 - 0.25 * (1.0 - profile) * cover
            colour = [(j + (w * groove - j) * cover) for j, w in zip(joint_rgb, wood)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            plank_rough = base_rough + 0.06 * trait[4] + 0.35 * scuff + 0.05 * ring + 0.1 * (1.0 - profile)
            rough.append(0.95 + (plank_rough - 0.95) * cover)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.01, roughness=rough,
                     ao_radius=0.012, ao_strength=0.9, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
