# Bounce animation with exact parabolic arcs

Keys a bounce on the active object. The timing comes from free fall: the first drop takes sqrt(2h/g) seconds, every rebound reaches the previous height times the restitution squared, and each flight lasts 2 * sqrt(2h/g). Every arc between an apex and a contact is a single Bezier segment with handles a third of the way along, which is an exact parabola in time, so the object accelerates like a dropped ball without extra keys. The object travels along +X at a constant speed, and optional squash keys flatten it at each contact.

## When to use it

Use it for bouncing balls, dropped props, motion tests and timing reference, or as the base motion that you then refine by hand in the Graph Editor.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `anim_bounce.py`.
2. Enable "Baltor Bounce Animation".
3. Run it from View3D > Object > Bounce Animation (with the object to animate active). The operator is `baltor.anim_bounce`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python anim_bounce.py -- --drop_height 3 --restitution 0.7 --bounces 8 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the active object of the opened file is animated. The operator reads the frame rate and start frame from the scene; in script mode pass `--fps` and `--start_frame` if the defaults do not match.

### From Python

The core needs no Blender:

```python
import anim_bounce
result = anim_bounce.keyframes(drop_height=3.0, restitution=0.7)
height = result["channels"][0]
print(result["report"]["contacts"], anim_bounce.evaluate(height, 10.0))
```

Inside Blender, `anim_bounce.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

`fixture(bpy.context)` adds the 0.25 m demo ball named `Bounce Ball` that the native check animates.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `drop_height` | float | 2.0 | 0.01 to 1000.0 | m | Height of the object's lowest point above the ground at the first apex. |
| `ground_z` | float | 0.0 | -10000.0 to 10000.0 | m | Height of the ground plane. |
| `radius` | float | 0.25 | 0.001 to 1000.0 | m | Distance from the object origin down to its lowest point; measured when measure_radius. |
| `measure_radius` | bool | true | true or false | flag | Measure the radius from the active object's bounding box instead of using radius. |
| `restitution` | float | 0.65 | 0.05 to 0.95 | ratio | Rebound speed divided by impact speed. |
| `gravity` | float | 9.81 | 0.1 to 100.0 | m/s^2 | Gravitational acceleration. |
| `fps` | float | 24.0 | 1.0 to 240.0 | frame/s | Frames per second; the operator fills it from the scene. |
| `start_frame` | int | 1 | -100000 to 100000 | frame | Frame of the first apex. |
| `bounces` | int | 6 | 1 to 60 | count | Most rebounds to key after the first contact. |
| `min_height` | float | 0.02 | 0.0001 to 10.0 | m | Stop when a rebound apex would be lower than this. |
| `travel_speed` | float | 0.8 | 0.0 to 100.0 | m/s | Constant horizontal speed along +X. |
| `squash` | float | 0.15 | 0.0 to 0.6 | ratio | Vertical squash at the first contact, scaled down with impact speed for later contacts. |

## Outputs

Keyframes on the active object: `location[2]` with free Bezier handles (apex and contact keys), `location[0]` with two linear keys, and `scale[0..2]` keys around each contact when `squash` is above zero. The scene end frame grows to the last contact when needed. The core returns the same channels with their handles and a `report` with the number of contacts, the duration and the apex heights.

With the default parameters the core returns 5 channels, 35 keys. The package tests pin these numbers.

## Limits

Point-mass free fall with a constant restitution: no air drag, spin, rolling or deformation physics. The squash is a stylized scale key at each contact, scaled with impact speed, and it lowers the contact key by radius times squash so the object stays on the ground. Motion is along +X on a flat ground only. Keys sit on fractional frames. Verified in Blender 5.2.1, where F-curves live in the action's channel bag; the 4.2 code path uses action.fcurves and was not run.

## Technique

- Free fall: t = sqrt(2 h / g), apex height times restitution squared per bounce
- Degree elevation of a quadratic Bezier to a cubic: handles at one third of the span
- Cubic Bezier F-curve evaluation by solving for the curve parameter
- Volume-preserving squash: scale z by 1 - s and x, y by 1 / sqrt(1 - s)

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
