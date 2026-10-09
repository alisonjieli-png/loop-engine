class_name BaltorHexGrid
extends RefCounted
## Hexagon grid math on axial coordinates: distance, neighbors, rings, spirals, lines, rotation, pixel
## conversion, reachable ranges and A* paths.
##
## A hex is a Vector2i(q, r) in axial coordinates. The cube form is Vector3i(q, r, s) with q + r + s = 0, and the
## distance between two hexes is the largest absolute cube difference. Lines sample the cube-space segment at
## evenly spaced points and round each point to the nearest hex, after a small nudge so points on an edge round
## the same way every time. Pixel conversion works for pointy-top and flat-top layouts of a given hex size (the
## center-to-corner distance). Paths use A* with the hex distance as the heuristic, so they are shortest paths
## when every step costs 1. All methods are static; nothing needs to be instanced.

## Axial offsets of the six neighbors, counter-clockwise starting east (pointy-top layout).
const DIRECTIONS: Array[Vector2i] = [
	Vector2i(1, 0), Vector2i(1, -1), Vector2i(0, -1), Vector2i(-1, 0), Vector2i(-1, 1), Vector2i(0, 1)]
const _SQRT3: float = 1.7320508075688772


## The cube coordinates (q, r, s) of an axial hex.
static func axial_to_cube(hex: Vector2i) -> Vector3i:
	return Vector3i(hex.x, hex.y, -hex.x - hex.y)


## The axial coordinates of a cube hex (s is dropped).
static func cube_to_axial(cube: Vector3i) -> Vector2i:
	return Vector2i(cube.x, cube.y)


## Rounds fractional cube coordinates to the nearest hex, fixing the component with the largest rounding error.
static func cube_round(cube: Vector3) -> Vector3i:
	var q: float = roundf(cube.x)
	var r: float = roundf(cube.y)
	var s: float = roundf(cube.z)
	var dq: float = absf(q - cube.x)
	var dr: float = absf(r - cube.y)
	var ds: float = absf(s - cube.z)
	if dq > dr and dq > ds:
		q = -r - s
	elif dr > ds:
		r = -q - s
	else:
		s = -q - r
	return Vector3i(int(q), int(r), int(s))


## Number of steps between two hexes.
static func distance(a: Vector2i, b: Vector2i) -> int:
	var d: Vector3i = axial_to_cube(a) - axial_to_cube(b)
	return maxi(absi(d.x), maxi(absi(d.y), absi(d.z)))


## The neighbor of [param hex] in direction 0 to 5 (wrapped).
static func neighbor(hex: Vector2i, direction: int) -> Vector2i:
	return hex + DIRECTIONS[posmod(direction, 6)]


## The six neighbors of [param hex] in direction order.
static func neighbors(hex: Vector2i) -> Array[Vector2i]:
	var result: Array[Vector2i] = []
	for offset: Vector2i in DIRECTIONS:
		result.append(hex + offset)
	return result


## The hexes at exactly [param radius] steps from [param center], walking once around the ring.
static func ring(center: Vector2i, radius: int) -> Array[Vector2i]:
	var result: Array[Vector2i] = []
	if radius < 0:
		return result
	if radius == 0:
		result.append(center)
		return result
	var hex: Vector2i = center + DIRECTIONS[4] * radius
	for side in range(6):
		for _step in range(radius):
			result.append(hex)
			hex = neighbor(hex, side)
	return result


## Every hex within [param radius] steps, ring by ring from the center outwards.
static func spiral(center: Vector2i, radius: int) -> Array[Vector2i]:
	var result: Array[Vector2i] = []
	for step in range(radius + 1):
		result.append_array(ring(center, step))
	return result


## The hexes on the straight line from [param a] to [param b], both included.
static func line(a: Vector2i, b: Vector2i) -> Array[Vector2i]:
	var steps: int = distance(a, b)
	var start := Vector3(axial_to_cube(a)) + Vector3(1e-6, 2e-6, -3e-6)
	var finish := Vector3(axial_to_cube(b)) + Vector3(1e-6, 2e-6, -3e-6)
	var result: Array[Vector2i] = []
	for index in range(steps + 1):
		var t: float = 0.0 if steps == 0 else float(index) / float(steps)
		result.append(cube_to_axial(cube_round(start.lerp(finish, t))))
	return result


## [param hex] rotated by [param steps] sixths of a turn counter-clockwise around [param center].
static func rotate(hex: Vector2i, center: Vector2i, steps: int) -> Vector2i:
	var cube: Vector3i = axial_to_cube(hex - center)
	for _turn in range(posmod(steps, 6)):
		cube = Vector3i(-cube.z, -cube.x, -cube.y)
	return cube_to_axial(cube) + center


