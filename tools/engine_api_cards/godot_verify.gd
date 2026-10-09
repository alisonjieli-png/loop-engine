extends SceneTree
## Ask the running engine about every class an expectations file lists, and write what it answered.
##
## godot --headless --script godot_verify.gd -- expectations.json results.json
##
## A class ClassDB registers: the class is known, its parent is the expected one, and every listed method, property,
## signal, integer constant and enumeration is the class's own (a property that overrides an ancestor's default is
## looked up with inheritance). A Variant type: the type is known, every listed method is callable on a value of the
## type, and every listed member can be read from one. A global scope: every listed function compiles in a script
## (with untyped arguments, one more argument for a variadic call, or constant arguments of the declared types for a
## function that needs constants such as preload), and every listed member is an engine singleton.

const RECORD_TYPE := "godot_class_check_results/v1"
const PROBE_TARGET := "res://probe_target.gd"
## A constant of each declared type, for the third probe shape; any other type gets null.
const CONSTANT_ARGUMENTS := {
	"String": "\"res://probe_target.gd\"", "StringName": "&\"probe\"", "NodePath": "^\"probe\"",
	"int": "1", "float": "1.0", "bool": "true",
}


func _init() -> void:
	var arguments := OS.get_cmdline_user_args()
	if arguments.size() != 2:
		printerr("usage: -- expectations.json results.json")
		quit(2)
		return
	var expected = JSON.parse_string(FileAccess.get_file_as_string(arguments[0]))
	if typeof(expected) != TYPE_DICTIONARY or not expected.has("classes"):
		printerr("the expectations file is not a JSON object with classes")
		quit(2)
		return
	var results := {}
	for entry in expected["classes"]:
		match entry["kind"]:
			"class":
				results[entry["name"]] = _object_class(entry)
			"builtin_type":
				results[entry["name"]] = _builtin_type(entry)
			"global_scope":
				results[entry["name"]] = _global_scope(entry)
			_:
				results[entry["name"]] = {"known": false, "error": "unknown kind"}
	var file := FileAccess.open(arguments[1], FileAccess.WRITE)
	file.store_string(JSON.stringify({"record_type": RECORD_TYPE, "version": Engine.get_version_info(),
			"classes": results}, "", true))
	file.close()
	quit(0)


func _names(rows: Array) -> Dictionary:
	var names := {}
	for row in rows:
		names[row["name"]] = true
	return names


func _missing(expected: Array, known: Dictionary) -> Array:
	var missing := []
	for name in expected:
		if not known.has(name):
			missing.append(name)
	return missing


## The element prefixes of the class's array properties (an array property names "Label,prefix" as its class name),
## so a documented element property such as point_{index}/position is known to belong to the array point_.
func _array_prefixes(name: String) -> Array:
	var prefixes := []
	for row in ClassDB.class_get_property_list(name, false):
		var label := String(row["class_name"])
		if row["usage"] & PROPERTY_USAGE_ARRAY and not label.is_empty():
			prefixes.append(label.get_slice(",", 1) if label.contains(",") else label)
	return prefixes


## The property names of a new instance of a container node holding one child, so a per-child property such as
## tab_{index}/title is read as tab_0/title. Empty for a class that is not an instantiable node.
func _container_element_names(name: String) -> Dictionary:
	if not ClassDB.can_instantiate(name) or not ClassDB.is_parent_class(name, "Node"):
		return {}
	var node: Node = ClassDB.instantiate(name)
	node.add_child(Control.new())
	var names := _names(node.get_property_list())
	node.free()
	return names


## The object that answers has_setting for a settings class: its engine singleton, or a new instance of it.
func _settings_holder(name: String) -> Object:
	if not ClassDB.class_has_method(name, "has_setting", false):
		return null
	if Engine.has_singleton(name):
		return Engine.get_singleton(name)
	return ClassDB.instantiate(name) if ClassDB.can_instantiate(name) else null


