"""Fish skin: round overlapping scales with growth rings, radial grooves, pigmented edges and iridescence.

Round (cycloid) scales sit in offset rows with whole counts across and down, so the skin tiles; the head is toward
the top. Each scale is set into the skin at its front, so the row above covers the front of the row below and only
the rear crescent of every scale shows. On a scale, fine ridges ring the growth centre (circuli) and grooves radiate
from it; the free rear edge carries a band of dark pigment, which draws the net-like pattern seen on carp. Silver
scales reflect with a colour that turns across each scale, a stylized stand-in for the thin-film sheen of guanine.
Per-scale colour fields add koi patches or trout spots.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "fish_scales"
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
    {"name": "columns", "type": "int", "default": 12, "minimum": 4, "maximum": 32,
     "meaning": "Scales across the tile; the row count follows from the exposure."},
    {"name": "exposure", "type": "float", "default": 0.42, "minimum": 0.25, "maximum": 0.7,
     "meaning": "Row spacing as a share of the scale diameter: how much of each scale shows."},
    {"name": "circuli", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Depth of the growth rings around each scale's centre."},
    {"name": "radii", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Depth of the grooves radiating from the growth centre."},
    {"name": "edge_pigment", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Dark pigment along the free edge of each scale (a net pattern)."},
    {"name": "iridescence", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Colour sheen turning across each scale."},
    {"name": "pattern", "type": "int", "default": 0, "minimum": 0, "maximum": 2,
     "meaning": "0 even colour, 1 large patches of a second colour (koi), 2 dark spots (trout)."},
    {"name": "gloss", "type": "float", "default": 0.7, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Wet gloss of the skin."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Silver baitfish scales with a blue-green and pink sheen.", "values": {}},
    "koi_kohaku": {"description": "White koi scales with large red patches and a faint net.",
                   "values": {"pattern": 1, "iridescence": 0.15, "edge_pigment": 0.25, "columns": 10,
                              "exposure": 0.5}},
    "carp_bronze": {"description": "Large bronze carp scales with dark pigmented edges.",
                    "values": {"columns": 7, "edge_pigment": 0.8, "iridescence": 0.2, "circuli": 0.7,
                               "radii": 0.5, "exposure": 0.5}},
    "trout_spotted": {"description": "Small olive trout scales with dark spots and a pink sheen.",
                      "values": {"columns": 22, "pattern": 2, "iridescence": 0.45, "edge_pigment": 0.15,
                                 "circuli": 0.3}},
}
#: Growth rings (circuli) from the centre of a scale to its rim.
RING_COUNT = 7.0
#: Scale colour, second (patch or spot) colour, pigment colour, skin colour, iridescent hue offset and metallic.
PALETTES = {
    "default": ("#c9ced6", "#9aa4b4", "#3a4656", "#2a3038", 0.45, 0.85),
    "koi_kohaku": ("#ece6dc", "#d2401c", "#8a6a50", "#6a5040", 0.05, 0.0),
    "carp_bronze": ("#b48a3c", "#8a6a2a", "#2e1f0e", "#3a2a14", 0.12, 0.45),
    "trout_spotted": ("#8a8a5a", "#1e1e14", "#4a4a30", "#2e2e1e", 0.9, 0.3),
}


def _hue_rgb(hue: float) -> tuple:
    """A saturated colour for a hue in turns (piecewise linear HSV wheel, value 1, saturation 1)."""
    h = (hue % 1.0) * 6.0
    sector = int(h) % 6
    f = h - math.floor(h)
    return ((1.0, f, 0.0), (1.0 - f, 1.0, 0.0), (0.0, 1.0, f), (0.0, 1.0 - f, 1.0), (f, 0.0, 1.0),
            (1.0, 0.0, 1.0 - f))[sector]


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The fish skin maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    scale_code, second_code, pigment_code, skin_code, hue_offset, metal = PALETTES[preset]
    scale_rgb, second_rgb = tk.hex_rgb(scale_code), tk.hex_rgb(second_code)
    pigment_rgb, skin_rgb = tk.hex_rgb(pigment_code), tk.hex_rgb(skin_code)
    columns = p["columns"]
    radius = 0.62
    spacing = 2.0 * radius * p["exposure"]
    rows = max(2, 2 * int(round(columns / spacing / 2.0)))
    ratio = columns / rows
    circuli, radii, pigment = p["circuli"], p["radii"], p["edge_pigment"]
    iridescence, gloss, pattern = p["iridescence"], p["gloss"], p["pattern"]
    ring_count = RING_COUNT
    pixels_per_scale = min(width, height) / columns * radius
    ring_fade = tk.smoothstep(1.5, 3.5, pixels_per_scale / ring_count)
    patches = tk.fbm(width, height, 3, 3, tk.hash_u32(seed, 1))
    spots = tk.value_noise(width, height, min(columns * 2, max(4, width // 2)), min(rows, max(4, height // 2)),
                           tk.hash_u32(seed, 2))
    rng = tk.Rng(seed, 0xF1)
    tones = [(rng.uniform(-1.0, 1.0), rng.random()) for _ in range(columns * rows)]
    second_share = [0.0] * (columns * rows)
    for j in range(rows):
        for i in range(columns):
            cu = (i + 0.5 + 0.5 * (j % 2)) / columns
            cv = (j + 0.5) / rows
            if pattern == 1:
                second_share[j * columns + i] = tk.smoothstep(0.02, 0.12, tk.sample(patches, width, height, cu, cv))
            elif pattern == 2:
                second_share[j * columns + i] = 1.0 if tk.sample(spots, width, height, cu, cv) > 0.82 else 0.0
    count = width * height
    heights, red, green, blue, rough, metallic = [0.0] * count, [], [], [], [], []
    for y in range(height):
        gy = (y + 0.5) / height * rows
        j0 = int(math.floor(gy))
        for x in range(width):
            gx = (x + 0.5) / width * columns
            index = y * width + x
            chosen = None
            for dj in (-3, -2, -1, 0, 1):
                j = j0 + dj
                shift = 0.5 * (j % 2)
                i0 = int(math.floor(gx - shift))
                for di in (0, 1, -1):
                    i = i0 + di
                    dx = (gx - (i + 0.5 + shift)) / radius
                    dy = (gy - (j + 0.5)) * ratio / radius
                    r2 = dx * dx + dy * dy
                    if r2 < 1.0:
                        chosen = (dx, dy, r2, (j % rows) * columns + i % columns)
                        break
                if chosen is not None:
                    break
            if chosen is None:
                heights[index] = 0.05
                red.append(skin_rgb[0])
                green.append(skin_rgb[1])
                blue.append(skin_rgb[2])
                rough.append(0.6)
                metallic.append(0.0)
                continue
            sx, sy, r2, key = chosen
            r = math.sqrt(r2)
            fx, fy = sx, sy + 0.45
            rho = math.hypot(fx, fy)
            theta = math.atan2(fx, fy)
            rings = 0.5 + 0.5 * math.cos(math.tau * ring_count * rho)
            grooves = 0.5 + 0.5 * math.cos(9.0 * theta)
            rim = tk.smoothstep(0.82, 1.0, r)
            edge = pigment * tk.smoothstep(0.55, 0.95, r) * tk.smoothstep(-0.1, 0.4, sy)
            heights[index] = (0.45 + 0.18 * sy - 0.06 * circuli * ring_fade * rings
                              - 0.05 * radii * grooves * tk.smoothstep(0.3, 0.8, rho) - 0.2 * rim)
            tone, phase = tones[key]
            share = second_share[key]
            colour = [a + (b - a) * share for a, b in zip(scale_rgb, second_rgb)]
            if iridescence > 0.0:
                sheen = _hue_rgb(hue_offset + 0.25 * sx + 0.18 * sy + 0.1 * phase)
                colour = [c + (c * (0.62 + 0.5 * s) - c) * iridescence * (1.0 - share)
                          for c, s in zip(colour, sheen)]
            colour = [c + (g - c) * edge for c, g in zip(colour, pigment_rgb)]
            shade = 0.9 + 0.06 * tone - 0.25 * rim - 0.05 * circuli * ring_fade * rings
            red.append(colour[0] * shade)
            green.append(colour[1] * shade)
            blue.append(colour[2] * shade)
            rough.append(0.5 - 0.35 * gloss + 0.08 * circuli * ring_fade * rings + 0.2 * rim)
            metallic.append(metal * (1.0 - share) * (1.0 - 0.7 * edge) * (1.0 - rim))
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.2 / columns, roughness=rough,
                     metallic=metallic, ao_radius=0.3 / columns, ao_strength=0.9, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
