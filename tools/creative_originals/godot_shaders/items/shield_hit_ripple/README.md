# Shield impact ripple from a hit point

The hit position is given as azimuth and elevation on the object's unit sphere. For each fragment the angle between its object-space direction and the hit direction is the distance travelled along the sphere surface. A ring sits where that angle equals `ring_reach_degrees` times the impact progress and fades as the progress grows; a flash brightens the hit point early on. Progress comes from `impact_progress` (animate it from a script on each hit) or from a looping timer.

## When to use it

Use it on spherical shields, bubbles and force domes to show where a projectile struck; combine with `force_field_intersection` or `hexagon_shield_pulse` in a second pass.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/shield_hit_ripple/`. `material.tres` loads the shader from `res://baltor/godot_shaders/shield_hit_ripple/shield_hit_ripple.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `shield_color` | vec4 | source_color | (0.25, 0.6, 1, 1) | Colour of the resting shield. |
| `impact_color` | vec4 | source_color | (1, 0.85, 0.5, 1) | Colour of the ring and flash. |
| `hit_azimuth_degrees` | float | hint_range(-180.0, 180.0) | 25.0 | Hit direction around the object's Y axis (0 is +Z). |
| `hit_elevation_degrees` | float | hint_range(-90.0, 90.0) | 15.0 | Hit direction above the equator. |
| `impact_progress` | float | hint_range(0.0, 1.0) | 0.35 | Ring progress from 0 (impact) to 1 (faded) when not looping. |
| `loop_impacts` | bool | none | true | Repeat the impact on a timer instead of using `impact_progress`. |
| `loop_period` | float | hint_range(0.2, 5.0) | 1.5 | Seconds per looping impact. |
| `ring_width` | float | hint_range(0.01, 0.5) | 0.12 | Angular width of the ring in radians. |
| `ring_reach_degrees` | float | hint_range(10.0, 180.0) | 110.0 | Angle the ring has travelled at full progress. |
| `base_strength` | float | hint_range(0.0, 1.0) | 0.08 | Uniform glow of the shield. |
| `rim_strength` | float | hint_range(0.0, 2.0) | 0.6 | Silhouette glow of the shield. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A sphere centred on its origin. To aim at a world hit point, convert it to the object's local direction in a script and set the two angles.

## Output

A faint blue bubble with a bright ring spreading out from the impact point.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

One impact at a time; several simultaneous hits need several materials or an array uniform. Directions are taken from vertex positions, so the mesh must be roughly spherical around its origin. Additive, so it cannot darken.

## Technique

- Great-circle distance from the angle between unit vectors
- Expanding ring with energy fade
- Facing ratio rim
