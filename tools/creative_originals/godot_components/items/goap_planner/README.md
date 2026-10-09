# GOAP planner with A* over world states

Plan the cheapest sequence of actions from preconditions, effects and costs to reach a goal world state, with optional procedural checks and a bound on expanded states.

## How it works

Goal-oriented action planning: finds the cheapest sequence of actions that turns a world state into one that
satisfies a goal, with A* search over world states.

A world state is a Dictionary of facts (key to value). An action has a name, a cost, preconditions (facts that
must hold before it) and effects (facts it sets), plus an optional check Callable that receives the state and
can refuse the action for reasons the facts do not capture. plan() searches forward from the given state: each
search node is a world state, each edge an applicable action, and the heuristic counts goal facts that do not
hold yet. With every action costing at least 1 and setting at most one goal fact the heuristic never
overestimates and the plan is the cheapest; otherwise the plan is valid but may cost more than the best one.
The search stops after max_nodes expanded states.

## When to use it

Use it for agents that should find their own way to a goal from a list of abilities, such as a villager who must fetch an axe before chopping wood, without scripting every sequence.

## Installation

Copy this folder to `res://baltor/godot_components/goap_planner/` in a Godot 4.3 or later project. The script `goap_planner.gd` declares the global class `BaltorGoapPlanner`, which extends `RefCounted`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Methods

- `add_action(action_name: StringName, preconditions: Dictionary, effects: Dictionary, cost: float = 1.0, check: Callable = Callable()) -> bool`: Adds or replaces an action. Refuses an empty name, empty effects or a cost below zero.
- `remove_action(action_name: StringName) -> bool`: Removes an action. Returns false when it does not exist.
- `has_action(action_name: StringName) -> bool`: True when an action with that name exists.
- `static satisfies(state: Dictionary, conditions: Dictionary) -> bool`: True when every fact of `conditions` holds in `state`.
- `apply(state: Dictionary, action_name: StringName) -> Dictionary`: The state after applying the effects of `action_name` to `state` (preconditions not checked).
- `is_applicable(state: Dictionary, action_name: StringName) -> bool`: True when `action_name` can run in `state`: its preconditions hold and its check accepts.
- `plan(state: Dictionary, goal: Dictionary, max_nodes: int = 2048) -> Array[StringName]`: The cheapest action names found from `state` to a state satisfying `goal`. Empty when the goal already holds or no plan was found; is_last_plan_found() tells the two apart.
- `get_last_cost() -> float`: Total cost of the last plan found.
- `is_last_plan_found() -> bool`: True when the last plan() call reached the goal (an empty plan means the goal already held).
- `get_last_expanded() -> int`: Number of states the last plan() call expanded.

## Usage

```gdscript
extends Node

var planner: BaltorGoapPlanner = BaltorGoapPlanner.new()


func _ready() -> void:
	planner.add_action(&"get_axe", {"has_axe": false}, {"has_axe": true})
	planner.add_action(&"chop_wood", {"has_axe": true}, {"has_wood": true}, 2.0)
	planner.add_action(&"make_fire", {"has_wood": true}, {"warm": true})
	var steps: Array[StringName] = planner.plan({"has_axe": false}, {"warm": true})
	print(steps, " cost ", planner.get_last_cost())
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/goap_planner/run_tests.gd -- res://baltor/godot_components/goap_planner/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Forward search over Dictionary world states; facts are compared with ==. The heuristic counts unmet goal facts, so the plan is the cheapest only when every action costs at least 1 and sets at most one goal fact. Large action sets need the max_nodes bound. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
