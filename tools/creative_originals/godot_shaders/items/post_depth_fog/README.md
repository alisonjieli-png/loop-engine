# Distance and height fog from the depth buffer

Each pixel's view position comes from the depth buffer and is turned into a world position. Distance fog is `1 - exp(-density * distance)`. Height fog integrates an exponential density that falls off with altitude along the view ray in closed form, so it is thick in valleys and thin on hilltops and looking up. The fog colour blends from near to far with distance, and a lobe toward the sun direction brightens it.

## When to use it

Use it for atmospheric depth, misty valleys and mornings, sandstorm or smog tints, and in renderers where volumetric fog is unavailable.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_depth_fog/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_depth_fog/post_depth_fog.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `depth_texture` | sampler2D | hint_depth_texture, filter_nearest |  | The scene depth buffer (filled by Godot). |
| `near_color` | vec4 | source_color | (0.62, 0.68, 0.75, 1) | Fog colour close to the camera. |
| `far_color` | vec4 | source_color | (0.78, 0.82, 0.88, 1) | Fog colour at `color_distance` and beyond. |
| `sun_color` | vec4 | source_color | (1, 0.85, 0.6, 1) | Glow added to fog looking toward the sun. |
| `distance_density` | float | hint_range(0.0, 1.0) | 0.08 | Density of the uniform distance fog per metre. |
| `height_density` | float | hint_range(0.0, 2.0) | 0.6 | Density of the height fog at its base height. |
| `height_falloff` | float | hint_range(0.01, 4.0) | 1.2 | How quickly height fog thins with altitude. |
| `fog_base_height` | float | hint_range(-50.0, 50.0) | -0.5 | World height where the height fog has full density. |
| `color_distance` | float | hint_range(1.0, 200.0) | 25.0 | Distance over which fog colour blends from near to far. |
| `sun_azimuth_degrees` | float | hint_range(-180.0, 180.0) | 20.0 | Sun direction around Y, measured from the camera's forward (-Z) toward +X. |
| `sun_elevation_degrees` | float | hint_range(-10.0, 90.0) | 15.0 | Sun height above the horizon. |
| `sun_glow` | float | hint_range(0.0, 2.0) | 0.6 | Strength of the sun glow in the fog. |
| `max_opacity` | float | hint_range(0.0, 1.0) | 1.0 | Upper limit of the fog opacity. |

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene fading into pale blue-grey fog with distance and near the ground, warmer toward the sun.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Sky pixels are at the far plane, so they take full fog unless `max_opacity` is lowered. Fog is computed after lighting, so it does not affect shadows or light scattering. Transparent objects are fogged as their background. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Exponential distance fog
- Analytic integral of exponential height fog along the view ray
- World position reconstruction from depth
