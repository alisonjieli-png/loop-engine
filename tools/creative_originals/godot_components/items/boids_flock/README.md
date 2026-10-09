# Boids flocking with a spatial hash

Simulate a 2D flock with separation, alignment and cohesion over neighbors found through a uniform spatial hash, with speed and force limits and optional wrapping bounds.

## How it works

A 2D boids flock: separation, alignment and cohesion over neighbors found with a spatial hash.

Each boid steers by the weighted sum of three rules computed over the boids within `neighbor_radius`:
separation pushes away from boids closer than `separation_radius` (weighted by inverse distance),
alignment steers toward the neighbors' average velocity, and cohesion seeks their average position. Each rule is
a desired velocity at `max_speed` minus the current velocity, and the sum is limited to
`max_force`. Neighbors come from a uniform grid of cells as large as the neighbor radius, so a step looks
at nearby cells only. With `bounds` set (non-zero size), boids wrap around its edges. All boids update
from the same snapshot, so the result does not depend on boid order.

## When to use it

Use it for birds, fish, swarms and crowds of small units that should move as a group.

## Installation

Copy this folder to `res://baltor/godot_components/boids_flock/` in a Godot 4.3 or later project. The script `boids_flock.gd` declares the global class `BaltorFlock`, which extends `RefCounted`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Properties

- `neighbor_radius: float`: Distance within which other boids count as neighbors.
- `separation_radius: float`: Distance below which separation applies.
- `separation_weight: float`: Weight of separation.
- `alignment_weight: float`: Weight of alignment.
- `cohesion_weight: float`: Weight of cohesion.
- `max_speed: float`: Top speed.
- `max_force: float`: Largest steering force (acceleration per second).
- `bounds: Rect2`: Area the boids wrap around in; a zero size disables wrapping.

### Methods

- `add_boid(position: Vector2, velocity: Vector2 = Vector2.ZERO) -> int`: Adds a boid and returns its index.
- `get_count() -> int`: Number of boids.
- `get_positions() -> PackedVector2Array`: A copy of every position.
- `get_velocities() -> PackedVector2Array`: A copy of every velocity.
- `neighbors_of(index: int) -> PackedInt32Array`: Indices of the boids within the neighbor radius of boid `index`, excluding itself, in index order.
- `steering_of(index: int) -> Vector2`: The steering of boid `index` from the three rules, before integration.
- `step(delta: float) -> void`: Moves every boid by `delta` seconds.

## Usage

```gdscript
extends Node2D

var flock: BaltorFlock = BaltorFlock.new()


func _ready() -> void:
	flock.bounds = Rect2(0, 0, 1152, 648)
	for index in range(80):
		flock.add_boid(Vector2(randf() * 1152.0, randf() * 648.0), Vector2.from_angle(randf() * TAU) * 60.0)


func _process(delta: float) -> void:
	flock.step(delta)
	queue_redraw()


func _draw() -> void:
	for point: Vector2 in flock.get_positions():
		draw_circle(point, 3.0, Color.WHITE)
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/boids_flock/run_tests.gd -- res://baltor/godot_components/boids_flock/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Positions and velocities live in the flock object; drawing them (for example with a MultiMeshInstance2D) is up to you. GDScript cost grows with neighbors per boid; hundreds of boids are practical, thousands need a compute approach. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
