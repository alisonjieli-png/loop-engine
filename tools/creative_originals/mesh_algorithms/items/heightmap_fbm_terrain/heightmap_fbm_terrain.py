"""Heightmap terrain: a square grid displaced by fractal gradient noise, with normals, UVs and banded colours.

Command line: python3 heightmap_fbm_terrain.py --output terrain.gltf --size 40 --resolution 40 --height 6 --seed 7
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "size", "type": "float", "default": 40.0, "unit": "m", "minimum": 0.001, "maximum": 100000.0,
     "meaning": "Side length of the square terrain, centred on the origin."},
    {"name": "resolution", "type": "int", "default": 40, "unit": "cells", "minimum": 1, "maximum": 1024,
     "meaning": "Grid cells per side; the grid has (resolution + 1)^2 vertices."},
    {"name": "height", "type": "float", "default": 6.0, "unit": "m", "minimum": 0.0, "maximum": 100000.0,
     "meaning": "Noise amplitude; heights stay within about plus or minus this value."},
    {"name": "feature_size", "type": "float", "default": 14.0, "unit": "m", "minimum": 0.001, "maximum": 100000.0,
     "meaning": "Horizontal size of the largest hills (the first noise octave's wavelength)."},
    {"name": "octaves", "type": "int", "default": 5, "unit": "count", "minimum": 1, "maximum": 12,
     "meaning": "Noise octaves; each adds detail at half the size and half the amplitude."},
    {"name": "seed", "type": "int", "default": 7, "unit": "integer", "minimum": 0, "maximum": 2147483647,
     "meaning": "Noise seed; the same seed gives the same terrain."},
]

_PALETTE = ((0.0, (0.16, 0.30, 0.48)), (0.36, (0.22, 0.42, 0.58)), (0.40, (0.76, 0.70, 0.50)),
            (0.46, (0.36, 0.56, 0.27)), (0.64, (0.27, 0.45, 0.22)), (0.76, (0.47, 0.43, 0.39)),
            (0.86, (0.62, 0.60, 0.58)), (1.0, (0.94, 0.95, 0.97)))


def height_at(x, z, height=6.0, feature_size=14.0, octaves=5, seed=7):
    """Terrain height in metres at horizontal position (x, z): fBm gradient noise times ``height``.

    The noise is zero at every lattice point, so height_at is 0 wherever x and z are whole multiples of
    ``feature_size``."""
    return height * meshkit.fbm_2d(x / feature_size, z / feature_size, octaves=octaves, seed=seed)


def terrain_color(normalized_height, steepness):
    """RGBA colour for a height in [0, 1] (low to high) and a steepness in [0, 1] (flat to vertical)."""
    t = min(1.0, max(0.0, normalized_height))
    for (t0, c0), (t1, c1) in zip(_PALETTE, _PALETTE[1:]):
        if t <= t1:
            w = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            color = tuple(c0[k] + (c1[k] - c0[k]) * w for k in range(3))
            break
    rock = (0.45, 0.41, 0.38)
    blend = min(1.0, max(0.0, (steepness - 0.35) / 0.3))
    return tuple(color[k] + (rock[k] - color[k]) * blend for k in range(3)) + (1.0,)


def heightmap_terrain(size=40.0, resolution=40, height=6.0, feature_size=14.0, octaves=5, seed=7):
    """A terrain mesh of (resolution + 1)^2 vertices and resolution^2 quads, centred on the origin, +Y up.

    Columns run along +X and rows along +Z. Normals come from central differences of the height field, UVs
    span [0, 1] over the square (u along +X, v along +Z) and colours band by height with rock on steep slopes."""
    if not size > 0 or resolution < 1 or height < 0 or not feature_size > 0:
        raise meshkit.MeshError("parameter_invalid", "size > 0, resolution >= 1, height >= 0, feature_size > 0")
    step = size / resolution
    half = size / 2.0
    side = resolution + 3
    field = [[height_at(-half + (c - 1) * step, -half + (r - 1) * step, height, feature_size, octaves, seed)
              for c in range(side)] for r in range(side)]
    vertices, normals, uvs, colors = [], [], [], []
    for r in range(resolution + 1):
        for c in range(resolution + 1):
            y = field[r + 1][c + 1]
            dx = (field[r + 1][c + 2] - field[r + 1][c]) / (2.0 * step)
            dz = (field[r + 2][c + 1] - field[r][c + 1]) / (2.0 * step)
            normal = meshkit.vnormalize((-dx, 1.0, -dz))
            vertices.append((-half + c * step, y, -half + r * step))
            normals.append(normal)
            uvs.append((c / resolution, r / resolution))
            relative = 0.5 + 0.5 * y / height if height > 0 else 0.5
            colors.append(terrain_color(relative, 1.0 - normal[1]))
    return meshkit.Mesh(vertices, meshkit.grid_faces(resolution + 1, resolution + 1), normals=normals, uvs=uvs,
                        colors=colors, name="terrain", material=meshkit.material("terrain", (1.0, 1.0, 1.0, 1.0),
                                                                                  roughness=0.9))


def main(argv=None):
    """Command line: write the terrain as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=heightmap_terrain)


if __name__ == "__main__":
    raise SystemExit(main())
