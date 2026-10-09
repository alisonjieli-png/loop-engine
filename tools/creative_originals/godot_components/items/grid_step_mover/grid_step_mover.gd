class_name BaltorGridMover
extends Node2D
## Cell-by-cell grid movement with smooth interpolation, one buffered move and a blocked-cell check.
##
## The node lives on a grid of [member cell_size] pixels with cell (0, 0) centered at [member grid_origin]. A move
## request starts a step to the neighboring cell that takes [member step_time] seconds, with the position eased
## (smoothstep) between the two cell centers. A request made during a step is buffered and starts as soon as the
## step ends, so held or tapped input chains smoothly. Before every step the optional [member blocked_check]
## Callable receives the target cell and returns true to refuse it; a refused step emits bumped. Diagonal moves
## are refused unless [member allow_diagonal] is on. The logical cell changes when a step starts, so other
## systems can reserve the target cell immediately.

## Emitted when a step begins.
signal step_started(from_cell: Vector2i, to_cell: Vector2i)
## Emitted when a step ends on [param cell].
signal step_finished(cell: Vector2i)
## Emitted when a move is refused because the target cell is blocked.
signal bumped(cell: Vector2i)

## Size of a cell in pixels.
@export var cell_size: Vector2 = Vector2(16, 16)
## Position of the center of cell (0, 0).
@export var grid_origin: Vector2 = Vector2(8, 8)
## Seconds per step.
@export var step_time: float = 0.15
## Allow moves to the four diagonal neighbors.
@export var allow_diagonal: bool = false

## Called with a target cell (Vector2i); return true to refuse the step.
var blocked_check: Callable = Callable()

var _cell: Vector2i = Vector2i.ZERO
var _from: Vector2 = Vector2.ZERO
var _to: Vector2 = Vector2.ZERO
var _elapsed: float = 0.0
var _moving: bool = false
var _buffered: Vector2i = Vector2i.ZERO


func _process(delta: float) -> void:
	advance(delta)


## The world position of the center of [param cell].
func cell_to_position(cell: Vector2i) -> Vector2:
	return grid_origin + Vector2(cell) * cell_size


## The cell whose area contains [param point].
func position_to_cell(point: Vector2) -> Vector2i:
	var local: Vector2 = (point - grid_origin) / cell_size
	return Vector2i(roundi(local.x), roundi(local.y))


## The logical cell (the target cell while a step runs).
func get_cell() -> Vector2i:
	return _cell


## Places the node on [param cell] at once, cancelling any step and buffered move.
func set_cell(cell: Vector2i) -> void:
	_cell = cell
	_moving = false
	_buffered = Vector2i.ZERO
	position = cell_to_position(cell)


## True while a step is running.
func is_moving() -> bool:
	return _moving


## Requests a move by [param direction] (a unit grid offset). Starts it now, or buffers it during a step.
## Returns false for a zero, too long or refused diagonal direction, or a blocked cell.
func try_move(direction: Vector2i) -> bool:
	if direction == Vector2i.ZERO or absi(direction.x) > 1 or absi(direction.y) > 1:
		return false
	if not allow_diagonal and direction.x != 0 and direction.y != 0:
		return false
	if _moving:
		_buffered = direction
		return true
	return _start(direction)


## Advances the running step by [param delta] seconds; starts the buffered move when a step ends.
func advance(delta: float) -> void:
	if not _moving:
		return
	_elapsed += delta
	var t: float = 1.0 if step_time <= 0.0 else clampf(_elapsed / step_time, 0.0, 1.0)
	position = _from.lerp(_to, t * t * (3.0 - 2.0 * t))
	if t < 1.0:
		return
	_moving = false
	step_finished.emit(_cell)
	if _buffered != Vector2i.ZERO:
		var next: Vector2i = _buffered
		_buffered = Vector2i.ZERO
		_start(next)


func _start(direction: Vector2i) -> bool:
	var target: Vector2i = _cell + direction
	if blocked_check.is_valid() and bool(blocked_check.call(target)):
		bumped.emit(target)
		return false
	var previous: Vector2i = _cell
	_cell = target
	_from = cell_to_position(previous)
	_to = cell_to_position(target)
	_elapsed = 0.0
	_moving = true
	step_started.emit(previous, target)
	return true
