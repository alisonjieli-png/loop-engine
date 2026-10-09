# Slot inventory with stacks and a weight limit

Store items in a fixed number of slots with per-item stack limits and an optional total weight limit. Add returns what did not fit; remove, move, merge, swap, split and save to JSON-friendly data with validation.

## How it works

A fixed number of item slots with stack limits and an optional total weight limit.

Each slot is empty or holds one item id (a StringName) with a count. The stack limit and unit weight of an id
come from `item_definitions` as {id: {"max_stack": int, "weight": float}}; an id without a definition
uses `default_max_stack` and weighs nothing. Adding fills partial stacks of the same id first, in slot
order, then empty slots, and stops at the weight limit; the amount that did not fit is returned. Removing takes
from the last matching slots first and can be all-or-nothing. Moving a slot onto another moves it, merges equal
ids up to the stack limit, or swaps different ids. `to_dict` and `from_dict` save and restore the
slots as JSON-friendly data, and refuse malformed data without changing anything.

## When to use it

Use it as the model behind a backpack, chest or shop UI. Keep one instance per container in a node or autoload and connect `slot_changed` to redraw only the slots that changed.

## Installation

Copy this folder to `res://baltor/godot_components/slot_inventory/` in a Godot 4.3 or later project. The script `slot_inventory.gd` declares the global class `BaltorSlotInventory`, which extends `RefCounted`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `slot_changed(index: int)`: Emitted when the content of slot `index` changes.
- `item_added(item_id: StringName, amount: int)`: Emitted once per add_item() call that stored at least one item.
- `item_removed(item_id: StringName, amount: int)`: Emitted once per remove_item() call that removed at least one item.

### Properties

- `max_weight: float`: Largest total weight; 0 or less means no weight limit.
- `default_max_stack: int`: Stack limit for ids that have no definition.
- `item_definitions: Dictionary`: Item definitions as {id: {"max_stack": int, "weight": float}}; String or StringName keys.

### Methods

- `get_slot_count() -> int`: Number of slots.
- `resize(new_count: int) -> bool`: Changes the number of slots. Refuses (returns false) a count below 1 or a shrink that would drop items.
- `max_stack_of(item_id: StringName) -> int`: Stack limit of `item_id`.
- `weight_of(item_id: StringName) -> float`: Unit weight of `item_id`.
- `total_weight() -> float`: Weight of everything stored.
- `get_slot(index: int) -> Dictionary`: A copy of slot `index` as {"id": StringName, "count": int}, or an empty Dictionary.
- `is_slot_empty(index: int) -> bool`: True when slot `index` holds nothing (or does not exist).
- `first_empty_slot() -> int`: Index of the first empty slot, or -1.
- `set_slot(index: int, item_id: StringName, count: int) -> bool`: Puts `count` of `item_id` in slot `index`, replacing its content; a count of 0 empties it. Refuses an index out of range, a negative count, a count above the stack limit or a weight above the limit.
- `add_item(item_id: StringName, amount: int) -> int`: Adds `amount` of `item_id` and returns how many did not fit (0 when all were stored).
- `remove_item(item_id: StringName, amount: int, require_all: bool = false) -> int`: Removes up to `amount` of `item_id`, last slots first, and returns how many were removed. With `require_all` nothing is removed unless the whole amount is present.
- `count_item(item_id: StringName) -> int`: How many of `item_id` are stored in all slots.
- `has_item(item_id: StringName, amount: int = 1) -> bool`: True when at least `amount` of `item_id` are stored.
- `move_slot(from_index: int, to_index: int) -> bool`: Moves slot `from_index` onto `to_index`: into an empty slot, merged into the same id up to the stack limit, or swapped with a different id. Returns false when nothing could move.
- `split_slot(index: int, amount: int, to_index: int = -1) -> bool`: Moves `amount` items of slot `index` into the empty slot `to_index` (or the first empty slot when it is -1). The amount must leave at least one item behind.
- `clear() -> void`: Empties every slot.
- `to_dict() -> Dictionary`: The slots as JSON-friendly data: {"version": 1, "slots": [null or {"id": String, "count": int}, ...]}.
- `from_dict(data: Dictionary) -> bool`: Restores slots from `to_dict` data (counts may be JSON floats). Refuses, changing nothing, data without a non-empty slots array, entries that are not null or {"id", "count"}, counts that are not whole positive numbers within the stack limit, and contents above the weight limit.

## Usage

```gdscript
extends Node

var bag: BaltorSlotInventory = BaltorSlotInventory.new(24, 60.0)


func _ready() -> void:
	bag.item_definitions = {"arrow": {"max_stack": 50, "weight": 0.05}}
	bag.slot_changed.connect(_on_slot_changed)
	var leftover: int = bag.add_item(&"arrow", 120)
	if leftover > 0:
		print("no room for %d arrows" % leftover)


func _on_slot_changed(index: int) -> void:
	print("slot %d now holds %s" % [index, bag.get_slot(index)])
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/slot_inventory/run_tests.gd -- res://baltor/godot_components/slot_inventory/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Item definitions are plain dictionaries keyed by id, with a stack limit and unit weight only; no item instances with unique data (durability, enchantments). Slots are a flat list without shapes (see a grid inventory for that). Weight comparisons use a 1e-6 tolerance. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
