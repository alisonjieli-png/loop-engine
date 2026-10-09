# Rail camera that rides a Path3D

Move a Camera3D along a Path3D rail to the point closest to its target, with an optional lead, clamping at the rail ends, smooth travel and a constant look at the target.

## How it works

A camera that rides a Path3D rail: it stays at the rail point closest to its target, optionally leads ahead
along the rail, eases along it and always looks at the target.

Each update projects the target onto the rail with Curve3D.get_closest_offset() in the path's local space,
adds `lead_distance` along the rail, clamps the result to the rail length, and moves the current rail
offset toward it with exponential smoothing at `follow_speed` per second. The camera sits at that rail
point and looks at the target plus `look_offset`. Typical uses are side-scrolling 3D levels,
corridors and cinematic dolly shots that must never leave a designed track.

## When to use it

Use it for 2.5D side-scrollers, corridor shooters and cinematic shots where the camera must stay on a designed track while following the action.

## Installation

Copy this folder to `res://baltor/godot_components/rail_camera_3d/` in a Godot 4.3 or later project. The script `rail_camera_3d.gd` declares the global class `BaltorRailCamera3D`, which extends `Camera3D`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Exported properties

- `path_node: NodePath = NodePath("")`: The Path3D to ride.
- `target_path: NodePath = NodePath("")`: The node to watch.
- `lead_distance: float = 0.0`: Distance along the rail added in front of the projected target.
- `follow_speed: float = 5.0`: Exponential easing rate of the rail offset, per second; 0 jumps.
- `look_offset: Vector3 = Vector3(0, 1, 0)`: Offset from the target's origin to the point looked at.

### Methods

- `get_rail() -> Path3D`: The rail Path3D, or null.
- `rail_offset_for(world_point: Vector3) -> float`: The rail offset for a target at `world_point`: the closest offset plus the lead, clamped to the rail.
- `rail_point(offset: float) -> Vector3`: The world position of the rail at `offset`.
- `get_rail_offset() -> float`: The current offset along the rail.
- `update_camera(target_position: Vector3, delta: float) -> void`: Moves along the rail toward the point for a target at `target_position` and looks at it.

## Usage

```gdscript
extends Node3D

@onready var rail_camera: BaltorRailCamera3D = $RailCamera


func _ready() -> void:
	rail_camera.path_node = rail_camera.get_path_to($Rail)
	rail_camera.target_path = rail_camera.get_path_to($Player)
	rail_camera.lead_distance = 2.0
	rail_camera.make_current()
```

## Example scene

`example.tscn` has a straight Path3D rail, a box target and the rail camera with a small lead.

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/rail_camera_3d/run_tests.gd -- res://baltor/godot_components/rail_camera_3d/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Closest-point projection can jump when a rail folds back near itself; keep rails gently curved. The camera does not avoid geometry between it and the target. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
