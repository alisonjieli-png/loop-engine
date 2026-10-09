extends Node
## Base script for Baltor component tests.
##
## The shared runner (run_tests.gd) creates a fresh instance of a test script for every method whose name
## starts with "test_", adds it to the scene tree, awaits the method and then collects the failures these
## helpers recorded. A test script extends this file by relative path: extends "../baltor_test.gd".
## Nodes a test adds with add_child() are freed with the test; other objects can be passed to autofree().

## Engine and script errors this test expects to cause. The runner compares the count on Godot 4.5 and later.
var expected_errors: int = 0

var _failures: PackedStringArray = PackedStringArray()
var _assertions: int = 0
var _tracked: Array[Object] = []
var _signal_logs: Dictionary = {}


## Records one emission per signal call; connected by watch_signals().
class _SignalLog extends RefCounted:
	var emissions: Dictionary = {}

	func record0(signal_name: StringName) -> void:
		_add(signal_name, [])

	func record1(a: Variant, signal_name: StringName) -> void:
		_add(signal_name, [a])

	func record2(a: Variant, b: Variant, signal_name: StringName) -> void:
		_add(signal_name, [a, b])

	func record3(a: Variant, b: Variant, c: Variant, signal_name: StringName) -> void:
		_add(signal_name, [a, b, c])

	func record4(a: Variant, b: Variant, c: Variant, d: Variant, signal_name: StringName) -> void:
		_add(signal_name, [a, b, c, d])

	func record5(a: Variant, b: Variant, c: Variant, d: Variant, e: Variant, signal_name: StringName) -> void:
		_add(signal_name, [a, b, c, d, e])

	func record6(a: Variant, b: Variant, c: Variant, d: Variant, e: Variant, f: Variant,
			signal_name: StringName) -> void:
		_add(signal_name, [a, b, c, d, e, f])

	func _add(signal_name: StringName, arguments: Array) -> void:
		if not emissions.has(signal_name):
			emissions[signal_name] = []
		(emissions[signal_name] as Array).append(arguments)


## Passes when [param condition] is true.
func assert_true(condition: bool, message: String = "") -> bool:
	return _check(condition, "expected true", message)


## Passes when [param condition] is false.
func assert_false(condition: bool, message: String = "") -> bool:
	return _check(not condition, "expected false", message)


## Passes when the values are equal. Integers and floats compare by value, String and StringName by text,
## and arrays and dictionaries element by element.
func assert_eq(actual: Variant, expected: Variant, message: String = "") -> bool:
	var passed: bool = values_equal(actual, expected)
	return _check(passed, "" if passed else "expected %s but got %s" % [_show(expected), _show(actual)], message)


## Passes when the values differ.
func assert_ne(actual: Variant, unexpected: Variant, message: String = "") -> bool:
	var passed: bool = not values_equal(actual, unexpected)
	return _check(passed, "" if passed else "expected a value other than %s" % _show(unexpected), message)


## Passes when the numbers, vectors, colours, transforms or arrays differ by at most [param tolerance].
func assert_almost_eq(actual: Variant, expected: Variant, tolerance: float = 0.0001, message: String = "") -> bool:
	var difference: float = difference_between(actual, expected)
	var passed: bool = difference >= 0.0 and difference <= tolerance
	return _check(passed, "" if passed else "expected %s within %s but got %s" % [_show(expected), tolerance,
			_show(actual)], message)


## Passes when [param value] is null or a freed object.
func assert_null(value: Variant, message: String = "") -> bool:
	var empty: bool = value == null or (typeof(value) == TYPE_OBJECT and not is_instance_valid(value))
	return _check(empty, "" if empty else "expected null but got %s" % _show(value), message)


## Passes when [param value] is neither null nor a freed object.
func assert_not_null(value: Variant, message: String = "") -> bool:
	var empty: bool = value == null or (typeof(value) == TYPE_OBJECT and not is_instance_valid(value))
	return _check(not empty, "expected a value but got null", message)


## Passes when the number [param actual] is greater than [param threshold].
func assert_gt(actual: float, threshold: float, message: String = "") -> bool:
	return _check(actual > threshold, "expected more than %s but got %s" % [threshold, actual], message)


## Passes when the number [param actual] is less than [param threshold].
func assert_lt(actual: float, threshold: float, message: String = "") -> bool:
	return _check(actual < threshold, "expected less than %s but got %s" % [threshold, actual], message)


