extends "../baltor_test.gd"
## Tests for BaltorGridMover: eased stepping, buffered chaining, blocked cells, diagonal rules and teleporting.

const Subject := preload("../grid_step_mover.gd")


func _mover() -> Subject:
	var mover: Subject = Subject.new()
	add_child(mover)
	mover.set_process(false)
	mover.set_cell(Vector2i(2, 2))
	return mover


func test_steps_one_cell_with_easing() -> void:
	var mover := _mover()
	watch_signals(mover)
	assert_eq(mover.position, Vector2(40, 40))
	assert_true(mover.try_move(Vector2i.RIGHT))
	assert_eq(mover.get_cell(), Vector2i(3, 2), "the logical cell changes at once")
	mover.advance(0.075)
	assert_almost_eq(mover.position, Vector2(48, 40), 0.001)
	mover.advance(0.0375)
	assert_almost_eq(mover.position.x, 40.0 + 16.0 * (0.75 * 0.75 * (3.0 - 1.5)), 0.001)
	mover.advance(0.1)
	assert_eq(mover.position, Vector2(56, 40))
	assert_false(mover.is_moving())
	assert_eq(signal_emissions(mover, &"step_finished"), [[Vector2i(3, 2)]])


func test_a_move_during_a_step_is_buffered_and_chained() -> void:
	var mover := _mover()
	watch_signals(mover)
	mover.try_move(Vector2i.DOWN)
	mover.advance(0.05)
	assert_true(mover.try_move(Vector2i.DOWN))
	mover.advance(0.1)
	assert_true(mover.is_moving(), "the buffered step started right away")
	mover.advance(0.15)
	assert_eq(mover.get_cell(), Vector2i(2, 4))
	assert_eq(signal_emissions(mover, &"step_started"), [[Vector2i(2, 2), Vector2i(2, 3)], [Vector2i(2, 3), Vector2i(2, 4)]])


func test_blocked_cells_bump_and_do_not_move() -> void:
	var mover := _mover()
	mover.blocked_check = func(cell: Vector2i) -> bool: return cell == Vector2i(1, 2)
	watch_signals(mover)
	assert_false(mover.try_move(Vector2i.LEFT))
	assert_eq(mover.get_cell(), Vector2i(2, 2))
	assert_false(mover.is_moving())
	assert_eq(signal_emissions(mover, &"bumped"), [[Vector2i(1, 2)]])


func test_diagonal_and_long_moves_are_refused_unless_allowed() -> void:
	var mover := _mover()
	assert_false(mover.try_move(Vector2i(1, 1)), "diagonal moves are off by default")
	assert_false(mover.try_move(Vector2i(2, 0)), "only neighbors")
	assert_false(mover.try_move(Vector2i.ZERO))
	mover.allow_diagonal = true
	assert_true(mover.try_move(Vector2i(1, 1)))
	assert_eq(mover.get_cell(), Vector2i(3, 3))


func test_set_cell_teleports_and_cancels() -> void:
	var mover := _mover()
	mover.try_move(Vector2i.UP)
	mover.advance(0.05)
	mover.set_cell(Vector2i(10, -1))
	assert_false(mover.is_moving())
	assert_eq(mover.position, Vector2(168, -8))
	assert_eq(mover.position_to_cell(Vector2(170, -3)), Vector2i(10, -1))
