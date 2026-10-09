# Geodesic dome with strut length classes

Builds a geodesic dome. An icosahedron is turned so a vertex points up, each face is split into a triangular grid of the chosen frequency, the grid points are pushed onto the sphere, and the upper half is kept. With an even frequency the cut runs along grid edges on the equator, so the rim is flat. The dome is built either as hexagonal struts between small hub spheres or as a shell of panels with a thickness. The report lists every distinct strut length with its count and chord factor (length over radius), which is what a builder cuts.

## When to use it

Use it for greenhouses, planetariums, playground climbers, sci-fi habitats and festival domes, and to plan a real build: the strut classes tell you how many struts of each length to cut.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `geodesic_dome.py`.
2. Enable "Baltor Geodesic Dome".
3. Run it from View3D > Add > Mesh > Geodesic Dome. The operator is `baltor.geodesic_dome`; its redo panel shows every parameter listed below.

### As a script

```
blender --background --python geodesic_dome.py -- --frequency 4 --mode panels --radius 5 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import geodesic_dome
dome = geodesic_dome.build_geometry(frequency=3, radius=4.0)
for row in dome["report"]["strut_classes"]:
    print(row["length_m"], row["count"], row["chord_factor"])
```

Inside Blender, `geodesic_dome.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `frequency` | int | 2 | 1 to 10 | count | Divisions of each icosahedron edge; even values give a flat rim. |
| `radius` | float | 3.0 | 0.05 to 1000.0 | m | Radius of the sphere the hubs lie on. |
| `mode` | choice | `struts` | `struts`, `panels` | mode | Struts with hubs, or a closed panel shell. |
| `strut_radius` | float | 0.035 | 0.001 to 10.0 | m | Radius of each hexagonal strut (struts mode). |
| `hub_radius` | float | 0.07 | 0.001 to 20.0 | m | Radius of each hub (struts mode). |
| `thickness` | float | 0.08 | 0.001 to 50.0 | m | Shell thickness (panels mode). |

## Outputs

One mesh object named `Geodesic Dome` with the material `Baltor Dome Frame`, centred on the 3D cursor and standing on z = 0. The core returns `vertices`, `faces` and a `report` with the numbers of hubs, struts and panels, the strut classes, the rim type and the height.

With the default parameters the core returns 1092 vertices, 1040 faces. The package tests pin these numbers.

## Limits

Class I subdivision with the vertex-up orientation only; other classes, orientations and truncations (such as 5/8 domes) are not available. Odd frequencies end in a stepped rim. Struts are straight hexagonal prisms that overlap the hubs; connector design, panel joints and loads are not modelled. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Class I geodesic subdivision of icosahedron faces into a triangular grid
- Projection of grid points onto the sphere
- Chord factors of geodesic struts
- Hemisphere cut along the equator of a vertex-up icosahedron

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
