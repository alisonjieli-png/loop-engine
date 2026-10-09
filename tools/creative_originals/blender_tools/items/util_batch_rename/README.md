# Batch rename objects by rule

Renames the selected objects, or every object, by a fixed sequence of rules: strip Blender's `.001` style suffix, find and replace (plain text or a regular expression), split the name into words and apply a case style, add a prefix and a suffix, and number names. With the default `duplicates` numbering only names that would collide get a number, so `Cube`, `Cube.001` and `Cube.002` become `SM_cube_01` to `SM_cube_03` while `Sphere` becomes `SM_sphere`. The plan is computed first, without Blender, and never collides with names outside the batch.

## When to use it

Use it before exporting to a game engine or handing a file to another team, to apply a naming convention such as `SM_` for static meshes, or to clean the `.001` suffixes that duplication leaves behind.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `util_batch_rename.py`.
2. Enable "Baltor Batch Rename".
3. Run it from View3D > Object > Batch Rename by Rule. The operator is `baltor.util_batch_rename`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python util_batch_rename.py -- --prefix SM_ --case snake --numbering duplicates --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the selection saved in the file decides what is renamed unless `--scope all` is given. The plan is printed as one JSON line.

### From Python

The core needs no Blender:

```python
import util_batch_rename
plan = util_batch_rename.plan_renames(["Cube", "Cube.001", "Lamp Post"])
print(plan["report"]["renames"])
# [['Cube', 'SM_cube_01'], ['Cube.001', 'SM_cube_02'], ['Lamp Post', 'SM_lamp_post']]
```

Inside Blender, `util_batch_rename.run(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

`run(bpy.context, ...)` applies the plan and returns it. `fixture(bpy.context)` adds the seven demo objects that the native check renames.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `prefix` | string | `SM_` | any | text | Text put in front of every name (not repeated when already present). |
| `suffix` | string | empty | any | text | Text put after every name, before any number. |
| `find` | string | empty | any | text | Text or regular expression to replace; empty skips this step. |
| `replace` | string | empty | any | text | Replacement for find; with use_regex it may use groups such as \1. |
| `use_regex` | bool | false | true or false | flag | Treat find as a Python regular expression. |
| `case` | choice | `snake` | `keep`, `lower`, `upper`, `snake`, `pascal` | style | Case style applied to the words of the name. |
| `strip_duplicate_suffix` | bool | true | true or false | flag | Remove Blender's .001 style suffix first. |
| `numbering` | choice | `duplicates` | `none`, `duplicates`, `always` | mode | Number every name, only names that would collide, or none. |
| `start` | int | 1 | 0 to 100000 | count | First number of a numbered group. |
| `padding` | int | 2 | 1 to 6 | digits | Digits of each number, padded with zeros. |
| `separator` | string | `_` | any | text | Text between a name and its number. |
| `scope` | choice | `selected` | `selected`, `all` | mode | Rename the selected objects or every object in the file. |
| `rename_data` | bool | true | true or false | flag | Give single-user object data (meshes, curves, lights) the new object name. |

## Outputs

The objects are renamed in place, and single-user object data takes the new object name. The core returns `report.renames` as `[old, new]` pairs plus the counts `renamed`, `unchanged` and `numbered`.

## Limits

Renames objects and, when they have a single user, their data; materials, collections and other data blocks keep their names. Case splitting is a heuristic for ASCII words and digit runs. Names are cut to 63 bytes, so very long names lose their end. Regular expressions use Python syntax. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Two-pass renaming through temporary names to avoid automatic .001 suffixes
- Word splitting at case changes and digit runs with regular expressions
- Collision-free numbering within groups of equal names

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
