# 2D follow camera with dead zone and look-ahead

Follow a target with a Camera2D that ignores motion inside a dead zone, leads in the direction of travel by up to a set distance and eases toward its goal with exponential smoothing.

## How it works

A 2D follow camera with a dead zone, velocity look-ahead and exponential smoothing.

The camera keeps a focus point. While the target stays inside a rectangle of `dead_zone` size around
the focus, the focus does not move, which avoids jitter for small motions; when the target leaves it, the focus
moves by exactly the overshoot (deadzone_follow()). The target's velocity, estimated from its movement between
updates, adds a look-ahead offset up to `look_ahead_distance` in the direction of travel, which eases in
and out at `look_ahead_speed`. The camera position then approaches focus plus look-ahead with exponential
smoothing at `follow_speed` per second.

## When to use it

Use it for platformers and top-down games where the camera should feel calm during small moves and show more of what lies ahead during fast ones.

## Installation

Copy this folder to `res://baltor/godot_components/camera_follow_deadzone/` in a Godot 4.3 or later project. The script `camera_follow_deadzone.gd` declares the global class `BaltorFollowCamera2D`, which extends `Camera2D`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Exported properties

- `target_path: NodePath = NodePath("")`: The node to follow.
- `dead_zone: Vector2 = Vector2(64, 48)`: Size of the dead zone in pixels.
- `look_ahead_distance: float = 80.0`: Largest look-ahead offset in pixels.
- `look_ahead_full_speed: float = 300.0`: Target speed in pixels per second that gives the full look-ahead.
- `look_ahead_speed: float = 3.0`: Exponential rate at which the look-ahead offset changes, per second.
- `follow_speed: float = 8.0`: Exponential rate at which the camera approaches its goal, per second.

### Methods

- `static deadzone_follow(focus: Vector2, target: Vector2, size: Vector2) -> Vector2`: The smallest move of `focus` that puts `target` inside a dead zone of `size` around it.
- `update_camera(target_position: Vector2, delta: float) -> void`: Moves the camera for a target at `target_position` after `delta` seconds.
- `snap_to(target_position: Vector2) -> void`: Puts the camera and its focus on `target_position` at once, with no look-ahead.
- `get_focus() -> Vector2`: The current focus point (the center of the dead zone).
- `get_look_ahead() -> Vector2`: The current look-ahead offset.

## Usage

```gdscript
extends Node2D

@onready var camera: BaltorFollowCamera2D = $Camera


func _ready() -> void:
	camera.target_path = camera.get_path_to($Player)
	camera.dead_zone = Vector2(120, 80)
	camera.make_current()


func respawn(at: Vector2) -> void:
	$Player.global_position = at
	camera.snap_to(at)
```

## Example scene

`example.tscn` holds a target marker and a follow camera pointing at it with a larger dead zone.

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/camera_follow_deadzone/run_tests.gd -- res://baltor/godot_components/camera_follow_deadzone/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Velocity comes from frame-to-frame position changes, so teleports produce a look-ahead spike; call snap_to() after teleporting. No room limits (see the room camera) and no shake. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
