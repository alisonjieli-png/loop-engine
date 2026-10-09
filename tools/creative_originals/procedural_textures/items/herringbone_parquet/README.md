# Herringbone and chevron parquet floor

Oak herringbone, double herringbone in walnut, a pale ash chevron or a smoked, oiled rustic floor. `pattern` picks herringbone or chevron, `ratio` the block length in widths, `planks` how many planks share a block (2 gives double herringbone) and `repeats` how often the pattern repeats across the tile.

Herringbone is computed in an axis-aligned frame where a point lies in a horizontal block when (x - floor(y)) mod 2 ratio is below the ratio, then turned 45 degrees so both periods of the pattern land exactly on the square tile. Chevron boards are parallelograms in columns whose slope alternates, so they meet in V shapes. Every plank has its own grain: ring lines that wander and bend into arches, finer rings and pore streaks, all running along the plank's axis. Joints are bevelled V grooves, `gloss` sets the finish and `wear` dulls patches of it.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `herringbone_parquet_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.9 |
| `normal` | `herringbone_parquet_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `herringbone_parquet_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.12 to 1 |
| `height` | `herringbone_parquet_height.png` | 1 | linear | white is high |
| `ao` | `herringbone_parquet_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Natural oak blocks in classic herringbone with a satin lacquer.
- `double_walnut`: Dark walnut in double herringbone: pairs of narrow planks per block.
- `chevron_ash`: Pale ash chevron with long boards meeting in a straight centre line.
- `smoked_rustic`: Smoked, oiled oak herringbone with wide bevels, strong grain and wear.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `pattern` | int | 0 | 0 to 1 | 0 herringbone (square block ends against the next block's side), 1 chevron (ends cut at 45 degrees so the blocks meet in a straight centre line). |
| `ratio` | int | 5 | 2 to 8 | Block length in block widths; chevron uses the nearest even number. |
| `planks` | int | 1 | 1 to 3 | Planks laid side by side in each block: 1 single, 2 double, 3 triple herringbone or chevron. |
| `repeats` | int | 2 | 1 to 4 | Times the pattern repeats across the tile; more repeats make smaller blocks. |
| `joint_width` | float | 0.025 | 0 to 0.1 | Gap between planks in plank widths. |
| `bevel` | float | 0.04 | 0 to 0.2 | Width of the bevelled plank edge (a V groove between planks) in plank widths. |
| `grain_contrast` | float | 0.5 | 0 to 1 | Strength of the ring lines and pore streaks. |
| `figure` | float | 0.4 | 0 to 1 | Waviness of the grain lines along each plank. |
| `colour_variation` | float | 0.5 | 0 to 1 | Spread of tone between planks. |
| `gloss` | float | 0.6 | 0 to 1 | Finish: 0 matte oil, 1 glossy lacquer. |
| `wear` | float | 0.15 | 0 to 1 | Dull, lighter patches where the finish has worn. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`herringbone_parquet.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python herringbone_parquet.py --size 1024 --seed 7 --preset double_walnut --out textures/herringbone_parquet
python herringbone_parquet.py --width 512 --height 256 --set pattern=1 --orm --out maps
```

`--orm` also writes `herringbone_parquet_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import herringbone_parquet

maps = herringbone_parquet.generate(512, 512, seed=3, preset="double_walnut")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 42.9 s (31 s to compute, 11.9 s to write the PNG files) with a peak of about 518 MB; 256 x 256 takes about 2.87 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/herringbone_parquet/` of your project (for example `python herringbone_parquet.py --size 1024 --out path/to/project/baltor/textures/herringbone_parquet`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.005, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

The zigzag always runs along the tile height at 45 degrees; other angles need a rotated UV. Grain is a geometric ring model (wavy lines bent into arches, finer rings and pore streaks), not wood anatomy: there are no knots, ray fleck or end grain. Blocks are flat with a slight tilt; there is no cupping, gapping by season or borders. At small output sizes the joints are thinner than a pixel and fade into the albedo. Occlusion is a blurred-height estimate, not ray traced.
