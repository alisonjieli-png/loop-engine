# 2D platformer controller with coyote time and jump buffer

Move a CharacterBody2D like a platformer hero: jump height and time to apex set gravity, early release cuts the jump, coyote time and a jump buffer forgive late and early presses, and ground and air acceleration differ.

## How it works

Side-view platformer movement with coyote time, a jump buffer and variable jump height.

Gravity and jump speed come from two design values: the jump height in pixels and the time to reach it.
Rising uses gravity g = 2h / t^2 and the jump starts at v = -2h / t, so a held jump peaks at the chosen
height. Falling multiplies gravity by `fall_gravity_multiplier`. Releasing the jump button while rising
scales the upward speed by `jump_cut_multiplier` once, which gives a lower jump.
Coyote time keeps a jump available for a short while after walking off a ledge, and the jump buffer keeps a
jump press alive for a short while before landing. `step` holds all of this as a pure update of
`CharacterBody2D.velocity` from a floor flag, so it can be tested and reused without the physics
server; `_physics_process` calls it with `CharacterBody2D.is_on_floor` and then
`CharacterBody2D.move_and_slide`.

## When to use it

Use it as the movement core of a 2D platformer character when you want the jump to be tuned in pixels and seconds instead of raw gravity numbers. Turn off `use_input_actions` to drive it from AI or a replay.

## Installation

Copy this folder to `res://baltor/godot_components/platformer_controller_2d/` in a Godot 4.3 or later project. The script `platformer_controller_2d.gd` declares the global class `BaltorPlatformerController2D`, which extends `CharacterBody2D`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `jumped()`: Emitted when a jump starts.
- `landed(impact_speed: float)`: Emitted on the first frame on the floor after being airborne, with the downward speed before landing.

### Exported properties

- `move_speed: float = 220.0`: Top horizontal speed in pixels per second.
- `ground_acceleration: float = 1800.0`: Horizontal acceleration on the floor while a direction is held.
- `ground_deceleration: float = 2200.0`: Horizontal deceleration on the floor with no direction held.
- `air_acceleration: float = 1100.0`: Horizontal acceleration and deceleration in the air.
- `jump_height: float = 72.0`: Peak height of a held jump in pixels.
- `time_to_apex: float = 0.36`: Seconds from take-off to the peak of a held jump.
- `fall_gravity_multiplier: float = 1.6`: Gravity multiplier while falling.
- `jump_cut_multiplier: float = 0.45` (@export_range(0.0, 1.0)): Upward speed is multiplied by this once when the jump is released while rising.
- `max_fall_speed: float = 900.0`: Largest downward speed in pixels per second.
- `coyote_time: float = 0.1`: Seconds a jump stays available after leaving the floor without jumping.
- `jump_buffer_time: float = 0.12`: Seconds a jump press is remembered before landing.
- `use_input_actions: bool = true`: Read the actions below in _physics_process. Turn off to drive the body from code.
- `action_left: StringName = &"ui_left"`: Action that moves left.
- `action_right: StringName = &"ui_right"`: Action that moves right.
- `action_jump: StringName = &"ui_accept"`: Action that jumps.

### Methods

- `jump_velocity() -> float`: Upward take-off speed for `jump_height` and `time_to_apex` (negative: up is -y).
- `rise_gravity() -> float`: Gravity while rising, in pixels per second squared.
- `set_move_axis(axis: float) -> void`: Sets the horizontal input from -1 (left) to 1 (right). Values outside are clamped.
- `press_jump() -> void`: Presses jump: starts the buffer and marks the button as held.
- `release_jump() -> void`: Releases jump; a rising jump is cut on the next step.
- `can_jump(on_floor: bool) -> bool`: True while a jump would start now: on the floor or within coyote time.
- `step(delta: float, on_floor: bool) -> Vector2`: Advances the movement model by `delta` seconds with the given floor contact and returns the new velocity, which is also stored in `CharacterBody2D.velocity`.

## Usage

```gdscript
extends Node2D

@onready var player: BaltorPlatformerController2D = $Player


func _ready() -> void:
	player.jump_height = 96.0
	player.time_to_apex = 0.4
	player.landed.connect(_on_landed)


func _on_landed(impact_speed: float) -> void:
	if impact_speed > 600.0:
		print("hard landing")
```

## Example scene

`example.tscn` places the controller with a box collision shape above a static floor and a camera. It reads the default `ui_left`, `ui_right` and `ui_accept` actions.

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/platformer_controller_2d/run_tests.gd -- res://baltor/godot_components/platformer_controller_2d/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Side view with up as -y only; no slopes tuning, wall jumps, ladders or one-way platform drop-through. Gravity comes from the jump settings and ignores the project gravity setting. The apex height matches the design value up to the integration error of the physics step (about 2 percent at 120 Hz in the tests). Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
