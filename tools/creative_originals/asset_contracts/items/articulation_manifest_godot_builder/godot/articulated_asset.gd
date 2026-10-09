extends Node3D
## Loads a glTF and its articulation_manifest/v1 at run time and moves each joint within its limits.
##
## load_asset() binds every joint to the generated scene node it names. set_joint() clamps a value to the joint's
## limits and sets the node to BASE * M(value): a hinge turns by value degrees about its axis through its pivot, a
## slider moves value metres along its axis (axis and pivot in the node's own frame). build_animation_player() adds
## one clip per non-zero limit, <joint>_lower and <joint>_upper, from the modelled pose to that limit in one second.
## save_scene() packs everything into a scene that rebinds its joints in _ready(), without the glTF.

const TYPES := {"hinge": 360.0, "slider": 1000.0}

@export_multiline var manifest_text := ""
@export var joint_paths := {}
@export var joint_bases := {}

var joints := {}
var errors: Array = []


func _ready() -> void:
	if joints.is_empty() and manifest_text != "" and not joint_paths.is_empty():
		_bind()


func load_asset(gltf_path: String, manifest_path: String) -> int:
	errors.clear()
	joints.clear()
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	var error := document.append_from_file(gltf_path, state)
	if error != OK:
		errors.append("the glTF did not load: %s" % error_string(error))
		return error
	var scene := document.generate_scene(state)
	scene.name = "Model"
	add_child(scene)
	manifest_text = FileAccess.get_file_as_string(manifest_path)
	var manifest = JSON.parse_string(manifest_text)
	if typeof(manifest) != TYPE_DICTIONARY or manifest.get("record_type") != "articulation_manifest/v1" \
			or typeof(manifest.get("joints")) != TYPE_ARRAY:
		errors.append("the manifest is not an articulation_manifest/v1 object with a joints list")
		return ERR_INVALID_DATA
	var gltf_nodes := state.get_nodes()
	var paths := {}
	var by_name := {}
	for index in gltf_nodes.size():
		var parent: int = gltf_nodes[index].parent
		var own := String(gltf_nodes[index].resource_name)
		paths[index] = own if parent < 0 or not paths.has(parent) else paths[parent] + "/" + own
		var original: String = gltf_nodes[index].original_name
		if not by_name.has(original):
			by_name[original] = []
		by_name[original].append(index)
	var used := {}
	var names := {}
	for joint in manifest["joints"]:
		var problem := _problem(joint, by_name, used, names)
		if problem != "":
			errors.append(problem)
			continue
		var index: int = by_name[joint["node"]][0]
		var node := scene.get_node_or_null(NodePath(paths[index])) as Node3D
		if node == null:
			node = scene.find_child(String(gltf_nodes[index].resource_name), true, false) as Node3D
		if node == null:
			errors.append("joint %s: node %s is not in the generated scene" % [joint["name"], joint["node"]])
			continue
		used[joint["node"]] = joint["name"]
		names[joint["name"]] = true
		joint_paths[joint["name"]] = get_path_to(node)
		joint_bases[joint["name"]] = node.transform
	if not errors.is_empty():
		return ERR_INVALID_DATA
	_bind()
	return OK if errors.is_empty() else ERR_INVALID_DATA


func _problem(joint, by_name: Dictionary, used: Dictionary, names: Dictionary) -> String:
	if typeof(joint) != TYPE_DICTIONARY or typeof(joint.get("name")) != TYPE_STRING or joint["name"] == "":
		return "a joint has no name"
	var name: String = joint["name"]
	if names.has(name):
		return "joint %s: the name is used twice" % name
	if not TYPES.has(joint.get("type")):
		return "joint %s: type is hinge or slider" % name
	if not by_name.has(joint.get("node")):
		return "joint %s: no node named %s" % [name, joint.get("node")]
	if by_name[joint["node"]].size() != 1:
		return "joint %s: %d nodes are named %s" % [name, by_name[joint["node"]].size(), joint["node"]]
	if used.has(joint["node"]):
		return "joint %s: node %s already moves with %s" % [name, joint["node"], used[joint["node"]]]
	var axis = joint.get("axis")
	if typeof(axis) != TYPE_ARRAY or axis.size() != 3 \
			or absf(Vector3(axis[0], axis[1], axis[2]).length() - 1.0) > 0.001:
		return "joint %s: the axis is not a unit vector" % name
	var pivot = joint.get("pivot", [0.0, 0.0, 0.0])
	if typeof(pivot) != TYPE_ARRAY or pivot.size() != 3:
		return "joint %s: the pivot is not three numbers" % name
	var limits = joint.get("limits")
	var bound: float = TYPES[joint["type"]]
	if typeof(limits) != TYPE_ARRAY or limits.size() != 2:
		return "joint %s: limits are [lower, upper]" % name
	var lower := float(limits[0])
	var upper := float(limits[1])
	var rest := float(joint.get("rest", 0.0))
	if not (-bound <= lower and lower < upper and upper <= bound and lower <= rest and rest <= upper):
		return "joint %s: limits must have lower < upper within +-%s, around the rest value" % [name, bound]
	return ""


