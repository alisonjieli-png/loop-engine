class_name BaltorKnockback
extends Node
## Knockback that adds up, fades with exponential friction and stuns in proportion to its strength.
##
## apply_knockback() adds direction * strength / [member weight] to the knockback velocity, so heavier objects are
## pushed less. advance() multiplies the velocity by exp(-[member friction] * delta) and snaps it to zero below
## [member min_speed]. Each hit also stuns for strength / weight * [member stun_per_unit] seconds, up to
## [member max_stun]; a stronger hit replaces a weaker remaining stun, a weaker one never shortens it. The owner
## adds get_velocity() to its own movement and ignores input while is_stunned() is true.

## Emitted for each hit with the knockback velocity after it.
signal knocked(velocity: Vector2)
## Emitted when the stun runs out.
signal stun_ended

## Divides incoming knockback; 2 halves it.
@export var weight: float = 1.0
## Exponential decay rate of the knockback per second.
@export var friction: float = 8.0
## Speeds below this snap to zero.
@export var min_speed: float = 5.0
## Seconds of stun per unit of knockback speed.
@export var stun_per_unit: float = 0.002
## Longest stun in seconds.
@export var max_stun: float = 0.6
## Advance in this node's own physics frames.
@export var auto_advance: bool = true

var _velocity: Vector2 = Vector2.ZERO
var _stun_left: float = 0.0


func _physics_process(delta: float) -> void:
	if auto_advance:
		advance(delta)


## Adds a hit of [param strength] toward [param direction]. Ignored for a zero direction or strength at or below 0.
func apply_knockback(direction: Vector2, strength: float) -> void:
	if strength <= 0.0 or direction.length_squared() < 0.000001:
		return
	var speed: float = strength / maxf(weight, 0.001)
	_velocity += direction.normalized() * speed
	_stun_left = maxf(_stun_left, minf(speed * stun_per_unit, max_stun))
	knocked.emit(_velocity)


## Decays the knockback and the stun by [param delta] seconds and returns the knockback velocity.
func advance(delta: float) -> Vector2:
	_velocity *= exp(-friction * delta)
	if _velocity.length() < min_speed:
		_velocity = Vector2.ZERO
	if _stun_left > 0.0:
		_stun_left = maxf(_stun_left - delta, 0.0)
		if _stun_left == 0.0:
			stun_ended.emit()
	return _velocity


## The current knockback velocity.
func get_velocity() -> Vector2:
	return _velocity


## True while stunned.
func is_stunned() -> bool:
	return _stun_left > 0.0


## Seconds of stun left.
func get_stun_left() -> float:
	return _stun_left


## Removes all knockback and stun at once.
func clear() -> void:
	_velocity = Vector2.ZERO
	_stun_left = 0.0
