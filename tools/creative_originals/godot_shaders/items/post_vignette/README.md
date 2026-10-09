# Shaped vignette with colour and focus point

The distance from a focus point is measured either round (a circle corrected for the screen aspect) or boxy (the larger axis distance), blended by `roundness`. A smoothstep from `radius` over `softness` gives the mask, which blends the scene toward `vignette_color` by `intensity`. Moving the focus point keeps a subject clear when it is off centre.

## When to use it

Use it to frame shots, draw attention to the centre or a subject, add mood (cold blue or warm amber edges), and show low health or tunnel vision by animating the radius.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_vignette/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_vignette/post_vignette.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `vignette_color` | vec4 | source_color | (0.02, 0, 0.04, 1) | Colour the edges move toward. |
| `intensity` | float | hint_range(0.0, 1.0) | 0.75 | Opacity of the vignette at its strongest. |
| `radius` | float | hint_range(0.0, 1.5) | 0.55 | Distance from the focus point where the darkening starts. |
| `softness` | float | hint_range(0.01, 1.0) | 0.45 | Width of the transition. |
| `roundness` | float | hint_range(0.0, 1.0) | 1.0 | 1 gives a circle corrected for aspect, 0 a rectangle following the screen. |
| `focus_x` | float | hint_range(0.0, 1.0) | 0.5 | Horizontal position of the clear centre (0 to 1). |
| `focus_y` | float | hint_range(0.0, 1.0) | 0.5 | Vertical position of the clear centre (0 to 1). |

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene with soft, very dark purple edges and a clear centre.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

A colour blend, not an exposure change: bright highlights at the edges are flattened toward the colour. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Distance mask with adjustable roundness and aspect
- Colour blend vignette
