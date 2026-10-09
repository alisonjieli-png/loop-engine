class_name BaltorBuoyancy3D
extends Node
## Buoyancy for the parent RigidBody3D from probe points: each submerged probe pushes up in proportion to its depth,
## and water drag slows the body while it is wet.
##
## Probes are points in the parent's local space. The water surface height at a point is [member water_height]
## plus a sum of travelling sine waves, each a Vector4(amplitude, wavelength, speed, direction in degrees); the
## same formula can drive a water shader so visuals and physics agree. A probe at depth d below the surface pushes
## up with buoyancy * (mass / probe count) * gravity * clamp(d / probe_depth, 0, 1), at the probe's position, so
## uneven depth also produces the righting torque. On flat water every probe rests at probe_depth / buoyancy
## below the surface. Linear and angular drag scale with the fraction of submerged probes.

## Emitted when the first probe goes under the surface.
signal entered_water
## Emitted when the last probe comes out of the water.
signal left_water

## Height of the calm water surface.
@export var water_height: float = 0.0
## Waves as Vector4(amplitude, wavelength, speed, direction in degrees).
@export var waves: PackedVector4Array = PackedVector4Array()
## Probe points in the parent's local space.
@export var probes: PackedVector3Array = PackedVector3Array([Vector3(-0.5, 0, -0.5), Vector3(0.5, 0, -0.5),
		Vector3(-0.5, 0, 0.5), Vector3(0.5, 0, 0.5)])
## Depth at which a probe gives its full force.
@export var probe_depth: float = 0.5
## Full-depth force per probe share relative to the body's weight; 2 floats at half probe_depth.
@export var buoyancy: float = 2.0
## Downward acceleration used for the force, in meters per second squared.
@export var gravity: float = 9.8
## Linear drag per second while fully submerged.
@export var water_drag: float = 1.5
## Angular drag per second while fully submerged.
@export var water_angular_drag: float = 1.5

var _time: float = 0.0
var _submerged: float = 0.0


func _physics_process(delta: float) -> void:
	var body := get_parent() as RigidBody3D
	if body != null:
		apply_forces(body, delta)


## The surface height at world point (x, z) = [param point] at [param time] for [param wave_list] over
## [param base_height].
static func wave_height_at(point: Vector2, time: float, base_height: float, wave_list: PackedVector4Array) -> float:
	var height: float = base_height
	for wave: Vector4 in wave_list:
		var wavelength: float = maxf(wave.y, 0.001)
		var number: float = TAU / wavelength
		var direction: Vector2 = Vector2.from_angle(deg_to_rad(wave.w))
		height += wave.x * sin(number * direction.dot(point) - wave.z * number * time)
	return height


## The surface height under [param world_position] at the component's current time.
func surface_height(world_position: Vector3) -> float:
	return wave_height_at(Vector2(world_position.x, world_position.z), _time, water_height, waves)


## The upward force for one probe at [param depth] below the surface carrying [param mass_share] kilograms.
func probe_force(depth: float, mass_share: float) -> float:
	if depth <= 0.0:
		return 0.0
	return buoyancy * mass_share * gravity * clampf(depth / maxf(probe_depth, 0.001), 0.0, 1.0)


## Fraction of probes under water in the last update (0 to 1).
func get_submerged_ratio() -> float:
	return _submerged


## Seconds of wave time so far.
func get_time() -> float:
	return _time


## Advances wave time by [param delta] and applies buoyancy and drag to [param body].
func apply_forces(body: RigidBody3D, delta: float) -> void:
	_time += delta
	if probes.is_empty():
		return
	var share: float = body.mass / float(probes.size())
	var wet: int = 0
	for local_point: Vector3 in probes:
		var point: Vector3 = body.global_transform * local_point
		var depth: float = surface_height(point) - point.y
		if depth <= 0.0:
			continue
		wet += 1
		body.apply_force(Vector3.UP * probe_force(depth, share), point - body.global_position)
	var ratio: float = float(wet) / float(probes.size())
	if ratio > 0.0:
		body.apply_central_force(-body.linear_velocity * water_drag * body.mass * ratio)
		body.apply_torque(-body.angular_velocity * water_angular_drag * body.mass * ratio)
	if ratio > 0.0 and _submerged == 0.0:
		entered_water.emit()
	elif ratio == 0.0 and _submerged > 0.0:
		left_water.emit()
	_submerged = ratio
