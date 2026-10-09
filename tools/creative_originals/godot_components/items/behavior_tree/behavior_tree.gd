class_name BaltorBehaviorTree
extends RefCounted
## A behavior tree built from code: sequences, selectors, a parallel, decorators, conditions, actions, waits and a
## shared blackboard Dictionary.
##
## Every task returns SUCCESS, FAILURE or RUNNING when ticked. A sequence runs its children in order until one
## fails; a selector until one succeeds. By default both remember the running child and resume there on the next
## tick. A reactive composite starts from its first child on every tick, so a condition placed first can cancel a
## running action; the cancelled task is reset and an action's halt callable runs. A parallel ticks all unfinished
## children and succeeds once success_threshold of them succeeded, or fails when that is no longer possible.
## Decorators: inverter, succeeder, repeater (counts child successes, one child run per tick) and cooldown (blocks
## its child for a time after the child finishes). Leaves: condition(check) where check(blackboard) returns bool,
## action(work, halt) where work(blackboard, delta) returns a Status, and wait(seconds), which counts the deltas
## it is ticked with. The tree keeps its own clock from the deltas passed to tick(), so cooldowns follow game time.

## The result of ticking a task.
enum Status { SUCCESS, FAILURE, RUNNING }

## Emitted after every tick with the root's status.
signal ticked(status: int)

## Data shared by every task of the tree.
var blackboard: Dictionary = {}
## The root task.
var root: Task = null

var _time: float = 0.0


## Base of every task. Subclasses override _run(); tick() records last_status for describe().
class Task extends RefCounted:
	var label: String = ""
	var children: Array = []
	var last_status: int = -1

	func tick(board: Dictionary, delta: float, time: float) -> int:
		var status: int = _run(board, delta, time)
		if status != Status.SUCCESS and status != Status.FAILURE and status != Status.RUNNING:
			status = Status.FAILURE
		last_status = status
		return status

	func reset(board: Dictionary) -> void:
		last_status = -1
		for child: Task in children:
			child.reset(board)

	func _run(_board: Dictionary, _delta: float, _time: float) -> int:
		return Status.FAILURE


class Composite extends Task:
	var reactive: bool = false
	var stop_on: int = Status.FAILURE
	var _index: int = 0

	func _run(board: Dictionary, delta: float, time: float) -> int:
		var start: int = 0 if reactive else _index
		for index in range(start, children.size()):
			var status: int = (children[index] as Task).tick(board, delta, time)
			if status == Status.RUNNING:
				if reactive and index < _index:
					(children[_index] as Task).reset(board)
				_index = index
				return Status.RUNNING
			if status == stop_on:
				if reactive and index < _index:
					(children[_index] as Task).reset(board)
				_index = 0
				return stop_on
		_index = 0
		return Status.SUCCESS if stop_on == Status.FAILURE else Status.FAILURE

	func reset(board: Dictionary) -> void:
		super.reset(board)
		_index = 0


class Parallel extends Task:
	var success_threshold: int = 1
	var _done: Dictionary = {}

	func _run(board: Dictionary, delta: float, time: float) -> int:
		var successes: int = 0
		var failures: int = 0
		for index in range(children.size()):
			if not _done.has(index):
				var status: int = (children[index] as Task).tick(board, delta, time)
				if status != Status.RUNNING:
					_done[index] = status
			if _done.has(index):
				successes += 1 if _done[index] == Status.SUCCESS else 0
				failures += 1 if _done[index] == Status.FAILURE else 0
		var needed: int = clampi(success_threshold, 1, maxi(children.size(), 1))
		if successes >= needed or failures > children.size() - needed:
			for index in range(children.size()):
				if not _done.has(index):
					(children[index] as Task).reset(board)
			_done.clear()
			return Status.SUCCESS if successes >= needed else Status.FAILURE
		return Status.RUNNING

	func reset(board: Dictionary) -> void:
		super.reset(board)
		_done.clear()


class Decorator extends Task:
	var kind: String = "inverter"
	var amount: float = 0.0
	var _count: int = 0
	var _ready_at: float = -1.0

	func _run(board: Dictionary, delta: float, time: float) -> int:
		var child: Task = children[0]
		if kind == "cooldown" and time < _ready_at:
			return Status.FAILURE
		var status: int = child.tick(board, delta, time)
		match kind:
			"inverter":
				if status == Status.SUCCESS:
					return Status.FAILURE
				if status == Status.FAILURE:
					return Status.SUCCESS
			"succeeder":
				if status == Status.FAILURE:
					return Status.SUCCESS
			"repeater":
				if status == Status.SUCCESS:
					_count += 1
					if _count >= int(amount):
						_count = 0
						return Status.SUCCESS
					return Status.RUNNING
				if status == Status.FAILURE:
					_count = 0
			"cooldown":
				if status != Status.RUNNING:
					_ready_at = time + amount
		return status

	func reset(board: Dictionary) -> void:
		super.reset(board)
		_count = 0


