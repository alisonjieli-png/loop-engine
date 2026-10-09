# Hierarchical state machine with event bubbling and history

Define nested states in code with event transitions that bubble from the leaf to its ancestors, guards, entry and exit in hierarchy order and shallow history, so shared behavior lives in parent states.

## How it works

A hierarchical state machine built in code: nested states, events that bubble up the hierarchy, guards,
entry and exit in hierarchy order, and optional shallow history.

Every state has a name and an optional parent. A state with children is composite: entering it also enters
its initial child (the first child added unless set_initial() picked another), down to a leaf. While running,
the machine is in exactly one leaf and in all of that leaf's ancestors. send() offers an event to the leaf
first and then to each ancestor; the first transition for the event whose guard accepts the data is taken.
Taking it exits states from the leaf up to, but not including, the lowest common ancestor of the leaf and the
target, then enters states from below that ancestor down to the target and on to a leaf. A transition whose
target is the leaf or one of its ancestors exits and re-enters that target. A composite with history enabled
re-enters the child that was active when it was last exited. Callbacks are Callables: enter and exit take no
arguments, update takes the delta, and a guard takes the event data Dictionary and returns bool.

## When to use it

Use it when several states share transitions, for example every ground state reacting to jump or hit, so the shared rule is written once on a parent instead of on every child.

## Installation

Copy this folder to `res://baltor/godot_components/hierarchical_state_machine/` in a Godot 4.3 or later project. The script `hierarchical_state_machine.gd` declares the global class `BaltorHierarchicalStateMachine`, which extends `RefCounted`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `state_entered(state_name: StringName)`: Emitted after a state is entered.
- `state_exited(state_name: StringName)`: Emitted after a state is exited.
- `transitioned(from_leaf: StringName, to_leaf: StringName, event: StringName)`: Emitted after a transition, with the leaf before and after and the event (empty for start).

### Methods

- `add_state(state_name: StringName, parent_name: StringName = &"", on_enter: Callable = Callable(), on_exit: Callable = Callable(), on_update: Callable = Callable()) -> bool`: Adds a state under `parent_name` (empty for the top level) with optional callbacks. Refuses an empty or repeated name and an unknown parent.
- `set_initial(parent_name: StringName, child_name: StringName) -> bool`: Makes `child_name` the initial child of `parent_name` (empty for the top level).
- `set_history(state_name: StringName, enabled: bool) -> bool`: Turns shallow history on or off for the composite `state_name`.
- `add_transition(from_state: StringName, event: StringName, to_state: StringName, guard: Callable = Callable()) -> bool`: Adds a transition from `from_state` on `event` to `to_state`, taken only when the optional `guard` returns true for the event data. Refuses unknown states or an empty event.
- `start() -> bool`: Enters the initial top-level state and its initial descendants. Returns false when already running or empty.
- `stop() -> void`: Exits every active state, leaf first.
- `send(event: StringName, data: Dictionary = {}) -> bool`: Offers `event` to the leaf and then its ancestors; returns true when a transition was taken.
- `update(delta: float) -> void`: Calls the update callbacks of the active states, outermost first.
- `get_leaf() -> StringName`: The active leaf, or an empty StringName when stopped.
- `get_active_path() -> Array[StringName]`: The active states from the top level down to the leaf.
- `is_in(state_name: StringName) -> bool`: True when `state_name` is the leaf or one of its ancestors.
- `has_state(state_name: StringName) -> bool`: True when `state_name` was added.
- `is_running() -> bool`: True between start() and stop().

## Usage

```gdscript
extends Node

var machine: BaltorHierarchicalStateMachine = BaltorHierarchicalStateMachine.new()


func _ready() -> void:
	machine.add_state(&"Ground")
	machine.add_state(&"Idle", &"Ground")
	machine.add_state(&"Run", &"Ground")
	machine.add_state(&"Air", &"", _on_air_entered)
	machine.add_transition(&"Ground", &"jump", &"Air")
	machine.add_transition(&"Idle", &"move", &"Run")
	machine.add_transition(&"Air", &"land", &"Ground")
	machine.set_history(&"Ground", true)
	machine.start()


func _on_air_entered() -> void:
	print("airborne; path is %s" % [machine.get_active_path()])
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/hierarchical_state_machine/run_tests.gd -- res://baltor/godot_components/hierarchical_state_machine/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

A subset of statecharts: no orthogonal (parallel) regions, no deep history, no internal transitions and no delayed events. Callbacks run synchronously; sending an event from inside a callback is not queued and runs immediately. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
