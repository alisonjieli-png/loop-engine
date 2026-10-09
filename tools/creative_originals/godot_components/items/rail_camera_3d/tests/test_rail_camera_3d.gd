extends "../baltor_test.gd"
## Tests for BaltorRailCamera3D: projecting the target onto the rail, lead and clamping, smoothing along the rail
## and looking at the target.

const Subject := preload("../rail_camera_3d.gd")


func _rig(lead: float = 0.0, speed: float = 0.0) -> Subject:
	var rail := Path3D.new()
	rail.name = "Rail"
	rail.curve = Curve3D.new()
	rail.curve.add_point(Vector3(0, 2, 6))
	rail.curve.add_point(Vector3(20, 2, 6))
	add_child(rail)
	var camera: Subject = Subject.new()
	camera.path_node = NodePath("../Rail")
	camera.lead_distance = lead
	camera.follow_speed = speed
	camera.look_offset = Vector3.ZERO
	add_child(camera)
	camera.set_process(false)
	return camera


func test_camera_sits_at_the_closest_rail_point() -> void:
	var camera := _rig()
	camera.update_camera(Vector3(7, 0, 0), 0.016)
	assert_almost_eq(camera.global_position, Vector3(7, 2, 6), 0.05)
	assert_almost_eq(camera.get_rail_offset(), 7.0, 0.05)


func test_lead_and_clamping_to_the_rail_ends() -> void:
	var camera := _rig(3.0)
	assert_almost_eq(camera.rail_offset_for(Vector3(7, 0, 0)), 10.0, 0.05)
	assert_almost_eq(camera.rail_offset_for(Vector3(19, 0, 0)), 20.0, 0.05, "clamped at the end")
	assert_almost_eq(camera.rail_offset_for(Vector3(-30, 0, 0)), 3.0, 0.05, "the start projection plus the lead")


func test_offset_eases_toward_the_target_point() -> void:
	var camera := _rig(0.0, 5.0)
	camera.update_camera(Vector3(0, 0, 0), 0.016)
	camera.update_camera(Vector3(10, 0, 0), 0.1)
	assert_almost_eq(camera.get_rail_offset(), 10.0 * (1.0 - exp(-0.5)), 0.05)
	for _i in range(60):
		camera.update_camera(Vector3(10, 0, 0), 0.1)
	assert_almost_eq(camera.get_rail_offset(), 10.0, 0.05)


func test_camera_looks_at_the_target() -> void:
	var camera := _rig()
	camera.update_camera(Vector3(5, 0, 0), 0.016)
	var toward: Vector3 = (Vector3(5, 0, 0) - camera.global_position).normalized()
	assert_almost_eq(-camera.global_basis.z, toward, 0.01)


func test_without_a_rail_the_camera_stays_put() -> void:
	var camera: Subject = Subject.new()
	add_child(camera)
	camera.set_process(false)
	camera.global_position = Vector3(1, 2, 3)
	assert_eq(camera.rail_offset_for(Vector3.ZERO), 0.0)
	camera.update_camera(Vector3(9, 0, 0), 0.1)
	assert_eq(camera.global_position, Vector3(1, 2, 3))
