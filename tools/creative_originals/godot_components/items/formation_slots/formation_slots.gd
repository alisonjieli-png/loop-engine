class_name BaltorFormation
extends RefCounted
## Formation slot layouts (line, column, wedge, circle, grid) and an assignment of members to slots that keeps
## the total travel distance short.
##
## Offsets are in formation space: the formation faces +x, slot 0 is the anchor at the origin (except for the
## circle, whose slots ring the anchor), and the other slots spread sideways (y) and behind (-x) at the given
## spacing. world_slots() rotates and moves them to an anchor position and facing angle. assign() first pairs the
## closest member and slot globally, then swaps pairs of assignments while a swap shortens the total, which
## removes crossing paths; it is a heuristic, not an optimal assignment.

## Formation layouts.
enum Shape { LINE, COLUMN, WEDGE, CIRCLE, GRID }


## Local offsets of [param count] slots for [param shape] at [param spacing].
static func slot_offsets(shape: Shape, count: int, spacing: float) -> PackedVector2Array:
	var offsets := PackedVector2Array()
	if count <= 0:
		return offsets
	match shape:
		Shape.LINE:
			for index in range(count):
				offsets.append(Vector2(0.0, (index - (count - 1) * 0.5) * spacing))
		Shape.COLUMN:
			for index in range(count):
				offsets.append(Vector2(-index * spacing, 0.0))
		Shape.WEDGE:
			offsets.append(Vector2.ZERO)
			for index in range(1, count):
				var row: int = (index + 1) >> 1
				var side: float = -1.0 if index % 2 == 1 else 1.0
				offsets.append(Vector2(-row * spacing, side * row * spacing))
		Shape.CIRCLE:
			var radius: float = maxf(spacing * count / TAU, spacing * 0.5)
			for index in range(count):
				offsets.append(Vector2.from_angle(TAU * index / count) * radius)
		Shape.GRID:
			var columns: int = ceili(sqrt(float(count)))
			for index in range(count):
				var column: int = index % columns
				var row: int = floori(float(index) / float(columns))
				offsets.append(Vector2(-row * spacing, (column - (columns - 1) * 0.5) * spacing))
	return offsets


## [param offsets] rotated by [param facing_angle] (radians) and moved to [param anchor].
static func world_slots(offsets: PackedVector2Array, anchor: Vector2, facing_angle: float) -> PackedVector2Array:
	var placed := PackedVector2Array()
	for offset: Vector2 in offsets:
		placed.append(anchor + offset.rotated(facing_angle))
	return placed


## The slot index for each member (same order as [param members]). Refuses (empty result) different sizes.
static func assign(members: PackedVector2Array, slots: PackedVector2Array) -> PackedInt32Array:
	var result := PackedInt32Array()
	if members.size() != slots.size():
		return result
	var count: int = members.size()
	result.resize(count)
	result.fill(-1)
	var taken: Dictionary = {}
	for _round in range(count):
		var best_member: int = -1
		var best_slot: int = -1
		var best_distance: float = INF
		for member in range(count):
			if result[member] >= 0:
				continue
			for slot in range(count):
				if taken.has(slot):
					continue
				var distance: float = members[member].distance_squared_to(slots[slot])
				if distance < best_distance:
					best_distance = distance
					best_member = member
					best_slot = slot
		result[best_member] = best_slot
		taken[best_slot] = true
	var improved: bool = true
	var passes: int = 0
	while improved and passes < 32:
		improved = false
		passes += 1
		for a in range(count):
			for b in range(a + 1, count):
				var now: float = members[a].distance_to(slots[result[a]]) + members[b].distance_to(slots[result[b]])
				var swapped: float = members[a].distance_to(slots[result[b]]) + members[b].distance_to(slots[result[a]])
				if swapped < now - 0.000001:
					var keep: int = result[a]
					result[a] = result[b]
					result[b] = keep
					improved = true
	return result


## Sum of the distances from each member to its assigned slot.
static func total_distance(members: PackedVector2Array, slots: PackedVector2Array,
		assignment: PackedInt32Array) -> float:
	var total: float = 0.0
	for member in range(mini(members.size(), assignment.size())):
		total += members[member].distance_to(slots[assignment[member]])
	return total
