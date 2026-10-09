extends "../baltor_test.gd"
## Tests for BaltorBuoyancy3D: the wave formula, the probe force curve, a body floating at the predicted draft and
## the water entry and exit signals.

const Subject := preload("../buoyancy_probes_3d.gd")


func _floater(start_height: float) -> RigidBody3D:
	var body := RigidBody3D.new()
	body.mass = 3.0
	var shape := CollisionShape3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = 0.3
	shape.shape = sphere
	body.add_child(shape)
	body.position = Vector3(0, start_height, 0)
	var floater: Subject = Subject.new()
	floater.name = "Buoyancy"
	body.add_child(floater)
	add_child(body)
	return body


func test_wave_height_formula() -> void:
	assert_eq(Subject.wave_height_at(Vector2(3, 4), 1.0, 2.0, PackedVector4Array()), 2.0)
	var wave := PackedVector4Array([Vector4(0.5, 8.0, 0.0, 0.0)])
	assert_almost_eq(Subject.wave_height_at(Vector2(2, 0), 0.0, 0.0, wave), 0.5, 0.0001, "a quarter wavelength is the crest")
	assert_almost_eq(Subject.wave_height_at(Vector2(0, 2), 0.0, 0.0, wave), 0.0, 0.0001, "the wave runs along x")
	var moving := PackedVector4Array([Vector4(0.5, 8.0, 2.0, 0.0)])
	assert_almost_eq(Subject.wave_height_at(Vector2(6, 0), 2.0, 0.0, moving), 0.5, 0.0001, "the crest moved 4 m in 2 s")
	for index in range(20):
		var point := Vector2(index * 0.7, index * -1.3)
		assert_true(absf(Subject.wave_height_at(point, index * 0.1, 0.0, moving)) <= 0.5 + 0.0001)


func test_probe_force_grows_with_depth_and_caps() -> void:
	var floater: Subject = Subject.new()
	assert_eq(floater.probe_force(-0.1, 1.0), 0.0)
	assert_almost_eq(floater.probe_force(0.25, 1.0), 2.0 * 9.8 * 0.5)
	assert_almost_eq(floater.probe_force(0.5, 1.0), 2.0 * 9.8)
	assert_almost_eq(floater.probe_force(3.0, 1.0), 2.0 * 9.8, 0.0001, "capped at full depth")
	floater.free()


func test_body_floats_at_the_predicted_draft() -> void:
	var body := _floater(1.0)
	var floater := body.get_node("Buoyancy") as Subject
	floater.water_drag = 8.0
	floater.water_angular_drag = 8.0
	await wait_physics_frames(240)
	assert_almost_eq(body.position.y, -0.25, 0.03)
	assert_lt(body.linear_velocity.length(), 0.1)
	assert_eq(floater.get_submerged_ratio(), 1.0)


func test_entering_and_leaving_the_water_is_reported() -> void:
	var body := _floater(0.4)
	var floater := body.get_node("Buoyancy") as Subject
	watch_signals(floater)
	await wait_physics_frames(30)
	assert_signal_count(floater, &"entered_water", 1)
	body.global_position = Vector3(0, 10, 0)
	body.linear_velocity = Vector3.ZERO
	await wait_physics_frames(2)
	assert_signal_count(floater, &"left_water", 1)
	assert_eq(floater.get_submerged_ratio(), 0.0)
