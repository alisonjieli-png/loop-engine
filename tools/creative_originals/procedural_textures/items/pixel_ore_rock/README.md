# Pixel-art rock with ore nuggets and gems

Grey stone with gold, brown stone flecked with iron, dark cave stone with cyan gems or warm stone with copper and green patina, drawn on a small art grid (`art_pixels` square) and enlarged with nearest-neighbour sampling. The rock is a Voronoi diagram: each cell is a stone chunk with its own shade, cell borders are one-pixel crevices, and chunk pixels beside a crevice on their upper or left side take the light colour while those beside one on their lower or right side take the shadow colour.

Ore clusters sit at Poisson-disc points spread evenly over the torus, and `ore` sets the share that hold ore. Each cluster is `nuggets` small sprites with a highlight pixel at the top left and a shadow pixel at the bottom right; gem ores add a white glint. Metal ores are metallic in the metallic map and gems are smooth dielectrics. Cracks are short random walks inside chunks.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `pixel_ore_rock_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.98 |
| `normal` | `pixel_ore_rock_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `pixel_ore_rock_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.1 to 1 |
| `metallic` | `pixel_ore_rock_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `pixel_ore_rock_height.png` | 1 | linear | white is high |
| `ao` | `pixel_ore_rock_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Grey stone with gold nuggets.
- `iron_ore`: Brown-grey stone with many rusty iron flecks.
- `diamond_gems`: Dark deep-cave stone with a few bright cyan gems.
- `copper_patina`: Warm stone with copper nuggets spotted with green patina.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `art_pixels` | int | 32 | 16 to 64 | Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling. |
| `chunks` | int | 5 | 2 to 10 | Stone chunks across the tile. |
| `ore` | float | 0.5 | 0 to 1 | Share of the evenly spread cluster positions that hold ore. |
| `nuggets` | int | 3 | 1 to 5 | Nuggets or gems in each ore cluster. |
| `cracks` | float | 0.3 | 0 to 1 | Share of chunks with a crack. |
| `relief` | float | 1 | 0.2 to 2 | Strength of the per-pixel normal map. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`pixel_ore_rock.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python pixel_ore_rock.py --size 1024 --seed 7 --preset iron_ore --out textures/pixel_ore_rock
python pixel_ore_rock.py --width 512 --height 256 --set art_pixels=64 --orm --out maps
```

`--orm` also writes `pixel_ore_rock_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import pixel_ore_rock

maps = pixel_ore_rock.generate(512, 512, seed=3, preset="iron_ore")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 9.1 s (0.9 s to compute, 8.2 s to write the PNG files) with a peak of about 96 MB; 256 x 256 takes about 0.64 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/pixel_ore_rock/` of your project (for example `python pixel_ore_rock.py --size 1024 --out path/to/project/baltor/textures/pixel_ore_rock`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Texture filtering is nearest with mipmaps, which keeps pixel edges sharp.

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

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap`.

For Godot 2D, load the albedo and normal PNGs into a CanvasTexture (diffuse and normal textures) and set the texture filter to nearest; `material.tres` is a StandardMaterial3D for putting the tile on 3D surfaces, where the metallic map makes the nuggets shine. Choose an output size that is a whole multiple of `art_pixels` (for example `--size 256` with 32 art pixels) so every art pixel covers the same number of output pixels; `--size 32` writes one output pixel per art pixel.

## Limits

Stylized pixel art with the light from the top left baked into the chunk edges and nugget sprites; it is not a geological model, and ore colours are artistic. Chunks are Voronoi cells and nuggets are four or five-pixel sprites, so a 16-pixel grid shows two-by-two nuggets only. Gems are smooth dielectrics and metal ores fully metallic, with nothing in between. The normal map treats each art pixel as a flat facet. Output sizes that are not a whole multiple of art_pixels give art pixels of unequal widths. Occlusion is a blurred-height estimate posterized to eighths.
