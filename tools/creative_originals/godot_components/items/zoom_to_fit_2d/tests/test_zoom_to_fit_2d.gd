extends "../baltor_test.gd"
## Tests for BaltorGroupCamera2D: centering on the group, the zoom that fits the wider axis, zoom limits, empty
## input and smoothing.

const Subject := preload("../zoom_to_fit_2d.gd")
const VIEW := Vector2(800, 400)


func test_two_points_center_and_fit_the_tighter_axis() -> void:
	var result: Dictionary = Subject.fit(PackedVector2Array([Vector2(0, 0), Vector2(1000, 100)]), VIEW, 50.0, 0.1, 4.0)
	assert_eq(result["center"], Vector2(500, 50))
	assert_almost_eq(float(result["zoom"]), 800.0 / 1100.0, 0.0001)
	var tall: Dictionary = Subject.fit(PackedVector2Array([Vector2(0, 0), Vector2(100, 700)]), VIEW, 50.0, 0.1, 4.0)
	assert_almost_eq(float(tall["zoom"]), 400.0 / 800.0, 0.0001)


func test_zoom_limits_hold() -> void:
	var near: Dictionary = Subject.fit(PackedVector2Array([Vector2(5, 5)]), VIEW, 10.0, 0.25, 2.0)
	assert_eq(near["zoom"], 2.0, "one point gets the closest zoom")
	assert_eq(near["center"], Vector2(5, 5))
	var far: Dictionary = Subject.fit(PackedVector2Array([Vector2(0, 0), Vector2(100000, 0)]), VIEW, 10.0, 0.25, 2.0)
	assert_eq(far["zoom"], 0.25)


func test_empty_input_gives_the_default() -> void:
	assert_eq(Subject.fit(PackedVector2Array(), VIEW, 10.0, 0.25, 2.0), {"center": Vector2.ZERO, "zoom": 1.0})


func test_camera_eases_toward_the_fit() -> void:
	var camera: Subject = Subject.new()
	add_child(camera)
	camera.set_process(false)
	var points := PackedVector2Array([Vector2(-300, 0), Vector2(300, 0)])
	camera.update_camera(points, VIEW, 0.25)
	assert_almost_eq(camera.zoom.x, 1.0 + (800.0 / 728.0 - 1.0) * (1.0 - exp(-1.0)), 0.0001)
	for _i in range(40):
		camera.update_camera(points, VIEW, 0.25)
	assert_almost_eq(camera.zoom.x, 800.0 / 728.0, 0.0001)
	assert_almost_eq(camera.global_position, Vector2.ZERO, 0.0001)
