# Picket fence along a path

Builds a picket fence along a path of ground points. Each segment of the path gets posts at both ends and as many intermediate posts as keep every bay at or under the post spacing. Two rails per bay follow the slope of the ground on the front side of the posts, and pickets are spaced evenly along the bay in front of the rails, with the gap adjusted so each bay is filled. Picket tops can be pointed, flat, round or dog-eared.

## When to use it

Use it to fence gardens, yards, paddocks and paths in renders and games. Give the corner points of the fence line, including heights when the ground slopes.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `picket_fence.py`.
2. Enable "Baltor Picket Fence".
3. Run it from View3D > Add > Mesh > Picket Fence. The operator is `baltor.picket_fence`; its redo panel shows every parameter listed below.

### As a script

```
blender --background --python picket_fence.py -- --points "0,0,0; 6,0,0; 6,4,0.5" --top round --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import picket_fence
fence = picket_fence.build_geometry(points="0,0,0; 6,0,0", top="dog_ear")
print(fence["report"])  # posts, rails, pickets, path length
```

Inside Blender, `picket_fence.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `points` | string | `0,0,0; 4,0,0; 4,3,0.3` | any | m | Ground path as x,y,z points separated by semicolons. |
| `height` | float | 1.0 | 0.2 to 5.0 | m | Height of the pickets above the ground. |
| `post_spacing` | float | 2.0 | 0.5 to 10.0 | m | Largest distance between neighbouring posts. |
| `post_size` | float | 0.09 | 0.02 to 0.5 | m | Side of the square posts. |
| `picket_width` | float | 0.075 | 0.01 to 0.5 | m | Width of each picket. |
| `picket_gap` | float | 0.05 | 0.005 to 0.5 | m | Target gap between pickets; the actual gap is adjusted to fill each bay evenly. |
| `picket_thickness` | float | 0.02 | 0.005 to 0.2 | m | Thickness of each picket. |
| `top` | choice | `pointed` | `pointed`, `flat`, `round`, `dog_ear` | style | Shape of the picket tops. |

## Outputs

One mesh object named `Picket Fence` with the material slots `Baltor Fence Post`, `Baltor Fence Rail` and `Baltor Fence Picket`, in path coordinates relative to the 3D cursor. The core returns `vertices`, `faces`, `face_materials` and a `report` with the numbers of posts, rails and pickets and the path length.

With the default parameters the core returns 629 vertices, 457 faces. The package tests pin these numbers.

## Limits

Pickets stay vertical and their bottoms step along a straight ground line between path points; uneven terrain between points is not followed. No gates, diagonal braces or rail joinery. Every part is a separate closed solid that touches its neighbours. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Even subdivision of path segments into bays no longer than a maximum
- Even redistribution of the remaining gap between pickets
- Closed hexahedra from three edge vectors with a positive triple product

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
