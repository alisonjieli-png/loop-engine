class_name BaltorThreatTable
extends RefCounted
## An aggro table for enemies: attackers build threat, threat decays over time, a taunt forces the target for a
## while, and the target only changes when another attacker passes the current one by a margin.
##
## add_threat() adds to an attacker's threat (never below zero). update() decays all threat exponentially by
## [member decay_per_second] (a fraction per second), forgets attackers below [member forget_below], counts down a
## taunt and picks the target: the taunting attacker while the taunt lasts, otherwise the current target unless
## another attacker's threat exceeds it times [member switch_margin] (1.1 is the common melee rule). A taunt also
## raises the taunter's threat to the current highest so the target does not snap back when it ends.

## Emitted when the target changes; an empty StringName means no target.
signal target_changed(previous: StringName, current: StringName)

## Another attacker must exceed the current target's threat times this to take over.
var switch_margin: float = 1.1
## Fraction of threat lost per second (exponential decay); 0 keeps threat forever.
var decay_per_second: float = 0.0
## Attackers whose threat falls below this are forgotten.
var forget_below: float = 0.01

var _threat: Dictionary = {}
var _target: StringName = &""
var _taunter: StringName = &""
var _taunt_left: float = 0.0


## Adds [param amount] (may be negative) to [param source]'s threat, clamped at zero, and re-picks the target.
func add_threat(source: StringName, amount: float) -> void:
	if source == &"":
		return
	_threat[source] = maxf(float(_threat.get(source, 0.0)) + amount, 0.0)
	_pick()


## The threat of [param source] (0.0 when unknown).
func get_threat(source: StringName) -> float:
	return float(_threat.get(source, 0.0))


## Forgets [param source] (for example when it dies) and re-picks the target.
func remove_source(source: StringName) -> void:
	_threat.erase(source)
	if _taunter == source:
		_taunter = &""
		_taunt_left = 0.0
	_pick()


## Forces [param source] as the target for [param seconds] and raises its threat to the current highest.
func taunt(source: StringName, seconds: float) -> void:
	if source == &"" or seconds <= 0.0:
		return
	var highest: float = 0.0
	for value: float in _threat.values():
		highest = maxf(highest, value)
	_threat[source] = maxf(get_threat(source), highest)
	_taunter = source
	_taunt_left = seconds
	_pick()


## Advances decay and the taunt timer by [param delta] seconds and re-picks the target.
func update(delta: float) -> void:
	if decay_per_second > 0.0:
		var factor: float = exp(-decay_per_second * delta)
		for source: StringName in _threat.keys():
			_threat[source] = float(_threat[source]) * factor
			if float(_threat[source]) < forget_below:
				_threat.erase(source)
	if _taunt_left > 0.0:
		_taunt_left = maxf(_taunt_left - delta, 0.0)
		if _taunt_left == 0.0:
			_taunter = &""
	_pick()


## The current target, or an empty StringName.
func get_target() -> StringName:
	return _target


## Attackers sorted by threat, highest first (ties by name).
func get_sorted_sources() -> Array[StringName]:
	var sources: Array[StringName] = []
	for source: StringName in _threat:
		sources.append(source)
	sources.sort_custom(func(a: StringName, b: StringName) -> bool:
		var ta: float = float(_threat[a])
		var tb: float = float(_threat[b])
		return ta > tb or (ta == tb and String(a) < String(b)))
	return sources


## Seconds of taunt left (0 when none).
func get_taunt_time_left() -> float:
	return _taunt_left


## Forgets everyone; the target becomes empty.
func clear() -> void:
	_threat.clear()
	_taunter = &""
	_taunt_left = 0.0
	_pick()


func _pick() -> void:
	var next: StringName = _target
	if _taunter != &"" and _threat.has(_taunter):
		next = _taunter
	else:
		var sorted: Array[StringName] = get_sorted_sources()
		if sorted.is_empty():
			next = &""
		elif not _threat.has(_target) or float(_threat[_target]) <= 0.0:
			next = sorted[0]
		elif float(_threat[sorted[0]]) > float(_threat[_target]) * switch_margin:
			next = sorted[0]
	if next != _target:
		var previous: StringName = _target
		_target = next
		target_changed.emit(previous, next)
