extends "../baltor_test.gd"
## Tests for BaltorWallJump2D: the slide cap, jumping away from the wall, wall coyote time, the input lock and
## the rules on the floor.

const Subject := preload("../wall_slide_jump_2d.gd")
const DT: float = 1.0 / 60.0
const LEFT_WALL_NORMAL := Vector2(1, 0)


func _helper() -> Subject:
	return autofree(Subject.new())


func test_slide_caps_the_fall_only_when_pressing_into_the_wall() -> void:
	var helper := _helper()
	watch_signals(helper)
	var pressing: Vector2 = helper.apply(Vector2(0, 400), true, false, LEFT_WALL_NORMAL, -1.0, false, DT)
	assert_eq(pressing.y, 120.0)
	assert_true(helper.is_sliding())
	var released: Vector2 = helper.apply(Vector2(0, 400), true, false, LEFT_WALL_NORMAL, 0.0, false, DT)
	assert_eq(released.y, 400.0, "no input toward the wall, no slide")
	var rising: Vector2 = helper.apply(Vector2(0, -200), true, false, LEFT_WALL_NORMAL, -1.0, false, DT)
	assert_eq(rising.y, -200.0, "rising is never slowed")
	assert_eq(signal_emissions(helper, &"wall_slide_started").size(), 1)
	assert_eq(signal_emissions(helper, &"wall_slide_ended").size(), 1)


func test_wall_jump_pushes_away_and_up() -> void:
	var helper := _helper()
	watch_signals(helper)
	var jumped: Vector2 = helper.apply(Vector2(0, 100), true, false, LEFT_WALL_NORMAL, -1.0, true, DT)
	assert_eq(jumped, Vector2(260, -380))
	assert_eq(signal_emissions(helper, &"wall_jumped"), [[1.0]])
	var right_wall: Vector2 = _helper().apply(Vector2.ZERO, true, false, Vector2(-1, 0), 1.0, true, DT)
	assert_eq(right_wall, Vector2(-260, -380))


func test_wall_coyote_time_allows_a_late_jump_only() -> void:
	var helper := _helper()
	helper.apply(Vector2(0, 50), true, false, LEFT_WALL_NORMAL, -1.0, false, DT)
	for _i in range(3):
		helper.apply(Vector2(0, 50), false, false, Vector2.ZERO, 0.0, false, DT)
	assert_eq(helper.apply(Vector2(0, 50), false, false, Vector2.ZERO, 0.0, true, DT), Vector2(260, -380))
	var late := _helper()
	late.apply(Vector2(0, 50), true, false, LEFT_WALL_NORMAL, -1.0, false, DT)
	for _i in range(12):
		late.apply(Vector2(0, 50), false, false, Vector2.ZERO, 0.0, false, DT)
	assert_eq(late.apply(Vector2(0, 50), false, false, Vector2.ZERO, 0.0, true, DT), Vector2(0, 50))


func test_input_toward_the_wall_is_locked_briefly() -> void:
	var helper := _helper()
	helper.apply(Vector2.ZERO, true, false, LEFT_WALL_NORMAL, -1.0, true, DT)
	assert_eq(helper.filter_input(-1.0), 0.0, "back toward the wall")
	assert_eq(helper.filter_input(1.0), 1.0, "away from the wall is free")
	for _i in range(12):
		helper.apply(Vector2(260, -300), false, false, Vector2.ZERO, 0.0, false, DT)
	assert_eq(helper.get_lock_time_left(), 0.0)
	assert_eq(helper.filter_input(-1.0), -1.0)


func test_no_slide_or_wall_jump_from_the_floor() -> void:
	var helper := _helper()
	watch_signals(helper)
	var grounded: Vector2 = helper.apply(Vector2(0, 30), true, true, LEFT_WALL_NORMAL, -1.0, true, DT)
	assert_eq(grounded, Vector2(0, 30))
	assert_false(helper.is_sliding())
	assert_signal_not_emitted(helper, &"wall_jumped")
