# Particle water fountain with swirl and floor bounce

`start()` places each droplet on a small disc around the emitter and launches it inside a cone around the emitter's up axis, with a tangential swirl and a random size. `process()` applies gravity, detects the floor plane at `floor_height` (world space), reflects the vertical velocity with `bounce` and damps the horizontal velocity, then fades the colour from `water_color` to `spray_color` with age or after a bounce. Godot integrates the position from `VELOCITY`.

## When to use it

Use it for fountains, water jets, sprinklers and similar arcs of droplets that should land and splash. Rotate the emitter to aim the jet.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/particles_fountain/`. `material.tres` loads the shader from `res://baltor/godot_shaders/particles_fountain/particles_fountain.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` as the `process_material` of a GPUParticles node. Give a GPUParticles3D a draw pass mesh whose material uses the vertex colour as albedo, or give a GPUParticles2D a texture; the shader writes position, velocity and colour.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `launch_speed` | float | hint_range(0.0, 20.0) | 5.5 | Initial speed along the jet direction, in metres per second. |
| `spread_degrees` | float | hint_range(0.0, 45.0) | 9.0 | Half-angle of the launch cone. |
| `nozzle_radius` | float | hint_range(0.0, 1.0) | 0.06 | Radius of the disc droplets start on. |
| `swirl_speed` | float | hint_range(-4.0, 4.0) | 0.8 | Tangential speed around the jet axis; negative swirls the other way. |
| `gravity` | float | hint_range(0.0, 30.0) | 9.8 | Downward acceleration in metres per second squared. |
| `floor_height` | float | hint_range(-5.0, 5.0) | 0.0 | World-space height of the floor plane droplets bounce on. |
| `bounce` | float | hint_range(0.0, 1.0) | 0.3 | Fraction of vertical speed kept after hitting the floor. |
| `droplet_scale` | float | hint_range(0.1, 4.0) | 1.0 | Scale applied to every droplet, with per-droplet variation. |
| `water_color` | vec4 | source_color | (0.45, 0.75, 1, 1) | Colour of droplets in flight. |
| `spray_color` | vec4 | source_color | (0.92, 0.97, 1, 1) | Colour droplets move toward with age and after bouncing. |

## Inputs

- A GPUParticles3D node with a draw pass mesh (for example a small QuadMesh) whose material uses vertex colour as albedo and particle billboarding, as in `demo.tscn`.

## Output

An arcing jet of droplets that rises, falls, bounces on the floor height and fades into spray.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

The floor is an infinite horizontal plane; there is no collision with scene geometry (use Godot's particle collision nodes for that). Each droplet bounces with the same rule, so repeated bounces lose energy quickly. Positions are in world space (local_coords off), so moving the emitter leaves droplets behind as real water would.

## Technique

- Integer hash for per-particle random numbers
- Uniform sampling of a cone and a disc
- Explicit Euler integration with velocity reflection at a plane
