class_name BaltorStateMachine
extends Node
## A finite state machine whose states are its child nodes.
##
## Each child node is one state, named by its node name. The machine calls optional methods on the active state:
## [code]state_enter(previous: StringName, data: Dictionary)[/code], [code]state_exit(next: StringName)[/code],
## [code]state_process(delta: float)[/code], [code]state_physics_process(delta: float)[/code] and
## [code]state_input(event: InputEvent)[/code]. A state defines only the methods it needs, so any Node works.
## Transitions can be limited by a table. A transition requested while another one runs (from state_enter,
## state_exit or a state_changed handler) is queued and applied right after it, in request order. A bounded
## history lets go_back() return to earlier states.

## Emitted after a transition completes.
signal state_changed(previous: StringName, current: StringName)
## Emitted when a request is refused; [param reason] is "not started", "unknown state", "not allowed" or
## "cannot go back".
signal transition_refused(from_state: StringName, to_state: StringName, reason: String)

## Name of the child that becomes active on start. Empty means the first child.
@export var initial_state: StringName = &""
## Start automatically when the node is ready.
@export var auto_start: bool = true
## Allowed transitions as {from_name: [to_name, ...]}. An empty table allows every transition.
@export var allowed_transitions: Dictionary = {}
## How many previous states go_back() can return through.
@export_range(0, 64) var history_size: int = 8

## Seconds spent in the current state, advanced every process frame.
var time_in_state: float = 0.0

var _current: StringName = &""
var _active: Node = null
var _history: Array[StringName] = []
var _busy: bool = false
var _queue: Array[Dictionary] = []


func _ready() -> void:
	if auto_start:
		start()


func _process(delta: float) -> void:
	if _current == &"":
		return
	time_in_state += delta
	if _active_has("state_process"):
		_active.call("state_process", delta)


func _physics_process(delta: float) -> void:
	if _active_has("state_physics_process"):
		_active.call("state_physics_process", delta)


func _unhandled_input(event: InputEvent) -> void:
	if _active_has("state_input"):
		_active.call("state_input", event)


## Enters [member initial_state], or the first child when it is empty. Returns false when there is no such
## state. Calling it again while running does nothing and returns true.
func start(data: Dictionary = {}) -> bool:
	if _current != &"":
		return true
	var first: StringName = initial_state
	if first == &"" and get_child_count() > 0:
		first = get_child(0).name
	if not has_state(first):
		transition_refused.emit(&"", first, "unknown state")
		return false
	_switch(first, data, false)
	return true


## Exits the active state and returns to the stopped condition. The history is kept.
func stop() -> void:
	if _current == &"":
		return
	if _active_has("state_exit"):
		_active.call("state_exit", &"")
	_current = &""
	_active = null
	_queue.clear()


## Requests a transition to [param state_name] with optional [param data] for state_enter. Returns false when it
## is refused. A request made during another transition is queued, returns true and is checked when applied.
func transition_to(state_name: StringName, data: Dictionary = {}) -> bool:
	if _current == &"":
		transition_refused.emit(_current, state_name, "not started")
		return false
	if not has_state(state_name):
		transition_refused.emit(_current, state_name, "unknown state")
		return false
	if _busy:
		_queue.append({"state": state_name, "data": data})
		return true
	if not can_transition(_current, state_name):
		transition_refused.emit(_current, state_name, "not allowed")
		return false
	_switch(state_name, data, true)
	return true


## Returns to the most recent state in the history. Returns false when the history is empty or the move is not
## allowed.
func go_back(data: Dictionary = {}) -> bool:
	if _history.is_empty() or _busy or _current == &"":
		return false
	var target: StringName = _history.back()
	if not has_state(target) or not can_transition(_current, target):
		transition_refused.emit(_current, target, "cannot go back")
		return false
	_history.pop_back()
	_switch(target, data, false)
	return true


## True when a child node named [param state_name] exists.
func has_state(state_name: StringName) -> bool:
	return get_state_node(state_name) != null


## The child node for [param state_name], or null.
func get_state_node(state_name: StringName) -> Node:
	if state_name == &"":
		return null
	for child: Node in get_children():
		if child.name == state_name:
			return child
	return null


## The active state's name, or an empty StringName while stopped.
func get_current_state() -> StringName:
	return _current


## The state names in child order.
func get_state_names() -> PackedStringArray:
	var names := PackedStringArray()
	for child: Node in get_children():
		names.append(String(child.name))
	return names


## Previous states, oldest first.
func get_history() -> Array[StringName]:
	return _history.duplicate()


## True when the transition table allows [param from_state] to [param to_state] (always with an empty table).
func can_transition(from_state: StringName, to_state: StringName) -> bool:
	if allowed_transitions.is_empty():
		return true
	var targets: Variant = allowed_transitions.get(from_state, allowed_transitions.get(String(from_state), []))
	if typeof(targets) != TYPE_ARRAY and typeof(targets) != TYPE_PACKED_STRING_ARRAY:
		return false
	for target: Variant in targets:
		if String(target) == String(to_state):
			return true
	return false


func _active_has(method: StringName) -> bool:
	return _active != null and is_instance_valid(_active) and _active.has_method(method)


func _switch(state_name: StringName, data: Dictionary, record: bool) -> void:
	_busy = true
	var previous: StringName = _current
	if previous != &"" and _active_has("state_exit"):
		_active.call("state_exit", state_name)
	if record and previous != &"":
		_history.append(previous)
		while _history.size() > history_size:
			_history.remove_at(0)
	_current = state_name
	_active = get_state_node(state_name)
	time_in_state = 0.0
	if _active_has("state_enter"):
		_active.call("state_enter", previous, data)
	state_changed.emit(previous, state_name)
	_busy = false
	_drain()


func _drain() -> void:
	while not _queue.is_empty() and not _busy:
		var request: Dictionary = _queue.pop_front()
		var target: StringName = request["state"]
		if not has_state(target):
			transition_refused.emit(_current, target, "unknown state")
		elif not can_transition(_current, target):
			transition_refused.emit(_current, target, "not allowed")
		else:
			_switch(target, request["data"], true)
