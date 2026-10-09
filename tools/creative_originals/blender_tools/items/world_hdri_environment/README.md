# HDRI environment world with a solid camera backdrop

Builds a world lit by an equirectangular image. The world direction is rotated about Z and looks up the image in an Environment Texture; saturation and strength can be adjusted. In solid backdrop mode a Light Path node gives camera rays a plain colour, so the image keeps lighting the scene and showing in reflections while the background stays clean.

## When to use it

Use it to light products, characters and look development scenes with a captured environment, to turn the environment until reflections sit well, or to keep a studio-clean backdrop while lighting from an outdoor capture.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `world_hdri_environment.py`.
2. Enable "Baltor HDRI Environment".
3. Run it from View3D > Add > HDRI Environment. The operator is `baltor.world_hdri_environment`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python world_hdri_environment.py -- --image_path //sky.exr --rotation 90 --backdrop solid --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import world_hdri_environment
graph = world_hdri_environment.world_graph(image_path="//sky.exr", backdrop="solid")
print(world_hdri_environment.equirect_pixel([1.0, 0.0, 0.0], 2048, 1024))  # centre column
```

Inside Blender, `world_hdri_environment.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

`fixture(bpy.context)` writes a 128 by 64 demo sky to `//textures/baltor_sky_demo.png` and adds a chrome test sphere.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `image_path` | string | `//textures/baltor_sky_demo.png` | any | path | Equirectangular image (.hdr, .exr, .png, .jpg); // is relative to the .blend. |
| `rotation` | float | 0.0 | -360.0 to 360.0 | degree | Rotation of the environment about Z. |
| `strength` | float | 1.0 | 0.0 to 1000.0 | ratio | Strength of the environment light. |
| `saturation` | float | 1.0 | 0.0 to 2.0 | ratio | Saturation of the image; 1 leaves it unchanged. |
| `backdrop` | choice | `image` | `image`, `solid` | mode | What camera rays see: the image or a solid colour. |
| `backdrop_color` | vector | 0.05,0.05,0.055 | 0.0 to 1.0 | linear RGB | Colour the camera sees in solid backdrop mode. |

## Outputs

A world named `Baltor HDRI` set as the scene world, with the image loaded into its Environment Texture node. The core returns the world tree and the image path it needs.

With the default parameters the core returns 6 nodes, 5 links. The package tests pin these numbers.

## Limits

Needs an image file; the demo fixture writes a small 8-bit PNG sky, which lights only roughly because it holds no high dynamic range. No ground projection, sun extraction or importance map tuning. The solid backdrop uses the Light Path node, which Cycles honours fully and EEVEE only partly. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Equirectangular environment lookup with a Z rotation
- Light Path camera ray mask to separate backdrop from lighting
- Hue Saturation adjustment of an environment

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process.
