class_name BaltorRoomCamera2D
extends Node
## Room-based camera limits for 2D: the camera stays inside the room that holds the target and eases across when
## the target enters another room, as in exploration platformers.
##
## Rooms are Rect2 areas in world space. Each update finds the room containing the target (keeping the current one
## while the target stands where rooms overlap) and clamps the camera center so the view stays inside that room;
## when the view is larger than the room on an axis, the camera centers on the room on that axis. On a room change
## the camera moves from where it was to the new clamped position over [member transition_time] seconds with
## smoothstep easing, then follows normally. The view size is the viewport size divided by the camera zoom.

## Emitted when the target enters a different room (-1 means no room).
signal room_changed(previous: int, current: int)

## The Camera2D to move.
@export var camera_path: NodePath = NodePath("..")
## The node the camera follows.
@export var target_path: NodePath = NodePath("")
## Rooms in world coordinates.
@export var rooms: Array[Rect2] = []
## Seconds of the eased move between rooms.
@export var transition_time: float = 0.4

var _room: int = -1
var _from: Vector2 = Vector2.ZERO
var _elapsed: float = 0.0
var _transitioning: bool = false


func _process(delta: float) -> void:
	var camera := get_node_or_null(camera_path) as Camera2D
	var target := get_node_or_null(target_path) as Node2D if not target_path.is_empty() else null
	if camera == null or target == null:
		return
	var view: Vector2 = camera.get_viewport_rect().size / camera.zoom
	camera.global_position = update_center(camera.global_position, target.global_position, view, delta)


## Adds a room and returns its index.
func add_room(area: Rect2) -> int:
	rooms.append(area.abs())
	return rooms.size() - 1


## Index of the room containing [param point], preferring the current room where rooms overlap; -1 when none.
func room_at(point: Vector2) -> int:
	if _room >= 0 and _room < rooms.size() and rooms[_room].has_point(point):
		return _room
	for index in range(rooms.size()):
		if rooms[index].has_point(point):
			return index
	return -1


## [param center] moved so a view of [param view_size] stays inside [param area]; centered on axes where the view
## is larger than the room.
static func clamp_center(center: Vector2, view_size: Vector2, area: Rect2) -> Vector2:
	var half: Vector2 = view_size * 0.5
	var result: Vector2 = center
	if view_size.x >= area.size.x:
		result.x = area.get_center().x
	else:
		result.x = clampf(center.x, area.position.x + half.x, area.end.x - half.x)
	if view_size.y >= area.size.y:
		result.y = area.get_center().y
	else:
		result.y = clampf(center.y, area.position.y + half.y, area.end.y - half.y)
	return result


## The camera center for this frame from the current [param camera_center], the [param target] position and the
## [param view_size], after [param delta] seconds.
func update_center(camera_center: Vector2, target: Vector2, view_size: Vector2, delta: float) -> Vector2:
	var found: int = room_at(target)
	if found != _room:
		var previous: int = _room
		_room = found
		if previous >= 0 and found >= 0:
			_from = camera_center
			_elapsed = 0.0
			_transitioning = transition_time > 0.0
		room_changed.emit(previous, found)
	if _room < 0:
		return target
	var goal: Vector2 = clamp_center(target, view_size, rooms[_room])
	if not _transitioning:
		return goal
	_elapsed += delta
	var t: float = clampf(_elapsed / transition_time, 0.0, 1.0)
	if t >= 1.0:
		_transitioning = false
	return _from.lerp(goal, t * t * (3.0 - 2.0 * t))


## The current room index (-1 when the target is outside every room).
func get_current_room() -> int:
	return _room


## True while easing between rooms.
func is_transitioning() -> bool:
	return _transitioning
