# Waypoint moving platform that carries riders

Move an AnimatableBody2D through waypoint offsets at an exact speed, wait at each point, loop or ping-pong, and carry CharacterBody2D riders through the physics engine's platform sync.

## How it works

A platform that moves along waypoints at a constant speed, waits at each one, and loops or ping-pongs.

Waypoints are offsets from the position the platform has when it starts, so a scene can be placed anywhere.
In each physics frame the platform moves toward the next waypoint by `speed` * delta, carrying any
remaining distance over to the following segment so the speed stays exact through corners. At each waypoint it
waits `wait_time` seconds. After the last waypoint it either runs the list backward
(`ping_pong`) or continues to the first one. As an AnimatableBody2D with sync_to_physics on, it carries
CharacterBody2D riders that stand on it. With sync_to_physics the engine shows a new position only after the
physics server applies it, so the logical position is kept separately and read with get_current_point().

## When to use it

Use it for elevators, moving ledges and patrol platforms in 2D platformers without writing animation tracks.

## Installation

Copy this folder to `res://baltor/godot_components/moving_platform_path/` in a Godot 4.3 or later project. The script `moving_platform_path.gd` declares the global class `BaltorWaypointMover`, which extends `AnimatableBody2D`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `waypoint_reached(index: int)`: Emitted when the platform arrives at waypoint `index`.

### Exported properties

- `waypoints: PackedVector2Array = PackedVector2Array([Vector2.ZERO, Vector2(128, 0)])`: Offsets from the start position, in order.
- `speed: float = 80.0`: Speed in pixels per second.
- `wait_time: float = 0.5`: Seconds to wait at each waypoint.
- `ping_pong: bool = true`: Run back through the list instead of looping to the first waypoint.
- `auto_advance: bool = true`: Move in this node's own physics frames.

### Methods

- `advance(delta: float) -> Vector2`: Moves the platform by up to `delta` seconds of travel and returns the displacement.
- `get_current_point() -> Vector2`: The platform's logical position in the parent's coordinates (where it is or is about to be synced to).
- `get_target_index() -> int`: Index of the waypoint the platform is heading to.
- `is_waiting() -> bool`: True while waiting at a waypoint.
- `pause() -> void`: Stops moving until resume().
- `resume() -> void`: Continues after pause().
- `get_path_points() -> PackedVector2Array`: The waypoints in the parent's coordinates (the start position plus each offset).

## Usage

```gdscript
extends Node2D

@onready var platform: BaltorWaypointMover = $Platform


func _ready() -> void:
	platform.waypoints = PackedVector2Array([Vector2.ZERO, Vector2(0, -160)])
	platform.wait_time = 1.0
	platform.waypoint_reached.connect(func(index: int) -> void: print("arrived at %d" % index))
```

## Example scene

`example.tscn` runs a platform with a shape and a visual through three waypoints.

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/moving_platform_path/run_tests.gd -- res://baltor/godot_components/moving_platform_path/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Straight segments only (no curves or easing). With sync_to_physics on, the shown position follows the physics step, so read get_current_point() for the logical position between frames. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
