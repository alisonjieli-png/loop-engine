extends "../baltor_test.gd"
## Tests for BaltorFraming: thirds points, nearest third and offset, safe areas, lead room, projecting a 3D box
## through a camera and screen coverage.

const Subject := preload("../framing_guide.gd")
const SCREEN := Vector2(1920, 1080)


func test_thirds_points_and_nearest_third() -> void:
	assert_eq(Subject.thirds_points(Vector2(300, 90)), PackedVector2Array([Vector2(100, 30), Vector2(200, 30), Vector2(100, 60), Vector2(200, 60)]))
	assert_eq(Subject.nearest_third_point(Vector2(1500, 900), SCREEN), Vector2(1280, 720))
	assert_eq(Subject.offset_to_nearest_third(Vector2(600, 400), SCREEN), Vector2(40, -40))


func test_safe_areas() -> void:
	assert_eq(Subject.safe_area(SCREEN, 0.9), Rect2(96, 54, 1728, 972))
	assert_true(Subject.is_inside_safe_area(Vector2(960, 540), SCREEN, 0.8))
	assert_false(Subject.is_inside_safe_area(Vector2(150, 540), SCREEN, 0.8), "inside the outer 10 percent")
	assert_eq(Subject.safe_area(SCREEN, 2.0), Rect2(Vector2.ZERO, SCREEN), "the fraction is clamped")


func test_lead_room_measures_space_in_front() -> void:
	assert_almost_eq(Subject.lead_room(Vector2(640, 540), Vector2.RIGHT, SCREEN), 2.0 / 3.0, 0.0001)
	assert_almost_eq(Subject.lead_room(Vector2(640, 540), Vector2.LEFT, SCREEN), 1.0 / 3.0, 0.0001)
	assert_almost_eq(Subject.lead_room(Vector2(960, 270), Vector2.UP, SCREEN), 0.25, 0.0001)


func test_projected_rect_of_a_box_in_front_of_the_camera() -> void:
	var viewport := SubViewport.new()
	viewport.size = Vector2i(800, 600)
	add_child(viewport)
	var camera := Camera3D.new()
	viewport.add_child(camera)
	camera.current = true
	var corners := PackedVector3Array()
	for x: float in [-1.0, 1.0]:
		for y: float in [-1.0, 1.0]:
			corners.append(Vector3(x, y, -10.0))
	var bounds: Rect2 = Subject.projected_rect(camera, corners)
	assert_almost_eq(bounds.get_center(), Vector2(400, 300), 0.5, "centered in front")
	assert_almost_eq(bounds.size.x, bounds.size.y, 0.5, "square box, square on screen")
	corners.append(Vector3(0, 0, 10))
	assert_eq(Subject.projected_rect(camera, corners), bounds, "points behind the camera are skipped")
	assert_eq(Subject.projected_rect(camera, PackedVector3Array([Vector3(0, 0, 5)])), Rect2())


func test_coverage_clips_to_the_screen() -> void:
	assert_almost_eq(Subject.coverage(Rect2(0, 0, 960, 540), SCREEN), 0.25, 0.0001)
	assert_almost_eq(Subject.coverage(Rect2(-960, 0, 1920, 1080), SCREEN), 0.5, 0.0001)
	assert_eq(Subject.coverage(Rect2(5000, 5000, 10, 10), SCREEN), 0.0)
