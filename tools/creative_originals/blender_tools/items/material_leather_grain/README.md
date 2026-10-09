# Pebbled leather material with creases

Creates a pebbled leather material. One Voronoi cell pattern is read twice: the distance to the nearest cell edge becomes a crease mask, and the distance to the cell centre gives every pebble a dome. Their product drives the bump, so pebbles rise between sunken creases; the crease mask also darkens and roughens the creases, and a fine noise varies the tone.

## When to use it

Use it for handbags, wallets, shoes, car and sofa seats, belts, gloves and book covers. Set `grain_scale` so that one pebble is about a millimetre wide on real-scale objects.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_leather_grain.py`.
2. Enable "Baltor Leather Grain Material".
3. Run it from View3D > Object > Leather Grain Material (with an object active). The operator is `baltor.material_leather_grain`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python material_leather_grain.py -- --grain_scale 250 --crease_width 0.08 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file.

### From Python

The core needs no Blender:

```python
import material_leather_grain
graph = material_leather_grain.material_graph(grain_scale=250)
print(material_leather_grain.crease_mask(0.03))  # 0.5 halfway out of a crease
```

Inside Blender, `material_leather_grain.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `material_name` | string | `Baltor Leather` | any | text | Name of the new material. |
| `leather_color` | vector | 0.16,0.06,0.025 | 0.0 to 1.0 | linear RGB | Colour of the grain surface. |
| `crease_color` | vector | 0.05,0.018,0.008 | 0.0 to 1.0 | linear RGB | Colour inside the creases. |
| `grain_scale` | float | 160.0 | 5.0 to 5000.0 | 1/m | Grain cells per metre. |
| `crease_width` | float | 0.06 | 0.005 to 0.4 | ratio | Width of the creases as a share of a cell. |
| `bump` | float | 0.45 | 0.0 to 1.0 | ratio | Strength of the grain bump. |
| `roughness` | float | 0.42 | 0.0 to 1.0 | ratio | Roughness of the grain surface; creases are rougher. |
| `assign` | bool | true | true or false | flag | Assign the material to the active object. |

## Outputs

A material named by `material_name` (default `Baltor Leather`) with 13 named nodes. When `assign` is true it replaces the material slots of the active object; otherwise it keeps a fake user. The core returns the tree as `trees[0]`.

With the default parameters the core returns 13 nodes, 16 links. The package tests pin these numbers.

## Limits

An even pebble grain only; no stitching, wrinkles from use, scratches or pore detail. Object coordinates tie the grain size to the object's scale, so scaled objects need a matching grain scale. The bump is subtle at a distance. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Voronoi distance to edge for creases
- Voronoi F1 distance for domed cells
- Overlay blend for tone variation

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
