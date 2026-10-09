class_name BaltorSlotInventory
extends RefCounted
## A fixed number of item slots with stack limits and an optional total weight limit.
##
## Each slot is empty or holds one item id (a StringName) with a count. The stack limit and unit weight of an id
## come from [member item_definitions] as {id: {"max_stack": int, "weight": float}}; an id without a definition
## uses [member default_max_stack] and weighs nothing. Adding fills partial stacks of the same id first, in slot
## order, then empty slots, and stops at the weight limit; the amount that did not fit is returned. Removing takes
## from the last matching slots first and can be all-or-nothing. Moving a slot onto another moves it, merges equal
## ids up to the stack limit, or swaps different ids. [method to_dict] and [method from_dict] save and restore the
## slots as JSON-friendly data, and refuse malformed data without changing anything.

## Emitted when the content of slot [param index] changes.
signal slot_changed(index: int)
## Emitted once per add_item() call that stored at least one item.
signal item_added(item_id: StringName, amount: int)
## Emitted once per remove_item() call that removed at least one item.
signal item_removed(item_id: StringName, amount: int)

## Largest total weight; 0 or less means no weight limit.
var max_weight: float = 0.0
## Stack limit for ids that have no definition.
var default_max_stack: int = 99
## Item definitions as {id: {"max_stack": int, "weight": float}}; String or StringName keys.
var item_definitions: Dictionary = {}

var _slots: Array[Dictionary] = []


func _init(slots: int = 20, weight_limit: float = 0.0) -> void:
	for _index in range(maxi(slots, 1)):
		_slots.append({})
	max_weight = weight_limit


## Number of slots.
func get_slot_count() -> int:
	return _slots.size()


## Changes the number of slots. Refuses (returns false) a count below 1 or a shrink that would drop items.
func resize(new_count: int) -> bool:
	if new_count < 1:
		return false
	for index in range(new_count, _slots.size()):
		if not _slots[index].is_empty():
			return false
	while _slots.size() > new_count:
		_slots.pop_back()
	while _slots.size() < new_count:
		_slots.append({})
	return true


## Stack limit of [param item_id].
func max_stack_of(item_id: StringName) -> int:
	return maxi(int(_definition(item_id).get("max_stack", default_max_stack)), 1)


## Unit weight of [param item_id].
func weight_of(item_id: StringName) -> float:
	return maxf(float(_definition(item_id).get("weight", 0.0)), 0.0)


## Weight of everything stored.
func total_weight() -> float:
	var total: float = 0.0
	for slot: Dictionary in _slots:
		if not slot.is_empty():
			total += weight_of(slot["id"]) * int(slot["count"])
	return total


## A copy of slot [param index] as {"id": StringName, "count": int}, or an empty Dictionary.
func get_slot(index: int) -> Dictionary:
	return _slots[index].duplicate() if _valid(index) else {}


## True when slot [param index] holds nothing (or does not exist).
func is_slot_empty(index: int) -> bool:
	return not _valid(index) or _slots[index].is_empty()


## Index of the first empty slot, or -1.
func first_empty_slot() -> int:
	for index in range(_slots.size()):
		if _slots[index].is_empty():
			return index
	return -1


## Puts [param count] of [param item_id] in slot [param index], replacing its content; a count of 0 empties it.
## Refuses an index out of range, a negative count, a count above the stack limit or a weight above the limit.
func set_slot(index: int, item_id: StringName, count: int) -> bool:
	if not _valid(index) or count < 0:
		return false
	if count == 0 or item_id == &"":
		_slots[index] = {}
		slot_changed.emit(index)
		return true
	if count > max_stack_of(item_id):
		return false
	var current: Dictionary = _slots[index]
	var freed: float = 0.0 if current.is_empty() else weight_of(current["id"]) * int(current["count"])
	if max_weight > 0.0 and total_weight() - freed + weight_of(item_id) * count > max_weight + 0.000001:
		return false
	_slots[index] = {"id": item_id, "count": count}
	slot_changed.emit(index)
	return true


## Adds [param amount] of [param item_id] and returns how many did not fit (0 when all were stored).
func add_item(item_id: StringName, amount: int) -> int:
	if amount <= 0:
		return 0
	if item_id == &"":
		return amount
	var remaining: int = mini(amount, _weight_room(item_id))
	var refused_by_weight: int = amount - remaining
	var stack: int = max_stack_of(item_id)
	var added: int = 0
	for index in range(_slots.size()):
		if remaining == 0:
			break
		var slot: Dictionary = _slots[index]
		if slot.is_empty() or slot["id"] != item_id or int(slot["count"]) >= stack:
			continue
		var moved: int = mini(stack - int(slot["count"]), remaining)
		slot["count"] = int(slot["count"]) + moved
		remaining -= moved
		added += moved
		slot_changed.emit(index)
	for index in range(_slots.size()):
		if remaining == 0:
			break
		if not _slots[index].is_empty():
			continue
		var moved: int = mini(stack, remaining)
		_slots[index] = {"id": item_id, "count": moved}
		remaining -= moved
		added += moved
		slot_changed.emit(index)
	if added > 0:
		item_added.emit(item_id, added)
	return remaining + refused_by_weight


