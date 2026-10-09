extends "../baltor_test.gd"
## Tests for BaltorBehaviorTree: sequence and selector results, resuming a running child, reactive cancellation
## with halt, decorators, the parallel threshold, waits on tree time, invalid action results and describe().

const Subject := preload("../behavior_tree.gd")
const S := Subject.Status

var calls: Array[String] = []


func _step(task_label: String, result: int) -> Subject.Task:
	return Subject.action(func(_board: Dictionary, _delta: float) -> int:
		calls.append(task_label)
		return result, Callable(), task_label)


func test_sequence_stops_at_failure_and_selector_at_success() -> void:
	var tree: Subject = Subject.new(Subject.sequence([_step("a", S.SUCCESS), _step("b", S.FAILURE), _step("c", S.SUCCESS)]))
	assert_eq(tree.tick(0.1), S.FAILURE)
	assert_eq(calls, ["a", "b"])
	calls.clear()
	tree.root = Subject.selector([_step("x", S.FAILURE), _step("y", S.SUCCESS), _step("z", S.SUCCESS)])
	assert_eq(tree.tick(0.1), S.SUCCESS)
	assert_eq(calls, ["x", "y"])


func test_memory_sequence_resumes_at_the_running_child() -> void:
	var progress: Array[int] = [0]
	var walk := Subject.action(func(_board: Dictionary, _delta: float) -> int:
		progress[0] += 1
		calls.append("walk")
		return S.SUCCESS if progress[0] >= 3 else S.RUNNING)
	var tree: Subject = Subject.new(Subject.sequence([_step("look", S.SUCCESS), walk, _step("open", S.SUCCESS)]))
	assert_eq(tree.tick(0.1), S.RUNNING)
	assert_eq(tree.tick(0.1), S.RUNNING)
	assert_eq(tree.tick(0.1), S.SUCCESS)
	assert_eq(calls, ["look", "walk", "walk", "walk", "open"])


func test_reactive_sequence_cancels_a_running_action_and_halts_it() -> void:
	var tree: Subject = Subject.new()
	tree.blackboard["enemy_visible"] = true
	var halted: Array[bool] = [false]
	var chase := Subject.action(func(_board: Dictionary, _delta: float) -> int: return S.RUNNING,
		func(_board: Dictionary) -> void: halted[0] = true, "chase")
	var seen := Subject.condition(func(board: Dictionary) -> bool: return bool(board["enemy_visible"]), "seen")
	tree.root = Subject.sequence([seen, chase], true)
	assert_eq(tree.tick(0.1), S.RUNNING)
	tree.blackboard["enemy_visible"] = false
	assert_eq(tree.tick(0.1), S.FAILURE)
	assert_true(halted[0], "the running chase was halted")


func test_decorators_invert_succeed_repeat_and_cool_down() -> void:
	var tree: Subject = Subject.new(Subject.inverter(_step("i", S.SUCCESS)))
	assert_eq(tree.tick(0.1), S.FAILURE)
	tree.root = Subject.succeeder(_step("s", S.FAILURE))
	assert_eq(tree.tick(0.1), S.SUCCESS)
	tree.root = Subject.repeater(_step("r", S.SUCCESS), 3)
	assert_eq([tree.tick(0.1), tree.tick(0.1), tree.tick(0.1)], [S.RUNNING, S.RUNNING, S.SUCCESS])
	calls.clear()
	tree.root = Subject.cooldown(_step("shoot", S.SUCCESS), 1.0)
	assert_eq(tree.tick(0.1), S.SUCCESS)
	assert_eq(tree.tick(0.5), S.FAILURE, "cooling down")
	assert_eq(tree.tick(0.6), S.SUCCESS)
	assert_eq(calls, ["shoot", "shoot"])


func test_parallel_succeeds_at_threshold_and_fails_when_out_of_reach() -> void:
	var tree: Subject = Subject.new(Subject.parallel([_step("a", S.SUCCESS), _step("b", S.RUNNING), _step("c", S.SUCCESS)], 2))
	assert_eq(tree.tick(0.1), S.SUCCESS)
	tree.root = Subject.parallel([_step("a", S.FAILURE), _step("b", S.FAILURE), _step("c", S.RUNNING)], 2)
	assert_eq(tree.tick(0.1), S.FAILURE)
	tree.root = Subject.parallel([_step("a", S.SUCCESS), _step("b", S.RUNNING)], 2)
	assert_eq(tree.tick(0.1), S.RUNNING)


func test_wait_follows_tree_time() -> void:
	var tree: Subject = Subject.new(Subject.sequence([Subject.wait(0.5), _step("after", S.SUCCESS)]))
	assert_eq(tree.tick(0.2), S.RUNNING)
	assert_eq(tree.tick(0.2), S.RUNNING)
	assert_eq(tree.tick(0.2), S.SUCCESS)
	assert_almost_eq(tree.get_time(), 0.6)
	assert_eq(calls, ["after"])


func test_invalid_results_and_empty_trees_fail() -> void:
	var tree: Subject = Subject.new()
	assert_eq(tree.tick(0.1), S.FAILURE, "an empty tree fails")
	tree.root = Subject.action(func(_board: Dictionary, _delta: float) -> String: return "done")
	assert_eq(tree.tick(0.1), S.FAILURE, "a non-Status result is a failure")
	tree.root = _step("odd", 7)
	assert_eq(tree.tick(0.1), S.FAILURE, "an out-of-range status is a failure")


func test_describe_lists_labels_and_last_statuses() -> void:
	var tree: Subject = Subject.new(Subject.selector([_step("flee", S.FAILURE), _step("fight", S.RUNNING)], false, "root"))
	watch_signals(tree)
	tree.tick(0.1)
	assert_eq(tree.describe(), "root [RUNNING]\n  flee [FAILURE]\n  fight [RUNNING]")
	assert_eq(signal_emissions(tree, &"ticked"), [[S.RUNNING]])
