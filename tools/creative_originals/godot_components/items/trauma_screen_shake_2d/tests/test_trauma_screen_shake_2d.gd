extends "../baltor_test.gd"
## Tests for BaltorTraumaShake2D: clamping and linear decay, the shake curve and bounds, repeatable noise per
## seed, and shaking then restoring a parent Camera2D.

const Subject := preload("../trauma_screen_shake_2d.gd")


func _shake() -> Subject:
	var shake: Subject = Subject.new()
	add_child(shake)
	return shake


func test_trauma_is_clamped_and_decays_linearly() -> void:
	var shake := _shake()
	shake.add_trauma(0.8)
	shake.advance(0.5)
	assert_almost_eq(shake.get_trauma(), 0.35, 0.00001)
	shake.add_trauma(2.0)
	assert_eq(shake.get_trauma(), 1.0)
	shake.advance(5.0)
	assert_eq(shake.get_trauma(), 0.0)


func test_shake_follows_the_curve_and_stays_within_bounds() -> void:
	var shake := _shake()
	shake.set_trauma(0.5)
	assert_almost_eq(shake.get_shake(), 0.25, 0.00001)
	var limit: Vector2 = shake.max_offset * shake.get_shake()
	var moved: bool = false
	for index in range(200):
		var time: float = index * 0.013
		var offset: Vector2 = shake.offset_at(time)
		assert_true(absf(offset.x) <= limit.x + 0.0001 and absf(offset.y) <= limit.y + 0.0001)
		assert_true(absf(shake.roll_at(time)) <= deg_to_rad(shake.max_roll_degrees) * 0.25 + 0.0001)
		moved = moved or offset.length() > 0.5
	assert_true(moved, "the offset is not stuck at zero")


func test_noise_repeats_for_a_seed_and_differs_between_seeds() -> void:
	var first := _shake()
	var second := _shake()
	var other := _shake()
	other.noise_seed = 99
	for shake: Subject in [first, second, other]:
		shake.set_trauma(1.0)
	var differs: bool = false
	for index in range(20):
		var time: float = index * 0.07
		assert_eq(first.offset_at(time), second.offset_at(time))
		differs = differs or not first.offset_at(time).is_equal_approx(other.offset_at(time))
	assert_true(differs, "another seed gives another motion")


func test_shakes_the_parent_camera_and_restores_it() -> void:
	var camera := Camera2D.new()
	camera.offset = Vector2(5, -3)
	camera.rotation = 0.2
	add_child(camera)
	var shake: Subject = Subject.new()
	camera.add_child(shake)
	watch_signals(shake)
	shake.add_trauma(0.6)
	shake.advance(0.05)
	assert_ne(camera.offset, Vector2(5, -3), "the camera moved")
	assert_true(camera.offset.distance_to(Vector2(5, -3)) <= shake.max_offset.length())
	for _i in range(40):
		shake.advance(0.05)
	assert_eq(shake.get_trauma(), 0.0)
	assert_eq(camera.offset, Vector2(5, -3))
	assert_almost_eq(camera.rotation, 0.2)
	assert_signal_count(shake, &"shake_started", 1)
	assert_signal_count(shake, &"shake_finished", 1)


func test_negative_trauma_never_starts_a_shake() -> void:
	var shake := _shake()
	watch_signals(shake)
	shake.add_trauma(-0.5)
	shake.advance(0.1)
	assert_eq(shake.get_trauma(), 0.0)
	assert_eq(shake.offset_at(1.0), Vector2.ZERO)
	assert_eq(shake.roll_at(1.0), 0.0)
	assert_signal_not_emitted(shake, &"shake_started")
