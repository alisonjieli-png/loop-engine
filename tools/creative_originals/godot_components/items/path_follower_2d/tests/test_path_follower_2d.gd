extends "../baltor_test.gd"
## Tests for BaltorPathFollower: length, projections, points along the path, wrapping on closed paths, steering
## back into the corridor and following a bend.

const Subject := preload("../path_follower_2d.gd")


func test_length_and_projection() -> void:
	var path: Subject = Subject.new(PackedVector2Array([Vector2(0, 0), Vector2(100, 0), Vector2(100, 50)]))
	assert_almost_eq(path.get_length(), 150.0)
	var nearest: Dictionary = path.closest_point(Vector2(40, 10))
	assert_eq(nearest["point"], Vector2(40, 0))
	assert_almost_eq(float(nearest["distance_along"]), 40.0)
	assert_almost_eq(float(nearest["distance_away"]), 10.0)
	assert_almost_eq(path.progress_of(Vector2(130, 30)), 130.0)


func test_points_along_open_and_closed_paths() -> void:
	var square := PackedVector2Array([Vector2(0, 0), Vector2(10, 0), Vector2(10, 10), Vector2(0, 10)])
	var open_path: Subject = Subject.new(square)
	assert_almost_eq(open_path.get_length(), 30.0)
	assert_eq(open_path.point_at_distance(15.0), Vector2(10, 5))
	assert_eq(open_path.point_at_distance(99.0), Vector2(0, 10), "clamped at the end")
	var loop: Subject = Subject.new(square, true)
	assert_almost_eq(loop.get_length(), 40.0)
	assert_almost_eq(loop.point_at_distance(45.0), Vector2(5, 0), 0.0001, "wrapped")
	assert_almost_eq(loop.point_at_distance(-5.0), Vector2(0, 5), 0.0001)


func test_steering_is_zero_inside_and_pulls_back_outside() -> void:
	var path: Subject = Subject.new(PackedVector2Array([Vector2(0, 0), Vector2(500, 0)]), false, 10.0)
	assert_eq(path.steer(Vector2(50, 5), Vector2(40, 0), 40.0), Vector2.ZERO)
	var force: Vector2 = path.steer(Vector2(50, 40), Vector2(40, 0), 40.0)
	assert_lt(force.y, 0.0, "back toward the path")
	assert_eq(Subject.new(PackedVector2Array([Vector2(1, 1)])).steer(Vector2.ZERO, Vector2.ZERO, 10.0), Vector2.ZERO)


func test_an_agent_follows_a_bend_and_progresses() -> void:
	var path: Subject = Subject.new(PackedVector2Array([Vector2(0, 0), Vector2(200, 0), Vector2(200, 200)]), false, 8.0)
	var position := Vector2(0, 30)
	var velocity := Vector2(60, 0)
	var farthest: float = 0.0
	for _i in range(480):
		var force: Vector2 = path.steer(position, velocity, 60.0, 0.4)
		velocity = (velocity + force.limit_length(200.0) / 60.0).limit_length(60.0)
		position += velocity / 60.0
		var away: float = float(path.closest_point(position)["distance_away"])
		if _i > 120:
			assert_lt(away, 30.0, "stays near the corridor; the corner costs a turning radius of about 18 px")
		farthest = maxf(farthest, path.progress_of(position))
	assert_gt(farthest, 300.0, "went round the bend")
