# Ledge grab, hang and climb for 2D platformers

Find grabbable ledges with chest and head rays plus a downward ray for the top, hang from the corner, climb up along an up-then-forward path over a set time, or drop with a regrab cooldown.

## How it works

Ledge grabbing for side-view characters: probe a ledge with two rays, hang from its corner, climb up over a set
time or drop, as a three-state machine.

A ledge is found when a ray at chest height hits a wall while a ray at head height does not; a third ray cast
down from above the wall finds the top surface, and the corner is (wall x, top y). probe_ledge() does this
with the physics space; detect() is the same rule for probe results you already have. Grabbing only happens
while falling and not during the cooldown after a drop. While hanging, the body belongs at the corner plus
`hang_offset` (mirrored by facing). climb() moves it over `climb_time` seconds to the corner plus
`climb_offset`: first up, then forward. drop() lets go and starts `regrab_cooldown`.

## When to use it

Use it in platformers and Metroidvanias where the character should catch ledges after near-miss jumps.

## Installation

Copy this folder to `res://baltor/godot_components/ledge_grab_2d/` in a Godot 4.3 or later project. The script `ledge_grab_2d.gd` declares the global class `BaltorLedgeGrab2D`, which extends `Node`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `grabbed(corner: Vector2)`: Emitted when a ledge is grabbed, with the corner.
- `climbed(position: Vector2)`: Emitted when a climb finishes, with the standing position.
- `dropped()`: Emitted when the character lets go.

### Exported properties

- `hang_offset: Vector2 = Vector2(-10, 14)`: Body position relative to the corner while hanging, for facing right (x is mirrored for facing left).
- `climb_offset: Vector2 = Vector2(10, -16)`: Standing position relative to the corner after climbing, for facing right.
- `climb_time: float = 0.25`: Seconds a climb takes.
- `regrab_cooldown: float = 0.3`: Seconds after a drop before another grab.
- `chest_height: float = -4.0`: Height of the chest ray above the body origin (negative is up).
- `head_height: float = -20.0`: Height of the head ray above the body origin (negative is up).
- `reach: float = 14.0`: Length of the forward rays.

### Methods

- `static detect(chest_hit: bool, head_hit: bool, falling: bool) -> bool`: The rule for a grabbable ledge: a wall at chest height, open space at head height, and falling.
- `probe_ledge(space: PhysicsDirectSpaceState2D, origin: Vector2, facing: float, exclude: Array[RID] = [], mask: int = 1) -> Dictionary`: Casts the probe rays from `origin` toward `facing` (1 right, -1 left) in `space`. Returns {"found": bool, "corner": Vector2}. `exclude` lists RIDs to ignore, such as the body itself.
- `try_grab(corner: Vector2, facing: float, falling: bool) -> bool`: Grabs the ledge at `corner` while facing `facing`. Refused (false) unless free, falling and out of the cooldown.
- `climb() -> bool`: Starts climbing from a hang. Returns false when not hanging.
- `drop() -> bool`: Lets go of the ledge (while hanging) and starts the regrab cooldown.
- `advance(delta: float) -> Vector2`: Advances the climb and the cooldown by `delta` seconds and returns where the body belongs now (its hang or climb position; Vector2.ZERO while free).
- `get_state() -> State`: The current state.
- `get_hang_position() -> Vector2`: The body position while hanging from the current corner.
- `get_stand_position() -> Vector2`: The body position after climbing the current corner.

### Enums

- `State`: FREE, HANGING, CLIMBING: FREE: not on a ledge. HANGING: holding a corner. CLIMBING: moving up over it.

## Usage

```gdscript
extends CharacterBody2D

@onready var ledge: BaltorLedgeGrab2D = $LedgeGrab
var facing: float = 1.0


func _physics_process(delta: float) -> void:
	if ledge.get_state() == BaltorLedgeGrab2D.State.FREE and velocity.y > 0.0:
		var space: PhysicsDirectSpaceState2D = get_world_2d().direct_space_state
		var probe: Dictionary = ledge.probe_ledge(space, global_position, facing, [get_rid()])
		if probe["found"]:
			ledge.try_grab(probe["corner"], facing, true)
	if ledge.get_state() != BaltorLedgeGrab2D.State.FREE:
		global_position = ledge.advance(delta)
		if Input.is_action_just_pressed("ui_up"):
			ledge.climb()
	else:
		ledge.advance(delta)
		velocity.y += 900.0 * delta
		move_and_slide()
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/ledge_grab_2d/run_tests.gd -- res://baltor/godot_components/ledge_grab_2d/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Axis-aligned ledges; the corner uses the chest hit x and the top surface y. The owner moves the body to the returned positions and disables its own gravity while hanging or climbing. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
