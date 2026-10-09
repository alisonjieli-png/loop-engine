extends "../baltor_test.gd"
## Tests for BaltorInfluenceMap: stamp falloff, walls, propagation around walls, best cells, combining maps,
## coordinate conversion and refusals.

const Subject := preload("../influence_map.gd")


func test_stamp_falls_off_with_distance_and_skips_walls() -> void:
	var map: Subject = Subject.new(9, 9)
	map.set_blocked(Vector2i(5, 4), true)
	map.stamp(Vector2i(4, 4), 10.0, 3)
	assert_almost_eq(map.get_value(Vector2i(4, 4)), 10.0)
	assert_almost_eq(map.get_value(Vector2i(6, 4)), 10.0 * (1.0 - 2.0 / 4.0))
	assert_eq(map.get_value(Vector2i(5, 4)), 0.0, "walls hold no influence")
	assert_eq(map.get_value(Vector2i(8, 4)), 0.0, "outside the radius")
	map.clear()
	map.stamp(Vector2i(4, 4), 8.0, 2, Subject.Falloff.CONSTANT)
	assert_almost_eq(map.get_value(Vector2i(4, 6)), 8.0)
	assert_eq(map.get_value(Vector2i(6, 6)), 0.0, "the corner is farther than the radius")


func test_propagation_spreads_decays_and_goes_around_walls() -> void:
	var map: Subject = Subject.new(7, 5)
	for y in range(0, 4):
		map.set_blocked(Vector2i(3, y), true)
	map.set_value(Vector2i(1, 1), 1.0)
	map.propagate(0.5, 1.0, 12)
	var near: float = map.get_value(Vector2i(2, 1))
	assert_almost_eq(near, exp(-0.5), 0.0001)
	var behind: float = map.get_value(Vector2i(4, 1))
	assert_gt(behind, 0.0, "influence flows around the wall through row 4")
	assert_lt(behind, map.get_value(Vector2i(2, 1)) * exp(-0.5 * 2.0), "the detour costs more than going straight")
	assert_eq(map.get_value(Vector2i(3, 1)), 0.0)


func test_best_cell_finds_highest_and_lowest_in_range() -> void:
	var map: Subject = Subject.new(10, 10)
	map.set_value(Vector2i(2, 2), 5.0)
	map.set_value(Vector2i(3, 2), -4.0)
	map.set_value(Vector2i(9, 9), 50.0)
	assert_eq(map.best_cell(Vector2i(2, 2), 2, true), Vector2i(2, 2), "the 50 is out of range")
	assert_eq(map.best_cell(Vector2i(2, 2), 2, false), Vector2i(3, 2))
	var walled: Subject = Subject.new(1, 1)
	walled.set_blocked(Vector2i(0, 0), true)
	assert_eq(walled.best_cell(Vector2i(0, 0), 3), Vector2i(-1, -1))


func test_combine_builds_a_control_map() -> void:
	var friends: Subject = Subject.new(4, 4)
	var enemies: Subject = Subject.new(4, 4)
	friends.set_value(Vector2i(1, 1), 3.0)
	enemies.set_value(Vector2i(1, 1), 1.0)
	enemies.set_value(Vector2i(2, 2), 2.0)
	assert_true(friends.combine(enemies, -1.0))
	assert_eq(friends.get_value(Vector2i(1, 1)), 2.0)
	assert_eq(friends.get_value(Vector2i(2, 2)), -2.0)
	assert_false(friends.combine(Subject.new(5, 4)), "sizes must match")


func test_coordinates_and_refusals_outside_the_map() -> void:
	var map: Subject = Subject.new(4, 3, 16.0)
	assert_eq(map.world_to_cell(Vector2(17.0, 40.0)), Vector2i(1, 2))
	assert_eq(map.cell_to_world(Vector2i(1, 2)), Vector2(24.0, 40.0))
	assert_eq(map.world_to_cell(Vector2(-1.0, 0.0)), Vector2i(-1, 0))
	assert_false(map.set_value(Vector2i(4, 0), 1.0))
	assert_false(map.set_blocked(Vector2i(0, -1), true))
	assert_eq(map.get_value(Vector2i(10, 10)), 0.0)
	assert_eq(map.get_values().size(), 12)
