# Data-driven state machine from a JSON transition table

Load states and event transitions from a Dictionary or JSON file, with wildcard rows, named guards and named actions registered in code, validation that refuses malformed tables, and signals for taken and ignored events.

## How it works

A data-driven state machine: states and event transitions come from a Dictionary, such as parsed JSON, and
guards and actions are named Callables registered in code.

A table has "initial", "states" (names) and "transitions": a list of {"from", "event", "to"} with optional
"guard" (a registered guard name) and "actions" (registered action names, run in order with the payload).
"from" may be "*" to match any state. fire() checks the transitions from the exact current state first, then
the wildcard ones, each group in table order, and takes the first whose guard accepts the payload. Designers can
edit door, quest or menu flows in a JSON file while programmers own the guard and action code. load_table()
validates the whole table first and changes nothing when it is malformed; get_errors() says why.

## When to use it

Use it when designers should edit flows (doors, quests, menus, tutorials) as data while the code only provides the guard and action functions.

## Installation

Copy this folder to `res://baltor/godot_components/event_transition_table/` in a Godot 4.3 or later project. The script `event_transition_table.gd` declares the global class `BaltorTransitionTable`, which extends `RefCounted`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `transitioned(from_state: StringName, to_state: StringName, event: StringName)`: Emitted after a transition and its actions.
- `event_ignored(state: StringName, event: StringName)`: Emitted when fire() finds no transition for the event in the current state.

### Methods

- `register_guard(guard_name: StringName, guard: Callable) -> void`: Registers a guard: `guard` is called with the payload Dictionary and returns bool.
- `register_action(action_name: StringName, action: Callable) -> void`: Registers an action: `action` is called with the payload Dictionary.
- `load_table(table: Dictionary) -> bool`: Loads and validates `table`; on success the machine is in the initial state. Returns false, changing nothing, when the table is malformed.
- `get_errors() -> PackedStringArray`: Why the last load_table() call failed (empty after a success).
- `fire(event: StringName, payload: Dictionary = {}) -> bool`: Offers `event` with `payload`; returns true when a transition was taken.
- `get_state() -> StringName`: The current state, or an empty StringName before a table is loaded.
- `reset() -> void`: Returns to the initial state without running actions.
- `available_events() -> PackedStringArray`: Events that have a transition from the current state (guards not evaluated), without repeats.

## Usage

```gdscript
extends Node

var door: BaltorTransitionTable = BaltorTransitionTable.new()


func _ready() -> void:
	door.register_guard(&"not_blocked", func(payload: Dictionary) -> bool: return not payload.get("blocked", false))
	door.register_guard(&"has_key", func(payload: Dictionary) -> bool: return payload.get("key", "") == "brass")
	door.register_action(&"play_creak", func(_payload: Dictionary) -> void: print("creak"))
	door.register_action(&"spawn_debris", func(_payload: Dictionary) -> void: print("debris"))
	var path: String = get_script().resource_path.get_base_dir().path_join("door_table.json")
	if not door.load_table(JSON.parse_string(FileAccess.get_file_as_string(path))):
		push_error(", ".join(door.get_errors()))
	door.fire(&"open")
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/event_transition_table/run_tests.gd -- res://baltor/godot_components/event_transition_table/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Flat states only. Guards and actions must be registered before load_table(). The first matching row wins; there are no priorities beyond table order and exact-before-wildcard. door_table.json is sample data. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
