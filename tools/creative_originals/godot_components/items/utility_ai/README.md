# Utility AI scorer with response curves

Score named actions from considerations mapped through response curves (linear, polynomial, logistic, step, smoothstep) with compensated products, vetoes, weights and hysteresis, and pick the best action.

## How it works

Utility AI: scores named actions from considerations shaped by response curves and picks the best one.

A consideration reads a number from the context through a Callable, normalizes it to 0..1 between a minimum
and a maximum, and passes it through a response curve. An action's score is its weight times the product of
its considerations. Because multiplying many values below one penalizes actions with more considerations, each
value v is first raised by a compensation factor: v + (1 - v) * (1 - 1/n) * v for n considerations. A value of
0 still vetoes the action. choose() returns the action with the highest score; the action chosen last time gets
its score multiplied by (1 + `current_bonus`) so small changes do not make the agent switch back and
forth.

## When to use it

Use it when an agent weighs many needs at once (hunger, danger, ammo, distance) and simple if chains become hard to balance.

## Installation

Copy this folder to `res://baltor/godot_components/utility_ai/` in a Godot 4.3 or later project. The script `utility_ai.gd` declares the global class `BaltorUtilityAI`, which extends `RefCounted`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `action_changed(previous: StringName, current: StringName)`: Emitted by choose() when the chosen action changes.

### Properties

- `current_bonus: float`: Multiplier bonus for the action chosen last time (hysteresis). 0 turns it off.

### Methods

- `add_action(action_name: StringName, weight: float = 1.0) -> bool`: Adds an action with a weight that scales its score. Refuses an empty or repeated name or a negative weight.
- `add_consideration(action_name: StringName, input: Callable, minimum: float, maximum: float, curve: Response = Response.LINEAR, slope: float = 1.0, exponent: float = 1.0, x_shift: float = 0.0, y_shift: float = 0.0) -> bool`: Adds a consideration to `action_name`: `input` is called with the context and returns a number, which is mapped from `minimum`..`maximum` to 0..1 and shaped by `curve` and its parameters. Refuses an unknown action, an invalid Callable or an empty range.
- `static curve_value(curve: Response, x: float, slope: float = 1.0, exponent: float = 1.0, x_shift: float = 0.0, y_shift: float = 0.0) -> float`: The response of `curve` at `x` (0..1), clamped to 0..1.
- `score_action(action_name: StringName, context: Variant = null) -> float`: The score of `action_name` for `context`, or -1.0 for an unknown action. An action without considerations scores its weight.
- `scores(context: Variant = null) -> Dictionary`: Scores of every action for `context` as {name: score}, without the hysteresis bonus.
- `choose(context: Variant = null) -> StringName`: Picks the action with the highest score (the last choice gets the bonus). Returns an empty StringName when there is no action or every score is 0; ties go to the action added first.
- `get_current() -> StringName`: The action chosen by the last choose() call.
- `get_actions() -> Array[StringName]`: Names of the actions in the order they were added.

### Enums

- `Response`: LINEAR, POLYNOMIAL, LOGISTIC, STEP, SMOOTHSTEP: Response curves; every result is clamped to 0..1. LINEAR: slope * (x - x_shift) + y_shift. POLYNOMIAL: slope * (x - x_shift)^exponent + y_shift. LOGISTIC: 1 / (1 + e^(-slope * (x - x_shift))) + y_shift. STEP: 1 when x >= x_shift, else y_shift. SMOOTHSTEP: 3t^2 - 2t^3 of x.

## Usage

```gdscript
extends Node

var brain: BaltorUtilityAI = BaltorUtilityAI.new()
var health: float = 30.0


func _ready() -> void:
	brain.add_action(&"heal")
	brain.add_action(&"attack")
	brain.add_consideration(&"heal", _missing_health, 0.0, 100.0, BaltorUtilityAI.Response.POLYNOMIAL, 1.0, 2.0)
	brain.add_consideration(&"attack", _health_left, 0.0, 100.0)
	print(brain.choose(self))


func _missing_health(_context: Variant) -> float:
	return 100.0 - health


func _health_left(_context: Variant) -> float:
	return health
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/utility_ai/run_tests.gd -- res://baltor/godot_components/utility_ai/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Chooses the single best action; no weighted random among the top choices. Scores are only as good as the considerations and curve parameters, which need tuning per game. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
