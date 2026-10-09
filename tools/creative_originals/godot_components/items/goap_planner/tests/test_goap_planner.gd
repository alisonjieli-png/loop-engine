extends "../baltor_test.gd"
## Tests for BaltorGoapPlanner: a chain of preconditions, choosing the cheaper route, goals that already hold,
## unreachable goals, procedural checks and the expansion bound.

const Subject := preload("../goap_planner.gd")


func _camp() -> Subject:
	var planner: Subject = Subject.new()
	planner.add_action(&"get_axe", {"has_axe": false}, {"has_axe": true}, 1.0)
	planner.add_action(&"chop_wood", {"has_axe": true}, {"has_wood": true}, 2.0)
	planner.add_action(&"buy_wood", {"has_gold": true}, {"has_wood": true, "has_gold": false}, 5.0)
	planner.add_action(&"make_fire", {"has_wood": true}, {"warm": true}, 1.0)
	return planner


func test_plans_a_chain_of_preconditions() -> void:
	var planner := _camp()
	var steps: Array[StringName] = planner.plan({"has_axe": false, "has_gold": false}, {"warm": true})
	assert_eq(steps, [&"get_axe", &"chop_wood", &"make_fire"])
	assert_almost_eq(planner.get_last_cost(), 4.0)
	assert_true(planner.is_last_plan_found())


func test_prefers_the_cheaper_route_and_follows_cost_changes() -> void:
	var planner := _camp()
	var start: Dictionary = {"has_axe": false, "has_gold": true}
	assert_eq(planner.plan(start, {"warm": true}), [&"get_axe", &"chop_wood", &"make_fire"])
	planner.add_action(&"chop_wood", {"has_axe": true}, {"has_wood": true}, 9.0)
	assert_eq(planner.plan(start, {"warm": true}), [&"buy_wood", &"make_fire"])
	assert_almost_eq(planner.get_last_cost(), 6.0)


func test_goal_already_holding_gives_an_empty_found_plan() -> void:
	var planner := _camp()
	assert_eq(planner.plan({"warm": true}, {"warm": true}), [])
	assert_true(planner.is_last_plan_found())
	assert_eq(planner.get_last_cost(), 0.0)


func test_unreachable_goals_and_checks_give_no_plan() -> void:
	var planner := _camp()
	assert_eq(planner.plan({"has_axe": false}, {"flying": true}), [])
	assert_false(planner.is_last_plan_found(), "no action sets flying")
	planner.add_action(&"get_axe", {"has_axe": false}, {"has_axe": true}, 1.0,
		func(state: Dictionary) -> bool: return bool(state.get("shop_open", false)))
	assert_eq(planner.plan({"has_axe": false, "has_gold": false}, {"warm": true}), [])
	assert_false(planner.is_last_plan_found(), "the closed shop blocks the only route")
	assert_eq(planner.plan({"has_axe": false, "has_gold": false, "shop_open": true}, {"warm": true}).size(), 3)


func test_satisfies_apply_and_definition_refusals() -> void:
	var planner := _camp()
	assert_true(Subject.satisfies({"a": 1, "b": 2}, {"a": 1}))
	assert_false(Subject.satisfies({"a": 1}, {"a": 2}))
	assert_false(Subject.satisfies({}, {"a": 1}))
	assert_eq(planner.apply({"has_gold": true}, &"buy_wood"), {"has_gold": false, "has_wood": true})
	assert_false(planner.add_action(&"", {}, {"x": true}))
	assert_false(planner.add_action(&"noop", {}, {}))
	assert_false(planner.add_action(&"refund", {}, {"x": true}, -1.0))
	assert_true(planner.remove_action(&"buy_wood"))
	assert_false(planner.has_action(&"buy_wood"))
	assert_false(planner.remove_action(&"buy_wood"))


func test_search_stops_at_max_nodes() -> void:
	var planner: Subject = Subject.new()
	for index in range(12):
		planner.add_action(StringName("flip_%d" % index), {}, {"bit_%d" % index: true}, 1.0)
	var goal: Dictionary = {"bit_0": true, "bit_5": true, "bit_11": true, "unreachable": true}
	assert_eq(planner.plan({}, goal, 50), [])
	assert_eq(planner.get_last_expanded(), 50)
