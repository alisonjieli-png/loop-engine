class_name BaltorPathFollower
extends RefCounted
## Path following steering on a polyline with a radius, plus distance queries along the path.
##
## The path is a list of points, open or closed, with a width given by [member radius]. steer() predicts where the
## agent will be after [param lookahead] seconds, projects that point onto the path, and when the prediction lies
## outside the radius it seeks a point a little further along the path than the projection; inside the radius it
## returns zero and the agent keeps its course. The same projection gives the progress along the path, which is
## useful for race positions and for spawning along routes. Distances wrap around on a closed path.

## Half width of the path corridor.
var radius: float = 16.0

var _points: PackedVector2Array = PackedVector2Array()
var _closed: bool = false
var _starts: PackedFloat32Array = PackedFloat32Array()
var _length: float = 0.0


func _init(points: PackedVector2Array = PackedVector2Array(), closed: bool = false, path_radius: float = 16.0) -> void:
	radius = path_radius
	set_points(points, closed)


## Replaces the path. Needs at least two points to steer.
func set_points(points: PackedVector2Array, closed: bool = false) -> void:
	_points = points.duplicate()
	_closed = closed
	_starts = PackedFloat32Array()
	_length = 0.0
	for index in range(_segment_count()):
		_starts.append(_length)
		_length += _points[index].distance_to(_points[(index + 1) % _points.size()])


## Total length of the path (including the closing segment when closed).
func get_length() -> float:
	return _length


## The closest point on the path to [param point] as {"point", "distance_along", "segment", "distance_away"}.
func closest_point(point: Vector2) -> Dictionary:
	var best: Dictionary = {"point": point, "distance_along": 0.0, "segment": -1, "distance_away": INF}
	for index in range(_segment_count()):
		var a: Vector2 = _points[index]
		var b: Vector2 = _points[(index + 1) % _points.size()]
		var on_segment: Vector2 = Geometry2D.get_closest_point_to_segment(point, a, b)
		var away: float = point.distance_to(on_segment)
		if away < float(best["distance_away"]):
			best = {"point": on_segment, "distance_along": _starts[index] + a.distance_to(on_segment),
					"segment": index, "distance_away": away}
	return best


## The point at [param distance] along the path (clamped on open paths, wrapped on closed ones).
func point_at_distance(distance: float) -> Vector2:
	if _points.is_empty():
		return Vector2.ZERO
	if _segment_count() == 0:
		return _points[0]
	var along: float = fposmod(distance, _length) if _closed else clampf(distance, 0.0, _length)
	for index in range(_segment_count() - 1, -1, -1):
		if along >= _starts[index]:
			var a: Vector2 = _points[index]
			var b: Vector2 = _points[(index + 1) % _points.size()]
			var segment_length: float = a.distance_to(b)
			var t: float = 0.0 if segment_length == 0.0 else (along - _starts[index]) / segment_length
			return a.lerp(b, clampf(t, 0.0, 1.0))
	return _points[0]


## Steering that keeps an agent at [param position] with [param velocity] on the path. [param ahead] is how far
## past the projection the target sits.
func steer(position: Vector2, velocity: Vector2, max_speed: float, lookahead: float = 0.5,
		ahead: float = 24.0) -> Vector2:
	if _segment_count() == 0:
		return Vector2.ZERO
	var future: Vector2 = position + velocity * lookahead
	var nearest: Dictionary = closest_point(future)
	if float(nearest["distance_away"]) <= radius:
		return Vector2.ZERO
	var target: Vector2 = point_at_distance(float(nearest["distance_along"]) + ahead)
	var offset: Vector2 = target - position
	if offset.length_squared() < 0.000001:
		return Vector2.ZERO
	return offset.normalized() * max_speed - velocity


## How far along the path the projection of [param point] is, from 0 to the length.
func progress_of(point: Vector2) -> float:
	return float(closest_point(point)["distance_along"])


func _segment_count() -> int:
	if _points.size() < 2:
		return 0
	return _points.size() if _closed else _points.size() - 1
