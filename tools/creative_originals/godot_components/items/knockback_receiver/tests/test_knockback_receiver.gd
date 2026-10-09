extends "../baltor_test.gd"
## Tests for BaltorKnockback: weight, exponential decay with a snap to zero, adding hits, stun rules and ignored
## inputs.

const Subject := preload("../knockback_receiver.gd")


func _receiver() -> Subject:
	var receiver: Subject = Subject.new()
	receiver.auto_advance = false
	add_child(receiver)
	return receiver


func test_weight_scales_and_friction_decays_exponentially() -> void:
	var receiver := _receiver()
	receiver.weight = 2.0
	receiver.apply_knockback(Vector2.RIGHT, 400.0)
	assert_eq(receiver.get_velocity(), Vector2(200, 0))
	receiver.advance(0.1)
	assert_almost_eq(receiver.get_velocity().x, 200.0 * exp(-0.8), 0.001)
	for _i in range(60):
		receiver.advance(0.05)
	assert_eq(receiver.get_velocity(), Vector2.ZERO, "slow knockback snaps to zero")


func test_hits_add_up() -> void:
	var receiver := _receiver()
	watch_signals(receiver)
	receiver.apply_knockback(Vector2.RIGHT, 100.0)
	receiver.apply_knockback(Vector2.UP, 100.0)
	assert_eq(receiver.get_velocity(), Vector2(100, -100))
	assert_eq(signal_emissions(receiver, &"knocked"), [[Vector2(100, 0)], [Vector2(100, -100)]])


func test_stun_follows_strength_is_capped_and_never_shortened() -> void:
	var receiver := _receiver()
	watch_signals(receiver)
	receiver.apply_knockback(Vector2.LEFT, 100.0)
	assert_almost_eq(receiver.get_stun_left(), 0.2)
	receiver.apply_knockback(Vector2.LEFT, 10.0)
	assert_almost_eq(receiver.get_stun_left(), 0.2, 0.00001, "a weak hit does not shorten the stun")
	receiver.apply_knockback(Vector2.LEFT, 10000.0)
	assert_almost_eq(receiver.get_stun_left(), 0.6, 0.00001, "capped")
	receiver.advance(0.61)
	assert_false(receiver.is_stunned())
	assert_signal_count(receiver, &"stun_ended", 1)


func test_zero_or_negative_hits_are_ignored() -> void:
	var receiver := _receiver()
	receiver.apply_knockback(Vector2.ZERO, 300.0)
	receiver.apply_knockback(Vector2.RIGHT, -50.0)
	receiver.apply_knockback(Vector2.RIGHT, 0.0)
	assert_eq(receiver.get_velocity(), Vector2.ZERO)
	assert_false(receiver.is_stunned())
	receiver.apply_knockback(Vector2.RIGHT, 300.0)
	receiver.clear()
	assert_eq(receiver.get_velocity(), Vector2.ZERO)
	assert_eq(receiver.get_stun_left(), 0.0)
