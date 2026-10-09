# Dithered distance fade for camera occluders

Each pixel is kept or discarded by comparing the opacity with a 4 x 4 ordered dither (Bayer) threshold chosen by the screen position. With `use_distance`, the opacity falls from 1 at `far_distance` to 0 at `near_distance` from the camera, and `fade` multiplies it. Because surviving pixels are fully opaque, the object still writes depth, casts shadows and needs no transparency sorting; the eye blends the pattern into a fade.

## When to use it

Use it on walls, trees and props that come between a third-person camera and the player, for LOD cross-fades, and to fade objects in and out without sorting artefacts.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/screen_door_fade/`. `material.tres` loads the shader from `res://baltor/godot_shaders/screen_door_fade/screen_door_fade.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `albedo` | vec4 | source_color | (0.55, 0.6, 0.68, 1) | Surface colour. |
| `roughness` | float | hint_range(0.0, 1.0) | 0.7 | Surface roughness. |
| `fade` | float | hint_range(0.0, 1.0) | 1.0 | Overall opacity from 0 (gone) to 1 (solid). |
| `near_distance` | float | hint_range(0.0, 20.0) | 1.0 | Camera distance in metres where the object is fully dissolved. |
| `far_distance` | float | hint_range(0.1, 40.0) | 2.6 | Camera distance in metres where the object is solid again. |
| `dither_scale` | float | hint_range(1.0, 8.0) | 1.0 | Size of the dither cells in pixels. |
| `use_distance` | bool | none | true | Fade by camera distance as well as by `fade`. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

Pillars near the camera break into a regular dot pattern you can see through, solid further away.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

The pattern is visible as a grid at low resolutions and flickers with temporal anti-aliasing off; with TAA or FSR it smooths out. Shadows use the shadow camera's distance, not the main camera's, so a faded object can still cast a full shadow.

## Technique

- Ordered dithering with a 4 x 4 Bayer matrix
- Alpha-tested screen-door transparency
- Camera distance fade
