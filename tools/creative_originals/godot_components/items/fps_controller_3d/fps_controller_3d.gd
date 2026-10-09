class_name BaltorFirstPersonController
extends CharacterBody3D
## First-person movement: mouse look with a pitch limit, walk, sprint and crouch speeds, jumping, head bob, and a
## crouch that only stands up when there is room.
##
## The body turns around Y for yaw; a head node (the child at [member head_path], created with a Camera3D when it
## is missing) turns around X for pitch, clamped to [member pitch_limit_degrees]. Movement input (x = strafe
## right, y = forward) becomes a direction relative to the body's yaw. The horizontal velocity moves toward that
## direction times the current speed by [member ground_acceleration] per second on the floor and
## [member air_acceleration] in the air; gravity pulls down while airborne. Crouching moves the head toward
## [member crouch_head_height] at [member crouch_transition_speed] and uses [member crouch_speed]; standing up is
## refused while a body test upward collides. Head bob moves the head on a sine path whose phase advances with
## the horizontal distance walked, and fades out when the body stops or leaves the floor.

## Emitted when a jump starts.
signal jumped
## Emitted on the first floor frame after being airborne, with the downward speed before landing.
signal landed(impact_speed: float)
## Emitted when the crouch state changes.
signal crouch_changed(crouching: bool)

## Degrees of turn per pixel of mouse motion.
@export var mouse_sensitivity: float = 0.15
## Largest look angle above or below the horizon, in degrees.
@export var pitch_limit_degrees: float = 85.0
## Walking speed in meters per second.
@export var walk_speed: float = 4.5
## Sprinting speed in meters per second.
@export var sprint_speed: float = 7.5
## Crouching speed in meters per second.
@export var crouch_speed: float = 2.0
## Horizontal speed change per second on the floor.
@export var ground_acceleration: float = 40.0
## Horizontal speed change per second in the air.
@export var air_acceleration: float = 8.0
## Upward speed at take-off in meters per second.
@export var jump_velocity: float = 4.8
## Downward acceleration in meters per second squared.
@export var gravity: float = 9.8
## Head height above the body origin while standing.
@export var stand_head_height: float = 1.6
## Head height above the body origin while crouching.
@export var crouch_head_height: float = 0.9
## Meters per second the head moves between the two heights.
@export var crouch_transition_speed: float = 6.0
## Vertical head bob amplitude in meters.
@export var bob_amplitude: float = 0.05
## Head bob cycles per meter walked.
@export var bob_frequency: float = 0.6
## The head node, relative to the body.
@export var head_path: NodePath = NodePath("Head")
## Read the actions below and mouse motion. Turn off to drive the body from code.
@export var use_input_actions: bool = true
## Action that moves forward.
@export var action_forward: StringName = &"ui_up"
## Action that moves back.
@export var action_back: StringName = &"ui_down"
## Action that strafes left.
@export var action_left: StringName = &"ui_left"
## Action that strafes right.
@export var action_right: StringName = &"ui_right"
## Action that jumps.
@export var action_jump: StringName = &"ui_accept"

var _head: Node3D = null
var _move: Vector2 = Vector2.ZERO
var _sprinting: bool = false
var _crouching: bool = false
var _jump_requested: bool = false
var _head_height: float = 1.6
var _bob_phase: float = 0.0
var _bob_weight: float = 0.0
var _was_on_floor: bool = true
var _air_speed: float = 0.0


func _ready() -> void:
	_head_height = stand_head_height
	_ensure_head()


func _physics_process(delta: float) -> void:
	if use_input_actions:
		set_move_input(Input.get_vector(action_left, action_right, action_back, action_forward))
		if Input.is_action_just_pressed(action_jump):
			press_jump()
	step(delta, is_on_floor())
	move_and_slide()


func _unhandled_input(event: InputEvent) -> void:
	if use_input_actions and event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		look((event as InputEventMouseMotion).relative)


## Turns by a mouse motion of [param relative] pixels: x turns the body, y tilts the head within the limit.
func look(relative: Vector2) -> void:
	_ensure_head()
	rotate_y(deg_to_rad(-relative.x * mouse_sensitivity))
	var limit: float = deg_to_rad(pitch_limit_degrees)
	_head.rotation.x = clampf(_head.rotation.x - deg_to_rad(relative.y * mouse_sensitivity), -limit, limit)


