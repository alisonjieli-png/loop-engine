class_name BaltorPotentialField
extends RefCounted
## An artificial potential field in 2D: goals attract, obstacles repel within an influence radius, and agents
## move down the gradient.
##
## An attractor at g with strength k adds k * |p - g| to the potential (a cone), whose force has constant size k
## toward the goal. A repulsor at o with strength e and influence radius r adds e / 2 * (1 / d - 1 / r)^2 for
## distances d < r (the classic obstacle potential), whose force grows without bound near the obstacle and is zero
## beyond r. force_at() is the negative gradient, computed analytically. follow() takes fixed-length steps along
## the force and stops at the goal radius, at a step limit, or when the force vanishes, which is how a local
## minimum (an obstacle between agent and goal in a symmetric layout) shows up.

var _attractors: Array[Vector3] = []
var _repulsors: Array[Vector4] = []


## Adds a goal at [param point] pulling with constant [param strength].
func add_attractor(point: Vector2, strength: float = 1.0) -> void:
	_attractors.append(Vector3(point.x, point.y, strength))


## Adds an obstacle at [param point] pushing with [param strength] inside [param influence_radius].
func add_repulsor(point: Vector2, strength: float, influence_radius: float) -> void:
	_repulsors.append(Vector4(point.x, point.y, strength, maxf(influence_radius, 0.001)))


## Removes every attractor and repulsor.
func clear() -> void:
	_attractors.clear()
	_repulsors.clear()


## The potential at [param point].
func potential_at(point: Vector2) -> float:
	var total: float = 0.0
	for goal: Vector3 in _attractors:
		total += goal.z * point.distance_to(Vector2(goal.x, goal.y))
	for obstacle: Vector4 in _repulsors:
		var distance: float = maxf(point.distance_to(Vector2(obstacle.x, obstacle.y)), 0.0001)
		if distance < obstacle.w:
			var gap: float = 1.0 / distance - 1.0 / obstacle.w
			total += 0.5 * obstacle.z * gap * gap
	return total


## The force (negative gradient of the potential) at [param point].
func force_at(point: Vector2) -> Vector2:
	var total := Vector2.ZERO
	for goal: Vector3 in _attractors:
		var toward: Vector2 = Vector2(goal.x, goal.y) - point
		if toward.length_squared() > 0.0:
			total += toward.normalized() * goal.z
	for obstacle: Vector4 in _repulsors:
		var away: Vector2 = point - Vector2(obstacle.x, obstacle.y)
		var distance: float = maxf(away.length(), 0.0001)
		if distance < obstacle.w:
			var gap: float = 1.0 / distance - 1.0 / obstacle.w
			total += away / distance * obstacle.z * gap / (distance * distance)
	return total


## Walks from [param start] along the force in steps of [param step_length]. Stops within [param goal_radius] of
## any attractor, after [param max_steps] steps, or where the force is weaker than [param min_force].
## Returns {"points": PackedVector2Array, "reached": bool}.
func follow(start: Vector2, step_length: float, max_steps: int = 500, goal_radius: float = 1.0,
		min_force: float = 0.001) -> Dictionary:
	var points := PackedVector2Array([start])
	var here: Vector2 = start
	for _step in range(max_steps):
		if _near_goal(here, goal_radius):
			return {"points": points, "reached": true}
		var force: Vector2 = force_at(here)
		if force.length() < min_force:
			break
		here += force.normalized() * step_length
		points.append(here)
	return {"points": points, "reached": _near_goal(here, goal_radius)}


func _near_goal(point: Vector2, goal_radius: float) -> bool:
	for goal: Vector3 in _attractors:
		if point.distance_to(Vector2(goal.x, goal.y)) <= goal_radius:
			return true
	return false
