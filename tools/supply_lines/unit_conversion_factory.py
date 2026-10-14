"""Template 3: Deterministic Engineering and Scientific Unit Conversion Factory.

Generates 60 deterministic unit conversion component packages across 12 physical
dimensions (5 components per dimension) using NIST SP 811 and CODATA constants.

Every generated component includes:
- implement.py: convert(value, from_unit, to_unit) and round-trip verification
- test_implement.py: reference test cases, 1e-9 round-trip checks, unknown unit refusals, and known-wrong controls
- SKILL.md and harness integration guides (claude-code, codex, cursor, opencode)
- LICENSE (MIT) and ATTRIBUTION.md
- CataloguePackage with SHA-256 digests and local preview metadata, not an admission record
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import sys
from typing import Any

_REPO_SRC = str(Path(__file__).resolve().parents[2] / "src")
if _REPO_SRC not in sys.path:
    sys.path.insert(0, _REPO_SRC)

from loop_engine.core.service_runtime.catalogue_packages import (
    PACKAGE_BODY,
    CataloguePackage,
    CataloguePackageFile,
    sha256_hex,
)

FACTORY_ID = "gen-conversion-tables"
FACTORY_VERSION = "1.0.0"
GENERATED_ON = "2026-10-13"
ROUND_TRIP_TOLERANCE = 1e-9

MIT_LICENSE_TEXT = (
    "MIT License\n\n"
    "Copyright (c) 2026 Alie Jie Li\n\n"
    "Permission is hereby granted, free of charge, to any person obtaining a copy "
    "of this software and associated documentation files (the \"Software\"), to deal "
    "in the Software without restriction, including without limitation the rights "
    "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell "
    "copies of the Software, and to permit persons to whom the Software is "
    "furnished to do so, subject to the following conditions:\n\n"
    "The above copyright notice and this permission notice shall be included in all "
    "copies or substantial portions of the Software.\n\n"
    "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR "
    "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, "
    "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR "
    "COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN "
    "ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE "
    "SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.\n"
)

DIMENSIONS = (
    "length",
    "mass",
    "time",
    "temperature",
    "data_size",
    "speed",
    "pressure",
    "energy",
    "power",
    "angle",
    "frequency",
    "volume_flow",
)


@dataclass(frozen=True)
class UnitConversionSpec:
    component_id: str
    dimension: str
    title: str
    base_unit: str
    description: str
    # Each unit maps to (scale, offset) such that base_value = value * scale + offset
    units: dict[str, tuple[float, float]]
    reference_cases: tuple[tuple[float, str, str, float], ...]


def _linear(mapping: dict[str, float]) -> dict[str, tuple[float, float]]:
    return {unit: (float(factor), 0.0) for unit, factor in mapping.items()}


UNIT_CONVERSION_SPECS: tuple[UnitConversionSpec, ...] = (
    # 1. length (5 components)
    UnitConversionSpec(
        component_id="length-si-metric",
        dimension="length",
        title="SI metric length converter (nm to km)",
        base_unit="m",
        description="Converts metric lengths across nanometers, micrometers, millimeters, centimeters, meters, and kilometers.",
        units=_linear({"m": 1.0, "km": 1000.0, "cm": 0.01, "mm": 0.001, "um": 1e-6, "nm": 1e-9}),
        reference_cases=((1.0, "km", "m", 1000.0), (250.0, "cm", "m", 2.5), (1000.0, "mm", "m", 1.0)),
    ),
    UnitConversionSpec(
        component_id="length-imperial-survey",
        dimension="length",
        title="Imperial and US survey length converter",
        base_unit="m",
        description="Converts inches, feet, yards, miles, chains, and furlongs using the exact international foot (0.3048 m).",
        units=_linear({"m": 1.0, "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "chain": 20.1168, "furlong": 201.168, "mi": 1609.344}),
        reference_cases=((12.0, "in", "ft", 1.0), (3.0, "ft", "yd", 1.0), (1.0, "mi", "ft", 5280.0)),
    ),
    UnitConversionSpec(
        component_id="length-nautical-marine",
        dimension="length",
        title="Marine and nautical length converter",
        base_unit="m",
        description="Converts meters, kilometers, international nautical miles (1852 m), fathoms, and cables.",
        units=_linear({"m": 1.0, "km": 1000.0, "nmi": 1852.0, "cable": 185.2, "fathom": 1.8288}),
        reference_cases=((1.0, "nmi", "m", 1852.0), (10.0, "cable", "nmi", 1.0), (100.0, "fathom", "m", 182.88)),
    ),
    UnitConversionSpec(
        component_id="length-astronomy-parsec",
        dimension="length",
        title="Astronomical distance converter (AU, light-year, parsec)",
        base_unit="m",
        description="Converts astronomical units (IAU 2012 exact), light-years, parsecs, kiloparsecs, and kilometers.",
        units=_linear({"m": 1.0, "km": 1000.0, "au": 149597870700.0, "ly": 9460730472580800.0, "pc": 3.0856775814913673e16, "kpc": 3.0856775814913673e19}),
        reference_cases=((1.0, "au", "km", 149597870.7), (1.0, "kpc", "pc", 1000.0), (1.0, "ly", "m", 9460730472580800.0)),
    ),
    UnitConversionSpec(
        component_id="length-typography-machining",
        dimension="length",
        title="Typography and precision machining length converter",
        base_unit="m",
        description="Converts millimeters, inches, thousandths of an inch (mil), desktop publishing points (1/72 in), and picas.",
        units=_linear({"m": 1.0, "mm": 0.001, "in": 0.0254, "mil": 0.0000254, "pt": 0.0254 / 72.0, "pica": 0.0254 / 6.0}),
        reference_cases=((1000.0, "mil", "in", 1.0), (72.0, "pt", "in", 1.0), (12.0, "pt", "pica", 1.0)),
    ),
    # 2. mass (5 components)
    UnitConversionSpec(
        component_id="mass-si-metric",
        dimension="mass",
        title="SI metric mass converter (ug to metric ton)",
        base_unit="kg",
        description="Converts micrograms, milligrams, grams, kilograms, and metric tonnes.",
        units=_linear({"kg": 1.0, "g": 0.001, "mg": 1e-6, "ug": 1e-9, "t": 1000.0}),
        reference_cases=((1.0, "t", "kg", 1000.0), (1000.0, "g", "kg", 1.0), (1000.0, "mg", "g", 1.0)),
    ),
    UnitConversionSpec(
        component_id="mass-avoirdupois-imperial",
        dimension="mass",
        title="Avoirdupois imperial and US mass converter",
        base_unit="kg",
        description="Converts kilograms, pounds, ounces, stones, US short tons, and UK long tons.",
        units=_linear({"kg": 1.0, "lb": 0.45359237, "oz": 0.028349523125, "st": 6.35029318, "short_ton": 907.18474, "long_ton": 1016.0469088}),
        reference_cases=((16.0, "oz", "lb", 1.0), (14.0, "lb", "st", 1.0), (1.0, "short_ton", "lb", 2000.0)),
    ),
    UnitConversionSpec(
        component_id="mass-precious-troy",
        dimension="mass",
        title="Precious metals and gemology mass converter (troy oz, carat, grain)",
        base_unit="kg",
        description="Converts grams, troy ounces, troy pounds, pennyweights, metric carats, and grains.",
        units=_linear({"kg": 1.0, "g": 0.001, "grain": 0.00006479891, "carat": 0.0002, "pennyweight": 0.00155517384, "troy_oz": 0.0311034768, "troy_lb": 0.3732417216}),
        reference_cases=((5.0, "carat", "g", 1.0), (20.0, "pennyweight", "troy_oz", 1.0), (12.0, "troy_oz", "troy_lb", 1.0)),
    ),
    UnitConversionSpec(
        component_id="mass-atomic-dalton",
        dimension="mass",
        title="Atomic and molecular mass converter (Dalton to kg)",
        base_unit="kg",
        description="Converts unified atomic mass units (Daltons, kilodaltons, megadaltons) and grams/kilograms.",
        units=_linear({"kg": 1.0, "g": 0.001, "Da": 1.66053906660e-27, "kDa": 1.66053906660e-24, "MDa": 1.66053906660e-21}),
        reference_cases=((1000.0, "Da", "kDa", 1.0), (1000.0, "kDa", "MDa", 1.0), (1.0, "kg", "g", 1000.0)),
    ),
    UnitConversionSpec(
        component_id="mass-freight-shipping",
        dimension="mass",
        title="Freight and cargo hundredweight mass converter",
        base_unit="kg",
        description="Converts kilograms, metric tonnes, pounds, US hundredweight (cwt_us), and UK imperial hundredweight (cwt_uk).",
        units=_linear({"kg": 1.0, "t": 1000.0, "lb": 0.45359237, "cwt_us": 45.359237, "cwt_uk": 50.80234544}),
        reference_cases=((1.0, "cwt_us", "lb", 100.0), (1.0, "cwt_uk", "lb", 112.0), (1.0, "t", "kg", 1000.0)),
    ),
    # 3. time (5 components)
    UnitConversionSpec(
        component_id="time-subsecond-clock",
        dimension="time",
        title="Subsecond high-resolution clock converter (ps to s)",
        base_unit="s",
        description="Converts seconds, milliseconds, microseconds, nanoseconds, and picoseconds.",
        units=_linear({"s": 1.0, "ms": 1e-3, "us": 1e-6, "ns": 1e-9, "ps": 1e-12}),
        reference_cases=((1.0, "s", "ms", 1000.0), (1.0, "ms", "us", 1000.0), (1.0, "us", "ns", 1000.0)),
    ),
    UnitConversionSpec(
        component_id="time-calendar-standard",
        dimension="time",
        title="Standard civil time duration converter (s to wk)",
        base_unit="s",
        description="Converts seconds, minutes, hours, days (86400 s), and weeks (604800 s).",
        units=_linear({"s": 1.0, "min": 60.0, "h": 3600.0, "d": 86400.0, "wk": 604800.0}),
        reference_cases=((60.0, "min", "h", 1.0), (24.0, "h", "d", 1.0), (7.0, "d", "wk", 1.0)),
    ),
    UnitConversionSpec(
        component_id="time-astronomy-epochs",
        dimension="time",
        title="Astronomical epoch and orbital period converter",
        base_unit="s",
        description="Converts seconds, solar days, IAU Julian years (365.25 d), sidereal days, and synodic months.",
        units=_linear({"s": 1.0, "d": 86400.0, "julian_year": 31557600.0, "sidereal_day": 86164.0905, "synodic_month": 2551442.8896}),
        reference_cases=((1.0, "julian_year", "d", 365.25), (1.0, "d", "s", 86400.0), (1.0, "sidereal_day", "s", 86164.0905)),
    ),
    UnitConversionSpec(
        component_id="time-compute-ticks",
        dimension="time",
        title="Real-time rendering frame and kernel tick converter",
        base_unit="s",
        description="Converts seconds, milliseconds, 60 Hz frame intervals, 24 Hz cinema frames, and 100 Hz kernel jiffies.",
        units=_linear({"s": 1.0, "ms": 0.001, "frame_60hz": 1.0 / 60.0, "frame_24hz": 1.0 / 24.0, "jiffy_100hz": 0.01}),
        reference_cases=((60.0, "frame_60hz", "s", 1.0), (24.0, "frame_24hz", "s", 1.0), (100.0, "jiffy_100hz", "s", 1.0)),
    ),
    UnitConversionSpec(
        component_id="time-historical-decades",
        dimension="time",
        title="Long-horizon calendar span converter (days to millennia)",
        base_unit="s",
        description="Converts days, 365-day standard years, decades, centuries, and millennia.",
        units=_linear({"s": 1.0, "d": 86400.0, "yr_365": 31536000.0, "decade": 315360000.0, "century": 3153600000.0, "millennium": 31536000000.0}),
        reference_cases=((10.0, "yr_365", "decade", 1.0), (10.0, "decade", "century", 1.0), (10.0, "century", "millennium", 1.0)),
    ),
    # 4. temperature (5 affine components)
    UnitConversionSpec(
        component_id="temperature-thermodynamic-core",
        dimension="temperature",
        title="Thermodynamic temperature converter (Kelvin, Celsius, Fahrenheit)",
        base_unit="K",
        description="Affine conversion across Kelvin, degrees Celsius, and degrees Fahrenheit.",
        units={"K": (1.0, 0.0), "C": (1.0, 273.15), "F": (5.0 / 9.0, 459.67 * 5.0 / 9.0)},
        reference_cases=((0.0, "C", "F", 32.0), (100.0, "C", "K", 373.15), (-40.0, "C", "F", -40.0)),
    ),
    UnitConversionSpec(
        component_id="temperature-engineering-rankine",
        dimension="temperature",
        title="Engineering thermodynamic Rankine converter",
        base_unit="K",
        description="Affine conversion across Kelvin, Rankine, Celsius, and Fahrenheit for propulsion and steam tables.",
        units={"K": (1.0, 0.0), "R": (5.0 / 9.0, 0.0), "C": (1.0, 273.15), "F": (5.0 / 9.0, 459.67 * 5.0 / 9.0)},
        reference_cases=((0.0, "K", "R", 0.0), (273.15, "K", "R", 491.67), (32.0, "F", "R", 491.67)),
    ),
    UnitConversionSpec(
        component_id="temperature-cryogenic-kelvin",
        dimension="temperature",
        title="Cryogenic millikelvin and Kelvin converter",
        base_unit="K",
        description="Converts millikelvin, Kelvin, Celsius, and Rankine for low-temperature physics.",
        units={"K": (1.0, 0.0), "mK": (0.001, 0.0), "C": (1.0, 273.15), "R": (5.0 / 9.0, 0.0)},
        reference_cases=((1000.0, "mK", "K", 1.0), (4200.0, "mK", "K", 4.2), (0.0, "C", "mK", 273150.0)),
    ),
    UnitConversionSpec(
        component_id="temperature-metallurgy-furnace",
        dimension="temperature",
        title="Metallurgical heat-treatment temperature converter",
        base_unit="K",
        description="Converts high-temperature furnace setpoints across Celsius, Fahrenheit, Kelvin, and Rankine.",
        units={"K": (1.0, 0.0), "C": (1.0, 273.15), "F": (5.0 / 9.0, 459.67 * 5.0 / 9.0), "R": (5.0 / 9.0, 0.0)},
        reference_cases=((1000.0, "C", "F", 1832.0), (1000.0, "C", "K", 1273.15), (212.0, "F", "C", 100.0)),
    ),
    UnitConversionSpec(
        component_id="temperature-hvac-ambient",
        dimension="temperature",
        title="HVAC ambient and dew-point temperature converter",
        base_unit="K",
        description="Converts ambient building and psychrometric temperatures across Celsius, Fahrenheit, and Kelvin.",
        units={"K": (1.0, 0.0), "C": (1.0, 273.15), "F": (5.0 / 9.0, 459.67 * 5.0 / 9.0)},
        reference_cases=((20.0, "C", "F", 68.0), (25.0, "C", "F", 77.0), (68.0, "F", "K", 293.15)),
    ),
    # 5. data_size (5 components)
    UnitConversionSpec(
        component_id="data-decimal-si-bytes",
        dimension="data_size",
        title="SI decimal byte capacity converter (B to PB)",
        base_unit="B",
        description="Converts bytes, kilobytes (10^3), megabytes (10^6), gigabytes (10^9), terabytes (10^12), and petabytes (10^15).",
        units=_linear({"B": 1.0, "kB": 1e3, "MB": 1e6, "GB": 1e9, "TB": 1e12, "PB": 1e15}),
        reference_cases=((1.0, "GB", "MB", 1000.0), (1.0, "TB", "GB", 1000.0), (1000.0, "kB", "MB", 1.0)),
    ),
    UnitConversionSpec(
        component_id="data-binary-iec-bytes",
        dimension="data_size",
        title="IEC 80000-13 binary byte capacity converter (B to PiB)",
        base_unit="B",
        description="Converts bytes, kibibytes (2^10), mebibytes (2^20), gibibytes (2^30), tebibytes (2^40), and pebibytes (2^50).",
        units=_linear({"B": 1.0, "KiB": 1024.0, "MiB": 1048576.0, "GiB": 1073741824.0, "TiB": 1099511627776.0, "PiB": 1125899906842624.0}),
        reference_cases=((1.0, "KiB", "B", 1024.0), (1.0, "GiB", "MiB", 1024.0), (1.0, "TiB", "GiB", 1024.0)),
    ),
    UnitConversionSpec(
        component_id="data-network-bits",
        dimension="data_size",
        title="Network payload bit and byte converter",
        base_unit="B",
        description="Converts bits, kilobits, megabits, gigabits, terabits, and 8-bit octets (bytes).",
        units=_linear({"B": 1.0, "bit": 0.125, "kbit": 125.0, "Mbit": 125000.0, "Gbit": 1.25e8, "Tbit": 1.25e11}),
        reference_cases=((8.0, "bit", "B", 1.0), (8.0, "Mbit", "B", 1000000.0), (1.0, "Gbit", "Mbit", 1000.0)),
    ),
    UnitConversionSpec(
        component_id="data-storage-sectors",
        dimension="data_size",
        title="Block storage sector and page size converter",
        base_unit="B",
        description="Converts bytes, KiB, MiB, 512-byte disk sectors, 4 KiB memory pages, and 64 KiB database blocks.",
        units=_linear({"B": 1.0, "KiB": 1024.0, "MiB": 1048576.0, "sector_512B": 512.0, "page_4KiB": 4096.0, "block_64KiB": 65536.0}),
        reference_cases=((8.0, "sector_512B", "page_4KiB", 1.0), (16.0, "page_4KiB", "block_64KiB", 1.0), (16.0, "block_64KiB", "MiB", 1.0)),
    ),
    UnitConversionSpec(
        component_id="data-memory-words",
        dimension="data_size",
        title="Machine word, dword, and qword width converter",
        base_unit="B",
        description="Converts bits, 4-bit nibbles, bytes, 16-bit words, 32-bit doublewords, and 64-bit quadwords.",
        units=_linear({"B": 1.0, "bit": 0.125, "nibble": 0.5, "word_16bit": 2.0, "dword_32bit": 4.0, "qword_64bit": 8.0}),
        reference_cases=((2.0, "nibble", "B", 1.0), (2.0, "word_16bit", "dword_32bit", 1.0), (2.0, "dword_32bit", "qword_64bit", 1.0)),
    ),
    # 6. speed (5 components)
    UnitConversionSpec(
        component_id="speed-kinematic-standard",
        dimension="speed",
        title="Kinematic terrestrial speed converter (m/s, km/h, mph, ft/s)",
        base_unit="m_s",
        description="Converts meters per second, kilometers per hour, miles per hour, and feet per second.",
        units=_linear({"m_s": 1.0, "km_h": 1.0 / 3.6, "mph": 0.44704, "ft_s": 0.3048}),
        reference_cases=((10.0, "m_s", "km_h", 36.0), (60.0, "mph", "ft_s", 88.0), (100.0, "ft_s", "m_s", 30.48)),
    ),
    UnitConversionSpec(
        component_id="speed-aviation-marine",
        dimension="speed",
        title="Aviation and maritime speed converter (knots, Mach ISA)",
        base_unit="m_s",
        description="Converts meters per second, knots (1852 m/h), km/h, mph, and ISA sea-level Mach number (340.29 m/s).",
        units=_linear({"m_s": 1.0, "kn": 1852.0 / 3600.0, "km_h": 1.0 / 3.6, "mph": 0.44704, "mach_isa": 340.29}),
        reference_cases=((1.0, "kn", "km_h", 1.852), (1.0, "mach_isa", "m_s", 340.29), (36.0, "km_h", "m_s", 10.0)),
    ),
    UnitConversionSpec(
        component_id="speed-orbital-ballistic",
        dimension="speed",
        title="Orbital and ballistic velocity converter (km/s, mi/s)",
        base_unit="m_s",
        description="Converts meters per second, kilometers per second, kilometers per hour, and miles per second.",
        units=_linear({"m_s": 1.0, "km_s": 1000.0, "km_h": 1.0 / 3.6, "mi_s": 1609.344}),
        reference_cases=((7.8, "km_s", "m_s", 7800.0), (1.0, "mi_s", "m_s", 1609.344), (1.0, "km_s", "km_h", 3600.0)),
    ),
    UnitConversionSpec(
        component_id="speed-manufacturing-feed",
        dimension="speed",
        title="CNC machining feed-rate speed converter (mm/min, in/min, ft/min)",
        base_unit="m_s",
        description="Converts meters per second, millimeters per second, millimeters per minute, inches per minute, and surface feet per minute.",
        units=_linear({"m_s": 1.0, "mm_s": 0.001, "mm_min": 0.001 / 60.0, "in_min": 0.0254 / 60.0, "ft_min": 0.3048 / 60.0}),
        reference_cases=((60.0, "mm_min", "mm_s", 1.0), (12.0, "in_min", "ft_min", 1.0), (1000.0, "mm_s", "m_s", 1.0)),
    ),
    UnitConversionSpec(
        component_id="speed-geophysical-creep",
        dimension="speed",
        title="Geophysical tectonic plate and glacier creep velocity converter",
        base_unit="m_s",
        description="Converts meters per second, meters per day, centimeters per Julian year, and millimeters per Julian year.",
        units=_linear({"m_s": 1.0, "m_day": 1.0 / 86400.0, "cm_yr": 0.01 / 31557600.0, "mm_yr": 0.001 / 31557600.0}),
        reference_cases=((10.0, "mm_yr", "cm_yr", 1.0), (86400.0, "m_day", "m_s", 1.0), (100.0, "cm_yr", "mm_yr", 1000.0)),
    ),
    # 7. pressure (5 components)
    UnitConversionSpec(
        component_id="pressure-si-pascal",
        dimension="pressure",
        title="SI Pascal pressure converter (Pa to GPa)",
        base_unit="Pa",
        description="Converts Pascals, hectopascals, kilopascals, megapascals, and gigapascals.",
        units=_linear({"Pa": 1.0, "hPa": 100.0, "kPa": 1000.0, "MPa": 1e6, "GPa": 1e9}),
        reference_cases=((10.0, "hPa", "kPa", 1.0), (1000.0, "kPa", "MPa", 1.0), (1000.0, "MPa", "GPa", 1.0)),
    ),
    UnitConversionSpec(
        component_id="pressure-atmospheric-bar",
        dimension="pressure",
        title="Barometric and standard atmospheric pressure converter",
        base_unit="Pa",
        description="Converts Pascals, bars, millibars, standard atmospheres (101325 Pa), and Torr.",
        units=_linear({"Pa": 1.0, "bar": 100000.0, "mbar": 100.0, "atm": 101325.0, "torr": 101325.0 / 760.0}),
        reference_cases=((1.0, "bar", "mbar", 1000.0), (1.0, "atm", "torr", 760.0), (1.0, "atm", "Pa", 101325.0)),
    ),
    UnitConversionSpec(
        component_id="pressure-hydraulic-imperial",
        dimension="pressure",
        title="Hydraulic and structural stress converter (psi, ksi, bar, MPa)",
        base_unit="Pa",
        description="Converts Pascals, kilopascals, megapascals, bars, pounds per square inch (psi), and kips per square inch (ksi).",
        units=_linear({"Pa": 1.0, "kPa": 1000.0, "MPa": 1e6, "bar": 100000.0, "psi": 6894.757293168, "ksi": 6894757.293168}),
        reference_cases=((1000.0, "psi", "ksi", 1.0), (1.0, "bar", "kPa", 100.0), (1.0, "MPa", "bar", 10.0)),
    ),
    UnitConversionSpec(
        component_id="pressure-manometric-column",
        dimension="pressure",
        title="Manometric fluid-column pressure converter (mmHg, inHg, mmH2O)",
        base_unit="Pa",
        description="Converts Pascals, millimeters of mercury, inches of mercury, millimeters of water, and inches of water.",
        units=_linear({"Pa": 1.0, "mmHg": 133.322387415, "inHg": 3386.388640341, "mmH2O": 9.80665, "inH2O": 249.08891}),
        reference_cases=((1.0, "inH2O", "mmH2O", 25.4), (1.0, "mmH2O", "Pa", 9.80665), (1.0, "inHg", "mmHg", 25.4)),
    ),
    UnitConversionSpec(
        component_id="pressure-vacuum-chamber",
        dimension="pressure",
        title="High-vacuum chamber pressure converter (mPa, Torr, mTorr, mbar)",
        base_unit="Pa",
        description="Converts Pascals, millipascals, Torr, millitorr (microns of Hg), and millibars.",
        units=_linear({"Pa": 1.0, "mPa": 0.001, "torr": 101325.0 / 760.0, "mtorr": 101325.0 / 760000.0, "mbar": 100.0}),
        reference_cases=((1000.0, "mtorr", "torr", 1.0), (1000.0, "mPa", "Pa", 1.0), (1.0, "mbar", "Pa", 100.0)),
    ),
    # 8. energy (5 components)
    UnitConversionSpec(
        component_id="energy-si-mechanical",
        dimension="energy",
        title="SI mechanical energy converter (erg to GJ)",
        base_unit="J",
        description="Converts Joules, kilojoules, megajoules, gigajoules, and CGS ergs.",
        units=_linear({"J": 1.0, "kJ": 1000.0, "MJ": 1e6, "GJ": 1e9, "erg": 1e-7}),
        reference_cases=((1.0, "J", "erg", 1e7), (1000.0, "kJ", "MJ", 1.0), (1000.0, "MJ", "GJ", 1.0)),
    ),
    UnitConversionSpec(
        component_id="energy-electrical-grid",
        dimension="energy",
        title="Electrical utility energy converter (Wh to GWh)",
        base_unit="J",
        description="Converts Joules, watt-hours, kilowatt-hours, megawatt-hours, and gigawatt-hours.",
        units=_linear({"J": 1.0, "Wh": 3600.0, "kWh": 3.6e6, "MWh": 3.6e9, "GWh": 3.6e12}),
        reference_cases=((1.0, "Wh", "J", 3600.0), (1.0, "kWh", "J", 3600000.0), (1000.0, "kWh", "MWh", 1.0)),
    ),
    UnitConversionSpec(
        component_id="energy-thermal-calorimetric",
        dimension="energy",
        title="Thermal and calorimetric energy converter (cal, kcal, BTU, therm)",
        base_unit="J",
        description="Converts Joules, thermochemical calories, kilocalories, IT British thermal units, and US therms.",
        units=_linear({"J": 1.0, "cal": 4.184, "kcal": 4184.0, "btu": 1055.05585262, "therm_us": 105505585.262}),
        reference_cases=((1.0, "kcal", "cal", 1000.0), (1.0, "cal", "J", 4.184), (1.0, "therm_us", "btu", 100000.0)),
    ),
    UnitConversionSpec(
        component_id="energy-particle-physics",
        dimension="energy",
        title="Particle physics electronvolt energy converter (eV to TeV)",
        base_unit="J",
        description="Converts Joules and SI-exact electronvolts (eV, keV, MeV, GeV, TeV).",
        units=_linear({"J": 1.0, "eV": 1.602176634e-19, "keV": 1.602176634e-16, "MeV": 1.602176634e-13, "GeV": 1.602176634e-10, "TeV": 1.602176634e-7}),
        reference_cases=((1000.0, "eV", "keV", 1.0), (1000.0, "MeV", "GeV", 1.0), (1000.0, "GeV", "TeV", 1.0)),
    ),
    UnitConversionSpec(
        component_id="energy-mechanical-imperial",
        dimension="energy",
        title="Imperial mechanical work and torque-energy converter",
        base_unit="J",
        description="Converts Joules, foot-pounds-force (ft_lbf), inch-pounds-force (in_lbf), and horsepower-hours.",
        units=_linear({"J": 1.0, "ft_lbf": 1.3558179483314004, "in_lbf": 0.1129848290276167, "hp_h": 2684519.5376961727}),
        reference_cases=((1.0, "ft_lbf", "in_lbf", 12.0), (1980000.0, "ft_lbf", "hp_h", 1.0), (1.0, "ft_lbf", "J", 1.3558179483314004)),
    ),
    # 9. power (5 components)
    UnitConversionSpec(
        component_id="power-si-watt",
        dimension="power",
        title="SI electrical and mechanical power converter (uW to GW)",
        base_unit="W",
        description="Converts microwatts, milliwatts, watts, kilowatts, megawatts, and gigawatts.",
        units=_linear({"W": 1.0, "uW": 1e-6, "mW": 1e-3, "kW": 1e3, "MW": 1e6, "GW": 1e9}),
        reference_cases=((1000.0, "mW", "W", 1.0), (1000.0, "W", "kW", 1.0), (1000.0, "kW", "MW", 1.0)),
    ),
    UnitConversionSpec(
        component_id="power-automotive-mechanical",
        dimension="power",
        title="Automotive and shaft horsepower converter",
        base_unit="W",
        description="Converts watts, kilowatts, imperial mechanical horsepower (550 ft*lbf/s), metric horsepower (PS), and ft*lbf/s.",
        units=_linear({"W": 1.0, "kW": 1000.0, "hp_mechanical": 745.6998715822702, "hp_metric": 735.49875, "ft_lbf_s": 1.3558179483314004}),
        reference_cases=((1.0, "hp_mechanical", "ft_lbf_s", 550.0), (1.0, "hp_metric", "W", 735.49875), (1.0, "kW", "W", 1000.0)),
    ),
    UnitConversionSpec(
        component_id="power-hvac-thermal",
        dimension="power",
        title="HVAC cooling and thermal heat-transfer power converter",
        base_unit="W",
        description="Converts watts, kilowatts, BTU per hour, tons of refrigeration (12000 BTU/h), and kcal per hour.",
        units=_linear({"W": 1.0, "kW": 1000.0, "btu_h": 1055.05585262 / 3600.0, "ton_refrigeration": 12000.0 * 1055.05585262 / 3600.0, "kcal_h": 4184.0 / 3600.0}),
        reference_cases=((1.0, "ton_refrigeration", "btu_h", 12000.0), (3600.0, "kcal_h", "W", 4184.0), (1.0, "kW", "W", 1000.0)),
    ),
    UnitConversionSpec(
        component_id="power-industrial-boiler",
        dimension="power",
        title="Industrial steam boiler power converter",
        base_unit="W",
        description="Converts watts, kilowatts, megawatts, boiler horsepower (9809.5 W), and million BTU per hour (MBtu_h).",
        units=_linear({"W": 1.0, "kW": 1000.0, "MW": 1e6, "hp_boiler": 9809.5, "MBtu_h": 1e6 * 1055.05585262 / 3600.0}),
        reference_cases=((1.0, "hp_boiler", "W", 9809.5), (1.0, "MW", "kW", 1000.0), (1000.0, "W", "kW", 1.0)),
    ),
    UnitConversionSpec(
        component_id="power-radiant-solar",
        dimension="power",
        title="Radiant flux and calorimetric power converter (erg/s, cal/s, W)",
        base_unit="W",
        description="Converts watts, milliwatts, kilowatts, ergs per second, and calories per second.",
        units=_linear({"W": 1.0, "mW": 0.001, "kW": 1000.0, "erg_s": 1e-7, "cal_s": 4.184}),
        reference_cases=((1.0, "W", "erg_s", 1e7), (1.0, "cal_s", "W", 4.184), (1.0, "W", "mW", 1000.0)),
    ),
    # 10. angle (5 components)
    UnitConversionSpec(
        component_id="angle-trigonometric-core",
        dimension="angle",
        title="Trigonometric plane angle converter (rad, mrad, deg, turn)",
        base_unit="rad",
        description="Converts radians, milliradians, degrees, and full turns (2*pi rad).",
        units=_linear({"rad": 1.0, "mrad": 0.001, "deg": math.pi / 180.0, "turn": 2.0 * math.pi}),
        reference_cases=((180.0, "deg", "rad", math.pi), (1.0, "turn", "deg", 360.0), (1.0, "rad", "mrad", 1000.0)),
    ),
    UnitConversionSpec(
        component_id="angle-astronomy-astrometry",
        dimension="angle",
        title="Astrometric angular resolution converter (deg, arcmin, arcsec, mas)",
        base_unit="rad",
        description="Converts radians, degrees, arcminutes, arcseconds, and milliarcseconds.",
        units=_linear({"rad": 1.0, "deg": math.pi / 180.0, "arcmin": math.pi / 10800.0, "arcsec": math.pi / 648000.0, "mas": math.pi / 6.48e8}),
        reference_cases=((1.0, "deg", "arcmin", 60.0), (1.0, "arcmin", "arcsec", 60.0), (1.0, "arcsec", "mas", 1000.0)),
    ),
    UnitConversionSpec(
        component_id="angle-surveying-geodesy",
        dimension="angle",
        title="Geodetic and surveying angle converter (grad, gon, deg, turn)",
        base_unit="rad",
        description="Converts radians, degrees, gradians (1/400 turn), gons, and full turns.",
        units=_linear({"rad": 1.0, "deg": math.pi / 180.0, "grad": math.pi / 200.0, "gon": math.pi / 200.0, "turn": 2.0 * math.pi}),
        reference_cases=((100.0, "grad", "deg", 90.0), (400.0, "gon", "turn", 1.0), (1.0, "grad", "gon", 1.0)),
    ),
    UnitConversionSpec(
        component_id="angle-artillery-ballistic",
        dimension="angle",
        title="Angular mil and ballistic sighting converter",
        base_unit="rad",
        description="Converts radians, milliradians, degrees, NATO mils (1/6400 turn), and Swedish streck (1/6300 turn).",
        units=_linear({"rad": 1.0, "mrad": 0.001, "deg": math.pi / 180.0, "mil_nato": 2.0 * math.pi / 6400.0, "mil_swedish": 2.0 * math.pi / 6300.0}),
        reference_cases=((6400.0, "mil_nato", "deg", 360.0), (6300.0, "mil_swedish", "deg", 360.0), (1.0, "rad", "mrad", 1000.0)),
    ),
    UnitConversionSpec(
        component_id="angle-navigation-compass",
        dimension="angle",
        title="Maritime compass point and bearing converter",
        base_unit="rad",
        description="Converts radians, degrees, 32-wind compass points (11.25 deg), gradians, and turns.",
        units=_linear({"rad": 1.0, "deg": math.pi / 180.0, "point_compass": math.pi / 16.0, "grad": math.pi / 200.0, "turn": 2.0 * math.pi}),
        reference_cases=((32.0, "point_compass", "turn", 1.0), (1.0, "point_compass", "deg", 11.25), (8.0, "point_compass", "deg", 90.0)),
    ),
    # 11. frequency (5 components)
    UnitConversionSpec(
        component_id="frequency-si-hertz",
        dimension="frequency",
        title="SI electromagnetic frequency converter (Hz to THz)",
        base_unit="Hz",
        description="Converts hertz, kilohertz, megahertz, gigahertz, and terahertz.",
        units=_linear({"Hz": 1.0, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9, "THz": 1e12}),
        reference_cases=((1000.0, "Hz", "kHz", 1.0), (1000.0, "MHz", "GHz", 1.0), (1000.0, "GHz", "THz", 1.0)),
    ),
    UnitConversionSpec(
        component_id="frequency-rotational-mechanical",
        dimension="frequency",
        title="Rotational shaft speed and angular frequency converter (rpm, rps, rad/s)",
        base_unit="Hz",
        description="Converts cycles per second (Hz), revolutions per minute (rpm), revolutions per second (rps), radians per second, and degrees per second.",
        units=_linear({"Hz": 1.0, "rps": 1.0, "rpm": 1.0 / 60.0, "rad_s": 1.0 / (2.0 * math.pi), "deg_s": 1.0 / 360.0}),
        reference_cases=((60.0, "rpm", "Hz", 1.0), (360.0, "deg_s", "Hz", 1.0), (1.0, "Hz", "rps", 1.0)),
    ),
    UnitConversionSpec(
        component_id="frequency-acoustics-tempo",
        dimension="frequency",
        title="Acoustic and musical tempo frequency converter (Hz, bpm, kHz)",
        base_unit="Hz",
        description="Converts hertz, millihertz, kilohertz, and beats per minute (bpm).",
        units=_linear({"Hz": 1.0, "mHz": 0.001, "kHz": 1000.0, "bpm": 1.0 / 60.0}),
        reference_cases=((120.0, "bpm", "Hz", 2.0), (1.0, "kHz", "Hz", 1000.0), (1000.0, "mHz", "Hz", 1.0)),
    ),
    UnitConversionSpec(
        component_id="frequency-rf-microwave",
        dimension="frequency",
        title="RF and microwave carrier frequency converter",
        base_unit="Hz",
        description="Converts hertz, megahertz, gigahertz, and terahertz for radio and optical engineering.",
        units=_linear({"Hz": 1.0, "MHz": 1e6, "GHz": 1e9, "THz": 1e12}),
        reference_cases=((2.4, "GHz", "MHz", 2400.0), (5.0, "GHz", "Hz", 5e9), (1.0, "THz", "GHz", 1000.0)),
    ),
    UnitConversionSpec(
        component_id="frequency-spectroscopy-cycle",
        dimension="frequency",
        title="Laboratory centrifuge and oscillation cycle converter (cpm to GHz)",
        base_unit="Hz",
        description="Converts cycles per minute (cpm), hertz, kilohertz, megahertz, and gigahertz.",
        units=_linear({"Hz": 1.0, "cpm": 1.0 / 60.0, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9}),
        reference_cases=((600.0, "cpm", "Hz", 10.0), (1.0, "MHz", "kHz", 1000.0), (1.0, "GHz", "MHz", 1000.0)),
    ),
    # 12. volume_flow (5 components)
    UnitConversionSpec(
        component_id="volume-si-liter",
        dimension="volume_flow",
        title="SI cubic meter and metric liter volume converter",
        base_unit="m3",
        description="Converts cubic meters, liters, milliliters, microliters, cubic centimeters, and cubic millimeters.",
        units=_linear({"m3": 1.0, "L": 0.001, "mL": 1e-6, "uL": 1e-9, "cm3": 1e-6, "mm3": 1e-9}),
        reference_cases=((1.0, "m3", "L", 1000.0), (1.0, "L", "mL", 1000.0), (1.0, "mL", "cm3", 1.0)),
    ),
    UnitConversionSpec(
        component_id="volume-us-liquid",
        dimension="volume_flow",
        title="US customary liquid volume converter (gal, qt, pt, cup, fl oz)",
        base_unit="m3",
        description="Converts cubic meters, liters, US liquid gallons (231 in^3), quarts, pints, cups, and US fluid ounces.",
        units=_linear({
            "m3": 1.0,
            "L": 0.001,
            "gal_us": 0.003785411784,
            "qt_us": 0.000946352946,
            "pt_us": 0.000473176473,
            "cup_us": 0.0002365882365,
            "fl_oz_us": 0.0000295735295625,
        }),
        reference_cases=((1.0, "gal_us", "qt_us", 4.0), (1.0, "qt_us", "pt_us", 2.0), (1.0, "gal_us", "fl_oz_us", 128.0)),
    ),
    UnitConversionSpec(
        component_id="volume-uk-imperial",
        dimension="volume_flow",
        title="UK imperial volume converter (imperial gal, qt, pt, fl oz)",
        base_unit="m3",
        description="Converts cubic meters, liters, UK imperial gallons (4.54609 L), quarts, pints, and imperial fluid ounces.",
        units=_linear({
            "m3": 1.0,
            "L": 0.001,
            "gal_uk": 0.00454609,
            "qt_uk": 0.0011365225,
            "pt_uk": 0.00056826125,
            "fl_oz_uk": 0.0000284130625,
        }),
        reference_cases=((1.0, "gal_uk", "L", 4.54609), (1.0, "gal_uk", "pt_uk", 8.0), (1.0, "pt_uk", "fl_oz_uk", 20.0)),
    ),
    UnitConversionSpec(
        component_id="volume-industrial-petroleum",
        dimension="volume_flow",
        title="Petroleum barrel and cubic foot industrial volume converter",
        base_unit="m3",
        description="Converts cubic meters, liters, petroleum barrels (42 US gallons), cubic feet, and cubic inches.",
        units=_linear({
            "m3": 1.0,
            "L": 0.001,
            "bbl_oil": 0.158987294928,
            "ft3": 0.028316846592,
            "in3": 0.000016387064,
        }),
        reference_cases=((1.0, "ft3", "in3", 1728.0), (1.0, "bbl_oil", "L", 158.987294928), (1.0, "m3", "L", 1000.0)),
    ),
    UnitConversionSpec(
        component_id="volume-flow-rate-hydraulic",
        dimension="volume_flow",
        title="Hydraulic and pneumatic volumetric flow-rate converter",
        base_unit="m3_s",
        description="Converts cubic meters per second, liters per second, liters per minute, cubic meters per hour, US gallons per minute (gpm), and cubic feet per minute (cfm).",
        units=_linear({
            "m3_s": 1.0,
            "L_s": 0.001,
            "L_min": 0.001 / 60.0,
            "m3_h": 1.0 / 3600.0,
            "gpm_us": 0.003785411784 / 60.0,
            "cfm": 0.028316846592 / 60.0,
        }),
        reference_cases=((1.0, "m3_s", "L_s", 1000.0), (60.0, "L_min", "L_s", 1.0), (3.6, "m3_h", "L_s", 1.0)),
    ),
)


def convert_units(component_id: str, value: float, from_unit: str, to_unit: str) -> float:
    """Convert value from from_unit to to_unit using the specified unit conversion component."""
    spec_map = {item.component_id: item for item in UNIT_CONVERSION_SPECS}
    if component_id not in spec_map:
        raise KeyError(f"unknown_unit_conversion_component: {component_id!r}")
    spec = spec_map[component_id]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError("invalid_numeric_value")
    if from_unit not in spec.units:
        raise ValueError(f"unknown_from_unit: {from_unit!r}")
    if to_unit not in spec.units:
        raise ValueError(f"unknown_to_unit: {to_unit!r}")
    from_scale, from_offset = spec.units[from_unit]
    to_scale, to_offset = spec.units[to_unit]
    base_val = float(value) * from_scale + from_offset
    result = (base_val - to_offset) / to_scale
    if not math.isfinite(result):
        raise ValueError("conversion_result_not_finite")
    return result


def _render_implement_py(spec: UnitConversionSpec) -> bytes:
    code = f'''"""{spec.title} (dimension: {spec.dimension}).

