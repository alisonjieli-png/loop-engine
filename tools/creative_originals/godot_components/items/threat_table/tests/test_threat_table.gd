extends "../baltor_test.gd"
## Tests for BaltorThreatTable: picking the highest, the switch margin, taunts, decay and forgetting, removal and
## negative amounts.

const Subject := preload("../threat_table.gd")


func test_highest_threat_is_the_target_with_a_switch_margin() -> void:
	var table: Subject = Subject.new()
	watch_signals(table)
	table.add_threat(&"tank", 100.0)
	assert_eq(table.get_target(), &"tank")
	table.add_threat(&"mage", 105.0)
	assert_eq(table.get_target(), &"tank", "105 is not above 110 percent of 100")
	table.add_threat(&"mage", 10.0)
	assert_eq(table.get_target(), &"mage")
	assert_eq(signal_emissions(table, &"target_changed"), [[&"", &"tank"], [&"tank", &"mage"]])
	assert_eq(table.get_sorted_sources(), [&"mage", &"tank"])


func test_taunt_forces_the_target_then_threat_rules_again() -> void:
	var table: Subject = Subject.new()
	table.add_threat(&"rogue", 300.0)
	table.taunt(&"warrior", 2.0)
	assert_eq(table.get_target(), &"warrior")
	assert_eq(table.get_threat(&"warrior"), 300.0, "the taunt raises threat to the top")
	table.add_threat(&"rogue", 100.0)
	table.update(1.0)
	assert_eq(table.get_target(), &"warrior", "still taunted")
	table.update(1.5)
	assert_eq(table.get_taunt_time_left(), 0.0)
	assert_eq(table.get_target(), &"rogue", "400 passes 110 percent of 300 after the taunt")


func test_decay_forgets_quiet_attackers() -> void:
	var table: Subject = Subject.new()
	table.decay_per_second = 1.0
	table.forget_below = 1.0
	table.add_threat(&"archer", 10.0)
	table.update(1.0)
	assert_almost_eq(table.get_threat(&"archer"), 10.0 * exp(-1.0), 0.0001)
	table.update(2.0)
	assert_eq(table.get_threat(&"archer"), 0.0)
	assert_eq(table.get_target(), &"")


func test_removing_the_target_picks_the_next() -> void:
	var table: Subject = Subject.new()
	table.add_threat(&"a", 50.0)
	table.add_threat(&"b", 40.0)
	table.remove_source(&"a")
	assert_eq(table.get_target(), &"b")
	table.clear()
	assert_eq(table.get_target(), &"")


func test_negative_amounts_never_make_negative_threat() -> void:
	var table: Subject = Subject.new()
	table.add_threat(&"healer", -20.0)
	assert_eq(table.get_threat(&"healer"), 0.0)
	table.add_threat(&"healer", 5.0)
	table.add_threat(&"healer", -50.0)
	assert_eq(table.get_threat(&"healer"), 0.0)
	table.add_threat(&"", 99.0)
	assert_eq(table.get_sorted_sources(), [&"healer"], "an empty id is ignored")
	table.taunt(&"warrior", 0.0)
	assert_ne(table.get_target(), &"warrior", "a zero-second taunt does nothing")
