class_name BaltorUtilityAI
extends RefCounted
## Utility AI: scores named actions from considerations shaped by response curves and picks the best one.
##
## A consideration reads a number from the context through a Callable, normalizes it to 0..1 between a minimum
## and a maximum, and passes it through a response curve. An action's score is its weight times the product of
## its considerations. Because multiplying many values below one penalizes actions with more considerations, each
## value v is first raised by a compensation factor: v + (1 - v) * (1 - 1/n) * v for n considerations. A value of
## 0 still vetoes the action. choose() returns the action with the highest score; the action chosen last time gets
## its score multiplied by (1 + [member current_bonus]) so small changes do not make the agent switch back and
## forth.

## Response curves; every result is clamped to 0..1.
## LINEAR: slope * (x - x_shift) + y_shift. POLYNOMIAL: slope * (x - x_shift)^exponent + y_shift.
## LOGISTIC: 1 / (1 + e^(-slope * (x - x_shift))) + y_shift. STEP: 1 when x >= x_shift, else y_shift.
## SMOOTHSTEP: 3t^2 - 2t^3 of x.
enum Response { LINEAR, POLYNOMIAL, LOGISTIC, STEP, SMOOTHSTEP }

## Emitted by choose() when the chosen action changes.
signal action_changed(previous: StringName, current: StringName)

## Multiplier bonus for the action chosen last time (hysteresis). 0 turns it off.
var current_bonus: float = 0.1

var _actions: Dictionary = {}
var _order: Array[StringName] = []
var _current: StringName = &""


## Adds an action with a weight that scales its score. Refuses an empty or repeated name or a negative weight.
func add_action(action_name: StringName, weight: float = 1.0) -> bool:
	if action_name == &"" or _actions.has(action_name) or weight < 0.0:
		return false
	_actions[action_name] = {"weight": weight, "considerations": []}
	_order.append(action_name)
	return true


## Adds a consideration to [param action_name]: [param input] is called with the context and returns a number,
## which is mapped from [param minimum]..[param maximum] to 0..1 and shaped by [param curve] and its parameters.
## Refuses an unknown action, an invalid Callable or an empty range.
func add_consideration(action_name: StringName, input: Callable, minimum: float, maximum: float,
		curve: Response = Response.LINEAR, slope: float = 1.0, exponent: float = 1.0, x_shift: float = 0.0,
		y_shift: float = 0.0) -> bool:
	if not _actions.has(action_name) or not input.is_valid() or is_equal_approx(minimum, maximum):
		return false
	(_actions[action_name]["considerations"] as Array).append({"input": input, "minimum": minimum,
			"maximum": maximum, "curve": curve, "slope": slope, "exponent": exponent, "x_shift": x_shift,
			"y_shift": y_shift})
	return true


## The response of [param curve] at [param x] (0..1), clamped to 0..1.
static func curve_value(curve: Response, x: float, slope: float = 1.0, exponent: float = 1.0, x_shift: float = 0.0,
		y_shift: float = 0.0) -> float:
	var t: float = clampf(x, 0.0, 1.0)
	var y: float = 0.0
	match curve:
		Response.LINEAR:
			y = slope * (t - x_shift) + y_shift
		Response.POLYNOMIAL:
			y = slope * pow(maxf(t - x_shift, 0.0), exponent) + y_shift
		Response.LOGISTIC:
			y = 1.0 / (1.0 + exp(-slope * (t - x_shift))) + y_shift
		Response.STEP:
			y = 1.0 if t >= x_shift else y_shift
		Response.SMOOTHSTEP:
			y = t * t * (3.0 - 2.0 * t)
	return clampf(y, 0.0, 1.0)


## The score of [param action_name] for [param context], or -1.0 for an unknown action. An action without
## considerations scores its weight.
func score_action(action_name: StringName, context: Variant = null) -> float:
	if not _actions.has(action_name):
		return -1.0
	var action: Dictionary = _actions[action_name]
	var considerations: Array = action["considerations"]
	var count: int = considerations.size()
	var score: float = float(action["weight"])
	if count == 0:
		return score
	var modification: float = 1.0 - 1.0 / float(count)
	for consideration: Dictionary in considerations:
		var raw: float = float((consideration["input"] as Callable).call(context))
		var normalized: float = inverse_lerp(float(consideration["minimum"]), float(consideration["maximum"]), raw)
		var value: float = curve_value(consideration["curve"], normalized, consideration["slope"],
				consideration["exponent"], consideration["x_shift"], consideration["y_shift"])
		value += (1.0 - value) * modification * value
		score *= value
		if score <= 0.0:
			return 0.0
	return score


## Scores of every action for [param context] as {name: score}, without the hysteresis bonus.
func scores(context: Variant = null) -> Dictionary:
	var result: Dictionary = {}
	for action_name: StringName in _order:
		result[action_name] = score_action(action_name, context)
	return result


## Picks the action with the highest score (the last choice gets the bonus). Returns an empty StringName when
## there is no action or every score is 0; ties go to the action added first.
func choose(context: Variant = null) -> StringName:
	var best: StringName = &""
	var best_score: float = 0.0
	for action_name: StringName in _order:
		var score: float = score_action(action_name, context)
		if action_name == _current:
			score *= 1.0 + current_bonus
		if score > best_score:
			best = action_name
			best_score = score
	if best != _current:
		var previous: StringName = _current
		_current = best
		action_changed.emit(previous, best)
	return best


## The action chosen by the last choose() call.
func get_current() -> StringName:
	return _current


## Names of the actions in the order they were added.
func get_actions() -> Array[StringName]:
	return _order.duplicate()
