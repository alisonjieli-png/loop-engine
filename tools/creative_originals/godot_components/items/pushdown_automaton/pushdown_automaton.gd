class_name BaltorStateStack
extends Node
## A pushdown automaton: a stack of state objects where only the top runs, for screens and modal states.
##
## A state is any Object; the stack calls the methods it defines: [code]stack_enter(data: Dictionary)[/code]
## when it is pushed or becomes top by replace, [code]stack_exit()[/code] when it is popped or replaced,
## [code]stack_pause()[/code] when another state is pushed over it, [code]stack_resume()[/code] when it is on top
## again, and [code]stack_update(delta: float)[/code] every frame while it runs. With
## [member update_all] every state updates, bottom first; otherwise only the top does. The stack never holds the
## same object twice and refuses to grow past [member max_depth]. Typical use: a pause menu pushed over gameplay,
## an inventory screen over the pause menu, each one popping back to exactly where the game was.

## Emitted after a state is pushed.
signal pushed(state: Object)
## Emitted after a state is popped.
signal popped(state: Object)
## Emitted when the top changes, with the old and new top (null when the stack is empty).
signal top_changed(previous: Object, current: Object)

## Largest number of states on the stack.
@export_range(1, 256) var max_depth: int = 16
## Update every state each frame (bottom first) instead of only the top one.
@export var update_all: bool = false

var _stack: Array[Object] = []


func _process(delta: float) -> void:
	update(delta)


## Pushes [param state] with [param data] for its stack_enter: the old top pauses first. Refuses null, a state
## already on the stack and a full stack.
func push(state: Object, data: Dictionary = {}) -> bool:
	if state == null or _stack.has(state) or _stack.size() >= max_depth:
		return false
	var previous: Object = peek()
	_call(previous, &"stack_pause")
	_stack.append(state)
	_call(state, &"stack_enter", [data])
	pushed.emit(state)
	top_changed.emit(previous, state)
	return true


## Pops the top state (its stack_exit runs, then the new top resumes) and returns it, or null when empty.
func pop() -> Object:
	if _stack.is_empty():
		return null
	var leaving: Object = _stack.pop_back()
	_call(leaving, &"stack_exit")
	var current: Object = peek()
	_call(current, &"stack_resume")
	popped.emit(leaving)
	top_changed.emit(leaving, current)
	return leaving


## Replaces the top state with [param state] without pausing or resuming the states below. On an empty stack it
## behaves like push(). Refuses null and a state already on the stack.
func replace(state: Object, data: Dictionary = {}) -> bool:
	if state == null or _stack.has(state):
		return false
	if _stack.is_empty():
		return push(state, data)
	var leaving: Object = _stack.pop_back()
	_call(leaving, &"stack_exit")
	_stack.append(state)
	_call(state, &"stack_enter", [data])
	popped.emit(leaving)
	pushed.emit(state)
	top_changed.emit(leaving, state)
	return true


## Pops states until [param state] is on top. Returns false (and pops nothing) when it is not on the stack.
func pop_to(state: Object) -> bool:
	if not _stack.has(state):
		return false
	while peek() != state:
		pop()
	return true


## Pops every state, top first.
func clear() -> void:
	while not _stack.is_empty():
		pop()


## The top state, or null.
func peek() -> Object:
	return _stack.back() if not _stack.is_empty() else null


## Number of states on the stack.
func depth() -> int:
	return _stack.size()


## True when [param state] is somewhere on the stack.
func contains(state: Object) -> bool:
	return _stack.has(state)


## Calls stack_update(delta) on the top state, or on every state bottom first with update_all.
func update(delta: float) -> void:
	if _stack.is_empty():
		return
	if not update_all:
		_call(_stack.back(), &"stack_update", [delta])
		return
	for state: Object in _stack.duplicate():
		_call(state, &"stack_update", [delta])


func _call(state: Object, method: StringName, arguments: Array = []) -> void:
	if state != null and is_instance_valid(state) and state.has_method(method):
		state.callv(method, arguments)
