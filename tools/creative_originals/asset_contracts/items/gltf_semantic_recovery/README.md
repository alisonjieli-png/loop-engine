# glTF semantic recovery against an asset specification

Reads what an asset means from the file alone and compares it with what the asset was supposed to be. A model can
pass every structural check and still be wrong: written in centimetres, exported Z-up into a Y-up file, flattened
so the handle no longer follows the door, with a part left unnamed or a clip dropped. If the meaning cannot be
recovered from the artifact itself, a game or a harness cannot rely on it.

## What it recovers

For every node in the scene: name, path, parent, world pivot (node origin), world box and dimensions in metres at
the rest pose, the dimensions of its whole subtree, and the materials of its mesh. Also the clip list with play
lengths, the material list and the nodes that have no name.

## What it compares

With `--spec`, an `asset_specification/v1` document: each part's parent, dimensions (its own mesh, or its subtree
with `"measure": "subtree"`), pivot and material, the material list, and each clip's presence and duration. A
dimension mismatch names its likely cause when one fits: one uniform factor (centimetres, millimetres, inches,
feet) or Y and Z swapped.

## Run it

```bash
python3 gltf_semantic_recovery.py door.gltf                      # recovered facts only
python3 gltf_semantic_recovery.py door.gltf --spec door.spec.json # compare with the specification
```

One JSON report; exit 0 when everything matches, 1 otherwise.

## What a pass proves

The parts, parents, dimensions, pivots, materials and clips a reader recovers from the file equal the
specification within its tolerances (5 mm and 0.05 s by default).

## What a pass does not prove

That the shapes are right, that clips move the right way or that joints work. Boxes are axis-aligned in world
axes at the rest pose.

## Engine evidence

For every fixture, known-good and known-wrong, the native verifier loads the file in Godot 4.7.2 and Blender
5.2.1 and requires both engines to report the same part names, parents, world boxes, pivots, part materials and
clip lengths as this tool. The known-wrong files therefore show the defect as the engines see it: the centimetre
door is 210 m tall in both.

## Limits

Exact name matching. Rotated parts measure as their world box. Skinned meshes are measured at the bind pose.
