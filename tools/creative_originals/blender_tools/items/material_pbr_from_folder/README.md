# PBR material from a folder of maps

Builds a PBR material from a folder of texture maps. Each file name is split into lower-case words and matched against a synonym table, so `rock_basecolor.png`, `Rock_Albedo.jpg` and `rockDiffuse.png` all count as base colour. Gloss maps are inverted into roughness, a normal map named with `dx` or `directx` gets its green channel inverted, ambient occlusion is multiplied into the base colour, and a height map drives a Displacement node. Every image gets the right colour space. Files that match nothing are reported, not guessed.

## When to use it

Use it when importing texture sets from scans or texture libraries, to turn a folder of maps into a working material in one step, and to check which maps a folder really contains.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_pbr_from_folder.py`.
2. Enable "Baltor PBR From Folder".
3. Run it from View3D > Object > PBR Material From Folder (with an object active). The operator is `baltor.material_pbr_from_folder`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python material_pbr_from_folder.py -- --folder //textures/rock --uv_scale 2 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file, and the classification report is printed as one JSON line.

### From Python

The core needs no Blender:

```python
import material_pbr_from_folder
print(material_pbr_from_folder.classify(["wall_Albedo.png", "wall_Normal_DX.png", "wall_Gloss.jpg"]))
graph = material_pbr_from_folder.material_graph(
    ["wall_Albedo.png", "wall_Normal_DX.png"])
```

Inside Blender, `material_pbr_from_folder.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

`fixture(bpy.context)` writes five 16 by 16 demo maps into `//textures/pbr_demo` and adds the sphere that the native check shades.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `material_name` | string | `Baltor PBR` | any | text | Name of the new material. |
| `folder` | string | `//textures/pbr_demo` | any | path | Folder with the maps; // is relative to the .blend file. |
| `uv_scale` | float | 1.0 | 0.001 to 10000.0 | repeats | Repeats of the maps per UV unit. |
| `normal_strength` | float | 1.0 | 0.0 to 10.0 | ratio | Strength of the normal map. |
| `displacement_scale` | float | 0.02 | 0.0 to 10.0 | m | Height of the displacement from the height map. |
| `ao_strength` | float | 1.0 | 0.0 to 1.0 | ratio | How strongly ambient occlusion darkens the base colour. |
| `assign` | bool | true | true or false | flag | Assign the material to the active object. |

## Outputs

A material named by `material_name` (default `Baltor PBR`) with one image node per recognised map, loaded from the folder. `create` returns the material name and a `report` with the channels, the normal convention, the ignored files and the duplicates. The core returns the same report with the tree.

With the default parameters the core returns 15 nodes, 20 links. The package tests pin these numbers.

## Limits

Recognition is by file name tokens only; files with unusual names are listed as ignored, and when two files match one channel the first in sorted order wins and the rest are reported. Packed channel maps (such as ORM) and UDIM tile sets are not split. Height goes through the Displacement node, which renders as bump unless the material's displacement method is changed. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- File name tokenisation with camel case and separator splitting
- Colour space by channel: sRGB for colour, Non-Color for data maps
- DirectX to OpenGL normal conversion by inverting green

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process.
