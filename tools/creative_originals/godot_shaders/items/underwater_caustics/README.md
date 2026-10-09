# Underwater caustics projected from above

Caustics are approximated by Voronoi borders, which form a web of thin cells like light focused by waves. Two layers at different scales drift in different directions; taking their minimum and product keeps only lines where both are bright, so the web shifts and recombines over time. The web is added as emission tinted by the albedo, only on surfaces whose world normal faces up, and fades exponentially with depth below `water_surface_height`.

## When to use it

Use it for seabeds, pool floors, underwater ruins and objects lying in shallow water; combine with a fog or a tinted environment for the water volume.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/underwater_caustics/`. `material.tres` loads the shader from `res://baltor/godot_shaders/underwater_caustics/underwater_caustics.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `albedo` | vec4 | source_color | (0.75, 0.7, 0.55, 1) | Surface colour. |
| `caustic_color` | vec4 | source_color | (0.65, 1, 0.95, 1) | Colour of the caustic light. |
| `caustic_scale` | float | hint_range(0.2, 10.0) | 1.6 | Caustic cells per world unit. |
| `caustic_strength` | float | hint_range(0.0, 4.0) | 1.4 | Brightness of the caustic web. |
| `sharpness` | float | hint_range(1.0, 12.0) | 5.0 | Exponent that thins the web lines. |
| `drift_speed` | float | hint_range(0.0, 2.0) | 0.25 | Drift speed of the two layers. |
| `water_surface_height` | float | hint_range(-20.0, 20.0) | 2.0 | World height of the water surface above. |
| `depth_falloff` | float | hint_range(0.0, 2.0) | 0.25 | Exponential fade of caustics with depth below the surface. |
| `roughness` | float | hint_range(0.0, 1.0) | 0.9 | Surface roughness. |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

Sand-coloured floor and objects covered by a shifting web of bright cyan light lines on their tops.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

A pattern, not light transport: it ignores the real water surface and shadows from objects above. Projected straight down in world space, so vertical walls get none. Emission makes caustics visible even in shade.

## Technique

- Voronoi border web as caustic approximation
- Two drifting layers combined with min and product
- Normal-facing and depth attenuation
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
