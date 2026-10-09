# Underwater camera view

The screen is wobbled by two crossing sine waves over time. The distance to each pixel's surface is rebuilt from the depth buffer and used in Beer-Lambert absorption with a separate coefficient per channel, red highest, so distant objects lose red first and turn blue-green. Light scattered by the water is added in proportion to the absorbed share, a gradient brightens the top of the screen toward the surface, and a vignette closes the view.

## When to use it

Use it whenever the camera is underwater: diving and swimming sections, flooded levels, submarine views and aquariums. Toggle it when the camera crosses the water surface.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_underwater_view/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_underwater_view/post_underwater_view.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `depth_texture` | sampler2D | hint_depth_texture, filter_nearest |  | The scene depth buffer (filled by Godot). |
| `water_color` | vec4 | source_color | (0.04, 0.28, 0.38, 1) | Colour of light scattered by the water. |
| `absorption` | float | hint_range(0.0, 2.0) | 0.22 | Absorption per metre for green light. |
| `red_absorption` | float | hint_range(1.0, 6.0) | 3.0 | How many times faster red is absorbed than green (blue uses 0.7 times). |
| `distortion` | float | hint_range(0.0, 0.03) | 0.006 | Strength of the wavy screen distortion. |
| `wave_frequency` | float | hint_range(1.0, 60.0) | 18.0 | Frequency of the distortion waves. |
| `wave_speed` | float | hint_range(0.0, 6.0) | 1.5 | Speed of the distortion waves. |
| `surface_light` | float | hint_range(0.0, 1.0) | 0.35 | Extra light toward the top of the screen from the surface. |
| `vignette` | float | hint_range(0.0, 1.0) | 0.45 | Darkening toward the edges. |

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene tinted deep teal and fading into murk with distance, gently wavering.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Sky pixels are clamped to 200 metres of water. The wobble is screen-space and the same at all depths. No caustics or particles (see `underwater_caustics` for surface caustics). The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Beer-Lambert absorption with per-channel coefficients
- In-scattering proportional to absorbed light
- Sine wave screen distortion
- Distance from reconstructed view position
