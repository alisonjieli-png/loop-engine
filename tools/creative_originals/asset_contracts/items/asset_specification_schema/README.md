# Asset specification schema with validator and blockout generator

States what a 3D asset must be before anyone models it, in a form a harness, a modeller and a checker can all read.
A specification lists the asset's named parts (parent, dimensions in metres, centre, pivot, material), its joints
(type, part, axis, limits), its clips (duration, targets) and its behaviors (which joint and clip a trigger uses).

## Files

- `schema.json`: the JSON Schema (draft 2020-12). Any validator can use it.
- `asset_specification_schema.py`: applies the schema with the standard library, adds the cross-reference rules a
  schema cannot express, and writes a blockout.

## Rules beyond the schema

Unique part, clip and material names; parents that exist and form no cycle; one joint per part; joint parts that
exist; unit axes; limits that fit the joint type (`limits_deg` for revolute, `limits_m` for prismatic, none for
continuous and fixed) with lower below upper and the rest value inside; clip targets and behavior references that
exist; part materials that are declared. Names use letters, digits, underscore, space and hyphen only, because
Godot renames `.`, `:`, `@`, `/`, `"` and `%`.

## Run it

```bash
python3 asset_specification_schema.py cabinet.spec.json
python3 asset_specification_schema.py cabinet.spec.json --blockout cabinet_blockout.gltf
```

The blockout is a glTF with one box per part at its centre and size, node origins at the pivots, the declared
materials, and for each revolute or prismatic joint a clip per non-zero limit, `<joint>_lower` and
`<joint>_upper`, that moves the part from the modelled pose (joint value 0) to that limit in one second. It is a
placeholder to build against, not a model.

## What a pass proves

The document is a well-formed, internally consistent specification.

## What a pass does not prove

That any model satisfies it. Use `gltf_semantic_recovery` to compare a model with the specification.

## Engine evidence

The native verifier checks that this tool's schema verdict equals the `jsonschema` library's (draft 2020-12) for
every fixture, writes the blockout of each valid fixture, and loads it in Godot 4.7.2 and Blender 5.2.1: parts,
parents, pivots, world boxes and materials equal the specification, and each limit clip ends at its limit (Godot
samples the rotation or translation at the clip's end; Blender is measured at frame 0, the modelled pose).

## Limits

Rest poses carry no rotation. Continuous and fixed joints get no limit clip.
