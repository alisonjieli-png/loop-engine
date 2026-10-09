# Arcade glider flight model with stall

Fly a Node3D like a glider: a sink-rate polar with a best glide speed, speed traded against height, banked turns at the coordinated-turn rate, auto-levelling wings and a stall with nose drop and recovery.

## How it works

An arcade glider flight model: a sink-rate polar, speed traded against height, banked turns, auto-levelling
and a stall with nose drop and recovery.

The glider flies along its nose direction (yaw, pitch; forward is -Z at yaw 0) at its airspeed and also sinks.
The sink rate follows a polar with its minimum `min_sink_rate` at `best_glide_speed`:
sink(v) = min_sink * (v / best + best / v) / 2, so flying slower or faster sinks more. Airspeed changes by
-gravity * sin(pitch) per second (diving speeds up, climbing slows down) minus quadratic drag. Banking turns the
heading at the coordinated-turn rate gravity * tan(roll) / speed, and with no roll input the wings level
out. Below `stall_speed` the glider stalls: the nose falls toward `stall_dive_degrees` down and the
sink rate doubles until the speed recovers to 1.15 times the stall speed. Not a physical aerodynamics model.

## When to use it

Use it for gliding sections, paragliders, birds or wingsuits where the player manages speed and height instead of thrust.

## Installation

Copy this folder to `res://baltor/godot_components/glider_flight_3d/` in a Godot 4.3 or later project. The script `glider_flight_3d.gd` declares the global class `BaltorGlider`, which extends `Node3D`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `stalled()`: Emitted when the speed falls below the stall speed.
- `recovered()`: Emitted when the glider leaves the stall.

### Exported properties

- `start_speed: float = 12.0`: Airspeed at start, in meters per second.
- `best_glide_speed: float = 12.0`: Airspeed with the lowest sink rate.
- `min_sink_rate: float = 1.0`: Lowest sink rate in meters per second.
- `drag: float = 0.004`: Quadratic drag coefficient per meter.
- `stall_speed: float = 7.0`: Airspeed below which the glider stalls.
- `stall_dive_degrees: float = 35.0`: Nose-down pitch the stall falls toward, in degrees.
- `pitch_rate_degrees: float = 60.0`: Pitch change per second at full input, in degrees.
- `roll_rate_degrees: float = 90.0`: Roll change per second at full input, in degrees.
- `max_pitch_degrees: float = 45.0`: Largest pitch up or down, in degrees.
- `max_roll_degrees: float = 60.0`: Largest bank, in degrees.
- `level_rate_degrees: float = 45.0`: Roll returned toward level per second without roll input, in degrees.
- `gravity: float = 9.8`: Downward acceleration in meters per second squared.
- `use_input_actions: bool = true`: Read pitch from ui_up/ui_down and roll from ui_left/ui_right. Turn off to fly from code.

### Methods

- `set_controls(pitch_input: float, roll_input: float) -> void`: Sets pitch input (1 nose up) and roll input (1 bank right), each clamped to -1..1.
- `sink_rate(speed: float) -> float`: The polar sink rate at `speed`.
- `get_speed() -> float`: Current airspeed.
- `set_speed(speed: float) -> void`: Sets the airspeed (for launches and boosts).
- `get_heading_degrees() -> float`: Heading in degrees (0 = -Z, positive turns left as seen from above).
- `get_pitch_degrees() -> float`: Pitch in degrees (positive nose up).
- `get_roll_degrees() -> float`: Bank in degrees (positive right wing down).
- `is_stalled() -> bool`: True while stalled.
- `get_glide_ratio() -> float`: Horizontal distance per meter of height lost at the current speed (in level flight).
- `step(delta: float) -> Vector3`: Advances the flight model by `delta` seconds, updates the node's rotation and returns the world velocity.

## Usage

```gdscript
extends Node3D

@onready var glider: BaltorGlider = $Glider


func _ready() -> void:
	glider.stalled.connect(func() -> void: print("stall! push the nose down"))


func _process(_delta: float) -> void:
	$HUD/Speed.text = "%.0f m/s, glide %.0f:1" % [glider.get_speed(), glider.get_glide_ratio()]
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/glider_flight_3d/run_tests.gd -- res://baltor/godot_components/glider_flight_3d/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Arcade model, not physically based aerodynamics: no wind, thermals, collisions, angle of attack or side slip. Moves the node directly (not a physics body). Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
