# Grid flow field for many units with terrain costs

Build a Dijkstra flow field from one or more goal cells over a grid with terrain costs and walls, then read a direction per cell so any number of units can share one search.

## How it works

A grid flow field: one Dijkstra pass from the goal cells gives every cell its travel cost to the nearest goal
and a direction to follow, so any number of units can share one search.

Each cell has a crossing cost: 1 by default, higher for slow terrain, 0 or less for walls. A step out of a cell
toward the goal costs that cell's cost, times sqrt(2) for a diagonal step. build() runs Dijkstra from all goal
cells at once over 8 neighbors, and a diagonal step may not cut past a wall corner. direction_at() points from a cell toward its cheapest neighbor, so a
unit only reads the vector under it each frame. Cells that cannot reach a goal have infinite distance and a
zero direction.

## When to use it

Use it for RTS and tower defense games where many units head to the same goals.

## Installation

Copy this folder to `res://baltor/godot_components/flow_field_grid/` in a Godot 4.3 or later project. The script `flow_field_grid.gd` declares the global class `BaltorFlowField`, which extends `RefCounted`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Methods

- `has_cell(cell: Vector2i) -> bool`: True when `cell` is inside the grid.
- `set_cost(cell: Vector2i, cost: float) -> bool`: Sets the crossing cost of `cell`; 0 or less makes it a wall. Returns false outside the grid.
- `get_cost(cell: Vector2i) -> float`: The crossing cost of `cell` (0 outside the grid).
- `build(goals: Array[Vector2i]) -> int`: Computes distances and directions toward the nearest of `goals`. Returns the number of reachable cells.
- `get_distance(cell: Vector2i) -> float`: Travel cost from `cell` to the nearest goal (INF when unreachable or outside).
- `direction_at(cell: Vector2i) -> Vector2`: The unit direction to follow from `cell` (zero at a goal, on walls and where no goal is reachable).
- `sample(point: Vector2) -> Vector2`: The direction under world position `point`.
- `world_to_cell(point: Vector2) -> Vector2i`: The cell under world position `point`.
- `trace(cell: Vector2i, max_steps: int = 4096) -> Array[Vector2i]`: The cell sequence a unit at `cell` follows to the goal, both ends included (empty if unreachable).

## Usage

```gdscript
extends Node2D

var field: BaltorFlowField = BaltorFlowField.new(40, 25, 32.0)


func _ready() -> void:
	field.set_cost(Vector2i(10, 5), 0.0)
	field.set_cost(Vector2i(11, 5), 4.0)
	var goals: Array[Vector2i] = [Vector2i(39, 12)]
	field.build(goals)


func direction_for(unit_position: Vector2) -> Vector2:
	return field.sample(unit_position)
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/flow_field_grid/run_tests.gd -- res://baltor/godot_components/flow_field_grid/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Grid-based with 8 neighbors and no corner cutting; directions point to the next cell center, so units should blend them for smooth motion. Rebuilding costs O(cells log cells) in GDScript. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
