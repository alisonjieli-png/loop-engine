extends "../baltor_test.gd"
## Tests for BaltorFirstPersonController: look limits, yaw-relative movement, speeds, crouch height and the
## ceiling check, head bob, jumping only from the floor, and landing on a real floor.

const Subject := preload("../fps_controller_3d.gd")
const DT: float = 1.0 / 60.0


func _body() -> Subject:
	var body: Subject = autofree(Subject.new())
	body.use_input_actions = false
	return body


func test_look_turns_the_body_and_clamps_the_head() -> void:
	var body := _body()
	body.look(Vector2(-600, 0))
	assert_almost_eq(body.rotation.y, deg_to_rad(90.0), 0.0001)
	body.look(Vector2(0, -10000))
	assert_almost_eq(body.get_pitch(), deg_to_rad(85.0), 0.0001, "looking up stops at the limit")
	body.look(Vector2(0, 20000))
	assert_almost_eq(body.get_pitch(), deg_to_rad(-85.0), 0.0001)


func test_movement_follows_yaw_and_reaches_each_speed() -> void:
	var body := _body()
	body.rotation.y = PI / 2.0
	body.set_move_input(Vector2(0, 1))
	assert_almost_eq(body.wish_direction(), Vector3(-1, 0, 0), 0.0001)
	for _i in range(60):
		body.step(DT, true)
	assert_almost_eq(Vector2(body.velocity.x, body.velocity.z).length(), 4.5, 0.001)
	body.set_sprinting(true)
	for _i in range(60):
		body.step(DT, true)
	assert_almost_eq(Vector2(body.velocity.x, body.velocity.z).length(), 7.5, 0.001)
	body.set_crouching(true)
	for _i in range(60):
		body.step(DT, true)
	assert_almost_eq(Vector2(body.velocity.x, body.velocity.z).length(), 2.0, 0.001, "crouching beats sprinting")


func test_crouch_moves_the_head_and_needs_room_to_stand() -> void:
	var body := _body()
	body.step(DT, true)
	assert_true(body.set_crouching(true))
	body.step(0.05, true)
	assert_almost_eq(body.get_head_height(), 1.6 - 0.3, 0.0001)
	for _i in range(30):
		body.step(DT, true)
	assert_almost_eq(body.get_head_height(), 0.9, 0.0001)
	assert_true(body.set_crouching(false))
	assert_false(body.is_crouching())


func test_ceiling_blocks_standing_up_in_the_physics_world() -> void:
	var ceiling := StaticBody3D.new()
	var ceiling_shape := CollisionShape3D.new()
	var slab := BoxShape3D.new()
	slab.size = Vector3(4, 0.2, 4)
	ceiling_shape.shape = slab
	ceiling.add_child(ceiling_shape)
	ceiling.position = Vector3(0, 1.4, 0)
	add_child(ceiling)
	var body: Subject = Subject.new()
	body.use_input_actions = false
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.3
	capsule.height = 1.0
	shape.shape = capsule
	shape.position.y = 0.5
	body.add_child(shape)
	add_child(body)
	body.set_physics_process(false)
	await wait_physics_frames(2)
	assert_true(body.set_crouching(true))
	assert_false(body.can_stand_up())
	assert_false(body.set_crouching(false), "the ceiling is in the way")
	assert_true(body.is_crouching())


func test_head_bob_runs_while_walking_and_fades_when_stopped() -> void:
	var body := _body()
	body.step(DT, true)
	assert_eq(body.get_bob_offset(), Vector3.ZERO)
	body.set_move_input(Vector2(0, 1))
	var highest: float = 0.0
	for _i in range(120):
		body.step(DT, true)
		highest = maxf(highest, absf(body.get_bob_offset().y))
	assert_gt(highest, 0.03)
	assert_true(highest <= body.bob_amplitude + 0.0001)
	body.set_move_input(Vector2.ZERO)
	for _i in range(120):
		body.step(DT, true)
	assert_eq(body.get_bob_offset(), Vector3.ZERO)


func test_jumps_only_from_the_floor_and_reports_landing() -> void:
	var body := _body()
	watch_signals(body)
	body.press_jump()
	body.step(DT, false)
	assert_signal_not_emitted(body, &"jumped", "no jump in the air")
	body.press_jump()
	body.step(DT, true)
	assert_signal_count(body, &"jumped", 1)
	assert_almost_eq(body.velocity.y, 4.8, 0.0001)
	for _i in range(60):
		body.step(DT, false)
	body.step(DT, true)
	assert_signal_count(body, &"landed", 2, "once after the first air step, once after the jump")
	assert_gt(float(signal_emissions(body, &"landed")[1][0]), 2.0)


func test_falls_and_stands_on_a_real_floor() -> void:
	var ground := StaticBody3D.new()
	var ground_shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(20, 1, 20)
	ground_shape.shape = box
	ground.add_child(ground_shape)
	ground.position = Vector3(0, -0.5, 0)
	add_child(ground)
	var body: Subject = Subject.new()
	body.use_input_actions = false
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.3
	capsule.height = 1.8
	shape.shape = capsule
	shape.position.y = 0.9
	body.add_child(shape)
	body.position = Vector3(0, 1.0, 0)
	add_child(body)
	await wait_physics_frames(45)
	assert_true(body.is_on_floor())
	assert_almost_eq(body.position.y, 0.0, 0.05)
