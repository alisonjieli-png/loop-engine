# Pushdown state stack for screens and modal states

Keep a stack of state objects where only the top runs: pushing pauses the state below, popping resumes it, replace swaps the top, and pop_to unwinds several levels. Use it for pause menus and nested screens.

## How it works

A pushdown automaton: a stack of state objects where only the top runs, for screens and modal states.

A state is any Object; the stack calls the methods it defines: `stack_enter(data: Dictionary)`
when it is pushed or becomes top by replace, `stack_exit()` when it is popped or replaced,
`stack_pause()` when another state is pushed over it, `stack_resume()` when it is on top
again, and `stack_update(delta: float)` every frame while it runs. With
`update_all` every state updates, bottom first; otherwise only the top does. The stack never holds the
same object twice and refuses to grow past `max_depth`. Typical use: a pause menu pushed over gameplay,
an inventory screen over the pause menu, each one popping back to exactly where the game was.

## When to use it

Use it when states nest and must return exactly where they were: gameplay under a pause menu under an options screen, or an interrupted AI task resumed after a short reaction.

## Installation

Copy this folder to `res://baltor/godot_components/pushdown_automaton/` in a Godot 4.3 or later project. The script `pushdown_automaton.gd` declares the global class `BaltorStateStack`, which extends `Node`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `pushed(state: Object)`: Emitted after a state is pushed.
- `popped(state: Object)`: Emitted after a state is popped.
- `top_changed(previous: Object, current: Object)`: Emitted when the top changes, with the old and new top (null when the stack is empty).

### Exported properties

- `max_depth: int = 16` (@export_range(1, 256)): Largest number of states on the stack.
- `update_all: bool = false`: Update every state each frame (bottom first) instead of only the top one.

### Methods

- `push(state: Object, data: Dictionary = {}) -> bool`: Pushes `state` with `data` for its stack_enter: the old top pauses first. Refuses null, a state already on the stack and a full stack.
- `pop() -> Object`: Pops the top state (its stack_exit runs, then the new top resumes) and returns it, or null when empty.
- `replace(state: Object, data: Dictionary = {}) -> bool`: Replaces the top state with `state` without pausing or resuming the states below. On an empty stack it behaves like push(). Refuses null and a state already on the stack.
- `pop_to(state: Object) -> bool`: Pops states until `state` is on top. Returns false (and pops nothing) when it is not on the stack.
- `clear() -> void`: Pops every state, top first.
- `peek() -> Object`: The top state, or null.
- `depth() -> int`: Number of states on the stack.
- `contains(state: Object) -> bool`: True when `state` is somewhere on the stack.
- `update(delta: float) -> void`: Calls stack_update(delta) on the top state, or on every state bottom first with update_all.

## Usage

```gdscript
extends Node

var stack: BaltorStateStack


class PauseMenu extends RefCounted:
	func stack_enter(_data: Dictionary) -> void:
		print("paused")

	func stack_exit() -> void:
		print("resumed")


func _ready() -> void:
	stack = BaltorStateStack.new()
	add_child(stack)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		if stack.depth() == 0:
			stack.push(PauseMenu.new())
		else:
			stack.pop()
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/pushdown_automaton/run_tests.gd -- res://baltor/godot_components/pushdown_automaton/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

States are plain objects found by the methods they define; the stack holds references and does not free them. Callbacks run synchronously in push and pop order. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
