class_name BaltorGroupCamera2D
extends Camera2D
## A 2D camera that frames several targets: it centers on their bounding box and zooms so all of them fit with a
## margin, within zoom limits, with smoothing.
##
## fit() takes the axis-aligned bounds of the points grown by [member margin] on every side and returns the bounds'
## center and the zoom at which they fill the view: min(view width / bounds width, view height / bounds height),
## clamped to [member min_zoom]..[member max_zoom] (Camera2D zoom above 1 magnifies). A single point gets the
## largest zoom. The camera eases its position and zoom toward the fit at [member follow_speed] per second.
## Targets are NodePaths to Node2D nodes; positions can also be given directly to update_camera().

## The nodes to keep in view.
@export var targets: Array[NodePath] = []
## World units of space around the targets.
@export var margin: float = 64.0
## Smallest zoom (farthest out).
@export var min_zoom: float = 0.25
## Largest zoom (closest in).
@export var max_zoom: float = 2.0
## Exponential easing rate of position and zoom, per second; 0 jumps.
@export var follow_speed: float = 4.0


func _process(delta: float) -> void:
	var points := PackedVector2Array()
	for node_path: NodePath in targets:
		var node := get_node_or_null(node_path) as Node2D
		if node != null:
			points.append(node.global_position)
	if not points.is_empty():
		update_camera(points, get_viewport_rect().size, delta)


## The center and zoom that fit [param points] into [param view_size] with [param border] around them, as
## {"center": Vector2, "zoom": float}. An empty list gives the origin and zoom 1.
static func fit(points: PackedVector2Array, view_size: Vector2, border: float, smallest: float,
		largest: float) -> Dictionary:
	if points.is_empty():
		return {"center": Vector2.ZERO, "zoom": 1.0}
	var bounds := Rect2(points[0], Vector2.ZERO)
	for point: Vector2 in points:
		bounds = bounds.expand(point)
	bounds = bounds.grow(border)
	var zoom_x: float = view_size.x / maxf(bounds.size.x, 0.001)
	var zoom_y: float = view_size.y / maxf(bounds.size.y, 0.001)
	return {"center": bounds.get_center(), "zoom": clampf(minf(zoom_x, zoom_y), smallest, largest)}


## Eases toward the fit for [param points] in a view of [param view_size] after [param delta] seconds.
func update_camera(points: PackedVector2Array, view_size: Vector2, delta: float) -> void:
	var goal: Dictionary = fit(points, view_size, margin, min_zoom, max_zoom)
	var weight: float = 1.0 if follow_speed <= 0.0 else 1.0 - exp(-follow_speed * maxf(delta, 0.0))
	global_position = global_position.lerp(goal["center"], weight)
	var level: float = lerpf(zoom.x, float(goal["zoom"]), weight)
	zoom = Vector2(level, level)
