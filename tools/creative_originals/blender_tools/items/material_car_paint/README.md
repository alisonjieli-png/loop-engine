# Metallic flake car paint with a flip colour

Creates a metallic car paint. The facing term of a Layer Weight node drives a colour ramp, so the base colour shifts toward the flip colour at grazing angles. Flakes are tiny Voronoi cells whose random colours, centred on zero and scaled, tilt the base layer's normal; each flake then catches the light at its own angle. The clear coat keeps the smooth geometric normal, so a sharp reflection sits on top of the sparkle.

## When to use it

Use it on car bodies, motorbikes, helmets, toys and product shots that need a deep coloured metallic finish. Lower `flake_strength` for a subtle finish and raise `flake_scale` for finer flakes on small objects.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_car_paint.py`.
2. Enable "Baltor Car Paint Material".
3. Run it from View3D > Object > Car Paint Material (with an object active). The operator is `baltor.material_car_paint`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python material_car_paint.py -- --base_color 0.02,0.1,0.45 --flip_color 0.0,0.02,0.1 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file.

### From Python

The core needs no Blender:

```python
import material_car_paint
graph = material_car_paint.material_graph(flake_strength=0.2)
print(material_car_paint.flake_normal([0, 0, 1], [0.9, 0.5, 0.5], 0.3))
```

Inside Blender, `material_car_paint.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `material_name` | string | `Baltor Car Paint` | any | text | Name of the new material. |
| `base_color` | vector | 0.45,0.02,0.03 | 0.0 to 1.0 | linear RGB | Colour seen face on. |
| `flip_color` | vector | 0.12,0.0,0.05 | 0.0 to 1.0 | linear RGB | Colour at grazing angles. |
| `metallic` | float | 0.75 | 0.0 to 1.0 | ratio | Metallic weight of the base layer. |
| `base_roughness` | float | 0.38 | 0.0 to 1.0 | ratio | Roughness of the base layer under the coat. |
| `flake_scale` | float | 1500.0 | 10.0 to 100000.0 | 1/m | Flakes per metre. |
| `flake_strength` | float | 0.3 | 0.0 to 2.0 | ratio | How far flakes tilt the base normal. |
| `coat_roughness` | float | 0.03 | 0.0 to 1.0 | ratio | Roughness of the clear coat. |
| `assign` | bool | true | true or false | flag | Assign the material to the active object. |

## Outputs

A material named by `material_name` (default `Baltor Car Paint`) with 11 named nodes. When `assign` is true it replaces the material slots of the active object; otherwise it keeps a fake user. The core returns the tree as `trees[0]`.

With the default parameters the core returns 11 nodes, 10 links. The package tests pin these numbers.

## Limits

Flakes come from Voronoi cells in object space, so their size scales with the object and they alias at a distance unless enough samples are rendered. The flip colour uses a facing ramp, not measured pearlescent data, and the paint is not physically based beyond the Principled BSDF. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Layer Weight facing term driving a colour ramp for a flip colour
- Normal perturbation by random Voronoi cell colours for flakes
- Separate coat normal over a perturbed base normal

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
