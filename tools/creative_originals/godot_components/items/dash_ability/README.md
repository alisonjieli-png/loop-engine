# Dash ability with charges and invulnerability frames

Dash at a fixed speed for a set time in a locked direction, spend and recharge charges one at a time, keep a fraction of the speed on exit and stay invulnerable for a window that can outlast the dash.

## How it works

A dash with a fixed speed and duration, charges that recharge one at a time, and an invulnerability window.

try_dash() spends a charge and locks a normalized direction for `dash_time` seconds; during that time
get_dash_velocity() returns direction * `dash_speed` for the owner to use instead of its normal
velocity. When the dash ends the owner can keep get_exit_velocity() (a fraction of the dash speed) so the
dash flows into running. Invulnerability starts with the dash and lasts `invulnerability_time`
seconds, which may be longer than the dash. Spent charges come back one at a time every
`recharge_time` seconds, starting when a dash begins. The node only keeps time: call advance() from
_physics_process or let it run in its own physics frames.

## When to use it

Use it for action games and roguelites with a dodge or air dash.

## Installation

Copy this folder to `res://baltor/godot_components/dash_ability/` in a Godot 4.3 or later project. The script `dash_ability.gd` declares the global class `BaltorDash`, which extends `Node`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `dash_started(direction: Vector2)`: Emitted when a dash begins.
- `dash_ended()`: Emitted when a dash ends or is cancelled.
- `charges_changed(charges: int)`: Emitted when the number of charges changes.

### Exported properties

- `dash_speed: float = 600.0`: Dash speed in pixels per second.
- `dash_time: float = 0.15`: Dash length in seconds.
- `max_charges: int = 1` (@export_range(1, 8)): Charges held when full.
- `recharge_time: float = 0.6`: Seconds to restore one charge.
- `invulnerability_time: float = 0.25`: Seconds of invulnerability from the start of a dash.
- `end_speed_factor: float = 0.3` (@export_range(0.0, 1.0)): Fraction of the dash speed returned by get_exit_velocity().
- `auto_advance: bool = true`: Advance timers in this node's own physics frames.

### Methods

- `try_dash(direction: Vector2) -> bool`: Starts a dash toward `direction`. Refused (false) with no charge, while dashing, or with a zero direction.
- `advance(delta: float) -> void`: Advances the dash, invulnerability and recharge timers by `delta` seconds.
- `cancel() -> void`: Ends a running dash at once.
- `is_dashing() -> bool`: True during a dash.
- `is_invulnerable() -> bool`: True while hits should be ignored.
- `get_dash_velocity() -> Vector2`: The velocity to use during a dash, or zero when not dashing.
- `get_exit_velocity() -> Vector2`: The velocity to keep after the dash: its direction times dash_speed times end_speed_factor.
- `get_charges() -> int`: Charges ready now.
- `get_recharge_progress() -> float`: Progress of the next charge from 0 to 1 (0 when full).

## Usage

```gdscript
extends CharacterBody2D

@onready var dash: BaltorDash = $Dash


func _physics_process(_delta: float) -> void:
	var input: Vector2 = Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	if Input.is_action_just_pressed("ui_accept"):
		dash.try_dash(input)
	velocity = dash.get_dash_velocity() if dash.is_dashing() else input * 180.0
	move_and_slide()


func take_hit(amount: int) -> void:
	if not dash.is_invulnerable():
		print("hit for %d" % amount)
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/dash_ability/run_tests.gd -- res://baltor/godot_components/dash_ability/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Keeps time and velocity only; the owner applies the velocity and checks is_invulnerable() when taking damage. 2D vectors. The dash does not stop at walls by itself; call cancel() on a collision if needed. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
