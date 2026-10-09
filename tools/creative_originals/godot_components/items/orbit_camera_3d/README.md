# Third-person orbit camera with collision pull-in

Orbit a Camera3D around a target with yaw, pitch and zoom limits, smooth distance changes and a ray that pulls the camera in front of walls so the target stays visible.

## How it works

A third-person orbit camera: yaw, pitch and distance around a target, with limits, smoothing and a pull-in
when geometry blocks the view.

The camera orbits a pivot: the target node's global position plus `target_offset`. The desired offset
from the pivot is (sin(yaw) cos(pitch), sin(pitch), cos(yaw) cos(pitch)) times the distance, so yaw 0 and pitch
0 put the camera on the +Z side of the target looking toward -Z. With `collide` a ray from the pivot to
the desired position (excluding the target's own collision object) shortens the distance to the first hit minus
`collision_margin`. A shorter distance is taken at once so walls never come between camera and target;
a longer one eases in with exponential smoothing at `smoothing` per second. The camera then looks at
the pivot.

## When to use it

Use it for third-person action and exploration games where the player rotates the camera with the mouse and the camera must not end up inside walls.

## Installation

Copy this folder to `res://baltor/godot_components/orbit_camera_3d/` in a Godot 4.3 or later project. The script `orbit_camera_3d.gd` declares the global class `BaltorOrbitCamera3D`, which extends `Camera3D`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Exported properties

- `target_path: NodePath = NodePath("")`: The node to orbit.
- `target_offset: Vector3 = Vector3(0, 1.5, 0)`: Offset from the target's origin to the pivot, for example head height.
- `yaw_degrees: float = 0.0`: Horizontal angle in degrees.
- `pitch_degrees: float = 20.0`: Vertical angle in degrees; positive looks down from above.
- `distance: float = 5.0`: Wanted distance from the pivot.
- `min_distance: float = 1.5`: Closest zoom.
- `max_distance: float = 12.0`: Farthest zoom.
- `min_pitch_degrees: float = -60.0`: Lowest pitch in degrees.
- `max_pitch_degrees: float = 75.0`: Highest pitch in degrees.
- `sensitivity: float = 0.25`: Degrees per pixel of captured mouse motion.
- `zoom_step: float = 0.5`: Distance change per mouse wheel notch.
- `smoothing: float = 12.0`: Exponential easing rate of the distance, per second.
- `collide: bool = true`: Pull the camera in front of geometry between it and the pivot.
- `collision_mask: int = 1` (@export_flags_3d_physics): Physics layers the collision ray tests.
- `collision_margin: float = 0.2`: Gap kept between the camera and a hit surface.
- `use_mouse: bool = true`: Orbit with captured mouse motion and zoom with the wheel.

### Methods

- `static orbit_offset(yaw: float, pitch: float, length: float) -> Vector3`: The offset from the pivot for `yaw` and `pitch` (radians) at `length`.
- `orbit(delta_yaw_degrees: float, delta_pitch_degrees: float) -> void`: Turns the orbit by the given degrees; pitch is clamped, yaw wraps into -180..180.
- `zoom(amount: float) -> void`: Changes the wanted distance by `amount`, clamped to the zoom limits.
- `get_target() -> Node3D`: The node being orbited, or null.
- `get_pivot() -> Vector3`: The world point the camera orbits and looks at.
- `get_current_distance() -> float`: The distance used at the last update (after collision and smoothing).
- `update_camera(delta: float) -> void`: Places the camera for this frame: limits, collision pull-in, smoothing and look-at.

## Usage

```gdscript
extends Node3D

@onready var orbit: BaltorOrbitCamera3D = $OrbitCamera


func _ready() -> void:
	orbit.target_path = orbit.get_path_to($Player)
	orbit.distance = 6.0
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/orbit_camera_3d/run_tests.gd -- res://baltor/godot_components/orbit_camera_3d/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

One ray from the pivot; thin gaps can still let the near plane clip into walls, so keep collision_margin above the camera's near distance. No auto-rotation behind the target and no lock-on. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
