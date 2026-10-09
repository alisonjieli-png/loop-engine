class_name BaltorPerception
extends RefCounted
## Sight and hearing for 2D AI agents, with a memory of where each target was last seen.
##
## A target is visible when it is within [member view_distance] and within half of [member view_angle_degrees]
## of the facing direction, or within [member peripheral_distance] in any direction, and the optional occlusion
## Callable does not report a blocked line (for example a PhysicsDirectSpaceState2D ray query). observe() updates
## the memory once per frame from a Dictionary of target ids to positions: newly visible targets are spotted,
## remembered targets keep their last known position and the time since they were seen, and targets unseen for
## longer than [member memory_seconds] are forgotten. Noises are heard within [member hearing_radius] times
## their loudness.

## Emitted when a target becomes visible after being unseen or unknown.
signal target_spotted(target_id: StringName, at: Vector2)
## Emitted when a target has been unseen for longer than memory_seconds and is forgotten.
signal target_lost(target_id: StringName, last_known: Vector2)
## Emitted when report_noise() hears a noise.
signal noise_heard(at: Vector2, loudness: float)

## Longest sight distance.
var view_distance: float = 400.0
## Full width of the view cone in degrees.
var view_angle_degrees: float = 110.0
## Distance within which targets are noticed in any direction.
var peripheral_distance: float = 40.0
## Hearing range for a noise of loudness 1.
var hearing_radius: float = 300.0
## Seconds a target stays remembered after it was last seen.
var memory_seconds: float = 5.0

var _memory: Dictionary = {}
var _last_noise: Vector2 = Vector2.ZERO
var _heard_any: bool = false


## True when [param target] is visible from [param observer] facing [param facing]. [param occluded], when valid,
## is called with (observer, target) and returns true when the line is blocked.
func can_see(observer: Vector2, facing: Vector2, target: Vector2, occluded: Callable = Callable()) -> bool:
	var offset: Vector2 = target - observer
	var distance: float = offset.length()
	if distance > view_distance:
		return false
	if distance > peripheral_distance:
		if facing.length_squared() == 0.0:
			return false
		var half_angle: float = deg_to_rad(view_angle_degrees) * 0.5
		if absf(facing.angle_to(offset)) > half_angle + 0.000001:
			return false
	return not (occluded.is_valid() and bool(occluded.call(observer, target)))


## True when a noise of [param loudness] at [param source] reaches [param listener].
func can_hear(listener: Vector2, source: Vector2, loudness: float = 1.0) -> bool:
	return listener.distance_to(source) <= hearing_radius * maxf(loudness, 0.0)


## Updates the memory by [param delta] seconds from [param targets] ({id: position}) as seen by an observer at
## [param observer] facing [param facing].
func observe(delta: float, observer: Vector2, facing: Vector2, targets: Dictionary,
		occluded: Callable = Callable()) -> void:
	for target_id: Variant in targets:
		var key := StringName(str(target_id))
		var at: Vector2 = targets[target_id]
		if not can_see(observer, facing, at, occluded):
			continue
		var known: Dictionary = _memory.get(key, {})
		var was_visible: bool = not known.is_empty() and bool(known["visible"])
		_memory[key] = {"position": at, "unseen": 0.0, "visible": true}
		if not was_visible:
			target_spotted.emit(key, at)
	for key: StringName in _memory.keys():
		var entry: Dictionary = _memory[key]
		var seen_now: bool = targets.has(key) or targets.has(String(key))
		if seen_now and can_see(observer, facing, targets.get(key, targets.get(String(key), Vector2.ZERO)), occluded):
			continue
		entry["visible"] = false
		entry["unseen"] = float(entry["unseen"]) + delta
		if float(entry["unseen"]) > memory_seconds:
			_memory.erase(key)
			target_lost.emit(key, entry["position"])


## Reports a noise; returns true and remembers it as the place to investigate when it is heard.
func report_noise(listener: Vector2, source: Vector2, loudness: float = 1.0) -> bool:
	if not can_hear(listener, source, loudness):
		return false
	_last_noise = source
	_heard_any = true
	noise_heard.emit(source, loudness)
	return true


## Ids of every remembered target.
func get_known_targets() -> Array[StringName]:
	var ids: Array[StringName] = []
	for key: StringName in _memory:
		ids.append(key)
	return ids


## True when [param target_id] was visible at the last observe().
func is_visible(target_id: StringName) -> bool:
	return _memory.has(target_id) and bool(_memory[target_id]["visible"])


## Where [param target_id] was last seen (Vector2.ZERO when it is not remembered).
func get_last_known_position(target_id: StringName) -> Vector2:
	return _memory[target_id]["position"] if _memory.has(target_id) else Vector2.ZERO


## Seconds since [param target_id] was last seen, or -1.0 when it is not remembered.
func get_time_since_seen(target_id: StringName) -> float:
	return float(_memory[target_id]["unseen"]) if _memory.has(target_id) else -1.0


## The position of the last heard noise, and whether there was one, as {"heard": bool, "at": Vector2}.
func get_last_noise() -> Dictionary:
	return {"heard": _heard_any, "at": _last_noise}


## Forgets every target and noise without emitting signals.
func forget_all() -> void:
	_memory.clear()
	_heard_any = false
