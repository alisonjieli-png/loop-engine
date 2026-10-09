# AI perception with view cone, hearing and memory

Decide what a 2D agent sees (range, view cone, peripheral sense, optional occlusion check) and hears (radius times loudness), and remember targets with last known positions until a memory time runs out.

## How it works

Sight and hearing for 2D AI agents, with a memory of where each target was last seen.

A target is visible when it is within `view_distance` and within half of `view_angle_degrees`
of the facing direction, or within `peripheral_distance` in any direction, and the optional occlusion
Callable does not report a blocked line (for example a PhysicsDirectSpaceState2D ray query). observe() updates
the memory once per frame from a Dictionary of target ids to positions: newly visible targets are spotted,
remembered targets keep their last known position and the time since they were seen, and targets unseen for
longer than `memory_seconds` are forgotten. Noises are heard within `hearing_radius` times
their loudness.

## When to use it

Use it for guards and stealth enemies that should notice the player in front of them, lose them behind cover and search the last known position.

## Installation

Copy this folder to `res://baltor/godot_components/perception_senses/` in a Godot 4.3 or later project. The script `perception_senses.gd` declares the global class `BaltorPerception`, which extends `RefCounted`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `target_spotted(target_id: StringName, at: Vector2)`: Emitted when a target becomes visible after being unseen or unknown.
- `target_lost(target_id: StringName, last_known: Vector2)`: Emitted when a target has been unseen for longer than memory_seconds and is forgotten.
- `noise_heard(at: Vector2, loudness: float)`: Emitted when report_noise() hears a noise.

### Properties

- `view_distance: float`: Longest sight distance.
- `view_angle_degrees: float`: Full width of the view cone in degrees.
- `peripheral_distance: float`: Distance within which targets are noticed in any direction.
- `hearing_radius: float`: Hearing range for a noise of loudness 1.
- `memory_seconds: float`: Seconds a target stays remembered after it was last seen.

### Methods

- `can_see(observer: Vector2, facing: Vector2, target: Vector2, occluded: Callable = Callable()) -> bool`: True when `target` is visible from `observer` facing `facing`. `occluded`, when valid, is called with (observer, target) and returns true when the line is blocked.
- `can_hear(listener: Vector2, source: Vector2, loudness: float = 1.0) -> bool`: True when a noise of `loudness` at `source` reaches `listener`.
- `observe(delta: float, observer: Vector2, facing: Vector2, targets: Dictionary, occluded: Callable = Callable()) -> void`: Updates the memory by `delta` seconds from `targets` ({id: position}) as seen by an observer at `observer` facing `facing`.
- `report_noise(listener: Vector2, source: Vector2, loudness: float = 1.0) -> bool`: Reports a noise; returns true and remembers it as the place to investigate when it is heard.
- `get_known_targets() -> Array[StringName]`: Ids of every remembered target.
- `is_visible(target_id: StringName) -> bool`: True when `target_id` was visible at the last observe().
- `get_last_known_position(target_id: StringName) -> Vector2`: Where `target_id` was last seen (Vector2.ZERO when it is not remembered).
- `get_time_since_seen(target_id: StringName) -> float`: Seconds since `target_id` was last seen, or -1.0 when it is not remembered.
- `get_last_noise() -> Dictionary`: The position of the last heard noise, and whether there was one, as {"heard": bool, "at": Vector2}.
- `forget_all() -> void`: Forgets every target and noise without emitting signals.

## Usage

```gdscript
extends Node2D

var senses: BaltorPerception = BaltorPerception.new()


func _ready() -> void:
	senses.target_spotted.connect(_on_spotted)
	senses.target_lost.connect(_on_lost)


func _physics_process(delta: float) -> void:
	var player_position: Vector2 = Vector2(200, 0)
	senses.observe(delta, global_position, Vector2.RIGHT.rotated(rotation), {&"player": player_position})


func _on_spotted(target_id: StringName, at: Vector2) -> void:
	print("%s spotted at %s" % [target_id, at])


func _on_lost(target_id: StringName, last_known: Vector2) -> void:
	print("lost %s, search near %s" % [target_id, last_known])
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/perception_senses/run_tests.gd -- res://baltor/godot_components/perception_senses/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

2D only, with the view cone measured from a facing vector. Occlusion is whatever the Callable reports, such as a physics ray; nothing is cast by default. Hearing ignores walls. Target ids are StringNames. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
