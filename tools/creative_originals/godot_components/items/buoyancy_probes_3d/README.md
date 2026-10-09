# Probe buoyancy and water drag for RigidBody3D

Float a RigidBody3D on water from probe points: depth-proportional upward force per probe, travelling sine waves for the surface height, water drag and signals for entering and leaving the water.

## How it works

Buoyancy for the parent RigidBody3D from probe points: each submerged probe pushes up in proportion to its depth,
and water drag slows the body while it is wet.

Probes are points in the parent's local space. The water surface height at a point is `water_height`
plus a sum of travelling sine waves, each a Vector4(amplitude, wavelength, speed, direction in degrees); the
same formula can drive a water shader so visuals and physics agree. A probe at depth d below the surface pushes
up with buoyancy * (mass / probe count) * gravity * clamp(d / probe_depth, 0, 1), at the probe's position, so
uneven depth also produces the righting torque. On flat water every probe rests at probe_depth / buoyancy
below the surface. Linear and angular drag scale with the fraction of submerged probes.

## When to use it

Use it for boats, crates and debris that should float, tilt with waves and settle at a predictable draft.

## Installation

Copy this folder to `res://baltor/godot_components/buoyancy_probes_3d/` in a Godot 4.3 or later project. The script `buoyancy_probes_3d.gd` declares the global class `BaltorBuoyancy3D`, which extends `Node`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `entered_water()`: Emitted when the first probe goes under the surface.
- `left_water()`: Emitted when the last probe comes out of the water.

### Exported properties

- `water_height: float = 0.0`: Height of the calm water surface.
- `waves: PackedVector4Array = PackedVector4Array()`: Waves as Vector4(amplitude, wavelength, speed, direction in degrees).
- `probes: PackedVector3Array = PackedVector3Array([Vector3(-0.5, 0, -0.5), Vector3(0.5, 0, -0.5), Vector3(-0.5, 0, 0.5), Vector3(0.5, 0, 0.5)])`: Probe points in the parent's local space.
- `probe_depth: float = 0.5`: Depth at which a probe gives its full force.
- `buoyancy: float = 2.0`: Full-depth force per probe share relative to the body's weight; 2 floats at half probe_depth.
- `gravity: float = 9.8`: Downward acceleration used for the force, in meters per second squared.
- `water_drag: float = 1.5`: Linear drag per second while fully submerged.
- `water_angular_drag: float = 1.5`: Angular drag per second while fully submerged.

### Methods

- `static wave_height_at(point: Vector2, time: float, base_height: float, wave_list: PackedVector4Array) -> float`: The surface height at world point (x, z) = `point` at `time` for `wave_list` over `base_height`.
- `surface_height(world_position: Vector3) -> float`: The surface height under `world_position` at the component's current time.
- `probe_force(depth: float, mass_share: float) -> float`: The upward force for one probe at `depth` below the surface carrying `mass_share` kilograms.
- `get_submerged_ratio() -> float`: Fraction of probes under water in the last update (0 to 1).
- `get_time() -> float`: Seconds of wave time so far.
- `apply_forces(body: RigidBody3D, delta: float) -> void`: Advances wave time by `delta` and applies buoyancy and drag to `body`.

## Usage

```gdscript
extends RigidBody3D

@onready var floats: BaltorBuoyancy3D = $Buoyancy


func _ready() -> void:
	floats.waves = PackedVector4Array([Vector4(0.3, 12.0, 2.0, 0.0), Vector4(0.15, 5.0, 1.0, 40.0)])
	floats.entered_water.connect(func() -> void: print("splash"))
```

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/buoyancy_probes_3d/run_tests.gd -- res://baltor/godot_components/buoyancy_probes_3d/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Not a fluid simulation: probes ignore hull shape and displaced volume, and waves are sums of sines without Gerstner sideways motion. Light default drag lets bodies bob for a while. The surface function must match any water shader you pair it with. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
