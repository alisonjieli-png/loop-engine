# Polished marble material with turbulent veins

Creates a node material that looks like polished marble. Veins come from the classic turbulence formula: the sine of a coordinate along the vein direction plus scaled noise, folded with an absolute value and sharpened with a power so that only thin lines stay dark. A colour ramp maps them from the stone colour to the vein colour, a second noise adds soft clouding, the vein mask drives a faint bump, and a thin clear coat gives the polish.

## When to use it

Use it for floors, kitchen counters, columns, statues, bathrooms and product plinths. Raise `vein_frequency` for busy stone, raise `sharpness` for finer veins, and turn `direction` to align the veins with the object.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_marble_veins.py`.
2. Enable "Baltor Marble Veins Material".
3. Run it from View3D > Object > Marble Veins Material (with an object active). The operator is `baltor.material_marble_veins`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python material_marble_veins.py -- --vein_frequency 6 --sharpness 14 --direction 60 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file.

### From Python

The core needs no Blender:

```python
import material_marble_veins
graph = material_marble_veins.material_graph(vein_frequency=6)
print(len(graph["trees"][0]["nodes"]))
print(material_marble_veins.vein_mask(0.0, 0.0))  # 1.0 at a vein centre
```

Inside Blender, `material_marble_veins.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `material_name` | string | `Baltor Marble` | any | text | Name of the new material. |
| `vein_frequency` | float | 2.5 | 0.1 to 200.0 | 1/m | Veins per metre across the vein direction. |
| `turbulence` | float | 0.45 | 0.0 to 2.0 | m | How far noise bends the veins. |
| `turbulence_scale` | float | 1.6 | 0.05 to 100.0 | 1/m | Frequency of the bending noise. |
| `sharpness` | float | 6.0 | 1.0 to 80.0 | exponent | Higher values give thinner veins. |
| `direction` | float | 35.0 | -180.0 to 180.0 | degree | Rotation of the vein pattern around the object's Z axis. |
| `stone_color` | vector | 0.8,0.77,0.72 | 0.0 to 1.0 | linear RGB | Colour of the stone. |
| `vein_color` | vector | 0.18,0.17,0.17 | 0.0 to 1.0 | linear RGB | Colour at the centre of a vein. |
| `clouding` | float | 0.35 | 0.0 to 1.0 | ratio | Strength of the soft clouding noise. |
| `roughness` | float | 0.12 | 0.0 to 1.0 | ratio | Roughness of the stone under the coat. |
| `coat` | float | 0.4 | 0.0 to 1.0 | ratio | Weight of the clear polish coat. |
| `assign` | bool | true | true or false | flag | Assign the material to the active object. |

## Outputs

A material named by `material_name` (default `Baltor Marble`) with 17 named nodes. When `assign` is true it replaces the material slots of the active object; otherwise it keeps a fake user so it is saved. The core returns the tree as `trees[0]`.

With the default parameters the core returns 17 nodes, 19 links. The package tests pin these numbers.

## Limits

The veins are a single family of turbulent sine bands, so they run broadly parallel; branching and crossing veins of real marble are not reproduced. Object coordinates tie the pattern to the object's scale. The subsurface weight is small and stylized, not measured. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Turbulence marble: sin of a coordinate plus scaled noise
- Vein width by raising 1 - |sin| to a power
- Soft light blend for clouding
- Clear coat layer of the Principled BSDF

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
