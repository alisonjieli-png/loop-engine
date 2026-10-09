class_name BaltorTopDownMover2D
extends CharacterBody2D
## Top-down eight-way movement with acceleration, friction, a reversal boost and facing for animation.
##
## The input direction is clamped to length 1, so diagonals are not faster. While a direction is held the velocity
## moves toward direction * [member max_speed] by [member acceleration] per second, multiplied by
## [member turn_boost] when the input points against the current velocity, which makes quick reversals feel tight.
## With no input the velocity falls toward zero by [member friction] per second. With
## [member snap_eight_directions] the input is rounded to the nearest of eight directions, as on a d-pad.
## The last non-zero input is kept as the facing, and get_facing_index() turns it into a sector index for
## animation (0 = right, then clockwise on screen: down-right, down, down-left, left, up-left, up, up-right).
## step() holds the velocity model; _physics_process reads input, calls it and moves with move_and_slide().

## Emitted when the facing direction changes.
signal facing_changed(direction: Vector2)

## Top speed in pixels per second.
@export var max_speed: float = 200.0
## Speed gained per second while input is held.
@export var acceleration: float = 1400.0
## Speed lost per second with no input.
@export var friction: float = 1600.0
## Acceleration multiplier when the input points against the velocity.
@export var turn_boost: float = 2.0
## Round input to the nearest of eight directions.
@export var snap_eight_directions: bool = false
## Read the actions below in _physics_process. Turn off to drive the body from code.
@export var use_input_actions: bool = true
## Action that moves left.
@export var action_left: StringName = &"ui_left"
## Action that moves right.
@export var action_right: StringName = &"ui_right"
## Action that moves up.
@export var action_up: StringName = &"ui_up"
## Action that moves down.
@export var action_down: StringName = &"ui_down"

var _input: Vector2 = Vector2.ZERO
var _facing: Vector2 = Vector2.RIGHT


func _physics_process(delta: float) -> void:
	if use_input_actions:
		set_input(Input.get_vector(action_left, action_right, action_up, action_down))
	step(delta)
	move_and_slide()


## Sets the movement input; it is clamped to length 1 (and snapped when enabled).
func set_input(direction: Vector2) -> void:
	var clamped: Vector2 = direction.limit_length(1.0)
	if snap_eight_directions and clamped.length_squared() > 0.0001:
		var sector: float = TAU / 8.0
		clamped = Vector2.from_angle(roundf(clamped.angle() / sector) * sector) * clamped.length()
	_input = clamped
	if clamped.length_squared() > 0.0001:
		var heading: Vector2 = clamped.normalized()
		if not heading.is_equal_approx(_facing):
			_facing = heading
			facing_changed.emit(heading)


## The current (clamped, snapped) input.
func get_input() -> Vector2:
	return _input


## The last non-zero input direction, normalized; right before any input.
func get_facing() -> Vector2:
	return _facing


## The facing as a sector index out of [param sectors] (0 = right, increasing clockwise on screen).
func get_facing_index(sectors: int = 8) -> int:
	var count: int = maxi(sectors, 1)
	return posmod(roundi(_facing.angle() / (TAU / count)), count)


## Advances the velocity model by [param delta] seconds and returns the new velocity.
func step(delta: float) -> Vector2:
	if _input.length_squared() > 0.0001:
		var target: Vector2 = _input * max_speed
		var rate: float = acceleration
		if velocity.dot(target) < 0.0:
			rate *= turn_boost
		velocity = velocity.move_toward(target, rate * delta)
	else:
		velocity = velocity.move_toward(Vector2.ZERO, friction * delta)
	return velocity
