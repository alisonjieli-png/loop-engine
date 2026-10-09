class_name BaltorDash
extends Node
## A dash with a fixed speed and duration, charges that recharge one at a time, and an invulnerability window.
##
## try_dash() spends a charge and locks a normalized direction for [member dash_time] seconds; during that time
## get_dash_velocity() returns direction * [member dash_speed] for the owner to use instead of its normal
## velocity. When the dash ends the owner can keep get_exit_velocity() (a fraction of the dash speed) so the
## dash flows into running. Invulnerability starts with the dash and lasts [member invulnerability_time]
## seconds, which may be longer than the dash. Spent charges come back one at a time every
## [member recharge_time] seconds, starting when a dash begins. The node only keeps time: call advance() from
## _physics_process or let it run in its own physics frames.

## Emitted when a dash begins.
signal dash_started(direction: Vector2)
## Emitted when a dash ends or is cancelled.
signal dash_ended
## Emitted when the number of charges changes.
signal charges_changed(charges: int)

## Dash speed in pixels per second.
@export var dash_speed: float = 600.0
## Dash length in seconds.
@export var dash_time: float = 0.15
## Charges held when full.
@export_range(1, 8) var max_charges: int = 1
## Seconds to restore one charge.
@export var recharge_time: float = 0.6
## Seconds of invulnerability from the start of a dash.
@export var invulnerability_time: float = 0.25
## Fraction of the dash speed returned by get_exit_velocity().
@export_range(0.0, 1.0) var end_speed_factor: float = 0.3
## Advance timers in this node's own physics frames.
@export var auto_advance: bool = true

var _charges: int = 1
var _direction: Vector2 = Vector2.ZERO
var _dash_left: float = 0.0
var _invulnerable_left: float = 0.0
var _recharge_elapsed: float = 0.0


func _ready() -> void:
	_charges = max_charges


func _physics_process(delta: float) -> void:
	if auto_advance:
		advance(delta)


## Starts a dash toward [param direction]. Refused (false) with no charge, while dashing, or with a zero direction.
func try_dash(direction: Vector2) -> bool:
	if _charges <= 0 or _dash_left > 0.0 or direction.length_squared() < 0.000001:
		return false
	_direction = direction.normalized()
	_dash_left = dash_time
	_invulnerable_left = maxf(_invulnerable_left, invulnerability_time)
	if _charges == max_charges:
		_recharge_elapsed = 0.0
	_set_charges(_charges - 1)
	dash_started.emit(_direction)
	return true


## Advances the dash, invulnerability and recharge timers by [param delta] seconds.
func advance(delta: float) -> void:
	if _dash_left > 0.0:
		_dash_left = maxf(_dash_left - delta, 0.0)
		if _dash_left == 0.0:
			dash_ended.emit()
	_invulnerable_left = maxf(_invulnerable_left - delta, 0.0)
	if _charges < max_charges:
		_recharge_elapsed += delta
		while _recharge_elapsed >= recharge_time and _charges < max_charges:
			_recharge_elapsed -= recharge_time
			_set_charges(_charges + 1)
		if _charges == max_charges:
			_recharge_elapsed = 0.0


## Ends a running dash at once.
func cancel() -> void:
	if _dash_left > 0.0:
		_dash_left = 0.0
		dash_ended.emit()


## True during a dash.
func is_dashing() -> bool:
	return _dash_left > 0.0


## True while hits should be ignored.
func is_invulnerable() -> bool:
	return _invulnerable_left > 0.0


## The velocity to use during a dash, or zero when not dashing.
func get_dash_velocity() -> Vector2:
	return _direction * dash_speed if _dash_left > 0.0 else Vector2.ZERO


## The velocity to keep after the dash: its direction times dash_speed times end_speed_factor.
func get_exit_velocity() -> Vector2:
	return _direction * dash_speed * end_speed_factor


## Charges ready now.
func get_charges() -> int:
	return _charges


## Progress of the next charge from 0 to 1 (0 when full).
func get_recharge_progress() -> float:
	if _charges >= max_charges or recharge_time <= 0.0:
		return 0.0
	return clampf(_recharge_elapsed / recharge_time, 0.0, 1.0)


func _set_charges(value: int) -> void:
	if value != _charges:
		_charges = value
		charges_changed.emit(value)
