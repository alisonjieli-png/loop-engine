extends "../baltor_test.gd"
## Tests for BaltorFollowCamera2D: the dead zone rule, minimal focus moves, look-ahead in the travel direction
## that eases back when stopping, smoothing toward the goal and snapping.

const Subject := preload("../camera_follow_deadzone.gd")


func _camera() -> Subject:
	var camera: Subject = Subject.new()
	add_child(camera)
	camera.set_process(false)
	return camera


func test_deadzone_rule_moves_only_by_the_overshoot() -> void:
	var size := Vector2(64, 48)
	assert_eq(Subject.deadzone_follow(Vector2.ZERO, Vector2(20, -10), size), Vector2.ZERO, "inside the zone")
	assert_eq(Subject.deadzone_follow(Vector2.ZERO, Vector2(50, 0), size), Vector2(18, 0))
	assert_eq(Subject.deadzone_follow(Vector2.ZERO, Vector2(-40, 40), size), Vector2(-8, 16))


func test_small_moves_inside_the_zone_do_not_move_the_camera() -> void:
	var camera := _camera()
	camera.look_ahead_distance = 0.0
	camera.snap_to(Vector2(100, 100))
	for _i in range(10):
		camera.update_camera(Vector2(110, 95), 1.0 / 60.0)
	assert_eq(camera.get_focus(), Vector2(100, 100))
	assert_almost_eq(camera.global_position, Vector2(100, 100), 0.0001)


func test_look_ahead_follows_motion_and_eases_back() -> void:
	var camera := _camera()
	camera.snap_to(Vector2.ZERO)
	var target := Vector2.ZERO
	for _i in range(120):
		target += Vector2(300.0 / 60.0, 0)
		camera.update_camera(target, 1.0 / 60.0)
	assert_almost_eq(camera.get_look_ahead().x, 80.0, 2.0)
	assert_gt(camera.global_position.x, camera.get_focus().x, "the camera leads the target")
	for _i in range(240):
		camera.update_camera(target, 1.0 / 60.0)
	assert_lt(camera.get_look_ahead().length(), 0.5)


func test_camera_converges_on_focus_with_smoothing() -> void:
	var camera := _camera()
	camera.look_ahead_distance = 0.0
	camera.snap_to(Vector2.ZERO)
	camera.update_camera(Vector2(232, 0), 0.1)
	var expected_focus := Vector2(200, 0)
	assert_eq(camera.get_focus(), expected_focus)
	assert_almost_eq(camera.global_position.x, 200.0 * (1.0 - exp(-0.8)), 0.01)
	for _i in range(60):
		camera.update_camera(Vector2(232, 0), 0.1)
	assert_almost_eq(camera.global_position, expected_focus, 0.01)
