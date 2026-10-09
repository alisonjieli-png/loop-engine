"""Starfield with nebulae: emissive stars over glowing gas and dark dust lanes, tileable maps (standard library).

Stars are drawn in texture space from a seeded sequence, so a seed keeps its sky at any output size. Brightness
follows a power law (many faint stars, few bright ones) and colour comes from a blackbody temperature: Planck's law
integrated over the visible band against an analytic multi-lobe Gaussian approximation of the CIE 1931
colour-matching functions, then converted to linear sRGB. Bright stars get a soft halo and optional four-point
diffraction spikes. Gas is domain-warped fractal noise through two colour ramps, and ridged noise carves dust lanes
that dim the gas and the stars behind them. Light is summed in linear units and encoded as sRGB at the end.

The emissive map carries the light. Albedo is near black with the faint glow and dust tint, so the material still
reads when it is lit. Height and normals follow the gas density and are kept shallow.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "starfield_nebula"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.0, 0.85]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.4, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
    {"name": "emissive", "channels": 3, "colour_space": "srgb", "convention": "gltf_emissive"},
]
PARAMETERS = [
    {"name": "star_count", "type": "int", "default": 1600, "minimum": 100, "maximum": 6000,
     "meaning": "Stars drawn in the tile."},
    {"name": "bright_stars", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of bright stars: 0 nearly all faint, 1 many bright ones."},
    {"name": "star_size", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 3.0,
     "meaning": "Apparent star size; brighter stars are drawn larger."},
    {"name": "spikes", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Four-point diffraction spikes on bright stars, 0 none."},
    {"name": "star_temperature", "type": "float", "default": 6500.0, "minimum": 3000.0, "maximum": 15000.0,
     "meaning": "Typical star temperature in kelvin: low gives orange stars, high blue-white ones."},
    {"name": "nebula", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Amount and brightness of glowing gas."},
    {"name": "nebula_scale", "type": "int", "default": 2, "minimum": 1, "maximum": 8,
     "meaning": "Cloud features across the tile; larger values give smaller clouds."},
    {"name": "swirl", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Domain warping that pulls the gas into filaments and swirls."},
    {"name": "dust", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Dark dust lanes that dim the gas and the stars behind them."},
    {"name": "cluster", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of stars gathered in a cluster around the middle of the tile."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo and the light in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Deep field: many faint stars over faint violet and blue gas.", "values": {}},
    "emission_nebula": {"description": "Bright red and teal gas torn by dark dust lanes, fewer stars.",
                        "values": {"nebula": 0.95, "dust": 0.8, "swirl": 0.85, "star_count": 900,
                                   "spikes": 0.15}},
    "star_cluster": {"description": "A dense cluster of hot bright stars with diffraction spikes and little gas.",
                     "values": {"cluster": 0.55, "star_count": 3600, "bright_stars": 0.6, "spikes": 0.85,
                                "nebula": 0.18, "dust": 0.1, "star_temperature": 9000.0}},
    "dark_void": {"description": "Sparse cool stars and faint brown dust in a nearly empty field.",
                  "values": {"star_count": 450, "nebula": 0.12, "dust": 0.55, "bright_stars": 0.2, "spikes": 0.0,
                             "star_temperature": 4500.0, "nebula_scale": 3}},
}
#: Per preset: main gas ramp, second gas ramp (sRGB stops), dust tint (sRGB) and the faint sky glow (linear).
PALETTES = {
    "default": ([(0.0, "#000000"), (0.3, "#1a1040"), (0.65, "#4a40b4"), (1.0, "#b4c4ff")],
                [(0.0, "#000000"), (0.5, "#30124a"), (1.0, "#c070d0")], "#2a2236", 0.0025),
    "emission_nebula": ([(0.0, "#000000"), (0.3, "#3a0610"), (0.65, "#c02848"), (1.0, "#ffb0a0")],
                        [(0.0, "#000000"), (0.5, "#06343a"), (1.0, "#40e0d0")], "#3a2418", 0.004),
    "star_cluster": ([(0.0, "#000000"), (0.4, "#101830"), (0.8, "#3050a0"), (1.0, "#a0c8ff")],
                     [(0.0, "#000000"), (0.6, "#182040"), (1.0, "#6080c0")], "#202838", 0.006),
    "dark_void": ([(0.0, "#000000"), (0.5, "#0c0a14"), (1.0, "#403850")],
                  [(0.0, "#000000"), (0.6, "#140e0a"), (1.0, "#504030")], "#4a3a2a", 0.001),
}


def _cie_xyz(wavelength: float) -> tuple:
    """CIE 1931 colour-matching functions at a wavelength in nanometres, as sums of piecewise Gaussian lobes
    (a separate width on each side of every peak)."""

    def lobe(peak: float, below: float, above: float) -> float:
        t = (wavelength - peak) / (below if wavelength < peak else above)
        return math.exp(-0.5 * t * t)

    x = 1.056 * lobe(599.8, 37.9, 31.0) + 0.362 * lobe(442.0, 16.0, 26.7) - 0.065 * lobe(501.1, 20.4, 26.2)
    y = 0.821 * lobe(568.8, 46.9, 40.5) + 0.286 * lobe(530.9, 16.3, 31.1)
    z = 1.217 * lobe(437.0, 11.8, 36.0) + 0.681 * lobe(459.0, 26.0, 13.8)
    return x, y, z


def blackbody_rgb(temperature: float) -> tuple:
    """Linear sRGB colour of a blackbody at ``temperature`` kelvin, scaled so the largest channel is 1."""
    if not 500.0 <= temperature <= 100000.0:
        raise ValueError("temperature is from 500 to 100000 kelvin")
    total = [0.0, 0.0, 0.0]
    for step in range(81):
        wavelength = 380.0 + 5.0 * step
        metres = wavelength * 1e-9
        radiance = 1.0 / (metres ** 5 * (math.exp(1.4388e-2 / (metres * temperature)) - 1.0))
        for channel, weight in enumerate(_cie_xyz(wavelength)):
            total[channel] += radiance * weight
    x, y, z = total
    rgb = [max(0.0, 3.2406 * x - 1.5372 * y - 0.4986 * z), max(0.0, -0.9689 * x + 1.8758 * y + 0.0415 * z),
           max(0.0, 0.0557 * x - 0.2040 * y + 1.0570 * z)]
    top = max(rgb)
    return tuple(c / top for c in rgb)


#: Star colours for temperatures from 2500 K to 25000 K, spaced evenly in log temperature.
_TEMPERATURES = [2500.0 * 10.0 ** (k / 47.0) for k in range(48)]
_STAR_COLOURS = [blackbody_rgb(t) for t in _TEMPERATURES]


def _linear_stops(stops: list) -> list:
    return [(position, tuple(tk.srgb_to_linear(c) for c in tk.hex_rgb(code))) for position, code in stops]


def _splat(channels: tuple, width: int, height: int, u: float, v: float, sigma_x: float, sigma_y: float,
           amount: float, colour: tuple) -> None:
    """Add a Gaussian spot of linear light (peak ``amount``) centred at (u, v), wrapping around both edges."""
    cx, cy = u * width - 0.5, v * height - 0.5
    reach_x, reach_y = int(math.ceil(3.0 * sigma_x)), int(math.ceil(3.0 * sigma_y))
    inverse_x, inverse_y = 0.5 / (sigma_x * sigma_x), 0.5 / (sigma_y * sigma_y)
    red, green, blue = channels
    cr, cg, cb = (amount * c for c in colour)
    x0, y0 = math.floor(cx) - reach_x, math.floor(cy) - reach_y
    for y in range(y0, y0 + 2 * reach_y + 2):
        fall_y = (y - cy) * (y - cy) * inverse_y
        if fall_y > 4.5:
            continue
        row = (y % height) * width
        for x in range(x0, x0 + 2 * reach_x + 2):
            weight = math.exp(-((x - cx) * (x - cx) * inverse_x + fall_y))
            if weight < 1e-3:
                continue
            index = row + x % width
            red[index] += cr * weight
            green[index] += cg * weight
            blue[index] += cb * weight


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The starfield maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    gas_stops, second_stops, dust_hex, sky_glow = PALETTES[preset]
    cells, swirl, nebula, dust = p["nebula_scale"], p["swirl"], p["nebula"], p["dust"]
    offset_u = tk.fbm(width, height, cells, 4, tk.hash_u32(seed, 1))
    offset_v = tk.fbm(width, height, cells, 4, tk.hash_u32(seed, 2))
    gas = tk.warp(tk.fbm(width, height, cells, 6, tk.hash_u32(seed, 3)), width, height, offset_u, offset_v,
                  0.22 * swirl)
    second = tk.warp(tk.fbm(width, height, 2 * cells, 5, tk.hash_u32(seed, 4)), width, height, offset_v, offset_u,
                     0.3 * swirl)
    lanes = tk.warp(tk.ridged(width, height, 2 * cells, 5, tk.hash_u32(seed, 5)), width, height, offset_u,
                    offset_v, 0.22 * swirl)
    low = 0.62 - 0.32 * nebula
    density = [nebula * tk.smoothstep(low, 0.95, 0.5 + 0.5 * g) for g in gas]
    density2 = [0.8 * nebula * tk.smoothstep(low + 0.08, 0.98, 0.5 + 0.5 * g) for g in second]
    dusty = [dust * tk.smoothstep(0.6, 0.9, lane) for lane in lanes]
    first_light = tk.ramp(density, _linear_stops(gas_stops))
    second_light = tk.ramp(density2, _linear_stops(second_stops))
    light = []
    for channel in range(3):
        a, b = first_light[channel], second_light[channel]
        light.append([sky_glow + (x + y) * (1.0 - 0.92 * d) for x, y, d in zip(a, b, dusty)])

    rng = tk.Rng(seed, 0x57A)
    exponent = 2.5 + 7.0 * (1.0 - p["bright_stars"])
    temperature = p["star_temperature"]
    log_low, log_span = math.log(_TEMPERATURES[0]), math.log(_TEMPERATURES[-1] / _TEMPERATURES[0])
    size = p["star_size"]
    for _ in range(p["star_count"]):
        if rng.chance(p["cluster"]):
            u, v = (0.5 + rng.gauss(0.0, 0.075)) % 1.0, (0.5 + rng.gauss(0.0, 0.075)) % 1.0
        else:
            u, v = rng.random(), rng.random()
        bright = rng.random() ** exponent
        kelvin = min(24000.0, max(2600.0, temperature * math.exp(rng.gauss(0.0, 0.32))))
        colour = _STAR_COLOURS[min(47, max(0, int((math.log(kelvin) - log_low) / log_span * 47.0 + 0.5)))]
        bright *= 1.0 - 0.9 * tk.sample(dusty, width, height, u, v)
        sigma = 0.00035 * size * (0.6 + 1.6 * bright)
        sigma_x, sigma_y = max(0.55, sigma * width), max(0.55, sigma * height)
        peak = (0.12 + 2.2 * bright) * min(1.0, sigma * width / sigma_x)
        _splat(light, width, height, u, v, sigma_x, sigma_y, peak, colour)
        if bright > 0.3:
            _splat(light, width, height, u, v, 4.0 * sigma_x, 4.0 * sigma_y, 0.06 * bright, colour)
        if bright > 0.8 and p["spikes"] > 0.0:
            reach = p["spikes"] * (0.012 + 0.2 * (bright - 0.8))
            radius = 0.75 / min(width, height)
            for du, dv in ((reach, 0.0), (0.0, reach)):
                for index, distance, along in tk.segment_pixels(width, height, u - du, v - dv, u + du, v + dv,
                                                                radius):
                    fade = (1.0 - abs(2.0 * along - 1.0)) ** 3 * (1.0 - distance) ** 2 * 0.9 * bright
                    for channel in range(3):
                        light[channel][index] += fade * colour[channel]

    lut = [tk.linear_to_srgb(k / 4095.0) for k in range(4096)]
    emissive = tuple([lut[int((v if v < 1.0 else 1.0) * 4095.0 + 0.5)] for v in channel] for channel in light)
    dust_colour = [tk.srgb_to_linear(c) for c in tk.hex_rgb(dust_hex)]
    glint = tk.fbm(width, height, 24, 3, tk.hash_u32(seed, 6))
    albedo_linear = []
    for channel in range(3):
        tint = dust_colour[channel]
        albedo_linear.append([0.004 + 0.45 * min(1.0, e) + tint * (0.25 * d + 0.08 * (1.0 + g))
                              for e, d, g in zip(light[channel], dusty, glint)])
    albedo = tuple([lut[int((v if v < 1.0 else 1.0) * 4095.0 + 0.5)] for v in channel] for channel in albedo_linear)
    heights, rough, occlusion = [], [], []
    for g, g2, d, n in zip(density, density2, dusty, glint):
        heights.append(0.45 + 0.35 * (g + 0.5 * g2) - 0.22 * d + 0.06 * n)
        rough.append(0.78 + 0.18 * d - 0.2 * g + 0.04 * n)
        occlusion.append(1.0 - 0.35 * d - 0.12 * g - 0.03 * (1.0 + n))
    albedo = tk.grade(albedo, p["hue_shift"], p["saturation"], p["brightness"])
    emissive = tk.grade(emissive, p["hue_shift"], 1.0, 1.0)
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.006, roughness=rough,
                     ao=occlusion, emissive=emissive, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
