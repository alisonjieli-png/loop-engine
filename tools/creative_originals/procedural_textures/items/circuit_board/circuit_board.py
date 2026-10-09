"""Printed circuit board: solder mask, traces, vias, chips, silkscreen and LEDs, tileable PBR maps (standard library).

Chips are placed first as dark rectangles with metal pins along two or four sides. Traces leave from pins and wander
on a routing grid, turning only by multiples of 45 degrees, and end in vias (copper rings with a drilled hole);
extra traces run between random vias. Traces sit raised under the solder mask, which tints them lighter; exposed
pads and pins are metal (gold or tin). Silkscreen draws chip outlines and small marks, and indicator LEDs glow in the
emissive map. Every element wraps around the tile edges.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "circuit_board"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.12, 1.0]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
    {"name": "emissive", "channels": 3, "colour_space": "srgb", "convention": "gltf_emissive"},
]
PARAMETERS = [
    {"name": "chips", "type": "int", "default": 3, "minimum": 0, "maximum": 10,
     "meaning": "Chip packages on the tile."},
    {"name": "traces", "type": "int", "default": 40, "minimum": 4, "maximum": 160,
     "meaning": "Traces routed across the board."},
    {"name": "grid", "type": "int", "default": 64, "minimum": 24, "maximum": 160,
     "meaning": "Routing grid steps across the tile (higher gives finer traces)."},
    {"name": "leds", "type": "int", "default": 4, "minimum": 1, "maximum": 30,
     "meaning": "Glowing indicator LEDs."},
    {"name": "silkscreen", "type": "float", "default": 0.7, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Visibility of the white silkscreen outlines and marks."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo and lights in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Green solder mask with gold pads and red LEDs.", "values": {}},
    "blue_dense": {"description": "Blue mask with dense fine traces and tin pads.",
                   "values": {"traces": 110, "grid": 96, "chips": 5, "leds": 6}},
    "black_matte": {"description": "Matte black mask with gold traces and white LEDs.",
                    "values": {"traces": 60, "chips": 2, "leds": 3, "silkscreen": 0.9}},
    "glowing_traces": {"description": "Dark board with glowing cyan data lines.",
                       "values": {"traces": 70, "chips": 4, "leds": 12, "silkscreen": 0.3}},
}
#: Mask, trace-under-mask, pad metal, chip, silkscreen and LED colours (sRGB), mask roughness and whether the
#: traces also glow in the LED colour (a stylized science fiction board), per preset.
PALETTES = {
    "default": ("#1f5e2c", "#3c8a46", "#d9b45a", "#1b1b1d", "#e8e8e2", "#ff3b2f", 0.3, False),
    "blue_dense": ("#1b3e76", "#3263a8", "#c8ccd0", "#141416", "#e8e8e2", "#4cff6a", 0.28, False),
    "black_matte": ("#141516", "#2a2b2d", "#d9b45a", "#0e0e0f", "#f2f2ee", "#f4f4ff", 0.7, False),
    "glowing_traces": ("#0d1a1f", "#16404a", "#c8ccd0", "#0a0b0c", "#7f9aa3", "#3ae6ff", 0.35, True),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The circuit board maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    mask_rgb, trace_rgb, pad_rgb, chip_rgb, silk_rgb, led_rgb, mask_rough, glowing_traces = PALETTES[preset]
    mask_rgb, trace_rgb, pad_rgb, chip_rgb, silk_rgb, led_rgb = (tk.hex_rgb(c) for c in
                                                                 (mask_rgb, trace_rgb, pad_rgb, chip_rgb, silk_rgb,
                                                                  led_rgb))
    count = width * height
    step = 1.0 / p["grid"]
    rng = tk.Rng(seed, 1)
    trace = [0.0] * count
    pads = [0.0] * count
    holes = [0.0] * count
    chip = [0.0] * count
    silk = [0.0] * count
    led = [0.0] * count
    starts = []
    for _ in range(p["chips"]):
        cw, ch = step * rng.integer(6, 14), step * rng.integer(6, 14)
        cu, cv = step * rng.integer(0, p["grid"] - 1), step * rng.integer(0, p["grid"] - 1)
        four_sides = rng.chance(0.5)
        for index, s, t in tk.ellipse_pixels(width, height, cu, cv, cw * 0.62, ch * 0.62):
            if abs(s) <= 0.8 and abs(t) <= 0.8:
                chip[index] = 1.0
            elif abs(s) <= 0.92 and abs(t) <= 0.92 and (abs(s) > 0.86 or abs(t) > 0.86):
                silk[index] = max(silk[index], 1.0)
        pins = int(cw / step)
        for k in range(pins):
            pu = cu - cw * 0.5 + (k + 0.5) * step
            for side in (-1, 1):
                pv = cv + side * ch * 0.5
                tk.draw_segment(pads, width, height, pu, pv - side * step * 0.6, pu, pv + side * step * 0.4,
                                step * 0.18, profile=lambda d: 1.0)
                starts.append((pu, pv + side * step * 0.4, 0.0 if side < 0 else 0.0, side))
        if four_sides:
            for k in range(int(ch / step)):
                pv = cv - ch * 0.5 + (k + 0.5) * step
                for side in (-1, 1):
                    pu = cu + side * cw * 0.5
                    tk.draw_segment(pads, width, height, pu - side * step * 0.6, pv, pu + side * step * 0.4, pv,
                                    step * 0.18, profile=lambda d: 1.0)
                    starts.append((pu + side * step * 0.4, pv, side, 0))
    directions = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
    for number in range(p["traces"]):
        if starts and rng.chance(0.6):
            su, sv, dx, dy = starts[rng.integer(0, len(starts) - 1)]
            heading = directions.index((int(dx), int(dy))) if (int(dx), int(dy)) in directions else rng.integer(0, 7)
        else:
            su, sv = step * rng.integer(0, p["grid"] - 1), step * rng.integer(0, p["grid"] - 1)
            heading = rng.integer(0, 3) * 2
        points = [(su, sv)]
        u, v = su, sv
        for _ in range(rng.integer(2, 6)):
            dx, dy = directions[heading]
            run = rng.integer(2, 12)
            u, v = u + dx * run * step, v + dy * run * step
            points.append((u, v))
            heading = (heading + rng.choice((-1, 1))) % 8
        tk.draw_path(trace, width, height, points, step * rng.choice((0.16, 0.22, 0.3)), profile=lambda d: 1.0)
        end_u, end_v = points[-1]
        radius = step * 0.5
        tk.stamp(pads, width, height, end_u % 1.0, end_v % 1.0, radius, radius,
                 lambda s, t: 1.0 if s * s + t * t <= 1.0 else None)
        tk.stamp(holes, width, height, end_u % 1.0, end_v % 1.0, radius * 0.45, radius * 0.45,
                 lambda s, t: 1.0 if s * s + t * t <= 1.0 else None)
    for _ in range(int(25 * p["silkscreen"])):
        mu, mv = rng.random(), rng.random()
        length = step * rng.integer(2, 6)
        tk.draw_segment(silk, width, height, mu, mv, mu + length, mv, step * 0.12, profile=lambda d: 1.0)
    for _ in range(p["leds"]):
        lu, lv = rng.random(), rng.random()
        tk.stamp(led, width, height, lu, lv, step * 1.2, step * 0.8,
                 lambda s, t: 1.0 - 0.4 * (s * s + t * t) if s * s + t * t <= 1.0 else None)
    texture = tk.fbm(width, height, 30, 2, tk.hash_u32(seed, 2))
    silkscreen = p["silkscreen"]
    red, green, blue, heights, rough, metallic, glow = [], [], [], [], [], [], []
    for index in range(count):
        is_chip, is_pad, hole = chip[index], min(1.0, pads[index]), holes[index]
        on_trace = min(1.0, trace[index])
        colour = [m + (t - m) * on_trace for m, t in zip(mask_rgb, trace_rgb)]
        colour = [c * (0.96 + 0.06 * texture[index]) for c in colour]
        if silk[index] > 0.0:
            colour = [c + (s - c) * silkscreen * min(1.0, silk[index]) for c, s in zip(colour, silk_rgb)]
        level = 0.4 + 0.08 * on_trace
        metal = 0.0
        if is_pad > 0.0:
            colour = [c + (pd - c) * is_pad for c, pd in zip(colour, pad_rgb)]
            level = 0.48
            metal = is_pad
        if hole > 0.0:
            colour = [0.04, 0.04, 0.04]
            level = 0.15
            metal = 0.0
        if is_chip > 0.0:
            colour = [c * (0.9 + 0.1 * texture[index]) for c in chip_rgb]
            level = 0.85
            metal = 0.0
        light = led[index]
        if light > 0.0:
            colour = [0.25 * l + 0.2 for l in led_rgb]
            level = max(level, 0.6 + 0.2 * light)
            metal = 0.0
        glow_amount = light + (0.7 * on_trace * (1.0 - is_chip) if glowing_traces else 0.0)
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        heights.append(level)
        metallic.append(metal)
        rough.append(mask_rough + 0.05 * texture[index] if metal == 0.0 else 0.25)
        glow.append(min(1.0, glow_amount))
    trace_light = led_rgb
    emissive = ([g * trace_light[0] for g in glow], [g * trace_light[1] for g in glow],
                [g * trace_light[2] for g in glow])
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    emissive = tk.grade(emissive, p["hue_shift"], 1.0, 1.0)
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.01, roughness=rough,
                     metallic=metallic, emissive=emissive, ao_radius=0.006, ao_strength=0.8,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
