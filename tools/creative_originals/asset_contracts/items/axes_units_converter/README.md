# Axes, handedness and units checker and converter for glTF

glTF is +Y up, right-handed and in metres, with an asset's front facing +Z. Measured in Blender 5.2.1: exporting with
"+Y Up" turned off writes the height along Z, and a scene set to centimetres (unit scale 0.01, modelled 100 units
tall) exports a door 200 m tall, because the exporter writes raw Blender units. Data from a left-handed tool read
without conversion is mirrored and its faces turn inside out.

## Check

```bash
python3 axes_units_converter.py check door.gltf --expect-dimensions 1.1 2.1 0.15
```

Measures the scene box and the share of triangles whose winding agrees with their normals, and reports
`up_axis_mismatch` (Y and Z swapped), `unit_scale_mismatch` (one uniform factor: centimetres, millimetres, inches,
feet, decimetres), `dimensions_mismatch` or `winding_inverted`, each with the conversion that repairs it.

## Convert

```bash
python3 axes_units_converter.py convert door_zup.gltf door.gltf --from z_up_right
python3 axes_units_converter.py convert door_cm.gltf door.gltf --unit-m 0.01
python3 axes_units_converter.py convert door_lh.gltf door.gltf --from y_up_left_cw
```

Conventions: `gltf`, `z_up_right` (Blender's object space), `y_up_left_cw` and `z_up_left_cw` (left-handed with
clockwise front faces). Every node transform is conjugated, and every point, vector, tangent, morph target, inverse
bind matrix and animation output is mapped. Triangle order is reversed only when needed to keep front faces in front:
a mirroring change between conventions with the same front-face winding, or a non-mirroring change between
different windings.

## What a pass proves

`check`: the box matches the expectation and triangles wind with their normals. `convert`: one change of basis and
unit was applied consistently to the whole file.

## What a pass does not prove

Which way the asset should face, correct camera and light orientation, or support for quantized data.

## Engine evidence

The native verifier repairs the three known-wrong fixtures and loads the results in Godot 4.7.2 and Blender 5.2.1:
every part has the same world box as the correct door. It also builds a door in Blender and exports it three ways
(defaults, "+Y Up" off, centimetre scene): this tool passes the first, reports `up_axis_mismatch` and
`unit_scale_mismatch` for the others, repairs both, and Godot and a Blender re-import give the repaired doors the same
world box as the correct export.

## Limits

Signed axis permutations with a uniform unit factor. Quantized data is refused. Outputs embed one buffer.
