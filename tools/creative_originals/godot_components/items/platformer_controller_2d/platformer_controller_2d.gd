class_name BaltorPlatformerController2D
extends CharacterBody2D
## Side-view platformer movement with coyote time, a jump buffer and variable jump height.
##
## Gravity and jump speed come from two design values: the jump height in pixels and the time to reach it.
## Rising uses gravity g = 2h / t^2 and the jump starts at v = -2h / t, so a held jump peaks at the chosen
## height. Falling multiplies gravity by [member fall_gravity_multiplier]. Releasing the jump button while rising
## scales the upward speed by [member jump_cut_multiplier] once, which gives a lower jump.
## Coyote time keeps a jump available for a short while after walking off a ledge, and the jump buffer keeps a
## jump press alive for a short while before landing. [method step] holds all of this as a pure update of
## [member CharacterBody2D.velocity] from a floor flag, so it can be tested and reused without the physics
## server; [method _physics_process] calls it with [method CharacterBody2D.is_on_floor] and then
## [method CharacterBody2D.move_and_slide].

## Emitted when a jump starts.
signal jumped
## Emitted on the first frame on the floor after being airborne, with the downward speed before landing.
signal landed(impact_speed: float)

## Top horizontal speed in pixels per second.
@export var move_speed: float = 220.0
## Horizontal acceleration on the floor while a direction is held.
@export var ground_acceleration: float = 1800.0
## Horizontal deceleration on the floor with no direction held.
@export var ground_deceleration: float = 2200.0
## Horizontal acceleration and deceleration in the air.
@export var air_acceleration: float = 1100.0
## Peak height of a held jump in pixels.
@export var jump_height: float = 72.0
## Seconds from take-off to the peak of a held jump.
@export var time_to_apex: float = 0.36
## Gravity multiplier while falling.
@export var fall_gravity_multiplier: float = 1.6
## Upward speed is multiplied by this once when the jump is released while rising.
@export_range(0.0, 1.0) var jump_cut_multiplier: float = 0.45
## Largest downward speed in pixels per second.
@export var max_fall_speed: float = 900.0
## Seconds a jump stays available after leaving the floor without jumping.
@export var coyote_time: float = 0.1
## Seconds a jump press is remembered before landing.
@export var jump_buffer_time: float = 0.12
## Read the actions below in _physics_process. Turn off to drive the body from code.
@export var use_input_actions: bool = true
## Action that moves left.
@export var action_left: StringName = &"ui_left"
## Action that moves right.
@export var action_right: StringName = &"ui_right"
## Action that jumps.
@export var action_jump: StringName = &"ui_accept"

var _axis: float = 0.0
var _jump_held: bool = false
var _buffer_left: float = 0.0
var _coyote_left: float = 0.0
var _rising_from_jump: bool = false
var _was_on_floor: bool = true
var _air_speed: float = 0.0


func _physics_process(delta: float) -> void:
	if use_input_actions:
		_read_actions()
	step(delta, is_on_floor())
	move_and_slide()


## Upward take-off speed for [member jump_height] and [member time_to_apex] (negative: up is -y).
func jump_velocity() -> float:
	return -2.0 * jump_height / maxf(time_to_apex, 0.001)


## Gravity while rising, in pixels per second squared.
func rise_gravity() -> float:
	var apex: float = maxf(time_to_apex, 0.001)
	return 2.0 * jump_height / (apex * apex)


## Sets the horizontal input from -1 (left) to 1 (right). Values outside are clamped.
func set_move_axis(axis: float) -> void:
	_axis = clampf(axis, -1.0, 1.0)


## Presses jump: starts the buffer and marks the button as held.
func press_jump() -> void:
	_jump_held = true
	_buffer_left = jump_buffer_time


## Releases jump; a rising jump is cut on the next step.
func release_jump() -> void:
	_jump_held = false


## True while a jump would start now: on the floor or within coyote time.
func can_jump(on_floor: bool) -> bool:
	return on_floor or _coyote_left > 0.0


## Advances the movement model by [param delta] seconds with the given floor contact and returns the new
## velocity, which is also stored in [member CharacterBody2D.velocity].
func step(delta: float, on_floor: bool) -> Vector2:
	var moving: Vector2 = velocity
	if on_floor:
		if not _was_on_floor:
			landed.emit(_air_speed)
		_coyote_left = coyote_time
		_rising_from_jump = false
		moving.y = minf(moving.y, 0.0)
	var target: float = _axis * move_speed
	var rate: float = air_acceleration
	if on_floor:
		rate = ground_acceleration if absf(_axis) > 0.0 else ground_deceleration
	moving.x = move_toward(moving.x, target, rate * delta)
	if _buffer_left > 0.0 and can_jump(on_floor):
		moving.y = jump_velocity()
		_buffer_left = 0.0
		_coyote_left = 0.0
		_rising_from_jump = true
		jumped.emit()
	elif not on_floor:
		_coyote_left = maxf(_coyote_left - delta, 0.0)
	if _rising_from_jump and not _jump_held and moving.y < 0.0:
		moving.y *= jump_cut_multiplier
		_rising_from_jump = false
	if not on_floor:
		var gravity: float = rise_gravity()
		if moving.y > 0.0:
			gravity *= fall_gravity_multiplier
		moving.y = minf(moving.y + gravity * delta, max_fall_speed)
		_air_speed = maxf(moving.y, 0.0)
	_buffer_left = maxf(_buffer_left - delta, 0.0)
	_was_on_floor = on_floor
	velocity = moving
	return moving


func _read_actions() -> void:
	set_move_axis(Input.get_axis(action_left, action_right))
	if Input.is_action_just_pressed(action_jump):
		press_jump()
	elif not Input.is_action_pressed(action_jump):
		release_jump()