class Leaf extends Task:
	var kind: String = "action"
	var work: Callable = Callable()
	var halt: Callable = Callable()
	var seconds: float = 0.0
	var _elapsed: float = 0.0

	func _run(board: Dictionary, delta: float, _time: float) -> int:
		match kind:
			"condition":
				return Status.SUCCESS if work.is_valid() and bool(work.call(board)) else Status.FAILURE
			"wait":
				_elapsed += delta
				if _elapsed + 0.000001 >= seconds:
					_elapsed = 0.0
					return Status.SUCCESS
				return Status.RUNNING
		if not work.is_valid():
			return Status.FAILURE
		var result: Variant = work.call(board, delta)
		if typeof(result) != TYPE_INT:
			return Status.FAILURE
		return int(result)

	func reset(board: Dictionary) -> void:
		if last_status == Status.RUNNING and halt.is_valid():
			halt.call(board)
		super.reset(board)
		_elapsed = 0.0


func _init(root_task: Task = null) -> void:
	root = root_task


## Ticks the tree once, advancing its clock by [param delta] seconds, and returns the root's status.
## An empty tree fails.
func tick(delta: float) -> int:
	_time += maxf(delta, 0.0)
	var status: int = Status.FAILURE
	if root != null:
		status = root.tick(blackboard, delta, _time)
	ticked.emit(status)
	return status


## Resets every task: running children are dropped, counters and timers restart, running actions halt.
func reset() -> void:
	if root != null:
		root.reset(blackboard)


## Seconds of game time ticked so far.
func get_time() -> float:
	return _time


## A text outline of the tree with each task's label and last status, for debugging.
func describe() -> String:
	var lines: PackedStringArray = PackedStringArray()
	if root != null:
		_describe(root, 0, lines)
	return "\n".join(lines)


## A sequence: runs children in order until one fails or is running.
static func sequence(tasks: Array, reactive: bool = false, label: String = "sequence") -> Task:
	var task := Composite.new()
	task.reactive = reactive
	task.stop_on = Status.FAILURE
	return _named(task, tasks, label)


## A selector: runs children in order until one succeeds or is running.
static func selector(tasks: Array, reactive: bool = false, label: String = "selector") -> Task:
	var task := Composite.new()
	task.reactive = reactive
	task.stop_on = Status.SUCCESS
	return _named(task, tasks, label)


## A parallel: ticks all unfinished children; succeeds when [param success_threshold] of them succeeded.
static func parallel(tasks: Array, success_threshold: int, label: String = "parallel") -> Task:
	var task := Parallel.new()
	task.success_threshold = success_threshold
	return _named(task, tasks, label)


## Swaps SUCCESS and FAILURE of [param child].
static func inverter(child: Task, label: String = "inverter") -> Task:
	return _decorator("inverter", child, 0.0, label)


## Turns FAILURE of [param child] into SUCCESS.
static func succeeder(child: Task, label: String = "succeeder") -> Task:
	return _decorator("succeeder", child, 0.0, label)


## Succeeds after [param child] succeeded [param times] times (one child run per tick); fails when it fails.
static func repeater(child: Task, times: int, label: String = "repeater") -> Task:
	return _decorator("repeater", child, float(maxi(times, 1)), label)


## Fails without ticking [param child] for [param seconds] after the child finished.
static func cooldown(child: Task, seconds: float, label: String = "cooldown") -> Task:
	return _decorator("cooldown", child, seconds, label)


## A leaf that succeeds when [param check] (called with the blackboard) returns true.
static func condition(check: Callable, label: String = "condition") -> Task:
	var task := Leaf.new()
	task.kind = "condition"
	task.work = check
	task.label = label
	return task


## A leaf that returns what [param work] (called with the blackboard and delta) returns; anything other than a
## Status is FAILURE. [param halt] (called with the blackboard) runs when a running action is cancelled.
static func action(work: Callable, halt: Callable = Callable(), label: String = "action") -> Task:
	var task := Leaf.new()
	task.kind = "action"
	task.work = work
	task.halt = halt
	task.label = label
	return task


## A leaf that is RUNNING until the deltas it was ticked with add up to [param seconds], then succeeds.
static func wait(seconds: float, label: String = "wait") -> Task:
	var task := Leaf.new()
	task.kind = "wait"
	task.seconds = seconds
	task.label = label
	return task


static func _named(task: Task, tasks: Array, label: String) -> Task:
	task.label = label
	task.children = tasks.duplicate()
	return task


static func _decorator(kind: String, child: Task, amount: float, label: String) -> Task:
	var task := Decorator.new()
	task.kind = kind
	task.amount = amount
	task.children = [child]
	task.label = label
	return task


func _describe(task: Task, depth: int, lines: PackedStringArray) -> void:
	var status_text: String = "-"
	if task.last_status >= 0:
		status_text = Status.keys()[task.last_status]
	lines.append("%s%s [%s]" % ["  ".repeat(depth), task.label, status_text])
	for child: Task in task.children:
		_describe(child, depth + 1, lines)
