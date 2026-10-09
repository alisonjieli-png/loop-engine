# Grid influence map for tactical AI

Stamp influence with distance falloff onto a grid, spread it around walls with decay and momentum, combine maps (friend minus foe) and query the strongest or weakest cell near a point.

## How it works

A grid influence map for tactical AI: sources stamp influence that falls off with distance, propagation spreads
and decays it through open cells, and queries find the strongest or weakest cell in an area.

The map is width x height cells of cell_size world units, stored row by row. stamp() adds strength at a center
cell, scaled down with the Euclidean cell distance up to a radius (linear, quadratic or constant falloff).
propagate() runs iterations of the classic spread rule: each open cell moves toward the strongest neighbor value
times exp(-decay * distance) (8 neighbors, diagonal distance sqrt(2)) by the momentum fraction, so influence
flows around walls but not through them. Two maps can be combined, for example friendly minus enemy influence
for a control map. Values are floats in a PackedFloat32Array.

## When to use it

Use it to let AI read the battlefield: where enemies are strong, which areas are contested, where to flank or retreat.

## Installation

Copy this folder to `res://baltor/godot_components/influence_map/` in a Godot 4.3 or later project. The script `influence_map.gd` declares the global class `BaltorInfluenceMap`, which extends `RefCounted`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Methods

- `get_width() -> int`: Number of columns.
- `get_height() -> int`: Number of rows.
- `has_cell(cell: Vector2i) -> bool`: True when `cell` lies inside the map.
- `set_blocked(cell: Vector2i, blocked: bool) -> bool`: Marks `cell` as a wall (no influence, blocks propagation) or open. Returns false outside the map.
- `is_blocked(cell: Vector2i) -> bool`: True when `cell` is a wall or outside the map.
- `get_value(cell: Vector2i) -> float`: The influence at `cell` (0.0 outside the map).
- `set_value(cell: Vector2i, value: float) -> bool`: Sets the influence at an open `cell`. Returns false for walls and cells outside the map.
- `clear() -> void`: Sets every value to zero (walls stay).
- `stamp(center: Vector2i, strength: float, radius: int, falloff: Falloff = Falloff.LINEAR) -> void`: Adds `strength` around `center` out to `radius` cells with the given falloff.
- `propagate(decay: float, momentum: float, iterations: int = 1) -> void`: Spreads influence `iterations` times: each open cell moves toward max(neighbor * exp(-decay * d)) by the `momentum` fraction (0 keeps the old value, 1 takes the neighbor value). Negative influence spreads by magnitude with its sign.
- `combine(other: BaltorInfluenceMap, factor: float = 1.0) -> bool`: Adds `other` times `factor` cell by cell. Returns false when the sizes differ.
- `best_cell(center: Vector2i, radius: int, highest: bool = true) -> Vector2i`: The open cell within `radius` of `center` with the highest value, or the lowest with `highest` false. Returns Vector2i(-1, -1) when no open cell is in range.
- `world_to_cell(point: Vector2) -> Vector2i`: The cell containing world point `point` (may lie outside the map).
- `cell_to_world(cell: Vector2i) -> Vector2`: The world position of the center of `cell`.
- `get_values() -> PackedFloat32Array`: A copy of every value, row by row.

### Enums

- `Falloff`: LINEAR, QUADRATIC, CONSTANT: How stamped influence falls off with distance from the center.

## Usage

```gdscript
extends Node2D

var enemy_map: BaltorInfluenceMap = BaltorInfluenceMap.new(40, 30, 32.0)


func refresh(enemy_positions: PackedVector2Array) -> void:
	enemy_map.clear()
	for point: Vector2 in enemy_positions:
		enemy_map.stamp(enemy_map.world_to_cell(point), 10.0, 4)
	enemy_map.propagate(0.4, 0.6, 2)


func safest_cell_near(point: Vector2) -> Vector2:
	var cell: Vector2i = enemy_map.best_cell(enemy_map.world_to_cell(point), 6, false)
	return enemy_map.cell_to_world(cell)
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/influence_map/run_tests.gd -- res://baltor/godot_components/influence_map/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Uniform grid in one layer per map; propagation is O(cells x iterations) in GDScript, so large maps should update over several frames or at a coarse resolution. Diagonal spread is blocked when either adjacent straight cell is a wall. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
