extends SceneTree
## Headless test runner for Baltor Godot components.
##
## godot --headless --path PROJECT --script res://baltor/godot_components/ID/run_tests.gd -- FOLDER_OR_FILE ...
##
## Finds every test_*.gd file under the given res:// folders, then runs each method whose name starts with
## "test_" on a fresh instance of its script, added to the scene tree. Before and after a test the methods
## before_each() and after_each() run when the script defines them. Test methods may await.
## A test fails when an assertion of baltor_test.gd fails, when it makes no assertion, when it does not finish
## within the time limit, when it leaves orphan nodes behind, or (Godot 4.5 and later, through a Logger) when
## it causes more engine or script errors than its expected_errors property allows.
## Prints "ok LABEL" or "FAIL LABEL: REASON" for each test and ends with one summary line:
##     BALTOR_TESTS passed=<n> failed=<m>
## The exit code is 0 only when no test failed and at least one test passed.
## Options after "--": --filter=TEXT runs only tests whose label contains TEXT; --timeout=SECONDS (default 20).

const SUMMARY_PREFIX: String = "BALTOR_TESTS"
const DEFAULT_TIMEOUT_SECONDS: float = 20.0
const _CATCHER_SOURCE: String = (
	"extends Logger\n"
	+ "var entries: Array[String] = []\n"
	+ "var lock: Mutex = Mutex.new()\n"
	+ "func _log_error(_function: String, file: String, line: int, code: String, rationale: String,"
	+ " _editor_notify: bool, error_type: int, _script_backtraces: Array[ScriptBacktrace]) -> void:\n"
	+ "\tif error_type == 1:\n"
	+ "\t\treturn\n"
	+ "\tlock.lock()\n"
	+ "\tentries.append(\"%s (%s:%d)\" % [code if rationale.is_empty() else code + \": \" + rationale, file, line])\n"
	+ "\tlock.unlock()\n"
	+ "func _log_message(_message: String, _error: bool) -> void:\n"
	+ "\tpass\n"
	+ "func snapshot() -> Array[String]:\n"
	+ "\tlock.lock()\n"
	+ "\tvar copy: Array[String] = entries.duplicate()\n"
	+ "\tlock.unlock()\n"
	+ "\treturn copy\n"
)

var _passed: int = 0
var _failed: int = 0
var _filter: String = ""
var _timeout_msec: int = int(DEFAULT_TIMEOUT_SECONDS * 1000.0)
var _catcher: Object = null


func _initialize() -> void:
	_install_catcher()
	_main()


func _main() -> void:
	await process_frame
	var targets: PackedStringArray = PackedStringArray()
	for argument: String in OS.get_cmdline_user_args():
		if argument.begins_with("--filter="):
			_filter = argument.trim_prefix("--filter=")
		elif argument.begins_with("--timeout="):
			_timeout_msec = int(argument.trim_prefix("--timeout=").to_float() * 1000.0)
		else:
			targets.append(argument)
	if _catcher == null:
		print("note: this engine has no Logger class (Godot 4.4 or earlier); engine errors are not counted")
	var scripts: PackedStringArray = PackedStringArray()
	for target: String in targets:
		_collect(target, scripts)
	scripts.sort()
	if targets.is_empty():
		print("usage: godot --headless --path PROJECT --script res://.../run_tests.gd -- res://tests_folder")
	elif scripts.is_empty():
		_record(", ".join(targets), PackedStringArray(["no test_*.gd script was found"]))
	for path: String in scripts:
		await _run_script(path)
	_finish()


func _collect(path: String, into: PackedStringArray) -> void:
	if path.ends_with(".gd"):
		if FileAccess.file_exists(path):
			if not into.has(path):
				into.append(path)
		else:
			_record(path, PackedStringArray(["the test script does not exist"]))
		return
	var directory := DirAccess.open(path)
	if directory == null:
		_record(path, PackedStringArray(["the folder does not exist"]))
		return
	for file_name: String in directory.get_files():
		if file_name.begins_with("test_") and file_name.ends_with(".gd"):
			var full_path: String = path.path_join(file_name)
			if not into.has(full_path):
				into.append(full_path)
	for folder: String in directory.get_directories():
		if not folder.begins_with("."):
			_collect(path.path_join(folder), into)


