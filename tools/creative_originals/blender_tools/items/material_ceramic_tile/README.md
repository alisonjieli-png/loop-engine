# Glazed ceramic tile material with bevelled edges

Creates a ceramic tile material entirely from math nodes. Object coordinates in the chosen plane are divided by the tile size; the floor of that gives each tile an integer index that drives a white noise, so every tile picks its own mix of two glaze colours, and the fractional part gives the distance to the nearest tile edge. A map range turns that distance into a mask that is 0 in the grout and rises across the bevel; the mask blends grout and glaze colour and roughness and drives a bump, so the tiles look raised with rounded edges.

## When to use it

Use it for kitchen and bathroom walls, shower floors, pools, metro-style walls and any surface tiled in a square grid. Set the tile size to the tile plus one grout line.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_ceramic_tile.py`.
2. Enable "Baltor Ceramic Tile Material".
3. Run it from View3D > Object > Ceramic Tile Material (with an object active). The operator is `baltor.material_ceramic_tile`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python material_ceramic_tile.py -- --tile_size 0.1 --orientation wall_xz --grout_width 0.003 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file.

### From Python

The core needs no Blender:

```python
import material_ceramic_tile
graph = material_ceramic_tile.material_graph(tile_size=0.1)
print(material_ceramic_tile.edge_mask(0.05, 0.05, tile_size=0.1))  # 1.0 at a tile centre
```

Inside Blender, `material_ceramic_tile.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `material_name` | string | `Baltor Ceramic Tile` | any | text | Name of the new material. |
| `orientation` | choice | `floor_xy` | `floor_xy`, `wall_xz`, `wall_yz` | plane | Plane the tiles lie in. |
| `tile_size` | float | 0.2 | 0.005 to 10.0 | m | Tile pitch: tile plus one grout line. |
| `grout_width` | float | 0.004 | 0.0 to 0.1 | m | Width of the grout lines. |
| `bevel` | float | 0.006 | 0.0001 to 0.2 | m | Width of the rounded tile edge. |
| `glaze_a` | vector | 0.05,0.22,0.32 | 0.0 to 1.0 | linear RGB | First glaze colour. |
| `glaze_b` | vector | 0.08,0.3,0.38 | 0.0 to 1.0 | linear RGB | Second glaze colour; each tile picks a mix. |
| `grout_color` | vector | 0.6,0.6,0.58 | 0.0 to 1.0 | linear RGB | Grout colour. |
| `glaze_roughness` | float | 0.06 | 0.0 to 1.0 | ratio | Roughness of the glaze. |
| `assign` | bool | true | true or false | flag | Assign the material to the active object. |

## Outputs

A material named by `material_name` (default `Baltor Ceramic Tile`) with 19 named nodes. When `assign` is true it replaces the material slots of the active object; otherwise it keeps a fake user. The core returns the tree as `trees[0]`.

With the default parameters the core returns 19 nodes, 24 links. The package tests pin these numbers.

## Limits

Square grid tiles only; no offset, herringbone or hexagonal layouts (see the tiled floor generator for geometry layouts). The bevel is a bump effect, not geometry. Colour variation is a mix of two glaze colours per tile, not crackle or pooling. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Cell index by floor and in-cell position by fraction of scaled coordinates
- Distance to the nearest square edge: 0.5 - max(|x - 0.5|, |y - 0.5|)
- Per-cell random values from white noise of the cell index

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
