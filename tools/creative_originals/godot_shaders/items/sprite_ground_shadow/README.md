# Projected ground shadow for 2D sprites

The vertex stage recovers the sprite's base line from each vertex's position and UV, measures the vertex height above it, and maps it back down below the base scaled by `flatten` and shifted sideways by `skew`, which lays the sprite on the ground like a shadow from a low light. The fragment stage keeps only the alpha and paints it in the shadow colour, fading toward the far end.

## When to use it

Use it for characters, trees and props in side-on or three-quarter 2D games where a simple directional shadow adds grounding; animate `skew` with the time of day.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/sprite_ground_shadow/`. `material.tres` loads the shader from `res://baltor/godot_shaders/sprite_ground_shadow/sprite_ground_shadow.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `shadow_color` | vec4 | source_color | (0.05, 0.05, 0.1, 0.5) | Colour and opacity of the shadow. |
| `flatten` | float | hint_range(0.05, 1.5) | 0.45 | Shadow length relative to the sprite height. |
| `skew` | float | hint_range(-3.0, 3.0) | 1.1 | Sideways lean of the shadow per unit of height (light direction). |
| `base_v` | float | hint_range(0.0, 1.0) | 1.0 | UV v of the sprite's feet (1 is the bottom of the texture). |
| `fade` | float | hint_range(0.0, 1.0) | 0.6 | How much the shadow fades toward its far end. |
| `sway` | float | hint_range(0.0, 1.0) | 0.0 | Slow back-and-forth of the lean, for moving light such as torches. |

## Inputs

- A second sprite node with the same texture, placed at the character's position and drawn first.

## Output

A sprite standing on the ground with a flattened dark shadow stretching to its lower right.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Use a second node with the same texture and this material, drawn before the character (as in the demo). The shadow is a projection of the sprite outline, not lit by Godot's 2D lights, and does not bend over terrain.

## Technique

- Planar shadow projection by vertex shear and flattening
- Base line recovered from vertex position and UV
