extends "../baltor_test.gd"
## Tests for BaltorOrbitCamera3D: the orbit formula, limits, placement and look direction, distance smoothing,
## and the pull-in in front of a wall.

const Subject := preload("../orbit_camera_3d.gd")


func _rig(collide: bool) -> Subject:
	var target := Node3D.new()
	target.name = "Target"
	add_child(target)
	var camera: Subject = Subject.new()
	camera.target_path = NodePath("../Target")
	camera.target_offset = Vector3.ZERO
	camera.collide = collide
	camera.use_mouse = false
	add_child(camera)
	camera.set_process(false)
	return camera


func test_orbit_offset_has_known_directions() -> void:
	assert_almost_eq(Subject.orbit_offset(0.0, 0.0, 5.0), Vector3(0, 0, 5), 0.0001)
	assert_almost_eq(Subject.orbit_offset(PI / 2.0, 0.0, 5.0), Vector3(5, 0, 0), 0.0001)
	assert_almost_eq(Subject.orbit_offset(0.0, PI / 2.0, 5.0), Vector3(0, 5, 0), 0.0001)
	assert_almost_eq(Subject.orbit_offset(0.3, 0.7, 4.0).length(), 4.0, 0.0001)


func test_pitch_and_zoom_are_clamped_and_yaw_wraps() -> void:
	var camera := _rig(false)
	camera.orbit(0.0, 500.0)
	assert_eq(camera.pitch_degrees, 75.0)
	camera.orbit(0.0, -500.0)
	assert_eq(camera.pitch_degrees, -60.0)
	camera.zoom(100.0)
	assert_eq(camera.distance, 12.0)
	camera.zoom(-100.0)
	assert_eq(camera.distance, 1.5)
	camera.yaw_degrees = 170.0
	camera.orbit(30.0, 0.0)
	assert_almost_eq(camera.yaw_degrees, -160.0, 0.0001)


func test_camera_is_placed_on_the_orbit_and_looks_at_the_pivot() -> void:
	var camera := _rig(false)
	camera.yaw_degrees = 90.0
	camera.pitch_degrees = 0.0
	camera.distance = 6.0
	camera.update_camera(1.0)
	assert_almost_eq(camera.global_position, Vector3(6, 0, 0), 0.0001)
	assert_almost_eq(-camera.global_basis.z, Vector3(-1, 0, 0), 0.0001, "the camera faces the pivot")


func test_longer_distances_ease_in_and_shorter_ones_snap() -> void:
	var camera := _rig(false)
	camera.distance = 4.0
	camera.update_camera(0.016)
	camera.distance = 8.0
	camera.update_camera(0.05)
	var eased: float = camera.get_current_distance()
	assert_almost_eq(eased, 4.0 + 4.0 * (1.0 - exp(-12.0 * 0.05)), 0.0001)
	camera.distance = 2.0
	camera.update_camera(0.0)
	assert_eq(camera.get_current_distance(), 2.0, "pulling in is immediate")


func test_wall_between_pivot_and_camera_pulls_it_in() -> void:
	var wall := StaticBody3D.new()
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(4, 4, 0.5)
	shape.shape = box
	wall.add_child(shape)
	wall.position = Vector3(0, 0, 3)
	add_child(wall)
	var camera := _rig(true)
	camera.pitch_degrees = 0.0
	camera.distance = 8.0
	await wait_physics_frames(2)
	camera.update_camera(0.016)
	assert_almost_eq(camera.get_current_distance(), 2.75 - 0.2, 0.01)
	assert_lt(camera.global_position.z, 2.75)
