# Top-down eight-way movement with acceleration and friction

Move a CharacterBody2D in eight directions with acceleration, friction, a reversal boost, optional d-pad snapping and a facing sector index for animation.

## How it works

Top-down eight-way movement with acceleration, friction, a reversal boost and facing for animation.

The input direction is clamped to length 1, so diagonals are not faster. While a direction is held the velocity
moves toward direction * `max_speed` by `acceleration` per second, multiplied by
`turn_boost` when the input points against the current velocity, which makes quick reversals feel tight.
With no input the velocity falls toward zero by `friction` per second. With
`snap_eight_directions` the input is rounded to the nearest of eight directions, as on a d-pad.
The last non-zero input is kept as the facing, and get_facing_index() turns it into a sector index for
animation (0 = right, then clockwise on screen: down-right, down, down-left, left, up-left, up, up-right).
step() holds the velocity model; _physics_process reads input, calls it and moves with move_and_slide().

## When to use it

Use it for top-down action, twin-stick and RPG characters that should start, stop and turn with weight instead of snapping to full speed.

## Installation

Copy this folder to `res://baltor/godot_components/top_down_movement_2d/` in a Godot 4.3 or later project. The script `top_down_movement_2d.gd` declares the global class `BaltorTopDownMover2D`, which extends `CharacterBody2D`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `facing_changed(direction: Vector2)`: Emitted when the facing direction changes.

### Exported properties

- `max_speed: float = 200.0`: Top speed in pixels per second.
- `acceleration: float = 1400.0`: Speed gained per second while input is held.
- `friction: float = 1600.0`: Speed lost per second with no input.
- `turn_boost: float = 2.0`: Acceleration multiplier when the input points against the velocity.
- `snap_eight_directions: bool = false`: Round input to the nearest of eight directions.
- `use_input_actions: bool = true`: Read the actions below in _physics_process. Turn off to drive the body from code.
- `action_left: StringName = &"ui_left"`: Action that moves left.
- `action_right: StringName = &"ui_right"`: Action that moves right.
- `action_up: StringName = &"ui_up"`: Action that moves up.
- `action_down: StringName = &"ui_down"`: Action that moves down.

### Methods

- `set_input(direction: Vector2) -> void`: Sets the movement input; it is clamped to length 1 (and snapped when enabled).
- `get_input() -> Vector2`: The current (clamped, snapped) input.
- `get_facing() -> Vector2`: The last non-zero input direction, normalized; right before any input.
- `get_facing_index(sectors: int = 8) -> int`: The facing as a sector index out of `sectors` (0 = right, increasing clockwise on screen).
- `step(delta: float) -> Vector2`: Advances the velocity model by `delta` seconds and returns the new velocity.

## Usage

```gdscript
extends Node2D

@onready var player: BaltorTopDownMover2D = $Player
@onready var sprite: AnimatedSprite2D = $Player/Sprite


func _ready() -> void:
	player.facing_changed.connect(_on_facing_changed)


func _on_facing_changed(_direction: Vector2) -> void:
	sprite.frame = player.get_facing_index(8)
```

## Example scene

`example.tscn` holds the mover with a circle shape in Floating motion mode and eight-way snapping on, reading the default ui actions.

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/top_down_movement_2d/run_tests.gd -- res://baltor/godot_components/top_down_movement_2d/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Set the body's motion_mode to Floating for top-down games (the example scene does). No dodge, knockback or terrain speed modifiers; combine with the dash and knockback components. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
