# Barrel from bulged staves, hoops and heads

Builds a barrel the way a cooper does: separate staves bent to a parabolic bilge profile with small gaps between them, iron hoops that follow the profile just outside the staves, and two head discs set into the ends. Every stave, hoop and head is its own closed solid, and each kind has its own material slot so they can be shaded separately.

## When to use it

Use it for taverns, wine cellars, ships, docks and medieval or western game scenes, or when a barrel must break apart into staves for an effect.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `barrel_staves.py`.
2. Enable "Baltor Barrel Staves".
3. Run it from View3D > Add > Mesh > Barrel. The operator is `baltor.barrel_staves`; its redo panel shows every parameter listed below.

### As a script

```
blender --background --python barrel_staves.py -- --staves 24 --hoops 6 --bilge_radius 0.36 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import barrel_staves
barrel = barrel_staves.build_geometry(staves=24, hoops=6)
print(barrel["report"]["outer_volume_litres"])
```

Inside Blender, `barrel_staves.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `height` | float | 0.9 | 0.05 to 20.0 | m | Height of the staves. |
| `head_radius` | float | 0.28 | 0.02 to 10.0 | m | Outer radius at the top and bottom. |
| `bilge_radius` | float | 0.34 | 0.02 to 10.0 | m | Outer radius at mid height; at least the head radius. |
| `staves` | int | 20 | 6 to 120 | count | Number of staves. |
| `stave_thickness` | float | 0.025 | 0.002 to 1.0 | m | Radial thickness of each stave. |
| `gap` | float | 0.002 | 0.0 to 0.05 | m | Gap between neighbouring staves at the head radius. |
| `rows` | int | 12 | 2 to 96 | count | Segments along the height of each stave and hoop. |
| `hoops` | int | 4 | 0 to 12 | count | Number of hoops, placed symmetrically. |
| `hoop_width` | float | 0.045 | 0.005 to 1.0 | m | Height of each hoop band. |
| `heads` | bool | true | true or false | flag | Close the barrel with two recessed head discs. |

## Outputs

One mesh object named `Barrel` with the material slots `Baltor Oak Stave`, `Baltor Iron Hoop` and `Baltor Oak Head`, base at z = 0 under the 3D cursor. The core returns `vertices`, `faces`, `face_materials` and a `report` with the stave and hoop counts and the outer volume.

With the default parameters the core returns 1840 vertices, 1724 faces. The package tests pin these numbers.

## Limits

The bilge is a parabola in height, not a measured cooperage curve. Staves are faceted (one chord per stave across its width) and have no bevel, chime chamfer or bung hole. Hoops are plain rectangular bands with no rivets. The volume is the outer volume from the profile, not the inner capacity. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Parabolic bilge profile r(z) = r_head + (r_bilge - r_head)(1 - (2z/H - 1)^2)
- Closed slabs from a two-sided grid with side walls
- Rectangular-section rings as closed genus-one solids

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
