# Loft through a stack of profiles

Builds a skin through closed profiles in order. Each profile is resampled to the same number of points, turned counter-clockwise about the direction from the first to the last profile, and rotated to line up with its neighbour; quads join the rings and the end rings are capped.

## When to use it

Use it for bottles and vases from cross-sections, boat and aircraft hulls from stations, towers that change from square to octagon, and organic shapes from scanned slices.

## How it works

Resampling walks the polygon by arc length. Orientation is fixed with the Newell normal against the loft direction. Alignment picks the cyclic shift with the least summed squared distance to the previous ring. Caps are ear clipped in the plane of the dominant normal axis.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `shape` | str | name | `bottle` | one of `bottle`, `tower`, `boat` | Demonstration stack of profiles. |
| `samples` | int | count | `48` | 3 to 100000 | Points per profile after resampling. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 loft_profiles.py --output model.gltf --shape bottle --samples 48
```

From Python:

```python
from loft_profiles import loft

base = [(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)]
top = [(-0.5, 2, -0.5), (0.5, 2, -0.5), (0.5, 2, 0.5), (-0.5, 2, 0.5)]
frustum = loft([base, top])
```

Entry points:

- `resample_closed(polygon, count)`: ``count`` points spaced evenly by arc length around a closed polygon, starting at its first vertex.
- `align(reference, ring)`: ``ring`` cyclically shifted to minimize the summed squared distance to ``reference`` (same orientation assumed), which keeps the skin from twisting.
- `loft(profiles, samples=None, caps=True)`: A closed skin through 3D profiles (each a closed planar polygon, listed from the first end to the other).
- `demo_profiles(shape='bottle')`: Closed profiles (3D, horizontal) for a bottle (circles), a tower (square turning into an octagon) or a boat hull (U-shaped sections closed at the deck).
- `build(shape='bottle', samples=48)`: The lofted demonstration solid with smooth normals.
- `main(argv=None)`: Command line: write the lofted solid (.gltf or .obj) and print a JSON summary.

## Complexity

O(profiles * samples^2) for the alignment search.

## Outputs

- `.gltf`: the lofted demonstration solid with POSITION and NORMAL
- `.obj`: the same solid as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `bottle`: `loft(profiles=demo_profiles(...), samples=48)` gives 336 vertices; 380 faces; watertight; Euler characteristic 2.
- `box`: `loft(profiles=[2 items])` gives 8 vertices; 8 faces; watertight; volume 8 (tolerance 1e-12).
- `frustum_with_reversed_ring`: `loft(profiles=[2 items])` gives watertight; volume 7 (tolerance 1e-12).
- `square_to_circle_resampling`: `resample_closed(polygon=[4 items], count=8)` gives points matching the listed coordinates.

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Profiles should be planar, simple and stacked without crossing each other; the alignment tries every cyclic shift (quadratic in the sample count). Corners are kept only when resampling lands on them. Side quads between non-parallel profiles are not planar.
