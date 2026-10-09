class_name BaltorHierarchicalStateMachine
extends RefCounted
## A hierarchical state machine built in code: nested states, events that bubble up the hierarchy, guards,
## entry and exit in hierarchy order, and optional shallow history.
##
## Every state has a name and an optional parent. A state with children is composite: entering it also enters
## its initial child (the first child added unless set_initial() picked another), down to a leaf. While running,
## the machine is in exactly one leaf and in all of that leaf's ancestors. send() offers an event to the leaf
## first and then to each ancestor; the first transition for the event whose guard accepts the data is taken.
## Taking it exits states from the leaf up to, but not including, the lowest common ancestor of the leaf and the
## target, then enters states from below that ancestor down to the target and on to a leaf. A transition whose
## target is the leaf or one of its ancestors exits and re-enters that target. A composite with history enabled
## re-enters the child that was active when it was last exited. Callbacks are Callables: enter and exit take no
## arguments, update takes the delta, and a guard takes the event data Dictionary and returns bool.

## Emitted after a state is entered.
signal state_entered(state_name: StringName)
## Emitted after a state is exited.
signal state_exited(state_name: StringName)
## Emitted after a transition, with the leaf before and after and the event (empty for start).
signal transitioned(from_leaf: StringName, to_leaf: StringName, event: StringName)

var _parent: Dictionary = {}
var _children: Dictionary = {&"": []}
var _initial: Dictionary = {}
var _history: Dictionary = {}
var _last_child: Dictionary = {}
var _callbacks: Dictionary = {}
var _transitions: Dictionary = {}
var _path: Array[StringName] = []


## Adds a state under [param parent_name] (empty for the top level) with optional callbacks. Refuses an empty
## or repeated name and an unknown parent.
func add_state(state_name: StringName, parent_name: StringName = &"", on_enter: Callable = Callable(),
		on_exit: Callable = Callable(), on_update: Callable = Callable()) -> bool:
	if state_name == &"" or _parent.has(state_name):
		return false
	if parent_name != &"" and not _parent.has(parent_name):
		return false
	_parent[state_name] = parent_name
	_children[state_name] = []
	(_children[parent_name] as Array).append(state_name)
	if not _initial.has(parent_name):
		_initial[parent_name] = state_name
	_callbacks[state_name] = {"enter": on_enter, "exit": on_exit, "update": on_update}
	_transitions[state_name] = []
	return true


## Makes [param child_name] the initial child of [param parent_name] (empty for the top level).
func set_initial(parent_name: StringName, child_name: StringName) -> bool:
	if not _children.has(parent_name) or not (_children[parent_name] as Array).has(child_name):
		return false
	_initial[parent_name] = child_name
	return true


## Turns shallow history on or off for the composite [param state_name].
func set_history(state_name: StringName, enabled: bool) -> bool:
	if not _parent.has(state_name):
		return false
	_history[state_name] = enabled
	return true


## Adds a transition from [param from_state] on [param event] to [param to_state], taken only when the optional
## [param guard] returns true for the event data. Refuses unknown states or an empty event.
func add_transition(from_state: StringName, event: StringName, to_state: StringName,
		guard: Callable = Callable()) -> bool:
	if event == &"" or not _parent.has(from_state) or not _parent.has(to_state):
		return false
	(_transitions[from_state] as Array).append({"event": event, "target": to_state, "guard": guard})
	return true


## Enters the initial top-level state and its initial descendants. Returns false when already running or empty.
func start() -> bool:
	if not _path.is_empty() or not _initial.has(&""):
		return false
	_enter_chain([_initial[&""]])
	transitioned.emit(&"", get_leaf(), &"")
	return true


## Exits every active state, leaf first.
func stop() -> void:
	_exit_to(0)


## Offers [param event] to the leaf and then its ancestors; returns true when a transition was taken.
func send(event: StringName, data: Dictionary = {}) -> bool:
	for index in range(_path.size() - 1, -1, -1):
		for transition: Dictionary in _transitions[_path[index]]:
			if transition["event"] != event:
				continue
			var guard: Callable = transition["guard"]
			if guard.is_valid() and not bool(guard.call(data)):
				continue
			_take(transition["target"], event)
			return true
	return false


## Calls the update callbacks of the active states, outermost first.
func update(delta: float) -> void:
	for state_name: StringName in _path.duplicate():
		var callback: Callable = _callbacks[state_name]["update"]
		if callback.is_valid():
			callback.call(delta)


## The active leaf, or an empty StringName when stopped.
func get_leaf() -> StringName:
	return _path.back() if not _path.is_empty() else &""


## The active states from the top level down to the leaf.
func get_active_path() -> Array[StringName]:
	return _path.duplicate()


## True when [param state_name] is the leaf or one of its ancestors.
func is_in(state_name: StringName) -> bool:
	return _path.has(state_name)


## True when [param state_name] was added.
func has_state(state_name: StringName) -> bool:
	return _parent.has(state_name)


## True between start() and stop().
func is_running() -> bool:
	return not _path.is_empty()


func _ancestry(state_name: StringName) -> Array[StringName]:
	var chain: Array[StringName] = []
	var current: StringName = state_name
	while current != &"":
		chain.push_front(current)
		current = _parent[current]
	return chain


func _take(target: StringName, event: StringName) -> void:
	var from_leaf: StringName = get_leaf()
	var chain: Array[StringName] = _ancestry(target)
	var common: int = 0
	if _path.has(target):
		common = _path.find(target)
	else:
		while common < mini(_path.size(), chain.size()) and _path[common] == chain[common]:
			common += 1
	_exit_to(common)
	_enter_chain(chain.slice(common))
	transitioned.emit(from_leaf, get_leaf(), event)


func _exit_to(depth: int) -> void:
	while _path.size() > depth:
		var leaving: StringName = _path.pop_back()
		var parent_name: StringName = _parent[leaving]
		_last_child[parent_name] = leaving
		var callback: Callable = _callbacks[leaving]["exit"]
		if callback.is_valid():
			callback.call()
		state_exited.emit(leaving)


func _enter_chain(chain: Array[StringName]) -> void:
	var queue: Array[StringName] = chain.duplicate()
	while not queue.is_empty():
		var entering: StringName = queue.pop_front()
		_path.append(entering)
		var callback: Callable = _callbacks[entering]["enter"]
		if callback.is_valid():
			callback.call()
		state_entered.emit(entering)
		if queue.is_empty() and not (_children[entering] as Array).is_empty():
			var next: StringName = _initial[entering]
			if bool(_history.get(entering, false)) and _last_child.has(entering):
				next = _last_child[entering]
			queue.append(next)
