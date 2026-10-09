extends "../baltor_test.gd"
## Tests for BaltorPotentialField: attraction, the repulsion range and growth, force as the negative gradient,
## reaching a goal around an obstacle and stalling in a symmetric local minimum.

const Subject := preload("../potential_field.gd")


func test_attractor_pulls_with_constant_strength() -> void:
	var field: Subject = Subject.new()
	field.add_attractor(Vector2(100, 0), 2.0)
	assert_almost_eq(field.force_at(Vector2.ZERO), Vector2(2, 0), 0.0001)
	assert_almost_eq(field.force_at(Vector2(100, 50)), Vector2(0, -2), 0.0001)
	assert_almost_eq(field.potential_at(Vector2.ZERO), 200.0, 0.0001)


func test_repulsor_acts_only_inside_its_radius_and_grows_near_it() -> void:
	var field: Subject = Subject.new()
	field.add_repulsor(Vector2.ZERO, 100.0, 50.0)
	assert_eq(field.force_at(Vector2(60, 0)), Vector2.ZERO)
	assert_eq(field.potential_at(Vector2(60, 0)), 0.0)
	var far: Vector2 = field.force_at(Vector2(40, 0))
	var near: Vector2 = field.force_at(Vector2(10, 0))
	assert_gt(far.x, 0.0)
	assert_gt(near.x, far.x * 10.0)


func test_force_matches_the_numerical_gradient() -> void:
	var field: Subject = Subject.new()
	field.add_attractor(Vector2(80, -30), 1.5)
	field.add_repulsor(Vector2(30, 10), 400.0, 60.0)
	for point: Vector2 in [Vector2(10, 5), Vector2(45, 20), Vector2(60, -10)]:
		var h: float = 0.001
		var gradient := Vector2(
			(field.potential_at(point + Vector2(h, 0)) - field.potential_at(point - Vector2(h, 0))) / (2.0 * h),
			(field.potential_at(point + Vector2(0, h)) - field.potential_at(point - Vector2(0, h))) / (2.0 * h))
		assert_almost_eq(field.force_at(point), -gradient, 0.01)


func test_walks_around_an_offset_obstacle_to_the_goal() -> void:
	var field: Subject = Subject.new()
	field.add_attractor(Vector2(200, 0), 1.0)
	field.add_repulsor(Vector2(100, 8), 2000.0, 40.0)
	var walk: Dictionary = field.follow(Vector2.ZERO, 2.0, 400, 3.0)
	assert_true(walk["reached"])
	for point: Vector2 in walk["points"]:
		assert_gt(point.distance_to(Vector2(100, 8)), 10.0)


func test_symmetric_layout_stalls_in_a_local_minimum() -> void:
	var field: Subject = Subject.new()
	field.add_attractor(Vector2(200, 0), 1.0)
	field.add_repulsor(Vector2(100, 0), 20000.0, 60.0)
	var walk: Dictionary = field.follow(Vector2.ZERO, 1.0, 300, 3.0)
	assert_false(walk["reached"], "pushing straight at the obstacle never gets past it")
	var last: Vector2 = (walk["points"] as PackedVector2Array)[-1]
	assert_lt(last.x, 100.0)
