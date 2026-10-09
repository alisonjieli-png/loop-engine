# Raycast suspension vehicle for arcade driving

Drive a RigidBody3D on raycast wheels: spring-damper suspension per wheel, drive force on driven wheels, steering on front wheels, lateral grip and rolling resistance, with a ride height independent of mass.

## How it works

An arcade vehicle on raycast suspension: each wheel casts a ray down, a spring-damper pushes the body up at that
wheel, drive force pushes along the wheel's heading and lateral grip cancels sideways sliding.

Wheels are points in the body's local space at the top of their suspension travel. Every physics frame each
wheel casts a ray along the body's down axis, `rest_length` + `wheel_radius` long. On a hit the
compression x is rest_length minus the spring length, and the spring force along the body's up axis is
(stiffness * x + damping * dx/dt) * mass / wheel count, never pulling the body down. With stiffness and damping
given per kilogram the ride height does not depend on the mass: at rest x = gravity / stiffness. Grounded wheels
also add drive force (driven wheels, split evenly), rolling resistance and a lateral force that cancels the
sideways speed at the contact point times `lateral_grip`. The first `steering_wheel_count` wheels
turn by up to `max_steer_degrees`. The chassis collision shape is up to you; keep it above the wheels.

## When to use it

Use it for arcade racers, delivery games and vehicle sections where cars should bounce over bumps and corner without a full tire simulation.

## Installation

Copy this folder to `res://baltor/godot_components/raycast_vehicle_3d/` in a Godot 4.3 or later project. The script `raycast_vehicle_3d.gd` declares the global class `BaltorRaycastVehicle`, which extends `RigidBody3D`. The files in the folder refer to each other by relative path, so the folder also works elsewhere; the example scene and the commands below assume the path above.

## API

### Signals

- `airborne_changed(airborne: bool)`: Emitted when every wheel leaves the ground or the first wheel touches it again.

### Exported properties

- `wheel_points: PackedVector3Array = PackedVector3Array([Vector3(-0.8, 0, -1.2), Vector3(0.8, 0, -1.2), Vector3(-0.8, 0, 1.2), Vector3(0.8, 0, 1.2)])`: Wheel mount points in local space, front wheels first.
- `steering_wheel_count: int = 2`: How many wheels at the start of wheel_points steer.
- `driven_wheels: PackedInt32Array = PackedInt32Array([2, 3])`: Indices of the wheels that receive drive force.
- `rest_length: float = 0.5`: Spring length at rest, in meters.
- `wheel_radius: float = 0.35`: Wheel radius in meters.
- `spring_stiffness: float = 30.0`: Spring stiffness per kilogram of body mass, per wheel share.
- `spring_damping: float = 4.0`: Spring damping per kilogram of body mass, per wheel share.
- `engine_acceleration: float = 12.0`: Drive acceleration at full throttle in meters per second squared.
- `max_steer_degrees: float = 30.0`: Largest steering angle in degrees.
- `lateral_grip: float = 8.0`: How strongly sideways sliding is cancelled, per second.
- `rolling_resistance: float = 0.3`: Forward speed lost per second, as a fraction of the speed.
- `ground_mask: int = 1` (@export_flags_3d_physics): Physics layers the wheel rays test.
- `use_input_actions: bool = true`: Read throttle and steering from the ui actions. Turn off to drive from code.

### Methods

- `static suspension_force(compression: float, compression_speed: float, stiffness: float, damping: float, mass_share: float) -> float`: The spring force for a compression and compression speed (per wheel, before the mass share); never negative.
- `static lateral_force(side_speed: float, grip: float, mass_share: float) -> float`: The sideways force that cancels `side_speed` for a wheel carrying `mass_share` kilograms.
- `set_controls(throttle: float, steer: float) -> void`: Sets throttle (-1 reverse to 1 forward) and steering (-1 left to 1 right).
- `get_wheel_count() -> int`: Number of wheels.
- `is_wheel_grounded(index: int) -> bool`: True when wheel `index` touched the ground in the last physics frame.
- `get_wheel_compression(index: int) -> float`: Spring compression of wheel `index` in the last physics frame, in meters.
- `grounded_wheel_count() -> int`: How many wheels touched the ground in the last physics frame.
- `get_forward_speed() -> float`: Speed along the body's forward axis (-Z), in meters per second.

## Usage

```gdscript
extends Node3D

@onready var car: BaltorRaycastVehicle = $Car


func _ready() -> void:
	car.use_input_actions = false


func _physics_process(_delta: float) -> void:
	var throttle: float = Input.get_axis("ui_down", "ui_up")
	var steer: float = Input.get_axis("ui_left", "ui_right")
	car.set_controls(throttle, steer)
```

## Example scene

`example.tscn` drops the vehicle with a box chassis onto a large static ground with a camera.

## Tests

From the project root:

```sh
godot --headless --path . --script res://baltor/godot_components/raycast_vehicle_3d/run_tests.gd -- res://baltor/godot_components/raycast_vehicle_3d/tests
```

The runner prints one line per test and ends with `BALTOR_TESTS passed=<n> failed=0` when every test passes; its exit code is 0 only then. `python3 -m unittest test_package` checks the script against `component.json` without an engine.

## Limits

Arcade model: no engine torque curve, gears, tire slip curves or differential; wheel meshes are not moved. Grip is linear in sideways speed. The chassis collision shape must sit above the wheel points. Tested on flat ground in headless Godot physics. Verified with Godot 4.7.2 headless; written against the Godot 4.3 API.
