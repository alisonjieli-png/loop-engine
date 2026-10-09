class_name BaltorWallJump2D
extends Node
## Wall sliding and wall jumping for a side-view character: a capped fall speed while pressing into a wall, a jump
## that pushes away from it, a short wall coyote time and an input lock after the jump.
##
## Add the node to a character and call apply() every physics frame after the character's own velocity update and
## before move_and_slide(), passing CharacterBody2D.is_on_wall_only(), is_on_floor() and get_wall_normal(). While
## airborne, falling and pressing toward a wall, the downward speed is limited to [member slide_speed]. A jump
## request on a wall, or within [member wall_coyote_time] after leaving one, sets the velocity to
## (wall normal x * [member jump_push], -[member jump_up]). For [member control_lock_time] after a wall jump,
## filter_input() returns 0 for input that points back toward the wall, so the jump arcs away instead of sticking.

## Emitted when a wall slide begins.
signal wall_slide_started
## Emitted when a wall slide ends.
signal wall_slide_ended
## Emitted on a wall jump with the push direction (1 right, -1 left).
signal wall_jumped(direction: float)

## Largest downward speed while sliding, in pixels per second.
@export var slide_speed: float = 120.0
## Horizontal speed of a wall jump away from the wall.
@export var jump_push: float = 260.0
## Upward speed of a wall jump.
@export var jump_up: float = 380.0
## Seconds after leaving a wall during which a wall jump still works.
@export var wall_coyote_time: float = 0.1
## Seconds after a wall jump during which input toward that wall is ignored.
@export var control_lock_time: float = 0.18

var _sliding: bool = false
var _wall_side: float = 0.0
var _coyote_left: float = 0.0
var _lock_left: float = 0.0


## Returns [param velocity] adjusted for wall sliding and wall jumping this frame. [param input_x] is the
## horizontal input (-1..1) and [param jump_pressed] is true on the frame jump was pressed.
func apply(velocity: Vector2, on_wall: bool, on_floor: bool, wall_normal: Vector2, input_x: float,
		jump_pressed: bool, delta: float) -> Vector2:
	var result: Vector2 = velocity
	_lock_left = maxf(_lock_left - delta, 0.0)
	_coyote_left = maxf(_coyote_left - delta, 0.0)
	var touching: bool = on_wall and not on_floor and absf(wall_normal.x) > 0.01
	if touching:
		_wall_side = signf(wall_normal.x)
		_coyote_left = wall_coyote_time
	var pressing_in: bool = touching and input_x * _wall_side < 0.0
	var sliding: bool = pressing_in and result.y > 0.0
	if sliding:
		result.y = minf(result.y, slide_speed)
	if jump_pressed and not on_floor and (touching or _coyote_left > 0.0) and _wall_side != 0.0:
		result = Vector2(_wall_side * jump_push, -jump_up)
		_lock_left = control_lock_time
		_coyote_left = 0.0
		sliding = false
		wall_jumped.emit(_wall_side)
	if on_floor:
		_coyote_left = 0.0
	_set_sliding(sliding)
	return result


## [param input_x], or 0 while the post-jump lock blocks input toward the wall just left.
func filter_input(input_x: float) -> float:
	if _lock_left > 0.0 and input_x * _wall_side < 0.0:
		return 0.0
	return input_x


## True while sliding down a wall.
func is_sliding() -> bool:
	return _sliding


## Seconds left of the post-jump input lock.
func get_lock_time_left() -> float:
	return _lock_left


func _set_sliding(sliding: bool) -> void:
	if sliding == _sliding:
		return
	_sliding = sliding
	if sliding:
		wall_slide_started.emit()
	else:
		wall_slide_ended.emit()
