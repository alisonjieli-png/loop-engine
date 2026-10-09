extends "../baltor_test.gd"
## Tests for BaltorTopDownMover2D: acceleration to the cap, diagonal clamp, friction, the reversal boost,
## eight-way snapping, facing sectors and a slide against a real wall.

const Subject := preload("../top_down_movement_2d.gd")
const DT: float = 1.0 / 60.0


func _mover() -> Subject:
	var mover: Subject = autofree(Subject.new())
	mover.use_input_actions = false
	return mover


func test_accelerates_to_max_speed_and_diagonals_are_not_faster() -> void:
	var mover := _mover()
	mover.set_input(Vector2.RIGHT)
	for _i in range(6):
		mover.step(DT)
	assert_almost_eq(mover.velocity.x, 140.0, 0.01)
	for _i in range(60):
		mover.step(DT)
	assert_almost_eq(mover.velocity.length(), 200.0, 0.01)
	mover.set_input(Vector2(1, 1))
	for _i in range(120):
		mover.step(DT)
	assert_almost_eq(mover.velocity.length(), 200.0, 0.01, "diagonal input is clamped to length 1")


func test_friction_stops_the_body() -> void:
	var mover := _mover()
	mover.velocity = Vector2(160, 0)
	mover.set_input(Vector2.ZERO)
	mover.step(0.05)
	assert_almost_eq(mover.velocity.x, 80.0, 0.01)
	mover.step(0.1)
	assert_eq(mover.velocity, Vector2.ZERO)


func test_reversal_uses_the_turn_boost() -> void:
	var boosted := _mover()
	boosted.velocity = Vector2(200, 0)
	boosted.set_input(Vector2.LEFT)
	boosted.step(0.05)
	assert_almost_eq(boosted.velocity.x, 200.0 - 1400.0 * 2.0 * 0.05, 0.01)
	var plain := _mover()
	plain.turn_boost = 1.0
	plain.velocity = Vector2(200, 0)
	plain.set_input(Vector2.LEFT)
	plain.step(0.05)
	assert_gt(plain.velocity.x, boosted.velocity.x)


func test_snapping_and_facing_sectors() -> void:
	var mover := _mover()
	mover.snap_eight_directions = true
	watch_signals(mover)
	mover.set_input(Vector2(1.0, 0.3))
	assert_almost_eq(mover.get_input(), Vector2.RIGHT, 0.0001)
	mover.set_input(Vector2(0.6, 0.5))
	assert_almost_eq(mover.get_input().normalized(), Vector2(1, 1).normalized(), 0.0001)
	assert_eq(mover.get_facing_index(), 1, "down-right")
	mover.set_input(Vector2(0, -1))
	assert_eq(mover.get_facing_index(), 6, "up")
	assert_eq(mover.get_facing_index(4), 3, "up in four sectors")
	mover.set_input(Vector2.ZERO)
	assert_almost_eq(mover.get_facing(), Vector2.UP, 0.0001, "facing keeps the last direction")
	assert_signal_count(mover, &"facing_changed", 2)


func test_slides_along_a_wall_in_the_physics_world() -> void:
	var wall := StaticBody2D.new()
	var wall_shape := CollisionShape2D.new()
	var rectangle := RectangleShape2D.new()
	rectangle.size = Vector2(20, 400)
	wall_shape.shape = rectangle
	wall.add_child(wall_shape)
	wall.position = Vector2(60, 0)
	add_child(wall)
	var mover: Subject = Subject.new()
	mover.use_input_actions = false
	var shape := CollisionShape2D.new()
	var circle := CircleShape2D.new()
	circle.radius = 8.0
	shape.shape = circle
	mover.add_child(shape)
	add_child(mover)
	mover.set_input(Vector2(1, 1))
	await wait_physics_frames(40)
	assert_almost_eq(mover.position.x, 60.0 - 10.0 - 8.0, 1.0, "stopped by the wall")
	assert_gt(mover.position.y, 50.0, "kept sliding down along it")
