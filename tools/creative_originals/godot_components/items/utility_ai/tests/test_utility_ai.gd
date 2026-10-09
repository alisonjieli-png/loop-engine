extends "../baltor_test.gd"
## Tests for BaltorUtilityAI: curve values, normalization, compensated products, vetoes, choosing with
## hysteresis and refused definitions.

const Subject := preload("../utility_ai.gd")
const C := Subject.Response


func test_curves_have_known_values_and_clamp() -> void:
	assert_almost_eq(Subject.curve_value(C.LINEAR, 0.25), 0.25)
	assert_almost_eq(Subject.curve_value(C.LINEAR, 0.25, -1.0, 1.0, 0.0, 1.0), 0.75)
	assert_almost_eq(Subject.curve_value(C.POLYNOMIAL, 0.5, 1.0, 2.0), 0.25)
	assert_almost_eq(Subject.curve_value(C.LOGISTIC, 0.6, 10.0, 1.0, 0.6), 0.5)
	assert_eq(Subject.curve_value(C.STEP, 0.29, 1.0, 1.0, 0.3), 0.0)
	assert_eq(Subject.curve_value(C.STEP, 0.3, 1.0, 1.0, 0.3), 1.0)
	assert_almost_eq(Subject.curve_value(C.SMOOTHSTEP, 0.5), 0.5)
	assert_eq(Subject.curve_value(C.LINEAR, 0.9, 3.0), 1.0, "results are clamped to 1")
	assert_eq(Subject.curve_value(C.LINEAR, 5.0, -1.0), 0.0, "inputs are clamped to 0..1")


func test_inputs_are_normalized_between_minimum_and_maximum() -> void:
	var ai: Subject = Subject.new()
	ai.add_action(&"heal")
	ai.add_consideration(&"heal", func(context: Dictionary) -> float: return context["missing"], 0.0, 200.0)
	assert_almost_eq(ai.score_action(&"heal", {"missing": 50.0}), 0.25)
	assert_eq(ai.score_action(&"heal", {"missing": 500.0}), 1.0)
	assert_eq(ai.score_action(&"heal", {"missing": -20.0}), 0.0)


func test_product_uses_the_compensation_factor_and_zero_vetoes() -> void:
	var ai: Subject = Subject.new()
	ai.add_action(&"attack", 2.0)
	ai.add_consideration(&"attack", func(_context: Variant) -> float: return 0.5, 0.0, 1.0)
	ai.add_consideration(&"attack", func(_context: Variant) -> float: return 0.5, 0.0, 1.0)
	assert_almost_eq(ai.score_action(&"attack"), 2.0 * 0.625 * 0.625)
	ai.add_consideration(&"attack", func(_context: Variant) -> float: return 0.0, 0.0, 1.0)
	assert_eq(ai.score_action(&"attack"), 0.0, "a zero consideration vetoes the action")


func test_choose_picks_the_best_with_hysteresis() -> void:
	var ai: Subject = Subject.new()
	ai.add_action(&"eat")
	ai.add_action(&"sleep")
	ai.add_consideration(&"eat", func(context: Dictionary) -> float: return context["hunger"], 0.0, 1.0)
	ai.add_consideration(&"sleep", func(context: Dictionary) -> float: return context["tired"], 0.0, 1.0)
	watch_signals(ai)
	assert_eq(ai.choose({"hunger": 0.6, "tired": 0.4}), &"eat")
	assert_eq(ai.choose({"hunger": 0.5, "tired": 0.53}), &"eat", "sleep is better by less than the bonus")
	assert_eq(ai.choose({"hunger": 0.3, "tired": 0.8}), &"sleep")
	assert_eq(signal_emissions(ai, &"action_changed"), [[&"", &"eat"], [&"eat", &"sleep"]])
	assert_eq(ai.get_current(), &"sleep")


func test_bad_definitions_are_refused_and_empty_choice_is_empty() -> void:
	var ai: Subject = Subject.new()
	assert_eq(ai.choose(), &"")
	assert_true(ai.add_action(&"flee"))
	assert_false(ai.add_action(&"flee"), "repeated name")
	assert_false(ai.add_action(&"hide", -1.0), "negative weight")
	assert_false(ai.add_consideration(&"missing", func(_context: Variant) -> float: return 1.0, 0.0, 1.0))
	assert_false(ai.add_consideration(&"flee", func(_context: Variant) -> float: return 1.0, 2.0, 2.0), "empty range")
	assert_eq(ai.score_action(&"missing"), -1.0)
	assert_eq(ai.scores(), {&"flee": 1.0})
