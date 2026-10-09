# Physical sky with a matching sun lamp

Builds a physical sky world and a sun lamp that agree. You give the sun's elevation and its compass bearing, clockwise from +Y, which is how the Sky Texture's sun rotation turns. The core computes the sun direction and the lamp rotation (90 - elevation, 0, 180 - bearing) that makes the lamp shine from that direction. The sky's own sun disc is off by default, so the lamp alone gives the direct sunlight and crisp shadows while the sky gives ambient light.

## When to use it

Use it for exteriors, architectural renders, landscapes and time-of-day studies, whenever the sun in the sky and the shadows on the ground must line up. Low elevations give long warm shadows; set the bearing from the real orientation of the site.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `world_sky_sun.py`.
2. Enable "Baltor Sky And Matching Sun".
3. Run it from View3D > Add > Sky And Matching Sun. The operator is `baltor.world_sky_sun`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python world_sky_sun.py -- --elevation 12 --azimuth 250 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import world_sky_sun
setup = world_sky_sun.sky_setup(elevation=12.0, azimuth=250.0)
print(setup["report"]["sun_direction"])
print(world_sky_sun.lamp_rotation(12.0, 250.0))  # [78.0, 0.0, 290.0]
```

Inside Blender, `world_sky_sun.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `elevation` | float | 28.0 | -10.0 to 90.0 | degree | Sun height above the horizon. |
| `azimuth` | float | 135.0 | 0.0 to 360.0 | degree | Compass bearing of the sun, clockwise from +Y (0 is +Y, 90 is +X). |
| `sun_strength` | float | 2.2 | 0.0 to 1000.0 | W/m^2 | Irradiance of the sun lamp. |
| `sun_angle` | float | 0.545 | 0.0 to 30.0 | degree | Angular diameter of the sun lamp; larger values soften shadows. |
| `world_strength` | float | 0.12 | 0.0 to 100.0 | ratio | Strength of the sky background. |
| `sky_sun_disc` | bool | false | true or false | flag | Also draw the sun disc in the sky texture (it then lights the scene as well). |
| `air_density` | float | 1.0 | 0.0 to 10.0 | ratio | Air density of the sky model. |
| `haze` | float | 1.0 | 0.0 to 10.0 | ratio | Dust or aerosol density of the sky model. |

## Outputs

A world named `Baltor Sky` set as the scene world, and a sun lamp named `Baltor Sky Sun` (reused when it exists) with the chosen strength and angle. The core returns the world tree, the lamp description and a `report` with the sun direction and the direction the light travels.

With the default parameters the core returns 3 nodes, 2 links, 1 objects. The package tests pin these numbers.

## Limits

The bearing convention (clockwise from +Y, as the Sky Texture sun rotation) was measured on Blender 5.2.1 only. Uses the multiple scattering sky where Blender offers it and the Nishita sky otherwise; their colours differ. Lamp strength is a free parameter, not derived from the sky model, so sky and sun brightness are balanced by eye. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Sun direction from elevation and bearing on the unit sphere
- Light rotation that points a lamp's -Z axis along a direction
- Equirectangular panorama render used to measure the sky's sun convention

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
