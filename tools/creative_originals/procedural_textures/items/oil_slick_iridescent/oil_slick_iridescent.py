"""Iridescent oil slick: thin-film interference colours over wet asphalt, water, soap film or heat-tinted steel.

A film thickness field (domain-warped fractal noise in swirls, or bands that thin away from weld lines) is turned
into colour by two-beam thin-film interference at normal incidence: the reflectance at a wavelength is
r1^2 + r2^2 + 2 r1 r2 cos(4 pi n d / lambda), with Fresnel amplitudes r1 (air to film) and r2 (film to substrate)
from the refractive indices of the preset. The reflectance spectrum is weighted by a 6500 K illuminant and integrated
against an analytic approximation of the CIE 1931 colour-matching functions (sums of piecewise Gaussian lobes),
then converted from XYZ to linear sRGB. A table over thickness keeps that to one lookup per pixel.

On asphalt the film floats only on puddles: water fills the hollows of the asphalt height field up to a level set by
`coverage`, so the liquid is flat and glossy while the dry stone around it stays rough. Heat-tinted steel is a metal,
so its film colour becomes the metallic base colour.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "oil_slick_iridescent"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.01, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.03, 0.95]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "pattern", "type": "int", "default": 0, "minimum": 0, "maximum": 1,
     "meaning": "Thickness layout: 0 swirls of warped noise, 1 bands thinning away from weld lines."},
    {"name": "film_min", "type": "float", "default": 120.0, "minimum": 0.0, "maximum": 1200.0,
     "meaning": "Thinnest film in nanometres."},
    {"name": "film_max", "type": "float", "default": 900.0, "minimum": 50.0, "maximum": 1600.0,
     "meaning": "Thickest film in nanometres."},
    {"name": "scale", "type": "int", "default": 3, "minimum": 1, "maximum": 10,
     "meaning": "Swirls or bands across the tile."},
    {"name": "swirl", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Domain warping of the film into marbled swirls."},
    {"name": "coverage", "type": "float", "default": 0.55, "minimum": 0.05, "maximum": 1.0,
     "meaning": "Share of the surface under liquid (asphalt and water bases); 1 covers it all."},
    {"name": "vividness", "type": "float", "default": 1.0, "minimum": 0.3, "maximum": 3.0,
     "meaning": "Strength of the interference colours."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Oil on puddles in dark asphalt: rainbow swirls on flat water, dry rough stone around.",
                "values": {}},
    "harbour_water": {"description": "A spill on dark harbour water covering the whole surface in broad swirls.",
                      "values": {"coverage": 1.0, "scale": 2, "swirl": 0.85, "film_min": 200.0,
                                 "film_max": 1300.0}},
    "soap_film": {"description": "Soap film in air: vivid swirling bands that go black where the film is thinnest.",
                  "values": {"coverage": 1.0, "film_min": 0.0, "film_max": 700.0, "swirl": 0.9, "scale": 2,
                             "vividness": 1.4}},
    "tempered_steel": {"description": "Heat tint on steel: straw, bronze, purple and blue bands beside weld lines.",
                       "values": {"pattern": 1, "film_min": 12.0, "film_max": 82.0, "scale": 3, "swirl": 0.2,
                                  "coverage": 1.0, "vividness": 1.0}},
}
#: Per preset: (film index, substrate amplitude r2 or None to compute it from the substrate index, substrate index,
#: base colour sRGB, base kind) where base kind is 0 asphalt with puddles, 1 water, 2 dark backdrop, 3 metal. A
#: metal reflects with a phase shift, approximated here by a negative real amplitude, so a vanishing oxide film
#: leaves bright bare steel and thickening films remove blue, then green, then red (straw, purple, blue).
SURFACES = {
    "default": (1.45, None, 1.33, "#1a1a1c", 0),
    "harbour_water": (1.45, None, 1.33, "#0c1a1c", 1),
    "soap_film": (1.33, None, 1.0, "#050506", 2),
    "tempered_steel": (2.4, -0.6, 0.0, "#8a8c90", 3),
}


def _cie_xyz(wavelength: float) -> tuple:
    """CIE 1931 colour-matching functions at a wavelength in nanometres, as sums of piecewise Gaussian lobes."""

    def lobe(peak: float, below: float, above: float) -> float:
        t = (wavelength - peak) / (below if wavelength < peak else above)
        return math.exp(-0.5 * t * t)

    x = 1.056 * lobe(599.8, 37.9, 31.0) + 0.362 * lobe(442.0, 16.0, 26.7) - 0.065 * lobe(501.1, 20.4, 26.2)
    y = 0.821 * lobe(568.8, 46.9, 40.5) + 0.286 * lobe(530.9, 16.3, 31.1)
    z = 1.217 * lobe(437.0, 11.8, 36.0) + 0.681 * lobe(459.0, 26.0, 13.8)
    return x, y, z


def _illuminant(wavelength: float) -> float:
    metres = wavelength * 1e-9
    return 1.0 / (metres ** 5 * (math.exp(1.4388e-2 / (metres * 6500.0)) - 1.0))


#: (wavelength, illuminant x colour-matching weights) every 10 nm from 380 to 780 nm, and their luminance sum.
_SPECTRUM = [(380.0 + 10.0 * step, tuple(_illuminant(380.0 + 10.0 * step) * w for w in _cie_xyz(380.0 + 10.0 * step)))
             for step in range(41)]
_LUMINANCE = sum(weights[1] for _wavelength, weights in _SPECTRUM)
_TABLES = {}
#: Per base kind (asphalt, water, backdrop, metal): brightest film colour in linear units, and the share of the
#: film's grey reflectance kept under the hues.
GAINS = (0.22, 0.25, 0.85, 0.7)
GREY_KEPT = (0.15, 0.15, 0.3, 1.0)


def film_colour(thickness: float, film_index: float, r1: float, r2: float) -> tuple:
    """Linear sRGB reflectance of a thin film ``thickness`` nanometres thick under a 6500 K illuminant (two-beam
    interference at normal incidence, amplitudes r1 and r2); a perfect white mirror gives about 1."""
    x = y = z = 0.0
    phase = 4.0 * math.pi * film_index * thickness
    base, swing = r1 * r1 + r2 * r2, 2.0 * r1 * r2
    for wavelength, (wx, wy, wz) in _SPECTRUM:
        reflectance = base + swing * math.cos(phase / wavelength)
        x += reflectance * wx
        y += reflectance * wy
        z += reflectance * wz
    x, y, z = x / _LUMINANCE, y / _LUMINANCE, z / _LUMINANCE
    return (max(0.0, 3.2406 * x - 1.5372 * y - 0.4986 * z), max(0.0, -0.9689 * x + 1.8758 * y + 0.0415 * z),
            max(0.0, 0.0557 * x - 0.2040 * y + 1.0570 * z))


def _table(low: float, high: float, film_index: float, r1: float, r2: float, steps: int) -> list:
    key = (low, high, film_index, r1, r2, steps)
    if key not in _TABLES:
        _TABLES[key] = [film_colour(low + (high - low) * k / (steps - 1), film_index, r1, r2) for k in range(steps)]
    return _TABLES[key]


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The oil slick maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    film_index, substrate_amplitude, substrate_index, base_hex, base_kind = SURFACES[preset]
    r1 = (1.0 - film_index) / (1.0 + film_index)
    r2 = substrate_amplitude if substrate_amplitude is not None else \
        (film_index - substrate_index) / (film_index + substrate_index)
    low, high = sorted((p["film_min"], p["film_max"]))
    steps = 512
    # the film's grey share (the r1^2 + r2^2 term) is mostly removed so the interference hues carry the colour
    keep = GREY_KEPT[base_kind]
    table = [tuple(c - (1.0 - keep) * min(colour) for c in colour)
             for colour in _table(low, high, film_index, r1, r2, steps)]
    reference = max(max(colour) for colour in table) or 1.0
    scale = p["scale"]
    offset_u = tk.fbm(width, height, scale, 4, tk.hash_u32(seed, 1))
    offset_v = tk.fbm(width, height, scale, 4, tk.hash_u32(seed, 2))
    if p["pattern"] == 0:
        film = tk.fbm(width, height, scale, 5, tk.hash_u32(seed, 3), gain=0.45)
        film = tk.warp(film, width, height, offset_u, offset_v, 0.3 * p["swirl"])
        film = tk.warp(film, width, height, offset_v, offset_u, 0.15 * p["swirl"])
        film = [0.5 + 0.75 * f for f in film]
    else:
        bands = []
        jitter = tk.fbm(width, height, 4 * scale, 3, tk.hash_u32(seed, 4))
        for y in range(height):
            v = (y + 0.5) / height
            for x in range(width):
                index = y * width + x
                wave = v + 0.02 * math.sin(math.tau * ((x + 0.5) / width * 2.0)) + 0.015 * jitter[index]
                distance = abs(tk.wrap_delta(wave * scale)) * 2.0
                bands.append(math.exp(-1.8 * distance))
        film = tk.warp(bands, width, height, offset_u, offset_v, 0.05 * p["swirl"])
    film = [tk.clamp(f) for f in film]
    stone = tk.fbm(width, height, 24, 4, tk.hash_u32(seed, 5))
    hollows = tk.fbm(width, height, 3, 4, tk.hash_u32(seed, 6))
    ripples = tk.fbm(width, height, 12, 3, tk.hash_u32(seed, 7))
    grain = tk.white_noise(width, height, tk.hash_u32(seed, 8))
    base = [tk.srgb_to_linear(c) for c in tk.hex_rgb(base_hex)]
    gain = p["vividness"] * GAINS[base_kind] / reference
    ground = [0.55 * h + 0.12 * s + 0.05 * (g - 0.5) for h, s, g in zip(hollows, stone, grain)]
    ordered = sorted(ground)
    level = ordered[min(len(ordered) - 1, int(p["coverage"] * len(ordered)))] + (1.0 if p["coverage"] >= 1.0 else 0.0)
    lut = [tk.linear_to_srgb(k / 4095.0) for k in range(4096)]
    red, green, blue, heights, rough, metallic = [], [], [], [], [], []
    for index in range(width * height):
        colour = table[min(steps - 1, int(film[index] * (steps - 1) + 0.5))]
        if base_kind == 0:
            wet = tk.smoothstep(-0.012, 0.012, level - ground[index])
            surface_height = max(ground[index], level)
            speck = 0.7 + 0.6 * grain[index] + 0.3 * stone[index]
            dry = [b * speck for b in base]
            lit = [d * (1.0 - 0.35 * wet) + wet * gain * c for d, c in zip(dry, colour)]
            heights.append(0.5 + 0.6 * surface_height)
            rough.append(0.9 - 0.85 * wet + 0.05 * grain[index] * (1.0 - wet))
            metallic.append(0.0)
        elif base_kind == 1:
            lit = [b * (0.85 + 0.3 * grain[index]) + gain * c for b, c in zip(base, colour)]
            heights.append(0.5 + 0.08 * ripples[index] + 0.03 * hollows[index])
            rough.append(0.04 + 0.03 * (0.5 + 0.5 * ripples[index]))
            metallic.append(0.0)
        elif base_kind == 2:
            lit = [b + gain * c for b, c in zip(base, colour)]
            heights.append(0.5 + 0.1 * film[index] + 0.02 * ripples[index])
            rough.append(0.03 + 0.02 * film[index])
            metallic.append(0.0)
        else:
            streak = 0.5 + 0.5 * stone[index]
            lit = [0.25 * b * (0.8 + 0.4 * streak) + gain * c for b, c in zip(base, colour)]
            heights.append(0.5 + 0.06 * stone[index] + 0.04 * (grain[index] - 0.5) + 0.05 * film[index])
            rough.append(0.3 + 0.12 * streak)
            metallic.append(1.0)
        red.append(lut[int(min(1.0, lit[0]) * 4095.0 + 0.5)])
        green.append(lut[int(min(1.0, lit[1]) * 4095.0 + 0.5)])
        blue.append(lut[int(min(1.0, lit[2]) * 4095.0 + 0.5)])
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.012, roughness=rough,
                     metallic=metallic, ao_radius=0.02, ao_strength=0.9, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
