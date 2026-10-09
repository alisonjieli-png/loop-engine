extends "../baltor_test.gd"
## Tests for BaltorFormation: layout counts and spacing, wedge symmetry, circle radius, grid rows, rotation into
## the world, assignment without crossings and refused inputs.

const Subject := preload("../formation_slots.gd")
const Shape := Subject.Shape


func test_line_and_column_spacing() -> void:
	var line: PackedVector2Array = Subject.slot_offsets(Shape.LINE, 3, 10.0)
	assert_eq(line, PackedVector2Array([Vector2(0, -10), Vector2(0, 0), Vector2(0, 10)]))
	var column: PackedVector2Array = Subject.slot_offsets(Shape.COLUMN, 3, 5.0)
	assert_eq(column, PackedVector2Array([Vector2.ZERO, Vector2(-5, 0), Vector2(-10, 0)]))
	assert_eq(Subject.slot_offsets(Shape.LINE, 0, 10.0).size(), 0)


func test_wedge_is_symmetric_and_circle_keeps_a_radius() -> void:
	var wedge: PackedVector2Array = Subject.slot_offsets(Shape.WEDGE, 5, 8.0)
	assert_eq(wedge[0], Vector2.ZERO)
	assert_eq(wedge[1], Vector2(-8, -8))
	assert_eq(wedge[2], Vector2(-8, 8))
	assert_eq(wedge[4], Vector2(-16, 16))
	var circle: PackedVector2Array = Subject.slot_offsets(Shape.CIRCLE, 12, 10.0)
	var radius: float = circle[0].length()
	assert_almost_eq(radius, 10.0 * 12.0 / TAU, 0.0001)
	for point: Vector2 in circle:
		assert_almost_eq(point.length(), radius, 0.0001)
	assert_almost_eq(circle[0].distance_to(circle[1]), 2.0 * radius * sin(PI / 12.0), 0.0001)


func test_grid_fills_rows_behind_the_anchor() -> void:
	var grid: PackedVector2Array = Subject.slot_offsets(Shape.GRID, 5, 2.0)
	assert_eq(grid.size(), 5)
	assert_eq(grid[0], Vector2(0, -2))
	assert_eq(grid[2], Vector2(0, 2))
	assert_eq(grid[3], Vector2(-2, -2), "the second row starts behind")


func test_world_slots_rotate_and_translate() -> void:
	var placed: PackedVector2Array = Subject.world_slots(PackedVector2Array([Vector2(-10, 0)]), Vector2(100, 50), PI / 2.0)
	assert_almost_eq(placed[0], Vector2(100, 40), 0.0001)


func test_assignment_removes_crossings_and_beats_identity() -> void:
	var members := PackedVector2Array([Vector2(0, 10), Vector2(0, 0)])
	var slots := PackedVector2Array([Vector2(10, 0), Vector2(10, 10)])
	var assignment: PackedInt32Array = Subject.assign(members, slots)
	assert_eq(assignment, PackedInt32Array([1, 0]))
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for _trial in range(5):
		var crowd := PackedVector2Array()
		for _i in range(8):
			crowd.append(Vector2(rng.randf_range(-50, 50), rng.randf_range(-50, 50)))
		var targets: PackedVector2Array = Subject.world_slots(Subject.slot_offsets(Shape.WEDGE, 8, 6.0), Vector2(30, 0), 0.4)
		var chosen: PackedInt32Array = Subject.assign(crowd, targets)
		var identity := PackedInt32Array([0, 1, 2, 3, 4, 5, 6, 7])
		var unique: Dictionary = {}
		for slot: int in chosen:
			unique[slot] = true
		assert_eq(unique.size(), 8, "every slot is used once")
		assert_true(Subject.total_distance(crowd, targets, chosen) <= Subject.total_distance(crowd, targets, identity) + 0.0001)


func test_mismatched_sizes_are_refused() -> void:
	assert_eq(Subject.assign(PackedVector2Array([Vector2.ZERO]), PackedVector2Array()).size(), 0)
	assert_eq(Subject.assign(PackedVector2Array(), PackedVector2Array()).size(), 0)
