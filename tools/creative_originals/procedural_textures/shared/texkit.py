"""Tileable procedural texture toolkit: noise, cells, warping, colour, normals, occlusion and PNG maps.

Standard library only (Python 3.10 or later). A field is a flat list of floats, row-major from the top-left,
``width * height`` long. Patterns are defined in texture space, u = (x + 0.5) / width and v = (y + 0.5) / height,
so the same seed and parameters keep their layout when the output size changes. Every lattice, cell grid,
distance, blur and derivative wraps around both edges, so every field made here tiles without a seam.

Conventions of the maps (glTF metallic-roughness): albedo and emissive are sRGB; normal, roughness, metallic,
height and ambient occlusion are linear. Normal maps use the OpenGL convention (green points to +V, up in the
image) unless DirectX (-Y) output is requested.

Cost: everything runs in pure Python, so time grows with the pixel count. Each item's README and component card give
the cost measured for that item at 1024 x 1024.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from itertools import accumulate
from pathlib import Path

import pngio

MIN_SIDE = 4
MAX_SIDE = 4096
MAX_SEED = 2 ** 31 - 1
TAU = 2.0 * math.pi
_MASK = 0xFFFFFFFF
_INV_2_32 = 1.0 / 4294967296.0
#: Map names in the glTF metallic-roughness model this toolkit writes, in output order.
MAP_NAMES = (ALBEDO, NORMAL, ROUGHNESS, METALLIC, HEIGHT, AO, EMISSIVE) = (
    "albedo", "normal", "roughness", "metallic", "height", "ao", "emissive")
#: Parameter types a PARAMETERS row declares: an integer or a finite number.
PARAMETER_TYPES = (INTEGER, NUMBER) = ("int", "float")
#: The base noises fbm sums: gradient (about -1 to 1) or value (0 to 1).
NOISE_KINDS = (GRADIENT, VALUE) = ("gradient", "value")
#: How stamp, draw_segment and draw_path combine a painted value with the field.
PAINT_MODES = (MODE_MAX, MODE_MIN, MODE_ADD, MODE_SET, MODE_MULTIPLY) = ("max", "min", "add", "set", "multiply")
#: sys.platform of macOS, where getrusage reports the peak memory in bytes instead of kibibytes.
_BYTE_RUSAGE_PLATFORM = "darwin"
_BAYER4 = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


# ---------------------------------------------------------------------------------------------- hashing and random

def hash_u32(*values) -> int:
    """A well-mixed 32-bit hash of integers; the same inputs give the same value on every platform and version."""
    state = 0x9E3779B9
    for value in values:
        state = ((state ^ (int(value) & _MASK)) * 0x85EBCA6B) & _MASK
        state ^= state >> 13
        state = (state * 0xC2B2AE35) & _MASK
        state ^= state >> 16
    return state


def hash_float(*values) -> float:
    """hash_u32 scaled to [0, 1)."""
    return hash_u32(*values) * _INV_2_32


class Rng:
    """Seeded random numbers built only on random.Random.random(), whose sequence Python keeps stable."""

    def __init__(self, seed: int, *salt: int) -> None:
        self._next = random.Random(hash_u32(seed, *salt) | (hash_u32(seed, 0x51, *salt) << 32)).random

    def random(self) -> float:
        """A float in [0, 1)."""
        return self._next()

    def uniform(self, low: float, high: float) -> float:
        """A float between low and high."""
        return low + (high - low) * self._next()

    def integer(self, low: int, high: int) -> int:
        """An integer from low to high, both included."""
        span = high - low + 1
        return low + min(int(self._next() * span), span - 1)

    def choice(self, options):
        """One element of a non-empty sequence."""
        return options[self.integer(0, len(options) - 1)]

    def gauss(self, mean: float = 0.0, deviation: float = 1.0) -> float:
        """A normally distributed float (Box-Muller from two uniform draws)."""
        first = 1.0 - self._next()
        return mean + deviation * math.sqrt(-2.0 * math.log(first)) * math.cos(TAU * self._next())

    def chance(self, probability: float) -> bool:
        """True with the given probability."""
        return self._next() < probability


# ------------------------------------------------------------------------------------------------------ validation

def check_size(width, height) -> tuple:
    """(width, height) when both are integers from MIN_SIDE to MAX_SIDE; ValueError otherwise."""
    for name, value in (("width", width), ("height", height)):
        if type(value) is not int or not MIN_SIDE <= value <= MAX_SIDE:
            raise ValueError(f"{name} must be an integer from {MIN_SIDE} to {MAX_SIDE}, got {value!r}")
    return width, height


def check_seed(seed) -> int:
    """The seed when it is an integer from 0 to MAX_SEED; ValueError otherwise."""
    if type(seed) is not int or not 0 <= seed <= MAX_SEED:
        raise ValueError(f"seed must be an integer from 0 to {MAX_SEED}, got {seed!r}")
    return seed


def _checked(row: dict, value):
    name, kind = row["name"], row["type"]
    if kind == INTEGER:
        if type(value) is not int:
            raise ValueError(f"{name} must be an integer, got {value!r}")
    elif kind == NUMBER:
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number, got {value!r}")
        value = float(value)
    else:
        raise ValueError(f"{name} has an unknown type {kind!r}")
    if not row["minimum"] <= value <= row["maximum"]:
        raise ValueError(f"{name} must be from {row['minimum']} to {row['maximum']}, got {value!r}")
    return value


def resolve(parameters: list, presets: dict, preset, overrides: dict) -> dict:
    """Parameter values for a preset plus overrides; refuses unknown presets, unknown names and out-of-range values."""
    if type(preset) is not str or preset not in presets:
        raise ValueError(f"unknown preset {preset!r}; presets are {sorted(presets)}")
    rows = {row["name"]: row for row in parameters}
    values = {name: _checked(row, row["default"]) for name, row in rows.items()}
    for source in (presets[preset].get("values", {}), overrides):
        for name, value in source.items():
            if name not in rows:
                raise ValueError(f"unknown parameter {name!r}; parameters are {sorted(rows)}")
            values[name] = _checked(rows[name], value)
    return values


# --------------------------------------------------------------------------------------------- scalar helpers

def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """value limited to [low, high]."""
    return low if value < low else high if value > high else value


def lerp(first: float, second: float, amount: float) -> float:
    """Linear interpolation from first (amount 0) to second (amount 1)."""
    return first + (second - first) * amount


def smoothstep(edge0: float, edge1: float, value: float) -> float:
    """Hermite step from 0 at edge0 to 1 at edge1 (a hard step when the edges are equal)."""
    if edge0 == edge1:
        return 0.0 if value < edge0 else 1.0
    t = (value - edge0) / (edge1 - edge0)
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    return t * t * (3.0 - 2.0 * t)


def fade(t: float) -> float:
    """Quintic fade 6t^5 - 15t^4 + 10t^3: zero first and second derivatives at 0 and 1."""
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def wrap_delta(delta: float) -> float:
    """A texture-space difference wrapped into [-0.5, 0.5): the shortest way around the torus."""
    return delta - math.floor(delta + 0.5)


def torus_distance(u0: float, v0: float, u1: float, v1: float) -> float:
    """Euclidean distance between two texture-space points on the torus (both axes wrap at 1)."""
    return math.hypot(wrap_delta(u1 - u0), wrap_delta(v1 - v0))


def segment_distance(pu: float, pv: float, au: float, av: float, bu: float, bv: float) -> float:
    """Distance from p to the segment a-b on the torus; p is wrapped to the copy nearest a (segments under 0.5)."""
    pu = au + wrap_delta(pu - au)
    pv = av + wrap_delta(pv - av)
    du, dv = bu - au, bv - av
    length2 = du * du + dv * dv
    t = 0.0 if length2 <= 0.0 else clamp(((pu - au) * du + (pv - av) * dv) / length2)
    return math.hypot(pu - (au + t * du), pv - (av + t * dv))


def box_distance(x: float, y: float, half_width: float, half_height: float, radius: float = 0.0) -> float:
    """Signed distance from (x, y) to a rectangle centred on the origin whose corners are rounded by ``radius``:
    negative inside, 0 on the outline. The half sizes include the rounding; radius is at most the smaller half."""
    qx = abs(x) - half_width + radius
    qy = abs(y) - half_height + radius
    return math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - radius


def polygon_distance(x: float, y: float, vertices) -> float:
    """Signed distance from (x, y) to a simple polygon [(x, y), ...] (either winding): negative inside, 0 on an edge.

    Inside or outside comes from the even-odd crossing rule, the magnitude from the nearest edge."""
    best = math.inf
    inside = False
    ax, ay = vertices[-1]
    for bx, by in vertices:
        ex, ey = bx - ax, by - ay
        wx, wy = x - ax, y - ay
        length2 = ex * ex + ey * ey
        t = 0.0 if length2 <= 0.0 else clamp((wx * ex + wy * ey) / length2)
        dx, dy = wx - ex * t, wy - ey * t
        best = min(best, dx * dx + dy * dy)
        if (ay > y) != (by > y) and x < ax + (y - ay) * ex / ey:
            inside = not inside
        ax, ay = bx, by
    distance = math.sqrt(best)
    return -distance if inside else distance


def smooth_min(first: float, second: float, softness: float) -> float:
    """Polynomial smooth minimum: min(first, second) rounded over a band of width ``softness`` (0 is the plain min)."""
    if softness <= 0.0:
        return min(first, second)
    h = clamp(0.5 + 0.5 * (second - first) / softness)
    return second + (first - second) * h - softness * h * (1.0 - h)


def poisson_points(radius: float, seed: int = 0, attempts: int = 24) -> list:
    """Well-spaced random points [(u, v), ...] on the unit torus, no two closer than ``radius`` texture units.

    Bridson's dart throwing on a background grid: new points are tried in the ring between radius and twice the
    radius around active points until ``attempts`` tries fail, so the tile fills up to the spacing. Distances wrap
    around both edges, so the points tile. Deterministic for a seed; radius from 0.004 to 0.5."""
    if not 0.004 <= radius <= 0.5:
        raise ValueError("radius is in texture units, from 0.004 to 0.5")
    cells = math.ceil(math.sqrt(2.0) / radius)
    reach = math.ceil(radius * cells)
    grid = {}
    rng = Rng(seed, 0x9D)
    points = [(rng.random(), rng.random())]
    grid[(int(points[0][0] * cells) % cells, int(points[0][1] * cells) % cells)] = 0
    active = [0]
    limit2 = radius * radius
    while active:
        slot = rng.integer(0, len(active) - 1)
        cu, cv = points[active[slot]]
        for _ in range(attempts):
            angle = TAU * rng.random()
            distance = radius * math.sqrt(1.0 + 3.0 * rng.random())
            u = (cu + distance * math.cos(angle)) % 1.0
            v = (cv + distance * math.sin(angle)) % 1.0
            gi, gj = int(u * cells) % cells, int(v * cells) % cells
            crowded = False
            for dj in range(-reach, reach + 1):
                for di in range(-reach, reach + 1):
                    other = grid.get(((gi + di) % cells, (gj + dj) % cells))
                    if other is not None:
                        ou, ov = points[other]
                        du, dv = wrap_delta(u - ou), wrap_delta(v - ov)
                        if du * du + dv * dv < limit2:
                            crowded = True
                            break
                if crowded:
                    break
            if not crowded:
                grid[(gi, gj)] = len(points)
                active.append(len(points))
                points.append((u, v))
                break
        else:
            active[slot] = active[-1]
            active.pop()
    return points


# ------------------------------------------------------------------------------------------------------- noise

def _check_cells(*cells) -> None:
    for value in cells:
        if type(value) is not int or value < 1:
            raise ValueError(f"cell counts are positive integers, got {value!r}")


def _column_runs(width: int, cells: int, offset: float = 0.0) -> list:
    """Runs of neighbouring pixel columns in the same lattice cell, in column order: (cell, [(local, fade)])."""
    runs = []
    scale = cells / width
    for x in range(width):
        u = (x + 0.5) * scale + offset
        whole = math.floor(u)
        local = u - whole
        cell = int(whole) % cells
        if not runs or runs[-1][0] != cell:
            runs.append((cell, []))
        runs[-1][1].append((local, fade(local)))
    return runs


def _row_cells(height: int, cells: int, offset: float = 0.0) -> list:
    scale = cells / height
    rows = []
    for y in range(height):
        v = (y + 0.5) * scale + offset
        whole = math.floor(v)
        local = v - whole
        rows.append((int(whole) % cells, local, fade(local)))
    return rows


def value_noise(width: int, height: int, cells_x: int, cells_y: "int | None" = None, seed: int = 0,
                offset: tuple = (0.0, 0.0)) -> list:
    """Tileable value noise in [0, 1]: random lattice values with quintic interpolation, cells_x by cells_y cells.

    ``offset`` shifts the lattice by (x, y) cells; any shift keeps the noise periodic."""
    cells_y = cells_y or cells_x
    _check_cells(cells_x, cells_y)
    lattice = [[hash_u32(i, j, seed, 0x5A) * _INV_2_32 for i in range(cells_x)] for j in range(cells_y)]
    runs = _column_runs(width, cells_x, offset[0])
    out = []
    extend = out.extend
    for j, _local, sy in _row_cells(height, cells_y, offset[1]):
        top, bottom = lattice[j], lattice[(j + 1) % cells_y]
        row = [a + (b - a) * sy for a, b in zip(top, bottom)]
        row.append(row[0])
        for i, run in runs:
            a = row[i]
            d = row[i + 1] - a
            extend([a + d * s for _local, s in run])
    return out


def gradient_noise(width: int, height: int, cells_x: int, cells_y: "int | None" = None, seed: int = 0,
                   offset: tuple = (0.0, 0.0)) -> list:
    """Tileable gradient (Perlin-style) noise, about -1 to 1: unit gradients on a periodic lattice.

    It is zero on its lattice points; ``offset`` shifts the lattice by (x, y) cells and keeps the noise periodic."""
    cells_y = cells_y or cells_x
    _check_cells(cells_x, cells_y)
    gxs, gys = [], []
    for j in range(cells_y):
        row_x, row_y = [], []
        for i in range(cells_x):
            angle = TAU * hash_u32(i, j, seed, 0x6B) * _INV_2_32
            row_x.append(math.cos(angle))
            row_y.append(math.sin(angle))
        row_x.append(row_x[0])
        row_y.append(row_y[0])
        gxs.append(row_x)
        gys.append(row_y)
    runs = _column_runs(width, cells_x, offset[0])
    scale = math.sqrt(2.0)
    out = []
    extend = out.extend
    for j, fy, sy in _row_cells(height, cells_y, offset[1]):
        j1 = (j + 1) % cells_y
        ax, ay, bx, by = gxs[j], gys[j], gxs[j1], gys[j1]
        fy1 = fy - 1.0
        for i, run in runs:
            i1 = i + 1
            bl = (ax[i] + sy * (bx[i] - ax[i])) * scale
            al = (ay[i] * fy + sy * (by[i] * fy1 - ay[i] * fy)) * scale
            br = (ax[i1] + sy * (bx[i1] - ax[i1])) * scale
            ar = (ay[i1] * fy + sy * (by[i1] * fy1 - ay[i1] * fy)) * scale
            c = ar - br - al
            d = br - bl
            extend([al + bl * dx + s * (c + d * dx) for dx, s in run])
    return out


def _octave_offset(seed: int, octave: int) -> tuple:
    """A lattice shift per octave, so octaves do not share zeros (gradient noise vanishes on its lattice)."""
    return (hash_u32(seed, octave, 0x0F1) * _INV_2_32 * 7.0, hash_u32(seed, octave, 0x0F2) * _INV_2_32 * 7.0)


def fbm(width: int, height: int, cells: int, octaves: int, seed: int = 0, gain: float = 0.5, lacunarity: int = 2,
        cells_y: "int | None" = None, kind: str = GRADIENT) -> list:
    """Fractal sum of tileable noise divided by the total amplitude: about -1..1 (gradient) or 0..1 (value).

    Octaves finer than one cell per pixel are skipped (their zero-mean detail is below the pixel size)."""
    if kind not in NOISE_KINDS:
        raise ValueError(f"kind is one of {NOISE_KINDS}")
    if type(lacunarity) is not int or lacunarity < 2 or type(octaves) is not int or octaves < 1:
        raise ValueError("lacunarity is an integer of at least 2 and octaves a positive integer")
    base = gradient_noise if kind == GRADIENT else value_noise
    rows = cells_y or cells
    middle = 0.0 if kind == GRADIENT else 0.5
    total = None
    amplitude, weight = 1.0, 0.0
    for octave in range(octaves):
        cx, cy = cells * lacunarity ** octave, rows * lacunarity ** octave
        if octave == 0 or (cx <= width and cy <= height):
            layer = base(width, height, cx, cy, hash_u32(seed, octave, 0xF1), _octave_offset(seed, octave))
            total = layer if total is None else [t + amplitude * v for t, v in zip(total, layer)]
        elif middle:
            total = [t + amplitude * middle for t in total]
        weight += amplitude
        amplitude *= gain
    inverse = 1.0 / weight
    return [t * inverse for t in total]


def ridged(width: int, height: int, cells: int, octaves: int, seed: int = 0, gain: float = 0.5, lacunarity: int = 2,
           cells_y: "int | None" = None) -> list:
    """Ridged fractal in [0, 1]: each octave adds (1 - |n|)^2, sharp crests where gradient noise crosses zero."""
    rows = cells_y or cells
    total = [0.0] * (width * height)
    amplitude, weight = 1.0, 0.0
    for octave in range(octaves):
        cx, cy = cells * lacunarity ** octave, rows * lacunarity ** octave
        if octave == 0 or (cx <= width and cy <= height):
            layer = gradient_noise(width, height, cx, cy, hash_u32(seed, octave, 0xF2), _octave_offset(seed, octave))
            total = [t + amplitude * (1.0 - abs(v)) * (1.0 - abs(v)) for t, v in zip(total, layer)]
        else:
            total = [t + amplitude * 0.5 for t in total]
        weight += amplitude
        amplitude *= gain
    inverse = 1.0 / weight
    return [min(1.0, t * inverse) for t in total]


def turbulence(width: int, height: int, cells: int, octaves: int, seed: int = 0, gain: float = 0.5,
               lacunarity: int = 2, cells_y: "int | None" = None) -> list:
    """Turbulence in [0, 1]: the fractal sum of |gradient noise|, creased where each octave crosses zero."""
    rows = cells_y or cells
    total = [0.0] * (width * height)
    amplitude, weight = 1.0, 0.0
    for octave in range(octaves):
        cx, cy = cells * lacunarity ** octave, rows * lacunarity ** octave
        if octave == 0 or (cx <= width and cy <= height):
            layer = gradient_noise(width, height, cx, cy, hash_u32(seed, octave, 0xF3), _octave_offset(seed, octave))
            total = [t + amplitude * abs(v) for t, v in zip(total, layer)]
        else:
            total = [t + amplitude * 0.3 for t in total]
        weight += amplitude
        amplitude *= gain
    inverse = 1.0 / weight
    return [min(1.0, t * inverse) for t in total]


def white_noise(width: int, height: int, seed: int = 0) -> list:
    """Independent uniform values in [0, 1) per pixel (grain; not resolution independent by nature)."""
    draw = random.Random(hash_u32(seed, 0x77)).random
    return [draw() for _ in range(width * height)]


# ------------------------------------------------------------------------------------------------------ cells

def cell_points(cells_x: int, cells_y: int, seed: int = 0, jitter: float = 1.0) -> tuple:
    """The feature point of every cell in cell units, as (xs, ys) lists indexed by j * cells_x + i."""
    _check_cells(cells_x, cells_y)
    xs, ys = [], []
    for j in range(cells_y):
        for i in range(cells_x):
            xs.append(i + 0.5 + jitter * (hash_u32(i, j, seed, 0xC1) * _INV_2_32 - 0.5))
            ys.append(j + 0.5 + jitter * (hash_u32(i, j, seed, 0xC2) * _INV_2_32 - 0.5))
    return xs, ys


def hex_rows(columns: int) -> int:
    """The even row count that makes a hexagonal lattice of ``columns`` columns closest to regular on a square tile.

    Pointy-top hexagons need rows / columns = 2 / sqrt(3) and an even row count to repeat, so the hexagons are
    squashed or stretched a little: about 1 % for 7, 12, 14, 19 or 26 columns, up to 15 % for 3, 4 or 6 columns."""
    _check_cells(columns)
    return max(2, 2 * round(columns / math.sqrt(3.0)))


def hex_points(columns: int, rows: int, seed: int = 0, jitter: float = 0.0) -> tuple:
    """Feature points of a pointy-top hexagonal lattice for voronoi(points=...): one centre per grid cell, odd rows
    shifted half a column, optionally jittered by ``jitter`` of a cell. ``rows`` must be even to repeat."""
    _check_cells(columns, rows)
    if rows % 2:
        raise ValueError("a hexagonal lattice repeats only with an even row count")
    xs, ys = [], []
    for j in range(rows):
        for i in range(columns):
            xs.append(i + 0.25 + 0.5 * (j % 2) + jitter * 0.25 * (hash_u32(i, j, seed, 0xE1) * _INV_2_32 - 0.5))
            ys.append(j + 0.5 + jitter * 0.25 * (hash_u32(i, j, seed, 0xE2) * _INV_2_32 - 0.5))
    return xs, ys


def voronoi(width: int, height: int, cells_x: int, cells_y: "int | None" = None, seed: int = 0, jitter: float = 1.0,
            edges: bool = True, points: "tuple | None" = None) -> dict:
    """Cellular (Worley) noise on a torus with one feature point per cell.

    Returns lists "f1" and "f2" (distance to the nearest and second-nearest point), "edge" (distance to the nearest
    cell border: the bisector between the nearest point and each neighbour, or None when edges is False) and "cell"
    (the index j * cells_x + i of the nearest point's cell). Distances are in units of one cell width. ``points``
    replaces the jittered points with (xs, ys) in cell units, one per cell, for example a hexagonal arrangement."""
    cells_y = cells_y or cells_x
    _check_cells(cells_x, cells_y)
    cx, cy = cells_x, cells_y
    xs, ys = points if points is not None else cell_points(cx, cy, seed, jitter)
    aspect = cx / cy
    count = width * height
    f1, f2, ids = [0.0] * count, [0.0] * count, [0] * count
    edge = [0.0] * count if edges else None
    col_u = [(x + 0.5) * cx / width for x in range(width)]
    groups = [[] for _ in range(cx)]
    for x, u in enumerate(col_u):
        groups[min(int(u), cx - 1)].append((x, u))
    sqrt = math.sqrt
    cached, blocks = -1, None
    for y in range(height):
        v = (y + 0.5) * cy / height
        j = min(int(v), cy - 1)
        if j != cached:
            blocks = []
            for i in range(cx):
                points9 = []
                for dj in (-1, 0, 1):
                    jj = j + dj
                    wj = jj % cy
                    for di in (-1, 0, 1):
                        ii = i + di
                        wi = ii % cx
                        k = wj * cx + wi
                        points9.append((k, xs[k] + (ii - wi), (ys[k] + (jj - wj)) * aspect))
                inverse = []
                for a in points9:
                    line = []
                    for b in points9:
                        distance = sqrt((a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)
                        line.append(0.5 / distance if distance > 1e-9 else 1e9)
                    inverse.append(line)
                blocks.append(([p[0] for p in points9], [p[1] for p in points9], [p[2] for p in points9], inverse))
            cached = j
        vs = v * aspect
        base = y * width
        for i, columns in enumerate(groups):
            if not columns:
                continue
            kid, pxs, pys, inverse = blocks[i]
            dy2 = [(vs - py) * (vs - py) for py in pys]
            for x, u in columns:
                ds = [(u - px) * (u - px) + d2 for px, d2 in zip(pxs, dy2)]
                best = min(ds)
                a = ds.index(best)
                ds[a] = 1e30
                second = min(ds)
                index = base + x
                f1[index] = sqrt(best)
                f2[index] = sqrt(second)
                ids[index] = kid[a]
                if edge is not None:
                    edge[index] = min([(d - best) * w for d, w in zip(ds, inverse[a])])
    return {"f1": f1, "f2": f2, "edge": edge, "cell": ids}


# ------------------------------------------------------------------------------------------------ painting

_MODES = {mode: code for code, mode in enumerate(PAINT_MODES)}


def _combine(field: list, index: int, value: float, mode: int) -> None:
    if mode == 0:
        if value > field[index]:
            field[index] = value
    elif mode == 1:
        if value < field[index]:
            field[index] = value
    elif mode == 2:
        field[index] += value
    elif mode == 3:
        field[index] = value
    else:
        field[index] *= value


def ellipse_pixels(width: int, height: int, center_u: float, center_v: float, radius_u: float, radius_v: float,
                   angle: float = 0.0) -> list:
    """(index, s, t) for every pixel of a rotated ellipse's bounding box, wrapping around both edges.

    s and t are local coordinates rotated by ``angle`` radians and scaled so the ellipse edge is s*s + t*t == 1;
    callers decide what to paint (several fields at once, z-buffered). Radii are in texture units under 0.5."""
    if not (0.0 < radius_u < 0.5 and 0.0 < radius_v < 0.5):
        raise ValueError("radii are in texture units, between 0 and 0.5")
    ca, sa = math.cos(angle), math.sin(angle)
    extent_u = math.sqrt((radius_u * ca) ** 2 + (radius_v * sa) ** 2)
    extent_v = math.sqrt((radius_u * sa) ** 2 + (radius_v * ca) ** 2)
    x0 = math.floor((center_u - extent_u) * width - 0.5)
    x1 = min(math.ceil((center_u + extent_u) * width - 0.5), x0 + width - 1)
    y0 = math.floor((center_v - extent_v) * height - 0.5)
    y1 = min(math.ceil((center_v + extent_v) * height - 0.5), y0 + height - 1)
    inverse_u, inverse_v = 1.0 / radius_u, 1.0 / radius_v
    out = []
    for y in range(y0, y1 + 1):
        dv = (y + 0.5) / height - center_v
        row = (y % height) * width
        for x in range(x0, x1 + 1):
            du = (x + 0.5) / width - center_u
            out.append((row + x % width, (du * ca + dv * sa) * inverse_u, (dv * ca - du * sa) * inverse_v))
    return out


def segment_pixels(width: int, height: int, u0: float, v0: float, u1: float, v1: float, radius: float) -> list:
    """(index, d, t) for every pixel within ``radius`` of the segment, wrapping around both edges.

    d is the distance to the segment divided by the radius (0 on the axis, 1 at the edge) and t the position along
    the segment (0 at the start, 1 at the end). Coordinates may run past 0 or 1; a footprint wider or taller than
    the tile measures each pixel against its nearest wrapped copy."""
    if radius <= 0.0:
        raise ValueError("radius is positive")
    du, dv = u1 - u0, v1 - v0
    length2 = du * du + dv * dv
    x0 = math.floor((min(u0, u1) - radius) * width - 0.5)
    x1 = math.ceil((max(u0, u1) + radius) * width - 0.5)
    y0 = math.floor((min(v0, v1) - radius) * height - 0.5)
    y1 = math.ceil((max(v0, v1) + radius) * height - 0.5)
    wide, tall = x1 - x0 >= width, y1 - y0 >= height
    if wide:
        x0, x1 = 0, width - 1
    if tall:
        y0, y1 = 0, height - 1
    shifts_u = (-1.0, 0.0, 1.0) if wide else (0.0,)
    shifts_v = (-1.0, 0.0, 1.0) if tall else (0.0,)
    radius2 = radius * radius
    inverse = 1.0 / radius
    out = []
    for y in range(y0, y1 + 1):
        row = (y % height) * width
        for x in range(x0, x1 + 1):
            best, along = radius2, 0.0
            for su in shifts_u:
                pu = (x + 0.5) / width + su
                for sv in shifts_v:
                    pv = (y + 0.5) / height + sv
                    t = 0.0 if length2 <= 0.0 else ((pu - u0) * du + (pv - v0) * dv) / length2
                    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
                    eu, ev = pu - u0 - t * du, pv - v0 - t * dv
                    d2 = eu * eu + ev * ev
                    if d2 < best:
                        best, along = d2, t
            if best < radius2:
                out.append((row + x % width, math.sqrt(best) * inverse, along))
    return out


def stamp(field: list, width: int, height: int, center_u: float, center_v: float, radius_u: float, radius_v: float,
          shape, mode: str = MODE_MAX, angle: float = 0.0) -> None:
    """Paint shape(s, t) into field around (center_u, center_v), wrapping around both edges.

    s and t are as in ellipse_pixels; shape returns a float, or None to leave the pixel unchanged. mode is "max",
    "min", "add", "set" or "multiply"."""
    if mode not in _MODES:
        raise ValueError(f"mode is one of {PAINT_MODES}")
    code = _MODES[mode]
    for index, s, t in ellipse_pixels(width, height, center_u, center_v, radius_u, radius_v, angle):
        value = shape(s, t)
        if value is not None:
            _combine(field, index, value, code)


def draw_segment(field: list, width: int, height: int, u0: float, v0: float, u1: float, v1: float, radius: float,
                 value: float = 1.0, mode: str = MODE_MAX, profile=None) -> None:
    """Paint a capsule from (u0, v0) to (u1, v1) with wrap-around: value * profile(d) inside the radius.

    d runs from 0 on the axis to 1 at the edge; the default profile is a cosine bump, 1 on the axis, 0 at the edge."""
    if mode not in _MODES:
        raise ValueError(f"mode is one of {PAINT_MODES}")
    code = _MODES[mode]
    for index, d, _t in segment_pixels(width, height, u0, v0, u1, v1, radius):
        weight = profile(d) if profile is not None else 0.5 + 0.5 * math.cos(math.pi * d)
        _combine(field, index, value * weight, code)


def draw_path(field: list, width: int, height: int, points: list, radius: float, value: float = 1.0,
              mode: str = MODE_MAX, profile=None) -> None:
    """draw_segment along consecutive (u, v) points; widths may vary per point as (u, v, radius) triples."""
    for first, second in zip(points, points[1:]):
        r = first[2] if len(first) > 2 else radius
        draw_segment(field, width, height, first[0], first[1], second[0], second[1], r, value, mode, profile)


# --------------------------------------------------------------------------------------------- field operations

def _blur_line(line: list, radius: int) -> list:
    size = len(line)
    radius = min(radius, (size - 1) // 2)
    if radius < 1:
        return list(line)
    extended = line[-radius:] + line + line[:radius]
    sums = list(accumulate(extended, initial=0.0))
    span = 2 * radius + 1
    inverse = 1.0 / span
    return [(sums[x + span] - sums[x]) * inverse for x in range(size)]


def blur(field: list, width: int, height: int, radius: float, passes: int = 2) -> list:
    """Wrap-around box blur repeated ``passes`` times (passes >= 2 approach a Gaussian).

    radius is in texture units (a fraction of the width and of the height), at least one pixel."""
    rx = max(1, int(round(radius * width)))
    ry = max(1, int(round(radius * height)))
    out = list(field)
    for _ in range(passes):
        rows = []
        for y in range(height):
            rows.extend(_blur_line(out[y * width:(y + 1) * width], rx))
        out = rows
        for x in range(width):
            out[x::width] = _blur_line(out[x::width], ry)
    return out


def normalize(field: list) -> list:
    """field stretched to [0, 1] by its minimum and maximum (0.5 everywhere when flat)."""
    low, high = min(field), max(field)
    if high - low < 1e-12:
        return [0.5] * len(field)
    scale = 1.0 / (high - low)
    return [(v - low) * scale for v in field]


def sample(field: list, width: int, height: int, u: float, v: float) -> float:
    """Bilinear wrap-around sample of field at texture coordinate (u, v)."""
    sx, sy = u * width - 0.5, v * height - 0.5
    x0, y0 = math.floor(sx), math.floor(sy)
    fx, fy = sx - x0, sy - y0
    x0 %= width
    y0 %= height
    x1, y1 = (x0 + 1) % width, (y0 + 1) % height
    top = field[y0 * width + x0] + (field[y0 * width + x1] - field[y0 * width + x0]) * fx
    bottom = field[y1 * width + x0] + (field[y1 * width + x1] - field[y1 * width + x0]) * fx
    return top + (bottom - top) * fy


def warp(field: list, width: int, height: int, offset_u: list, offset_v: list, amount: float) -> list:
    """field resampled at (u + amount * offset_u, v + amount * offset_v): domain warping with wrap-around.

    The offsets are fields (usually -1..1); amount is in texture units."""
    out = []
    append = out.append
    floor = math.floor
    au, av = amount * width, amount * height
    for y in range(height):
        base = y * width
        for x in range(width):
            sx = x + au * offset_u[base + x]
            sy = y + av * offset_v[base + x]
            x0, y0 = floor(sx), floor(sy)
            fx, fy = sx - x0, sy - y0
            x0 %= width
            y0 %= height
            x1 = x0 + 1 if x0 + 1 < width else 0
            r0 = y0 * width
            r1 = (y0 + 1) * width if y0 + 1 < height else 0
            top = field[r0 + x0] + (field[r0 + x1] - field[r0 + x0]) * fx
            bottom = field[r1 + x0] + (field[r1 + x1] - field[r1 + x0]) * fx
            append(top + (bottom - top) * fy)
    return out


def resample(field: list, source_width: int, source_height: int, width: int, height: int) -> list:
    """Bilinear wrap-around resize of a tileable field (for detail computed at a lower resolution)."""
    columns = []
    for x in range(width):
        sx = (x + 0.5) * source_width / width - 0.5
        x0 = math.floor(sx)
        columns.append((x0 % source_width, (x0 + 1) % source_width, sx - x0))
    out = []
    for y in range(height):
        sy = (y + 0.5) * source_height / height - 0.5
        y0 = math.floor(sy)
        fy = sy - y0
        top = field[(y0 % source_height) * source_width:(y0 % source_height + 1) * source_width]
        bottom = field[((y0 + 1) % source_height) * source_width:((y0 + 1) % source_height + 1) * source_width]
        line = [a + (b - a) * fy for a, b in zip(top, bottom)]
        out.extend([line[a] + (line[b] - line[a]) * f for a, b, f in columns])
    return out


def upscale_nearest(values: list, source_width: int, source_height: int, width: int, height: int) -> list:
    """Nearest-neighbour resize (pixel art): output pixel (x, y) takes source (x * sw // w, y * sh // h)."""
    columns = [x * source_width // width for x in range(width)]
    out = []
    for y in range(height):
        start = (y * source_height // height) * source_width
        row = values[start:start + source_width]
        out.extend([row[c] for c in columns])
    return out


def upscale_nearest_bytes(data: bytes, channels: int, source_width: int, source_height: int, width: int,
                          height: int) -> bytes:
    """Nearest-neighbour resize of interleaved 8-bit pixels, as upscale_nearest does for a field: for pixel-art maps
    and for normals computed once per art pixel."""
    if len(data) != source_width * source_height * channels:
        raise ValueError("data holds source_width * source_height * channels bytes")
    columns = [x * source_width // width for x in range(width)]
    out = bytearray()
    for y in range(height):
        start = (y * source_height // height) * source_width * channels
        row = data[start:start + source_width * channels]
        for column in columns:
            out += row[column * channels:(column + 1) * channels]
    return bytes(out)


def isoline_distance(field: list, width: int, height: int, level: float = 0.0) -> list:
    """Approximate texture-space distance from each pixel to the curve where field == level: |f - level| / |grad f|.

    The gradient uses wrap-around central differences in texture units, so thin lines drawn from this distance keep
    one width everywhere (a vein, a ring, a contour) instead of thickening where the field is flat."""
    out = []
    sx, sy = width * 0.5, height * 0.5
    for y in range(height):
        row = field[y * width:(y + 1) * width]
        above = field[((y - 1) % height) * width:((y - 1) % height + 1) * width]
        below = field[((y + 1) % height) * width:((y + 1) % height + 1) * width]
        right = row[1:] + row[:1]
        left = row[-1:] + row[:-1]
        out.extend([abs(f - level) / max(math.sqrt(((r - l) * sx) ** 2 + ((b - a) * sy) ** 2), 1e-9)
                    for f, l, r, a, b in zip(row, left, right, above, below)])
    return out


# ------------------------------------------------------------------------------------------- normals and occlusion

def normal_map(heights: list, width: int, height: int, depth: float, directx: bool = False) -> bytes:
    """Tangent-space normal map bytes (RGB) from a 0..1 height field, by wrap-around central differences.

    depth is the relief of a height step of 1.0 in texture units (0.02 rises one fiftieth of the tile width).
    Green points to +V (up in the image, OpenGL, glTF, Blender and Godot) unless directx is True (-Y)."""
    sx = depth * width * 0.5
    sy = depth * height * 0.5 * (-1.0 if directx else 1.0)
    red, green, blue = bytearray(), bytearray(), bytearray()
    for y in range(height):
        row = heights[y * width:(y + 1) * width]
        above = heights[((y - 1) % height) * width:((y - 1) % height + 1) * width]
        below = heights[((y + 1) % height) * width:((y + 1) % height + 1) * width]
        right = row[1:] + row[:1]
        left = row[-1:] + row[:-1]
        nx = [(a - b) * sx for a, b in zip(left, right)]
        ny = [(a - b) * sy for a, b in zip(below, above)]
        scale = [1.0 / math.sqrt(1.0 + a * a + b * b) for a, b in zip(nx, ny)]
        red.extend([int((a * s * 0.5 + 0.5) * 255.0 + 0.5) for a, s in zip(nx, scale)])
        green.extend([int((b * s * 0.5 + 0.5) * 255.0 + 0.5) for b, s in zip(ny, scale)])
        blue.extend([int((s * 0.5 + 0.5) * 255.0 + 0.5) for s in scale])
    return interleave(bytes(red), bytes(green), bytes(blue))


def ambient_occlusion(heights: list, width: int, height: int, radius: float = 0.03, strength: float = 1.0) -> list:
    """Approximate cavity occlusion in [0, 1] (1 is open): how far each pixel sits below its blurred surroundings
    at three scales (radius, radius / 2, radius / 4 in texture units). Not ray traced."""
    occlusion = [0.0] * (width * height)
    for scale, weight in ((radius, 0.5), (radius * 0.5, 0.3), (radius * 0.25, 0.2)):
        around = blur(heights, width, height, scale, passes=2)
        occlusion = [o + weight * (a - h if a > h else 0.0) for o, a, h in zip(occlusion, around, heights)]
    factor = 2.5 * strength
    return [max(0.0, 1.0 - factor * o) for o in occlusion]


# ---------------------------------------------------------------------------------------------------- colour

def hex_rgb(code: str) -> tuple:
    """"#rrggbb" as an (r, g, b) tuple of sRGB floats in [0, 1]."""
    text = code[1:] if code.startswith("#") else code
    if len(text) != 6:
        raise ValueError(f"colour {code!r} is not #rrggbb")
    return tuple(int(text[k:k + 2], 16) / 255.0 for k in (0, 2, 4))


def srgb_to_linear(value: float) -> float:
    """The sRGB transfer function inverted: an encoded value in [0, 1] to linear light."""
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def linear_to_srgb(value: float) -> float:
    """Linear light in [0, 1] to an sRGB-encoded value."""
    return value * 12.92 if value <= 0.0031308 else 1.055 * value ** (1.0 / 2.4) - 0.055


def _colour(value) -> tuple:
    return hex_rgb(value) if isinstance(value, str) else tuple(float(c) for c in value)


def ramp(field: list, stops: list, size: int = 1024) -> tuple:
    """Map values through colour stops [(position, "#rrggbb" or (r, g, b)), ...], interpolated in sRGB.

    Returns (r, g, b) lists; values outside the first and last positions take the end colours."""
    points = sorted((float(position), _colour(colour)) for position, colour in stops)
    if not points:
        raise ValueError("a ramp needs at least one stop")
    tables = ([], [], [])
    top = size - 1
    for k in range(size):
        t = k / top
        if t <= points[0][0]:
            colour = points[0][1]
        elif t >= points[-1][0]:
            colour = points[-1][1]
        else:
            for (p0, c0), (p1, c1) in zip(points, points[1:]):
                if p0 <= t <= p1:
                    f = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
                    colour = tuple(a + (b - a) * f for a, b in zip(c0, c1))
                    break
        for channel in range(3):
            tables[channel].append(colour[channel])
    indices = [int((0.0 if v < 0.0 else 1.0 if v > 1.0 else v) * top + 0.5) for v in field]
    return tuple(list(map(table.__getitem__, indices)) for table in tables)


def mix_rgb(first: tuple, second: tuple, amounts: list) -> tuple:
    """Per-pixel mix of two colours by amounts (0 keeps first); each colour is (r, g, b) of lists or of floats."""
    out = []
    for a, b in zip(_colour(first) if isinstance(first, str) else first,
                    _colour(second) if isinstance(second, str) else second):
        if isinstance(a, list) and isinstance(b, list):
            out.append([x + (y - x) * t for x, y, t in zip(a, b, amounts)])
        elif isinstance(a, list):
            out.append([x + (b - x) * t for x, t in zip(a, amounts)])
        elif isinstance(b, list):
            out.append([a + (y - a) * t for y, t in zip(b, amounts)])
        else:
            out.append([a + (b - a) * t for t in amounts])
    return tuple(out)


def shade(rgb: tuple, factors: list) -> tuple:
    """Each channel multiplied by a per-pixel factor."""
    return tuple([c * f for c, f in zip(channel, factors)] for channel in rgb)


def luminance(rgb: tuple) -> list:
    """Rec. 709 luma of an (r, g, b) tuple of lists."""
    r, g, b = rgb
    return [0.2126 * x + 0.7152 * y + 0.0722 * z for x, y, z in zip(r, g, b)]


def grade(rgb: tuple, hue_shift: float = 0.0, saturation: float = 1.0, brightness: float = 1.0) -> tuple:
    """Rotate hue (turns), scale saturation and brightness in YIQ space; returns new (r, g, b) lists."""
    if hue_shift == 0.0 and saturation == 1.0 and brightness == 1.0:
        return tuple(list(channel) for channel in rgb)
    to_yiq = ((0.299, 0.587, 0.114), (0.596, -0.274, -0.322), (0.211, -0.523, 0.312))
    from_yiq = ((1.0, 0.956, 0.621), (1.0, -0.272, -0.647), (1.0, -1.106, 1.703))
    c, s = math.cos(TAU * hue_shift), math.sin(TAU * hue_shift)
    k = saturation * brightness
    adjust = ((brightness, 0.0, 0.0), (0.0, k * c, -k * s), (0.0, k * s, k * c))
    middle = [[sum(adjust[i][k] * to_yiq[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    m = [[sum(from_yiq[i][k] * middle[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    r, g, b = rgb
    return tuple([row[0] * x + row[1] * y + row[2] * z for x, y, z in zip(r, g, b)] for row in m)


def nearest_palette(rgb: tuple, palette: list) -> list:
    """For every pixel, the index of the nearest palette colour (squared sRGB distance); palette of "#rrggbb"."""
    colours = [_colour(colour) for colour in palette]
    out = []
    for r, g, b in zip(*rgb):
        best, choice = 9.0, 0
        for index, (pr, pg, pb) in enumerate(colours):
            d = (r - pr) * (r - pr) + (g - pg) * (g - pg) + (b - pb) * (b - pb)
            if d < best:
                best, choice = d, index
        out.append(choice)
    return out


def bayer4(x: int, y: int) -> float:
    """Ordered-dither threshold in (0, 1) from the 4 x 4 Bayer matrix; it repeats every 4 pixels."""
    return (_BAYER4[y % 4][x % 4] + 0.5) / 16.0


# ------------------------------------------------------------------------------------------------- encoding

def to_bytes(field: list, low: float = 0.0, high: float = 1.0) -> bytes:
    """Samples clamped to [low, high] and scaled from [0, 1] to 0..255, rounded."""
    return bytes([int((low if v < low else high if v > high else v) * 255.0 + 0.5) for v in field])


def interleave(*channels: bytes) -> bytes:
    """One interleaved byte string from equally long single-channel byte strings."""
    count = len(channels)
    out = bytearray(len(channels[0]) * count)
    for index, channel in enumerate(channels):
        if len(channel) != len(channels[0]):
            raise ValueError("channels differ in length")
        out[index::count] = channel
    return bytes(out)


def _filled(value, count: int) -> list:
    return [float(value)] * count if isinstance(value, (int, float)) else value


def finish(width: int, height: int, maps: list, *, albedo: tuple, heights: "list | None" = None,
           depth: float = 0.02, roughness=None, metallic=None, ao=None, ao_radius: float = 0.03,
           ao_strength: float = 1.0, emissive: "tuple | None" = None, alpha: "list | None" = None,
           directx: bool = False, normal: "bytes | None" = None) -> dict:
    """Encode the declared maps ({"name", "channels", "colour_space", "range"?} rows) into the result dictionary.

    Each value is clamped to its map's declared range. The normal map comes from ``heights`` and ``depth`` unless
    ``normal`` gives its RGB bytes (for example normals computed per art pixel and enlarged); the occlusion map comes
    from ``heights`` unless ``ao`` is given. Roughness and metallic may be constants."""
    count = width * height
    result = {}
    for row in maps:
        name, channels = row["name"], row["channels"]
        low, high = row.get("range", (0.0, 1.0))
        if name == ALBEDO:
            layers = [to_bytes(channel, low, high) for channel in albedo]
            if channels == 4:
                layers.append(to_bytes(alpha))
            data = interleave(*layers)
        elif name == NORMAL:
            data = normal if normal is not None else normal_map(heights, width, height, depth, directx)
        elif name == ROUGHNESS:
            data = to_bytes(_filled(roughness, count), low, high)
        elif name == METALLIC:
            data = to_bytes(_filled(metallic, count), low, high)
        elif name == HEIGHT:
            data = to_bytes(heights, low, high)
        elif name == AO:
            data = to_bytes(ao if ao is not None else ambient_occlusion(heights, width, height, ao_radius,
                                                                        ao_strength), low, high)
        elif name == EMISSIVE:
            data = interleave(*[to_bytes(channel, low, high) for channel in emissive])
        else:
            raise ValueError(f"unknown map {name!r}")
        if len(data) != count * channels:
            raise ValueError(f"map {name} has {len(data)} bytes, expected {count * channels}")
        result[name] = {"channels": channels, "colour_space": row["colour_space"], "pixels": data}
    return result


def pack_orm(maps: dict, width: int, height: int) -> bytes:
    """Occlusion (R), roughness (G) and metallic (B) in one RGB image, as glTF, three.js and Unreal read them.

    A missing occlusion map packs as 255 (open) and a missing metallic map as 0 (dielectric)."""
    count = width * height
    occlusion = maps[AO]["pixels"] if AO in maps else bytes([255]) * count
    metallic = maps[METALLIC]["pixels"] if METALLIC in maps else bytes(count)
    return interleave(occlusion, maps[ROUGHNESS]["pixels"], metallic)


def write_maps(maps: dict, width: int, height: int, directory, identity: str, orm: bool = False) -> list:
    """Write every map as <identity>_<map>.png (and <identity>_orm.png when orm is True); returns the paths."""
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for name in sorted(maps):
        entry = maps[name]
        path = folder / f"{identity}_{name}.png"
        path.write_bytes(pngio.encode(width, height, entry["pixels"], entry["channels"]))
        paths.append(path)
    if orm:
        path = folder / f"{identity}_orm.png"
        path.write_bytes(pngio.encode(width, height, pack_orm(maps, width, height), 3))
        paths.append(path)
    return paths


def _override(text: str):
    name, separator, value = text.partition("=")
    if not separator or not name:
        raise ValueError(f"--set takes NAME=VALUE, got {text!r}")
    try:
        number = int(value)
    except ValueError:
        try:
            number = float(value)
        except ValueError:
            raise ValueError(f"--set {name} needs a number, got {value!r}") from None
    return name, number


def cli(identity: str, generate, presets: dict, argv=None) -> int:
    """The command line of an item module: write its maps as PNG files and print a JSON summary line."""
    parser = argparse.ArgumentParser(prog=f"{identity}.py",
                                     description=f"Write the tileable {identity} texture maps as PNG files.")
    parser.add_argument("--size", type=int, default=256, help="square size in pixels (default 256)")
    parser.add_argument("--width", type=int, help="width in pixels (overrides --size)")
    parser.add_argument("--height", type=int, help="height in pixels (overrides --size)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--preset", default="default", choices=sorted(presets))
    parser.add_argument("--out", default=".", help="output folder (created when missing)")
    parser.add_argument("--set", action="append", default=[], metavar="NAME=VALUE",
                        help="override one parameter; repeat for more")
    parser.add_argument("--directx-normal", action="store_true", help="write the normal map with green flipped (-Y)")
    parser.add_argument("--orm", action="store_true", help="also write <identity>_orm.png (occlusion, roughness, metallic)")
    args = parser.parse_args(argv)
    width, height = args.width or args.size, args.height or args.size
    try:
        overrides = dict(_override(text) for text in args.set)
        started = time.perf_counter()
        maps = generate(width, height, args.seed, args.preset, directx_normal=args.directx_normal, **overrides)
    except ValueError as error:
        parser.error(str(error))
    generated = time.perf_counter()
    paths = write_maps(maps, width, height, args.out, identity, orm=args.orm)
    written = time.perf_counter()
    summary = {"identity": identity, "width": width, "height": height, "seed": args.seed, "preset": args.preset,
               "files": [path.name for path in paths], "generate_seconds": round(generated - started, 3),
               "write_seconds": round(written - generated, 3)}
    try:
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        summary["peak_memory_mb"] = round(peak / (1024 * 1024 if sys.platform == _BYTE_RUSAGE_PLATFORM else 1024), 1)
    except ImportError:
        pass
    print(json.dumps(summary, sort_keys=True))
    return 0


# ------------------------------------------------------------------------------------------------------ seams

def seam_report(pixels: bytes, width: int, height: int, channels: int) -> dict:
    """Compare the wrap-around seams of an 8-bit image with its interior neighbours.

    Columns: the mean absolute difference between the last and the first column (the seam) against the same
    measure for every interior pair of neighbouring columns; rows likewise. A seam passes when it is no rougher
    than max(2.5 x the interior mean, 1.5 x the roughest interior pair) + 1 level. The margin over the roughest pair
    allows for structured patterns (courses, joints), where the seam is one more boundary among a few like it."""
    if width < 3 or height < 3 or len(pixels) != width * height * channels:
        raise ValueError("seam_report needs at least 3 x 3 pixels and width * height * channels samples")
    stride = width * channels
    columns = [0] * width
    rows = [0] * height
    previous = pixels[(height - 1) * stride:]
    for y in range(height):
        line = pixels[y * stride:(y + 1) * stride]
        shifted = line[channels:] + line[:channels]
        differences = [abs(a - b) for a, b in zip(line, shifted)]
        for x in range(width):
            columns[x] += sum(differences[x * channels:(x + 1) * channels])
        rows[(y - 1) % height] += sum([abs(a - b) for a, b in zip(previous, line)])
        previous = line

    def judge(values: list, samples: int) -> dict:
        scaled = [value / samples for value in values]
        seam, interior = scaled[-1], scaled[:-1]
        mean = sum(interior) / len(interior)
        limit = max(2.5 * mean, 1.5 * max(interior)) + 1.0
        return {"seam": round(seam, 4), "interior_mean": round(mean, 4), "interior_max": round(max(interior), 4),
                "limit": round(limit, 4), "passed": seam <= limit}

    across_columns = judge(columns, height * channels)
    across_rows = judge(rows, width * channels)
    return {"columns": across_columns, "rows": across_rows,
            "passed": across_columns["passed"] and across_rows["passed"]}


__all__ = ["MIN_SIDE", "MAX_SIDE", "MAX_SEED", "MAP_NAMES", "Rng", "hash_u32", "hash_float", "check_size",
           "check_seed", "resolve", "clamp", "lerp", "smoothstep", "fade", "wrap_delta", "torus_distance",
           "segment_distance", "box_distance", "polygon_distance", "smooth_min", "poisson_points", "value_noise", "gradient_noise", "fbm", "ridged", "turbulence", "white_noise",
           "cell_points", "hex_rows", "hex_points", "voronoi", "ellipse_pixels", "segment_pixels", "stamp", "draw_segment", "draw_path", "blur", "normalize", "sample", "warp",
           "isoline_distance",
           "resample", "upscale_nearest", "upscale_nearest_bytes", "normal_map", "ambient_occlusion", "hex_rgb", "srgb_to_linear",
           "linear_to_srgb", "ramp", "mix_rgb", "shade", "luminance", "grade", "nearest_palette", "bayer4",
           "to_bytes", "interleave", "finish", "pack_orm", "write_maps", "cli", "seam_report"]
