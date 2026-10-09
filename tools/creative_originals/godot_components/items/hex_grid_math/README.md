# Hex grid math on axial coordinates

Compute hex grid distance, neighbors, rings, spirals, lines, rotations, pixel conversion for pointy-top and flat-top layouts, reachable areas and A* paths, all as static functions on Vector2i axial coordinates.

## How it works

Hexagon grid math on axial coordinates: distance, neighbors, rings, spirals, lines, rotation, pixel
conversion, reachable ranges and A* paths.

A hex is a Vector2i(q, r) in axial coordinates. The cube form is Vector3i(q, r, s) with q + r + s = 0, and the
distance between two hexes is the largest absolute cube difference. Lines sample the cube-space segment at
evenly spaced points and round each point to the nearest hex, after a small nudge so points on an edge round
the same way every time. Pixel conversion works for pointy-top and flat-top layouts of a given hex size (the
center-to-corner distance). Paths use A* with the hex distance as the heuristic, so they are shortest paths
when every step costs 1. All methods are static; nothing needs to be instanced.

## When to use it

Use it for board games, strategy maps and roguelikes on hexagons: moving units, drawing range highlights, picking the hex under the mouse and finding routes around obstacles.

## Installation

Copy this folder to `res://baltor/godot_components/hex_grid_math/` in a Godot 4.3 or later project. The script `hex_grid_math.gd` declares the global class `BaltorHexGrid`, which extends `RefCounted`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Methods

- `static axial_to_cube(hex: Vector2i) -> Vector3i`: The cube coordinates (q, r, s) of an axial hex.
- `static cube_to_axial(cube: Vector3i) -> Vector2i`: The axial coordinates of a cube hex (s is dropped).
- `static cube_round(cube: Vector3) -> Vector3i`: Rounds fractional cube coordinates to the nearest hex, fixing the component with the largest rounding error.
- `static distance(a: Vector2i, b: Vector2i) -> int`: Number of steps between two hexes.
- `static neighbor(hex: Vector2i, direction: int) -> Vector2i`: The neighbor of `hex` in direction 0 to 5 (wrapped).
- `static neighbors(hex: Vector2i) -> Array[Vector2i]`: The six neighbors of `hex` in direction order.
- `static ring(center: Vector2i, radius: int) -> Array[Vector2i]`: The hexes at exactly `radius` steps from `center`, walking once around the ring.
- `static spiral(center: Vector2i, radius: int) -> Array[Vector2i]`: Every hex within `radius` steps, ring by ring from the center outwards.
- `static line(a: Vector2i, b: Vector2i) -> Array[Vector2i]`: The hexes on the straight line from `a` to `b`, both included.
- `static rotate(hex: Vector2i, center: Vector2i, steps: int) -> Vector2i`: `hex` rotated by `steps` sixths of a turn counter-clockwise around `center`.
- `static to_pixel(hex: Vector2i, size: float, pointy_top: bool = true) -> Vector2`: The pixel position of the center of `hex` for hexes of `size` (center to corner).
- `static from_pixel(point: Vector2, size: float, pointy_top: bool = true) -> Vector2i`: The hex that contains `point` for hexes of `size`.
- `static corners(hex: Vector2i, size: float, pointy_top: bool = true) -> PackedVector2Array`: The six corner points of `hex`, for drawing with Polygon2D or Line2D.
- `static reachable(start: Vector2i, steps: int, is_passable: Callable) -> Array[Vector2i]`: Every hex reachable from `start` in at most `steps` moves through hexes for which `is_passable` (a Callable taking a Vector2i and returning bool) is true. The start is included.
- `static find_path(start: Vector2i, goal: Vector2i, is_passable: Callable, max_expanded: int = 4096) -> Array[Vector2i]`: A shortest path from `start` to `goal` (both included) through passable hexes, found with A*. Returns an empty array when the goal cannot be reached within `max_expanded` expanded hexes.

## Usage

```gdscript
extends Node2D

const HEX_SIZE: float = 32.0

var walls: Dictionary = {Vector2i(1, 0): true}


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		var target: Vector2i = BaltorHexGrid.from_pixel(get_local_mouse_position(), HEX_SIZE)
		var path: Array[Vector2i] = BaltorHexGrid.find_path(Vector2i.ZERO, target, _is_open)
		print("steps: %d" % (path.size() - 1))


func _is_open(hex: Vector2i) -> bool:
	return not walls.has(hex) and BaltorHexGrid.distance(Vector2i.ZERO, hex) <= 12
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/hex_grid_math/run_tests.gd -- res://baltor/godot_components/hex_grid_math/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Axial and cube coordinates only (offset coordinates must be converted by the caller). Paths assume every step costs 1; use a weighted search for terrain costs. find_path stops after max_expanded expanded hexes and returns an empty array, so an unbounded passable area needs a bound in is_passable. Pixel conversion has no origin offset or non-uniform scale. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
