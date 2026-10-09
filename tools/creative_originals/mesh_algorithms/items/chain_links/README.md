# Chain of interlocking oval links

Builds a straight chain: every link is the same closed tube around a stadium-shaped centre line, written once as a glTF mesh and placed by one node per link. Odd links turn 90 degrees about X so neighbours hook through each other with the given clearance.

## When to use it

Use it for anchor and swing chains, fences, rigging, jewellery and dungeon props, or as an example of glTF instancing where many nodes share one mesh.

## How it works

The centre line is two straight sides joined by two semicircles, walked by arc length. A circle of the wire radius is swept along it in the plane's frame (the in-plane normal and +Y). Links are spaced by straight + 2 end_radius - 2 wire_radius - clearance, so the end of each link sits inside the bend of the next.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `links` | int | count | `7` | 1 to 10000 | Number of links. |
| `straight` | float | m | `0.4` | 0 to 1e+06 | Length of the straight sides of each link's centre line. |
| `end_radius` | float | m | `0.3` | 1e-06 to 1e+06 | Radius of the round ends of the centre line; above 2 * wire_radius + clearance. |
| `wire_radius` | float | m | `0.08` | 1e-06 to 1e+06 | Radius of the wire. |
| `clearance` | float | m | `0.02` | 0 to 1e+06 | Gap left between neighbouring links where they hook. |
| `samples` | int | count | `64` | 8 to 100000 | Samples along each link's centre line. |
| `sides` | int | count | `12` | 3 to 1024 | Divisions around the wire. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 chain_links.py --output model.gltf --links 7 --straight 0.4 --end-radius 0.3 --wire-radius 0.08 --clearance 0.02 --samples 64 --sides 12
```

From Python:

```python
import meshkit
from chain_links import chain

scene = chain(links=12, wire_radius=0.05)
meshkit.write_gltf("chain.gltf", scene["meshes"], scene["nodes"])
```

Entry points:

- `stadium_point(fraction, straight=0.4, end_radius=0.3)`: (position, unit tangent) on the stadium centre line in the XZ plane at arc-length ``fraction`` in [0, 1), starting at the middle of the +Z straight side and running counter-clockwise seen from +Y.
- `link_mesh(straight=0.4, end_radius=0.3, wire_radius=0.08, samples=64, sides=12)`: One closed link in the XZ plane centred at the origin: samples * sides vertices and quads (torus topology). The centre line is planar, so the frame is the in-plane normal and +Y.
- `chain(links=7, straight=0.4, end_radius=0.3, wire_radius=0.08, clearance=0.02, samples=64, sides=12)`: A scene dict {"meshes": [link], "nodes": [...]}: a root node and one child node per link along X.
- `chain_mesh(links=7, straight=0.4, end_radius=0.3, wire_radius=0.08, clearance=0.02, samples=64, sides=12)`: The chain baked into one mesh (each link transformed by its node), for measuring and for OBJ.
- `main(argv=None)`: Command line: write the chain (instanced nodes in .gltf, baked in .obj) and print a JSON summary.

## Complexity

O(samples * sides) for the link; O(links) nodes.

## Outputs

- `.gltf`: one link mesh and a root node with one child node per link (instancing)
- `.obj`: the chain with every link transformed into place

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `baked_chain`: `chain_mesh()` gives 5376 vertices; 7 connected components; genus 7; watertight; Euler characteristic 0; volume 0.360858 (tolerance 0.00108257).
- `centre_line_start`: `stadium_point(fraction=0)` gives values matching the listed numbers (tolerance 1e-15).
- `instanced_scene`: `chain(links=5)` gives 1 meshes; 6 nodes; 768 faces.
- `single_link`: `link_mesh()` gives 768 vertices; 768 faces; watertight; Euler characteristic 0; genus 1; volume 0.0515511 (tolerance 0.000154653); unit vertex normals; vertex normals agree with the face winding on 100 percent of triangles.

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Links are rigid and straight in a line; there is no physics or sag. Contact is only avoided geometrically when end_radius exceeds twice the wire radius plus the clearance (checked). No texture coordinates.
