# Gradient map recolouring

The scene's luminance (Rec. 709 weights) is adjusted by contrast and offset and used as the horizontal coordinate into a gradient texture, so shadows, midtones and highlights take the gradient's colours. The bundled GradientTexture1D is a tritone from deep violet through pink to pale gold; any ramp image works, including two-colour duotones and thermal-style palettes.

## When to use it

Use it for stylized grading, flashback and dream tones, thermal or infrared vision, poster looks and to unify mixed assets under one palette.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_gradient_map/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_gradient_map/post_gradient_map.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `gradient` | sampler2D | source_color, filter_linear, repeat_disable |  | Ramp from the colour for black (left) to the colour for white (right). |
| `contrast` | float | hint_range(0.2, 3.0) | 1.2 | Contrast of the luminance before the lookup. |
| `offset` | float | hint_range(-0.5, 0.5) | 0.0 | Shifts the luminance before the lookup. |
| `mix_amount` | float | hint_range(0.0, 1.0) | 1.0 | Blend between the original scene and the mapped colours. |
| `reverse` | bool | none | false | Invert the luminance before the lookup. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.
- A gradient texture for `gradient` (the bundled material has one).

## Output

The scene recoloured into violet shadows, pink midtones and pale gold highlights.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

All hue information is discarded at full mix; objects of equal brightness become the same colour. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Luminance to gradient lookup (gradient map)
- Contrast and offset before lookup
