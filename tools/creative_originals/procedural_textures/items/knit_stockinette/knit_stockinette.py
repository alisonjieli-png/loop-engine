"""Knitted fabric in stockinette, reverse stockinette, garter, k2p2 rib or seed stitch: tileable PBR maps.

The tile holds a whole number of stitch columns and rows, so the fabric repeats exactly. A knit stitch shows as a V:
two slanted legs, each an elliptical yarn dome whose upper end dips behind the stitch above it. A purl stitch shows
the yarn as a horizontal wave: the head of the loop arches up and the sinker loop dips down between stitches, giving
the familiar rows of purl bumps. The stitch pattern decides per stitch whether it is knit or purl; in rib and garter
the purl stitches sit back from the knit ones. Twisted plies cut diagonal grooves across each leg, fuzz adds a soft
halo, and every stitch gets a small offset, size and tone of its own. Stripes or a stranded two-colour motif colour
the stitches when ``colourwork`` asks for them.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "knit_stockinette"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.92]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.55, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "pattern", "type": "int", "default": 0, "minimum": 0, "maximum": 4,
     "meaning": "0 stockinette (all knit), 1 reverse stockinette (all purl), 2 garter (knit and purl rows "
                "alternate), 3 k2p2 rib (two knit columns, two purl columns), 4 seed stitch (knit and purl alternate "
                "in both directions)."},
    {"name": "stitches", "type": "int", "default": 16, "minimum": 4, "maximum": 48,
     "meaning": "Stitch columns across the tile width; rounded up to a multiple of 4 for rib and of 8 for a motif."},
    {"name": "row_ratio", "type": "float", "default": 1.4, "minimum": 1.0, "maximum": 1.8,
     "meaning": "Rows per stitch width (the gauge); the row count is rounded to keep the pattern repeating."},
    {"name": "yarn_width", "type": "float", "default": 1.0, "minimum": 0.7, "maximum": 1.25,
     "meaning": "Yarn thickness relative to the stitch: low values open gaps between the legs."},
    {"name": "twist", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Depth of the diagonal grooves between twisted plies."},
    {"name": "plies", "type": "float", "default": 3.5, "minimum": 1.5, "maximum": 6.0,
     "meaning": "Ply twists along one stitch leg."},
    {"name": "fuzz", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Fibre halo: fine noise in height and colour, and rougher yarn."},
    {"name": "irregularity", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Hand-knit unevenness: per-stitch offset, size and tone."},
    {"name": "colourwork", "type": "int", "default": 0, "minimum": 0, "maximum": 2,
     "meaning": "0 one colour, 1 contrast stripes two rows in six, 2 a stranded two-colour motif repeating every "
                "eight stitches and rows."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Cream wool in stockinette, a fine jumper knit.", "values": {}},
    "chunky_red": {"description": "Thick red yarn in stockinette with strongly twisted plies.",
                   "values": {"stitches": 8, "row_ratio": 1.3, "twist": 0.8, "plies": 4.5, "fuzz": 0.3}},
    "navy_rib": {"description": "Navy k2p2 ribbing as on cuffs and hems, the purl columns sunk between the knit.",
                 "values": {"pattern": 3, "stitches": 20, "irregularity": 0.25}},
    "heather_garter": {"description": "Grey heather yarn in garter stitch: ridges of purl bumps.",
                       "values": {"pattern": 2, "stitches": 14, "row_ratio": 1.6, "fuzz": 0.6}},
    "fair_isle": {"description": "Stranded colourwork: a navy motif on cream stockinette.",
                  "values": {"stitches": 24, "colourwork": 2, "fuzz": 0.3, "irregularity": 0.2}},
    "moss_seed": {"description": "Moss green seed stitch with a pebbly surface and contrast stripes.",
                  "values": {"pattern": 4, "stitches": 18, "colourwork": 1, "row_ratio": 1.2}},
}
#: Main yarn, contrast yarn, heather fleck colour and the shadow colour between the yarns, per preset (sRGB).
PALETTES = {
    "default": ("#e4dccb", "#4b5f84", "#f3eee2", "#3b352c"),
    "chunky_red": ("#a3242a", "#e7dfcf", "#c23a3a", "#2e0b0d"),
    "navy_rib": ("#25324f", "#c9c2b0", "#3a4a6e", "#0b0f18"),
    "heather_garter": ("#8b8a86", "#5a3b3b", "#c9c6bf", "#2a2927"),
    "fair_isle": ("#e8e0cc", "#233457", "#f5f0e4", "#2d2a24"),
    "moss_seed": ("#56693a", "#d9cfa8", "#7d8f55", "#1d2412"),
}
#: Knit legs in stitch units: centre (x, y with y down) and the sign of the slant of the leg's top end. A leg is
#: the superellipse along^4 + across^2 < 1, fuller than an ellipse, so neighbouring legs meet in narrow grooves.
LEGS = ((0.28, 0.55, -1.0), (0.72, 0.55, 1.0))
LEG_TILT = 0.42
LEG_HALF_LENGTH = 0.66
LEG_HALF_WIDTH = 0.25
#: Purl wave in stitch units: mean row position, arch amplitude and yarn half width.
PURL_CENTRE, PURL_ARCH, PURL_HALF_WIDTH = 0.5, 0.17, 0.21
MOTIF_SIZE = 8
STRIPE_PERIOD = 6
#: Base height of knit and purl stitches per pattern: rib sinks its purl columns, garter its knit rows.
LEVELS = {0: (0.3, 0.3), 1: (0.3, 0.3), 2: (0.12, 0.3), 3: (0.3, 0.1), 4: (0.3, 0.3)}


def _motif(seed: int) -> list:
    """An 8 x 8 stranded-colour chart, 1 for the contrast colour, symmetric about both axes like a Fair Isle peerie.

    The seed picks one of four figures (a diamond with a centre, a diagonal cross, a plus with corner dots, or
    hashed blocks) and may invert it, so every seed gives a symmetric two-colour motif."""
    rng = tk.Rng(seed, 0x4D)
    figure = rng.integer(0, 3)
    chart = []
    for r in range(MOTIF_SIZE):
        line = []
        for c in range(MOTIF_SIZE):
            dr, dc = abs(r - 3.5), abs(c - 3.5)
            if figure == 0:
                bit = dr + dc in (1.0, 4.0)
            elif figure == 1:
                bit = dr == dc and dr < 3.0
            elif figure == 2:
                bit = (min(dr, dc) == 0.5 and max(dr, dc) < 3.0) or (dr == 3.5 and dc == 3.5)
            else:
                bit = tk.hash_u32(seed, int(min(dr, dc) * 2), int(max(dr, dc) * 2)) % 3 == 0
            line.append(1 if bit else 0)
        chart.append(line)
    if rng.chance(0.25):
        chart = [[1 - bit for bit in line] for line in chart]
    return chart


def _is_knit(pattern: int, column: int, row: int) -> bool:
    if pattern == 0:
        return True
    if pattern == 1:
        return False
    if pattern == 2:
        return row % 2 == 1
    if pattern == 3:
        return column % 4 < 2
    return (column + row) % 2 == 0


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The knitted fabric maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    main_rgb, contrast_rgb, fleck_rgb, gap_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    pattern, colourwork = p["pattern"], p["colourwork"]
    column_step = MOTIF_SIZE if colourwork == 2 else 4 if pattern == 3 else 2 if pattern == 4 else 1
    columns = -(-p["stitches"] // column_step) * column_step
    row_step = MOTIF_SIZE if colourwork == 2 else STRIPE_PERIOD if colourwork == 1 else 2
    rows = max(row_step, int(round(columns * p["row_ratio"] / row_step)) * row_step)
    knit = [[_is_knit(pattern, i, j) for i in range(columns)] for j in range(rows)]
    knit_level, purl_level = LEVELS[pattern]
    chart = _motif(seed)
    contrast = [[(chart[j % MOTIF_SIZE][i % MOTIF_SIZE] if colourwork == 2 else
                  (1 if colourwork == 1 and j % STRIPE_PERIOD >= STRIPE_PERIOD - 2 else 0)) for i in range(columns)]
                for j in range(rows)]
    irregular = p["irregularity"]
    rng = tk.Rng(seed, 0x51)
    jitter = [[(irregular * rng.uniform(-0.05, 0.05), irregular * rng.uniform(-0.04, 0.04),
                1.0 + irregular * rng.uniform(-0.07, 0.07), irregular * rng.uniform(-1.0, 1.0))
               for _ in range(columns)] for _ in range(rows)]
    yarn = p["yarn_width"]
    half_length, half_width = LEG_HALF_LENGTH, LEG_HALF_WIDTH * yarn
    legs = []
    for cx, cy, sign in LEGS:
        ux, uy = sign * math.sin(LEG_TILT), -math.cos(LEG_TILT)
        legs.append((cx, cy, ux, uy))
    purl_half = PURL_HALF_WIDTH * yarn
    twist, plies, fuzz = p["twist"], p["plies"], p["fuzz"]
    stitch_pixels = min(width / columns, height / rows)
    twist_fade = twist * tk.smoothstep(2.5, 5.0, stitch_pixels * 2.0 * half_length / plies)
    fine = tk.fbm(width, height, max(8, columns * 4), 2, tk.hash_u32(seed, 2), cells_y=max(8, rows * 3))
    flecks = tk.value_noise(width, height, columns * 6, rows * 4, tk.hash_u32(seed, 3))
    column_cells = []
    for x in range(width):
        fu = (x + 0.5) / width * columns
        column_cells.append((int(fu) % columns, fu - math.floor(fu)))
    tau = math.tau
    red, green, blue, heights, rough = [], [], [], [], []
    for y in range(height):
        fv = (y + 0.5) / height * rows
        j = int(fv) % rows
        fy = fv - math.floor(fv)
        offsets = (0, -1) if fy < 0.25 else (0, 1) if fy > 0.8 else (0,)
        base = y * width
        for x in range(width):
            i, fx = column_cells[x]
            best, along_best, across_best, owner, kind = -1.0, 0.0, 0.0, None, 0
            for o in offsets:
                jj = (j + o) % rows
                if not knit[jj][i]:
                    continue
                jx, jy, js, _tone = jitter[jj][i]
                ly = fy - o - jy
                lx = fx - jx
                for cx, cy, ux, uy in legs:
                    dx, dy = lx - cx, ly - cy
                    along = (dx * ux + dy * uy) / (half_length * js)
                    if along <= -1.0 or along >= 1.0:
                        continue
                    across = (dy * ux - dx * uy) / (half_width * js)
                    squared = along * along
                    r2 = squared * squared + across * across
                    if r2 >= 1.0:
                        continue
                    dome = math.sqrt(1.0 - r2)
                    level = knit_level + 0.62 * dome * (1.0 - 0.3 * max(0.0, along))
                    if level > best:
                        best, along_best, across_best, owner, kind = level, along, across, (jj, i), 1
            if not knit[j][i]:
                jx, jy, js, _tone = jitter[j][i]
                shift = 0.5 * (j % 2)
                phase = fx - jx + shift
                path = PURL_CENTRE + jy + PURL_ARCH * math.cos(tau * phase)
                slope = PURL_ARCH * tau * math.sin(tau * phase)
                across = (fy - path) / (purl_half * js) / math.sqrt(1.0 + slope * slope)
                if -1.0 < across < 1.0:
                    dome = math.sqrt(1.0 - across * across)
                    head = 0.5 - 0.5 * math.cos(tau * phase)
                    level = purl_level + 0.6 * dome * (0.82 + 0.18 * head)
                    if level > best:
                        best, along_best, across_best, owner, kind = level, 2.0 * phase, across, (j, i), 2
            index = base + x
            noise = fine[index]
            if owner is None:
                level = 0.04 + 0.03 * fuzz * noise
                shade = 0.75 + 0.25 * fuzz * (flecks[index] - 0.5)
                colour = gap_rgb
                cover = 0.0
            else:
                grooves = 0.5 + 0.5 * math.cos(tau * plies * (0.5 * along_best + 0.35 * across_best))
                level = best - 0.1 * twist_fade * grooves * (best - 0.1) + 0.035 * fuzz * noise
                tone = jitter[owner[0]][owner[1]][3]
                shade = (0.78 + 0.32 * (best - 0.1) - 0.16 * twist_fade * grooves + 0.05 * tone
                         + 0.1 * fuzz * (flecks[index] - 0.5))
                yarn_rgb = contrast_rgb if contrast[owner[0]][owner[1]] else main_rgb
                fleck = 0.35 * tk.smoothstep(0.55, 0.95, flecks[index]) if kind else 0.0
                colour = [c + (f - c) * fleck for c, f in zip(yarn_rgb, fleck_rgb)]
                cover = tk.smoothstep(0.0, 0.18, best - 0.05)
            pixel = [g + (c * shade - g) * cover for g, c in zip(gap_rgb, colour)] if cover < 1.0 else \
                [c * shade for c in colour]
            red.append(pixel[0])
            green.append(pixel[1])
            blue.append(pixel[2])
            heights.append(level)
            rough.append(0.86 + 0.1 * fuzz * flecks[index] - 0.06 * (1.0 - cover))
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    scale = max(columns, rows / p["row_ratio"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.45 / scale, roughness=rough,
                     ao_radius=0.45 / scale, ao_strength=1.3, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
