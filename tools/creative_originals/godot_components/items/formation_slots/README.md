# Formation slots with short-travel assignment

Lay out slots for line, column, wedge, circle and grid formations, rotate them to a leader's position and facing, and assign members to slots so that paths are short and do not cross.

## How it works

Formation slot layouts (line, column, wedge, circle, grid) and an assignment of members to slots that keeps
the total travel distance short.

Offsets are in formation space: the formation faces +x, slot 0 is the anchor at the origin (except for the
circle, whose slots ring the anchor), and the other slots spread sideways (y) and behind (-x) at the given
spacing. world_slots() rotates and moves them to an anchor position and facing angle. assign() first pairs the
closest member and slot globally, then swaps pairs of assignments while a swap shortens the total, which
removes crossing paths; it is a heuristic, not an optimal assignment.

## When to use it

Use it for RTS squads, escorts and party followers that should take up a shape around a leader without units crossing paths.

## Installation

Copy this folder to `res://baltor/godot_components/formation_slots/` in a Godot 4.3 or later project. The script `formation_slots.gd` declares the global class `BaltorFormation`, which extends `RefCounted`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Methods

- `static slot_offsets(shape: Shape, count: int, spacing: float) -> PackedVector2Array`: Local offsets of `count` slots for `shape` at `spacing`.
- `static world_slots(offsets: PackedVector2Array, anchor: Vector2, facing_angle: float) -> PackedVector2Array`: `offsets` rotated by `facing_angle` (radians) and moved to `anchor`.
- `static assign(members: PackedVector2Array, slots: PackedVector2Array) -> PackedInt32Array`: The slot index for each member (same order as `members`). Refuses (empty result) different sizes.
- `static total_distance(members: PackedVector2Array, slots: PackedVector2Array, assignment: PackedInt32Array) -> float`: Sum of the distances from each member to its assigned slot.

### Enums

- `Shape`: LINE, COLUMN, WEDGE, CIRCLE, GRID: Formation layouts.

## Usage

```gdscript
extends Node2D

func targets_for(members: PackedVector2Array, leader: Vector2, heading: float) -> PackedVector2Array:
	var offsets: PackedVector2Array = BaltorFormation.slot_offsets(BaltorFormation.Shape.WEDGE, members.size(), 24.0)
	var slots: PackedVector2Array = BaltorFormation.world_slots(offsets, leader, heading)
	var order: PackedInt32Array = BaltorFormation.assign(members, slots)
	var targets := PackedVector2Array()
	for index in range(members.size()):
		targets.append(slots[order[index]])
	return targets
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/formation_slots/run_tests.gd -- res://baltor/godot_components/formation_slots/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

2D layouts facing +x. The assignment is greedy plus pairwise swaps, not an optimal Hungarian assignment; it is quadratic to cubic in the member count and meant for squads, not crowds. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
