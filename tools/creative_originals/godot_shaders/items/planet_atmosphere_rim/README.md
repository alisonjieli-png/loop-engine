# Planet atmosphere shell with analytic path length

The shell is a sphere of radius `shell_radius` drawn additively over a planet of radius `planet_radius`. For each fragment the shader works in object space: it finds the point where the camera ray passes closest to the centre, and from that impact distance computes the chord length through the shell, stopping at the planet surface when the ray hits it. That path length, divided by the longest chord that grazes the planet, becomes scattering through `1 - exp(-density * depth)`, so the limb glows several times brighter than the centre of the disc. `light()` lights the glow with each light using the direction of the closest point (or of the planet hit point when the ray hits the planet), so only the day side glows, tinted toward `sunset_color` near the terminator.

## When to use it

Use it on planets and moons in space scenes and orbital views; put it on a sphere slightly larger than the planet mesh.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/planet_atmosphere_rim/`. `material.tres` loads the shader from `res://baltor/godot_shaders/planet_atmosphere_rim/planet_atmosphere_rim.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `atmosphere_color` | vec4 | source_color | (0.35, 0.6, 1, 1) | Colour of the lit atmosphere. |
| `sunset_color` | vec4 | source_color | (1, 0.5, 0.3, 1) | Colour near the day and night boundary. |
| `shell_radius` | float | hint_range(0.1, 10.0) | 1.0 | Radius of the shell mesh in object units (match the mesh). |
| `planet_radius` | float | hint_range(0.1, 10.0) | 0.9 | Radius of the planet in the shell's object units. |
| `density` | float | hint_range(0.0, 10.0) | 1.2 | Scattering density; higher saturates the glow sooner. |
| `brightness` | float | hint_range(0.0, 8.0) | 1.6 | Brightness of the lit glow. |
| `terminator_softness` | float | hint_range(0.0, 1.0) | 0.35 | Width of the transition from day to night side. |
| `night_glow` | float | hint_range(0.0, 0.5) | 0.02 | Faint glow kept on the night side. |

## Inputs

- A planet mesh and a slightly larger sphere for the shell, both centred at the same point; a DirectionalLight3D as the sun.

## Output

A planet with a thin blue halo on its sunlit limb that turns orange at the terminator.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Single-colour scattering with an exponential falloff, not Rayleigh and Mie integration. The shell must be a sphere centred on its origin without non-uniform scale. Additive, so it cannot darken the planet. The camera must stay outside the shell.

## Technique

- Analytic ray-sphere chord length (closest approach distance)
- Exponential scattering from optical depth
- Fragment-to-light varying for light-dependent glow
