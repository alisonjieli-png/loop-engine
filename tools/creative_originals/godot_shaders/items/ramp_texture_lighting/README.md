# Lighting through an artist colour ramp

`light()` computes a half-Lambert term with shadows and uses it as the horizontal coordinate into `light_ramp`. Whatever the ramp holds becomes the light colour: hard steps give cel shading, smooth spans give soft shading, and colours give tinted shadows and warm highlights. The material ships with a GradientTexture1D going from deep purple shadow through a sharp orange terminator to warm white. A hard specular spot takes the ramp's brightest colour and a rim picks up the ramp at the silhouette.

## When to use it

Use it for stylized characters and worlds whose art direction defines lighting with colour ramps, and to match 2D concept art palettes.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/ramp_texture_lighting/`. `material.tres` loads the shader from `res://baltor/godot_shaders/ramp_texture_lighting/ramp_texture_lighting.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `light_ramp` | sampler2D | source_color, filter_linear, repeat_disable |  | Gradient that maps light (left dark, right lit) to a colour. |
| `albedo` | vec4 | source_color | (1, 1, 1, 1) | Surface colour multiplied with the ramp result. |
| `ramp_offset` | float | hint_range(-0.5, 0.5) | 0.0 | Shifts the lookup to brighten or darken the whole ramp. |
| `specular_size` | float | hint_range(0.0, 1.0) | 0.12 | Size of the hard specular spot. |
| `specular_strength` | float | hint_range(0.0, 2.0) | 0.6 | Brightness of the specular spot. |
| `rim_amount` | float | hint_range(0.0, 1.0) | 0.3 | Brightness of the rim light. |
| `rim_width` | float | hint_range(0.0, 1.0) | 0.25 | Width of the rim. |

## Inputs

- A ramp texture; edit the bundled GradientTexture1D or assign any horizontal gradient image.

## Output

Shapes shaded from purple shadows through an orange edge to warm white light.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Each light samples the ramp separately and adds, so several lights brighten past the ramp. Ambient light does not use the ramp. A ramp with sharp steps aliases at grazing angles.

## Technique

- Ramp texture lighting (lookup of the half-Lambert term)
- Hard step specular
- Ramp-tinted rim
