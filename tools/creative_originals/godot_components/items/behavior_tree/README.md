# Behavior tree with blackboard and decorators

Build behavior trees in code from sequences, selectors, a parallel, decorators (inverter, succeeder, repeater, cooldown), conditions, actions and waits, ticked with a shared blackboard and its own clock.

## How it works

A behavior tree built from code: sequences, selectors, a parallel, decorators, conditions, actions, waits and a
shared blackboard Dictionary.

Every task returns SUCCESS, FAILURE or RUNNING when ticked. A sequence runs its children in order until one
fails; a selector until one succeeds. By default both remember the running child and resume there on the next
tick. A reactive composite starts from its first child on every tick, so a condition placed first can cancel a
running action; the cancelled task is reset and an action's halt callable runs. A parallel ticks all unfinished
children and succeeds once success_threshold of them succeeded, or fails when that is no longer possible.
Decorators: inverter, succeeder, repeater (counts child successes, one child run per tick) and cooldown (blocks
its child for a time after the child finishes). Leaves: condition(check) where check(blackboard) returns bool,
action(work, halt) where work(blackboard, delta) returns a Status, and wait(seconds), which counts the deltas
it is ticked with. The tree keeps its own clock from the deltas passed to tick(), so cooldowns follow game time.

## When to use it

Use it for NPCs whose priorities change during play: patrol until an enemy is seen, chase while it stays visible, attack with a cooldown, and fall back when health is low.

## Installation

Copy this folder to `res://baltor/godot_components/behavior_tree/` in a Godot 4.3 or later project. The script `behavior_tree.gd` declares the global class `BaltorBehaviorTree`, which extends `RefCounted`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `ticked(status: int)`: Emitted after every tick with the root's status.

### Properties

- `blackboard: Dictionary`: Data shared by every task of the tree.
- `root: Task`: The root task.

### Methods

- `tick(delta: float) -> int`: Ticks the tree once, advancing its clock by `delta` seconds, and returns the root's status. An empty tree fails.
- `reset() -> void`: Resets every task: running children are dropped, counters and timers restart, running actions halt.
- `get_time() -> float`: Seconds of game time ticked so far.
- `describe() -> String`: A text outline of the tree with each task's label and last status, for debugging.
- `static sequence(tasks: Array, reactive: bool = false, label: String = "sequence") -> Task`: A sequence: runs children in order until one fails or is running.
- `static selector(tasks: Array, reactive: bool = false, label: String = "selector") -> Task`: A selector: runs children in order until one succeeds or is running.
- `static parallel(tasks: Array, success_threshold: int, label: String = "parallel") -> Task`: A parallel: ticks all unfinished children; succeeds when `success_threshold` of them succeeded.
- `static inverter(child: Task, label: String = "inverter") -> Task`: Swaps SUCCESS and FAILURE of `child`.
- `static succeeder(child: Task, label: String = "succeeder") -> Task`: Turns FAILURE of `child` into SUCCESS.
- `static repeater(child: Task, times: int, label: String = "repeater") -> Task`: Succeeds after `child` succeeded `times` times (one child run per tick); fails when it fails.
- `static cooldown(child: Task, seconds: float, label: String = "cooldown") -> Task`: Fails without ticking `child` for `seconds` after the child finished.
- `static condition(check: Callable, label: String = "condition") -> Task`: A leaf that succeeds when `check` (called with the blackboard) returns true.
- `static action(work: Callable, halt: Callable = Callable(), label: String = "action") -> Task`: A leaf that returns what `work` (called with the blackboard and delta) returns; anything other than a Status is FAILURE. `halt` (called with the blackboard) runs when a running action is cancelled.
- `static wait(seconds: float, label: String = "wait") -> Task`: A leaf that is RUNNING until the deltas it was ticked with add up to `seconds`, then succeeds.

### Enums

- `Status`: SUCCESS, FAILURE, RUNNING: The result of ticking a task.

## Usage

```gdscript
extends Node2D

var brain: BaltorBehaviorTree


func _ready() -> void:
	var seen := BaltorBehaviorTree.condition(func(board: Dictionary) -> bool: return board.get("enemy", false))
	var chase := BaltorBehaviorTree.action(_chase)
	var patrol := BaltorBehaviorTree.action(_patrol)
	brain = BaltorBehaviorTree.new(BaltorBehaviorTree.selector([
		BaltorBehaviorTree.sequence([seen, chase], true),
		patrol,
	]))


func _process(delta: float) -> void:
	brain.tick(delta)


func _chase(_board: Dictionary, _delta: float) -> int:
	return BaltorBehaviorTree.Status.RUNNING


func _patrol(_board: Dictionary, _delta: float) -> int:
	return BaltorBehaviorTree.Status.SUCCESS
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/behavior_tree/run_tests.gd -- res://baltor/godot_components/behavior_tree/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Trees are built in code, not in the editor; there is no visual editor or debugger beyond describe(). One child run per tick for the repeater. Reactive composites halt only the child that was running. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
