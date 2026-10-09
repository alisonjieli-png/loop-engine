extends "../baltor_test.gd"
## Tests for BaltorPerception: the view cone, range and peripheral sense, occlusion, spotting and forgetting,
## last known positions and hearing scaled by loudness.

const Subject := preload("../perception_senses.gd")


func test_view_cone_range_and_peripheral_sense() -> void:
	var eyes: Subject = Subject.new()
	var origin := Vector2.ZERO
	var east := Vector2.RIGHT
	assert_true(eyes.can_see(origin, east, Vector2(300, 100)), "about 18 degrees off the facing")
	assert_false(eyes.can_see(origin, east, Vector2(100, 200)), "about 63 degrees, outside the 55 degree half cone")
	assert_false(eyes.can_see(origin, east, Vector2(-300, 0)), "behind")
	assert_false(eyes.can_see(origin, east, Vector2(401, 0)), "too far")
	assert_true(eyes.can_see(origin, east, Vector2(-30, 0)), "close enough to notice from behind")


func test_occlusion_callable_blocks_sight() -> void:
	var eyes: Subject = Subject.new()
	var wall_at_x := 150.0
	var occluded := func(from: Vector2, to: Vector2) -> bool: return minf(from.x, to.x) < wall_at_x and maxf(from.x, to.x) > wall_at_x
	assert_false(eyes.can_see(Vector2.ZERO, Vector2.RIGHT, Vector2(200, 0), occluded))
	assert_true(eyes.can_see(Vector2.ZERO, Vector2.RIGHT, Vector2(100, 0), occluded))


func test_observe_spots_once_remembers_then_forgets() -> void:
	var eyes: Subject = Subject.new()
	eyes.memory_seconds = 1.0
	watch_signals(eyes)
	eyes.observe(0.1, Vector2.ZERO, Vector2.RIGHT, {&"thief": Vector2(100, 0)})
	eyes.observe(0.1, Vector2.ZERO, Vector2.RIGHT, {&"thief": Vector2(120, 0)})
	assert_eq(signal_emissions(eyes, &"target_spotted"), [[&"thief", Vector2(100, 0)]])
	assert_true(eyes.is_visible(&"thief"))
	eyes.observe(0.4, Vector2.ZERO, Vector2.LEFT, {&"thief": Vector2(150, 0)})
	assert_false(eyes.is_visible(&"thief"))
	assert_eq(eyes.get_last_known_position(&"thief"), Vector2(120, 0), "the hidden move is not known")
	assert_almost_eq(eyes.get_time_since_seen(&"thief"), 0.4)
	eyes.observe(0.7, Vector2.ZERO, Vector2.LEFT, {})
	assert_signal_count(eyes, &"target_lost", 1)
	assert_eq(eyes.get_known_targets(), [])
	assert_eq(eyes.get_time_since_seen(&"thief"), -1.0)


func test_hearing_scales_with_loudness() -> void:
	var ears: Subject = Subject.new()
	watch_signals(ears)
	assert_false(ears.report_noise(Vector2.ZERO, Vector2(400, 0), 1.0))
	assert_true(ears.report_noise(Vector2.ZERO, Vector2(400, 0), 2.0))
	assert_eq(ears.get_last_noise(), {"heard": true, "at": Vector2(400, 0)})
	assert_false(ears.can_hear(Vector2.ZERO, Vector2(1, 0), -1.0), "negative loudness is silent")
	assert_signal_count(ears, &"noise_heard", 1)


func test_zero_facing_sees_only_peripheral_targets() -> void:
	var eyes: Subject = Subject.new()
	assert_false(eyes.can_see(Vector2.ZERO, Vector2.ZERO, Vector2(100, 0)))
	assert_true(eyes.can_see(Vector2.ZERO, Vector2.ZERO, Vector2(10, 0)))
	eyes.observe(0.1, Vector2.ZERO, Vector2.RIGHT, {&"a": Vector2(50, 0)})
	eyes.forget_all()
	assert_eq(eyes.get_known_targets(), [])
