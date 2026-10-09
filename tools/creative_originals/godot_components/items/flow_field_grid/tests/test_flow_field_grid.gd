extends "../baltor_test.gd"
## Tests for BaltorFlowField: distances on open ground, slow terrain, walls and corner cutting, unreachable cells,
## several goals, directions and traces.

const Subject := preload("../flow_field_grid.gd")


func test_open_ground_distances_and_directions() -> void:
	var field: Subject = Subject.new(8, 8)
	assert_eq(field.build([Vector2i(0, 0)]), 64)
	assert_almost_eq(field.get_distance(Vector2i(3, 0)), 3.0)
	assert_almost_eq(field.get_distance(Vector2i(3, 3)), 3.0 * 1.41421356, 0.0001)
	assert_almost_eq(field.direction_at(Vector2i(3, 0)), Vector2.LEFT, 0.0001)
	assert_almost_eq(field.direction_at(Vector2i(2, 2)), Vector2(-1, -1).normalized(), 0.0001)
	assert_eq(field.direction_at(Vector2i(0, 0)), Vector2.ZERO, "the goal has no direction")


func test_slow_terrain_is_avoided_when_cheaper() -> void:
	var field: Subject = Subject.new(5, 3)
	for x in range(1, 4):
		field.set_cost(Vector2i(x, 1), 10.0)
	field.build([Vector2i(4, 1)])
	var path: Array[Vector2i] = field.trace(Vector2i(0, 1))
	assert_eq(path[0], Vector2i(0, 1))
	assert_eq(path[path.size() - 1], Vector2i(4, 1))
	for cell: Vector2i in path.slice(1, path.size() - 1):
		assert_ne(cell.y, 1, "the mud row is avoided")


func test_walls_block_and_diagonals_do_not_cut_corners() -> void:
	var field: Subject = Subject.new(3, 3)
	field.set_cost(Vector2i(1, 0), 0.0)
	field.set_cost(Vector2i(0, 1), 0.0)
	field.build([Vector2i(1, 1)])
	assert_true(is_inf(field.get_distance(Vector2i(0, 0))), "boxed in by two walls, no corner cutting")
	assert_eq(field.direction_at(Vector2i(0, 0)), Vector2.ZERO)
	assert_eq(field.trace(Vector2i(0, 0)), [])
	assert_false(field.set_cost(Vector2i(5, 5), 2.0))


func test_several_goals_share_one_field() -> void:
	var field: Subject = Subject.new(10, 1)
	field.build([Vector2i(0, 0), Vector2i(9, 0)])
	assert_almost_eq(field.get_distance(Vector2i(3, 0)), 3.0)
	assert_almost_eq(field.get_distance(Vector2i(7, 0)), 2.0)
	assert_eq(field.direction_at(Vector2i(7, 0)), Vector2.RIGHT)
	assert_eq(field.direction_at(Vector2i(3, 0)), Vector2.LEFT)


func test_world_sampling_and_walls_as_goals() -> void:
	var field: Subject = Subject.new(4, 4, 10.0)
	field.set_cost(Vector2i(3, 3), -1.0)
	assert_eq(field.build([Vector2i(3, 3)]), 0, "a wall cannot be a goal")
	field.build([Vector2i(0, 3)])
	assert_eq(field.world_to_cell(Vector2(25, 31)), Vector2i(2, 3))
	assert_almost_eq(field.sample(Vector2(25, 35)), Vector2.LEFT, 0.0001)
