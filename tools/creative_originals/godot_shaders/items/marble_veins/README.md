# Procedural marble with turbulent veins

Marble veins follow the classic turbulence construction: a sine wave across the object whose phase is pushed around by a sum of absolute noise octaves, which folds straight bands into wandering veins. One minus the absolute sine, raised to `vein_sharpness`, keeps only thin dark lines. A second, finer network runs in another direction, and low-frequency fBm adds cloudy grey patches to the white body. The finish is glossy with slightly rougher veins.

## When to use it

Use it for marble floors, counters, columns, statues, chess pieces and luxury interiors.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/marble_veins/`. `material.tres` loads the shader from `res://baltor/godot_shaders/marble_veins/marble_veins.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `body_color` | vec4 | source_color | (0.92, 0.91, 0.88, 1) | Main colour of the stone. |
| `cloud_color` | vec4 | source_color | (0.82, 0.8, 0.78, 1) | Colour of the soft cloudy patches. |
| `vein_color` | vec4 | source_color | (0.25, 0.27, 0.3, 1) | Colour of the veins. |
| `scale` | float | hint_range(0.2, 10.0) | 1.6 | Overall pattern scale per object unit. |
| `vein_frequency` | float | hint_range(0.5, 20.0) | 3.5 | Number of main veins across the object. |
| `turbulence` | float | hint_range(0.0, 10.0) | 4.5 | How strongly the veins wander. |
| `vein_sharpness` | float | hint_range(1.0, 40.0) | 14.0 | Exponent that thins the veins. |
| `fine_veins` | float | hint_range(0.0, 1.0) | 0.4 | Strength of the second, finer network. |
| `roughness` | float | hint_range(0.0, 1.0) | 0.12 | Roughness of the polished stone. |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

White polished stone with dark grey wandering veins and soft cloudy areas.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Solid texture in object space: objects that should continue one slab need the same transform. Veins have no depth or translucency. Ten noise octaves per pixel plus fBm make it moderately expensive.

## Technique

- Turbulence marble (sine of position plus absolute-noise turbulence, Perlin 1985)
- Two vein networks
- Value noise with quintic interpolation and fractional Brownian motion
