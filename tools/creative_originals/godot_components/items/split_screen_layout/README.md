# Split-screen layouts for local multiplayer

Compute view rectangles for one to many local players (halves, one wide plus two, grids with full-width last rows), with gaps between views, and place Control nodes such as SubViewportContainers on them.

## How it works

Split-screen layouts for one to many local players: screen rectangles for each view with a gap between them,
and a helper that places Control nodes (such as SubViewportContainers) on them.

One player gets the whole screen. Two players get two halves split side by side, or stacked when
`stacked` is true. Three players get one wide view and two smaller ones (on top with side-by-side
splits, or on the left when stacked). Four or more players get a grid with as many columns as the rounded-up
square root of the count; a last row with fewer views spreads them over the full width. `gap` pixels
separate neighboring views and never appear at the screen border.

## When to use it

Use it when a couch co-op game needs to switch between one to four or more views as players join and leave.

## Installation

Copy this folder to `res://baltor/godot_components/split_screen_layout/` in a Godot 4.3 or later project. The script `split_screen_layout.gd` declares the global class `BaltorSplitScreen`, which extends `RefCounted`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Methods

- `static layout(count: int, screen: Rect2, stacked: bool = false, gap: float = 0.0) -> Array[Rect2]`: The view rectangles for `count` players on `screen`.
- `static arrange(controls: Array, screen: Rect2, stacked: bool = false, gap: float = 0.0) -> int`: Places each Control of `controls` on its view rectangle. Returns the number of controls placed.

## Usage

```gdscript
extends Control

@onready var views: Array = [$PlayerOneView, $PlayerTwoView, $PlayerThreeView]


func _ready() -> void:
	resized.connect(_layout)
	_layout()


func _layout() -> void:
	BaltorSplitScreen.arrange(views, Rect2(Vector2.ZERO, size), false, 4.0)
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/split_screen_layout/run_tests.gd -- res://baltor/godot_components/split_screen_layout/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Rectangles only; creating SubViewports, cameras and input routing per player is up to you. Views in a grid differ in size when the last row is short. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
