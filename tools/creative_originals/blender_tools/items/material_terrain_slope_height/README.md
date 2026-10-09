# Terrain material blending by slope and height

Creates a terrain material that decides between grass, rock and snow per point. The Z component of the world normal is the cosine of the slope angle, so a map range around the rock slope gives a rock mask on steep ground. The world height, moved up and down by a noise for a ragged edge, gives a snow line, and a flatness mask keeps snow off cliffs. Colours and roughness blend grass to rock to snow.

## When to use it

Use it on generated terrains, sculpted mountains, islands and dioramas to get believable layering without painting masks. Set `snow_height` in world metres for your scene.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_terrain_slope_height.py`.
2. Enable "Baltor Terrain Slope Height Material".
3. Run it from View3D > Object > Terrain Slope Height Material (with the terrain active). The operator is `baltor.material_terrain_slope_height`; its redo panel shows every parameter listed below.

### As a script

```
blender --background land.blend --python material_terrain_slope_height.py -- --snow_height 6 --rock_slope 35 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file.

### From Python

The core needs no Blender:

```python
import material_terrain_slope_height
print(material_terrain_slope_height.layer_weights(1.0, 0.0))  # flat and low: grass
graph = material_terrain_slope_height.material_graph(snow_height=6.0)
```

Inside Blender, `material_terrain_slope_height.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

`fixture(bpy.context)` adds the 8 m demo hill named `Terrain Demo Hill` that the native check shades.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `material_name` | string | `Baltor Terrain Blend` | any | text | Name of the new material. |
| `grass_color` | vector | 0.07,0.16,0.035 | 0.0 to 1.0 | linear RGB | Colour of flat low ground. |
| `rock_color` | vector | 0.2,0.18,0.16 | 0.0 to 1.0 | linear RGB | Colour of steep ground. |
| `snow_color` | vector | 0.85,0.87,0.9 | 0.0 to 1.0 | linear RGB | Colour of high flat ground. |
| `rock_slope` | float | 32.0 | 1.0 to 89.0 | degree | Slope angle where ground turns from grass to rock. |
| `slope_blend` | float | 10.0 | 0.5 to 60.0 | degree | Width of the grass to rock transition. |
| `snow_height` | float | 2.2 | -10000.0 to 10000.0 | m | World height of the snow line. |
| `snow_blend` | float | 0.4 | 0.001 to 1000.0 | m | Height over which snow fades in. |
| `snow_max_slope` | float | 40.0 | 1.0 to 89.0 | degree | Steepest slope that holds snow. |
| `breakup` | float | 0.5 | 0.0 to 100.0 | m | How far noise moves the snow line up and down. |
| `assign` | bool | true | true or false | flag | Assign the material to the active object. |

## Outputs

A material named by `material_name` (default `Baltor Terrain Blend`) with 16 named nodes. When `assign` is true it replaces the material slots of the active object; otherwise it keeps a fake user. The core returns the tree as `trees[0]`.

With the default parameters the core returns 16 nodes, 20 links. The package tests pin these numbers.

## Limits

Three flat colours with roughness only; no texture detail per layer, no displacement and no erosion or flow information. World space inputs mean the blend changes when the object is rotated, by design. Shading normals from smooth shading soften the slope test on coarse meshes. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Slope from the Z component of the world normal (cosine of the slope angle)
- Snow line from world height shifted by noise
- Flatness mask to keep snow off cliffs

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
