class_name BaltorInfluenceMap
extends RefCounted
## A grid influence map for tactical AI: sources stamp influence that falls off with distance, propagation spreads
## and decays it through open cells, and queries find the strongest or weakest cell in an area.
##
## The map is width x height cells of cell_size world units, stored row by row. stamp() adds strength at a center
## cell, scaled down with the Euclidean cell distance up to a radius (linear, quadratic or constant falloff).
## propagate() runs iterations of the classic spread rule: each open cell moves toward the strongest neighbor value
## times exp(-decay * distance) (8 neighbors, diagonal distance sqrt(2)) by the momentum fraction, so influence
## flows around walls but not through them. Two maps can be combined, for example friendly minus enemy influence
## for a control map. Values are floats in a PackedFloat32Array.

## How stamped influence falls off with distance from the center.
enum Falloff { LINEAR, QUADRATIC, CONSTANT }

var _width: int = 0
var _height: int = 0
var _cell_size: float = 32.0
var _values: PackedFloat32Array = PackedFloat32Array()
var _blocked: PackedByteArray = PackedByteArray()


func _init(width: int = 32, height: int = 32, cell_size: float = 32.0) -> void:
	_width = maxi(width, 1)
	_height = maxi(height, 1)
	_cell_size = maxf(cell_size, 0.001)
	_values.resize(_width * _height)
	_blocked.resize(_width * _height)


## Number of columns.
func get_width() -> int:
	return _width


## Number of rows.
func get_height() -> int:
	return _height


## True when [param cell] lies inside the map.
func has_cell(cell: Vector2i) -> bool:
	return cell.x >= 0 and cell.y >= 0 and cell.x < _width and cell.y < _height


## Marks [param cell] as a wall (no influence, blocks propagation) or open. Returns false outside the map.
func set_blocked(cell: Vector2i, blocked: bool) -> bool:
	if not has_cell(cell):
		return false
	_blocked[_index(cell)] = 1 if blocked else 0
	if blocked:
		_values[_index(cell)] = 0.0
	return true


## True when [param cell] is a wall or outside the map.
func is_blocked(cell: Vector2i) -> bool:
	return not has_cell(cell) or _blocked[_index(cell)] == 1


## The influence at [param cell] (0.0 outside the map).
func get_value(cell: Vector2i) -> float:
	return _values[_index(cell)] if has_cell(cell) else 0.0


## Sets the influence at an open [param cell]. Returns false for walls and cells outside the map.
func set_value(cell: Vector2i, value: float) -> bool:
	if is_blocked(cell):
		return false
	_values[_index(cell)] = value
	return true


## Sets every value to zero (walls stay).
func clear() -> void:
	_values.fill(0.0)


## Adds [param strength] around [param center] out to [param radius] cells with the given falloff.
func stamp(center: Vector2i, strength: float, radius: int, falloff: Falloff = Falloff.LINEAR) -> void:
	for y in range(center.y - radius, center.y + radius + 1):
		for x in range(center.x - radius, center.x + radius + 1):
			var cell := Vector2i(x, y)
			if is_blocked(cell):
				continue
			var distance: float = Vector2(cell - center).length()
			if distance > float(radius) + 0.0001:
				continue
			var t: float = 0.0 if radius == 0 else distance / float(radius + 1)
			var scale: float = 1.0
			match falloff:
				Falloff.LINEAR:
					scale = 1.0 - t
				Falloff.QUADRATIC:
					scale = (1.0 - t) * (1.0 - t)
			_values[_index(cell)] += strength * scale


## Spreads influence [param iterations] times: each open cell moves toward max(neighbor * exp(-decay * d)) by the
## [param momentum] fraction (0 keeps the old value, 1 takes the neighbor value). Negative influence spreads by
## magnitude with its sign.
func propagate(decay: float, momentum: float, iterations: int = 1) -> void:
	var weight_straight: float = exp(-decay)
	var weight_diagonal: float = exp(-decay * sqrt(2.0))
	for _round in range(maxi(iterations, 0)):
		var next: PackedFloat32Array = _values.duplicate()
		for y in range(_height):
			for x in range(_width):
				var cell := Vector2i(x, y)
				if _blocked[_index(cell)] == 1:
					continue
				var strongest: float = 0.0
				for dy in range(-1, 2):
					for dx in range(-1, 2):
						if dx == 0 and dy == 0:
							continue
						var other := Vector2i(x + dx, y + dy)
						if is_blocked(other):
							continue
						if dx != 0 and dy != 0 and (is_blocked(Vector2i(x + dx, y)) or is_blocked(Vector2i(x, y + dy))):
							continue
						var carried: float = _values[_index(other)] * (weight_diagonal if dx != 0 and dy != 0 else weight_straight)
						if absf(carried) > absf(strongest):
							strongest = carried
				var current: float = _values[_index(cell)]
				next[_index(cell)] = lerpf(current, strongest, momentum) if absf(strongest) > absf(current) else current
		_values = next


## Adds [param other] times [param factor] cell by cell. Returns false when the sizes differ.
func combine(other: BaltorInfluenceMap, factor: float = 1.0) -> bool:
	if other == null or other.get_width() != _width or other.get_height() != _height:
		return false
	for index in range(_values.size()):
		if _blocked[index] == 0:
			_values[index] += other.get_value(Vector2i(index % _width, floori(float(index) / float(_width)))) * factor
	return true


## The open cell within [param radius] of [param center] with the highest value, or the lowest with
## [param highest] false. Returns Vector2i(-1, -1) when no open cell is in range.
func best_cell(center: Vector2i, radius: int, highest: bool = true) -> Vector2i:
	var best := Vector2i(-1, -1)
	var best_value: float = 0.0
	for y in range(center.y - radius, center.y + radius + 1):
		for x in range(center.x - radius, center.x + radius + 1):
			var cell := Vector2i(x, y)
			if is_blocked(cell):
				continue
			var value: float = _values[_index(cell)]
			if best.x < 0 or (value > best_value if highest else value < best_value):
				best = cell
				best_value = value
	return best


## The cell containing world point [param point] (may lie outside the map).
func world_to_cell(point: Vector2) -> Vector2i:
	return Vector2i(floori(point.x / _cell_size), floori(point.y / _cell_size))


## The world position of the center of [param cell].
func cell_to_world(cell: Vector2i) -> Vector2:
	return (Vector2(cell) + Vector2(0.5, 0.5)) * _cell_size


## A copy of every value, row by row.
func get_values() -> PackedFloat32Array:
	return _values.duplicate()


func _index(cell: Vector2i) -> int:
	return cell.y * _width + cell.x
