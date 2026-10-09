# Procedural wood material with growth rings

Creates a shader node material that draws wood growth rings around the object's Z axis. The ring phase is computed with math nodes as the fractional part of rings per metre times the distance from the axis, after the coordinates are warped by low-frequency noise. A colour ramp turns the phase into earlywood and latewood bands, a stretched noise darkens pores, and the same phase drives roughness and a bump. The material is assigned to the active mesh.

## When to use it

Use it for chairs, tables, floor boards, handles and other props that need wood without texture files, or as a starting graph to edit by hand. Set `rings_per_metre` from the look you want: about 20 for coarse softwood, 100 or more for tight hardwood.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_wood_rings.py`.
2. Enable "Baltor Wood Rings Material".
3. Run it from View3D > Object > Wood Rings Material (with a mesh object active). The operator is `baltor.material_wood_rings`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python material_wood_rings.py -- --rings_per_metre 90 --latewood_fraction 0.25 --warp 0.03 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file.

### From Python

The core needs no Blender:

```python
import material_wood_rings
graph = material_wood_rings.material_graph(rings_per_metre=90)
tree = graph["trees"][0]
print(len(tree["nodes"]), len(tree["links"]))
print(material_wood_rings.ring_value(0.0125, rings_per_metre=60))  # 0.75
```

Inside Blender, `material_wood_rings.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `material_name` | string | `Baltor Wood` | any | text | Name of the new material. |
| `rings_per_metre` | float | 60.0 | 2.0 to 600.0 | 1/m | Growth rings per metre of radius from the object's Z axis. |
| `latewood_fraction` | float | 0.3 | 0.05 to 0.9 | ratio | Share of each ring taken by the dark latewood band. |
| `warp` | float | 0.02 | 0.0 to 0.3 | m | How far noise displaces the rings. |
| `warp_scale` | float | 3.0 | 0.1 to 60.0 | 1/m | Frequency of the warping noise across the grain. |
| `grain_stretch` | float | 8.0 | 1.0 to 50.0 | ratio | How much longer noise features are along the grain (Z) than across it. |
| `earlywood_color` | vector | 0.6,0.38,0.2 | 0.0 to 1.0 | linear RGB | Colour of the light earlywood band. |
| `latewood_color` | vector | 0.28,0.14,0.06 | 0.0 to 1.0 | linear RGB | Colour of the dark latewood band. |
| `pore_strength` | float | 0.35 | 0.0 to 1.0 | ratio | How much the stretched pore noise darkens the colour. |
| `roughness` | vector | 0.45,0.62,0.0 | 0.0 to 1.0 | ratio | Roughness in latewood and in earlywood (third value unused). |
| `bump_strength` | float | 0.2 | 0.0 to 1.0 | ratio | Strength of the ring bump. |
| `assign` | bool | true | true or false | flag | Assign the material to the active mesh object. |

## Outputs

A material named by `material_name` (default `Baltor Wood`). Its node tree holds 18 nodes; every node has a readable name and label. When `assign` is true and a mesh is active, the mesh's material slots are replaced by this material; otherwise the material keeps a fake user so it is saved. The core returns the tree as `trees[0]` with `nodes` and `links`.

With the default parameters the core returns 18 nodes, 21 links. The package tests pin these numbers.

## Limits

Rings are cylinders around the object's local Z axis, so the grain follows the object's Z; rotate the object or edit the Grain Space mapping for other directions. Colours are a stylized approximation, not measured wood data. Pores come from stretched noise, not cell structure. Object coordinates make the pattern scale with the object. Rendered here with Cycles CPU only; EEVEE output is expected to match but was not rendered. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Growth rings as fract(k * radial distance) from math nodes
- Domain warping of coordinates by centred noise
- Anisotropic noise by scaling the grain axis before sampling
- Height-to-normal bump mapping

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