{spec.description}
Deterministic unit conversion using NIST SP 811 / CODATA constants.
"""
from __future__ import annotations

import math

COMPONENT_ID = {spec.component_id!r}
DIMENSION = {spec.dimension!r}
BASE_UNIT = {spec.base_unit!r}
UNITS = {spec.units!r}


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert value between units in {spec.component_id}."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError("invalid_numeric_value")
    if from_unit not in UNITS:
        raise ValueError(f"unknown_unit: {{from_unit!r}}")
    if to_unit not in UNITS:
        raise ValueError(f"unknown_unit: {{to_unit!r}}")
    from_scale, from_offset = UNITS[from_unit]
    to_scale, to_offset = UNITS[to_unit]
    base_val = float(value) * from_scale + from_offset
    result = (base_val - to_offset) / to_scale
    if not math.isfinite(result):
        raise ValueError("conversion_result_not_finite")
    return result
'''
    return code.encode("utf-8")


def _render_test_implement_py(spec: UnitConversionSpec) -> bytes:
    code = f'''"""Deterministic conformance and 1e-9 round-trip tests for {spec.component_id}."""
from __future__ import annotations

import math
import unittest
from implement import UNITS, convert

REFERENCE_CASES = {list(spec.reference_cases)!r}
TOLERANCE = {ROUND_TRIP_TOLERANCE!r}


class UnitConversionTests(unittest.TestCase):
    def test_reference_values(self) -> None:
        for val, u_from, u_to, expected in REFERENCE_CASES:
            actual = convert(val, u_from, u_to)
            self.assertTrue(
                math.isclose(actual, expected, rel_tol=TOLERANCE, abs_tol=TOLERANCE),
                f"{{val}} {{u_from}} -> {{u_to}}: got {{actual}}, expected {{expected}}",
            )

    def test_round_trip_precision_all_pairs(self) -> None:
        unit_names = list(UNITS.keys())
        for u1 in unit_names:
            for u2 in unit_names:
                for sample in (1.0, 42.5):
                    forward = convert(sample, u1, u2)
                    back = convert(forward, u2, u1)
                    self.assertTrue(
                        math.isclose(back, sample, rel_tol=TOLERANCE, abs_tol=TOLERANCE),
                        f"Round-trip failed for {{u1}} <-> {{u2}}: {{sample}} -> {{back}}",
                    )

    def test_unknown_unit_and_invalid_number_refused(self) -> None:
        u0 = next(iter(UNITS.keys()))
        with self.assertRaises(ValueError):
            convert(1.0, "unknown_unit_xyz", u0)
        with self.assertRaises(ValueError):
            convert(1.0, u0, "unknown_unit_xyz")
        with self.assertRaises(ValueError):
            convert(True, u0, u0)
        with self.assertRaises(ValueError):
            convert(float("nan"), u0, u0)

    def test_known_wrong_control_fails(self) -> None:
        val, u_from, u_to, expected = REFERENCE_CASES[0]
        actual = convert(val, u_from, u_to)
        with self.assertRaises(AssertionError):
            self.assertAlmostEqual(actual, expected + 100.0, delta=1e-6)


if __name__ == "__main__":
    unittest.main()
'''
    return code.encode("utf-8")


def _render_skill_md(spec: UnitConversionSpec) -> bytes:
    unit_list = ", ".join(f"`{u}`" for u in spec.units.keys())
    text = (
        f"---\n"
        f"name: {spec.component_id}\n"
        f"description: {spec.description}\n"
        f"---\n\n"
        f"# {spec.title}\n\n"
        f"Dimension: `{spec.dimension}`. Base unit: `{spec.base_unit}`.\n"
        f"Supported units: {unit_list}.\n\n"
        f"## Precision guarantee\n\n"
        f"All unit pairs satisfy round-trip conversion accuracy within `{ROUND_TRIP_TOLERANCE}`.\n"
    )
    return text.encode("utf-8")


def _render_integration_md(spec: UnitConversionSpec, harness_name: str) -> bytes:
    text = (
        f"# {spec.title} ({harness_name} integration)\n\n"
        f"Call `convert(value, from_unit, to_unit)` from `implement.py` in `{harness_name}` "
        f"for deterministic `{spec.dimension}` unit conversions.\n"
    )
    return text.encode("utf-8")


def build_unit_conversion_component(spec_or_id: UnitConversionSpec | str) -> dict[str, Any]:
    """Build a local package preview, not a library admission record for a unit conversion component."""
    if isinstance(spec_or_id, str):
        spec_map = {item.component_id: item for item in UNIT_CONVERSION_SPECS}
        if spec_or_id not in spec_map:
            raise KeyError(f"unknown_unit_conversion_component: {spec_or_id!r}")
        spec = spec_map[spec_or_id]
    else:
        spec = spec_or_id
    if not isinstance(spec, UnitConversionSpec) or spec not in UNIT_CONVERSION_SPECS:
        raise ValueError("unregistered_factory_spec")

    attribution = (
        f"# Attribution\n\n"
        f"Generated deterministically by `{FACTORY_ID}` version `{FACTORY_VERSION}` on {GENERATED_ON}.\n"
        f"Constants: NIST SP 811 and CODATA public-domain physical definitions.\n"
        f"Licence: MIT.\n"
    ).encode("utf-8")

    raw_files = [
        ("implement.py", _render_implement_py(spec), "text/x-python", "skill_script"),
        ("test_implement.py", _render_test_implement_py(spec), "text/x-python", "skill_reference"),
        ("SKILL.md", _render_skill_md(spec), "text/markdown", "skill_definition"),
        ("integrate/claude-code.md", _render_integration_md(spec, "claude_code"), "text/markdown", "skill_reference"),
        ("integrate/codex.md", _render_integration_md(spec, "codex"), "text/markdown", "skill_reference"),
        ("integrate/cursor.md", _render_integration_md(spec, "cursor"), "text/markdown", "skill_reference"),
        ("integrate/opencode.md", _render_integration_md(spec, "opencode"), "text/markdown", "skill_reference"),
        ("LICENSE", MIT_LICENSE_TEXT.encode("utf-8"), "text/plain", "other"),
        ("ATTRIBUTION.md", attribution, "text/markdown", "other"),
    ]

    entries: list[CataloguePackageFile] = []
    file_bodies: dict[str, bytes] = {}
    for path, data, mtype, role in raw_files:
        file_bodies[path] = data
        entries.append(CataloguePackageFile(path, sha256_hex(data), len(data), mtype, role))

    package = CataloguePackage(tuple(entries), PACKAGE_BODY)
    return {
        "build_state": "local_package_preview",
        "admission_ready": False,
        "factory_id": FACTORY_ID,
        "component_id": spec.component_id,
        "dimension": spec.dimension,
        "title": spec.title,
        "base_unit": spec.base_unit,
        "supported_units": list(spec.units.keys()),
        "description": spec.description,
        "licence": "MIT",
        "catalogue_package": package.to_dict(),
        "package_digest": package.package_digest,
        "file_bodies": file_bodies,
        "approved": False,
        "published": False,
        "effects_granted": [],
        "lifecycle": "candidate",
        "qualification": "not_independently_reviewed",
    }


def verify_unit_conversion_component(component: dict[str, Any]) -> dict[str, Any]:
    """Execute generated implement.py and verify reference values, 1e-9 round-trips, refusals, and known-wrong control."""
    comp_id = component["component_id"]
    spec = {item.component_id: item for item in UNIT_CONVERSION_SPECS}[comp_id]
    canonical = build_unit_conversion_component(comp_id)
    if component != canonical:
        raise ValueError("noncanonical_factory_package")
    namespace: dict[str, Any] = {}
    exec(compile(canonical["file_bodies"]["implement.py"].decode("utf-8"), "implement.py", "exec"), namespace)
    convert_fn = namespace["convert"]

    ref_ok = all(
        math.isclose(convert_fn(val, u_from, u_to), expected, rel_tol=ROUND_TRIP_TOLERANCE, abs_tol=ROUND_TRIP_TOLERANCE)
        for val, u_from, u_to, expected in spec.reference_cases
    )

    unit_names = list(spec.units.keys())
    round_trip_ok = True
    max_error = 0.0
    for u1 in unit_names:
        for u2 in unit_names:
            for sample in (1.0, 37.5):
                back = convert_fn(convert_fn(sample, u1, u2), u2, u1)
                err = abs(back - sample) / max(1.0, abs(sample))
                if err > max_error:
                    max_error = err
                if not math.isclose(back, sample, rel_tol=ROUND_TRIP_TOLERANCE, abs_tol=ROUND_TRIP_TOLERANCE):
                    round_trip_ok = False

    neg_ok = False
    try:
        convert_fn(1.0, "nonexistent_unit", unit_names[0])
    except ValueError:
        neg_ok = True

    val0, uf0, ut0, exp0 = spec.reference_cases[0]
    known_wrong_ok = not math.isclose(convert_fn(val0, uf0, ut0), exp0 + 999.0, rel_tol=1e-6, abs_tol=1e-6)

    passed = bool(ref_ok and round_trip_ok and neg_ok and known_wrong_ok)
    return {
        "component_id": comp_id,
        "dimension": spec.dimension,
        "passed": passed,
        "reference_cases_passed": ref_ok,
        "round_trip_within_1e9": round_trip_ok,
        "max_relative_round_trip_error": max_error,
        "negative_refusal_passed": neg_ok,
        "known_wrong_control_passed": known_wrong_ok,
    }


def build_all_unit_conversion_components() -> list[dict[str, Any]]:
    """Build all 60 deterministic unit conversion components across 12 physical dimensions."""
    return [build_unit_conversion_component(spec) for spec in UNIT_CONVERSION_SPECS]


__all__ = [
    "FACTORY_ID",
    "FACTORY_VERSION",
    "ROUND_TRIP_TOLERANCE",
    "DIMENSIONS",
    "UnitConversionSpec",
    "UNIT_CONVERSION_SPECS",
    "convert_units",
    "build_unit_conversion_component",
    "verify_unit_conversion_component",
    "build_all_unit_conversion_components",
]
