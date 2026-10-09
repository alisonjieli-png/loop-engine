class_name BaltorTransitionTable
extends RefCounted
## A data-driven state machine: states and event transitions come from a Dictionary, such as parsed JSON, and
## guards and actions are named Callables registered in code.
##
## A table has "initial", "states" (names) and "transitions": a list of {"from", "event", "to"} with optional
## "guard" (a registered guard name) and "actions" (registered action names, run in order with the payload).
## "from" may be "*" to match any state. fire() checks the transitions from the exact current state first, then
## the wildcard ones, each group in table order, and takes the first whose guard accepts the payload. Designers can
## edit door, quest or menu flows in a JSON file while programmers own the guard and action code. load_table()
## validates the whole table first and changes nothing when it is malformed; get_errors() says why.

## Emitted after a transition and its actions.
signal transitioned(from_state: StringName, to_state: StringName, event: StringName)
## Emitted when fire() finds no transition for the event in the current state.
signal event_ignored(state: StringName, event: StringName)

var _guards: Dictionary = {}
var _actions: Dictionary = {}
var _states: Array[StringName] = []
var _initial: StringName = &""
var _rows: Array[Dictionary] = []
var _state: StringName = &""
var _errors: PackedStringArray = PackedStringArray()


## Registers a guard: [param guard] is called with the payload Dictionary and returns bool.
func register_guard(guard_name: StringName, guard: Callable) -> void:
	_guards[guard_name] = guard


## Registers an action: [param action] is called with the payload Dictionary.
func register_action(action_name: StringName, action: Callable) -> void:
	_actions[action_name] = action


## Loads and validates [param table]; on success the machine is in the initial state. Returns false, changing
## nothing, when the table is malformed.
func load_table(table: Dictionary) -> bool:
	var errors := PackedStringArray()
	var states: Array[StringName] = []
	for value: Variant in table.get("states", []):
		if typeof(value) != TYPE_STRING and typeof(value) != TYPE_STRING_NAME:
			errors.append("a state name is not text")
		elif states.has(StringName(value)):
			errors.append("state %s is listed twice" % value)
		else:
			states.append(StringName(value))
	if states.is_empty():
		errors.append("no states")
	var initial := StringName(str(table.get("initial", "")))
	if not states.has(initial):
		errors.append("initial state %s is not listed" % initial)
	var rows: Array[Dictionary] = []
	var transitions: Variant = table.get("transitions", [])
	if typeof(transitions) != TYPE_ARRAY:
		errors.append("transitions is not a list")
		transitions = []
	for index in range((transitions as Array).size()):
		var raw: Variant = transitions[index]
		if typeof(raw) != TYPE_DICTIONARY:
			errors.append("transition %d is not an object" % index)
			continue
		var row := _row(raw as Dictionary, states, index, errors)
		if not row.is_empty():
			rows.append(row)
	_errors = errors
	if not errors.is_empty():
		return false
	_states = states
	_initial = initial
	_rows = rows
	_state = initial
	return true


## Why the last load_table() call failed (empty after a success).
func get_errors() -> PackedStringArray:
	return _errors


## Offers [param event] with [param payload]; returns true when a transition was taken.
func fire(event: StringName, payload: Dictionary = {}) -> bool:
	if _state == &"":
		return false
	for wildcard: bool in [false, true]:
		for row: Dictionary in _rows:
			if row["event"] != event or (row["from"] == &"*") != wildcard:
				continue
			if not wildcard and row["from"] != _state:
				continue
			if row["guard"] != &"" and not bool((_guards[row["guard"]] as Callable).call(payload)):
				continue
			var previous: StringName = _state
			_state = row["to"]
			for action_name: StringName in row["actions"]:
				(_actions[action_name] as Callable).call(payload)
			transitioned.emit(previous, _state, event)
			return true
	event_ignored.emit(_state, event)
	return false


## The current state, or an empty StringName before a table is loaded.
func get_state() -> StringName:
	return _state


## Returns to the initial state without running actions.
func reset() -> void:
	_state = _initial


## Events that have a transition from the current state (guards not evaluated), without repeats.
func available_events() -> PackedStringArray:
	var events := PackedStringArray()
	for row: Dictionary in _rows:
		if (row["from"] == _state or row["from"] == &"*") and not events.has(String(row["event"])):
			events.append(String(row["event"]))
	return events


func _row(raw: Dictionary, states: Array[StringName], index: int, errors: PackedStringArray) -> Dictionary:
	var from_state := StringName(str(raw.get("from", "")))
	var to_state := StringName(str(raw.get("to", "")))
	var event := StringName(str(raw.get("event", "")))
	var guard := StringName(str(raw.get("guard", "")))
	var before: int = errors.size()
	if from_state != &"*" and not states.has(from_state):
		errors.append("transition %d comes from unknown state %s" % [index, from_state])
	if not states.has(to_state):
		errors.append("transition %d goes to unknown state %s" % [index, to_state])
	if event == &"":
		errors.append("transition %d has no event" % index)
	if guard != &"" and not _guards.has(guard):
		errors.append("transition %d uses unregistered guard %s" % [index, guard])
	var actions: Array[StringName] = []
	var listed: Variant = raw.get("actions", [])
	if typeof(listed) != TYPE_ARRAY:
		errors.append("transition %d actions is not a list" % index)
		listed = []
	for value: Variant in listed:
		if not _actions.has(StringName(str(value))):
			errors.append("transition %d uses unregistered action %s" % [index, value])
		actions.append(StringName(str(value)))
	if errors.size() > before:
		return {}
	return {"from": from_state, "to": to_state, "event": event, "guard": guard, "actions": actions}
