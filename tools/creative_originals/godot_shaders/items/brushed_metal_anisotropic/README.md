# Brushed metal with a Ward anisotropic highlight

The fragment stage picks a brushing direction for each pixel: the mesh tangent for straight brushing, or the direction around a UV centre for spun metal, and passes it to `light()` through a varying. `light()` evaluates the Ward anisotropic model, a Gaussian lobe in the tangent frame with separate roughness along and across the brushing, so highlights stretch into bright streaks across the grooves. Thin value-noise stripes across the brushing modulate the albedo.

## When to use it

Use it for brushed steel and aluminium panels, spun metal discs, cookware, appliance faces and sci-fi hulls, where an isotropic highlight looks plastic.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/brushed_metal_anisotropic/`. `material.tres` loads the shader from `res://baltor/godot_shaders/brushed_metal_anisotropic/brushed_metal_anisotropic.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `metal_color` | vec4 | source_color | (0.82, 0.83, 0.85, 1) | Reflectance colour of the metal. |
| `roughness_along` | float | hint_range(0.02, 1.0) | 0.08 | Roughness along the brushing; low values make long streaks. |
| `roughness_across` | float | hint_range(0.02, 1.0) | 0.45 | Roughness across the brushing. |
| `circular` | bool | none | false | Brush in circles around a UV centre instead of along the tangent. |
| `circle_center_u` | float | hint_range(0.0, 1.0) | 0.5 | U coordinate of the circle centre. |
| `circle_center_v` | float | hint_range(0.0, 1.0) | 0.5 | V coordinate of the circle centre. |
| `streak_density` | float | hint_range(10.0, 2000.0) | 600.0 | Number of brush streaks across the UV range. |
| `streak_strength` | float | hint_range(0.0, 1.0) | 0.25 | Contrast of the brush streaks in the albedo. |
| `diffuse_amount` | float | hint_range(0.0, 1.0) | 0.15 | Small diffuse term for rough metal. |
| `specular_strength` | float | hint_range(0.0, 2.0) | 0.2 | Scale of the anisotropic highlight. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A mesh with UVs and tangents.

## Output

Metal with a bright highlight smeared along the brushing, here as rings across a spun disc.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Ignores environment reflections: only scene lights give specular, so add a light or use Godot's built-in ANISOTROPY output when reflections matter. Ward's model is not energy conserving at grazing angles. Circular brushing needs UVs centred on the disc (the CylinderMesh caps qualify).

## Technique

- Ward anisotropic BRDF (Ward 1992)
- Fragment-to-light varying for a per-pixel tangent frame
- Value noise with quintic interpolation and fractional Brownian motion for brush streaks
