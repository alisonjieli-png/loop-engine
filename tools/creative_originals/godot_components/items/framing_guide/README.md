# Shot framing helpers: thirds, safe areas and coverage

Check and adjust shot composition: rule-of-thirds points and offsets, action and title safe areas, lead room in front of a subject, screen bounds of 3D points through a Camera3D, and screen coverage.

## How it works

Shot composition helpers: rule-of-thirds points, safe areas, lead room, screen bounds of 3D subjects and
screen coverage, for camera scripts, cutscene tools and automated framing checks.

Screen positions are in pixels with the origin at the top left. The thirds points are the four intersections of
the lines at one and two thirds of the width and height. A safe area is the centered rectangle that keeps a
fraction of each side (0.9 for action safe, 0.8 for title safe are common choices). Lead room is the share of
the screen in front of a subject along its facing direction, from 0 (subject at the front edge) to 1 (at the
back edge). projected_rect() projects 3D points through a Camera3D and returns their screen bounding box,
skipping points behind the camera; coverage() is how much of the screen a rectangle covers.

## When to use it

Use it in cutscene tools, photo modes, automated screenshot checks and camera scripts that should keep subjects well placed and HUD text inside safe areas.

## Installation

Copy this folder to `res://baltor/godot_components/framing_guide/` in a Godot 4.3 or later project. The script `framing_guide.gd` declares the global class `BaltorFraming`, which extends `RefCounted`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Methods

- `static thirds_points(size: Vector2) -> PackedVector2Array`: The four rule-of-thirds intersections for a screen of `size`, top left first, row by row.
- `static nearest_third_point(point: Vector2, size: Vector2) -> Vector2`: The thirds intersection closest to `point`.
- `static safe_area(size: Vector2, fraction: float) -> Rect2`: The centered rectangle that keeps `fraction` of the width and height of a screen of `size`.
- `static is_inside_safe_area(point: Vector2, size: Vector2, fraction: float) -> bool`: True when `point` lies inside the safe area of `fraction`.
- `static offset_to_nearest_third(subject: Vector2, size: Vector2) -> Vector2`: The screen movement that brings `subject` onto its nearest thirds point.
- `static lead_room(subject: Vector2, facing: Vector2, size: Vector2) -> float`: The share of the screen in front of `subject` along `facing` (horizontal facing when the x part dominates, vertical otherwise), from 0 to 1.
- `static projected_rect(camera: Camera3D, points: PackedVector3Array) -> Rect2`: The screen bounding box of `points` seen by `camera`; points behind the camera are skipped. Returns an empty Rect2 when no point is in front.
- `static coverage(area: Rect2, size: Vector2) -> float`: The fraction of a screen of `size` covered by `area` after clipping it to the screen.

## Usage

```gdscript
extends Node3D

@onready var camera: Camera3D = $Camera3D


func check_subject(corners: PackedVector3Array) -> void:
	var size: Vector2 = get_viewport().get_visible_rect().size
	var bounds: Rect2 = BaltorFraming.projected_rect(camera, corners)
	if not BaltorFraming.is_inside_safe_area(bounds.get_center(), size, 0.9):
		print("subject near the edge; move by %s" % BaltorFraming.offset_to_nearest_third(bounds.get_center(), size))
	print("covers %.0f percent of the screen" % (BaltorFraming.coverage(bounds, size) * 100.0))
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/framing_guide/run_tests.gd -- res://baltor/godot_components/framing_guide/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Measures and suggests; it does not move cameras. Coverage uses axis-aligned screen rectangles, not silhouettes. Points behind the camera are skipped rather than clipped. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