## Removes up to [param amount] of [param item_id], last slots first, and returns how many were removed. With
## [param require_all] nothing is removed unless the whole amount is present.
func remove_item(item_id: StringName, amount: int, require_all: bool = false) -> int:
	if amount <= 0 or (require_all and count_item(item_id) < amount):
		return 0
	var removed: int = 0
	for index in range(_slots.size() - 1, -1, -1):
		if removed == amount:
			break
		var slot: Dictionary = _slots[index]
		if slot.is_empty() or slot["id"] != item_id:
			continue
		var taken: int = mini(int(slot["count"]), amount - removed)
		removed += taken
		if taken == int(slot["count"]):
			_slots[index] = {}
		else:
			slot["count"] = int(slot["count"]) - taken
		slot_changed.emit(index)
	if removed > 0:
		item_removed.emit(item_id, removed)
	return removed


## How many of [param item_id] are stored in all slots.
func count_item(item_id: StringName) -> int:
	var total: int = 0
	for slot: Dictionary in _slots:
		if not slot.is_empty() and slot["id"] == item_id:
			total += int(slot["count"])
	return total


## True when at least [param amount] of [param item_id] are stored.
func has_item(item_id: StringName, amount: int = 1) -> bool:
	return count_item(item_id) >= amount


## Moves slot [param from_index] onto [param to_index]: into an empty slot, merged into the same id up to the
## stack limit, or swapped with a different id. Returns false when nothing could move.
func move_slot(from_index: int, to_index: int) -> bool:
	if not _valid(from_index) or not _valid(to_index) or from_index == to_index:
		return false
	var source: Dictionary = _slots[from_index]
	var target: Dictionary = _slots[to_index]
	if source.is_empty():
		return false
	if target.is_empty() or target["id"] != source["id"]:
		_slots[to_index] = source
		_slots[from_index] = target
	else:
		var moved: int = mini(max_stack_of(source["id"]) - int(target["count"]), int(source["count"]))
		if moved <= 0:
			return false
		target["count"] = int(target["count"]) + moved
		source["count"] = int(source["count"]) - moved
		if int(source["count"]) == 0:
			_slots[from_index] = {}
	slot_changed.emit(from_index)
	slot_changed.emit(to_index)
	return true


## Moves [param amount] items of slot [param index] into the empty slot [param to_index] (or the first empty
## slot when it is -1). The amount must leave at least one item behind.
func split_slot(index: int, amount: int, to_index: int = -1) -> bool:
	if not _valid(index) or _slots[index].is_empty():
		return false
	var source: Dictionary = _slots[index]
	if amount <= 0 or amount >= int(source["count"]):
		return false
	var target_index: int = to_index if to_index >= 0 else first_empty_slot()
	if not _valid(target_index) or target_index == index or not _slots[target_index].is_empty():
		return false
	_slots[target_index] = {"id": source["id"], "count": amount}
	source["count"] = int(source["count"]) - amount
	slot_changed.emit(index)
	slot_changed.emit(target_index)
	return true


## Empties every slot.
func clear() -> void:
	for index in range(_slots.size()):
		if not _slots[index].is_empty():
			_slots[index] = {}
			slot_changed.emit(index)


## The slots as JSON-friendly data: {"version": 1, "slots": [null or {"id": String, "count": int}, ...]}.
func to_dict() -> Dictionary:
	var slots: Array = []
	for slot: Dictionary in _slots:
		if slot.is_empty():
			slots.append(null)
		else:
			slots.append({"id": String(slot["id"]), "count": int(slot["count"])})
	return {"version": 1, "slots": slots}


## Restores slots from [method to_dict] data (counts may be JSON floats). Refuses, changing nothing, data
## without a non-empty slots array, entries that are not null or {"id", "count"}, counts that are not whole
## positive numbers within the stack limit, and contents above the weight limit.
func from_dict(data: Dictionary) -> bool:
	var slots: Variant = data.get("slots")
	if typeof(slots) != TYPE_ARRAY or (slots as Array).is_empty():
		return false
	var parsed: Array[Dictionary] = []
	var weight: float = 0.0
	for entry: Variant in slots:
		if entry == null:
			parsed.append({})
			continue
		if typeof(entry) != TYPE_DICTIONARY:
			return false
		var id_value: Variant = (entry as Dictionary).get("id")
		var count_value: Variant = (entry as Dictionary).get("count")
		if not (typeof(id_value) in [TYPE_STRING, TYPE_STRING_NAME]) or String(id_value).is_empty():
			return false
		if not (typeof(count_value) in [TYPE_INT, TYPE_FLOAT]) or float(count_value) != floorf(float(count_value)):
			return false
		var item_id := StringName(String(id_value))
		var count: int = int(count_value)
		if count <= 0 or count > max_stack_of(item_id):
			return false
		weight += weight_of(item_id) * count
		parsed.append({"id": item_id, "count": count})
	if max_weight > 0.0 and weight > max_weight + 0.000001:
		return false
	_slots = parsed
	for index in range(_slots.size()):
		slot_changed.emit(index)
	return true


func _valid(index: int) -> bool:
	return index >= 0 and index < _slots.size()


func _definition(item_id: StringName) -> Dictionary:
	var found: Variant = item_definitions.get(item_id, item_definitions.get(String(item_id), {}))
	if typeof(found) == TYPE_DICTIONARY:
		return found
	return {}


func _weight_room(item_id: StringName) -> int:
	var unit: float = weight_of(item_id)
	if max_weight <= 0.0 or unit <= 0.0:
		return 1 << 30
	return maxi(int(floor((max_weight - total_weight()) / unit + 0.000001)), 0)
