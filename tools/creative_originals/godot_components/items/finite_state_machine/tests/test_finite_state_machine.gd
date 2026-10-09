extends "../baltor_test.gd"
## Tests for BaltorStateMachine: start, ordered exit and enter, refusals, the table, history and queuing.

const Subject := preload("../finite_state_machine.gd")


class RecordingState extends Node:
	var events: Array[String] = []
	var last_data: Dictionary = {}
	var next_on_enter: StringName = &""

	func state_enter(previous: StringName, data: Dictionary) -> void:
		events.append("enter:%s" % previous)
		last_data = data
		if next_on_enter != &"":
			get_parent().call("transition_to", next_on_enter)

	func state_exit(next: StringName) -> void:
		events.append("exit:%s" % next)

	func state_process(delta: float) -> void:
		events.append("process %.2f" % delta)


func _make(state_names: Array[String], start_now: bool = true) -> Subject:
	var machine: Subject = Subject.new()
	machine.auto_start = start_now
	for state_name: String in state_names:
		var state := RecordingState.new()
		state.name = state_name
		machine.add_child(state)
	add_child(machine)
	return machine


func _state(machine: Subject, state_name: StringName) -> RecordingState:
	return machine.get_state_node(state_name) as RecordingState


func test_starts_in_first_child_and_enters_it() -> void:
	var machine := _make(["Idle", "Run"])
	assert_eq(machine.get_current_state(), &"Idle")
	assert_eq(_state(machine, &"Idle").events, ["enter:"])
	assert_eq(machine.get_state_names(), PackedStringArray(["Idle", "Run"]))


func test_transition_exits_then_enters_with_data_and_signal() -> void:
	var machine := _make(["Idle", "Run"])
	watch_signals(machine)
	assert_true(machine.transition_to(&"Run", {"speed": 3}))
	assert_eq(machine.get_current_state(), &"Run")
	assert_eq(_state(machine, &"Idle").events, ["enter:", "exit:Run"])
	assert_eq(_state(machine, &"Run").events, ["enter:Idle"])
	assert_eq(_state(machine, &"Run").last_data, {"speed": 3})
	assert_eq(signal_emissions(machine, &"state_changed"), [[&"Idle", &"Run"]])


func test_unknown_state_is_refused_and_current_kept() -> void:
	var machine := _make(["Idle", "Run"])
	watch_signals(machine)
	assert_false(machine.transition_to(&"Fly"))
	assert_eq(machine.get_current_state(), &"Idle")
	assert_eq(signal_emissions(machine, &"transition_refused"), [[&"Idle", &"Fly", "unknown state"]])
	assert_signal_not_emitted(machine, &"state_changed")


func test_transition_table_blocks_a_move_it_does_not_list() -> void:
	var machine := _make(["Idle", "Run", "Dead"], false)
	machine.allowed_transitions = {"Idle": ["Run"], "Run": ["Idle", "Dead"]}
	assert_true(machine.start())
	assert_false(machine.transition_to(&"Dead"), "Idle may not go straight to Dead")
	assert_eq(machine.get_current_state(), &"Idle")
	assert_true(machine.transition_to(&"Run"))
	assert_true(machine.transition_to(&"Dead"))
	assert_false(machine.can_transition(&"Dead", &"Idle"))


func test_go_back_walks_a_bounded_history() -> void:
	var machine := _make(["A", "B", "C"], false)
	machine.history_size = 2
	machine.start()
	machine.transition_to(&"B")
	machine.transition_to(&"C")
	machine.transition_to(&"A")
	assert_eq(machine.get_history(), [&"B", &"C"])
	assert_true(machine.go_back())
	assert_eq(machine.get_current_state(), &"C")
	assert_true(machine.go_back())
	assert_eq(machine.get_current_state(), &"B")
	assert_false(machine.go_back(), "the history is empty")


func test_process_reaches_only_the_active_state() -> void:
	var machine := _make(["Idle", "Run"])
	machine._process(0.25)
	machine.transition_to(&"Run")
	machine._process(0.5)
	var only_process := func(entry: String) -> bool: return entry.begins_with("process")
	assert_eq(_state(machine, &"Idle").events.filter(only_process), ["process 0.25"])
	assert_eq(_state(machine, &"Run").events.filter(only_process), ["process 0.50"])
	assert_almost_eq(machine.time_in_state, 0.5)


func test_request_made_inside_enter_is_queued_then_applied() -> void:
	var machine := _make(["Idle", "Jump", "Fall"])
	_state(machine, &"Jump").next_on_enter = &"Fall"
	watch_signals(machine)
	assert_true(machine.transition_to(&"Jump"))
	assert_eq(machine.get_current_state(), &"Fall")
	assert_eq(signal_emissions(machine, &"state_changed"), [[&"Idle", &"Jump"], [&"Jump", &"Fall"]])


func test_requests_before_start_and_after_stop_are_refused() -> void:
	var machine := _make(["Idle"], false)
	assert_eq(machine.get_current_state(), &"")
	assert_false(machine.transition_to(&"Idle"))
	assert_true(machine.start())
	machine.stop()
	assert_eq(_state(machine, &"Idle").events, ["enter:", "exit:"])
	assert_false(machine.transition_to(&"Idle"), "a stopped machine refuses transitions")
