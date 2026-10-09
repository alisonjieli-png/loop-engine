class_name BaltorWaypointMover
extends AnimatableBody2D
## A platform that moves along waypoints at a constant speed, waits at each one, and loops or ping-pongs.
##
## Waypoints are offsets from the position the platform has when it starts, so a scene can be placed anywhere.
## In each physics frame the platform moves toward the next waypoint by [member speed] * delta, carrying any
## remaining distance over to the following segment so the speed stays exact through corners. At each waypoint it
## waits [member wait_time] seconds. After the last waypoint it either runs the list backward
## ([member ping_pong]) or continues to the first one. As an AnimatableBody2D with sync_to_physics on, it carries
## CharacterBody2D riders that stand on it. With sync_to_physics the engine shows a new position only after the
## physics server applies it, so the logical position is kept separately and read with get_current_point().

## Emitted when the platform arrives at waypoint [param index].
signal waypoint_reached(index: int)

## Offsets from the start position, in order.
@export var waypoints: PackedVector2Array = PackedVector2Array([Vector2.ZERO, Vector2(128, 0)])
## Speed in pixels per second.
@export var speed: float = 80.0
## Seconds to wait at each waypoint.
@export var wait_time: float = 0.5
## Run back through the list instead of looping to the first waypoint.
@export var ping_pong: bool = true
## Move in this node's own physics frames.
@export var auto_advance: bool = true

var _origin: Vector2 = Vector2.ZERO
var _point: Vector2 = Vector2.ZERO
var _started: bool = false
var _target: int = 1
var _direction: int = 1
var _wait_left: float = 0.0
var _paused: bool = false


func _physics_process(delta: float) -> void:
	if auto_advance:
		advance(delta)


## Moves the platform by up to [param delta] seconds of travel and returns the displacement.
func advance(delta: float) -> Vector2:
	if not _started:
		_origin = position
		_point = position
		_started = true
		_target = 1 if waypoints.size() > 1 else 0
	if _paused or waypoints.size() < 2 or speed <= 0.0:
		return Vector2.ZERO
	var before: Vector2 = _point
	var time_left: float = delta
	var guard: int = 0
	while time_left > 0.0 and guard < 64:
		guard += 1
		if _wait_left > 0.0:
			var waited: float = minf(_wait_left, time_left)
			_wait_left -= waited
			time_left -= waited
			continue
		var goal: Vector2 = _origin + waypoints[_target]
		var distance: float = _point.distance_to(goal)
		var travel: float = speed * time_left
		if travel < distance:
			_point = _point.move_toward(goal, travel)
			time_left = 0.0
		else:
			_point = goal
			time_left -= distance / speed
			waypoint_reached.emit(_target)
			_wait_left = wait_time
			_pick_next()
	position = _point
	return _point - before


## The platform's logical position in the parent's coordinates (where it is or is about to be synced to).
func get_current_point() -> Vector2:
	return _point if _started else position


## Index of the waypoint the platform is heading to.
func get_target_index() -> int:
	return _target


## True while waiting at a waypoint.
func is_waiting() -> bool:
	return _wait_left > 0.0


## Stops moving until resume().
func pause() -> void:
	_paused = true


## Continues after pause().
func resume() -> void:
	_paused = false


## The waypoints in the parent's coordinates (the start position plus each offset).
func get_path_points() -> PackedVector2Array:
	var base: Vector2 = _origin if _started else position
	var points := PackedVector2Array()
	for offset: Vector2 in waypoints:
		points.append(base + offset)
	return points


func _pick_next() -> void:
	var last: int = waypoints.size() - 1
	if ping_pong:
		if _target + _direction > last or _target + _direction < 0:
			_direction = -_direction
		_target += _direction
	else:
		_target = (_target + 1) % waypoints.size()
