# Articulation manifest with a Godot runtime joint builder

A glTF file carries meshes, a hierarchy and clips, but no joints. This item adds them: a small manifest beside the
asset names, for each joint, the node it moves, whether it is a hinge or a slider, its axis and pivot in the node's
own frame, and its limits. A checker validates the binding and predicts every pose; a Godot 4 node applies the
same manifest at run time.

## The manifest (`articulation_manifest/v1`, see `schema.json`)

```json
{"record_type": "articulation_manifest/v1", "asset": "toolbox.gltf",
 "joints": [{"name": "lid_hinge", "type": "hinge", "node": "Lid", "axis": [1, 0, 0],
             "pivot": [0, -0.01, -0.15], "limits": [-110, 0], "rest": 0},
            {"name": "tray_slide", "type": "slider", "node": "Tray", "axis": [0, 0, 1], "limits": [0, 0.2]}]}
```

A joint value moves its node from its modelled transform `BASE` to `BASE * M(value)`: a hinge turns by `value`
degrees about the axis through the pivot, a slider moves `value` metres along the axis.

## Check a binding

```bash
python3 articulation_manifest_godot_builder.py toolbox.gltf --manifest toolbox.articulation.json
```

Refuses missing or repeated node names, two joints on one node, non-unit axes, invalid pivots and limits that are
not ordered around the rest value. The report predicts each moving node's world matrix and world pivot at both
limits.

## Use it in Godot

```gdscript
const ArticulatedAsset := preload("res://godot/articulated_asset.gd")
var asset := ArticulatedAsset.new()
add_child(asset)
asset.load_asset("res://toolbox.gltf", "res://toolbox.articulation.json")
asset.set_joint("lid_hinge", -80.0)          # clamped to [-110, 0]
var player := asset.build_animation_player() # clips lid_hinge_lower, tray_slide_upper
asset.save_scene("res://toolbox_articulated.tscn")
```

The saved scene stores the manifest, the joint node paths and the modelled transforms, and rebinds its joints in
`_ready()`, so it opens without the glTF. `godot/articulation_probe.gd` exercises an asset headless and writes JSON.

## What a pass proves

The manifest binds cleanly to the asset, and the predicted poses are the forward kinematics of the manifest.

## What a pass does not prove

Collision-free motion, real-world limits, or physics behavior: the Godot node sets transforms and adds no physics
joints.

## Engine evidence

In Godot 4.7.2 the native verifier loads each known-good asset with its manifest, moves each joint to both limits
and past them, and compares the global transform and world pivot of the moving node with this tool's prediction;
it plays every generated clip to its end, saves the scene, reopens it in a new Godot process and repeats the
comparison, and confirms that the Godot node also refuses every known-wrong binding. Blender 5.2.1 confirms that
every bound node exists at the same world origin.

## Limits

Hinges and sliders only. Exact node names. Clips approximate a hinge arc with ten linear steps.
