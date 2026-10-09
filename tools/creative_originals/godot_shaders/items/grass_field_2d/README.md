# Procedural 2D grass field with wind

Each layer divides the width into slots with one blade each; a hash gives the blade's position in the slot, its height and its lean. A blade is a triangle that narrows to its tip and bends with the square of its height by a wind sine that travels along X. For each pixel the three nearest blades are tested so leaning blades are not cut at slot borders. Layers are drawn back to front, offset and darkened for depth, and the background stays transparent.

## When to use it

Use it for 2D meadows, side-scroller foregrounds, title screens and ground strips under sprites.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/grass_field_2d/`. `material.tres` loads the shader from `res://baltor/godot_shaders/grass_field_2d/grass_field_2d.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `front_color` | vec4 | source_color | (0.42, 0.72, 0.25, 1) | Blade colour of the front layer. |
| `back_color` | vec4 | source_color | (0.12, 0.32, 0.12, 1) | Blade colour of the back layer. |
| `tip_color` | vec4 | source_color | (0.8, 0.85, 0.45, 1) | Colour blended toward the blade tips. |
| `blades` | float | hint_range(10.0, 200.0) | 60.0 | Blades per rectangle width in the front layer. |
| `blade_height` | float | hint_range(0.1, 1.0) | 0.55 | Tallest blade height in rectangle heights. |
| `wind_strength` | float | hint_range(0.0, 0.3) | 0.06 | Sideways bend of the tips. |
| `wind_speed` | float | hint_range(0.0, 5.0) | 1.4 | Speed of the wind wave. |
| `layers` | int | hint_range(1, 5) | 3 | Number of depth layers. |

## Inputs

- A ColorRect (or any CanvasItem) sized to the area to fill; UVs span 0 to 1 across it.

## Output

A strip of layered green grass blades with light tips swaying in front of a blue sky.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Blades are flat colour without lighting. Very strong wind bends blades beyond the neighbour search and clips them. Cost is layers times three blade tests per pixel.

## Technique

- Hashed blade placement per slot with neighbour search
- Height-squared wind bending
- Back-to-front layer compositing
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
