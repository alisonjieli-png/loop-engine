class_name BaltorSplitScreen
extends RefCounted
## Split-screen layouts for one to many local players: screen rectangles for each view with a gap between them,
## and a helper that places Control nodes (such as SubViewportContainers) on them.
##
## One player gets the whole screen. Two players get two halves split side by side, or stacked when
## [param stacked] is true. Three players get one wide view and two smaller ones (on top with side-by-side
## splits, or on the left when stacked). Four or more players get a grid with as many columns as the rounded-up
## square root of the count; a last row with fewer views spreads them over the full width. [param gap] pixels
## separate neighboring views and never appear at the screen border.


## The view rectangles for [param count] players on [param screen].
static func layout(count: int, screen: Rect2, stacked: bool = false, gap: float = 0.0) -> Array[Rect2]:
	var views: Array[Rect2] = []
	if count <= 0:
		return views
	if count == 1:
		views.append(screen)
		return views
	if count == 2:
		return _split(screen, 2, not stacked, gap)
	if count == 3:
		var halves: Array[Rect2] = _split(screen, 2, stacked, gap)
		views.append(halves[0])
		views.append_array(_split(halves[1], 2, not stacked, gap))
		return views
	var columns: int = ceili(sqrt(float(count)))
	var rows: int = ceili(float(count) / float(columns))
	var row_rects: Array[Rect2] = _split(screen, rows, false, gap)
	var remaining: int = count
	for row in range(rows):
		var in_row: int = mini(columns, remaining)
		views.append_array(_split(row_rects[row], in_row, true, gap))
		remaining -= in_row
	return views


## Places each Control of [param controls] on its view rectangle. Returns the number of controls placed.
static func arrange(controls: Array, screen: Rect2, stacked: bool = false, gap: float = 0.0) -> int:
	var views: Array[Rect2] = layout(controls.size(), screen, stacked, gap)
	var placed: int = 0
	for index in range(views.size()):
		var control := controls[index] as Control
		if control == null:
			continue
		control.position = views[index].position
		control.size = views[index].size
		placed += 1
	return placed


static func _split(area: Rect2, parts: int, across: bool, gap: float) -> Array[Rect2]:
	var pieces: Array[Rect2] = []
	var total: float = area.size.x if across else area.size.y
	var length: float = (total - gap * (parts - 1)) / float(parts)
	for index in range(parts):
		var start: float = index * (length + gap)
		if across:
			pieces.append(Rect2(area.position + Vector2(start, 0), Vector2(length, area.size.y)))
		else:
			pieces.append(Rect2(area.position + Vector2(0, start), Vector2(area.size.x, length)))
	return pieces
