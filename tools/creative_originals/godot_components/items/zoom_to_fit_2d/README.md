# Group camera that zooms to fit several targets

Center a Camera2D on several targets and zoom so all of them fit with a margin, within zoom limits and with smoothing, for local multiplayer and boss fights.

## How it works

A 2D camera that frames several targets: it centers on their bounding box and zooms so all of them fit with a
margin, within zoom limits, with smoothing.

fit() takes the axis-aligned bounds of the points grown by `margin` on every side and returns the bounds'
center and the zoom at which they fill the view: min(view width / bounds width, view height / bounds height),
clamped to `min_zoom`..`max_zoom` (Camera2D zoom above 1 magnifies). A single point gets the
largest zoom. The camera eases its position and zoom toward the fit at `follow_speed` per second.
Targets are NodePaths to Node2D nodes; positions can also be given directly to update_camera().

## When to use it

Use it for couch co-op, fighting games and arenas where every player must stay on one shared screen.

## Installation

Copy this folder to `res://baltor/godot_components/zoom_to_fit_2d/` in a Godot 4.3 or later project. The script `zoom_to_fit_2d.gd` declares the global class `BaltorGroupCamera2D`, which extends `Camera2D`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Exported properties

- `targets: Array[NodePath] = []`: The nodes to keep in view.
- `margin: float = 64.0`: World units of space around the targets.
- `min_zoom: float = 0.25`: Smallest zoom (farthest out).
- `max_zoom: float = 2.0`: Largest zoom (closest in).
- `follow_speed: float = 4.0`: Exponential easing rate of position and zoom, per second; 0 jumps.

### Methods

- `static fit(points: PackedVector2Array, view_size: Vector2, border: float, smallest: float, largest: float) -> Dictionary`: The center and zoom that fit `points` into `view_size` with `border` around them, as {"center": Vector2, "zoom": float}. An empty list gives the origin and zoom 1.
- `update_camera(points: PackedVector2Array, view_size: Vector2, delta: float) -> void`: Eases toward the fit for `points` in a view of `view_size` after `delta` seconds.

## Usage

```gdscript
extends Node2D

@onready var camera: BaltorGroupCamera2D = $GroupCamera


func _ready() -> void:
	camera.targets = [camera.get_path_to($PlayerOne), camera.get_path_to($PlayerTwo)]
	camera.margin = 96.0
	camera.make_current()
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/zoom_to_fit_2d/run_tests.gd -- res://baltor/godot_components/zoom_to_fit_2d/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Fits the axis-aligned bounds of target positions, not their sprites; raise the margin for large characters. Uses the viewport size, so stretch settings change the result. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
