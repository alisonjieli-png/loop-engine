class_name BaltorTraumaShake2D
extends Node
## Trauma-based screen shake for a Camera2D, driven by smooth noise.
##
## Trauma is a value from 0 to 1 that events add to and that decays linearly over time. The visible shake is
## trauma raised to [member exponent], so small hits stay subtle and large hits stand out. Each frame the camera's
## offset and rotation move by up to [member max_offset] and [member max_roll_degrees] times the shake. The
## displacement comes from a FastNoiseLite sampled at the elapsed time times [member frequency], with one noise
## row each for x, y and roll, so the motion is smooth and repeats exactly for the same [member noise_seed]. When
## trauma reaches zero the camera returns to the offset and rotation it had when the shake started.

## Emitted when trauma rises above zero from rest.
signal shake_started
## Emitted when trauma returns to zero and the camera is restored.
signal shake_finished

## The Camera2D to shake; by default the parent.
@export var target_path: NodePath = NodePath("..")
## Largest offset in pixels at full shake.
@export var max_offset: Vector2 = Vector2(24, 16)
## Largest roll in degrees at full shake.
@export var max_roll_degrees: float = 4.0
## Trauma lost per second.
@export var decay_per_second: float = 0.9
## Shake = trauma ^ exponent.
@export_range(1.0, 4.0) var exponent: float = 2.0
## Noise samples per second; higher shakes faster.
@export var frequency: float = 18.0
## Seed of the noise; the same seed gives the same motion.
@export var noise_seed: int = 7:
	set(value):
		noise_seed = value
		if _noise != null:
			_noise.seed = value

var _noise: FastNoiseLite = null
var _trauma: float = 0.0
var _time: float = 0.0
var _base_offset: Vector2 = Vector2.ZERO
var _base_rotation: float = 0.0
var _shaking: bool = false


func _init() -> void:
	_noise = FastNoiseLite.new()
	_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX
	_noise.frequency = 1.0
	_noise.seed = noise_seed


func _process(delta: float) -> void:
	advance(delta)


## Adds [param amount] to the trauma (clamped to 0..1). Negative amounts reduce it.
func add_trauma(amount: float) -> void:
	set_trauma(_trauma + amount)


## Sets the trauma (clamped to 0..1), starting or finishing the shake as needed.
func set_trauma(value: float) -> void:
	var clamped: float = clampf(value, 0.0, 1.0)
	if clamped > 0.0 and not _shaking:
		_begin()
	_trauma = clamped
	if _trauma <= 0.0 and _shaking:
		_finish()


## Current trauma from 0 to 1.
func get_trauma() -> float:
	return _trauma


## Current shake strength: trauma ^ exponent.
func get_shake() -> float:
	return pow(_trauma, exponent)


## The camera offset displacement at [param time] seconds for the current shake.
func offset_at(time: float) -> Vector2:
	var shake: float = get_shake()
	return Vector2(max_offset.x * shake * _sample(0, time), max_offset.y * shake * _sample(1, time))


## The roll in radians at [param time] seconds for the current shake.
func roll_at(time: float) -> float:
	return deg_to_rad(max_roll_degrees) * get_shake() * _sample(2, time)


## The Camera2D at [member target_path], or null.
func get_target_camera() -> Camera2D:
	return get_node_or_null(target_path) as Camera2D


## Advances the shake by [param delta] seconds: trauma decays and the camera moves. Called every frame.
func advance(delta: float) -> void:
	if not _shaking:
		return
	_time += delta
	set_trauma(_trauma - decay_per_second * delta)
	if not _shaking:
		return
	var camera: Camera2D = get_target_camera()
	if camera != null:
		camera.offset = _base_offset + offset_at(_time)
		camera.rotation = _base_rotation + roll_at(_time)


func _sample(channel: int, time: float) -> float:
	return clampf(_noise.get_noise_2d(time * frequency, channel * 100.0), -1.0, 1.0)


func _begin() -> void:
	_shaking = true
	_time = 0.0
	var camera: Camera2D = get_target_camera()
	if camera != null:
		_base_offset = camera.offset
		_base_rotation = camera.rotation
	shake_started.emit()


func _finish() -> void:
	_shaking = false
	var camera: Camera2D = get_target_camera()
	if camera != null:
		camera.offset = _base_offset
		camera.rotation = _base_rotation
	shake_finished.emit()
