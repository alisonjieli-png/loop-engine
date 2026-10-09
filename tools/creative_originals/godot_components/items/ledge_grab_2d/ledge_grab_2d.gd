class_name BaltorLedgeGrab2D
extends Node
## Ledge grabbing for side-view characters: probe a ledge with two rays, hang from its corner, climb up over a set
## time or drop, as a three-state machine.
##
## A ledge is found when a ray at chest height hits a wall while a ray at head height does not; a third ray cast
## down from above the wall finds the top surface, and the corner is (wall x, top y). probe_ledge() does this
## with the physics space; detect() is the same rule for probe results you already have. Grabbing only happens
## while falling and not during the cooldown after a drop. While hanging, the body belongs at the corner plus
## [member hang_offset] (mirrored by facing). climb() moves it over [member climb_time] seconds to the corner plus
## [member climb_offset]: first up, then forward. drop() lets go and starts [member regrab_cooldown].

## Emitted when a ledge is grabbed, with the corner.
signal grabbed(corner: Vector2)
## Emitted when a climb finishes, with the standing position.
signal climbed(position: Vector2)
## Emitted when the character lets go.
signal dropped

## FREE: not on a ledge. HANGING: holding a corner. CLIMBING: moving up over it.
enum State { FREE, HANGING, CLIMBING }

## Body position relative to the corner while hanging, for facing right (x is mirrored for facing left).
@export var hang_offset: Vector2 = Vector2(-10, 14)
## Standing position relative to the corner after climbing, for facing right.
@export var climb_offset: Vector2 = Vector2(10, -16)
## Seconds a climb takes.
@export var climb_time: float = 0.25
## Seconds after a drop before another grab.
@export var regrab_cooldown: float = 0.3
## Height of the chest ray above the body origin (negative is up).
@export var chest_height: float = -4.0
## Height of the head ray above the body origin (negative is up).
@export var head_height: float = -20.0
## Length of the forward rays.
@export var reach: float = 14.0

var _state: State = State.FREE
var _corner: Vector2 = Vector2.ZERO
var _facing: float = 1.0
var _climb_elapsed: float = 0.0
var _cooldown_left: float = 0.0


## The rule for a grabbable ledge: a wall at chest height, open space at head height, and falling.
static func detect(chest_hit: bool, head_hit: bool, falling: bool) -> bool:
	return chest_hit and not head_hit and falling


## Casts the probe rays from [param origin] toward [param facing] (1 right, -1 left) in [param space].
## Returns {"found": bool, "corner": Vector2}. [param exclude] lists RIDs to ignore, such as the body itself.
func probe_ledge(space: PhysicsDirectSpaceState2D, origin: Vector2, facing: float, exclude: Array[RID] = [],
		mask: int = 1) -> Dictionary:
	var side: float = signf(facing) if facing != 0.0 else 1.0
	var chest: Dictionary = _ray(space, origin + Vector2(0, chest_height), side, exclude, mask)
	var head: Dictionary = _ray(space, origin + Vector2(0, head_height), side, exclude, mask)
	if chest.is_empty() or not head.is_empty():
		return {"found": false, "corner": Vector2.ZERO}
	var wall_x: float = (chest["position"] as Vector2).x
	var above := Vector2(wall_x + side * 2.0, origin.y + head_height)
	var down := PhysicsRayQueryParameters2D.create(above, above + Vector2(0, head_height * -1.0 + 8.0), mask, exclude)
	var top: Dictionary = space.intersect_ray(down)
	if top.is_empty():
		return {"found": false, "corner": Vector2.ZERO}
	return {"found": true, "corner": Vector2(wall_x, (top["position"] as Vector2).y)}


## Grabs the ledge at [param corner] while facing [param facing]. Refused (false) unless free, falling and out of
## the cooldown.
func try_grab(corner: Vector2, facing: float, falling: bool) -> bool:
	if _state != State.FREE or not falling or _cooldown_left > 0.0:
		return false
	_state = State.HANGING
	_corner = corner
	_facing = signf(facing) if facing != 0.0 else 1.0
	grabbed.emit(corner)
	return true


## Starts climbing from a hang. Returns false when not hanging.
func climb() -> bool:
	if _state != State.HANGING:
		return false
	_state = State.CLIMBING
	_climb_elapsed = 0.0
	return true


## Lets go of the ledge (while hanging) and starts the regrab cooldown.
func drop() -> bool:
	if _state != State.HANGING:
		return false
	_state = State.FREE
	_cooldown_left = regrab_cooldown
	dropped.emit()
	return true


## Advances the climb and the cooldown by [param delta] seconds and returns where the body belongs now
## (its hang or climb position; Vector2.ZERO while free).
func advance(delta: float) -> Vector2:
	_cooldown_left = maxf(_cooldown_left - delta, 0.0)
	match _state:
		State.HANGING:
			return get_hang_position()
		State.CLIMBING:
			_climb_elapsed += delta
			var t: float = 1.0 if climb_time <= 0.0 else clampf(_climb_elapsed / climb_time, 0.0, 1.0)
			var start: Vector2 = get_hang_position()
			var finish: Vector2 = get_stand_position()
			var lift: float = clampf(t * 2.0, 0.0, 1.0)
			var slide: float = clampf(t * 2.0 - 1.0, 0.0, 1.0)
			var point := Vector2(lerpf(start.x, finish.x, slide), lerpf(start.y, finish.y, lift))
			if t >= 1.0:
				_state = State.FREE
				climbed.emit(finish)
			return point
	return Vector2.ZERO


## The current state.
func get_state() -> State:
	return _state


## The body position while hanging from the current corner.
func get_hang_position() -> Vector2:
	return _corner + Vector2(hang_offset.x * _facing, hang_offset.y)


## The body position after climbing the current corner.
func get_stand_position() -> Vector2:
	return _corner + Vector2(climb_offset.x * _facing, climb_offset.y)


func _ray(space: PhysicsDirectSpaceState2D, from: Vector2, side: float, exclude: Array[RID], mask: int) -> Dictionary:
	return space.intersect_ray(PhysicsRayQueryParameters2D.create(from, from + Vector2(side * reach, 0), mask, exclude))
