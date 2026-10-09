# Room-bounded 2D camera with eased transitions

Keep a 2D camera inside the room that contains the target, center it in rooms smaller than the view, and ease across with smoothstep when the target enters another room.

## How it works

Room-based camera limits for 2D: the camera stays inside the room that holds the target and eases across when
the target enters another room, as in exploration platformers.

Rooms are Rect2 areas in world space. Each update finds the room containing the target (keeping the current one
while the target stands where rooms overlap) and clamps the camera center so the view stays inside that room;
when the view is larger than the room on an axis, the camera centers on the room on that axis. On a room change
the camera moves from where it was to the new clamped position over `transition_time` seconds with
smoothstep easing, then follows normally. The view size is the viewport size divided by the camera zoom.

## When to use it

Use it for exploration platformers and top-down dungeons built from rooms, where the camera should never show past a room's walls.

## Installation

Copy this folder to `res://baltor/godot_components/camera_room_bounds/` in a Godot 4.3 or later project. The script `camera_room_bounds.gd` declares the global class `BaltorRoomCamera2D`, which extends `Node`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `room_changed(previous: int, current: int)`: Emitted when the target enters a different room (-1 means no room).

### Exported properties

- `camera_path: NodePath = NodePath("..")`: The Camera2D to move.
- `target_path: NodePath = NodePath("")`: The node the camera follows.
- `rooms: Array[Rect2] = []`: Rooms in world coordinates.
- `transition_time: float = 0.4`: Seconds of the eased move between rooms.

### Methods

- `add_room(area: Rect2) -> int`: Adds a room and returns its index.
- `room_at(point: Vector2) -> int`: Index of the room containing `point`, preferring the current room where rooms overlap; -1 when none.
- `static clamp_center(center: Vector2, view_size: Vector2, area: Rect2) -> Vector2`: `center` moved so a view of `view_size` stays inside `area`; centered on axes where the view is larger than the room.
- `update_center(camera_center: Vector2, target: Vector2, view_size: Vector2, delta: float) -> Vector2`: The camera center for this frame from the current `camera_center`, the `target` position and the `view_size`, after `delta` seconds.
- `get_current_room() -> int`: The current room index (-1 when the target is outside every room).
- `is_transitioning() -> bool`: True while easing between rooms.

## Usage

```gdscript
extends Node2D

@onready var rooms: BaltorRoomCamera2D = $Camera2D/Rooms


func _ready() -> void:
	rooms.target_path = rooms.get_path_to($Player)
	rooms.add_room(Rect2(0, 0, 1280, 720))
	rooms.add_room(Rect2(1280, 0, 640, 720))
	rooms.room_changed.connect(func(_previous: int, current: int) -> void: print("room %d" % current))
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/camera_room_bounds/run_tests.gd -- res://baltor/godot_components/camera_room_bounds/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Axis-aligned rectangular rooms only. Overlapping rooms keep the current room until the target leaves it. The view size comes from the viewport and the camera zoom. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
