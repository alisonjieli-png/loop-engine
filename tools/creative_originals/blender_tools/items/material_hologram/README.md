# Hologram material with scanlines and glitch bands

Creates a hologram look. Scanlines come from the fractional part of world height times the line density, sharpened by a map range into thin bright lines. The Fresnel term of a Layer Weight node brightens the silhouette, and a coarse noise along Z, thresholded, makes horizontal glitch bands that dim the image. The combined value drives both the emission strength and the mix from a transparent shader to the emission, so only lines and rims glow.

## When to use it

Use it for sci-fi projections, holographic displays, ghosts, scanned-object reveals and futuristic user interfaces. Animate the object's height or the line density for motion.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_hologram.py`.
2. Enable "Baltor Hologram Material".
3. Run it from View3D > Object > Hologram Material (with an object active). The operator is `baltor.material_hologram`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python material_hologram.py -- --line_density 80 --glitch 0.7 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file.

### From Python

The core needs no Blender:

```python
import material_hologram
graph = material_hologram.material_graph(line_density=80)
print(material_hologram.scanline(0.024, line_density=40))  # inside a line
```

Inside Blender, `material_hologram.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `material_name` | string | `Baltor Hologram` | any | text | Name of the new material. |
| `color` | vector | 0.1,0.75,1.0 | 0.0 to 1.0 | linear RGB | Colour of the hologram light. |
| `line_density` | float | 40.0 | 1.0 to 5000.0 | 1/m | Scanlines per metre of world height. |
| `line_width` | float | 0.25 | 0.01 to 0.9 | ratio | Share of each line period that glows. |
| `rim` | float | 0.6 | 0.0 to 1.0 | ratio | Strength of the Fresnel rim. |
| `glitch` | float | 0.5 | 0.0 to 1.0 | ratio | How much the glitch bands dim the hologram. |
| `brightness` | float | 4.0 | 0.0 to 1000.0 | ratio | Emission strength at full brightness. |
| `assign` | bool | true | true or false | flag | Assign the material to the active object. |

## Outputs

A material named by `material_name` (default `Baltor Hologram`) with 16 named nodes and backface culling off. When `assign` is true it replaces the material slots of the active object; otherwise it keeps a fake user. The core returns the tree as `trees[0]`.

With the default parameters the core returns 16 nodes, 17 links. The package tests pin these numbers.

## Limits

Static: scanlines and glitches do not move unless you animate the mapping or a value. Lines follow world Z, so they stay horizontal when the object rotates. Transparency through a Transparent BSDF costs extra samples; EEVEE needs blended or dithered render settings. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Scanlines from the fractional part of height times density
- Fresnel rim from the Layer Weight node
- Thresholded noise along one axis for bands

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
