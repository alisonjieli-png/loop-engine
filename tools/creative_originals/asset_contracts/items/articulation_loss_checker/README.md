# Articulation loss checker for exports that drop joint information

An export can keep every mesh in place and still lose the joints. Measured in Blender 5.2.1: joining a door into its
frame removes the door node; "origin to geometry" moves the door's origin from the hinge edge to its centre; the
default glTF export leaves out custom properties, so a joint record stored on the object never reaches the file.
Applying rotation turns a node's frame so the same local axis points elsewhere, and flattening a hierarchy
detaches a handle from the door it should follow.

## What it checks

For each joint of an `articulation_manifest/v1`:

- `joint_node_missing`, `joint_node_ambiguous`: the node is gone, or its name repeats.
- `joint_node_without_geometry`: nothing with a mesh is left at or below the node.
- `pivot_moved`, `joint_axis_changed`, `joint_parent_changed`: against a reference export, the world pivot moved
  (1 mm tolerance), the world axis turned (0.5 degrees), or the parent changed.
- `joint_extras_missing`, `joint_extras_mismatch`: with `--extras required`, the node's `extras.joint` is absent
  or differs from the manifest.

## Run it

```bash
python3 articulation_loss_checker.py export.gltf --manifest door.articulation.json \
    --reference door_reference.gltf --extras required
```

In Blender, export with custom properties (`export_extras=True`, "Include > Custom Properties") when joints travel
in them, and avoid origin changes and joins on moving parts after the reference export.

## What a pass proves

Every joint's node survived with geometry, and, against the reference, kept its pivot, axis and parent; with extras
required, it carries the manifest's joint record.

## What a pass does not prove

That the joint moves the right geometry or that its values make sense. The reference is trusted as given.

## Engine evidence

For every fixture export, Godot 4.7.2 and Blender 5.2.1 report the same per-joint facts as this tool (node count,
parent, world pivot, world axis, extras record). The native verifier also builds a door in Blender whose joint record
is a custom property, exports it four ways (with custom properties, with defaults, after origin to geometry, after
join) and confirms that this tool passes the first and reports `joint_extras_missing`, `pivot_moved` and
`joint_node_missing` for the others; Godot reads the record from the first export's node metadata and finds none in
the default export.

## Limits

Exact node names. Pivot, axis and parent checks need a reference export.
