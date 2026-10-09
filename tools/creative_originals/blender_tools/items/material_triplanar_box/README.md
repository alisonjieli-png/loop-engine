# Triplanar box-projected image material

Creates a material that textures a mesh with no UV map. Object coordinates divided by the texture size go into an Image Texture node in box projection, which samples the image along X, Y and Z and blends the three by the surface normal with a soft blend zone. The texture keeps the same size in metres on every part of the object. With no image path the tool generates a UV grid image so the projection and blend seams can be judged first.

## When to use it

Use it on photogrammetry scans, sculpts, remeshed or boolean-heavy models, kitbash parts and level blockouts, where UV unwrapping is slow or impossible, and as a quick check of texture scale in metres.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_triplanar_box.py`.
2. Enable "Baltor Triplanar Box Material".
3. Run it from View3D > Object > Triplanar Box Material (with an object active). The operator is `baltor.material_triplanar_box`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python material_triplanar_box.py -- --texture_size 0.5 --blend 0.3 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file.

### From Python

The core needs no Blender:

```python
import material_triplanar_box
graph = material_triplanar_box.material_graph(texture_size=0.5)
print(graph["images"][0])
print(material_triplanar_box.repeats(3.0, texture_size=0.5))  # 6.0
```

Inside Blender, `material_triplanar_box.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `material_name` | string | `Baltor Triplanar` | any | text | Name of the new material. |
| `image_path` | string | empty | any | path | Image file to project; empty generates a UV grid image. |
| `texture_size` | float | 1.0 | 0.001 to 10000.0 | m | World size of one repeat of the image. |
| `blend` | float | 0.25 | 0.0 to 1.0 | ratio | Width of the soft blend between the three projections. |
| `grid_resolution` | int | 512 | 16 to 4096 | px | Side of the generated grid image when no path is given. |
| `roughness` | float | 0.5 | 0.0 to 1.0 | ratio | Roughness of the surface. |
| `assign` | bool | true | true or false | flag | Assign the material to the active object. |

## Outputs

A material named by `material_name` (default `Baltor Triplanar`) with 5 named nodes and, without a path, a generated image `Baltor Triplanar Grid`. When `assign` is true it replaces the material slots of the active object; otherwise it keeps a fake user. The core returns the tree and the image it needs.

With the default parameters the core returns 5 nodes, 4 links. The package tests pin these numbers.

## Limits

Box projection follows object axes, so rotating the object rotates the projection with it and curved surfaces show stretching in the blend zones. Normal maps are not projected; this is a colour texture tool. The generated grid is for judging scale and seams, not final look. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Box (triplanar) projection of an image along the three object axes
- Texture size in metres by scaling object coordinates
- Generated UV grid image

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
