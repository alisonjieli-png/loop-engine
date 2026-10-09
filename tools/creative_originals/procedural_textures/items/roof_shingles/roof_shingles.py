"""Staggered roof shingles: slate, asphalt or cedar, with square, round or pointed butts (tileable PBR maps).

The slope runs down the tile. Row r's shingles end at the butt line v = (r + 1) / rows and reach two rows up under
the rows above, and each row lies on top of the row below it, as shingles laid from the eaves upward do. A pixel
belongs to the first row, counting down from the butt line just below it, whose shingle covers it: the shingle's
butt may be cut round or pointed and neighbouring shingles leave a narrow keyway, so the shingle beneath shows
through. Shingle widths are equal (slate, asphalt) or random (cedar) and every row is offset, so joints break.
"""
from __future__ import annotations

import math
import sys
from bisect import bisect_right

import texkit as tk

IDENTITY = "roof_shingles"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.35, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "material", "type": "int", "default": 0, "minimum": 0, "maximum": 2,
     "meaning": "0 natural slate (cleft layers), 1 asphalt (mineral granules), 2 cedar shakes (split wood grain)."},
    {"name": "butt", "type": "int", "default": 0, "minimum": 0, "maximum": 2,
     "meaning": "Shape of the exposed lower edge: 0 square, 1 round (fish scale), 2 pointed."},
    {"name": "rows", "type": "int", "default": 8, "minimum": 3, "maximum": 20,
     "meaning": "Rows of shingles down the tile height."},
    {"name": "per_row", "type": "int", "default": 5, "minimum": 2, "maximum": 14,
     "meaning": "Shingles across the tile width in each row."},
    {"name": "width_variation", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Random shingle widths and row offsets, as split shakes have; 0 keeps equal widths offset by half."},
    {"name": "keyway", "type": "float", "default": 0.03, "minimum": 0.0, "maximum": 0.12,
     "meaning": "Gap between neighbouring shingles in a row, as a share of the mean shingle width."},
    {"name": "thickness", "type": "float", "default": 0.5, "minimum": 0.1, "maximum": 1.0,
     "meaning": "Height of the step at each butt."},
    {"name": "weathering", "type": "float", "default": 0.25, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Fading, streaks, lichen and moss."},
    {"name": "colour_variation", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spread of colour between shingles."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Blue-grey natural slate with square butts in staggered rows.", "values": {}},
    "asphalt_charcoal": {"description": "Charcoal and brown asphalt tabs with granules and wide keyways.",
                         "values": {"material": 1, "rows": 9, "per_row": 4, "keyway": 0.06, "thickness": 0.35,
                                    "weathering": 0.15, "colour_variation": 0.25}},
    "cedar_shakes": {"description": "Weathered cedar shakes of random widths with split grain and moss.",
                     "values": {"material": 2, "rows": 6, "per_row": 7, "width_variation": 0.8, "keyway": 0.05,
                                "thickness": 0.8, "weathering": 0.6, "colour_variation": 0.7}},
    "fishscale_slate": {"description": "Victorian fish-scale slate with round butts in two tones.",
                        "values": {"butt": 1, "rows": 9, "per_row": 6, "keyway": 0.02, "colour_variation": 0.8,
                                   "weathering": 0.1}},
    "pointed_green": {"description": "Green-grey slate with pointed butts, a decorative diamond course look.",
                      "values": {"butt": 2, "rows": 10, "per_row": 6, "keyway": 0.015, "thickness": 0.4,
                                 "colour_variation": 0.5, "weathering": 0.3}},
}
#: Shingle colours, keyway shadow, granule or grain accent, moss, lichen, base roughness per preset (sRGB).
PALETTES = {
    "default": (["#4d5560", "#565e69", "#454c56", "#5e6570", "#4a525c"], "#141619", "#6c7480", "#4d6a2b",
                "#cfd0c0", 0.68),
    "asphalt_charcoal": (["#3a3a3c", "#454342", "#4e4741", "#333436"], "#0d0d0e", "#7a7672", "#4d6a2b",
                         "#c8c9b8", 0.95),
    "cedar_shakes": (["#8a6b4e", "#7b5f45", "#95775a", "#6f5a48", "#857462"], "#1b140e", "#5f4632", "#4a6a2a",
                     "#d0d1bd", 0.88),
    "fishscale_slate": (["#5a5f66", "#7a5c5c", "#555a61", "#6d5355", "#60656c"], "#15171a", "#7c8088",
                        "#4d6a2b", "#cfd0c0", 0.66),
    "pointed_green": (["#5d6a60", "#56635a", "#667368", "#4f5b52", "#617064"], "#141815", "#7c887f", "#4d6a2b",
                      "#cfd0c0", 0.7),
}


def _rows(rows: int, per_row: int, variation: float, seed: int) -> list:
    """Per row: (left edges sorted in [0, 1), widths, offset); every row's widths sum to the tile width."""
    rng = tk.Rng(seed, 0x5E)
    layout = []
    for row in range(rows):
        widths = [math.exp(rng.gauss(0.0, 0.45 * variation)) for _ in range(per_row)]
        scale = 1.0 / sum(widths)
        widths = [w * scale for w in widths]
        offset = (0.5 * (row % 2) / per_row) * (1.0 - variation) + variation * rng.random()
        edges = []
        position = offset
        for w in widths:
            edges.append((position % 1.0, w))
            position += w
        edges.sort()
        layout.append(([e for e, _w in edges], [w for _e, w in edges]))
    return layout


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The shingle maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    colours_hex, keyway_hex, accent_hex, moss_hex, lichen_hex, base_rough = PALETTES[preset]
    palette = [tk.hex_rgb(code) for code in colours_hex]
    keyway_rgb, accent_rgb = tk.hex_rgb(keyway_hex), tk.hex_rgb(accent_hex)
    moss_rgb, lichen_rgb = tk.hex_rgb(moss_hex), tk.hex_rgb(lichen_hex)
    material, butt = p["material"], p["butt"]
    rows, per_row = p["rows"], p["per_row"]
    layout = _rows(rows, per_row, p["width_variation"], tk.hash_u32(seed, 1))
    exposure = 1.0 / rows
    depth = exposure * (0.0 if butt == 0 else 0.45)
    gap = p["keyway"] / per_row
    step, weathering, variation = p["thickness"], p["weathering"], p["colour_variation"]
    if material == 2:
        surface = tk.fbm(width, height, 6 * per_row, 4, tk.hash_u32(seed, 2), cells_y=max(2, rows // 2))
    else:
        surface = tk.fbm(width, height, max(2, per_row), 4, tk.hash_u32(seed, 2), cells_y=6 * rows)
    granules = tk.white_noise(width, height, tk.hash_u32(seed, 3))
    blotch = tk.fbm(width, height, 4, 4, tk.hash_u32(seed, 4))
    streaks = tk.fbm(width, height, 3 * per_row, 3, tk.hash_u32(seed, 5), cells_y=2)
    count = len(palette) - 1
    traits = {}
    floor = math.floor
    red, green, blue, heights, rough = [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        first = floor(v * rows)
        for x in range(width):
            index = y * width + x
            u = (x + 0.5) / width
            found, upper, slotted = None, None, False
            for row in (first - 1, first, first + 1, first + 2):
                edges, widths = layout[row % rows]
                slot = bisect_right(edges, u) - 1
                left, size = edges[slot], widths[slot]
                local = (u - left) % 1.0
                if local < 0.5 * gap or local > size - 0.5 * gap:
                    slotted = slotted or row >= first
                    continue
                centre = (local - 0.5 * size) / (0.5 * size - 0.5 * gap)
                if butt == 1:
                    lift = depth * (1.0 - math.sqrt(max(0.0, 1.0 - centre * centre)))
                elif butt == 2:
                    lift = depth * abs(centre)
                else:
                    lift = 0.0
                line = (row + 1) * exposure - lift
                above = line - v
                if above >= 0.0:
                    found = (row, slot, above, centre, local, size)
                    break
                upper = line
            heights_value = 0.1
            if found is None:
                colour = list(keyway_rgb)
                roughness = 0.95
                heights.append(heights_value)
                red.append(colour[0])
                green.append(colour[1])
                blue.append(colour[2])
                rough.append(roughness)
                continue
            row, slot, above, centre, local, size = found
            key = (row % rows, slot)
            trait = traits.get(key)
            if trait is None:
                code = tk.hash_u32(seed, *key)
                trait = tuple(tk.hash_float(code, k) for k in range(6))
                traits[key] = trait
            rise = tk.clamp(above / (2.0 * exposure))
            level = 0.3 + 0.5 * step * (1.0 - rise) + 0.012 * surface[index] + 0.02 * (trait[1] - 0.5)
            edge_gap = min(local - 0.5 * gap, size - 0.5 * gap - local) * width
            if edge_gap < 1.5:
                level -= 0.04 * (1.5 - edge_gap) / 1.5
            heights.append(level)
            pick = (trait[0] * variation + 0.5 * (1.0 - variation)) * count
            low = min(int(pick), count - 1)
            f = pick - low
            colour = [a + (b - a) * f for a, b in zip(palette[low], palette[low + 1])]
            if material == 1:
                g = granules[index]
                speck = accent_rgb if g > 0.85 else keyway_rgb if g < 0.12 else None
                tone = 0.9 + 0.2 * g
                colour = [c * tone for c in colour]
                if speck is not None:
                    colour = [c + (s - c) * 0.55 for c, s in zip(colour, speck)]
                shadow = 0.75 + 0.25 * tk.smoothstep(0.0, 0.35 * exposure, above)
                colour = [c * shadow for c in colour]
                roughness = base_rough + 0.04 * (g - 0.5)
            elif material == 2:
                grain = surface[index]
                crack = 1.0 if trait[4] < 0.4 and abs(local - (0.25 + 0.5 * trait[2]) * size) * width < 0.6 \
                    and above < exposure * (0.4 + 0.6 * trait[3]) else 0.0
                tone = 1.0 + 0.22 * grain + 0.05 * (granules[index] - 0.5) - 0.45 * crack
                colour = [(c + (a - c) * max(0.0, -grain) * 0.6) * tone for c, a in zip(colour, accent_rgb)]
                grey = weathering * (0.3 + 0.5 * trait[5])
                luma = 0.2126 * colour[0] + 0.7152 * colour[1] + 0.0722 * colour[2]
                colour = [c + (luma * 0.95 + 0.04 - c) * grey for c in colour]
                roughness = base_rough + 0.05 * grain
            else:
                cleft = surface[index]
                tone = 1.0 + 0.12 * cleft + 0.04 * (granules[index] - 0.5)
                colour = [c * tone for c in colour]
                if cleft > 0.35:
                    colour = [c + (a - c) * 0.25 for c, a in zip(colour, accent_rgb)]
                roughness = base_rough + 0.08 * cleft
            butt_shade = 1.0 - 0.18 * (1.0 - tk.smoothstep(0.0, 0.08 * exposure, above))
            if upper is not None:
                butt_shade *= 0.55 + 0.45 * tk.smoothstep(0.0, 0.18 * exposure * (0.5 + step), v - upper)
            if slotted:
                butt_shade *= 0.5
            colour = [c * butt_shade for c in colour]
            if weathering > 0.0:
                wash = weathering * tk.clamp(0.3 + 1.2 * streaks[index]) * 0.35
                colour = [c * (1.0 - wash * 0.5) for c in colour]
                lichen = weathering * tk.smoothstep(0.55, 0.7, blotch[index] + 0.35 * granules[index] * 0.5)
                colour = [c + (l - c) * lichen * 0.6 for c, l in zip(colour, lichen_rgb)]
                moss = weathering * tk.smoothstep(0.1, 0.5, -blotch[index]) * (1.0 - rise) * 0.8
                colour = [c + (m * (0.7 + 0.5 * granules[index]) - c) * moss for c, m in zip(colour, moss_rgb)]
                roughness += 0.08 * moss
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            rough.append(roughness + 0.04 * (trait[5] - 0.5))
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.025, roughness=rough,
                     ao_radius=0.02, ao_strength=1.1, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