func _bind() -> void:
	joints.clear()
	var manifest = JSON.parse_string(manifest_text)
	for joint in manifest["joints"]:
		var name: String = joint["name"]
		if not joint_paths.has(name):
			continue
		var node := get_node_or_null(joint_paths[name]) as Node3D
		if node == null:
			errors.append("joint %s: node path %s is missing" % [name, joint_paths[name]])
			continue
		var pivot = joint.get("pivot", [0.0, 0.0, 0.0])
		joints[name] = {"node": node, "type": joint["type"],
			"axis": Vector3(joint["axis"][0], joint["axis"][1], joint["axis"][2]).normalized(),
			"pivot": Vector3(pivot[0], pivot[1], pivot[2]), "lower": float(joint["limits"][0]),
			"upper": float(joint["limits"][1]), "rest": float(joint.get("rest", 0.0)),
			"base": joint_bases[name], "value": 0.0}
	reset_joints()


func joint_names() -> Array:
	return joints.keys()


func joint_limits(name: String) -> Array:
	return [joints[name]["lower"], joints[name]["upper"]]


func joint_node(name: String) -> Node3D:
	return joints[name]["node"]


func joint_pivot(name: String) -> Vector3:
	return joints[name]["pivot"]


func get_joint(name: String) -> float:
	return joints[name]["value"]


func motion(name: String, value: float) -> Transform3D:
	var joint: Dictionary = joints[name]
	if joint["type"] == "slider":
		return Transform3D(Basis.IDENTITY, joint["axis"] * value)
	var turn := Transform3D(Basis(joint["axis"], deg_to_rad(value)), Vector3.ZERO)
	return Transform3D(Basis.IDENTITY, joint["pivot"]) * turn * Transform3D(Basis.IDENTITY, -joint["pivot"])


func set_joint(name: String, value: float) -> float:
	var joint: Dictionary = joints[name]
	var clamped := clampf(value, joint["lower"], joint["upper"])
	joint["value"] = clamped
	joint["node"].transform = joint["base"] * motion(name, clamped)
	return clamped


func reset_joints() -> void:
	for name in joints:
		set_joint(name, joints[name]["rest"])


func build_animation_player(steps: int = 10) -> AnimationPlayer:
	var player := AnimationPlayer.new()
	player.name = "JointPlayer"
	var library := AnimationLibrary.new()
	for name in joints:
		var joint: Dictionary = joints[name]
		for label in ["lower", "upper"]:
			var limit: float = joint[label]
			if is_zero_approx(limit):
				continue
			var animation := Animation.new()
			animation.length = 1.0
			var path := get_path_to(joint["node"])
			var position_track := animation.add_track(Animation.TYPE_POSITION_3D)
			animation.track_set_path(position_track, path)
			var rotation_track := animation.add_track(Animation.TYPE_ROTATION_3D)
			animation.track_set_path(rotation_track, path)
			for step in steps + 1:
				var time := float(step) / steps
				var local: Transform3D = joint["base"] * motion(name, limit * time)
				animation.position_track_insert_key(position_track, time, local.origin)
				animation.rotation_track_insert_key(rotation_track, time, local.basis.get_rotation_quaternion())
			library.add_animation("%s_%s" % [name, label], animation)
	player.add_animation_library("", library)
	add_child(player)
	return player


func save_scene(path: String) -> int:
	reset_joints()
	_own(self)
	var packed := PackedScene.new()
	var error := packed.pack(self)
	if error != OK:
		return error
	return ResourceSaver.save(packed, path)


func _own(node: Node) -> void:
	for child in node.get_children():
		child.owner = self
		_own(child)
