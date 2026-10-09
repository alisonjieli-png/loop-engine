class_name BaltorFollowCamera2D
extends Camera2D
## A 2D follow camera with a dead zone, velocity look-ahead and exponential smoothing.
##
## The camera keeps a focus point. While the target stays inside a rectangle of [member dead_zone] size around
## the focus, the focus does not move, which avoids jitter for small motions; when the target leaves it, the focus
## moves by exactly the overshoot (deadzone_follow()). The target's velocity, estimated from its movement between
## updates, adds a look-ahead offset up to [member look_ahead_distance] in the direction of travel, which eases in
## and out at [member look_ahead_speed]. The camera position then approaches focus plus look-ahead with exponential
## smoothing at [member follow_speed] per second.

## The node to follow.
@export var target_path: NodePath = NodePath("")
## Size of the dead zone in pixels.
@export var dead_zone: Vector2 = Vector2(64, 48)
## Largest look-ahead offset in pixels.
@export var look_ahead_distance: float = 80.0
## Target speed in pixels per second that gives the full look-ahead.
@export var look_ahead_full_speed: float = 300.0
## Exponential rate at which the look-ahead offset changes, per second.
@export var look_ahead_speed: float = 3.0
## Exponential rate at which the camera approaches its goal, per second.
@export var follow_speed: float = 8.0

var _focus: Vector2 = Vector2.ZERO
var _look_ahead: Vector2 = Vector2.ZERO
var _last_target: Vector2 = Vector2.ZERO
var _has_last: bool = false


func _process(delta: float) -> void:
	var target := get_node_or_null(target_path) as Node2D if not target_path.is_empty() else null
	if target != null:
		update_camera(target.global_position, delta)


## The smallest move of [param focus] that puts [param target] inside a dead zone of [param size] around it.
static func deadzone_follow(focus: Vector2, target: Vector2, size: Vector2) -> Vector2:
	var half: Vector2 = size * 0.5
	var moved: Vector2 = focus
	if target.x > focus.x + half.x:
		moved.x = target.x - half.x
	elif target.x < focus.x - half.x:
		moved.x = target.x + half.x
	if target.y > focus.y + half.y:
		moved.y = target.y - half.y
	elif target.y < focus.y - half.y:
		moved.y = target.y + half.y
	return moved


## Moves the camera for a target at [param target_position] after [param delta] seconds.
func update_camera(target_position: Vector2, delta: float) -> void:
	if not _has_last:
		snap_to(target_position)
		return
	var velocity: Vector2 = (target_position - _last_target) / maxf(delta, 0.0001)
	_last_target = target_position
	_focus = deadzone_follow(_focus, target_position, dead_zone)
	var wanted: Vector2 = Vector2.ZERO
	if velocity.length() > 1.0:
		wanted = velocity.normalized() * look_ahead_distance * clampf(velocity.length() / look_ahead_full_speed, 0.0, 1.0)
	_look_ahead = _look_ahead.lerp(wanted, 1.0 - exp(-look_ahead_speed * delta))
	global_position = global_position.lerp(_focus + _look_ahead, 1.0 - exp(-follow_speed * delta))


## Puts the camera and its focus on [param target_position] at once, with no look-ahead.
func snap_to(target_position: Vector2) -> void:
	_focus = target_position
	_look_ahead = Vector2.ZERO
	_last_target = target_position
	_has_last = true
	global_position = target_position


## The current focus point (the center of the dead zone).
func get_focus() -> Vector2:
	return _focus


## The current look-ahead offset.
func get_look_ahead() -> Vector2:
	return _look_ahead
