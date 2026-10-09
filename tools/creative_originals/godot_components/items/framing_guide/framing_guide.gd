class_name BaltorFraming
extends RefCounted
## Shot composition helpers: rule-of-thirds points, safe areas, lead room, screen bounds of 3D subjects and
## screen coverage, for camera scripts, cutscene tools and automated framing checks.
##
## Screen positions are in pixels with the origin at the top left. The thirds points are the four intersections of
## the lines at one and two thirds of the width and height. A safe area is the centered rectangle that keeps a
## fraction of each side (0.9 for action safe, 0.8 for title safe are common choices). Lead room is the share of
## the screen in front of a subject along its facing direction, from 0 (subject at the front edge) to 1 (at the
## back edge). projected_rect() projects 3D points through a Camera3D and returns their screen bounding box,
## skipping points behind the camera; coverage() is how much of the screen a rectangle covers.


## The four rule-of-thirds intersections for a screen of [param size], top left first, row by row.
static func thirds_points(size: Vector2) -> PackedVector2Array:
	var points := PackedVector2Array()
	for row: float in [1.0, 2.0]:
		for column: float in [1.0, 2.0]:
			points.append(Vector2(size.x * column / 3.0, size.y * row / 3.0))
	return points


## The thirds intersection closest to [param point].
static func nearest_third_point(point: Vector2, size: Vector2) -> Vector2:
	var best: Vector2 = Vector2.ZERO
	var best_distance: float = INF
	for candidate: Vector2 in thirds_points(size):
		var distance: float = candidate.distance_squared_to(point)
		if distance < best_distance:
			best_distance = distance
			best = candidate
	return best


## The centered rectangle that keeps [param fraction] of the width and height of a screen of [param size].
static func safe_area(size: Vector2, fraction: float) -> Rect2:
	var kept: Vector2 = size * clampf(fraction, 0.0, 1.0)
	return Rect2((size - kept) * 0.5, kept)


## True when [param point] lies inside the safe area of [param fraction].
static func is_inside_safe_area(point: Vector2, size: Vector2, fraction: float) -> bool:
	return safe_area(size, fraction).has_point(point)


## The screen movement that brings [param subject] onto its nearest thirds point.
static func offset_to_nearest_third(subject: Vector2, size: Vector2) -> Vector2:
	return nearest_third_point(subject, size) - subject


## The share of the screen in front of [param subject] along [param facing] (horizontal facing when the x part
## dominates, vertical otherwise), from 0 to 1.
static func lead_room(subject: Vector2, facing: Vector2, size: Vector2) -> float:
	if absf(facing.x) >= absf(facing.y):
		var ahead_x: float = (size.x - subject.x) if facing.x >= 0.0 else subject.x
		return clampf(ahead_x / maxf(size.x, 0.001), 0.0, 1.0)
	var ahead_y: float = (size.y - subject.y) if facing.y >= 0.0 else subject.y
	return clampf(ahead_y / maxf(size.y, 0.001), 0.0, 1.0)


## The screen bounding box of [param points] seen by [param camera]; points behind the camera are skipped.
## Returns an empty Rect2 when no point is in front.
static func projected_rect(camera: Camera3D, points: PackedVector3Array) -> Rect2:
	var bounds := Rect2()
	var started: bool = false
	for point: Vector3 in points:
		if camera.is_position_behind(point):
			continue
		var screen: Vector2 = camera.unproject_position(point)
		if not started:
			bounds = Rect2(screen, Vector2.ZERO)
			started = true
		else:
			bounds = bounds.expand(screen)
	return bounds


## The fraction of a screen of [param size] covered by [param area] after clipping it to the screen.
static func coverage(area: Rect2, size: Vector2) -> float:
	var clipped: Rect2 = area.intersection(Rect2(Vector2.ZERO, size))
	if size.x <= 0.0 or size.y <= 0.0:
		return 0.0
	return clipped.get_area() / (size.x * size.y)
