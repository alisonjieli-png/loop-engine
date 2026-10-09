extends "../baltor_test.gd"
## Tests for BaltorStateStack: pause and resume order, replace, top-only and full updates, pop_to, and refusals.

const Subject := preload("../pushdown_automaton.gd")


class Screen extends RefCounted:
	var label: String
	var journal: Array[String]

	func _init(screen_label: String, shared: Array[String]) -> void:
		label = screen_label
		journal = shared

	func stack_enter(data: Dictionary) -> void:
		journal.append("%s enter %s" % [label, data.get("why", "")])

	func stack_exit() -> void:
		journal.append("%s exit" % label)

	func stack_pause() -> void:
		journal.append("%s pause" % label)

	func stack_resume() -> void:
		journal.append("%s resume" % label)

	func stack_update(delta: float) -> void:
		journal.append("%s update %.1f" % [label, delta])


var journal: Array[String] = []


func _stack() -> Subject:
	var stack: Subject = Subject.new()
	add_child(stack)
	stack.set_process(false)
	return stack


func test_push_pauses_below_and_pop_resumes_it() -> void:
	var stack := _stack()
	var game := Screen.new("game", journal)
	var pause := Screen.new("pause", journal)
	assert_true(stack.push(game))
	assert_true(stack.push(pause, {"why": "esc"}))
	assert_eq(stack.pop(), pause)
	assert_eq(journal, ["game enter ", "game pause", "pause enter esc", "pause exit", "game resume"])
	assert_eq(stack.peek(), game)


func test_replace_swaps_the_top_without_touching_below() -> void:
	var stack := _stack()
	var game := Screen.new("game", journal)
	var menu := Screen.new("menu", journal)
	var options := Screen.new("options", journal)
	stack.push(game)
	stack.push(menu)
	journal.clear()
	watch_signals(stack)
	assert_true(stack.replace(options))
	assert_eq(journal, ["menu exit", "options enter "])
	assert_eq(stack.depth(), 2)
	assert_eq(signal_emissions(stack, &"top_changed"), [[menu, options]])


func test_only_the_top_updates_unless_update_all() -> void:
	var stack := _stack()
	stack.push(Screen.new("game", journal))
	stack.push(Screen.new("hud", journal))
	journal.clear()
	stack.update(0.5)
	assert_eq(journal, ["hud update 0.5"])
	journal.clear()
	stack.update_all = true
	stack.update(0.25)
	assert_eq(journal, ["game update 0.2", "hud update 0.2"])


func test_pop_to_unwinds_several_states_in_order() -> void:
	var stack := _stack()
	var a := Screen.new("a", journal)
	var b := Screen.new("b", journal)
	var c := Screen.new("c", journal)
	stack.push(a)
	stack.push(b)
	stack.push(c)
	journal.clear()
	assert_true(stack.pop_to(a))
	assert_eq(journal, ["c exit", "b resume", "b exit", "a resume"])
	assert_false(stack.pop_to(c), "c is no longer on the stack")
	assert_eq(stack.depth(), 1)


func test_refuses_duplicates_null_and_overflow() -> void:
	var stack := _stack()
	stack.max_depth = 2
	var a := Screen.new("a", journal)
	assert_true(stack.push(a))
	assert_false(stack.push(a), "the same object twice")
	assert_false(stack.push(null))
	assert_true(stack.push(Screen.new("b", journal)))
	assert_false(stack.push(Screen.new("c", journal)), "max_depth reached")
	stack.clear()
	assert_null(stack.pop(), "popping an empty stack gives null")
	assert_eq(stack.depth(), 0)
