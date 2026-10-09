# Knockback with weight, exponential decay and stun

Add knockback from hits divided by weight, fade it with exponential friction, and stun in proportion to the hit strength with a cap, so heavy enemies barely move and light ones fly.

## How it works

Knockback that adds up, fades with exponential friction and stuns in proportion to its strength.

apply_knockback() adds direction * strength / `weight` to the knockback velocity, so heavier objects are
pushed less. advance() multiplies the velocity by exp(-`friction` * delta) and snaps it to zero below
`min_speed`. Each hit also stuns for strength / weight * `stun_per_unit` seconds, up to
`max_stun`; a stronger hit replaces a weaker remaining stun, a weaker one never shortens it. The owner
adds get_velocity() to its own movement and ignores input while is_stunned() is true.

## When to use it

Use it for brawlers, platformers and top-down action games where hits push characters around.

## Installation

Copy this folder to `res://baltor/godot_components/knockback_receiver/` in a Godot 4.3 or later project. The script `knockback_receiver.gd` declares the global class `BaltorKnockback`, which extends `Node`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `knocked(velocity: Vector2)`: Emitted for each hit with the knockback velocity after it.
- `stun_ended()`: Emitted when the stun runs out.

### Exported properties

- `weight: float = 1.0`: Divides incoming knockback; 2 halves it.
- `friction: float = 8.0`: Exponential decay rate of the knockback per second.
- `min_speed: float = 5.0`: Speeds below this snap to zero.
- `stun_per_unit: float = 0.002`: Seconds of stun per unit of knockback speed.
- `max_stun: float = 0.6`: Longest stun in seconds.
- `auto_advance: bool = true`: Advance in this node's own physics frames.

### Methods

- `apply_knockback(direction: Vector2, strength: float) -> void`: Adds a hit of `strength` toward `direction`. Ignored for a zero direction or strength at or below 0.
- `advance(delta: float) -> Vector2`: Decays the knockback and the stun by `delta` seconds and returns the knockback velocity.
- `get_velocity() -> Vector2`: The current knockback velocity.
- `is_stunned() -> bool`: True while stunned.
- `get_stun_left() -> float`: Seconds of stun left.
- `clear() -> void`: Removes all knockback and stun at once.

## Usage

```gdscript
extends CharacterBody2D

@onready var knockback: BaltorKnockback = $Knockback


func on_hit(from: Vector2, strength: float) -> void:
	knockback.apply_knockback(global_position - from, strength)


func _physics_process(_delta: float) -> void:
	var input: Vector2 = Vector2.ZERO
	if not knockback.is_stunned():
		input = Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	velocity = input * 150.0 + knockback.get_velocity()
	move_and_slide()
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/knockback_receiver/run_tests.gd -- res://baltor/godot_components/knockback_receiver/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Owner-driven: it computes a velocity to add and does not move anything. 2D vectors. The stun is a timer only; animations and AI pauses are up to the owner. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
