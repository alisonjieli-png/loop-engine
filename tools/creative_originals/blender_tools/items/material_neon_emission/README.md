# Neon tube material with a glass sheath

Creates a material that looks like a lit neon tube. The Layer Weight node's Fresnel term mixes an emissive core with a clear glass sheath: face on the glowing gas dominates, toward the edges of the tube the glass and its reflections take over, which rounds the tube. A colour ramp on the facing term pushes the core toward white, the way bright neon overexposes in its centre.

## When to use it

Use it on curves or thin tubes for shop signs, bar lettering, cyberpunk streets, arcades and stylized rim lighting. Pair it with a glare compositor setup for bloom.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_neon_emission.py`.
2. Enable "Baltor Neon Tube Material".
3. Run it from View3D > Object > Neon Tube Material (with the tube active). The operator is `baltor.material_neon_emission`; its redo panel shows every parameter listed below.

### As a script

```
blender --background sign.blend --python material_neon_emission.py -- --color 0.1,0.4,1.0 --strength 20 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file.

### From Python

The core needs no Blender:

```python
import material_neon_emission
graph = material_neon_emission.material_graph(color=[0.1, 0.4, 1.0])
print(material_neon_emission.core_color(0.0))  # whitened face-on colour
```

Inside Blender, `material_neon_emission.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

`fixture(bpy.context)` adds the upright torus named `Neon Tube Demo` that the native check lights up.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `material_name` | string | `Baltor Neon` | any | text | Name of the new material. |
| `color` | vector | 1.0,0.08,0.35 | 0.0 to 1.0 | linear RGB | Colour of the gas glow. |
| `strength` | float | 12.0 | 0.0 to 10000.0 | ratio | Emission strength of the core. |
| `core_whiteness` | float | 0.35 | 0.0 to 1.0 | ratio | How far the face-on centre shifts toward white. |
| `sheath` | float | 0.35 | 0.0 to 1.0 | ratio | Fresnel blend toward the glass sheath at the silhouette. |
| `assign` | bool | true | true or false | flag | Assign the material to the active object. |

## Outputs

A material named by `material_name` (default `Baltor Neon`) with 6 named nodes. When `assign` is true it replaces the material slots of the active object; otherwise it keeps a fake user. The core returns the tree as `trees[0]`.

With the default parameters the core returns 6 nodes, 6 links. The package tests pin these numbers.

## Limits

Emission lights the scene only in renderers that treat emissive meshes as lights (Cycles does, with noise); EEVEE needs light probes or extra lamps. No bloom: add glare in the compositor. The white core is a stylized ramp, not a gas discharge spectrum. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Layer Weight facing and Fresnel terms
- Mix of emission and glass by Fresnel
- Colour ramp toward white for an overexposed core

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
