extends "../baltor_test.gd"
## Tests for BaltorObstacleAvoidance: the ray test, picking the closest threat in the corridor, steering away to
## the free side, stronger force when closer, and a walk past an obstacle without touching it.

const Subject := preload("../obstacle_avoidance_2d.gd")


func test_ray_circle_known_distances() -> void:
	assert_almost_eq(Subject.ray_circle(Vector2.ZERO, Vector2.RIGHT, Vector2(10, 0), 2.0), 8.0)
	assert_eq(Subject.ray_circle(Vector2.ZERO, Vector2.RIGHT, Vector2(-10, 0), 2.0), -1.0, "behind")
	assert_eq(Subject.ray_circle(Vector2.ZERO, Vector2.RIGHT, Vector2(10, 5), 2.0), -1.0, "missed")
	assert_eq(Subject.ray_circle(Vector2(10, 0), Vector2.RIGHT, Vector2(10, 0), 2.0), 0.0, "inside")


func test_finds_the_closest_obstacle_inside_the_corridor() -> void:
	var obstacles := PackedVector3Array([Vector3(80, 0, 10), Vector3(40, 5, 8), Vector3(20, 40, 5), Vector3(-30, 0, 5)])
	assert_eq(Subject.find_threat(Vector2.ZERO, Vector2(10, 0), obstacles, 6.0, 100.0), 1)
	assert_eq(Subject.find_threat(Vector2.ZERO, Vector2(10, 0), obstacles, 6.0, 30.0), -1, "too far ahead")
	assert_eq(Subject.find_threat(Vector2.ZERO, Vector2.ZERO, obstacles, 6.0, 100.0), -1, "standing still")


func test_steers_toward_the_free_side_and_harder_when_closer() -> void:
	var above := PackedVector3Array([Vector3(50, -4, 8)])
	var force: Vector2 = Subject.avoid(Vector2.ZERO, Vector2(10, 0), above, 5.0, 100.0, 20.0)
	assert_gt(force.y, 0.0, "the obstacle is above the path, so steer down")
	assert_lt(force.x, 0.0, "and brake a little")
	var near: Vector2 = Subject.avoid(Vector2(40, 0), Vector2(10, 0), above, 5.0, 100.0, 20.0)
	assert_gt(near.length(), force.length())
	var centered: Vector2 = Subject.avoid(Vector2.ZERO, Vector2(10, 0), PackedVector3Array([Vector3(50, 0, 8)]), 5.0, 100.0, 20.0)
	assert_gt(centered.y, 0.0, "dead ahead turns to the right-hand side")
	assert_eq(Subject.avoid(Vector2.ZERO, Vector2(10, 0), PackedVector3Array(), 5.0, 100.0, 20.0), Vector2.ZERO)


func test_agent_walks_past_an_obstacle_without_touching_it() -> void:
	var obstacles := PackedVector3Array([Vector3(150, 2, 20)])
	var position := Vector2.ZERO
	var velocity := Vector2(80, 0)
	var closest: float = INF
	for _i in range(300):
		var steering: Vector2 = Subject.avoid(position, velocity, obstacles, 6.0, 90.0, 400.0)
		steering += (Vector2(300, 0) - position).normalized() * 80.0 - velocity
		velocity = (velocity + steering.limit_length(400.0) / 60.0).limit_length(80.0)
		position += velocity / 60.0
		closest = minf(closest, position.distance_to(Vector2(150, 2)))
	assert_gt(closest, 20.0 + 6.0, "never overlapped the obstacle")
	assert_gt(position.x, 250.0, "and kept going")
