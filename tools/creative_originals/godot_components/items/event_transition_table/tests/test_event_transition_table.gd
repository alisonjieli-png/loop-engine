extends "../baltor_test.gd"
## Tests for BaltorTransitionTable: loading the packaged door table, guards and actions, wildcard rows, ignored
## events, available events and malformed tables that change nothing.

const Subject := preload("../event_transition_table.gd")

var played: Array[String] = []


func _door() -> Subject:
	var door: Subject = Subject.new()
	door.register_guard(&"not_blocked", func(payload: Dictionary) -> bool: return not payload.get("blocked", false))
	door.register_guard(&"has_key", func(payload: Dictionary) -> bool: return payload.get("key", "") == "brass")
	door.register_action(&"play_creak", func(payload: Dictionary) -> void: played.append("creak %s" % payload.get("by", "")))
	door.register_action(&"spawn_debris", func(_payload: Dictionary) -> void: played.append("debris"))
	var table: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(package_path("door_table.json")))
	assert_true(door.load_table(table), str(door.get_errors()))
	return door


func test_loads_the_packaged_table_and_runs_actions() -> void:
	var door := _door()
	assert_eq(door.get_state(), &"closed")
	watch_signals(door)
	assert_true(door.fire(&"open", {"by": "guard"}))
	assert_eq(door.get_state(), &"open")
	assert_eq(played, ["creak guard"])
	assert_eq(signal_emissions(door, &"transitioned"), [[&"closed", &"open", &"open"]])


func test_guards_decide_and_unknown_events_are_ignored() -> void:
	var door := _door()
	watch_signals(door)
	assert_false(door.fire(&"open", {"blocked": true}))
	assert_false(door.fire(&"lock", {"key": "iron"}))
	assert_true(door.fire(&"lock", {"key": "brass"}))
	assert_false(door.fire(&"open"), "a locked door has no open transition")
	assert_eq(signal_emissions(door, &"event_ignored").size(), 3)
	assert_eq(door.get_state(), &"locked")


func test_exact_rows_win_over_wildcard_rows() -> void:
	var door := _door()
	assert_true(door.fire(&"smash"))
	assert_eq(played, ["debris"])
	assert_true(door.fire(&"smash"), "the exact broken row is taken, without debris")
	assert_eq(played, ["debris"])
	door.reset()
	assert_eq(door.get_state(), &"closed")


func test_available_events_list_exact_and_wildcard_rows() -> void:
	var door := _door()
	assert_eq(door.available_events(), PackedStringArray(["open", "lock", "smash"]))
	door.fire(&"open")
	assert_eq(door.available_events(), PackedStringArray(["close", "smash"]))


func test_malformed_tables_are_refused_without_changes() -> void:
	var door := _door()
	door.fire(&"open")
	var bad_tables: Array[Dictionary] = [
		{"initial": "a", "states": ["a"], "transitions": [{"from": "a", "event": "go", "to": "b"}]},
		{"initial": "z", "states": ["a"], "transitions": []},
		{"initial": "a", "states": ["a"], "transitions": [{"from": "a", "event": "go", "to": "a", "guard": "nope"}]},
		{"initial": "a", "states": ["a"], "transitions": [{"from": "a", "to": "a"}]},
		{"initial": "a", "states": ["a", "a"], "transitions": []},
		{"initial": "a", "states": ["a"], "transitions": [{"from": "a", "event": "go", "to": "a", "actions": ["x"]}]},
	]
	for table: Dictionary in bad_tables:
		assert_false(door.load_table(table), str(table))
		assert_false(door.get_errors().is_empty())
	assert_eq(door.get_state(), &"open", "the loaded table and state are unchanged")
	assert_true(door.fire(&"close"))
