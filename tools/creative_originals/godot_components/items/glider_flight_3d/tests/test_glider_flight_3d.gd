extends "../baltor_test.gd"
## Tests for BaltorGlider: the sink polar, trading speed and height, banked turns and levelling, the stall and
## recovery, and the attitude limits.

const Subject := preload("../glider_flight_3d.gd")
const DT: float = 1.0 / 60.0


func _glider() -> Subject:
	var glider: Subject = Subject.new()
	glider.use_input_actions = false
	add_child(glider)
	glider.set_physics_process(false)
	return glider


func test_sink_polar_is_lowest_at_the_best_speed() -> void:
	var glider := _glider()
	assert_almost_eq(glider.sink_rate(12.0), 1.0)
	assert_gt(glider.sink_rate(8.0), 1.0)
	assert_gt(glider.sink_rate(20.0), 1.0)
	assert_almost_eq(glider.sink_rate(6.0), 1.0 * (0.5 + 2.0) * 0.5)
	assert_almost_eq(glider.get_glide_ratio(), 12.0)


func test_diving_gains_speed_and_climbing_loses_it() -> void:
	var diver := _glider()
	diver.set_controls(-1.0, 0.0)
	for _i in range(30):
		diver.step(DT)
	diver.set_controls(0.0, 0.0)
	for _i in range(60):
		diver.step(DT)
	assert_gt(diver.get_speed(), 16.0)
	var climber := _glider()
	climber.set_controls(1.0, 0.0)
	for _i in range(20):
		climber.step(DT)
	assert_lt(climber.get_speed(), 12.0)
	var velocity: Vector3 = climber.step(DT)
	assert_gt(velocity.y, -1.5, "climbing mostly cancels the sink")


func test_banking_turns_right_and_wings_level_without_input() -> void:
	var glider := _glider()
	glider.set_controls(0.0, 1.0)
	for _i in range(30):
		glider.step(DT)
	assert_almost_eq(glider.get_roll_degrees(), 45.0, 0.01)
	assert_lt(glider.get_heading_degrees(), -5.0, "right bank turns clockwise from above")
	glider.set_controls(0.0, 0.0)
	for _i in range(90):
		glider.step(DT)
	assert_eq(glider.get_roll_degrees(), 0.0)
	glider.set_controls(0.0, 1.0)
	for _i in range(200):
		glider.step(DT)
	assert_almost_eq(glider.get_roll_degrees(), 60.0, 0.01, "the bank limit holds")


func test_pulling_up_stalls_then_the_nose_drops_and_recovers() -> void:
	var glider := _glider()
	watch_signals(glider)
	glider.set_controls(1.0, 0.0)
	var dropped: bool = false
	for _i in range(600):
		glider.step(DT)
		if glider.is_stalled() and glider.get_pitch_degrees() < 0.0:
			dropped = true
	assert_signal_emitted(glider, &"stalled")
	assert_true(dropped, "the nose fell while stalled")
	assert_signal_emitted(glider, &"recovered")
	assert_true(glider.get_pitch_degrees() <= 45.0 + 0.001)


func test_level_flight_moves_forward_and_sinks_slowly() -> void:
	var glider := _glider()
	var velocity: Vector3 = glider.step(DT)
	assert_almost_eq(velocity.z, -glider.get_speed(), 0.0001, "forward is -Z")
	assert_almost_eq(velocity.y, -glider.sink_rate(glider.get_speed()), 0.0001)
	glider.set_speed(-5.0)
	assert_eq(glider.get_speed(), 0.0, "speed never goes negative")
