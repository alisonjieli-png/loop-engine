# Swirling portal disc

UVs are turned into polar coordinates around the centre of the disc. The spiral term adds `twist` divided by the radius to the angle, so arms wind tighter toward the centre, and subtracts `TIME` so they rotate. The colour blends from `inner_color` near the core to `outer_color` at the edge, is modulated by the arm mask and an inward-scrolling radial wave, gets sparkles from thresholded noise, fades into a dark core and ends in a bright rim ring. Pixels outside the unit circle are discarded.

## When to use it

Use it for portals, warp gates, magic circles, black holes in stylized games and loading vortices.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/swirl_portal/`. `material.tres` loads the shader from `res://baltor/godot_shaders/swirl_portal/swirl_portal.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `outer_color` | vec4 | source_color | (0.45, 0.15, 0.95, 1) | Colour toward the edge of the disc. |
| `inner_color` | vec4 | source_color | (0.2, 0.9, 1, 1) | Colour toward the centre. |
| `core_color` | vec4 | source_color | (0.02, 0, 0.05, 1) | Colour of the central hole. |
| `rim_color` | vec4 | source_color | (1, 0.85, 1, 1) | Colour of the outer ring. |
| `arms` | int | hint_range(1, 12) | 4 | Number of spiral arms. |
| `twist` | float | hint_range(0.0, 20.0) | 6.0 | How tightly the arms wind toward the centre. |
| `spin_speed` | float | hint_range(-10.0, 10.0) | 2.0 | Rotation speed in radians per second. |
| `core_radius` | float | hint_range(0.0, 0.5) | 0.12 | Radius of the dark core (0 to 1 of the disc). |
| `rim_width` | float | hint_range(0.0, 0.2) | 0.04 | Width of the rim ring. |
| `sparkle_amount` | float | hint_range(0.0, 1.0) | 0.5 | Brightness of drifting sparkles. |
| `glow` | float | hint_range(0.0, 4.0) | 1.4 | Overall brightness multiplier. |

## Inputs

- A quad or disc with UVs spanning 0 to 1; the portal fills the inscribed circle.

## Output

A spinning purple and cyan spiral disc with a dark centre and a bright outer ring.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Flat effect on a card; it has no depth or parallax. The polar angle has a seam where atan wraps, hidden by whole numbers of arms but visible with sparkles at high zoom. Unshaded, so it ignores scene light.

## Technique

- Polar coordinate spiral (angle plus twist over radius)
- Thresholded value noise sparkles
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