## Head pitch in radians (positive looks up).
func get_pitch() -> float:
	_ensure_head()
	return _head.rotation.x


## The head node (created on first use when missing).
func get_head() -> Node3D:
	_ensure_head()
	return _head


## Sets the movement input: x strafes right, y moves forward; clamped to length 1.
func set_move_input(input: Vector2) -> void:
	_move = input.limit_length(1.0)


## Turns sprinting on or off (ignored while crouching).
func set_sprinting(sprinting: bool) -> void:
	_sprinting = sprinting


## Crouches or stands up. Standing up is refused (returns false) while there is no room above.
func set_crouching(crouching: bool) -> bool:
	if crouching == _crouching:
		return true
	if not crouching and not can_stand_up():
		return false
	_crouching = crouching
	crouch_changed.emit(crouching)
	return true


## True while crouching.
func is_crouching() -> bool:
	return _crouching


## Requests a jump for the next step; it only happens on the floor and not while crouching.
func press_jump() -> void:
	_jump_requested = true


## True when a body test upward by the crouch height difference does not collide (always true outside a tree).
func can_stand_up() -> bool:
	if not is_inside_tree():
		return true
	return not test_move(global_transform, Vector3.UP * maxf(stand_head_height - crouch_head_height, 0.0))


## The horizontal world direction of the current input relative to the body's yaw.
func wish_direction() -> Vector3:
	var forward: Vector3 = -global_basis.z if is_inside_tree() else -basis.z
	var right: Vector3 = global_basis.x if is_inside_tree() else basis.x
	forward.y = 0.0
	right.y = 0.0
	var direction: Vector3 = forward.normalized() * _move.y + right.normalized() * _move.x
	return direction.limit_length(1.0)


## The speed for the current state: crouch, sprint or walk.
func current_speed() -> float:
	if _crouching:
		return crouch_speed
	return sprint_speed if _sprinting else walk_speed


## The current head height above the body origin, without bob.
func get_head_height() -> float:
	return _head_height


## The current head bob offset.
func get_bob_offset() -> Vector3:
	return Vector3(cos(_bob_phase * 0.5) * bob_amplitude * 0.5, sin(_bob_phase) * bob_amplitude, 0.0) * _bob_weight


## Advances the movement model by [param delta] seconds with the given floor contact and returns the velocity.
func step(delta: float, on_floor: bool) -> Vector3:
	_ensure_head()
	var horizontal := Vector3(velocity.x, 0.0, velocity.z)
	var rate: float = ground_acceleration if on_floor else air_acceleration
	horizontal = horizontal.move_toward(wish_direction() * current_speed(), rate * delta)
	var vertical: float = velocity.y
	if on_floor:
		if not _was_on_floor:
			landed.emit(_air_speed)
		vertical = maxf(vertical, 0.0)
		if _jump_requested and not _crouching:
			vertical = jump_velocity
			jumped.emit()
	else:
		vertical -= gravity * delta
		_air_speed = maxf(-vertical, 0.0)
	_jump_requested = false
	_was_on_floor = on_floor
	var target_height: float = crouch_head_height if _crouching else stand_head_height
	_head_height = move_toward(_head_height, target_height, crouch_transition_speed * delta)
	var ground_speed: float = horizontal.length()
	if on_floor and ground_speed > 0.1:
		_bob_phase = fmod(_bob_phase + ground_speed * delta * bob_frequency * TAU, TAU * 2.0)
		_bob_weight = move_toward(_bob_weight, 1.0, delta * 4.0)
	else:
		_bob_weight = move_toward(_bob_weight, 0.0, delta * 4.0)
	_head.position = Vector3(0.0, _head_height, 0.0) + get_bob_offset()
	velocity = Vector3(horizontal.x, vertical, horizontal.z)
	return velocity


func _ensure_head() -> void:
	if _head != null and is_instance_valid(_head):
		return
	_head = get_node_or_null(head_path) as Node3D
	if _head == null:
		_head = Node3D.new()
		_head.name = "Head"
		_head.add_child(Camera3D.new())
		add_child(_head)
		_head.position.y = _head_height
