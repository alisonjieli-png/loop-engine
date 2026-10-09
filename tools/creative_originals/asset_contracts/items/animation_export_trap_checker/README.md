# Animation export trap checker with a Blender declare and repair procedure

Catches exports that keep every mesh and lose the animation. Blender 5.2 with default glTF settings writes only the
action an object is playing: an action kept by a fake user is left out without a warning. Other exports merge
every action into one clip, bake a clip over the whole scene range, write a channel with no target node, or bake
the clip to a single pose.

## What it checks

Against a declaration of the clips the source scene holds:

- `animations_missing`: clips were declared and the export has no animation at all.
- `clip_missing`: a declared clip is absent (similar names are listed).
- `clips_merged`: one undeclared export clip carries the targets of two or more missing clips.
- `clip_target_missing`: a declared node and path has no channel in the clip.
- `clip_static`: the clip plays, but every channel holds one value.
- `clip_duration_mismatch`: the play length differs from the declaration beyond its tolerance (0.05 s default).
- `channel_target_unresolved`: a channel points at no node, or at a node outside the scene.

## The procedure

```bash
# 1. Declare what the scene holds, before export.
blender --background door.blend --python procedure/declare_clips_blender.py -- door.clips.json
# 2. Export as usual, then check the export.
python3 animation_export_trap_checker.py door.gltf --declared door.clips.json
# 3. If clips are missing: give every action its own NLA track, save a copy, export that copy again.
blender --background door.blend --python procedure/push_actions_to_nla.py -- door_fixed.blend
```

A declaration can also be written by hand, or taken from the `clips` of an `asset_specification/v1`.

## What a pass proves

Every declared clip exists by name, animates each declared node and path through a resolved channel, changes at
least one value, and plays its declared length.

## What a pass does not prove

That the motion is the intended motion, that interpolation matches the source curves, or that a game plays the
clip on the right node.

## Engine evidence

The native verifier builds a framed door in Blender 5.2.1 with an Open action (fake user only) and a playing Close
action, declares its clips with the script above, exports with default settings and confirms that this tool
refuses the export with `clip_missing` for Open. It then runs the NLA script, exports again, confirms the export
passes, and loads it in Godot 4.7.2, where both clips play for 1 s. For every fixture it also compares clip names,
play lengths and moving channels with Godot's AnimationPlayer and Blender's imported actions. Two engine behaviors
showed up on the known-wrong exports: Godot drops a track whose value never changes, and a clip whose only channel
has no target becomes an empty 0.001 s clip in Godot and disappears in Blender. Play length and motion in this
tool's report therefore count only channels with a resolved target.

## Limits

Exact clip names. Motion means a value changed by more than 1e-5. The Blender scripts cover object, bone and shape
key channels, not drivers or constraints.