## The pixel position of the center of [param hex] for hexes of [param size] (center to corner).
static func to_pixel(hex: Vector2i, size: float, pointy_top: bool = true) -> Vector2:
	if pointy_top:
		return Vector2(size * (_SQRT3 * hex.x + _SQRT3 / 2.0 * hex.y), size * 1.5 * hex.y)
	return Vector2(size * 1.5 * hex.x, size * (_SQRT3 / 2.0 * hex.x + _SQRT3 * hex.y))


## The hex that contains [param point] for hexes of [param size].
static func from_pixel(point: Vector2, size: float, pointy_top: bool = true) -> Vector2i:
	var q: float = 0.0
	var r: float = 0.0
	if pointy_top:
		q = (_SQRT3 / 3.0 * point.x - point.y / 3.0) / size
		r = (2.0 / 3.0 * point.y) / size
	else:
		q = (2.0 / 3.0 * point.x) / size
		r = (-point.x / 3.0 + _SQRT3 / 3.0 * point.y) / size
	return cube_to_axial(cube_round(Vector3(q, r, -q - r)))


## The six corner points of [param hex], for drawing with Polygon2D or Line2D.
static func corners(hex: Vector2i, size: float, pointy_top: bool = true) -> PackedVector2Array:
	var center: Vector2 = to_pixel(hex, size, pointy_top)
	var points := PackedVector2Array()
	for index in range(6):
		var angle: float = deg_to_rad(60.0 * index - (30.0 if pointy_top else 0.0))
		points.append(center + Vector2(cos(angle), sin(angle)) * size)
	return points


## Every hex reachable from [param start] in at most [param steps] moves through hexes for which
## [param is_passable] (a Callable taking a Vector2i and returning bool) is true. The start is included.
static func reachable(start: Vector2i, steps: int, is_passable: Callable) -> Array[Vector2i]:
	var visited: Dictionary = {start: true}
	var frontier: Array[Vector2i] = [start]
	var result: Array[Vector2i] = [start]
	for _step in range(steps):
		var next_frontier: Array[Vector2i] = []
		for hex: Vector2i in frontier:
			for next: Vector2i in neighbors(hex):
				if visited.has(next) or not bool(is_passable.call(next)):
					continue
				visited[next] = true
				next_frontier.append(next)
				result.append(next)
		frontier = next_frontier
	return result


## A shortest path from [param start] to [param goal] (both included) through passable hexes, found with A*.
## Returns an empty array when the goal cannot be reached within [param max_expanded] expanded hexes.
static func find_path(start: Vector2i, goal: Vector2i, is_passable: Callable,
		max_expanded: int = 4096) -> Array[Vector2i]:
	var empty: Array[Vector2i] = []
	if start != goal and not bool(is_passable.call(goal)):
		return empty
	var came_from: Dictionary = {start: start}
	var cost: Dictionary = {start: 0}
	var heap: Array = [[distance(start, goal), 0, start, 0]]
	var order: int = 0
	var expanded: int = 0
	while not heap.is_empty() and expanded < max_expanded:
		var entry: Array = _heap_pop(heap)
		var current: Vector2i = entry[2]
		if int(entry[3]) > int(cost[current]):
			continue
		if current == goal:
			var path: Array[Vector2i] = [goal]
			while path[0] != start:
				path.push_front(came_from[path[0]])
			return path
		expanded += 1
		for next: Vector2i in neighbors(current):
			var next_cost: int = int(cost[current]) + 1
			if next != goal and not bool(is_passable.call(next)):
				continue
			if not cost.has(next) or next_cost < int(cost[next]):
				cost[next] = next_cost
				came_from[next] = current
				order += 1
				_heap_push(heap, [next_cost + distance(next, goal), order, next, next_cost])
	return empty


static func _heap_push(heap: Array, entry: Array) -> void:
	heap.append(entry)
	var index: int = heap.size() - 1
	while index > 0:
		var parent: int = (index - 1) >> 1
		if not _before(heap[index], heap[parent]):
			break
		var swap: Variant = heap[parent]
		heap[parent] = heap[index]
		heap[index] = swap
		index = parent


static func _heap_pop(heap: Array) -> Array:
	var top: Array = heap[0]
	var last: Array = heap.pop_back()
	if heap.is_empty():
		return top
	heap[0] = last
	var index: int = 0
	while true:
		var left: int = index * 2 + 1
		var smallest: int = index
		if left < heap.size() and _before(heap[left], heap[smallest]):
			smallest = left
		if left + 1 < heap.size() and _before(heap[left + 1], heap[smallest]):
			smallest = left + 1
		if smallest == index:
			break
		var swap: Variant = heap[smallest]
		heap[smallest] = heap[index]
		heap[index] = swap
		index = smallest
	return top


static func _before(a: Array, b: Array) -> bool:
	return int(a[0]) < int(b[0]) or (int(a[0]) == int(b[0]) and int(a[1]) < int(b[1]))
