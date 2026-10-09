# Pixel-art sci-fi hull panels with glowing lights

Grey space-station plating, white laboratory panels, rusty industrial plating with hazard stripes or a violet alien hull, drawn on a small art grid (`art_pixels` square) and enlarged with nearest-neighbour sampling. The tile is one module: a grid of `panels` by `panels` cells, each split once or twice more at random into smaller plates, so the module mixes large and small plates and repeats cleanly at the tile edges.

Every plate owns the seam on its top and left edge, its next row and column are a lit bevel and its last row and column a shadow bevel. Each plate then gets one detail: a plain face with corner rivets, vent slits, a grille of holes, a glowing light strip, indicator lamps or diagonal hazard stripes, chosen by `lights`, `vents` and `hazard`. Plates are metallic in the metallic map; lamps are glass and appear in the emissive map.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `pixel_scifi_panel_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.98 |
| `normal` | `pixel_scifi_panel_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `pixel_scifi_panel_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.1 to 1 |
| `metallic` | `pixel_scifi_panel_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `pixel_scifi_panel_height.png` | 1 | linear | white is high |
| `ao` | `pixel_scifi_panel_ao.png` | 1 | linear | white is unoccluded |
| `emissive` | `pixel_scifi_panel_emissive.png` | 3 | sRGB | glTF emissive colour |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Grey space-station plating with cyan light strips.
- `clean_lab`: White laboratory panels with blue lights and few vents.
- `rusty_industrial`: Dark brown industrial plating with amber lights and hazard stripes.
- `alien_hull`: Violet-black alien hull with green glowing seams of light.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `art_pixels` | int | 32 | 16 to 64 | Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling. |
| `panels` | int | 2 | 1 to 4 | Main panel cells across the tile before subdivision. |
| `subdivision` | float | 0.6 | 0 to 1 | Chance that a panel is split into smaller plates. |
| `lights` | float | 0.35 | 0 to 1 | Share of plates carrying a light strip or indicator lights. |
| `vents` | float | 0.3 | 0 to 1 | Share of plates carrying vent slits or a grille. |
| `hazard` | float | 0 | 0 to 1 | Share of plates painted with diagonal hazard stripes. |
| `rivets` | int | 1 | 0 to 1 | 1 puts rivets in the corners of plain plates. |
| `relief` | float | 1 | 0.2 to 2 | Strength of the per-pixel normal map. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo and the lights in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`pixel_scifi_panel.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python pixel_scifi_panel.py --size 1024 --seed 7 --preset clean_lab --out textures/pixel_scifi_panel
python pixel_scifi_panel.py --width 512 --height 256 --set art_pixels=64 --orm --out maps
```

`--orm` also writes `pixel_scifi_panel_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import pixel_scifi_panel

maps = pixel_scifi_panel.generate(512, 512, seed=3, preset="clean_lab")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 13.4 s (1.8 s to compute, 11.6 s to write the PNG files) with a peak of about 122 MB; 256 x 256 takes about 0.7 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/pixel_scifi_panel/` of your project (for example `python pixel_scifi_panel.py --size 1024 --out path/to/project/baltor/textures/pixel_scifi_panel`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion, emission and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Texture filtering is nearest with mipmaps, which keeps pixel edges sharp.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo and emission are decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.005, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo and emissive with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap` and `emissiveMap`.

For Godot 2D, load the albedo and normal PNGs into a CanvasTexture (diffuse and normal textures) and set the texture filter to nearest; the emissive PNG can drive a glow layer. `material.tres` is a StandardMaterial3D for putting the tile on 3D surfaces, where the metallic map makes the plates shine. Choose an output size that is a whole multiple of `art_pixels` (for example `--size 256` with 32 art pixels); `--size 32` writes one output pixel per art pixel.

## Limits

Stylized pixel art with the light from the top left baked into the plate bevels. The module repeats on a regular panel grid aligned with the tile edges, which suits modular plating but shows the grid on large areas. Plates are rectangles split at most twice; details are fixed small patterns, and lights do not animate. Metal and glass take fixed roughness values per class. The normal map treats each art pixel as a flat facet. Output sizes that are not a whole multiple of art_pixels give art pixels of unequal widths. Occlusion is a blurred-height estimate posterized to eighths.
