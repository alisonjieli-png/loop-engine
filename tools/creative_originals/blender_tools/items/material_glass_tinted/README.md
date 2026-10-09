# Tinted glass with Beer-Lambert absorption

Creates glass that is tinted the physical way: thin parts stay pale and thick parts get deeper in colour. You give the tint as the fraction of red, green and blue light that passes through a reference thickness. The core converts it to absorption coefficients with the Beer-Lambert law, a = -ln(T) / d, then to the density and colour of a Volume Absorption node that reproduce all three channels exactly. The surface is a clear Principled transmission shader with the chosen index of refraction and roughness.

## When to use it

Use it for bottles, glasses, vases, stained glass, gems, ice and coloured liquids, especially where the same material covers parts of very different thickness.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_glass_tinted.py`.
2. Enable "Baltor Tinted Glass Material".
3. Run it from View3D > Object > Tinted Glass Material (with an object active). The operator is `baltor.material_glass_tinted`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python material_glass_tinted.py -- --tint 0.4,0.7,0.9 --reference_thickness 0.02 --ior 1.52 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file.

### From Python

The core needs no Blender:

```python
import material_glass_tinted
print(material_glass_tinted.absorption([0.5, 0.8, 0.9], 0.01))
print(material_glass_tinted.transmittance(0.1, tint=[0.5, 0.8, 0.9], reference_thickness=0.01))
```

Inside Blender, `material_glass_tinted.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `material_name` | string | `Baltor Tinted Glass` | any | text | Name of the new material. |
| `tint` | vector | 0.55,0.85,0.7 | 0.001 to 1.0 | linear RGB | Fraction of red, green and blue light that passes the reference thickness. |
| `reference_thickness` | float | 0.5 | 0.0001 to 100.0 | m | Thickness at which the tint applies. |
| `ior` | float | 1.5 | 1.0 to 3.0 | ratio | Index of refraction (window glass about 1.5). |
| `roughness` | float | 0.0 | 0.0 to 1.0 | ratio | Surface roughness; above 0 gives frosted glass. |
| `assign` | bool | true | true or false | flag | Assign the material to the active object. |

## Outputs

A material named by `material_name` (default `Baltor Tinted Glass`) with a Principled BSDF on the surface and a Volume Absorption on the volume output, with backface culling off. When `assign` is true it replaces the material slots of the active object; otherwise it keeps a fake user. The core returns the tree and a `report` with the absorption coefficients per metre and the volume density and colour.

With the default parameters the core returns 3 nodes, 2 links. The package tests pin these numbers.

## Limits

Absorption needs closed, correctly oriented meshes and a renderer that traces volumes inside objects (Cycles); EEVEE approximates refraction and volumes differently. No dispersion, no thin-film and no scattering inside the glass. Caustics depend on the renderer settings. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Beer-Lambert law T = exp(-a d)
- Absorption coefficient a = -ln(T) / d per channel
- Volume Absorption extinction density * (1 - colour)

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
