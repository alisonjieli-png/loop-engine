class_name BaltorFlowField
extends RefCounted
## A grid flow field: one Dijkstra pass from the goal cells gives every cell its travel cost to the nearest goal
## and a direction to follow, so any number of units can share one search.
##
## Each cell has a crossing cost: 1 by default, higher for slow terrain, 0 or less for walls. A step out of a cell
## toward the goal costs that cell's cost, times sqrt(2) for a diagonal step. build() runs Dijkstra from all goal
## cells at once over 8 neighbors, and a diagonal step may not cut past a wall corner. direction_at() points from a cell toward its cheapest neighbor, so a
## unit only reads the vector under it each frame. Cells that cannot reach a goal have infinite distance and a
## zero direction.

var _width: int = 0
var _height: int = 0
var _cell_size: float = 32.0
var _costs: PackedFloat32Array = PackedFloat32Array()
var _distance: PackedFloat64Array = PackedFloat64Array()
var _next: PackedInt32Array = PackedInt32Array()


func _init(width: int = 32, height: int = 32, cell_size: float = 32.0) -> void:
	_width = maxi(width, 1)
	_height = maxi(height, 1)
	_cell_size = maxf(cell_size, 0.001)
	_costs.resize(_width * _height)
	_costs.fill(1.0)
	_distance.resize(_width * _height)
	_distance.fill(INF)
	_next.resize(_width * _height)
	_next.fill(-1)


## True when [param cell] is inside the grid.
func has_cell(cell: Vector2i) -> bool:
	return cell.x >= 0 and cell.y >= 0 and cell.x < _width and cell.y < _height


## Sets the crossing cost of [param cell]; 0 or less makes it a wall. Returns false outside the grid.
func set_cost(cell: Vector2i, cost: float) -> bool:
	if not has_cell(cell):
		return false
	_costs[cell.y * _width + cell.x] = cost
	return true


## The crossing cost of [param cell] (0 outside the grid).
func get_cost(cell: Vector2i) -> float:
	return _costs[cell.y * _width + cell.x] if has_cell(cell) else 0.0


## Computes distances and directions toward the nearest of [param goals]. Returns the number of reachable cells.
func build(goals: Array[Vector2i]) -> int:
	_distance.fill(INF)
	_next.fill(-1)
	var heap: Array = []
	var order: int = 0
	for goal: Vector2i in goals:
		if has_cell(goal) and get_cost(goal) > 0.0:
			_distance[goal.y * _width + goal.x] = 0.0
			order += 1
			_push(heap, [0.0, order, goal.y * _width + goal.x])
	var reached: int = 0
	while not heap.is_empty():
		var entry: Array = _pop(heap)
		var index: int = entry[2]
		if float(entry[0]) > _distance[index]:
			continue
		reached += 1
		var cell := Vector2i(index % _width, floori(float(index) / float(_width)))
		for dy in range(-1, 2):
			for dx in range(-1, 2):
				if dx == 0 and dy == 0:
					continue
				var other := Vector2i(cell.x + dx, cell.y + dy)
				var cost: float = get_cost(other)
				if cost <= 0.0:
					continue
				if dx != 0 and dy != 0 and (get_cost(Vector2i(cell.x + dx, cell.y)) <= 0.0 or get_cost(Vector2i(cell.x, cell.y + dy)) <= 0.0):
					continue
				var step: float = cost * (1.41421356 if dx != 0 and dy != 0 else 1.0)
				var other_index: int = other.y * _width + other.x
				var candidate: float = _distance[index] + step
				if candidate < _distance[other_index] - 0.000001:
					_distance[other_index] = candidate
					_next[other_index] = index
					order += 1
					_push(heap, [candidate, order, other_index])
	return reached


## Travel cost from [param cell] to the nearest goal (INF when unreachable or outside).
func get_distance(cell: Vector2i) -> float:
	return _distance[cell.y * _width + cell.x] if has_cell(cell) else INF


## The unit direction to follow from [param cell] (zero at a goal, on walls and where no goal is reachable).
func direction_at(cell: Vector2i) -> Vector2:
	if not has_cell(cell):
		return Vector2.ZERO
	var next: int = _next[cell.y * _width + cell.x]
	if next < 0:
		return Vector2.ZERO
	var target := Vector2i(next % _width, floori(float(next) / float(_width)))
	return Vector2(target - cell).normalized()


## The direction under world position [param point].
func sample(point: Vector2) -> Vector2:
	return direction_at(world_to_cell(point))


## The cell under world position [param point].
func world_to_cell(point: Vector2) -> Vector2i:
	return Vector2i(floori(point.x / _cell_size), floori(point.y / _cell_size))


## The cell sequence a unit at [param cell] follows to the goal, both ends included (empty if unreachable).
func trace(cell: Vector2i, max_steps: int = 4096) -> Array[Vector2i]:
	var path: Array[Vector2i] = []
	if not has_cell(cell) or is_inf(get_distance(cell)):
		return path
	var current: int = cell.y * _width + cell.x
	path.append(cell)
	while _next[current] >= 0 and path.size() < max_steps:
		current = _next[current]
		path.append(Vector2i(current % _width, floori(float(current) / float(_width))))
	return path


func _push(heap: Array, entry: Array) -> void:
	heap.append(entry)
	var index: int = heap.size() - 1
	while index > 0:
		var parent: int = (index - 1) >> 1
		if not _before(heap[index], heap[parent]):
			break
		var swap: Variant = heap[parent]
		heap[parent] = heap[index]
		heap[index] = swap
		index = parent


func _pop(heap: Array) -> Array:
	var top: Array = heap[0]
	var last: Array = heap.pop_back()
	if not heap.is_empty():
		heap[0] = last
		var index: int = 0
		while true:
			var smallest: int = index
			for child: int in [index * 2 + 1, index * 2 + 2]:
				if child < heap.size() and _before(heap[child], heap[smallest]):
					smallest = child
			if smallest == index:
				break
			var swap: Variant = heap[smallest]
			heap[smallest] = heap[index]
			heap[index] = swap
			index = smallest
	return top


func _before(a: Array, b: Array) -> bool:
	return float(a[0]) < float(b[0]) or (float(a[0]) == float(b[0]) and int(a[1]) < int(b[1]))
