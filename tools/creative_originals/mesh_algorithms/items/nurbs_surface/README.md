# NURBS surfaces with exact sphere and torus

Evaluates tensor-product NURBS surfaces: every row of the control net is reduced in v in homogeneous coordinates, then the resulting column in u. A profile curve revolved with the nine-point circle gives exact spheres and tori; tessellate turns any surface into a grid mesh.

## When to use it

Use it for exact round shapes (domes, tanks, rings), free-form patches from CAD control nets, or to check other tessellators against surfaces with known geometry.

## How it works

Control points are weighted into homogeneous coordinates. For a point (u, v), de Boor runs along each control row at v, then along the resulting column at u, and the result is divided by the weight. A revolved surface takes the product of a profile's weights with the circle's weights.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `shape` | str | name | `torus` | one of `sphere`, `torus`, `wave` | Demonstration surface: exact sphere, exact torus or a free-form wave patch. |
| `u_samples` | int | count | `48` | 2 to 4096 | Grid lines across the first parameter. |
| `v_samples` | int | count | `24` | 2 to 4096 | Grid lines across the second parameter. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 nurbs_surface.py --output model.gltf --shape torus --u-samples 48 --v-samples 24
```

From Python:

```python
from nurbs_surface import sphere_surface, tessellate

dome = tessellate(sphere_surface(2.0), u_samples=32, v_samples=48, closed_v=True)
```

Entry points:

- `surface_point(surface, u, v)`: Point at (u, v): each control row is reduced at v in homogeneous coordinates, then the column at u.
- `revolve_profile(profile, profile_weights, profile_degree, profile_knots)`: Surface of revolution about Y: an (r, y) NURBS profile times the nine-point exact circle.
- `sphere_surface(radius=1.0)`: Exact sphere: a five-point rational semicircle from the south to the north pole, revolved.
- `torus_surface(major_radius=1.0, minor_radius=0.35)`: Exact torus: the nine-point circle of the tube cross-section, revolved.
- `wave_surface()`: A bicubic free-form patch over [-1.5, 1.5]^2 with a 5 x 5 control net and unit weights.
- `tessellate(surface, u_samples=48, v_samples=24, closed_v=False)`: A grid mesh of u_samples x v_samples points evenly spaced in the parameters, normals from central differences in parameter space. ``closed_v`` leaves out the repeated last column of a closed direction.
- `build(shape='torus', u_samples=48, v_samples=24)`: The tessellated demonstration surface the command line writes.
- `main(argv=None)`: Command line: write the tessellated surface (.gltf or .obj) and print a JSON summary.

## Complexity

O(u_samples * v_samples * (degree_u + 1)(degree_v + 1)).

## Outputs

- `.gltf`: the tessellated surface with POSITION and NORMAL
- `.obj`: the same surface as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `exact_sphere`: `tessellate(surface=sphere_surface(...), u_samples=24, v_samples=16, closed_v=True)` gives 384 vertices; every vertex at distance 1 from [0.0, 0.0, 0.0]; watertight after welding coincident vertices; Euler characteristic 2 after welding.
- `exact_torus`: `tessellate(surface=torus_surface(...), u_samples=25, v_samples=16, closed_v=True)` gives 400 vertices; watertight after welding coincident vertices; genus 1; bounds [-1.35, -0.35, -1.35] to [1.35, 0.35, 1.35].
- `free_form_patch`: `tessellate(surface=wave_surface(...), u_samples=10, v_samples=10)` gives 100 vertices; 81 faces; 1 boundary loops; inside [-1.5, -0.5, -1.5] to [1.5, 0.5, 1.5].
- `sphere_equator`: `surface_point(surface=sphere_surface(...), u=0.5, v=0)` gives values matching the listed numbers (tolerance 1e-15).

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Uniform parameter sampling, not curvature adaptive. The sphere's poles and the closed seam are repeated grid points, so closed results are watertight after welding. Normals come from central differences in parameter space, with mesh normals at the poles.
