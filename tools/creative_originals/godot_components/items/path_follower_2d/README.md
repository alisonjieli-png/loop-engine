# Path following steering on a polyline corridor

Keep a 2D agent inside a polyline corridor with predictive path following, and query the path: length, closest point, point at a distance and progress along it, for open and closed paths.

## How it works

Path following steering on a polyline with a radius, plus distance queries along the path.

The path is a list of points, open or closed, with a width given by `radius`. steer() predicts where the
agent will be after `lookahead` seconds, projects that point onto the path, and when the prediction lies
outside the radius it seeks a point a little further along the path than the projection; inside the radius it
returns zero and the agent keeps its course. The same projection gives the progress along the path, which is
useful for race positions and for spawning along routes. Distances wrap around on a closed path.

## When to use it

Use it for patrol routes, racing AI and escorts that should follow a drawn route smoothly rather than visiting waypoints one by one.

## Installation

Copy this folder to `res://baltor/godot_components/path_follower_2d/` in a Godot 4.3 or later project. The script `path_follower_2d.gd` declares the global class `BaltorPathFollower`, which extends `RefCounted`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Properties

- `radius: float`: Half width of the path corridor.

### Methods

- `set_points(points: PackedVector2Array, closed: bool = false) -> void`: Replaces the path. Needs at least two points to steer.
- `get_length() -> float`: Total length of the path (including the closing segment when closed).
- `closest_point(point: Vector2) -> Dictionary`: The closest point on the path to `point` as {"point", "distance_along", "segment", "distance_away"}.
- `point_at_distance(distance: float) -> Vector2`: The point at `distance` along the path (clamped on open paths, wrapped on closed ones).
- `steer(position: Vector2, velocity: Vector2, max_speed: float, lookahead: float = 0.5, ahead: float = 24.0) -> Vector2`: Steering that keeps an agent at `position` with `velocity` on the path. `ahead` is how far past the projection the target sits.
- `progress_of(point: Vector2) -> float`: How far along the path the projection of `point` is, from 0 to the length.

## Usage

```gdscript
extends Node2D

var route: BaltorPathFollower
var velocity: Vector2 = Vector2.ZERO


func _ready() -> void:
	route = BaltorPathFollower.new(PackedVector2Array([Vector2(0, 0), Vector2(300, 0), Vector2(300, 200)]), false, 12.0)


func _physics_process(delta: float) -> void:
	var force: Vector2 = route.steer(global_position, velocity, 90.0, 0.4)
	if velocity.length() < 1.0:
		force += Vector2.RIGHT * 90.0
	velocity = (velocity + force.limit_length(300.0) * delta).limit_length(90.0)
	global_position += velocity * delta
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/path_follower_2d/run_tests.gd -- res://baltor/godot_components/path_follower_2d/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Straight segments only; the closest-point search checks every segment, so very long paths cost more per query. An agent can swing wide of tight corners by about its turning radius. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