## The documented properties ClassDB does not list as the class's own: an element of one of its arrays, or a
## setting its settings object holds. What neither route confirms is missing.
func _members(name: String, members: Array, confirmed: Dictionary) -> Array:
	var own := _names(ClassDB.class_get_property_list(name, true))
	var prefixes := _array_prefixes(name)
	var holder: Object = null
	var looked_for_holder := false
	var container_names = null
	var missing := []
	for member in members:
		if own.has(member):
			confirmed["static"] += 1
			continue
		var element := false
		for prefix in prefixes:
			if member.begins_with(prefix + "{index}"):
				element = true
		if element:
			confirmed["array_element"] += 1
			continue
		if member.contains("{index}"):
			if container_names == null:
				container_names = _container_element_names(name)
			if container_names.has(member.replace("{index}", "0")):
				confirmed["container_element"] += 1
				continue
		if not looked_for_holder:
			holder = _settings_holder(name)
			looked_for_holder = true
		if holder != null and holder.has_setting(member):
			confirmed["setting"] += 1
			continue
		missing.append(member)
	return missing


func _object_class(entry: Dictionary) -> Dictionary:
	var name: String = entry["name"]
	if not ClassDB.class_exists(name):
		return {"known": false}
	var every_property := _names(ClassDB.class_get_property_list(name, false))
	var constants := {}
	for constant in ClassDB.class_get_integer_constant_list(name, true):
		constants[constant] = true
	var enums := {}
	for enum_name in ClassDB.class_get_enum_list(name, true):
		enums[enum_name] = true
	var confirmed := {"static": 0, "array_element": 0, "container_element": 0, "setting": 0}
	return {
		"known": true,
		"parent": String(ClassDB.get_parent_class(name)),
		"missing": {
			"methods": _missing(entry["methods"], _names(ClassDB.class_get_method_list(name, true))),
			"members": _members(name, entry["members"], confirmed),
			"overridden_members": _missing(entry["overridden_members"], every_property),
			"signals": _missing(entry["signals"], _names(ClassDB.class_get_signal_list(name, true))),
			"constants": _missing(entry["constants"], constants),
			"enums": _missing(entry["enums"], enums),
		},
		"members_confirmed_by": confirmed,
	}


func _type_index(name: String) -> int:
	for index in range(TYPE_MAX):
		if type_string(index) == name:
			return index
	return -1


func _readable(value: Variant, member: String) -> bool:
	var _value = value[member]
	return true


func _builtin_type(entry: Dictionary) -> Dictionary:
	var index := _type_index(entry["name"])
	if index < 0:
		return {"known": false}
	var value: Variant = type_convert(null, index)
	var missing_methods := []
	for method in entry["methods"]:
		if not Callable.create(value, StringName(method)).is_valid():
			missing_methods.append(method)
	var missing_members := []
	for member in entry["members"]:
		if not _readable(value, member):
			missing_members.append(member)
	return {"known": true, "missing": {"methods": missing_methods, "members": missing_members}}


func _compiles(source: String) -> bool:
	var script := GDScript.new()
	script.source_code = source
	return script.reload() == OK


func _call_source(name: String, count: int, constants: Array) -> String:
	var names := []
	for index in range(count):
		names.append("a%d" % index)
	var arguments: Array = constants if not constants.is_empty() else names
	return "extends RefCounted\nfunc probe(%s):\n\t%s(%s)\n" % [", ".join(names), name, ", ".join(arguments)]


func _function_compiles(function: Dictionary) -> bool:
	var required := 0
	var constants := []
	for parameter in function["params"]:
		if parameter.has("default"):
			break
		required += 1
		constants.append(CONSTANT_ARGUMENTS.get(parameter["type"], "null"))
	return (_compiles(_call_source(function["name"], required, []))
			or _compiles(_call_source(function["name"], required + 1, []))
			or (required > 0 and _compiles(_call_source(function["name"], required, constants))))


func _global_scope(entry: Dictionary) -> Dictionary:
	var missing_functions := []
	for function in entry["functions"]:
		if not _function_compiles(function):
			missing_functions.append(function["name"])
	var missing_members := []
	for member in entry["members"]:
		if not Engine.has_singleton(member):
			missing_members.append(member)
	return {"known": true, "missing": {"methods": missing_functions, "members": missing_members}}
