"""Wicker: round weavers passing over and under round stakes, with open gaps, tileable PBR maps with alpha.

Stakes run down the tile and weavers across it, both as round rods with whole counts, so the weave repeats. Every
weaver has a depth at each stake (over or under, from the weave pattern) and moves between stake centres along a
cosine ease, so it bends around the stakes. At each pixel the higher of the two rod surfaces is visible; where
neither rod covers the pixel the albedo alpha is zero, so the weave is open like a basket or a chair back. Reeds get
fibre streaks along their length, a tone each and occasional rattan nodes; painted wicker wears through to the reed
on its high points.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "wicker_weave"
MAPS = [
    {"name": "albedo", "channels": 4, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.92]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.3, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "pattern", "type": "int", "default": 0, "minimum": 0, "maximum": 2,
     "meaning": "0 randing (over one stake, under one), 1 double randing (weavers in pairs), 2 over two and under "
                "two, stepping one stake per row."},
    {"name": "stakes", "type": "int", "default": 10, "minimum": 4, "maximum": 32,
     "meaning": "Upright stakes across the tile; rounded up to keep the pattern repeating."},
    {"name": "weavers", "type": "int", "default": 22, "minimum": 6, "maximum": 64,
     "meaning": "Weavers down the tile; rounded up to keep the pattern repeating."},
    {"name": "stake_width", "type": "float", "default": 0.5, "minimum": 0.25, "maximum": 0.9,
     "meaning": "Stake diameter as a share of the stake spacing."},
    {"name": "weaver_width", "type": "float", "default": 0.88, "minimum": 0.5, "maximum": 1.0,
     "meaning": "Weaver diameter as a share of the weaver spacing; below 1 light shows between weavers."},
    {"name": "bulge", "type": "float", "default": 0.8, "minimum": 0.2, "maximum": 1.0,
     "meaning": "How far the weavers bend over and under the stakes."},
    {"name": "fibres", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Fibre streaks, tone differences and nodes along the reeds."},
    {"name": "paint_wear", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "On painted presets, how much of the paint has worn through to the reed on high points."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Natural honey rattan in plain randing.", "values": {}},
    "white_painted": {"description": "White-painted wicker with the paint worn through on the high points.",
                      "values": {"paint_wear": 0.45, "stakes": 12, "weavers": 26, "fibres": 0.3}},
    "dark_stained": {"description": "Espresso-stained wicker in double randing.",
                     "values": {"pattern": 1, "stakes": 8, "weavers": 28, "stake_width": 0.6, "bulge": 0.7}},
    "willow_twill": {"description": "Grey-brown willow, over two and under two, with wide gaps.",
                     "values": {"pattern": 2, "stakes": 16, "weavers": 20, "stake_width": 0.45,
                                "weaver_width": 0.7, "fibres": 0.7}},
}
#: Reed colour, paint colour (or None for unpainted), node colour, reed roughness and paint roughness per preset.
PALETTES = {
    "default": ("#c4924f", None, "#7a5226", 0.62, 0.5),
    "white_painted": ("#b08a5a", "#ece8df", "#7a5a38", 0.65, 0.45),
    "dark_stained": ("#4a2c18", None, "#26160b", 0.5, 0.5),
    "willow_twill": ("#8a7a62", None, "#4f4434", 0.72, 0.5),
}
#: Columns and rows after which each pattern repeats.
REPEATS = {0: (2, 2), 1: (2, 4), 2: (4, 4)}


def _over(pattern: int, stake: int, weaver: int) -> bool:
    """Whether the weaver passes in front of the stake."""
    if pattern == 0:
        return (stake + weaver) % 2 == 0
    if pattern == 1:
        return (stake + weaver // 2) % 2 == 0
    return (stake + weaver) % 4 < 2


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The wicker maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    reed_code, paint_code, node_code, reed_rough, paint_rough = PALETTES[preset]
    reed_rgb, node_rgb = tk.hex_rgb(reed_code), tk.hex_rgb(node_code)
    paint_rgb = tk.hex_rgb(paint_code) if paint_code else None
    pattern = p["pattern"]
    step_x, step_y = REPEATS[pattern]
    stakes = -(-p["stakes"] // step_x) * step_x
    weavers = -(-p["weavers"] // step_y) * step_y
    stake_space, weaver_space = 1.0 / stakes, 1.0 / weavers
    stake_radius = 0.5 * p["stake_width"] * stake_space
    weaver_radius = 0.5 * p["weaver_width"] * weaver_space
    amplitude = p["bulge"] * (stake_radius + weaver_radius)
    top = amplitude + weaver_radius
    fibres, wear = p["fibres"], p["paint_wear"]
    over = [[amplitude if _over(pattern, i, j) else -amplitude for i in range(stakes)] for j in range(weavers)]
    rng = tk.Rng(seed, 0x3C)
    stake_tone = [rng.uniform(-1.0, 1.0) for _ in range(stakes)]
    weaver_tone = [rng.uniform(-1.0, 1.0) for _ in range(weavers)]
    nodes = [(rng.random(), rng.random() < 0.6) for _ in range(weavers + stakes)]
    limit = max(4, min(width, height) // 2)
    streak_h = tk.value_noise(width, height, 5, min(limit, weavers * 9), tk.hash_u32(seed, 1))
    streak_v = tk.value_noise(width, height, min(limit, stakes * 9), 5, tk.hash_u32(seed, 2))
    chips = tk.fbm(width, height, min(limit, 24), 3, tk.hash_u32(seed, 3))
    pixel = 1.0 / min(width, height)
    heights, red, green, blue, alpha, rough = [], [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        wv = v * weavers
        j = int(wv) % weavers
        dv = (wv - math.floor(wv) - 0.5) * weaver_space
        weaver_cross = weaver_radius * weaver_radius - dv * dv
        depths = over[j]
        for x in range(width):
            u = (x + 0.5) / width
            index = y * width + x
            su = u * stakes
            i = int(su) % stakes
            du = (su - math.floor(su) - 0.5) * stake_space
            best, kind, edge = -10.0, 0, 0.0
            stake_cross = stake_radius * stake_radius - du * du
            if stake_cross > 0.0:
                best, kind = math.sqrt(stake_cross), 1
                edge = stake_radius - abs(du)
            if weaver_cross > 0.0:
                position = su - 0.5
                left = int(math.floor(position))
                t = position - left
                z0, z1 = depths[left % stakes], depths[(left + 1) % stakes]
                centre = z0 + (z1 - z0) * (0.5 - 0.5 * math.cos(math.pi * t))
                surface = centre + math.sqrt(weaver_cross)
                if surface > best:
                    best, kind = surface, 2
                    edge = weaver_radius - abs(dv)
            if kind == 0:
                heights.append(0.0)
                red.append(reed_rgb[0] * 0.3)
                green.append(reed_rgb[1] * 0.3)
                blue.append(reed_rgb[2] * 0.3)
                alpha.append(0.0)
                rough.append(1.0)
                continue
            level = 0.5 + 0.5 * best / top
            heights.append(level)
            alpha.append(tk.smoothstep(0.0, pixel, edge))
            if kind == 1:
                streak, tone = streak_v[index], stake_tone[i]
                node_position, has_node = nodes[weavers + i]
                along = v
            else:
                streak, tone = streak_h[index], weaver_tone[j]
                node_position, has_node = nodes[j]
                along = u
            node = 0.0
            if has_node and fibres > 0.0:
                gap = abs(tk.wrap_delta(along - node_position))
                node = fibres * (1.0 - tk.smoothstep(0.004, 0.012, gap))
            shade = 0.82 + 0.25 * (level - 0.5) + 0.1 * fibres * (streak - 0.5) + 0.06 * fibres * tone
            colour = [c * shade for c in reed_rgb]
            colour = [c + (n - c) * node for c, n in zip(colour, node_rgb)]
            roughness = reed_rough + 0.08 * fibres * streak
            if paint_rgb is not None:
                worn = wear * tk.smoothstep(0.62, 0.9, level + 0.25 * chips[index])
                painted = [pc * (0.9 + 0.1 * shade) for pc in paint_rgb]
                colour = [pc + (c - pc) * worn for pc, c in zip(painted, colour)]
                roughness = paint_rough + (roughness - paint_rough) * worn
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            rough.append(roughness)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, alpha=alpha, heights=heights, depth=2.0 * top,
                     roughness=rough, ao_radius=0.5 * weaver_space, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
