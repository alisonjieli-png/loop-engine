extends "../baltor_test.gd"
## Tests for BaltorDash: dash velocity and length, refusals, the invulnerability window, charges and recharge.

const Subject := preload("../dash_ability.gd")


func _dash(charges: int = 1) -> Subject:
	var dash: Subject = Subject.new()
	dash.max_charges = charges
	dash.auto_advance = false
	add_child(dash)
	return dash


func test_dash_moves_at_speed_for_its_duration() -> void:
	var dash := _dash()
	watch_signals(dash)
	assert_true(dash.try_dash(Vector2(3, 4)))
	assert_almost_eq(dash.get_dash_velocity(), Vector2(360, 480), 0.001)
	dash.advance(0.1)
	assert_true(dash.is_dashing())
	dash.advance(0.06)
	assert_false(dash.is_dashing())
	assert_eq(dash.get_dash_velocity(), Vector2.ZERO)
	assert_almost_eq(dash.get_exit_velocity(), Vector2(108, 144), 0.001)
	assert_signal_count(dash, &"dash_ended", 1)


func test_refuses_without_charge_while_dashing_or_without_direction() -> void:
	var dash := _dash()
	assert_false(dash.try_dash(Vector2.ZERO))
	assert_true(dash.try_dash(Vector2.RIGHT))
	assert_false(dash.try_dash(Vector2.LEFT), "already dashing")
	dash.advance(0.2)
	assert_false(dash.try_dash(Vector2.LEFT), "no charge left yet")
	dash.advance(0.45)
	assert_true(dash.try_dash(Vector2.LEFT), "recharged after 0.6 s")


func test_invulnerability_outlasts_the_dash() -> void:
	var dash := _dash()
	dash.try_dash(Vector2.UP)
	dash.advance(0.2)
	assert_false(dash.is_dashing())
	assert_true(dash.is_invulnerable())
	dash.advance(0.06)
	assert_false(dash.is_invulnerable())


func test_charges_recharge_one_at_a_time() -> void:
	var dash := _dash(3)
	watch_signals(dash)
	dash.try_dash(Vector2.RIGHT)
	dash.advance(0.2)
	dash.try_dash(Vector2.RIGHT)
	dash.advance(0.2)
	assert_eq(dash.get_charges(), 1)
	assert_almost_eq(dash.get_recharge_progress(), 0.4 / 0.6, 0.0001)
	dash.advance(0.2)
	assert_eq(dash.get_charges(), 2)
	dash.advance(0.6)
	assert_eq(dash.get_charges(), 3)
	assert_eq(dash.get_recharge_progress(), 0.0)
	assert_eq(signal_emissions(dash, &"charges_changed"), [[2], [1], [2], [3]])


func test_cancel_ends_the_dash_early() -> void:
	var dash := _dash()
	dash.try_dash(Vector2.DOWN)
	dash.cancel()
	assert_false(dash.is_dashing())
	assert_true(dash.is_invulnerable(), "cancelling keeps the invulnerability window")
