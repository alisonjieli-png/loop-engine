extends "../baltor_test.gd"
## Tests for BaltorSlotInventory: stacking order, leftovers, the weight limit, removal, moving, splitting,
## resizing and the refusal of malformed save data.

const Subject := preload("../slot_inventory.gd")


func _inventory(slots: int = 4, weight_limit: float = 0.0) -> Subject:
	var inventory: Subject = Subject.new(slots, weight_limit)
	inventory.item_definitions = {"potion": {"max_stack": 5, "weight": 0.5}, "ore": {"max_stack": 10, "weight": 2.0}}
	return inventory


func test_adding_fills_partial_stacks_then_empty_slots_and_returns_leftover() -> void:
	var inventory := _inventory(3)
	assert_true(inventory.set_slot(1, &"potion", 3))
	watch_signals(inventory)
	assert_eq(inventory.add_item(&"potion", 6), 0)
	assert_eq(inventory.get_slot(1), {"id": &"potion", "count": 5})
	assert_eq(inventory.get_slot(0), {"id": &"potion", "count": 4})
	assert_eq(inventory.add_item(&"potion", 9), 3)
	assert_eq(inventory.count_item(&"potion"), 15)
	assert_eq(signal_emissions(inventory, &"item_added"), [[&"potion", 6], [&"potion", 6]])
	assert_eq(inventory.add_item(&"", 2), 2, "an empty id stores nothing")
	assert_eq(inventory.add_item(&"potion", -4), 0)


func test_weight_limit_stores_only_what_fits() -> void:
	var inventory := _inventory(4, 9.0)
	assert_eq(inventory.add_item(&"ore", 6), 2, "four ore weigh 8.0 of 9.0")
	assert_almost_eq(inventory.total_weight(), 8.0)
	assert_eq(inventory.add_item(&"potion", 3), 1, "two potions fill the last 1.0")
	assert_almost_eq(inventory.total_weight(), 9.0)
	assert_eq(inventory.add_item(&"feather", 50), 0, "an undefined id weighs nothing")
	assert_eq(inventory.max_stack_of(&"feather"), 99)


func test_remove_takes_from_the_last_slots_and_can_require_all() -> void:
	var inventory := _inventory(3)
	inventory.add_item(&"potion", 12)
	watch_signals(inventory)
	assert_eq(inventory.remove_item(&"potion", 4), 4)
	assert_eq(inventory.get_slot(2), {})
	assert_eq(inventory.get_slot(1), {"id": &"potion", "count": 3})
	assert_eq(inventory.remove_item(&"potion", 20, true), 0, "not enough for an all-or-nothing request")
	assert_eq(inventory.count_item(&"potion"), 8)
	assert_eq(inventory.remove_item(&"potion", 20), 8)
	assert_false(inventory.has_item(&"potion"))
	assert_eq(signal_emissions(inventory, &"item_removed"), [[&"potion", 4], [&"potion", 8]])


func test_move_slot_moves_merges_and_swaps() -> void:
	var inventory := _inventory(4)
	inventory.set_slot(0, &"potion", 4)
	inventory.set_slot(1, &"potion", 3)
	inventory.set_slot(2, &"ore", 7)
	assert_true(inventory.move_slot(1, 0), "merge up to the stack limit")
	assert_eq(inventory.get_slot(0), {"id": &"potion", "count": 5})
	assert_eq(inventory.get_slot(1), {"id": &"potion", "count": 2})
	assert_true(inventory.move_slot(2, 3))
	assert_true(inventory.is_slot_empty(2))
	assert_true(inventory.move_slot(3, 1), "different ids swap")
	assert_eq(inventory.get_slot(1), {"id": &"ore", "count": 7})
	assert_eq(inventory.get_slot(3), {"id": &"potion", "count": 2})
	assert_false(inventory.move_slot(2, 1), "an empty source moves nothing")
	assert_false(inventory.move_slot(0, 9), "out of range")


func test_split_slot_keeps_at_least_one_behind() -> void:
	var inventory := _inventory(3)
	inventory.set_slot(0, &"ore", 6)
	assert_true(inventory.split_slot(0, 2))
	assert_eq(inventory.get_slot(1), {"id": &"ore", "count": 2})
	assert_eq(inventory.get_slot(0), {"id": &"ore", "count": 4})
	assert_false(inventory.split_slot(0, 4), "splitting the whole stack is refused")
	assert_false(inventory.split_slot(0, 1, 1), "the target must be empty")
	assert_true(inventory.split_slot(0, 1, 2))
	assert_eq(inventory.count_item(&"ore"), 6)


func test_save_data_round_trips_and_malformed_data_is_refused() -> void:
	var inventory := _inventory(3, 20.0)
	inventory.add_item(&"ore", 3)
	inventory.add_item(&"potion", 2)
	var saved: Dictionary = JSON.parse_string(JSON.stringify(inventory.to_dict()))
	var restored := _inventory(3, 20.0)
	assert_true(restored.from_dict(saved))
	assert_eq(restored.to_dict(), inventory.to_dict())
	var bad_cases: Array[Dictionary] = [
		{"slots": [{"id": "ore", "count": -1}]},
		{"slots": [{"id": "potion", "count": 6}]},
		{"slots": [{"id": "ore", "count": 1.5}]},
		{"slots": ["ore"]},
		{"slots": []},
		{"slots": [{"id": "ore", "count": 10}, {"id": "ore", "count": 1}]},
	]
	for bad: Dictionary in bad_cases:
		assert_false(restored.from_dict(bad), str(bad))
	assert_eq(restored.to_dict(), inventory.to_dict(), "refused data changes nothing")


func test_resize_and_set_slot_refuse_invalid_requests() -> void:
	var inventory := _inventory(4)
	inventory.set_slot(3, &"ore", 1)
	assert_false(inventory.resize(2), "slot 3 holds an item")
	assert_eq(inventory.get_slot_count(), 4)
	inventory.clear()
	assert_true(inventory.resize(2))
	assert_eq(inventory.get_slot_count(), 2)
	assert_false(inventory.resize(0))
	assert_false(inventory.set_slot(0, &"potion", 6), "above the stack limit")
	assert_false(inventory.set_slot(5, &"potion", 1), "out of range")
