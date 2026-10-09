class_name BaltorGlider
extends Node3D
## An arcade glider flight model: a sink-rate polar, speed traded against height, banked turns, auto-levelling
## and a stall with nose drop and recovery.
##
## The glider flies along its nose direction (yaw, pitch; forward is -Z at yaw 0) at its airspeed and also sinks.
## The sink rate follows a polar with its minimum [member min_sink_rate] at [member best_glide_speed]:
## sink(v) = min_sink * (v / best + best / v) / 2, so flying slower or faster sinks more. Airspeed changes by
## -gravity * sin(pitch) per second (diving speeds up, climbing slows down) minus quadratic drag. Banking turns the
## heading at the coordinated-turn rate gravity * tan(roll) / speed, and with no roll input the wings level
## out. Below [member stall_speed] the glider stalls: the nose falls toward [member stall_dive_degrees] down and the
## sink rate doubles until the speed recovers to 1.15 times the stall speed. Not a physical aerodynamics model.

## Emitted when the speed falls below the stall speed.
signal stalled
## Emitted when the glider leaves the stall.
signal recovered

## Airspeed at start, in meters per second.
@export var start_speed: float = 12.0
## Airspeed with the lowest sink rate.
@export var best_glide_speed: float = 12.0
## Lowest sink rate in meters per second.
@export var min_sink_rate: float = 1.0
## Quadratic drag coefficient per meter.
@export var drag: float = 0.004
## Airspeed below which the glider stalls.
@export var stall_speed: float = 7.0
## Nose-down pitch the stall falls toward, in degrees.
@export var stall_dive_degrees: float = 35.0
## Pitch change per second at full input, in degrees.
@export var pitch_rate_degrees: float = 60.0
## Roll change per second at full input, in degrees.
@export var roll_rate_degrees: float = 90.0
## Largest pitch up or down, in degrees.
@export var max_pitch_degrees: float = 45.0
## Largest bank, in degrees.
@export var max_roll_degrees: float = 60.0
## Roll returned toward level per second without roll input, in degrees.
@export var level_rate_degrees: float = 45.0
## Downward acceleration in meters per second squared.
@export var gravity: float = 9.8
## Read pitch from ui_up/ui_down and roll from ui_left/ui_right. Turn off to fly from code.
@export var use_input_actions: bool = true

var _speed: float = 12.0
var _yaw: float = 0.0
var _pitch: float = 0.0
var _roll: float = 0.0
var _pitch_input: float = 0.0
var _roll_input: float = 0.0
var _stalled: bool = false


func _ready() -> void:
	_speed = start_speed
	_yaw = rotation.y


func _physics_process(delta: float) -> void:
	if use_input_actions:
		set_controls(Input.get_axis(&"ui_down", &"ui_up"), Input.get_axis(&"ui_left", &"ui_right"))
	position += step(delta) * delta


## Sets pitch input (1 nose up) and roll input (1 bank right), each clamped to -1..1.
func set_controls(pitch_input: float, roll_input: float) -> void:
	_pitch_input = clampf(pitch_input, -1.0, 1.0)
	_roll_input = clampf(roll_input, -1.0, 1.0)


## The polar sink rate at [param speed].
func sink_rate(speed: float) -> float:
	var v: float = maxf(speed, 0.1)
	return min_sink_rate * (v / best_glide_speed + best_glide_speed / v) * 0.5


## Current airspeed.
func get_speed() -> float:
	return _speed


## Sets the airspeed (for launches and boosts).
func set_speed(speed: float) -> void:
	_speed = maxf(speed, 0.0)


## Heading in degrees (0 = -Z, positive turns left as seen from above).
func get_heading_degrees() -> float:
	return rad_to_deg(_yaw)


## Pitch in degrees (positive nose up).
func get_pitch_degrees() -> float:
	return rad_to_deg(_pitch)


## Bank in degrees (positive right wing down).
func get_roll_degrees() -> float:
	return rad_to_deg(_roll)


## True while stalled.
func is_stalled() -> bool:
	return _stalled


## Horizontal distance per meter of height lost at the current speed (in level flight).
func get_glide_ratio() -> float:
	return _speed / maxf(sink_rate(_speed), 0.0001)


## Advances the flight model by [param delta] seconds, updates the node's rotation and returns the world velocity.
func step(delta: float) -> Vector3:
	var max_pitch: float = deg_to_rad(max_pitch_degrees)
	if _stalled:
		_pitch = move_toward(_pitch, -deg_to_rad(stall_dive_degrees), deg_to_rad(pitch_rate_degrees) * delta)
	else:
		_pitch = clampf(_pitch + _pitch_input * deg_to_rad(pitch_rate_degrees) * delta, -max_pitch, max_pitch)
	if absf(_roll_input) > 0.0:
		var max_roll: float = deg_to_rad(max_roll_degrees)
		_roll = clampf(_roll + _roll_input * deg_to_rad(roll_rate_degrees) * delta, -max_roll, max_roll)
	else:
		_roll = move_toward(_roll, 0.0, deg_to_rad(level_rate_degrees) * delta)
	_speed = maxf(_speed - (gravity * sin(_pitch) + drag * _speed * _speed) * delta, 0.0)
	_yaw -= gravity * tan(_roll) / maxf(_speed, 1.0) * delta
	if not _stalled and _speed < stall_speed:
		_stalled = true
		stalled.emit()
	elif _stalled and _speed > stall_speed * 1.15:
		_stalled = false
		recovered.emit()
	rotation = Vector3(_pitch, _yaw, -_roll)
	var forward: Vector3 = Basis.from_euler(Vector3(_pitch, _yaw, 0.0)) * Vector3.FORWARD
	var sink: float = sink_rate(_speed) * (2.0 if _stalled else 1.0)
	return forward * _speed + Vector3.DOWN * sink
