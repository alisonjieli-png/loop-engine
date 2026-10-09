class_name BaltorGoapPlanner
extends RefCounted
## Goal-oriented action planning: finds the cheapest sequence of actions that turns a world state into one that
## satisfies a goal, with A* search over world states.
##
## A world state is a Dictionary of facts (key to value). An action has a name, a cost, preconditions (facts that
## must hold before it) and effects (facts it sets), plus an optional check Callable that receives the state and
## can refuse the action for reasons the facts do not capture. plan() searches forward from the given state: each
## search node is a world state, each edge an applicable action, and the heuristic counts goal facts that do not
## hold yet. With every action costing at least 1 and setting at most one goal fact the heuristic never
## overestimates and the plan is the cheapest; otherwise the plan is valid but may cost more than the best one.
## The search stops after max_nodes expanded states.

var _actions: Dictionary = {}
var _order: Array[StringName] = []
var _last_cost: float = 0.0
var _last_found: bool = false
var _last_expanded: int = 0


## Adds or replaces an action. Refuses an empty name, empty effects or a cost below zero.
func add_action(action_name: StringName, preconditions: Dictionary, effects: Dictionary, cost: float = 1.0,
		check: Callable = Callable()) -> bool:
	if action_name == &"" or effects.is_empty() or cost < 0.0:
		return false
	if not _actions.has(action_name):
		_order.append(action_name)
	_actions[action_name] = {"pre": preconditions.duplicate(), "post": effects.duplicate(), "cost": cost,
			"check": check}
	return true


## Removes an action. Returns false when it does not exist.
func remove_action(action_name: StringName) -> bool:
	if not _actions.erase(action_name):
		return false
	_order.erase(action_name)
	return true


## True when an action with that name exists.
func has_action(action_name: StringName) -> bool:
	return _actions.has(action_name)


## True when every fact of [param conditions] holds in [param state].
static func satisfies(state: Dictionary, conditions: Dictionary) -> bool:
	for key: Variant in conditions:
		if not state.has(key) or state[key] != conditions[key]:
			return false
	return true


## The state after applying the effects of [param action_name] to [param state] (preconditions not checked).
func apply(state: Dictionary, action_name: StringName) -> Dictionary:
	var next: Dictionary = state.duplicate()
	if _actions.has(action_name):
		next.merge(_actions[action_name]["post"], true)
	return next


## True when [param action_name] can run in [param state]: its preconditions hold and its check accepts.
func is_applicable(state: Dictionary, action_name: StringName) -> bool:
	if not _actions.has(action_name):
		return false
	var action: Dictionary = _actions[action_name]
	if not satisfies(state, action["pre"]):
		return false
	var check: Callable = action["check"]
	return not check.is_valid() or bool(check.call(state))


## The cheapest action names found from [param state] to a state satisfying [param goal]. Empty when the goal
## already holds or no plan was found; is_last_plan_found() tells the two apart.
func plan(state: Dictionary, goal: Dictionary, max_nodes: int = 2048) -> Array[StringName]:
	var empty: Array[StringName] = []
	_last_cost = 0.0
	_last_expanded = 0
	_last_found = satisfies(state, goal)
	if _last_found:
		return empty
	var start_key: String = _key(state)
	var nodes: Dictionary = {start_key: {"state": state.duplicate(), "cost": 0.0, "parent": "", "action": &""}}
	var open: Array = [[_missing(state, goal), 0, start_key]]
	var closed: Dictionary = {}
	var order: int = 0
	while not open.is_empty() and _last_expanded < max_nodes:
		var best: int = 0
		for index in range(1, open.size()):
			if _before(open[index], open[best]):
				best = index
		var entry: Array = open[best]
		open.remove_at(best)
		var key: String = entry[2]
		if closed.has(key):
			continue
		closed[key] = true
		var node: Dictionary = nodes[key]
		if satisfies(node["state"], goal):
			_last_found = true
			_last_cost = node["cost"]
			return _unwind(nodes, key)
		_last_expanded += 1
		for action_name: StringName in _order:
			if not is_applicable(node["state"], action_name):
				continue
			var next_state: Dictionary = apply(node["state"], action_name)
			var next_key: String = _key(next_state)
			var next_cost: float = float(node["cost"]) + float(_actions[action_name]["cost"])
			if closed.has(next_key) or (nodes.has(next_key) and float(nodes[next_key]["cost"]) <= next_cost):
				continue
			nodes[next_key] = {"state": next_state, "cost": next_cost, "parent": key, "action": action_name}
			order += 1
			open.append([next_cost + _missing(next_state, goal), order, next_key])
	return empty


## Total cost of the last plan found.
func get_last_cost() -> float:
	return _last_cost


## True when the last plan() call reached the goal (an empty plan means the goal already held).
func is_last_plan_found() -> bool:
	return _last_found


## Number of states the last plan() call expanded.
func get_last_expanded() -> int:
	return _last_expanded


func _missing(state: Dictionary, goal: Dictionary) -> int:
	var count: int = 0
	for key: Variant in goal:
		if not state.has(key) or state[key] != goal[key]:
			count += 1
	return count


func _key(state: Dictionary) -> String:
	var keys: Array = state.keys()
	keys.sort_custom(func(a: Variant, b: Variant) -> bool: return str(a) < str(b))
	var parts: PackedStringArray = PackedStringArray()
	for key: Variant in keys:
		parts.append("%s=%s" % [var_to_str(key), var_to_str(state[key])])
	return ";".join(parts)


func _before(a: Array, b: Array) -> bool:
	return float(a[0]) < float(b[0]) or (is_equal_approx(float(a[0]), float(b[0])) and int(a[1]) < int(b[1]))


func _unwind(nodes: Dictionary, key: String) -> Array[StringName]:
	var steps: Array[StringName] = []
	var current: String = key
	while String(nodes[current]["parent"]) != "":
		steps.push_front(nodes[current]["action"])
		current = nodes[current]["parent"]
	return steps
