# Finite state machine with child-node states

Run one active state at a time from child nodes, with ordered exit and enter calls, an optional transition table, queued requests and a bounded history. Use it for characters, menus, doors and game flow.

## How it works

A finite state machine whose states are its child nodes.

Each child node is one state, named by its node name. The machine calls optional methods on the active state:
`state_enter(previous: StringName, data: Dictionary)`, `state_exit(next: StringName)`,
`state_process(delta: float)`, `state_physics_process(delta: float)` and
`state_input(event: InputEvent)`. A state defines only the methods it needs, so any Node works.
Transitions can be limited by a table. A transition requested while another one runs (from state_enter,
state_exit or a state_changed handler) is queued and applied right after it, in request order. A bounded
history lets go_back() return to earlier states.

## When to use it

Use it when an object has a few clear modes (idle, run, jump, dead) and each mode needs its own per-frame logic. Each state stays a small node script with only the callbacks it needs, and the table makes illegal moves fail loudly through a signal instead of silently.

## Installation

Copy this folder to `res://baltor/godot_components/finite_state_machine/` in a Godot 4.3 or later project. The script `finite_state_machine.gd` declares the global class `BaltorStateMachine`, which extends `Node`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `state_changed(previous: StringName, current: StringName)`: Emitted after a transition completes.
- `transition_refused(from_state: StringName, to_state: StringName, reason: String)`: Emitted when a request is refused; `reason` is "not started", "unknown state", "not allowed" or "cannot go back".

### Exported properties

- `initial_state: StringName = &""`: Name of the child that becomes active on start. Empty means the first child.
- `auto_start: bool = true`: Start automatically when the node is ready.
- `allowed_transitions: Dictionary = {}`: Allowed transitions as {from_name: [to_name, ...]}. An empty table allows every transition.
- `history_size: int = 8` (@export_range(0, 64)): How many previous states go_back() can return through.

### Properties

- `time_in_state: float`: Seconds spent in the current state, advanced every process frame.

### Methods

- `start(data: Dictionary = {}) -> bool`: Enters `initial_state`, or the first child when it is empty. Returns false when there is no such state. Calling it again while running does nothing and returns true.
- `stop() -> void`: Exits the active state and returns to the stopped condition. The history is kept.
- `transition_to(state_name: StringName, data: Dictionary = {}) -> bool`: Requests a transition to `state_name` with optional `data` for state_enter. Returns false when it is refused. A request made during another transition is queued, returns true and is checked when applied.
- `go_back(data: Dictionary = {}) -> bool`: Returns to the most recent state in the history. Returns false when the history is empty or the move is not allowed.
- `has_state(state_name: StringName) -> bool`: True when a child node named `state_name` exists.
- `get_state_node(state_name: StringName) -> Node`: The child node for `state_name`, or null.
- `get_current_state() -> StringName`: The active state's name, or an empty StringName while stopped.
- `get_state_names() -> PackedStringArray`: The state names in child order.
- `get_history() -> Array[StringName]`: Previous states, oldest first.
- `can_transition(from_state: StringName, to_state: StringName) -> bool`: True when the transition table allows `from_state` to `to_state` (always with an empty table).

## Usage

```gdscript
extends CharacterBody2D

@onready var machine: BaltorStateMachine = $StateMachine


func _ready() -> void:
	machine.state_changed.connect(_on_state_changed)
	machine.transition_refused.connect(_on_refused)


func _physics_process(_delta: float) -> void:
	if machine.get_current_state() == &"Idle" and Input.is_action_pressed("ui_right"):
		machine.transition_to(&"Run", {"direction": 1})


func _on_state_changed(previous: StringName, current: StringName) -> void:
	print("%s -> %s" % [previous, current])


func _on_refused(from_state: StringName, to_state: StringName, reason: String) -> void:
	push_warning("%s -> %s refused: %s" % [from_state, to_state, reason])
```

## Example scene

`example.tscn` holds a machine with two plain states, Idle and Walk, an initial state and a transition table. Attach scripts with `state_enter` and `state_process` to the state nodes to give them behavior.

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/finite_state_machine/run_tests.gd -- res://baltor/godot_components/finite_state_machine/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

One active state; no parallel or nested states (see the hierarchical state machine). States are found by node name among direct children. Queued requests are checked when they are applied, not when they are made. Input reaches the active state through _unhandled_input only. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
