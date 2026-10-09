# First-person controller with crouch, sprint and head bob

Drive a CharacterBody3D first-person player: mouse look with a pitch limit, walk, sprint and crouch speeds, jumping, head bob, and a crouch that refuses to stand up under a ceiling.

## How it works

First-person movement: mouse look with a pitch limit, walk, sprint and crouch speeds, jumping, head bob, and a
crouch that only stands up when there is room.

The body turns around Y for yaw; a head node (the child at `head_path`, created with a Camera3D when it
is missing) turns around X for pitch, clamped to `pitch_limit_degrees`. Movement input (x = strafe
right, y = forward) becomes a direction relative to the body's yaw. The horizontal velocity moves toward that
direction times the current speed by `ground_acceleration` per second on the floor and
`air_acceleration` in the air; gravity pulls down while airborne. Crouching moves the head toward
`crouch_head_height` at `crouch_transition_speed` and uses `crouch_speed`; standing up is
refused while a body test upward collides. Head bob moves the head on a sine path whose phase advances with
the horizontal distance walked, and fades out when the body stops or leaves the floor.

## When to use it

Use it as the starting point of a first-person game or walking simulator, then add weapons or interaction on top.

## Installation

Copy this folder to `res://baltor/godot_components/fps_controller_3d/` in a Godot 4.3 or later project. The script `fps_controller_3d.gd` declares the global class `BaltorFirstPersonController`, which extends `CharacterBody3D`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `jumped()`: Emitted when a jump starts.
- `landed(impact_speed: float)`: Emitted on the first floor frame after being airborne, with the downward speed before landing.
- `crouch_changed(crouching: bool)`: Emitted when the crouch state changes.

### Exported properties

- `mouse_sensitivity: float = 0.15`: Degrees of turn per pixel of mouse motion.
- `pitch_limit_degrees: float = 85.0`: Largest look angle above or below the horizon, in degrees.
- `walk_speed: float = 4.5`: Walking speed in meters per second.
- `sprint_speed: float = 7.5`: Sprinting speed in meters per second.
- `crouch_speed: float = 2.0`: Crouching speed in meters per second.
- `ground_acceleration: float = 40.0`: Horizontal speed change per second on the floor.
- `air_acceleration: float = 8.0`: Horizontal speed change per second in the air.
- `jump_velocity: float = 4.8`: Upward speed at take-off in meters per second.
- `gravity: float = 9.8`: Downward acceleration in meters per second squared.
- `stand_head_height: float = 1.6`: Head height above the body origin while standing.
- `crouch_head_height: float = 0.9`: Head height above the body origin while crouching.
- `crouch_transition_speed: float = 6.0`: Meters per second the head moves between the two heights.
- `bob_amplitude: float = 0.05`: Vertical head bob amplitude in meters.
- `bob_frequency: float = 0.6`: Head bob cycles per meter walked.
- `head_path: NodePath = NodePath("Head")`: The head node, relative to the body.
- `use_input_actions: bool = true`: Read the actions below and mouse motion. Turn off to drive the body from code.
- `action_forward: StringName = &"ui_up"`: Action that moves forward.
- `action_back: StringName = &"ui_down"`: Action that moves back.
- `action_left: StringName = &"ui_left"`: Action that strafes left.
- `action_right: StringName = &"ui_right"`: Action that strafes right.
- `action_jump: StringName = &"ui_accept"`: Action that jumps.

### Methods

- `look(relative: Vector2) -> void`: Turns by a mouse motion of `relative` pixels: x turns the body, y tilts the head within the limit.
- `get_pitch() -> float`: Head pitch in radians (positive looks up).
- `get_head() -> Node3D`: The head node (created on first use when missing).
- `set_move_input(input: Vector2) -> void`: Sets the movement input: x strafes right, y moves forward; clamped to length 1.
- `set_sprinting(sprinting: bool) -> void`: Turns sprinting on or off (ignored while crouching).
- `set_crouching(crouching: bool) -> bool`: Crouches or stands up. Standing up is refused (returns false) while there is no room above.
- `is_crouching() -> bool`: True while crouching.
- `press_jump() -> void`: Requests a jump for the next step; it only happens on the floor and not while crouching.
- `can_stand_up() -> bool`: True when a body test upward by the crouch height difference does not collide (always true outside a tree).
- `wish_direction() -> Vector3`: The horizontal world direction of the current input relative to the body's yaw.
- `current_speed() -> float`: The speed for the current state: crouch, sprint or walk.
- `get_head_height() -> float`: The current head height above the body origin, without bob.
- `get_bob_offset() -> Vector3`: The current head bob offset.
- `step(delta: float, on_floor: bool) -> Vector3`: Advances the movement model by `delta` seconds with the given floor contact and returns the velocity.

## Usage

```gdscript
extends Node3D

@onready var player: BaltorFirstPersonController = $Player


func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	player.landed.connect(_on_landed)


func _process(_delta: float) -> void:
	player.set_sprinting(Input.is_key_pressed(KEY_SHIFT))
	player.set_crouching(Input.is_key_pressed(KEY_CTRL))


func _on_landed(impact_speed: float) -> void:
	if impact_speed > 8.0:
		print("ouch")
```

## Example scene

`example.tscn` places the controller with a capsule, a Head node and a camera on a floor with a light.

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/fps_controller_3d/run_tests.gd -- res://baltor/godot_components/fps_controller_3d/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

No ladders, swimming, slopes speed changes or stairs stepping. The collision shape is not resized when crouching; only the head moves, and the stand-up test checks the space above the current shape. Mouse look runs only while the mouse is captured. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
