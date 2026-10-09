class_name BaltorRaycastVehicle
extends RigidBody3D
## An arcade vehicle on raycast suspension: each wheel casts a ray down, a spring-damper pushes the body up at that
## wheel, drive force pushes along the wheel's heading and lateral grip cancels sideways sliding.
##
## Wheels are points in the body's local space at the top of their suspension travel. Every physics frame each
## wheel casts a ray along the body's down axis, [member rest_length] + [member wheel_radius] long. On a hit the
## compression x is rest_length minus the spring length, and the spring force along the body's up axis is
## (stiffness * x + damping * dx/dt) * mass / wheel count, never pulling the body down. With stiffness and damping
## given per kilogram the ride height does not depend on the mass: at rest x = gravity / stiffness. Grounded wheels
## also add drive force (driven wheels, split evenly), rolling resistance and a lateral force that cancels the
## sideways speed at the contact point times [member lateral_grip]. The first [member steering_wheel_count] wheels
## turn by up to [member max_steer_degrees]. The chassis collision shape is up to you; keep it above the wheels.

## Emitted when every wheel leaves the ground or the first wheel touches it again.
signal airborne_changed(airborne: bool)

## Wheel mount points in local space, front wheels first.
@export var wheel_points: PackedVector3Array = PackedVector3Array([Vector3(-0.8, 0, -1.2), Vector3(0.8, 0, -1.2),
		Vector3(-0.8, 0, 1.2), Vector3(0.8, 0, 1.2)])
## How many wheels at the start of wheel_points steer.
@export var steering_wheel_count: int = 2
## Indices of the wheels that receive drive force.
@export var driven_wheels: PackedInt32Array = PackedInt32Array([2, 3])
## Spring length at rest, in meters.
@export var rest_length: float = 0.5
## Wheel radius in meters.
@export var wheel_radius: float = 0.35
## Spring stiffness per kilogram of body mass, per wheel share.
@export var spring_stiffness: float = 30.0
## Spring damping per kilogram of body mass, per wheel share.
@export var spring_damping: float = 4.0
## Drive acceleration at full throttle in meters per second squared.
@export var engine_acceleration: float = 12.0
## Largest steering angle in degrees.
@export var max_steer_degrees: float = 30.0
## How strongly sideways sliding is cancelled, per second.
@export var lateral_grip: float = 8.0
## Forward speed lost per second, as a fraction of the speed.
@export var rolling_resistance: float = 0.3
## Physics layers the wheel rays test.
@export_flags_3d_physics var ground_mask: int = 1
## Read throttle and steering from the ui actions. Turn off to drive from code.
@export var use_input_actions: bool = true

var _throttle: float = 0.0
var _steer: float = 0.0
var _compression: PackedFloat32Array = PackedFloat32Array()
var _grounded: PackedByteArray = PackedByteArray()
var _airborne: bool = true


## The spring force for a compression and compression speed (per wheel, before the mass share); never negative.
static func suspension_force(compression: float, compression_speed: float, stiffness: float, damping: float,
		mass_share: float) -> float:
	if compression <= 0.0:
		return 0.0
	return maxf((stiffness * compression + damping * compression_speed) * mass_share, 0.0)


## The sideways force that cancels [param side_speed] for a wheel carrying [param mass_share] kilograms.
static func lateral_force(side_speed: float, grip: float, mass_share: float) -> float:
	return -side_speed * grip * mass_share


## Sets throttle (-1 reverse to 1 forward) and steering (-1 left to 1 right).
func set_controls(throttle: float, steer: float) -> void:
	_throttle = clampf(throttle, -1.0, 1.0)
	_steer = clampf(steer, -1.0, 1.0)


## Number of wheels.
func get_wheel_count() -> int:
	return wheel_points.size()


## True when wheel [param index] touched the ground in the last physics frame.
func is_wheel_grounded(index: int) -> bool:
	return index >= 0 and index < _grounded.size() and _grounded[index] == 1


## Spring compression of wheel [param index] in the last physics frame, in meters.
func get_wheel_compression(index: int) -> float:
	return _compression[index] if index >= 0 and index < _compression.size() else 0.0


## How many wheels touched the ground in the last physics frame.
func grounded_wheel_count() -> int:
	var count: int = 0
	for flag: int in _grounded:
		count += flag
	return count


## Speed along the body's forward axis (-Z), in meters per second.
func get_forward_speed() -> float:
	return linear_velocity.dot(-global_basis.z)


func _physics_process(delta: float) -> void:
	if use_input_actions:
		set_controls(Input.get_axis(&"ui_down", &"ui_up"), Input.get_axis(&"ui_left", &"ui_right"))
	var count: int = wheel_points.size()
	if _compression.size() != count:
		_compression.resize(count)
		_compression.fill(0.0)
		_grounded.resize(count)
		_grounded.fill(0)
	if count == 0 or delta <= 0.0:
		return
	var space: PhysicsDirectSpaceState3D = get_world_3d().direct_space_state
	var up: Vector3 = global_basis.y
	var share: float = mass / float(count)
	var driven: int = maxi(driven_wheels.size(), 1)
	for index in range(count):
		var origin: Vector3 = global_transform * wheel_points[index]
		var query := PhysicsRayQueryParameters3D.create(origin, origin - up * (rest_length + wheel_radius), ground_mask,
				[get_rid()])
		var hit: Dictionary = space.intersect_ray(query)
		if hit.is_empty():
			_grounded[index] = 0
			_compression[index] = 0.0
			continue
		_grounded[index] = 1
		var contact: Vector3 = hit["position"]
		var compression: float = clampf(rest_length - (origin.distance_to(contact) - wheel_radius), 0.0, rest_length)
		var speed: float = (compression - _compression[index]) / delta
		_compression[index] = compression
		var offset: Vector3 = contact - global_position
		apply_force(up * suspension_force(compression, speed, spring_stiffness, spring_damping, share), offset)
		var heading: Vector3 = -global_basis.z
		if index < steering_wheel_count:
			heading = heading.rotated(up, -deg_to_rad(max_steer_degrees) * _steer)
		var side: Vector3 = heading.cross(up).normalized()
		var point_velocity: Vector3 = linear_velocity + angular_velocity.cross(offset)
		var traction: Vector3 = side * lateral_force(point_velocity.dot(side), lateral_grip, share)
		traction -= heading * point_velocity.dot(heading) * rolling_resistance * share
		if driven_wheels.has(index):
			traction += heading * _throttle * engine_acceleration * mass / float(driven)
		apply_force(traction, offset)
	var airborne: bool = grounded_wheel_count() == 0
	if airborne != _airborne:
		_airborne = airborne
		airborne_changed.emit(airborne)
