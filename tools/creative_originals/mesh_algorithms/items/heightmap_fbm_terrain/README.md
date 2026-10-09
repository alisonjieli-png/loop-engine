# Heightmap terrain from fractal noise

Builds a regular grid terrain displaced by fractional Brownian motion of seeded gradient noise. Normals come from the height field, texture coordinates span the square and vertex colours band from water blue through sand, grass and rock to snow, with rock on steep slopes.

## When to use it

Use it for game ground, background landscapes, physics test terrain and as input to erosion or scattering steps. Change the seed for a new landscape and feature_size for the spacing of hills.

## How it works

The height at (x, z) is the height parameter times an octave sum of gradient noise, each octave at twice the frequency and half the amplitude of the last, normalized by the amplitude total. Heights are sampled on the grid plus a one-cell border, normals use central differences, and the colour is a piecewise-linear palette over normalized height blended toward rock where the normal tilts away from +Y.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `size` | float | m | `40.0` | 0.001 to 100000 | Side length of the square terrain, centred on the origin. |
| `resolution` | int | cells | `40` | 1 to 1024 | Grid cells per side; the grid has (resolution + 1)^2 vertices. |
| `height` | float | m | `6.0` | 0 to 100000 | Noise amplitude; heights stay within about plus or minus this value. |
| `feature_size` | float | m | `14.0` | 0.001 to 100000 | Horizontal size of the largest hills (the first noise octave's wavelength). |
| `octaves` | int | count | `5` | 1 to 12 | Noise octaves; each adds detail at half the size and half the amplitude. |
| `seed` | int | integer | `7` | 0 to 2147483647 | Noise seed; the same seed gives the same terrain. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 heightmap_fbm_terrain.py --output model.gltf --size 40.0 --resolution 40 --height 6.0 --feature-size 14.0 --octaves 5 --seed 7
```

From Python:

```python
import meshkit
from heightmap_fbm_terrain import heightmap_terrain, height_at

ground = heightmap_terrain(size=80.0, resolution=64, height=10.0, seed=3)
print(height_at(5.0, -2.0, height=10.0, seed=3))
meshkit.write_gltf("ground.gltf", [ground])
```

Entry points:

- `height_at(x, z, height=6.0, feature_size=14.0, octaves=5, seed=7)`: Terrain height in metres at horizontal position (x, z): fBm gradient noise times ``height``.
- `terrain_color(normalized_height, steepness)`: RGBA colour for a height in [0, 1] (low to high) and a steepness in [0, 1] (flat to vertical).
- `heightmap_terrain(size=40.0, resolution=40, height=6.0, feature_size=14.0, octaves=5, seed=7)`: A terrain mesh of (resolution + 1)^2 vertices and resolution^2 quads, centred on the origin, +Y up.
- `main(argv=None)`: Command line: write the terrain as .gltf or .obj and print a JSON summary.

## Complexity

O(resolution^2 * octaves). One noise sum per grid vertex plus a one-cell border for the normals.

## Outputs

- `.gltf`: the terrain mesh with POSITION, NORMAL, TEXCOORD_0 and COLOR_0, indexed triangles
- `.obj`: the terrain as Wavefront OBJ with positions, texture coordinates, normals and quads

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `flat_when_height_is_zero`: `heightmap_terrain(size=10, resolution=4, height=0)` gives 25 vertices; 32 triangles; every vertex on the plane n . p = 0, n = [0.0, 1.0, 0.0]; surface area 100 (tolerance 1e-09); bounds [-5.0, 0.0, -5.0] to [5.0, 0.0, 5.0].
- `small_grid`: `heightmap_terrain(size=10, resolution=8)` gives 81 vertices; 64 faces; 128 triangles; manifold; 1 boundary loops; Euler characteristic 1; inside [-5.0, -12.0, -5.0] to [5.0, 12.0, 5.0]; unit vertex normals; vertex normals agree with the face winding on 100 percent of triangles; vertex colours; texture coordinates spanning [0.0, 0.0] to [1.0, 1.0].
- `zero_on_lattice`: `height_at(x=14, z=28)` gives exactly 0.

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

A single height per (x, z): no overhangs, caves or arches. The noise is not periodic, so tiles do not wrap. Heights stay within about plus or minus the height parameter (at most twice it). The colour bands are a fixed stylized palette, not a physical material model.
