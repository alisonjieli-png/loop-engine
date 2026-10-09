# Toon bands material from a fixed light direction

Creates a toon material with hard colour bands. The shading term is the half-Lambert (N . L) * 0.5 + 0.5 between the world normal and a light direction stored in the material, quantised by a constant colour ramp into equal bands from the shadow colour to the lit colour. A facing term above a threshold adds a dark rim like an ink line. The result is emitted, so the bands come from the stated direction and look the same in every renderer.

## When to use it

Use it for anime and comic looks, game-style characters, illustrations and turntables where the shading must stay identical between Cycles, EEVEE and the viewport. Point `light_direction` where the key light should appear to come from.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_toon_bands.py`.
2. Enable "Baltor Toon Bands Material".
3. Run it from View3D > Object > Toon Bands Material (with an object active). The operator is `baltor.material_toon_bands`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python material_toon_bands.py -- --bands 4 --light_direction 0.3,-0.6,0.7 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file.

### From Python

The core needs no Blender:

```python
import material_toon_bands
graph = material_toon_bands.material_graph(bands=4)
print(material_toon_bands.band_index([0.0, 0.0, 1.0], bands=4))
```

Inside Blender, `material_toon_bands.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `material_name` | string | `Baltor Toon` | any | text | Name of the new material. |
| `lit_color` | vector | 0.95,0.55,0.2 | 0.0 to 1.0 | linear RGB | Colour of the brightest band. |
| `shadow_color` | vector | 0.18,0.05,0.12 | 0.0 to 1.0 | linear RGB | Colour of the darkest band. |
| `bands` | int | 3 | 2 to 8 | count | Number of flat colour bands. |
| `light_direction` | vector | 0.5,-0.4,0.75 | -1.0 to 1.0 | direction | Direction toward the light in world space; normalised. |
| `rim_color` | vector | 0.02,0.01,0.02 | 0.0 to 1.0 | linear RGB | Colour of the ink rim. |
| `rim_width` | float | 0.25 | 0.0 to 0.9 | ratio | Width of the rim; 0 turns it off. |
| `assign` | bool | true | true or false | flag | Assign the material to the active object. |

## Outputs

A material named by `material_name` (default `Baltor Toon`) with 10 named nodes ending in an Emission shader. When `assign` is true it replaces the material slots of the active object; otherwise it keeps a fake user. The core returns the tree as `trees[0]`.

With the default parameters the core returns 10 nodes, 9 links. The package tests pin these numbers.

## Limits

Stylized and not physically based: scene lights, shadows and bounce light do not affect it, because the light direction is a material parameter and the colour is emitted. The rim follows the facing angle, so flat faces seen edge-on darken entirely; it is not a true outline. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Half-Lambert term (N . L) * 0.5 + 0.5
- Quantisation by a constant-interpolation colour ramp
- Facing term of the Layer Weight node for a rim

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
