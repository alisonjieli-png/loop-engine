# Three-point light rig with illuminance ratios

Adds the classic three-point lighting setup: a key light, a softer fill light on the other side and a rim light behind the subject. Each light is an area light placed by azimuth and elevation around a target point and rotated so its -Z axis points at the target. The fill and rim powers are computed from the key power and the illuminance ratios you ask for, corrected for each light's distance with the inverse square law.

## When to use it

Use it to light a product, a character bust or a turntable subject in a few seconds, or as a consistent starting point that you then tune by hand. A key to fill ratio of 2 gives soft, even light; 4 to 8 gives more contrast.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `light_three_point.py`.
2. Enable "Baltor Three Point Light Rig".
3. Run it from View3D > Add > Three Point Light Rig. The operator is `baltor.light_three_point`; its redo panel shows every parameter listed below.

### As a script

```
blender --background --python light_three_point.py -- --target 0,0,1.2 --key_power 800 --key_fill_ratio 4 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import light_three_point
rig = light_three_point.rig_layout(key_fill_ratio=4.0)
print(rig["report"]["powers_w"])
print(light_three_point.aim_rotation([0, -4, 1], [0, 0, 1]))  # [90.0, 0.0, 0.0]
```

Inside Blender, `light_three_point.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `target` | vector | 0.0,0.0,1.0 | -10000.0 to 10000.0 | m | Point the three lights aim at; the rig empty sits here. |
| `key_distance` | float | 4.0 | 0.1 to 1000.0 | m | Distance from the target to the key light. |
| `fill_distance` | float | 4.5 | 0.1 to 1000.0 | m | Distance from the target to the fill light. |
| `rim_distance` | float | 4.0 | 0.1 to 1000.0 | m | Distance from the target to the rim light. |
| `key_azimuth` | float | 40.0 | -180.0 to 180.0 | degree | Key light angle around Z; 0 is in front (-Y), positive toward +X. |
| `key_elevation` | float | 35.0 | -30.0 to 89.0 | degree | Key light angle above the target's horizontal plane. |
| `fill_azimuth` | float | -55.0 | -180.0 to 180.0 | degree | Fill light angle around Z. |
| `fill_elevation` | float | 12.0 | -30.0 to 89.0 | degree | Fill light angle above the horizontal plane. |
| `rim_azimuth` | float | 160.0 | -180.0 to 180.0 | degree | Rim light angle around Z; near 180 places it behind the subject. |
| `rim_elevation` | float | 45.0 | -30.0 to 89.0 | degree | Rim light angle above the horizontal plane. |
| `key_power` | float | 120.0 | 1.0 to 1000000.0 | W | Power of the key area light. |
| `key_fill_ratio` | float | 3.0 | 1.0 to 32.0 | ratio | Key illuminance divided by fill illuminance at the target. |
| `rim_ratio` | float | 1.0 | 0.0 to 8.0 | ratio | Rim illuminance relative to the key at the target. |
| `light_size` | float | 1.0 | 0.01 to 50.0 | m | Edge of the square key and fill area lights; the rim light is half this size. |
| `key_color` | vector | 1.0,0.92,0.82 | 0.0 to 1.0 | linear RGB | Key light colour. |
| `fill_color` | vector | 0.82,0.9,1.0 | 0.0 to 1.0 | linear RGB | Fill light colour. |
| `rim_color` | vector | 1.0,1.0,1.0 | 0.0 to 1.0 | linear RGB | Rim light colour. |

## Outputs

An empty named `Three Point Rig` at the target and three area lights named `Key Light`, `Fill Light` and `Rim Light`, parented to the empty and aimed at it with Track To constraints. The core returns `objects` (light locations relative to the empty, rotations in degrees, light type, power, size and colour) and a `report` with the powers in watts and the illuminance of each light relative to the key.

With the default parameters the core returns 4 objects. The package tests pin these numbers.

## Limits

Powers follow the inverse square law from each light's centre, which is approximate for area lights that are large compared with their distance. The ratios hold at the target point only. Colours are linear RGB values, not colour temperatures. The lights stay aimed by Track To constraints on the rig empty; glTF export keeps their positions but not the constraints. Verified in Blender 5.2.1 with Cycles; written for the 4.2 API.

## Technique

- Three-point lighting: key, fill and rim (back) light
- Inverse square law to hold illuminance ratios across distances
- Spherical coordinates for light placement
- Euler XYZ angles that point the -Z axis along a direction

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
