# Wall slide and wall jump helper for platformers

Cap the fall speed while a character presses into a wall, jump away from walls with a push, allow a short wall coyote time and lock input toward the wall briefly after the jump.

## How it works

Wall sliding and wall jumping for a side-view character: a capped fall speed while pressing into a wall, a jump
that pushes away from it, a short wall coyote time and an input lock after the jump.

Add the node to a character and call apply() every physics frame after the character's own velocity update and
before move_and_slide(), passing CharacterBody2D.is_on_wall_only(), is_on_floor() and get_wall_normal(). While
airborne, falling and pressing toward a wall, the downward speed is limited to `slide_speed`. A jump
request on a wall, or within `wall_coyote_time` after leaving one, sets the velocity to
(wall normal x * `jump_push`, -`jump_up`). For `control_lock_time` after a wall jump,
filter_input() returns 0 for input that points back toward the wall, so the jump arcs away instead of sticking.

## When to use it

Use it to add wall sliding and wall jumping to any 2D platformer controller, including the Baltor platformer controller.

## Installation

Copy this folder to `res://baltor/godot_components/wall_slide_jump_2d/` in a Godot 4.3 or later project. The script `wall_slide_jump_2d.gd` declares the global class `BaltorWallJump2D`, which extends `Node`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `wall_slide_started()`: Emitted when a wall slide begins.
- `wall_slide_ended()`: Emitted when a wall slide ends.
- `wall_jumped(direction: float)`: Emitted on a wall jump with the push direction (1 right, -1 left).

### Exported properties

- `slide_speed: float = 120.0`: Largest downward speed while sliding, in pixels per second.
- `jump_push: float = 260.0`: Horizontal speed of a wall jump away from the wall.
- `jump_up: float = 380.0`: Upward speed of a wall jump.
- `wall_coyote_time: float = 0.1`: Seconds after leaving a wall during which a wall jump still works.
- `control_lock_time: float = 0.18`: Seconds after a wall jump during which input toward that wall is ignored.

### Methods

- `apply(velocity: Vector2, on_wall: bool, on_floor: bool, wall_normal: Vector2, input_x: float, jump_pressed: bool, delta: float) -> Vector2`: Returns `velocity` adjusted for wall sliding and wall jumping this frame. `input_x` is the horizontal input (-1..1) and `jump_pressed` is true on the frame jump was pressed.
- `filter_input(input_x: float) -> float`: `input_x`, or 0 while the post-jump lock blocks input toward the wall just left.
- `is_sliding() -> bool`: True while sliding down a wall.
- `get_lock_time_left() -> float`: Seconds left of the post-jump input lock.

## Usage

```gdscript
extends CharacterBody2D

@onready var wall: BaltorWallJump2D = $WallJump


func _physics_process(delta: float) -> void:
	var axis: float = wall.filter_input(Input.get_axis("ui_left", "ui_right"))
	velocity.x = axis * 200.0
	velocity.y += 900.0 * delta
	velocity = wall.apply(velocity, is_on_wall_only(), is_on_floor(), get_wall_normal(), axis,
			Input.is_action_just_pressed("ui_accept"), delta)
	move_and_slide()
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/wall_slide_jump_2d/run_tests.gd -- res://baltor/godot_components/wall_slide_jump_2d/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

A helper called from your controller; it does not move the body or read input itself. Uses the wall normal's horizontal sign only, so sloped walls count as vertical. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
