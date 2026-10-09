class_name BaltorFlock
extends RefCounted
## A 2D boids flock: separation, alignment and cohesion over neighbors found with a spatial hash.
##
## Each boid steers by the weighted sum of three rules computed over the boids within [member neighbor_radius]:
## separation pushes away from boids closer than [member separation_radius] (weighted by inverse distance),
## alignment steers toward the neighbors' average velocity, and cohesion seeks their average position. Each rule is
## a desired velocity at [member max_speed] minus the current velocity, and the sum is limited to
## [member max_force]. Neighbors come from a uniform grid of cells as large as the neighbor radius, so a step looks
## at nearby cells only. With [member bounds] set (non-zero size), boids wrap around its edges. All boids update
## from the same snapshot, so the result does not depend on boid order.

## Distance within which other boids count as neighbors.
var neighbor_radius: float = 50.0
## Distance below which separation applies.
var separation_radius: float = 20.0
## Weight of separation.
var separation_weight: float = 1.5
## Weight of alignment.
var alignment_weight: float = 1.0
## Weight of cohesion.
var cohesion_weight: float = 1.0
## Top speed.
var max_speed: float = 120.0
## Largest steering force (acceleration per second).
var max_force: float = 240.0
## Area the boids wrap around in; a zero size disables wrapping.
var bounds: Rect2 = Rect2()

var _positions: PackedVector2Array = PackedVector2Array()
var _velocities: PackedVector2Array = PackedVector2Array()


## Adds a boid and returns its index.
func add_boid(position: Vector2, velocity: Vector2 = Vector2.ZERO) -> int:
	_positions.append(position)
	_velocities.append(velocity.limit_length(max_speed))
	return _positions.size() - 1


## Number of boids.
func get_count() -> int:
	return _positions.size()


## A copy of every position.
func get_positions() -> PackedVector2Array:
	return _positions.duplicate()


## A copy of every velocity.
func get_velocities() -> PackedVector2Array:
	return _velocities.duplicate()


## Indices of the boids within the neighbor radius of boid [param index], excluding itself, in index order.
func neighbors_of(index: int) -> PackedInt32Array:
	return _neighbors(index, _grid())


## The steering of boid [param index] from the three rules, before integration.
func steering_of(index: int) -> Vector2:
	return _steer(index, _grid())


## Moves every boid by [param delta] seconds.
func step(delta: float) -> void:
	var grid: Dictionary = _grid()
	var forces := PackedVector2Array()
	for index in range(_positions.size()):
		forces.append(_steer(index, grid))
	for index in range(_positions.size()):
		_velocities[index] = (_velocities[index] + forces[index] * delta).limit_length(max_speed)
		var next: Vector2 = _positions[index] + _velocities[index] * delta
		if bounds.size.x > 0.0 and bounds.size.y > 0.0:
			next = Vector2(wrapf(next.x, bounds.position.x, bounds.end.x), wrapf(next.y, bounds.position.y, bounds.end.y))
		_positions[index] = next


func _cell(point: Vector2) -> Vector2i:
	var size: float = maxf(neighbor_radius, 0.001)
	return Vector2i(floori(point.x / size), floori(point.y / size))


func _grid() -> Dictionary:
	var grid: Dictionary = {}
	for index in range(_positions.size()):
		var cell: Vector2i = _cell(_positions[index])
		if not grid.has(cell):
			grid[cell] = PackedInt32Array()
		var members: PackedInt32Array = grid[cell]
		members.append(index)
		grid[cell] = members
	return grid


func _neighbors(index: int, grid: Dictionary) -> PackedInt32Array:
	var found := PackedInt32Array()
	var center: Vector2i = _cell(_positions[index])
	for dy in range(-1, 2):
		for dx in range(-1, 2):
			for other: int in grid.get(center + Vector2i(dx, dy), PackedInt32Array()):
				if other != index and _positions[other].distance_to(_positions[index]) <= neighbor_radius:
					found.append(other)
	found.sort()
	return found


func _steer(index: int, grid: Dictionary) -> Vector2:
	var near: PackedInt32Array = _neighbors(index, grid)
	if near.is_empty():
		return Vector2.ZERO
	var here: Vector2 = _positions[index]
	var velocity: Vector2 = _velocities[index]
	var push := Vector2.ZERO
	var heading := Vector2.ZERO
	var center := Vector2.ZERO
	for other: int in near:
		var offset: Vector2 = here - _positions[other]
		var distance: float = offset.length()
		if distance < separation_radius and distance > 0.0001:
			push += offset / (distance * distance)
		heading += _velocities[other]
		center += _positions[other]
	var total := Vector2.ZERO
	if push.length_squared() > 0.0:
		total += (push.normalized() * max_speed - velocity) * separation_weight
	heading /= near.size()
	if heading.length_squared() > 0.0:
		total += (heading.normalized() * max_speed - velocity) * alignment_weight
	center /= near.size()
	var toward: Vector2 = center - here
	if toward.length_squared() > 0.0:
		total += (toward.normalized() * max_speed - velocity) * cohesion_weight
	return total.limit_length(max_force)