## Passes when [param low] <= [param actual] <= [param high].
func assert_between(actual: float, low: float, high: float, message: String = "") -> bool:
	return _check(actual >= low and actual <= high, "expected %s..%s but got %s" % [low, high, actual], message)


## Passes when an array or packed array holds [param item], a dictionary has the key, or a string contains it.
func assert_has(container: Variant, item: Variant, message: String = "") -> bool:
	var found: bool = false
	match typeof(container):
		TYPE_DICTIONARY:
			found = (container as Dictionary).has(item)
		TYPE_STRING, TYPE_STRING_NAME:
			found = str(container).contains(str(item))
		TYPE_ARRAY:
			for element: Variant in container:
				if values_equal(element, item):
					found = true
					break
		_:
			if typeof(container) >= TYPE_PACKED_BYTE_ARRAY:
				found = container.has(item)
	return _check(found, "" if found else "expected %s to hold %s" % [_show(container), _show(item)], message)


## Records a failure with [param message].
func fail(message: String) -> void:
	_check(false, "failed", message)


## Connects to every signal of [param emitter] (script signals when it has a script) so the emissions can be
## counted and read with signal_emissions().
func watch_signals(emitter: Object) -> void:
	var key: int = emitter.get_instance_id()
	if _signal_logs.has(key):
		return
	var signal_log := _SignalLog.new()
	_signal_logs[key] = signal_log
	var listed: Array[Dictionary] = []
	var script := emitter.get_script() as Script
	if script != null:
		listed = script.get_script_signal_list()
	else:
		listed = emitter.get_signal_list()
	for entry: Dictionary in listed:
		var count: int = (entry["args"] as Array).size()
		var signal_name: StringName = entry["name"]
		if count <= 6:
			emitter.connect(signal_name, Callable(signal_log, "record%d" % count).bind(signal_name))


## The argument arrays of every emission of [param signal_name] seen since watch_signals(), oldest first.
func signal_emissions(emitter: Object, signal_name: StringName) -> Array:
	var signal_log: _SignalLog = _signal_logs.get(emitter.get_instance_id())
	if signal_log == null:
		fail("watch_signals() was not called for %s" % _show(emitter))
		return []
	return (signal_log.emissions.get(signal_name, []) as Array).duplicate()


## Passes when [param signal_name] was emitted exactly [param times] times since watch_signals().
func assert_signal_count(emitter: Object, signal_name: StringName, times: int, message: String = "") -> bool:
	var seen: int = signal_emissions(emitter, signal_name).size()
	return _check(seen == times, "expected %s %d times but saw %d" % [signal_name, times, seen], message)


## Passes when [param signal_name] was emitted at least once since watch_signals().
func assert_signal_emitted(emitter: Object, signal_name: StringName, message: String = "") -> bool:
	var seen: int = signal_emissions(emitter, signal_name).size()
	return _check(seen > 0, "expected %s to be emitted" % signal_name, message)


## Passes when [param signal_name] was not emitted since watch_signals().
func assert_signal_not_emitted(emitter: Object, signal_name: StringName, message: String = "") -> bool:
	var seen: int = signal_emissions(emitter, signal_name).size()
	return _check(seen == 0, "expected %s not to be emitted but saw %d" % [signal_name, seen], message)


## Frees [param value] after the test unless it is reference counted or already freed. Returns it.
func autofree(value: Variant) -> Variant:
	if typeof(value) == TYPE_OBJECT and value != null:
		_tracked.append(value)
	return value


## Waits for [param count] process frames.
func wait_frames(count: int) -> void:
	for _frame in range(count):
		await get_tree().process_frame


## Waits for [param count] physics frames.
func wait_physics_frames(count: int) -> void:
	for _frame in range(count):
		await get_tree().physics_frame


## The res:// path of [param relative] inside the package that holds this test (the folder above tests/).
func package_path(relative: String) -> String:
	var script := get_script() as Script
	return script.resource_path.get_base_dir().get_base_dir().path_join(relative)


