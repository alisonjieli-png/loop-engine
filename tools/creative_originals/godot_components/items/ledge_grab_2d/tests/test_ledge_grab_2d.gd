extends "../baltor_test.gd"
## Tests for BaltorLedgeGrab2D: the detection rule, grabbing only while falling, hang and climb positions, the
## climb path, dropping with a cooldown and probing a real wall.

const Subject := preload("../ledge_grab_2d.gd")


func _ledge() -> Subject:
	return autofree(Subject.new())


func test_detection_needs_chest_wall_open_head_and_falling() -> void:
	assert_true(Subject.detect(true, false, true))
	assert_false(Subject.detect(true, true, true), "a full wall is not a ledge")
	assert_false(Subject.detect(false, false, true))
	assert_false(Subject.detect(true, false, false), "rising never grabs")


func test_grab_hangs_at_the_mirrored_offset() -> void:
	var ledge := _ledge()
	watch_signals(ledge)
	assert_false(ledge.try_grab(Vector2(100, 50), 1.0, false), "not while rising")
	assert_true(ledge.try_grab(Vector2(100, 50), -1.0, true))
	assert_eq(ledge.get_state(), Subject.State.HANGING)
	assert_eq(ledge.advance(0.016), Vector2(110, 64), "facing left mirrors x")
	assert_false(ledge.try_grab(Vector2(0, 0), 1.0, true), "already hanging")
	assert_eq(signal_emissions(ledge, &"grabbed"), [[Vector2(100, 50)]])


func test_climb_goes_up_then_forward_and_ends_free() -> void:
	var ledge := _ledge()
	watch_signals(ledge)
	ledge.try_grab(Vector2(100, 50), 1.0, true)
	assert_true(ledge.climb())
	var halfway: Vector2 = ledge.advance(0.125)
	assert_almost_eq(halfway, Vector2(90, 34), 0.001, "fully lifted, not yet forward")
	var finish: Vector2 = ledge.advance(0.125)
	assert_almost_eq(finish, Vector2(110, 34), 0.001)
	assert_eq(ledge.get_state(), Subject.State.FREE)
	assert_eq(signal_emissions(ledge, &"climbed"), [[Vector2(110, 34)]])
	assert_false(ledge.climb(), "nothing to climb when free")


func test_drop_starts_a_regrab_cooldown() -> void:
	var ledge := _ledge()
	ledge.try_grab(Vector2(10, 10), 1.0, true)
	assert_true(ledge.drop())
	assert_false(ledge.try_grab(Vector2(10, 10), 1.0, true), "cooling down")
	ledge.advance(0.31)
	assert_true(ledge.try_grab(Vector2(10, 10), 1.0, true))
	assert_false(_ledge().drop(), "dropping needs a hang")


func test_probe_finds_the_corner_of_a_real_wall() -> void:
	var wall := StaticBody2D.new()
	var shape := CollisionShape2D.new()
	var box := RectangleShape2D.new()
	box.size = Vector2(40, 40)
	shape.shape = box
	wall.add_child(shape)
	wall.position = Vector2(30, 10)
	add_child(wall)
	await wait_physics_frames(2)
	var ledge := _ledge()
	var space: PhysicsDirectSpaceState2D = get_viewport().find_world_2d().direct_space_state
	var result: Dictionary = ledge.probe_ledge(space, Vector2(0, 0), 1.0)
	assert_true(result["found"])
	assert_almost_eq(result["corner"], Vector2(10, -10), 0.01)
	var low: Dictionary = ledge.probe_ledge(space, Vector2(0, 30), 1.0)
	assert_false(low["found"], "lower down the wall covers the head ray too")
