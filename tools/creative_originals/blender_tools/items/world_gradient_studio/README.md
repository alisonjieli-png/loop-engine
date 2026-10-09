# Studio gradient world with a horizon band

Builds a world that is a smooth gradient: a ground colour below, a horizon band and a zenith colour above. The Z component of the world direction is the sine of the elevation; it is mapped to 0 to 1 and fed to a colour ramp whose stops sit at the horizon height minus and plus the softness. A second strength for camera rays lets the backdrop look brighter or darker than the light it casts.

## When to use it

Use it for product and character turntables, clean presentation renders, stylized skies and as a neutral lighting base that is quick to tune.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `world_gradient_studio.py`.
2. Enable "Baltor Gradient Studio World".
3. Run it from View3D > Add > Gradient Studio World. The operator is `baltor.world_gradient_studio`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python world_gradient_studio.py -- --zenith_color 0.1,0.15,0.3 --horizon_height 5 --softness 20 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import world_gradient_studio
print(world_gradient_studio.ramp_positions(0.0, 30.0))  # (0.25, 0.5, 0.75)
graph = world_gradient_studio.world_graph(softness=30.0)
```

Inside Blender, `world_gradient_studio.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `ground_color` | vector | 0.06,0.055,0.05 | 0.0 to 1.0 | linear RGB | Colour below the horizon. |
| `horizon_color` | vector | 0.55,0.55,0.58 | 0.0 to 1.0 | linear RGB | Colour of the horizon band. |
| `zenith_color` | vector | 0.12,0.16,0.28 | 0.0 to 1.0 | linear RGB | Colour straight up. |
| `horizon_height` | float | 0.0 | -60.0 to 60.0 | degree | Elevation of the horizon band. |
| `softness` | float | 12.0 | 0.5 to 90.0 | degree | Half the height of the horizon band. |
| `strength` | float | 1.0 | 0.0 to 100.0 | ratio | Strength of the light the world casts. |
| `camera_strength` | float | 1.0 | 0.0 to 100.0 | ratio | Strength of the backdrop as the camera sees it. |

## Outputs

A world named `Baltor Gradient Studio` set as the scene world. The core returns the world tree.

With the default parameters the core returns 8 nodes, 7 links. The package tests pin these numbers.

## Limits

A smooth three-colour gradient: no sun, clouds or image detail, so it gives soft light without shadows from a direction. The camera strength uses the Light Path node, which EEVEE honours only partly. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Elevation from the Z component of the world direction
- Colour ramp with stops at sin(elevation) positions
- Light Path camera ray mix for a separate backdrop strength

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
