# Soap bubble material with thin-film colours

Creates a soap bubble. A reflective Principled shader with a black base colour shows only its reflection, coloured by thin-film interference; the film thickness in nanometres runs from the top value at the top of the object to the larger bottom value at its base, like a film draining under gravity, and a noise swirls it. The reflective layer is mixed over a transparent shader by the Fresnel term, so the bubble is nearly invisible face on and shows colour toward its edges.

## When to use it

Use it on spheres for soap bubbles, on flat films for iridescent sheets, and as a starting point for oil-slick or beetle-shell effects by changing the thickness range.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_soap_bubble.py`.
2. Enable "Baltor Soap Bubble Material".
3. Run it from View3D > Object > Soap Bubble Material (with an object active). The operator is `baltor.material_soap_bubble`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python material_soap_bubble.py -- --top_thickness 200 --bottom_thickness 1200 --swirl 250 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file.

### From Python

The core needs no Blender:

```python
import material_soap_bubble
graph = material_soap_bubble.material_graph(swirl=250.0)
print(material_soap_bubble.thickness_at(1.0))  # thickness at the top, in nanometres
```

Inside Blender, `material_soap_bubble.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `material_name` | string | `Baltor Soap Bubble` | any | text | Name of the new material. |
| `top_thickness` | float | 250.0 | 0.0 to 5000.0 | nm | Film thickness at the top of the object. |
| `bottom_thickness` | float | 900.0 | 0.0 to 5000.0 | nm | Film thickness at the bottom of the object. |
| `swirl` | float | 180.0 | 0.0 to 2000.0 | nm | How far the swirling noise moves the thickness. |
| `swirl_scale` | float | 2.5 | 0.01 to 1000.0 | 1/m | Frequency of the swirls. |
| `film_ior` | float | 1.33 | 1.0 to 3.0 | ratio | Index of refraction of the soap film. |
| `assign` | bool | true | true or false | flag | Assign the material to the active object. |

## Outputs

A material named by `material_name` (default `Baltor Soap Bubble`) with 12 named nodes and backface culling off. When `assign` is true it replaces the material slots of the active object; otherwise it keeps a fake user. The core returns the tree as `trees[0]`.

With the default parameters the core returns 12 nodes, 12 links. The package tests pin these numbers.

## Limits

Needs the Thin Film inputs of the Principled BSDF (Blender 4.2 or newer). The film is shaded on a single surface with no refraction through a liquid layer, which suits thin bubbles but not thick soap water. Drainage follows the object's generated Z, so rotating the object rotates it. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Thin-film interference through the Principled BSDF thin film inputs
- Gravity drainage as a thickness gradient over height
- Fresnel mix of a transparent and a reflective shader

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
