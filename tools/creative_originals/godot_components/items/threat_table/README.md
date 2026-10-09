# Threat table with taunts and switch margin

Track threat per attacker for an enemy, decay it over time, force the target with taunts, and change targets only when another attacker passes the current one by a margin.

## How it works

An aggro table for enemies: attackers build threat, threat decays over time, a taunt forces the target for a
while, and the target only changes when another attacker passes the current one by a margin.

add_threat() adds to an attacker's threat (never below zero). update() decays all threat exponentially by
`decay_per_second` (a fraction per second), forgets attackers below `forget_below`, counts down a
taunt and picks the target: the taunting attacker while the taunt lasts, otherwise the current target unless
another attacker's threat exceeds it times `switch_margin` (1.1 is the common melee rule). A taunt also
raises the taunter's threat to the current highest so the target does not snap back when it ends.

## When to use it

Use it for RPG and action enemies that should fight whoever hurts them most while letting tanks hold attention with taunts.

## Installation

Copy this folder to `res://baltor/godot_components/threat_table/` in a Godot 4.3 or later project. The script `threat_table.gd` declares the global class `BaltorThreatTable`, which extends `RefCounted`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `target_changed(previous: StringName, current: StringName)`: Emitted when the target changes; an empty StringName means no target.

### Properties

- `switch_margin: float`: Another attacker must exceed the current target's threat times this to take over.
- `decay_per_second: float`: Fraction of threat lost per second (exponential decay); 0 keeps threat forever.
- `forget_below: float`: Attackers whose threat falls below this are forgotten.

### Methods

- `add_threat(source: StringName, amount: float) -> void`: Adds `amount` (may be negative) to `source`'s threat, clamped at zero, and re-picks the target.
- `get_threat(source: StringName) -> float`: The threat of `source` (0.0 when unknown).
- `remove_source(source: StringName) -> void`: Forgets `source` (for example when it dies) and re-picks the target.
- `taunt(source: StringName, seconds: float) -> void`: Forces `source` as the target for `seconds` and raises its threat to the current highest.
- `update(delta: float) -> void`: Advances decay and the taunt timer by `delta` seconds and re-picks the target.
- `get_target() -> StringName`: The current target, or an empty StringName.
- `get_sorted_sources() -> Array[StringName]`: Attackers sorted by threat, highest first (ties by name).
- `get_taunt_time_left() -> float`: Seconds of taunt left (0 when none).
- `clear() -> void`: Forgets everyone; the target becomes empty.

## Usage

```gdscript
extends Node

var threat: BaltorThreatTable = BaltorThreatTable.new()


func _ready() -> void:
	threat.decay_per_second = 0.05
	threat.target_changed.connect(_on_target_changed)


func on_damaged(attacker: StringName, amount: float) -> void:
	threat.add_threat(attacker, amount)


func _process(delta: float) -> void:
	threat.update(delta)


func _on_target_changed(_previous: StringName, current: StringName) -> void:
	print("now attacking %s" % current)
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/threat_table/run_tests.gd -- res://baltor/godot_components/threat_table/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Target selection uses threat only (no range or line of sight rules). Decay is exponential per second and applied in update(). Attacker ids are StringNames. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
