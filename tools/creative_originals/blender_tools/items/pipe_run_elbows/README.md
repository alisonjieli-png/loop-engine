# Pipe run with bent elbows and flanges

Builds a pipe along a list of corner points. Every corner becomes a circular elbow tangent to both runs, starting R * tan(theta / 2) before the corner, where R is the bend radius and theta the turn angle. The round section is swept along the straight runs and arcs with rotation-minimising frames, so the faces do not twist through the bends, and both ends are capped. Flanges can be added at the ends and at every joint between a run and an elbow.

## When to use it

Use it to lay out plumbing, factory piping, ducts, handrails with bends or conduits along a route you know as points. The report gives the elbow angles and the centreline length.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `pipe_run_elbows.py`.
2. Enable "Baltor Pipe Run With Elbows".
3. Run it from View3D > Add > Mesh > Pipe Run. The operator is `baltor.pipe_run_elbows`; its redo panel shows every parameter listed below.

### As a script

```
blender --background --python pipe_run_elbows.py -- --points "0,0,0; 3,0,0; 3,2,0; 3,2,2" --radius 0.05 --bend_radius 0.2 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import pipe_run_elbows
pipe = pipe_run_elbows.build_geometry(points="0,0,0; 2,0,0; 2,2,0", bend_radius=0.3)
print(pipe["report"])  # one 90 degree elbow and the centreline length
```

Inside Blender, `pipe_run_elbows.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `points` | string | `0,0,0; 2.5,0,0; 2.5,2,0; 2.5,2,1.6; 0.5,2,1.6` | any | m | Centreline corners as x,y,z separated by semicolons. |
| `radius` | float | 0.08 | 0.002 to 5.0 | m | Outer radius of the pipe. |
| `bend_radius` | float | 0.24 | 0.004 to 50.0 | m | Centreline radius of every elbow; at least the pipe radius. |
| `sides` | int | 16 | 3 to 128 | count | Sides of the pipe section. |
| `bend_segments` | int | 10 | 1 to 96 | count | Segments along a 90 degree elbow; other angles scale. |
| `flanges` | bool | true | true or false | flag | Add flanges at both ends and at every elbow joint. |
| `flange_ratio` | float | 1.6 | 1.05 to 4.0 | ratio | Flange radius divided by the pipe radius. |

## Outputs

One smooth-shaded mesh object named `Pipe Run` with the material `Baltor Pipe Paint`, in the coordinates of the given points relative to the 3D cursor. The core returns `vertices`, `faces`, `smooth` and a `report` with the elbow count, bend angles, centreline length and flange count.

With the default parameters the core returns 816 vertices, 690 faces. The package tests pin these numbers.

## Limits

Solid pipe without an inner bore; the wall thickness is not modelled. Elbows are circular arcs of one bend radius; tees, reducers and valves are not generated. Flanges are plain cylinders that overlap the pipe rather than being merged with it. A path that turns back on itself, or a run shorter than its two elbows need, is refused. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Tangent arc fillet: tangent length R tan(theta / 2), centre on the bisector
- Rotation-minimising frames by the double reflection method (Wang et al. 2008)
- Rodrigues rotation for points on the elbow arc

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