func _run_script(path: String) -> void:
	var script := load(path) as GDScript
	if script == null or not script.can_instantiate():
		_record(path, PackedStringArray(["the script did not load or compile"]))
		return
	var names: PackedStringArray = PackedStringArray()
	for method: Dictionary in script.get_script_method_list():
		var method_name: String = method["name"]
		if not method_name.begins_with("test_") or names.has(method_name):
			continue
		names.append(method_name)
		if (method["args"] as Array).size() > 0:
			_record(path + "::" + method_name, PackedStringArray(["a test method takes no arguments"]))
	if names.is_empty():
		_record(path, PackedStringArray(["the script has no test_ method"]))
		return
	for method_name: String in names:
		var label: String = path + "::" + method_name
		if not _filter.is_empty() and not label.contains(_filter):
			continue
		await _run_test(script, label, method_name)


func _run_test(script: GDScript, label: String, method_name: String) -> void:
	var errors_before: int = _errors().size()
	var orphans_before: int = _orphan_count()
	var problems: PackedStringArray = PackedStringArray()
	var instance: Object = script.new()
	var node := instance as Node
	if node != null:
		root.add_child(node)
	for step: String in ["before_each", method_name, "after_each"]:
		if step != method_name and not instance.has_method(step):
			continue
		var finished: bool = await _call_bounded(instance, step)
		if not finished:
			problems.append("%s did not finish within %d ms" % [step, _timeout_msec])
			break
	var expected_errors: int = 0
	if instance.has_method("_baltor_take_failures"):
		problems.append_array(instance.call("_baltor_take_failures"))
		if problems.is_empty() and int(instance.call("_baltor_assertion_count")) == 0:
			problems.append("the test made no assertion")
		expected_errors = int(instance.get("expected_errors"))
		instance.call("_baltor_cleanup")
	if node != null:
		node.queue_free()
	elif not (instance is RefCounted):
		instance.free()
	instance = null
	node = null
	await process_frame
	await process_frame
	if _catcher != null:
		var new_errors: Array = _errors().slice(errors_before)
		if new_errors.size() != expected_errors:
			problems.append("%d engine or script errors where %d were expected: %s"
					% [new_errors.size(), expected_errors, " | ".join(PackedStringArray(new_errors.slice(0, 3)))])
	var leaked: int = _orphan_count() - orphans_before
	if leaked > 0:
		problems.append("%d orphan nodes were left behind" % leaked)
	_record(label, problems)


func _call_bounded(target: Object, method: String) -> bool:
	var result: Variant = target.call(method)
	if typeof(result) != TYPE_OBJECT or not is_instance_valid(result):
		return true
	var state: Object = result
	if state.get_class() != "GDScriptFunctionState":
		return true
	var done: Array[bool] = [false]
	state.connect("completed", func(_value: Variant) -> void: done[0] = true)
	var started: int = Time.get_ticks_msec()
	while not done[0]:
		if Time.get_ticks_msec() - started > _timeout_msec:
			return false
		await process_frame
	return true


func _record(label: String, problems: PackedStringArray) -> void:
	if problems.is_empty():
		_passed += 1
		print("ok %s" % label)
	else:
		_failed += 1
		print("FAIL %s: %s" % [label, "; ".join(problems)])


func _install_catcher() -> void:
	if not ClassDB.class_exists("Logger") or not OS.has_method("add_logger"):
		return
	var catcher_script := GDScript.new()
	catcher_script.source_code = _CATCHER_SOURCE
	if catcher_script.reload() != OK:
		return
	_catcher = catcher_script.new()
	OS.call("add_logger", _catcher)


func _errors() -> Array[String]:
	if _catcher == null:
		return []
	return _catcher.call("snapshot")


func _orphan_count() -> int:
	return int(Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT))


func _finish() -> void:
	if _catcher != null:
		OS.call("remove_logger", _catcher)
		_catcher = null
	print("%s passed=%d failed=%d" % [SUMMARY_PREFIX, _passed, _failed])
	quit(0 if _failed == 0 and _passed > 0 else 1)
