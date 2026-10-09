extends "../baltor_test.gd"
## Tests for BaltorWaypointMover: exact speed through corners, waiting, ping-pong and loop order, pausing,
## degenerate paths and carrying a rider in the physics world.

const Subject := preload("../moving_platform_path.gd")


func _platform(points: PackedVector2Array, ping_pong: bool = true, wait: float = 0.0) -> Subject:
	var platform: Subject = Subject.new()
	platform.waypoints = points
	platform.ping_pong = ping_pong
	platform.wait_time = wait
	platform.speed = 100.0
	platform.auto_advance = false
	platform.position = Vector2(50, 50)
	add_child(platform)
	return platform


func test_moves_at_exact_speed_through_corners() -> void:
	var platform := _platform(PackedVector2Array([Vector2.ZERO, Vector2(100, 0), Vector2(100, 100)]))
	var moved: Vector2 = platform.advance(0.5)
	assert_almost_eq(moved, Vector2(50, 0), 0.001)
	platform.advance(0.75)
	assert_almost_eq(platform.get_current_point(), Vector2(150, 75), 0.001, "the remaining 25 px carried around the corner")
	assert_eq(platform.get_target_index(), 2)


func test_waits_at_each_waypoint() -> void:
	var platform := _platform(PackedVector2Array([Vector2.ZERO, Vector2(100, 0)]), true, 0.5)
	platform.advance(1.0)
	assert_true(platform.is_waiting())
	platform.advance(0.3)
	assert_almost_eq(platform.get_current_point(), Vector2(150, 50), 0.001, "still waiting")
	platform.advance(0.3)
	assert_almost_eq(platform.get_current_point(), Vector2(140, 50), 0.001, "0.1 s of travel back after the wait")


func test_ping_pong_and_loop_visit_waypoints_in_order() -> void:
	var points := PackedVector2Array([Vector2.ZERO, Vector2(10, 0), Vector2(20, 0)])
	var bouncing := _platform(points, true)
	watch_signals(bouncing)
	for _i in range(10):
		bouncing.advance(0.1)
	assert_eq(signal_emissions(bouncing, &"waypoint_reached"), [[1], [2], [1], [0], [1], [2], [1], [0], [1], [2]])
	var looping := _platform(points, false)
	watch_signals(looping)
	for _i in range(6):
		looping.advance(0.1)
	assert_eq(signal_emissions(looping, &"waypoint_reached"), [[1], [2], [0], [1], [2]])


func test_pause_and_degenerate_paths_stay_still() -> void:
	var platform := _platform(PackedVector2Array([Vector2.ZERO, Vector2(100, 0)]))
	platform.pause()
	assert_eq(platform.advance(1.0), Vector2.ZERO)
	platform.resume()
	assert_almost_eq(platform.advance(0.1), Vector2(10, 0), 0.001)
	var single := _platform(PackedVector2Array([Vector2.ZERO]))
	assert_eq(single.advance(1.0), Vector2.ZERO)
	assert_eq(single.get_path_points(), PackedVector2Array([Vector2(50, 50)]))


func test_carries_a_rider_in_the_physics_world() -> void:
	var platform: Subject = Subject.new()
	platform.waypoints = PackedVector2Array([Vector2.ZERO, Vector2(400, 0)])
	platform.speed = 60.0
	platform.position = Vector2(0, 100)
	var shape := CollisionShape2D.new()
	var box := RectangleShape2D.new()
	box.size = Vector2(200, 20)
	shape.shape = box
	platform.add_child(shape)
	add_child(platform)
	var rider := CharacterBody2D.new()
	var rider_shape := CollisionShape2D.new()
	var rider_box := RectangleShape2D.new()
	rider_box.size = Vector2(16, 16)
	rider_shape.shape = rider_box
	rider.add_child(rider_shape)
	rider.position = Vector2(0, 82)
	var gravity_script := GDScript.new()
	gravity_script.source_code = "extends CharacterBody2D\n\n\nfunc _physics_process(delta: float) -> void:\n\tvelocity.y += 900.0 * delta\n\tmove_and_slide()\n"
	gravity_script.reload()
	rider.set_script(gravity_script)
	add_child(rider)
	await wait_physics_frames(60)
	assert_gt(rider.position.x, 30.0, "the rider moved with the platform")
	assert_almost_eq(rider.position.x, platform.get_current_point().x, 3.0)
