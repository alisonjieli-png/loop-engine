extends "../baltor_test.gd"
## Tests for BaltorSplitScreen: one to five players, stacking, gaps that stay inside, no overlaps, and placing
## controls.

const Subject := preload("../split_screen_layout.gd")
const SCREEN := Rect2(0, 0, 1280, 720)


func test_one_and_two_players() -> void:
	assert_eq(Subject.layout(1, SCREEN), [SCREEN])
	assert_eq(Subject.layout(2, SCREEN), [Rect2(0, 0, 640, 720), Rect2(640, 0, 640, 720)])
	assert_eq(Subject.layout(2, SCREEN, true), [Rect2(0, 0, 1280, 360), Rect2(0, 360, 1280, 360)])
	assert_eq(Subject.layout(0, SCREEN), [])


func test_three_players_get_one_wide_and_two_small_views() -> void:
	assert_eq(Subject.layout(3, SCREEN), [Rect2(0, 0, 1280, 360), Rect2(0, 360, 640, 360), Rect2(640, 360, 640, 360)])
	assert_eq(Subject.layout(3, SCREEN, true), [Rect2(0, 0, 640, 720), Rect2(640, 0, 640, 360), Rect2(640, 360, 640, 360)])


func test_grids_cover_the_screen_without_overlap() -> void:
	for count: int in [4, 5, 6, 9]:
		var views: Array[Rect2] = Subject.layout(count, SCREEN)
		assert_eq(views.size(), count)
		var area: float = 0.0
		for index in range(views.size()):
			area += views[index].get_area()
			for other in range(index + 1, views.size()):
				assert_false(views[index].intersects(views[other]), "views %d and %d overlap" % [index, other])
		assert_almost_eq(area, SCREEN.get_area(), 0.5)
	var five: Array[Rect2] = Subject.layout(5, SCREEN)
	assert_eq(five[3], Rect2(0, 360, 640, 360), "a short last row spreads over the full width")


func test_gaps_separate_views_but_not_the_border() -> void:
	var views: Array[Rect2] = Subject.layout(4, SCREEN, false, 8.0)
	assert_eq(views[0], Rect2(0, 0, 636, 356))
	assert_eq(views[3], Rect2(644, 364, 636, 356))
	assert_eq(views[3].end, SCREEN.end)


func test_arrange_places_controls() -> void:
	var first := Control.new()
	var second := Control.new()
	add_child(first)
	add_child(second)
	assert_eq(Subject.arrange([first, second], SCREEN, true, 4.0), 2)
	assert_eq(second.position, Vector2(0, 362))
	assert_eq(second.size, Vector2(1280, 358))
