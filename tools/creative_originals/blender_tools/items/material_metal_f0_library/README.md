# Metal materials from a reflectance table

Creates a metal material from a table. Each metal is stored as its approximate reflectance straight on (F0) in linear sRGB, which is exactly what a fully metallic Principled BSDF takes as its base colour. A fine noise varies the roughness a little so large surfaces do not look synthetic, and an anisotropy setting gives a brushed finish.

## When to use it

Use it when a metal should look like that metal: gold jewellery, copper pans, silver cutlery, aluminium housings, titanium parts, chrome and brass fittings. Change only the roughness to go from polished to matte.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_metal_f0_library.py`.
2. Enable "Baltor Metal Reflectance Library".
3. Run it from View3D > Object > Metal From Reflectance Table (with an object active). The operator is `baltor.material_metal_f0_library`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python material_metal_f0_library.py -- --metal copper --roughness 0.3 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file.

### From Python

The core needs no Blender:

```python
import material_metal_f0_library
print(material_metal_f0_library.reflectance("copper"))  # [0.96, 0.64, 0.54]
graph = material_metal_f0_library.material_graph(metal="silver", brushed=0.6)
```

Inside Blender, `material_metal_f0_library.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `metal` | choice | `gold` | `aluminium`, `brass`, `chromium`, `cobalt`, `copper`, `gold`, `iron`, `nickel`, `platinum`, `silver`, `titanium`, `zinc` | name | Metal to look up in the reflectance table. |
| `roughness` | float | 0.22 | 0.0 to 1.0 | ratio | Surface roughness. |
| `roughness_variation` | float | 0.05 | 0.0 to 0.5 | ratio | How far a fine noise varies the roughness. |
| `brushed` | float | 0.0 | 0.0 to 1.0 | ratio | Anisotropy for a brushed finish; 0 is plain polished or matte metal. |
| `assign` | bool | true | true or false | flag | Assign the material to the active object. |

## Outputs

A material named `Baltor ` plus the metal name (for example `Baltor Gold`) with 5 named nodes. When `assign` is true it replaces the material slots of the active object; otherwise it keeps a fake user. The core returns the tree and a `report` with the F0 and its luminance.

With the default parameters the core returns 5 nodes, 4 links. The package tests pin these numbers.

## Limits

The F0 values are approximate linear sRGB reflectances rounded to two decimals; the edge tint of real metals is left to the Principled BSDF's default model, and oxidation, patina and scratches are not included. Brass and similar alloys vary with composition. Brushed anisotropy needs tangents that follow the brushing direction. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Normal-incidence reflectance (F0) as the base colour of a metallic BSDF
- Approximate F0 values derived from measured complex refractive indices
- Anisotropic specular for brushed metal

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
