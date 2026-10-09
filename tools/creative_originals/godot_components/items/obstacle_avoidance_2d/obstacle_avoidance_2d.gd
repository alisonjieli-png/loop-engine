class_name BaltorObstacleAvoidance
extends RefCounted
## Obstacle avoidance steering for 2D agents among circle obstacles, with a detection corridor ahead of the agent.
##
## Obstacles are Vector3(center x, center y, radius). The agent looks along its velocity over a corridor
## [param look_ahead] long and as wide as its own radius on each side. Among the obstacles that intersect the
## corridor, the closest one ahead is avoided: the steering pushes sideways away from that obstacle's center, more
## strongly the closer it is, and brakes a little in proportion to the same closeness. When the obstacle sits
## exactly on the path line the agent turns to its right-hand side (screen coordinates), so the choice is
## repeatable. ray_circle() is the underlying ray test.


## Distance along a unit [param direction] from [param origin] to the first point of the circle, 0 when the origin
## is inside it, or -1 when the ray misses.
static func ray_circle(origin: Vector2, direction: Vector2, center: Vector2, radius: float) -> float:
	var offset: Vector2 = origin - center
	var c: float = offset.length_squared() - radius * radius
	if c <= 0.0:
		return 0.0
	var b: float = offset.dot(direction)
	var discriminant: float = b * b - c
	if b > 0.0 or discriminant < 0.0:
		return -1.0
	return -b - sqrt(discriminant)


## The index of the closest obstacle inside the corridor ahead, or -1.
static func find_threat(position: Vector2, velocity: Vector2, obstacles: PackedVector3Array, agent_radius: float,
		look_ahead: float) -> int:
	if velocity.length_squared() < 0.000001:
		return -1
	var heading: Vector2 = velocity.normalized()
	var side := Vector2(-heading.y, heading.x)
	var best: int = -1
	var best_ahead: float = INF
	for index in range(obstacles.size()):
		var obstacle: Vector3 = obstacles[index]
		var local: Vector2 = Vector2(obstacle.x, obstacle.y) - position
		var ahead: float = local.dot(heading)
		var lateral: float = local.dot(side)
		if ahead < -obstacle.z or ahead - obstacle.z > look_ahead:
			continue
		if absf(lateral) >= obstacle.z + agent_radius:
			continue
		if ahead < best_ahead:
			best_ahead = ahead
			best = index
	return best


## The avoidance steering force, limited to [param max_force]; zero when nothing is in the corridor.
static func avoid(position: Vector2, velocity: Vector2, obstacles: PackedVector3Array, agent_radius: float,
		look_ahead: float, max_force: float) -> Vector2:
	var index: int = find_threat(position, velocity, obstacles, agent_radius, look_ahead)
	if index < 0:
		return Vector2.ZERO
	var heading: Vector2 = velocity.normalized()
	var side := Vector2(-heading.y, heading.x)
	var obstacle: Vector3 = obstacles[index]
	var local: Vector2 = Vector2(obstacle.x, obstacle.y) - position
	var ahead: float = maxf(local.dot(heading), 0.0)
	var lateral: float = local.dot(side)
	var closeness: float = clampf(1.0 - ahead / maxf(look_ahead, 0.001), 0.0, 1.0)
	var away: float = -signf(lateral) if absf(lateral) > 0.0001 else 1.0
	var push: Vector2 = side * away * max_force * (0.5 + 0.5 * closeness)
	var brake: Vector2 = -heading * max_force * 0.3 * closeness
	return (push + brake).limit_length(max_force)
