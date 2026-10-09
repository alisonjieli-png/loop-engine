# Grid step movement with eased tweening and input buffer

Move a Node2D one grid cell at a time with an eased step, one buffered move, an optional blocked-cell check and signals for start, finish and bump. Use it for roguelikes, puzzles and classic tile RPGs.

## How it works

Cell-by-cell grid movement with smooth interpolation, one buffered move and a blocked-cell check.

The node lives on a grid of `cell_size` pixels with cell (0, 0) centered at `grid_origin`. A move
request starts a step to the neighboring cell that takes `step_time` seconds, with the position eased
(smoothstep) between the two cell centers. A request made during a step is buffered and starts as soon as the
step ends, so held or tapped input chains smoothly. Before every step the optional `blocked_check`
Callable receives the target cell and returns true to refuse it; a refused step emits bumped. Diagonal moves
are refused unless `allow_diagonal` is on. The logical cell changes when a step starts, so other
systems can reserve the target cell immediately.

## When to use it

Use it when the game logic is cell based but movement should still look smooth, and fast taps should chain steps without losing input.

## Installation

Copy this folder to `res://baltor/godot_components/grid_step_mover/` in a Godot 4.3 or later project. The script `grid_step_mover.gd` declares the global class `BaltorGridMover`, which extends `Node2D`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `step_started(from_cell: Vector2i, to_cell: Vector2i)`: Emitted when a step begins.
- `step_finished(cell: Vector2i)`: Emitted when a step ends on `cell`.
- `bumped(cell: Vector2i)`: Emitted when a move is refused because the target cell is blocked.

### Exported properties

- `cell_size: Vector2 = Vector2(16, 16)`: Size of a cell in pixels.
- `grid_origin: Vector2 = Vector2(8, 8)`: Position of the center of cell (0, 0).
- `step_time: float = 0.15`: Seconds per step.
- `allow_diagonal: bool = false`: Allow moves to the four diagonal neighbors.

### Properties

- `blocked_check: Callable`: Called with a target cell (Vector2i); return true to refuse the step.

### Methods

- `cell_to_position(cell: Vector2i) -> Vector2`: The world position of the center of `cell`.
- `position_to_cell(point: Vector2) -> Vector2i`: The cell whose area contains `point`.
- `get_cell() -> Vector2i`: The logical cell (the target cell while a step runs).
- `set_cell(cell: Vector2i) -> void`: Places the node on `cell` at once, cancelling any step and buffered move.
- `is_moving() -> bool`: True while a step is running.
- `try_move(direction: Vector2i) -> bool`: Requests a move by `direction` (a unit grid offset). Starts it now, or buffers it during a step. Returns false for a zero, too long or refused diagonal direction, or a blocked cell.
- `advance(delta: float) -> void`: Advances the running step by `delta` seconds; starts the buffered move when a step ends.

## Usage

```gdscript
extends Node2D

@onready var mover: BaltorGridMover = $Hero
var walls: Dictionary = {Vector2i(4, 2): true}


func _ready() -> void:
	mover.blocked_check = func(cell: Vector2i) -> bool: return walls.has(cell)
	mover.bumped.connect(func(cell: Vector2i) -> void: print("bumped into %s" % cell))


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_right"):
		mover.try_move(Vector2i.RIGHT)
	elif event.is_action_pressed("ui_left"):
		mover.try_move(Vector2i.LEFT)
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/grid_step_mover/run_tests.gd -- res://baltor/godot_components/grid_step_mover/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Moves only to neighbor cells; no path following (combine with a pathfinder). The blocked check runs when a step starts, not during it. Uses smoothstep easing only. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
