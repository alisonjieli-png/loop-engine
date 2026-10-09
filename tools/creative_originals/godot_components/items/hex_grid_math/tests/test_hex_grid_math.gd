extends "../baltor_test.gd"
## Tests for BaltorHexGrid: cube identities, distance, rings and spirals, lines, rotation, pixel round trips,
## reachable areas and paths around walls.

const Subject := preload("../hex_grid_math.gd")


func test_cube_coordinates_sum_to_zero_and_distance_is_symmetric() -> void:
	for hex: Vector2i in Subject.spiral(Vector2i(2, -1), 3):
		var cube: Vector3i = Subject.axial_to_cube(hex)
		assert_eq(cube.x + cube.y + cube.z, 0)
		assert_eq(Subject.cube_to_axial(cube), hex)
	assert_eq(Subject.distance(Vector2i(0, 0), Vector2i(3, -1)), 3)
	assert_eq(Subject.distance(Vector2i(-2, 4), Vector2i(1, 0)), 4)
	assert_eq(Subject.distance(Vector2i(1, 0), Vector2i(-2, 4)), 4)


func test_rings_and_spirals_have_the_expected_sizes_and_distances() -> void:
	var center := Vector2i(1, 1)
	assert_eq(Subject.ring(center, 0), [center])
	for radius: int in [1, 2, 5]:
		var hexes: Array[Vector2i] = Subject.ring(center, radius)
		assert_eq(hexes.size(), 6 * radius)
		var unique: Dictionary = {}
		for hex: Vector2i in hexes:
			assert_eq(Subject.distance(center, hex), radius)
			unique[hex] = true
		assert_eq(unique.size(), 6 * radius)
	assert_eq(Subject.spiral(center, 4).size(), 1 + 3 * 4 * 5)
	assert_true(Subject.ring(center, -1).is_empty(), "a negative radius gives no hexes")


func test_line_steps_through_neighbors_from_end_to_end() -> void:
	var a := Vector2i(0, 0)
	var b := Vector2i(4, -2)
	var hexes: Array[Vector2i] = Subject.line(a, b)
	assert_eq(hexes.size(), Subject.distance(a, b) + 1)
	assert_eq(hexes[0], a)
	assert_eq(hexes[hexes.size() - 1], b)
	for index in range(1, hexes.size()):
		assert_eq(Subject.distance(hexes[index - 1], hexes[index]), 1)
	assert_eq(Subject.line(b, b), [b])


func test_rotation_turns_neighbors_and_six_turns_return() -> void:
	assert_eq(Subject.rotate(Vector2i(1, 0), Vector2i.ZERO, 1), Vector2i(1, -1))
	assert_eq(Subject.rotate(Vector2i(1, 0), Vector2i.ZERO, -1), Vector2i(0, 1))
	var hex := Vector2i(3, -1)
	var center := Vector2i(-1, 2)
	assert_eq(Subject.rotate(hex, center, 6), hex)
	assert_eq(Subject.distance(center, Subject.rotate(hex, center, 2)), Subject.distance(center, hex))


func test_pixel_conversion_round_trips_in_both_layouts() -> void:
	for pointy: bool in [true, false]:
		for hex: Vector2i in Subject.spiral(Vector2i.ZERO, 4):
			var center: Vector2 = Subject.to_pixel(hex, 32.0, pointy)
			assert_eq(Subject.from_pixel(center, 32.0, pointy), hex)
			assert_eq(Subject.from_pixel(center + Vector2(9.0, -7.0), 32.0, pointy), hex)
	var points: PackedVector2Array = Subject.corners(Vector2i(2, 1), 10.0)
	assert_eq(points.size(), 6)
	for point: Vector2 in points:
		assert_almost_eq(point.distance_to(Subject.to_pixel(Vector2i(2, 1), 10.0)), 10.0, 0.0001)


func test_path_goes_around_a_wall_and_refuses_an_enclosed_goal() -> void:
	var wall: Dictionary = {}
	for r in range(-3, 3):
		wall[Vector2i(1, r)] = true
	var passable := func(hex: Vector2i) -> bool:
		return not wall.has(hex) and Subject.distance(Vector2i.ZERO, hex) <= 6
	var path: Array[Vector2i] = Subject.find_path(Vector2i(0, 0), Vector2i(3, 0), passable)
	assert_false(path.is_empty())
	assert_eq(path[0], Vector2i(0, 0))
	assert_eq(path[path.size() - 1], Vector2i(3, 0))
	for index in range(1, path.size()):
		assert_eq(Subject.distance(path[index - 1], path[index]), 1)
		assert_false(wall.has(path[index]))
	assert_gt(path.size() - 1, 3, "the wall forces a detour")
	var goal := Vector2i(-4, 2)
	var fence: Array[Vector2i] = Subject.ring(goal, 1)
	var fenced := func(hex: Vector2i) -> bool:
		return not fence.has(hex) and Subject.distance(Vector2i.ZERO, hex) <= 8
	assert_eq(Subject.find_path(Vector2i(0, 0), goal, fenced), [])


func test_reachable_respects_steps_and_blocked_hexes() -> void:
	var blocked: Dictionary = {Vector2i(1, 0): true, Vector2i(1, -1): true}
	var passable := func(hex: Vector2i) -> bool: return not blocked.has(hex)
	var area: Array[Vector2i] = Subject.reachable(Vector2i.ZERO, 2, passable)
	assert_has(area, Vector2i.ZERO)
	assert_false(area.has(Vector2i(1, 0)))
	assert_false(area.has(Vector2i(2, -1)), "behind the blocked pair it needs three steps")
	for hex: Vector2i in area:
		assert_true(Subject.distance(Vector2i.ZERO, hex) <= 2)
	var open_area: Array[Vector2i] = Subject.reachable(Vector2i.ZERO, 2, func(_hex: Vector2i) -> bool: return true)
	assert_eq(open_area.size(), 19)
