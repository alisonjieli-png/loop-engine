extends "../baltor_test.gd"
## Tests for BaltorPlatformerController2D: jump physics from design values, coyote time, the jump buffer,
## variable jump height, acceleration, the fall speed cap and a real landing on a static floor.

const Subject := preload("../platformer_controller_2d.gd")
const DT: float = 1.0 / 120.0


func _body() -> Subject:
	var body: Subject = autofree(Subject.new())
	body.use_input_actions = false
	return body


func _apex(body: Subject, release_after: float) -> float:
	body.press_jump()
	body.step(DT, true)
	var height: float = 0.0
	var peak: float = 0.0
	var elapsed: float = 0.0
	for _i in range(600):
		elapsed += DT
		if elapsed >= release_after:
			body.release_jump()
		var moving: Vector2 = body.step(DT, false)
		height -= moving.y * DT
		peak = maxf(peak, height)
		if moving.y > 0.0:
			break
	return peak


func test_held_jump_peaks_at_the_design_height() -> void:
	var body := _body()
	assert_almost_eq(body.jump_velocity(), -400.0, 0.001)
	assert_almost_eq(body.rise_gravity(), 2.0 * 72.0 / (0.36 * 0.36), 0.001)
	assert_almost_eq(_apex(body, 10.0), 72.0, 4.0)


func test_releasing_early_gives_a_lower_jump() -> void:
	var full: float = _apex(_body(), 10.0)
	var short: float = _apex(_body(), 0.05)
	assert_lt(short, full * 0.6)
	assert_gt(short, 5.0)


func test_coyote_time_allows_a_late_jump_but_not_a_very_late_one() -> void:
	var body := _body()
	watch_signals(body)
	body.step(DT, true)
	for _i in range(6):
		body.step(DT, false)
	body.press_jump()
	body.step(DT, false)
	assert_signal_count(body, &"jumped", 1)
	assert_lt(body.velocity.y, 0.0)
	var late := _body()
	watch_signals(late)
	late.step(DT, true)
	for _i in range(30):
		late.step(DT, false)
	late.press_jump()
	late.step(DT, false)
	assert_signal_not_emitted(late, &"jumped", "0.25 s off the ledge is longer than the coyote time")
	assert_gt(late.velocity.y, 0.0)


func test_jump_buffer_fires_on_landing_only_when_recent() -> void:
	var body := _body()
	watch_signals(body)
	body.step(DT, false)
	body.press_jump()
	for _i in range(6):
		body.step(DT, false)
	assert_signal_not_emitted(body, &"jumped")
	body.step(DT, true)
	assert_signal_count(body, &"jumped", 1)
	assert_almost_eq(body.velocity.y, body.jump_velocity(), 0.001)
	var stale := _body()
	watch_signals(stale)
	stale.step(DT, false)
	stale.press_jump()
	for _i in range(40):
		stale.step(DT, false)
	stale.step(DT, true)
	assert_signal_not_emitted(stale, &"jumped")
	assert_eq(stale.velocity.y, 0.0)


func test_ground_acceleration_reaches_and_caps_at_move_speed() -> void:
	var body := _body()
	body.set_move_axis(1.0)
	for _i in range(12):
		body.step(DT, true)
	assert_almost_eq(body.velocity.x, 180.0, 0.01)
	for _i in range(24):
		body.step(DT, true)
	assert_almost_eq(body.velocity.x, 220.0, 0.01)
	body.set_move_axis(0.0)
	for _i in range(60):
		body.step(DT, true)
	assert_eq(body.velocity.x, 0.0)
	body.set_move_axis(5.0)
	for _i in range(120):
		body.step(DT, true)
	assert_almost_eq(body.velocity.x, 220.0, 0.01, "the axis is clamped to 1")


func test_fall_speed_is_capped() -> void:
	var body := _body()
	for _i in range(240):
		body.step(DT, false)
	assert_almost_eq(body.velocity.y, body.max_fall_speed, 0.001)


func test_lands_on_a_static_floor_in_the_physics_world() -> void:
	var floor_body := StaticBody2D.new()
	var floor_shape := CollisionShape2D.new()
	var floor_rect := RectangleShape2D.new()
	floor_rect.size = Vector2(800, 40)
	floor_shape.shape = floor_rect
	floor_body.add_child(floor_shape)
	floor_body.position = Vector2(0, 120)
	add_child(floor_body)
	var body: Subject = Subject.new()
	body.use_input_actions = false
	var shape := CollisionShape2D.new()
	var box := RectangleShape2D.new()
	box.size = Vector2(16, 24)
	shape.shape = box
	body.add_child(shape)
	add_child(body)
	watch_signals(body)
	await wait_physics_frames(60)
	assert_true(body.is_on_floor())
	assert_signal_count(body, &"landed", 1)
	assert_gt(float(signal_emissions(body, &"landed")[0][0]), 100.0)
	assert_almost_eq(body.position.y, 88.0, 1.0)
