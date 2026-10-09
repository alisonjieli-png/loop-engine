"""Corduroy: parallel cut-pile wales over a ground weave, tileable PBR maps from the standard library only.

The wales run down the tile (along V), a whole number of them across, so the cloth repeats. Each wale is a rounded
cord of cut pile; between wales a narrow groove shows the ground weave as fine weft ridges. The pile is a grain of
fibre tips streaked along the wale, its lean shows as tone and gloss changes on the cord tops, and wear flattens and
lightens the tops in patches, as on knees and elbows. Thick-and-thin corduroy alternates wide and narrow wales.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "corduroy_wales"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.35, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "wales", "type": "int", "default": 14, "minimum": 4, "maximum": 48,
     "meaning": "Wales across the tile width: about 40 is pinwale or needlecord, 6 is wide wale; rounded up to an "
                "even count when wales alternate."},
    {"name": "groove", "type": "float", "default": 0.18, "minimum": 0.05, "maximum": 0.4,
     "meaning": "Width of the groove between wales as a share of the wale spacing."},
    {"name": "pile", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Strength of the cut-pile grain on the cords."},
    {"name": "sheen", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Lustre of the pile on the cord tops."},
    {"name": "wear", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Crushed, lighter cord tops in patches."},
    {"name": "alternate", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 0.7,
     "meaning": "Thick-and-thin corduroy: how much wider every other wale is than its neighbour."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Camel medium-wale corduroy.", "values": {}},
    "pinwale_navy": {"description": "Navy pinwale (needlecord) with fine, shallow grooves.",
                     "values": {"wales": 36, "groove": 0.14, "pile": 0.5, "sheen": 0.35}},
    "wide_wale_rust": {"description": "Rust wide-wale corduroy with worn, crushed cords.",
                       "values": {"wales": 6, "groove": 0.22, "pile": 0.75, "sheen": 0.4, "wear": 0.45}},
    "thick_thin_olive": {"description": "Olive thick-and-thin corduroy: wide and narrow wales alternate.",
                         "values": {"wales": 12, "alternate": 0.55, "groove": 0.16, "wear": 0.2}},
    "lustre_burgundy": {"description": "Burgundy lustrous needlecord with a velvet sheen.",
                        "values": {"wales": 24, "groove": 0.12, "pile": 0.35, "sheen": 0.9, "wear": 0.05}},
}
#: Pile colour, worn-top colour and groove (ground weave) colour per preset (sRGB).
PALETTES = {
    "default": ("#a07a4a", "#c39e6c", "#5a4126"),
    "pinwale_navy": ("#23304f", "#3e4f73", "#121a2c"),
    "wide_wale_rust": ("#8a4325", "#b8714a", "#4a2112"),
    "thick_thin_olive": ("#5b5a32", "#80804f", "#2f2f18"),
    "lustre_burgundy": ("#5e1424", "#8a2f42", "#2c0811"),
}


def _wale_columns(width: int, wales: int, alternate: float, groove: float) -> list:
    """Per pixel column: (wale index, position across the wale from 0 to 1, groove closeness from 0 to 1)."""
    columns = []
    pairs = wales // 2 if alternate > 0.0 else wales
    wide = (1.0 + alternate) / (2.0 if alternate > 0.0 else 1.0)
    for x in range(width):
        position = (x + 0.5) / width * pairs
        pair = int(position) % pairs
        local = position - math.floor(position)
        if alternate > 0.0:
            if local < wide:
                index, across = 2 * pair, local / wide
            else:
                index, across = 2 * pair + 1, (local - wide) / (1.0 - wide)
        else:
            index, across = pair, local
        edge = min(across, 1.0 - across)
        columns.append((index, across, 1.0 - tk.smoothstep(0.0, groove * 0.5, edge)))
    return columns


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The corduroy maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    pile_rgb, worn_rgb, groove_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    alternate = p["alternate"]
    wales = p["wales"] + (p["wales"] % 2 if alternate > 0.0 else 0)
    groove, pile, sheen, wear = p["groove"], p["pile"], p["sheen"], p["wear"]
    columns = _wale_columns(width, wales, alternate, groove)
    limit = max(4, min(width, height) // 2)
    grain = tk.fbm(width, height, min(limit, wales * 8), 2, tk.hash_u32(seed, 1), cells_y=min(limit, 96))
    streaks = tk.fbm(width, height, min(limit, wales * 3), 3, tk.hash_u32(seed, 2), cells_y=3)
    patches = tk.fbm(width, height, 3, 4, tk.hash_u32(seed, 3))
    weft = 120
    weft_fade = tk.smoothstep(2.5, 5.0, height / weft)
    rng = tk.Rng(seed, 4)
    wale_tone = [rng.uniform(-1.0, 1.0) for _ in range(wales)]
    tau = math.tau
    heights, red, green, blue, rough = [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        ridge = 0.5 + 0.5 * math.cos(tau * weft * v)
        base = y * width
        for x in range(width):
            index = base + x
            wale, across, in_groove = columns[x]
            centred = 2.0 * across - 1.0
            cord = (1.0 - centred * centred) ** 0.6
            crush = wear * tk.smoothstep(0.05, 0.5, patches[index]) * cord
            fibres = grain[index]
            top = cord * (1.0 - 0.35 * crush) + 0.06 * pile * fibres * cord
            level = 0.08 + 0.85 * top * (1.0 - in_groove) + 0.04 * weft_fade * ridge * in_groove
            heights.append(level)
            lean = streaks[index]
            lustre = sheen * cord * (0.6 + 0.4 * (lean + 0.5))
            shade = (0.8 + 0.2 * cord + 0.12 * pile * fibres + 0.035 * pile * lean + 0.04 * wale_tone[wale]
                     + 0.25 * lustre * (0.5 + 0.5 * fibres))
            colour = [c + (w - c) * crush for c, w in zip(pile_rgb, worn_rgb)]
            colour = [c * shade for c in colour]
            colour = [c + (g * (0.85 + 0.15 * ridge) - c) * in_groove for c, g in zip(colour, groove_rgb)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            rough.append(0.9 - 0.45 * lustre - 0.12 * crush + 0.04 * pile * fibres + 0.05 * in_groove)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.32 / wales, roughness=rough,
                     ao_radius=0.35 / wales, ao_strength=1.2, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
