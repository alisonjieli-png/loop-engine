# glTF 2.0 structural validator

Checks that a `.gltf` or `.glb` file is internally consistent before an engine loads it. Engines are lenient in
different ways, so a broken file can load in one tool, hang in another and lose data silently in a third.

## What it catches

- Buffers that cannot be read or are shorter than declared, buffer views outside their buffer, invalid strides.
- Accessors with invalid types, misaligned offsets, data outside their buffer view, declared `min` and `max` that
  differ from the data, NaN or infinity, broken sparse storage.
- Primitives whose attributes disagree in count, wrong attribute types, indices out of range or of the wrong type,
  index counts that do not fit the primitive mode, broken morph targets.
- Material, texture, sampler and image references that point nowhere, out-of-range material factors.
- Node graphs with cycles, nodes with two parents, non-unit rotations, `matrix` together with TRS, scene roots
  that are children of other nodes.
- Skins whose inverse bind matrix count differs from the joint count, skinned meshes without `JOINTS_0` and
  `WEIGHTS_0`, joint indices beyond the skin.
- Animations with key times that do not strictly increase, wrong output types, and output counts that do not match
  the interpolation (three values per key for `CUBICSPLINE`).

Every failure has a closed code; `item.json` lists all of them under `failures_detected`.

## Run it

```bash
python3 gltf_structural_validator.py model.gltf
```

It prints one JSON report (`asset_contract_report/v1`) and exits 0 when no rule fails, 1 otherwise. From Python:

```python
import gltf_structural_validator
report = gltf_structural_validator.validate_file("model.gltf").as_dict()
```

## What a pass proves

Every reference resolves, every accessor lies inside its data and matches its declared bounds, and the node graph,
skins and animation samplers have the shapes the glTF 2.0 data model requires.

## What a pass does not prove

That the asset looks right, has real-world dimensions, sensible names or materials, plausible motion, or
extensions a given engine supports. It is not the Khronos glTF-Validator and does not check every rule of the
specification.

## Engine evidence

The native verifier loads the known-good fixtures in Godot 4.7.2 (GLTFDocument) and Blender 5.2.1 (glTF import)
and compares counts, names, clip lengths, per-node world origins and boxes, and triangle counts with this tool's
report. It also records how each engine reacts to each known-wrong fixture. In the run of October 9, 2026, Godot
stopped responding on the node cycle, and four defects (a buffer shorter than declared, repeated key times, a wrong
POSITION maximum, a non-unit rotation) loaded in both engines without any error. The evidence record lists every
reaction.

## Limits

Pure Python. Extension contents are not validated. Images are checked for existence and magic bytes, not decoded.
Animation pointer targets are accepted without further checks.
