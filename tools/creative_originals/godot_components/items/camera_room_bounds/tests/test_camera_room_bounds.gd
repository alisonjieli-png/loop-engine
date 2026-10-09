extends "../baltor_test.gd"
## Tests for BaltorRoomCamera2D: room lookup with overlap preference, clamping and centering, the room change
## signal and the eased transition.

const Subject := preload("../camera_room_bounds.gd")
const VIEW := Vector2(320, 180)


func _rooms() -> Subject:
	var rig: Subject = autofree(Subject.new())
	rig.add_room(Rect2(0, 0, 640, 360))
	rig.add_room(Rect2(600, 0, 400, 150))
	return rig


func test_room_lookup_prefers_the_current_room_in_overlaps() -> void:
	var rig := _rooms()
	assert_eq(rig.room_at(Vector2(100, 100)), 0)
	assert_eq(rig.room_at(Vector2(800, 50)), 1)
	assert_eq(rig.room_at(Vector2(2000, 0)), -1)
	rig.update_center(Vector2.ZERO, Vector2(800, 50), VIEW, 0.016)
	assert_eq(rig.room_at(Vector2(620, 50)), 1, "the overlap keeps the current room")


func test_clamp_keeps_the_view_inside_and_centers_small_rooms() -> void:
	var room := Rect2(0, 0, 640, 360)
	assert_eq(Subject.clamp_center(Vector2(10, 10), VIEW, room), Vector2(160, 90))
	assert_eq(Subject.clamp_center(Vector2(630, 300), VIEW, room), Vector2(480, 270))
	assert_eq(Subject.clamp_center(Vector2(300, 200), VIEW, room), Vector2(300, 200))
	assert_eq(Subject.clamp_center(Vector2(700, 20), VIEW, Rect2(600, 0, 400, 150)), Vector2(760, 75), "y is centered")


func test_room_change_eases_across_then_follows() -> void:
	var rig := _rooms()
	watch_signals(rig)
	var center: Vector2 = rig.update_center(Vector2.ZERO, Vector2(500, 200), VIEW, 0.016)
	assert_eq(center, Vector2(480, 200))
	center = rig.update_center(center, Vector2(700, 60), VIEW, 0.2)
	assert_true(rig.is_transitioning())
	assert_almost_eq(center, Vector2(480, 200).lerp(Vector2(760, 75), 0.5), 0.001, "halfway with smoothstep")
	center = rig.update_center(center, Vector2(700, 60), VIEW, 0.25)
	assert_false(rig.is_transitioning())
	assert_eq(center, Vector2(760, 75))
	assert_eq(signal_emissions(rig, &"room_changed"), [[-1, 0], [0, 1]])


func test_outside_every_room_the_camera_follows_the_target() -> void:
	var rig := _rooms()
	assert_eq(rig.update_center(Vector2.ZERO, Vector2(5000, 5000), VIEW, 0.016), Vector2(5000, 5000))
	assert_eq(rig.get_current_room(), -1)
