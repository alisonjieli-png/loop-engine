# Rain on a window with running drops

The pane reads the screen texture. Static droplets live in a grid of cells: a hash places one drop per occupied cell with a random size, and the offset from the drop centre acts as the drop's curved surface. Running drops travel down columns at hashed speeds, stretched vertically, leaving a short wet trail. Inside a drop the scene is sampled sharply with a refraction offset from the drop surface; outside, the scene is read from a blurred mip level and mixed toward a mist colour, like fogged glass. Each drop gets a small glint toward its upper left and a darker lower rim so it reads as a bead.

## When to use it

Use it for windows, windscreens, visors and camera-lens rain in rainy scenes, cockpit and car interiors.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/rain_glass_droplets/`. `material.tres` loads the shader from `res://baltor/godot_shaders/rain_glass_droplets/rain_glass_droplets.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | Copy of the scene behind the pane (filled by Godot). |
| `drop_density` | float | hint_range(2.0, 40.0) | 12.0 | Drop cells per UV unit. |
| `drop_size` | float | hint_range(0.05, 0.5) | 0.28 | Largest drop radius in cell units. |
| `runner_columns` | float | hint_range(1.0, 30.0) | 7.0 | Number of columns with running drops across the pane. |
| `runner_speed` | float | hint_range(0.0, 2.0) | 0.35 | Speed of running drops in UV units per second. |
| `refraction` | float | hint_range(0.0, 0.2) | 0.06 | Screen offset of the view inside drops. |
| `mist_blur` | float | hint_range(0.0, 6.0) | 3.0 | Mip level used for the misted glass between drops. |
| `mist_tint` | vec4 | source_color | (0.82, 0.87, 0.92, 1) | Colour of the mist. |
| `mist_amount` | float | hint_range(0.0, 1.0) | 0.25 | How much the mist colour covers the blurred view. |

## Inputs

- A quad (the pane) in front of the scene, with UV v pointing down the glass.

## Output

A misty pane with clear beads of water showing sharp, bent bits of the scene, and drops sliding down.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Screen-space refraction cannot show what is off screen and does not invert the view like a real lens. Drops do not merge or interact; runners can pass through static drops. The mist blur depends on the screen texture's mipmaps.

## Technique

- Hashed cellular droplet placement
- Screen texture refraction with mip-level blur
- Column-based running drops with trails
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
