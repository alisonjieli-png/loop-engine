extends "../baltor_test.gd"
## Tests for BaltorFlock: neighbor queries against brute force, separation, cohesion, alignment of a group, speed
## limits and wrapping.

const Subject := preload("../boids_flock.gd")


func _random_flock(count: int, seed_value: int) -> Subject:
	var flock: Subject = Subject.new()
	var rng := RandomNumberGenerator.new()
	rng.seed = seed_value
	for _i in range(count):
		flock.add_boid(Vector2(rng.randf_range(0, 300), rng.randf_range(0, 300)),
				Vector2.from_angle(rng.randf_range(0, TAU)) * 60.0)
	return flock


func test_neighbor_queries_match_brute_force() -> void:
	var flock := _random_flock(60, 3)
	var positions: PackedVector2Array = flock.get_positions()
	for index in range(0, 60, 7):
		var expected := PackedInt32Array()
		for other in range(60):
			if other != index and positions[other].distance_to(positions[index]) <= 50.0:
				expected.append(other)
		assert_eq(flock.neighbors_of(index), expected)


func test_separation_pushes_close_boids_apart() -> void:
	var flock: Subject = Subject.new()
	flock.alignment_weight = 0.0
	flock.cohesion_weight = 0.0
	flock.add_boid(Vector2(0, 0))
	flock.add_boid(Vector2(5, 0))
	for _i in range(30):
		flock.step(1.0 / 60.0)
	var positions: PackedVector2Array = flock.get_positions()
	assert_gt(positions[0].distance_to(positions[1]), 15.0)
	assert_lt(positions[0].x, 0.0)


func test_cohesion_pulls_a_loose_group_together() -> void:
	var flock: Subject = Subject.new()
	flock.separation_weight = 0.0
	flock.alignment_weight = 0.0
	flock.max_speed = 40.0
	for point: Vector2 in [Vector2(0, 0), Vector2(40, 0), Vector2(20, 35)]:
		flock.add_boid(point)
	var before: float = _spread(flock.get_positions())
	for _i in range(20):
		flock.step(1.0 / 60.0)
	assert_lt(_spread(flock.get_positions()), before)


func test_alignment_makes_a_group_head_the_same_way() -> void:
	var flock: Subject = Subject.new()
	flock.separation_weight = 0.0
	flock.cohesion_weight = 0.0
	var rng := RandomNumberGenerator.new()
	rng.seed = 11
	for index in range(12):
		flock.add_boid(Vector2(index % 4, floori(index / 4.0)) * 10.0, Vector2.from_angle(rng.randf_range(0, TAU)) * 60.0)
	var before: float = _heading_order(flock.get_velocities())
	for _i in range(120):
		flock.step(1.0 / 60.0)
	assert_gt(_heading_order(flock.get_velocities()), 0.95)
	assert_gt(_heading_order(flock.get_velocities()), before)
	for velocity: Vector2 in flock.get_velocities():
		assert_true(velocity.length() <= flock.max_speed + 0.001)


func test_bounds_wrap_positions() -> void:
	var flock: Subject = Subject.new()
	flock.bounds = Rect2(0, 0, 100, 100)
	flock.add_boid(Vector2(99, 50), Vector2(120, 0))
	flock.step(0.1)
	assert_almost_eq(flock.get_positions()[0], Vector2(11, 50), 0.001)
	assert_eq(flock.get_count(), 1)
	assert_eq(flock.steering_of(0), Vector2.ZERO, "a lone boid has no neighbors")


func _spread(points: PackedVector2Array) -> float:
	var center := Vector2.ZERO
	for point: Vector2 in points:
		center += point
	center /= points.size()
	var total: float = 0.0
	for point: Vector2 in points:
		total += point.distance_to(center)
	return total


func _heading_order(velocities: PackedVector2Array) -> float:
	var sum := Vector2.ZERO
	for velocity: Vector2 in velocities:
		if velocity.length_squared() > 0.0:
			sum += velocity.normalized()
	return sum.length() / velocities.size()
