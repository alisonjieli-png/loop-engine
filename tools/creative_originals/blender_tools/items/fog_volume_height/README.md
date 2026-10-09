# Height fog volume with exponential falloff

Adds a box filled with fog that is densest at the bottom and thins with height. The density at a world height z is d0 * exp(-(z - base) / h): d0 at the box base, falling to about 37 percent every h metres up, multiplied by a noise term so the fog drifts in patches. A Principled Volume scatters light with the chosen colour and anisotropy. The box displays only its bounds in the viewport so it does not hide the scene.

## When to use it

Use it for mist over water and fields, fog pooling in valleys and streets, dusty halls and dungeons, and any scene that needs light shafts or depth from the atmosphere.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `fog_volume_height.py`.
2. Enable "Baltor Height Fog Volume".
3. Run it from View3D > Add > Height Fog Volume. The operator is `baltor.fog_volume_height`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python fog_volume_height.py -- --density 0.3 --falloff 2 --size 30,30,8 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import fog_volume_height
print(fog_volume_height.density_at(1.2))  # density one falloff height up
box = fog_volume_height.build_geometry(size=[30, 30, 8])
```

Inside Blender, `fog_volume_height.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `size` | vector | 6.0,6.0,3.0 | 0.01 to 100000.0 | m | Width, depth and height of the fog box. |
| `density` | float | 0.25 | 0.0 to 1000.0 | 1/m | Fog density at the bottom of the box. |
| `falloff` | float | 1.2 | 0.001 to 100000.0 | m | Height over which the density falls to 1 / e (about 37 percent). |
| `breakup` | float | 0.6 | 0.0 to 1.0 | ratio | How much noise varies the density, as a share of it. |
| `noise_scale` | float | 0.35 | 0.001 to 1000.0 | 1/m | Frequency of the noise patches. |
| `color` | vector | 0.85,0.88,0.92 | 0.0 to 1.0 | linear RGB | Scattering colour of the fog. |
| `anisotropy` | float | 0.3 | -0.95 to 0.95 | ratio | Forward (positive) or backward (negative) scattering. |

## Outputs

A mesh object named `Height Fog` (a closed box with its base at the 3D cursor) using the volume material `Baltor Height Fog`, displayed as bounds. The core returns the box, the material tree and a `report` with the density at the base and top and a rough visibility distance.

With the default parameters the core returns 8 vertices, 6 faces, 13 nodes, 13 links. The package tests pin these numbers.

## Limits

Volumetric rendering is slow and noisy at low sample counts; EEVEE renders volumes with its own approximations. The fog fills only its box, so its edges show if the box is smaller than the view. Density follows the box's own base height from its origin, not the scene floor. The visibility in the report is the rough 3 / density rule for a dense medium. Verified in Blender 5.2.1 with Cycles CPU; written for the 4.2 API.

## Technique

- Exponential height fog d0 exp(-(z - base) / h)
- Principled Volume with Henyey-Greenstein anisotropy
- Noise breakup of density

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
