# Steering behaviors: seek, flee, arrive, pursue, evade, wander

Compute Reynolds-style steering forces for 2D agents (seek, flee with a panic distance, arrive with a slowing radius, pursue and evade with prediction, seeded wander) and integrate a point mass with force and speed limits.

## How it works

Classic steering behaviors for 2D agents: seek, flee, arrive, pursue, evade and wander, plus a point-mass
integrator with force and speed limits.

Each behavior returns a steering force: the desired velocity minus the current velocity, as in Reynolds'
steering model. Seek wants full speed toward a point; flee wants full speed away within a panic distance;
arrive slows down linearly inside a slowing radius and stops on the point; pursue and evade seek or flee the
position a moving target will have after the time it takes to cover the distance at full speed (capped by
max_prediction). Wander keeps an angle on a circle projected ahead of the agent and jitters it each step with a
seeded random generator, so paths are smooth and repeatable. integrate() applies a force with a mass, caps the
force and the speed, and returns the new position and velocity.

## When to use it

Use it for enemies, animals, drones and crowds that should move with momentum toward or away from targets instead of snapping to paths.

## Installation

Copy this folder to `res://baltor/godot_components/steering_behaviors_2d/` in a Godot 4.3 or later project. The script `steering_behaviors_2d.gd` declares the global class `BaltorSteering`, which extends `RefCounted`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Properties

- `wander_distance: float`: Distance of the wander circle in front of the agent.
- `wander_radius: float`: Radius of the wander circle.
- `wander_jitter: float`: Largest change of the wander angle per call, in radians.

### Methods

- `static seek(position: Vector2, velocity: Vector2, target: Vector2, max_speed: float) -> Vector2`: Steering toward `target` at full speed.
- `static flee(position: Vector2, velocity: Vector2, threat: Vector2, max_speed: float, panic_distance: float = INF) -> Vector2`: Steering away from `threat` at full speed while it is closer than `panic_distance`; zero beyond.
- `static arrive(position: Vector2, velocity: Vector2, target: Vector2, max_speed: float, slowing_radius: float) -> Vector2`: Steering that reaches `target` and slows down inside `slowing_radius`.
- `static pursue(position: Vector2, velocity: Vector2, target_position: Vector2, target_velocity: Vector2, max_speed: float, max_prediction: float = 1.0) -> Vector2`: Seek toward where a target moving at `target_velocity` will be.
- `static evade(position: Vector2, velocity: Vector2, threat_position: Vector2, threat_velocity: Vector2, max_speed: float, max_prediction: float = 1.0) -> Vector2`: Flee from where a threat moving at `threat_velocity` will be.
- `static truncate(force: Vector2, max_length: float) -> Vector2`: `force` shortened to at most `max_length`.
- `static integrate(position: Vector2, velocity: Vector2, steering: Vector2, max_force: float, max_speed: float, mass: float, delta: float) -> Dictionary`: Applies `steering` to a point mass and returns {"position", "velocity"} after `delta` seconds.
- `wander(velocity: Vector2, max_speed: float) -> Vector2`: A wandering steering force for an agent moving with `velocity`; the circle sits ahead of it.
- `get_wander_angle() -> float`: The current wander angle relative to the heading, in radians.

## Usage

```gdscript
extends Node2D

var velocity: Vector2 = Vector2.ZERO
var brain: BaltorSteering = BaltorSteering.new(42)


func _physics_process(delta: float) -> void:
	var target: Vector2 = get_global_mouse_position()
	var force: Vector2 = BaltorSteering.arrive(global_position, velocity, target, 200.0, 120.0)
	force += brain.wander(velocity, 200.0) * 0.2
	var state: Dictionary = BaltorSteering.integrate(global_position, velocity, force, 600.0, 200.0, 1.0, delta)
	global_position = state["position"]
	velocity = state["velocity"]
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/steering_behaviors_2d/run_tests.gd -- res://baltor/godot_components/steering_behaviors_2d/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Point-mass model in 2D; no obstacle handling (see obstacle avoidance) and no orientation smoothing. Arrive is an underdamped approach and can overshoot slightly before settling. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
