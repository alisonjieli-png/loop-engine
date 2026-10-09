# Artificial potential field navigation

Navigate in 2D with an artificial potential field: goals attract with constant force, obstacles repel inside an influence radius, forces are analytic gradients, and a walker reports whether it reached the goal or stalled in a local minimum.

## How it works

An artificial potential field in 2D: goals attract, obstacles repel within an influence radius, and agents
move down the gradient.

An attractor at g with strength k adds k * |p - g| to the potential (a cone), whose force has constant size k
toward the goal. A repulsor at o with strength e and influence radius r adds e / 2 * (1 / d - 1 / r)^2 for
distances d < r (the classic obstacle potential), whose force grows without bound near the obstacle and is zero
beyond r. force_at() is the negative gradient, computed analytically. follow() takes fixed-length steps along
the force and stops at the goal radius, at a step limit, or when the force vanishes, which is how a local
minimum (an obstacle between agent and goal in a symmetric layout) shows up.

## When to use it

Use it for simple reactive navigation of drones, robots and swarming units, or as a teaching and debugging aid next to a global planner.

## Installation

Copy this folder to `res://baltor/godot_components/potential_field/` in a Godot 4.3 or later project. The script `potential_field.gd` declares the global class `BaltorPotentialField`, which extends `RefCounted`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Methods

- `add_attractor(point: Vector2, strength: float = 1.0) -> void`: Adds a goal at `point` pulling with constant `strength`.
- `add_repulsor(point: Vector2, strength: float, influence_radius: float) -> void`: Adds an obstacle at `point` pushing with `strength` inside `influence_radius`.
- `clear() -> void`: Removes every attractor and repulsor.
- `potential_at(point: Vector2) -> float`: The potential at `point`.
- `force_at(point: Vector2) -> Vector2`: The force (negative gradient of the potential) at `point`.
- `follow(start: Vector2, step_length: float, max_steps: int = 500, goal_radius: float = 1.0, min_force: float = 0.001) -> Dictionary`: Walks from `start` along the force in steps of `step_length`. Stops within `goal_radius` of any attractor, after `max_steps` steps, or where the force is weaker than `min_force`. Returns {"points": PackedVector2Array, "reached": bool}.

## Usage

```gdscript
extends Node2D

var field: BaltorPotentialField = BaltorPotentialField.new()


func _ready() -> void:
	field.add_attractor(Vector2(600, 300), 1.0)
	field.add_repulsor(Vector2(300, 320), 3000.0, 80.0)
	var walk: Dictionary = field.follow(Vector2(50, 300), 4.0, 400, 6.0)
	print("reached: %s in %d points" % [walk["reached"], (walk["points"] as PackedVector2Array).size()])
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/potential_field/run_tests.gd -- res://baltor/godot_components/potential_field/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Local method: it can stall in local minima, for example when an obstacle sits exactly between agent and goal; follow() reports that instead of hiding it. Point obstacles with a radius only. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