## Value equality used by assert_eq().
static func values_equal(a: Variant, b: Variant) -> bool:
	var type_a: int = typeof(a)
	var type_b: int = typeof(b)
	if _is_number(type_a) and _is_number(type_b):
		return float(a) == float(b)
	if _is_text(type_a) and _is_text(type_b):
		return str(a) == str(b)
	if type_a != type_b:
		return false
	if type_a == TYPE_ARRAY:
		var left: Array = a
		var right: Array = b
		if left.size() != right.size():
			return false
		for index in range(left.size()):
			if not values_equal(left[index], right[index]):
				return false
		return true
	if type_a == TYPE_DICTIONARY:
		var left_map: Dictionary = a
		var right_map: Dictionary = b
		if left_map.size() != right_map.size():
			return false
		for key: Variant in left_map:
			if not right_map.has(key) or not values_equal(left_map[key], right_map[key]):
				return false
		return true
	return a == b


## The largest component difference between two comparable values, or -1.0 when they cannot be compared.
static func difference_between(a: Variant, b: Variant) -> float:
	var type_a: int = typeof(a)
	var type_b: int = typeof(b)
	if _is_number(type_a) and _is_number(type_b):
		return absf(float(a) - float(b))
	if type_a != type_b:
		return -1.0
	match type_a:
		TYPE_VECTOR2, TYPE_VECTOR3, TYPE_VECTOR4, TYPE_QUATERNION, TYPE_VECTOR2I, TYPE_VECTOR3I, TYPE_VECTOR4I:
			var gap: Variant = a - b
			return float(gap.length())
		TYPE_COLOR:
			var ca: Color = a
			var cb: Color = b
			return maxf(maxf(absf(ca.r - cb.r), absf(ca.g - cb.g)), maxf(absf(ca.b - cb.b), absf(ca.a - cb.a)))
		TYPE_RECT2:
			var ra: Rect2 = a
			var rb: Rect2 = b
			return maxf(ra.position.distance_to(rb.position), ra.size.distance_to(rb.size))
		TYPE_TRANSFORM2D:
			var ta: Transform2D = a
			var tb: Transform2D = b
			return maxf(maxf(ta.x.distance_to(tb.x), ta.y.distance_to(tb.y)), ta.origin.distance_to(tb.origin))
		TYPE_BASIS:
			var ba: Basis = a
			var bb: Basis = b
			return maxf(maxf(ba.x.distance_to(bb.x), ba.y.distance_to(bb.y)), ba.z.distance_to(bb.z))
		TYPE_TRANSFORM3D:
			var xa: Transform3D = a
			var xb: Transform3D = b
			return maxf(difference_between(xa.basis, xb.basis), xa.origin.distance_to(xb.origin))
	if type_a == TYPE_ARRAY or type_a >= TYPE_PACKED_BYTE_ARRAY:
		if a.size() != b.size():
			return -1.0
		var largest: float = 0.0
		for index in range(a.size()):
			var element: float = difference_between(a[index], b[index])
			if element < 0.0:
				return -1.0
			largest = maxf(largest, element)
		return largest
	return 0.0 if a == b else -1.0


## Called by the runner: the failures recorded so far, emptied afterwards.
func _baltor_take_failures() -> PackedStringArray:
	var taken: PackedStringArray = _failures
	_failures = PackedStringArray()
	return taken


## Called by the runner: how many assertions this test made.
func _baltor_assertion_count() -> int:
	return _assertions


## Called by the runner after the test: frees the objects passed to autofree().
func _baltor_cleanup() -> void:
	for value: Variant in _tracked:
		if not is_instance_valid(value) or value is RefCounted:
			continue
		var node := value as Node
		if node != null and node.is_inside_tree():
			node.queue_free()
		else:
			(value as Object).free()
	_tracked.clear()
	_signal_logs.clear()


func _check(passed: bool, detail: String, message: String) -> bool:
	_assertions += 1
	if not passed:
		_failures.append(detail if message.is_empty() else "%s (%s)" % [message, detail])
	return passed


static func _is_number(type: int) -> bool:
	return type == TYPE_INT or type == TYPE_FLOAT


static func _is_text(type: int) -> bool:
	return type == TYPE_STRING or type == TYPE_STRING_NAME


static func _show(value: Variant) -> String:
	var kind: int = typeof(value)
	var text: String = str(value) if kind in [TYPE_OBJECT, TYPE_ARRAY, TYPE_DICTIONARY] else var_to_str(value)
	return text if text.length() <= 160 else text.substr(0, 157) + "..."
