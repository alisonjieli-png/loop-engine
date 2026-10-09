extends "../baltor_test.gd"
## Tests for BaltorRaycastVehicle: the spring-damper and grip formulas, settling at the ride height on a real
## floor, driving forward under throttle and the airborne signal.

const Subject := preload("../raycast_vehicle_3d.gd")


func _ground() -> void:
	var ground := StaticBody3D.new()
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(200, 1, 200)
	shape.shape = box
	ground.add_child(shape)
	ground.position = Vector3(0, -0.5, 0)
	add_child(ground)


func _vehicle() -> Subject:
	var car: Subject = Subject.new()
	car.use_input_actions = false
	car.mass = 2.0
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(1.6, 0.3, 2.6)
	shape.shape = box
	shape.position.y = 0.4
	car.add_child(shape)
	car.position = Vector3(0, 1.5, 0)
	return car


func test_suspension_and_grip_formulas() -> void:
	assert_eq(Subject.suspension_force(0.0, 3.0, 30.0, 4.0, 1.0), 0.0, "no compression, no force")
	assert_eq(Subject.suspension_force(-0.2, 0.0, 30.0, 4.0, 1.0), 0.0, "a stretched spring does not pull")
	assert_almost_eq(Subject.suspension_force(0.1, 0.0, 30.0, 4.0, 2.0), 6.0)
	assert_almost_eq(Subject.suspension_force(0.1, 0.5, 30.0, 4.0, 2.0), 10.0)
	assert_eq(Subject.suspension_force(0.1, -5.0, 30.0, 4.0, 2.0), 0.0, "fast rebound clamps at zero")
	assert_almost_eq(Subject.lateral_force(2.0, 8.0, 0.5), -8.0)


func test_settles_at_the_ride_height() -> void:
	_ground()
	var car := _vehicle()
	add_child(car)
	watch_signals(car)
	await wait_physics_frames(150)
	assert_eq(car.grounded_wheel_count(), 4)
	var expected_compression: float = 9.8 / 30.0
	assert_almost_eq(car.get_wheel_compression(0), expected_compression, 0.03)
	assert_almost_eq(car.position.y, 0.5 - expected_compression + 0.35, 0.03)
	assert_lt(car.linear_velocity.length(), 0.2)
	assert_eq(signal_emissions(car, &"airborne_changed").back(), [false])


func test_throttle_drives_forward_and_steering_turns() -> void:
	_ground()
	var car := _vehicle()
	add_child(car)
	await wait_physics_frames(90)
	car.set_controls(1.0, 0.0)
	await wait_physics_frames(60)
	assert_gt(car.get_forward_speed(), 2.0)
	assert_lt(car.position.z, -1.0, "forward is -Z")
	var heading_before: Vector3 = -car.global_basis.z
	car.set_controls(1.0, 1.0)
	await wait_physics_frames(45)
	var heading_after: Vector3 = -car.global_basis.z
	assert_lt(heading_before.signed_angle_to(heading_after, Vector3.UP), -0.05, "steering right turns clockwise from above")


func test_lifting_the_car_reports_airborne_and_queries_are_safe() -> void:
	_ground()
	var car := _vehicle()
	add_child(car)
	watch_signals(car)
	await wait_physics_frames(60)
	assert_eq(car.get_wheel_count(), 4)
	assert_false(car.is_wheel_grounded(9), "out of range")
	assert_eq(car.get_wheel_compression(-1), 0.0)
	car.global_position = Vector3(0, 20, 0)
	car.linear_velocity = Vector3.ZERO
	await wait_physics_frames(3)
	assert_eq(car.grounded_wheel_count(), 0)
	assert_eq(signal_emissions(car, &"airborne_changed").back(), [true])
