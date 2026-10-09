# Screen-space light shafts from the sky

The vertex stage projects the sun direction (a point at infinity) with the view and projection matrices to find its screen position and whether it is in front of the camera. A light source mask is built from pixels whose depth is beyond `sky_depth` (open sky) weighted by a Gaussian around the sun. Each pixel then marches toward the sun, summing the mask with geometric decay, the radial blur method of light scattering as a post process. Where objects block the sky the mask is zero, so they cast dark shafts through the glow.

## When to use it

Use it for sunrises and sunsets behind trees, buildings, ruins and clouds, forest canopies and dusty interiors with a window to the sky.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_light_scattering/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_light_scattering/post_light_scattering.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `depth_texture` | sampler2D | hint_depth_texture, filter_nearest |  | The scene depth buffer (filled by Godot). |
| `sun_azimuth_degrees` | float | hint_range(-180.0, 180.0) | 8.0 | Sun direction around Y, from world -Z toward +X. |
| `sun_elevation_degrees` | float | hint_range(-10.0, 90.0) | 9.0 | Sun height above the horizon. |
| `ray_color` | vec4 | source_color | (1, 0.86, 0.6, 1) | Colour of the light shafts. |
| `samples` | int | hint_range(8, 96) | 48 | Steps marched toward the sun per pixel. |
| `density` | float | hint_range(0.1, 1.0) | 0.85 | Share of the distance to the sun covered by the march. |
| `decay` | float | hint_range(0.8, 1.0) | 0.965 | Per-step falloff of contributions further along the march. |
| `exposure` | float | hint_range(0.0, 2.0) | 0.5 | Brightness of the shafts. |
| `sky_depth` | float | hint_range(10.0, 4000.0) | 50.0 | Depth in metres beyond which a pixel counts as open sky. |
| `sun_size` | float | hint_range(0.01, 1.0) | 0.25 | Screen-space size of the glowing area around the sun. |
| `sun_glow` | float | hint_range(0.0, 2.0) | 0.6 | Brightness of the glow drawn around the sun itself. |

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

Warm shafts of light streaming from a glow near the horizon between the pillars.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Only works while the sun is on or near the screen; rays fade when it leaves. Light sources are sky pixels, so bright emissive objects do not cast rays. Long marches at high resolution are costly. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Light scattering as a post process (radial march with decay, after Mitchell 2007)
- Projection of a direction to the screen
- Depth-based sky mask
