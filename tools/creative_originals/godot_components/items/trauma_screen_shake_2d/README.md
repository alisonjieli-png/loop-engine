# Trauma screen shake for Camera2D

Shake a Camera2D from a decaying trauma value: the shake is trauma to a power, and smooth seeded noise moves the offset and roll within set limits. The camera returns to its original offset and rotation when the shake ends.

## How it works

Trauma-based screen shake for a Camera2D, driven by smooth noise.

Trauma is a value from 0 to 1 that events add to and that decays linearly over time. The visible shake is
trauma raised to `exponent`, so small hits stay subtle and large hits stand out. Each frame the camera's
offset and rotation move by up to `max_offset` and `max_roll_degrees` times the shake. The
displacement comes from a FastNoiseLite sampled at the elapsed time times `frequency`, with one noise
row each for x, y and roll, so the motion is smooth and repeats exactly for the same `noise_seed`. When
trauma reaches zero the camera returns to the offset and rotation it had when the shake started.

## When to use it

Use it for hits, explosions and landings where you want a shake that adds up across events and fades out smoothly instead of a random jitter per frame.

## Installation

Copy this folder to `res://baltor/godot_components/trauma_screen_shake_2d/` in a Godot 4.3 or later project. The script `trauma_screen_shake_2d.gd` declares the global class `BaltorTraumaShake2D`, which extends `Node`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `shake_started()`: Emitted when trauma rises above zero from rest.
- `shake_finished()`: Emitted when trauma returns to zero and the camera is restored.

### Exported properties

- `target_path: NodePath = NodePath("..")`: The Camera2D to shake; by default the parent.
- `max_offset: Vector2 = Vector2(24, 16)`: Largest offset in pixels at full shake.
- `max_roll_degrees: float = 4.0`: Largest roll in degrees at full shake.
- `decay_per_second: float = 0.9`: Trauma lost per second.
- `exponent: float = 2.0` (@export_range(1.0, 4.0)): Shake = trauma ^ exponent.
- `frequency: float = 18.0`: Noise samples per second; higher shakes faster.
- `noise_seed: int = 7`: Seed of the noise; the same seed gives the same motion.

### Methods

- `add_trauma(amount: float) -> void`: Adds `amount` to the trauma (clamped to 0..1). Negative amounts reduce it.
- `set_trauma(value: float) -> void`: Sets the trauma (clamped to 0..1), starting or finishing the shake as needed.
- `get_trauma() -> float`: Current trauma from 0 to 1.
- `get_shake() -> float`: Current shake strength: trauma ^ exponent.
- `offset_at(time: float) -> Vector2`: The camera offset displacement at `time` seconds for the current shake.
- `roll_at(time: float) -> float`: The roll in radians at `time` seconds for the current shake.
- `get_target_camera() -> Camera2D`: The Camera2D at `target_path`, or null.
- `advance(delta: float) -> void`: Advances the shake by `delta` seconds: trauma decays and the camera moves. Called every frame.

## Usage

```gdscript
extends Node2D

@onready var shake: BaltorTraumaShake2D = $Camera2D/TraumaShake


func on_explosion(strength: float) -> void:
	shake.add_trauma(clampf(strength, 0.0, 1.0))
```

## Example scene

`example.tscn` attaches the shake node to a Camera2D with a larger offset limit and its own seed. Call `add_trauma` on it to see the camera move.

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/trauma_screen_shake_2d/run_tests.gd -- res://baltor/godot_components/trauma_screen_shake_2d/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

2D cameras only; it writes Camera2D.offset and rotation, so another script writing them at the same time fights it. Noise values are clamped to -1..1; FastNoiseLite simplex output rarely reaches the ends, so the full offset is seldom reached. The motion repeats for a seed on this engine build; the noise library may differ between engine versions. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
