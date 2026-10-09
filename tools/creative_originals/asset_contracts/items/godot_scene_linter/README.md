# Godot .tscn and .tres parser and linter

Godot loads many broken text scenes without stopping. Measured in Godot 4.7.2: a scene whose material file is
missing loads without the material; a connection from a node that does not exist is dropped without a message; a
node with no type is dropped; a node whose parent path is wrong lands under a mangled name; two siblings with the
same name both load and share one path. Other defects stop the load: an unknown resource id, a sub-resource used
before it is declared, a syntax error, a newer format, a second root.

## What it checks

`ext_resource_missing_file`, `ext_resource_reference_unknown`, `ext_resource_id_repeated`,
`sub_resource_reference_unknown`, `sub_resource_forward_reference`, `sub_resource_id_repeated`,
`node_parent_missing`, `node_name_repeated`, `node_type_missing`, `root_node_count`, `connection_node_missing`,
`resource_section_missing`, `syntax_invalid`, `header_invalid`, `format_unsupported`. Unused resources and Godot 3
files (format 2, which Godot 4 converts on load) are warnings.

## Run it

```bash
python3 godot_scene_linter.py scenes/room.tscn               # finds project.godot upwards
python3 godot_scene_linter.py materials/oak.tres --project .
```

Nodes of instanced scenes count as known parents and connection ends, so overriding `DoorB/Panel` in a room that
instances a door scene is accepted.

## What a pass proves

The file parses and every reference Godot resolves on load points at something that exists, in the right order.

## What a pass does not prove

Valid property values, compiling scripts, existing signals and methods, or resolvable `uid://` references.

## Engine evidence

The native verifier copies the fixture project, loads every fixture in Godot 4.7.2 and instantiates every scene.
Known-good files load without errors, with every parsed node at its path and class and every parsed connection
connected. Every known-wrong file has a visible effect in Godot: refused, instancing failed, errors printed, or a
result that differs from the good door scene. The evidence lists each reaction.

## Limits

res:// paths only; values are not type-checked; connections are checked for nodes, not for signals or methods.
