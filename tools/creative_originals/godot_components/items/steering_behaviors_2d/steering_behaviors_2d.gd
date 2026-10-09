class_name BaltorSteering
extends RefCounted
## Classic steering behaviors for 2D agents: seek, flee, arrive, pursue, evade and wander, plus a point-mass
## integrator with force and speed limits.
##
## Each behavior returns a steering force: the desired velocity minus the current velocity, as in Reynolds'
## steering model. Seek wants full speed toward a point; flee wants full speed away within a panic distance;
## arrive slows down linearly inside a slowing radius and stops on the point; pursue and evade seek or flee the
## position a moving target will have after the time it takes to cover the distance at full speed (capped by
## max_prediction). Wander keeps an angle on a circle projected ahead of the agent and jitters it each step with a
## seeded random generator, so paths are smooth and repeatable. integrate() applies a force with a mass, caps the
## force and the speed, and returns the new position and velocity.

## Distance of the wander circle in front of the agent.
var wander_distance: float = 60.0
## Radius of the wander circle.
var wander_radius: float = 30.0
## Largest change of the wander angle per call, in radians.
var wander_jitter: float = 0.6

var _wander_angle: float = 0.0
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()


func _init(seed_value: int = 1) -> void:
	_rng.seed = seed_value


## Steering toward [param target] at full speed.
static func seek(position: Vector2, velocity: Vector2, target: Vector2, max_speed: float) -> Vector2:
	var offset: Vector2 = target - position
	if offset.length_squared() < 0.000001:
		return -velocity
	return offset.normalized() * max_speed - velocity


## Steering away from [param threat] at full speed while it is closer than [param panic_distance]; zero beyond.
static func flee(position: Vector2, velocity: Vector2, threat: Vector2, max_speed: float,
		panic_distance: float = INF) -> Vector2:
	var offset: Vector2 = position - threat
	if offset.length() > panic_distance:
		return Vector2.ZERO
	if offset.length_squared() < 0.000001:
		offset = Vector2.RIGHT
	return offset.normalized() * max_speed - velocity


## Steering that reaches [param target] and slows down inside [param slowing_radius].
static func arrive(position: Vector2, velocity: Vector2, target: Vector2, max_speed: float,
		slowing_radius: float) -> Vector2:
	var offset: Vector2 = target - position
	var distance: float = offset.length()
	if distance < 0.0001:
		return -velocity
	var speed: float = max_speed
	if distance < slowing_radius:
		speed = max_speed * distance / slowing_radius
	return offset / distance * speed - velocity


## Seek toward where a target moving at [param target_velocity] will be.
static func pursue(position: Vector2, velocity: Vector2, target_position: Vector2, target_velocity: Vector2,
		max_speed: float, max_prediction: float = 1.0) -> Vector2:
	var lead: float = minf(position.distance_to(target_position) / maxf(max_speed, 0.001), max_prediction)
	return seek(position, velocity, target_position + target_velocity * lead, max_speed)


## Flee from where a threat moving at [param threat_velocity] will be.
static func evade(position: Vector2, velocity: Vector2, threat_position: Vector2, threat_velocity: Vector2,
		max_speed: float, max_prediction: float = 1.0) -> Vector2:
	var lead: float = minf(position.distance_to(threat_position) / maxf(max_speed, 0.001), max_prediction)
	return flee(position, velocity, threat_position + threat_velocity * lead, max_speed)


## [param force] shortened to at most [param max_length].
static func truncate(force: Vector2, max_length: float) -> Vector2:
	return force.limit_length(max_length)


## Applies [param steering] to a point mass and returns {"position", "velocity"} after [param delta] seconds.
static func integrate(position: Vector2, velocity: Vector2, steering: Vector2, max_force: float, max_speed: float,
		mass: float, delta: float) -> Dictionary:
	var acceleration: Vector2 = truncate(steering, max_force) / maxf(mass, 0.001)
	var next_velocity: Vector2 = truncate(velocity + acceleration * delta, max_speed)
	return {"position": position + next_velocity * delta, "velocity": next_velocity}


## A wandering steering force for an agent moving with [param velocity]; the circle sits ahead of it.
func wander(velocity: Vector2, max_speed: float) -> Vector2:
	_wander_angle += _rng.randf_range(-wander_jitter, wander_jitter)
	var heading: Vector2 = velocity.normalized() if velocity.length_squared() > 0.000001 else Vector2.RIGHT
	var circle_center: Vector2 = heading * wander_distance
	var target: Vector2 = circle_center + Vector2.from_angle(heading.angle() + _wander_angle) * wander_radius
	return target.normalized() * max_speed - velocity


## The current wander angle relative to the heading, in radians.
func get_wander_angle() -> float:
	return _wander_angle
