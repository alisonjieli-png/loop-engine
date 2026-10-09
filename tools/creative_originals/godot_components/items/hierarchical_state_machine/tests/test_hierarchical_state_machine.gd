extends "../baltor_test.gd"
## Tests for BaltorHierarchicalStateMachine: entry order on start, sibling and cross-branch transitions,
## events bubbling to ancestors, guards, history, self transitions, updates and refused definitions.

const Subject := preload("../hierarchical_state_machine.gd")

var events: Array[String] = []


func _machine() -> Subject:
	var machine: Subject = Subject.new()
	for row: Array in [["Ground", &""], ["Idle", &"Ground"], ["Run", &"Ground"], ["Air", &""], ["Jump", &"Air"],
			["Fall", &"Air"], ["Hurt", &""]]:
		var state_name: StringName = StringName(row[0])
		machine.add_state(state_name, row[1], events.append.bind("+" + row[0]), events.append.bind("-" + row[0]))
	machine.add_transition(&"Idle", &"move", &"Run")
	machine.add_transition(&"Run", &"halt", &"Idle")
	machine.add_transition(&"Ground", &"jump", &"Jump")
	machine.add_transition(&"Jump", &"apex", &"Fall")
	machine.add_transition(&"Air", &"land", &"Ground")
	machine.add_transition(&"Ground", &"hit", &"Hurt", func(data: Dictionary) -> bool: return int(data.get("damage", 0)) > 0)
	machine.add_transition(&"Run", &"restart", &"Run")
	return machine


func test_start_enters_the_initial_chain_outermost_first() -> void:
	var machine := _machine()
	assert_true(machine.start())
	assert_eq(events, ["+Ground", "+Idle"])
	assert_eq(machine.get_active_path(), [&"Ground", &"Idle"])
	assert_false(machine.start(), "already running")


func test_cross_branch_transition_exits_to_the_common_ancestor() -> void:
	var machine := _machine()
	machine.start()
	events.clear()
	assert_true(machine.send(&"move"))
	assert_eq(events, ["-Idle", "+Run"])
	events.clear()
	assert_true(machine.send(&"jump"), "the Ground ancestor handles jump")
	assert_eq(events, ["-Run", "-Ground", "+Air", "+Jump"])
	assert_true(machine.is_in(&"Air"))
	assert_false(machine.is_in(&"Ground"))


func test_history_resumes_the_last_child() -> void:
	var machine := _machine()
	machine.set_history(&"Ground", true)
	machine.start()
	machine.send(&"move")
	machine.send(&"jump")
	machine.send(&"apex")
	events.clear()
	assert_true(machine.send(&"land"))
	assert_eq(events, ["-Fall", "-Air", "+Ground", "+Run"])
	var plain := _machine()
	plain.start()
	plain.send(&"move")
	plain.send(&"jump")
	plain.send(&"land")
	assert_eq(plain.get_leaf(), &"Idle", "without history the initial child is entered")


func test_guards_and_unknown_events_leave_the_state_alone() -> void:
	var machine := _machine()
	machine.start()
	machine.send(&"move")
	assert_false(machine.send(&"hit", {"damage": 0}), "the guard refuses zero damage")
	assert_eq(machine.get_leaf(), &"Run")
	assert_false(machine.send(&"fly"))
	assert_true(machine.send(&"hit", {"damage": 5}))
	assert_eq(machine.get_active_path(), [&"Hurt"])


func test_self_transition_exits_and_reenters() -> void:
	var machine := _machine()
	machine.start()
	machine.send(&"move")
	events.clear()
	var seen: Array = []
	machine.transitioned.connect(func(a: StringName, b: StringName, e: StringName) -> void: seen.append([a, b, e]))
	assert_true(machine.send(&"restart"))
	assert_eq(events, ["-Run", "+Run"])
	assert_eq(seen, [[&"Run", &"Run", &"restart"]])


func test_update_runs_outermost_first_and_stop_exits_leaf_first() -> void:
	var machine: Subject = Subject.new()
	var updates: Array[String] = []
	machine.add_state(&"Outer", &"", Callable(), Callable(), func(delta: float) -> void: updates.append("outer %.1f" % delta))
	machine.add_state(&"Inner", &"Outer", Callable(), events.append.bind("-Inner"),
			func(delta: float) -> void: updates.append("inner %.1f" % delta))
	machine.start()
	machine.update(0.5)
	assert_eq(updates, ["outer 0.5", "inner 0.5"])
	machine.stop()
	assert_eq(events, ["-Inner"])
	assert_false(machine.is_running())


func test_bad_definitions_are_refused() -> void:
	var machine := _machine()
	assert_false(machine.add_state(&"Idle", &"Ground"), "repeated name")
	assert_false(machine.add_state(&"Swim", &"Water"), "unknown parent")
	assert_false(machine.add_state(&""), "empty name")
	assert_false(machine.add_transition(&"Idle", &"go", &"Nowhere"))
	assert_false(machine.set_initial(&"Ground", &"Jump"), "Jump is not a child of Ground")
	assert_true(machine.set_initial(&"Ground", &"Run"))
	machine.start()
	assert_eq(machine.get_leaf(), &"Run")
