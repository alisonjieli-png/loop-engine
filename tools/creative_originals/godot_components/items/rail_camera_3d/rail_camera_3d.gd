class_name BaltorRailCamera3D
extends Camera3D
## A camera that rides a Path3D rail: it stays at the rail point closest to its target, optionally leads ahead
## along the rail, eases along it and always looks at the target.
##
## Each update projects the target onto the rail with Curve3D.get_closest_offset() in the path's local space,
## adds [member lead_distance] along the rail, clamps the result to the rail length, and moves the current rail
## offset toward it with exponential smoothing at [member follow_speed] per second. The camera sits at that rail
## point and looks at the target plus [member look_offset]. Typical uses are side-scrolling 3D levels,
## corridors and cinematic dolly shots that must never leave a designed track.

## The Path3D to ride.
@export var path_node: NodePath = NodePath("")
## The node to watch.
@export var target_path: NodePath = NodePath("")
## Distance along the rail added in front of the projected target.
@export var lead_distance: float = 0.0
## Exponential easing rate of the rail offset, per second; 0 jumps.
@export var follow_speed: float = 5.0
## Offset from the target's origin to the point looked at.
@export var look_offset: Vector3 = Vector3(0, 1, 0)

var _offset: float = -1.0


func _process(delta: float) -> void:
	var target := get_node_or_null(target_path) as Node3D if not target_path.is_empty() else null
	if target != null:
		update_camera(target.global_position, delta)


## The rail Path3D, or null.
func get_rail() -> Path3D:
	return get_node_or_null(path_node) as Path3D if not path_node.is_empty() else null


## The rail offset for a target at [param world_point]: the closest offset plus the lead, clamped to the rail.
func rail_offset_for(world_point: Vector3) -> float:
	var rail: Path3D = get_rail()
	if rail == null or rail.curve == null or rail.curve.point_count < 2:
		return 0.0
	var closest: float = rail.curve.get_closest_offset(rail.to_local(world_point))
	return clampf(closest + lead_distance, 0.0, rail.curve.get_baked_length())


## The world position of the rail at [param offset].
func rail_point(offset: float) -> Vector3:
	var rail: Path3D = get_rail()
	if rail == null or rail.curve == null or rail.curve.point_count < 2:
		return global_position
	return rail.to_global(rail.curve.sample_baked(clampf(offset, 0.0, rail.curve.get_baked_length())))


## The current offset along the rail.
func get_rail_offset() -> float:
	return maxf(_offset, 0.0)


## Moves along the rail toward the point for a target at [param target_position] and looks at it.
func update_camera(target_position: Vector3, delta: float) -> void:
	var goal: float = rail_offset_for(target_position)
	if _offset < 0.0 or follow_speed <= 0.0:
		_offset = goal
	else:
		_offset = lerpf(_offset, goal, 1.0 - exp(-follow_speed * maxf(delta, 0.0)))
	global_position = rail_point(_offset)
	var focus: Vector3 = target_position + look_offset
	if not global_position.is_equal_approx(focus):
		var up: Vector3 = Vector3.UP if absf((focus - global_position).normalized().y) < 0.999 else Vector3.FORWARD
		look_at(focus, up)
