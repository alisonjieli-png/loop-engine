# Obstacle avoidance steering among circle obstacles

Steer a 2D agent around circle obstacles with a detection corridor ahead of it: find the closest threat, push sideways away from it and brake, harder when closer, with a repeatable choice for dead-ahead obstacles.

## How it works

Obstacle avoidance steering for 2D agents among circle obstacles, with a detection corridor ahead of the agent.

Obstacles are Vector3(center x, center y, radius). The agent looks along its velocity over a corridor
`look_ahead` long and as wide as its own radius on each side. Among the obstacles that intersect the
corridor, the closest one ahead is avoided: the steering pushes sideways away from that obstacle's center, more
strongly the closer it is, and brakes a little in proportion to the same closeness. When the obstacle sits
exactly on the path line the agent turns to its right-hand side (screen coordinates), so the choice is
repeatable. ray_circle() is the underlying ray test.

## When to use it

Use it with seek or path following so agents slip around rocks, pillars and other units.

## Installation

Copy this folder to `res://baltor/godot_components/obstacle_avoidance_2d/` in a Godot 4.3 or later project. The script `obstacle_avoidance_2d.gd` declares the global class `BaltorObstacleAvoidance`, which extends `RefCounted`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Methods

- `static ray_circle(origin: Vector2, direction: Vector2, center: Vector2, radius: float) -> float`: Distance along a unit `direction` from `origin` to the first point of the circle, 0 when the origin is inside it, or -1 when the ray misses.
- `static find_threat(position: Vector2, velocity: Vector2, obstacles: PackedVector3Array, agent_radius: float, look_ahead: float) -> int`: The index of the closest obstacle inside the corridor ahead, or -1.
- `static avoid(position: Vector2, velocity: Vector2, obstacles: PackedVector3Array, agent_radius: float, look_ahead: float, max_force: float) -> Vector2`: The avoidance steering force, limited to `max_force`; zero when nothing is in the corridor.

## Usage

```gdscript
extends Node2D

var velocity: Vector2 = Vector2(80, 0)
var rocks: PackedVector3Array = PackedVector3Array([Vector3(200, 10, 24), Vector3(320, -30, 18)])


func _physics_process(delta: float) -> void:
	var steering: Vector2 = BaltorObstacleAvoidance.avoid(global_position, velocity, rocks, 8.0, 100.0, 300.0)
	steering += (Vector2(600, 0) - global_position).normalized() * 80.0 - velocity
	velocity = (velocity + steering.limit_length(300.0) * delta).limit_length(80.0)
	global_position += velocity * delta
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/obstacle_avoidance_2d/run_tests.gd -- res://baltor/godot_components/obstacle_avoidance_2d/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Circle obstacles only, given as Vector3(x, y, radius); walls and polygons need another method. Avoids one obstacle at a time, so dense clusters can still trap an agent. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
