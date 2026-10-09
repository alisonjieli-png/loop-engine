class_name BaltorOrbitCamera3D
extends Camera3D
## A third-person orbit camera: yaw, pitch and distance around a target, with limits, smoothing and a pull-in
## when geometry blocks the view.
##
## The camera orbits a pivot: the target node's global position plus [member target_offset]. The desired offset
## from the pivot is (sin(yaw) cos(pitch), sin(pitch), cos(yaw) cos(pitch)) times the distance, so yaw 0 and pitch
## 0 put the camera on the +Z side of the target looking toward -Z. With [member collide] a ray from the pivot to
## the desired position (excluding the target's own collision object) shortens the distance to the first hit minus
## [member collision_margin]. A shorter distance is taken at once so walls never come between camera and target;
## a longer one eases in with exponential smoothing at [member smoothing] per second. The camera then looks at
## the pivot.

## The node to orbit.
@export var target_path: NodePath = NodePath("")
## Offset from the target's origin to the pivot, for example head height.
@export var target_offset: Vector3 = Vector3(0, 1.5, 0)
## Horizontal angle in degrees.
@export var yaw_degrees: float = 0.0
## Vertical angle in degrees; positive looks down from above.
@export var pitch_degrees: float = 20.0
## Wanted distance from the pivot.
@export var distance: float = 5.0
## Closest zoom.
@export var min_distance: float = 1.5
## Farthest zoom.
@export var max_distance: float = 12.0
## Lowest pitch in degrees.
@export var min_pitch_degrees: float = -60.0
## Highest pitch in degrees.
@export var max_pitch_degrees: float = 75.0
## Degrees per pixel of captured mouse motion.
@export var sensitivity: float = 0.25
## Distance change per mouse wheel notch.
@export var zoom_step: float = 0.5
## Exponential easing rate of the distance, per second.
@export var smoothing: float = 12.0
## Pull the camera in front of geometry between it and the pivot.
@export var collide: bool = true
## Physics layers the collision ray tests.
@export_flags_3d_physics var collision_mask: int = 1
## Gap kept between the camera and a hit surface.
@export var collision_margin: float = 0.2
## Orbit with captured mouse motion and zoom with the wheel.
@export var use_mouse: bool = true

var _current_distance: float = -1.0


func _process(delta: float) -> void:
	update_camera(delta)


func _unhandled_input(event: InputEvent) -> void:
	if not use_mouse:
		return
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var motion: Vector2 = (event as InputEventMouseMotion).relative
		orbit(-motion.x * sensitivity, motion.y * sensitivity)
	elif event is InputEventMouseButton and (event as InputEventMouseButton).pressed:
		var button: MouseButton = (event as InputEventMouseButton).button_index
		if button == MOUSE_BUTTON_WHEEL_UP:
			zoom(-zoom_step)
		elif button == MOUSE_BUTTON_WHEEL_DOWN:
			zoom(zoom_step)


## The offset from the pivot for [param yaw] and [param pitch] (radians) at [param length].
static func orbit_offset(yaw: float, pitch: float, length: float) -> Vector3:
	return Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch)) * length


## Turns the orbit by the given degrees; pitch is clamped, yaw wraps into -180..180.
func orbit(delta_yaw_degrees: float, delta_pitch_degrees: float) -> void:
	yaw_degrees = wrapf(yaw_degrees + delta_yaw_degrees, -180.0, 180.0)
	pitch_degrees = clampf(pitch_degrees + delta_pitch_degrees, min_pitch_degrees, max_pitch_degrees)


## Changes the wanted distance by [param amount], clamped to the zoom limits.
func zoom(amount: float) -> void:
	distance = clampf(distance + amount, min_distance, max_distance)


## The node being orbited, or null.
func get_target() -> Node3D:
	return get_node_or_null(target_path) as Node3D if not target_path.is_empty() else null


## The world point the camera orbits and looks at.
func get_pivot() -> Vector3:
	var target: Node3D = get_target()
	return (target.global_position if target != null else Vector3.ZERO) + target_offset


## The distance used at the last update (after collision and smoothing).
func get_current_distance() -> float:
	return maxf(_current_distance, 0.0)


## Places the camera for this frame: limits, collision pull-in, smoothing and look-at.
func update_camera(delta: float) -> void:
	pitch_degrees = clampf(pitch_degrees, min_pitch_degrees, max_pitch_degrees)
	distance = clampf(distance, min_distance, max_distance)
	var pivot: Vector3 = get_pivot()
	var direction: Vector3 = orbit_offset(deg_to_rad(yaw_degrees), deg_to_rad(pitch_degrees), 1.0)
	var wanted: float = distance
	if collide and is_inside_tree():
		wanted = minf(wanted, _clear_distance(pivot, pivot + direction * distance))
	if _current_distance < 0.0 or wanted < _current_distance:
		_current_distance = wanted
	else:
		_current_distance = lerpf(_current_distance, wanted, 1.0 - exp(-smoothing * maxf(delta, 0.0)))
	global_position = pivot + direction * _current_distance
	if not global_position.is_equal_approx(pivot):
		var up: Vector3 = Vector3.UP if absf(direction.y) < 0.999 else Vector3.FORWARD
		look_at(pivot, up)


func _clear_distance(pivot: Vector3, wanted_point: Vector3) -> float:
	var query := PhysicsRayQueryParameters3D.create(pivot, wanted_point, collision_mask)
	var target := get_target() as CollisionObject3D
	if target != null:
		query.exclude = [target.get_rid()]
	var hit: Dictionary = get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty():
		return pivot.distance_to(wanted_point)
	return maxf(pivot.distance_to(hit["position"]) - collision_margin, 0.0)
