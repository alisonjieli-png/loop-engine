extends SceneTree
# What Godot itself makes of one .tscn or .tres in a project, written as JSON for the native verifier.
#   godot --headless --path PROJECT --script res://inspect_scene.gd -- OUTPUT.json res://path/to/file
# A scene is loaded and instantiated: every node path and class, every signal connection, and the material
# override of each mesh surface 0. A resource is loaded: its class, name and texture slot.


func _initialize() -> void:
	_run()


func _run() -> void:
	await process_frame
	var args := OS.get_cmdline_user_args()
	var facts := {"path": args[1]}
	var resource = ResourceLoader.load(args[1])
	facts["loaded"] = resource != null
	if resource is PackedScene:
		var instance: Node = resource.instantiate()
		facts["instantiated"] = instance != null
		if instance != null:
			root.add_child(instance)
			await process_frame
			var nodes := []
			var connections := []
			_walk(instance, instance, nodes, connections)
			facts["nodes"] = nodes
			facts["connections"] = connections
			root.remove_child(instance)
			instance.free()
	elif resource != null:
		facts["class"] = resource.get_class()
		facts["resource_name"] = String(resource.resource_name)
		if resource is BaseMaterial3D:
			facts["albedo_texture"] = resource.albedo_texture != null
	var file := FileAccess.open(args[0], FileAccess.WRITE)
	file.store_string(JSON.stringify(facts))
	file.close()
	quit(0)


func _walk(node: Node, base: Node, nodes: Array, connections: Array) -> void:
	var row := {"path": String(base.get_path_to(node)), "class": node.get_class(),
		"scene_file": node.scene_file_path}
	if node is MeshInstance3D:
		var material: Material = node.get_surface_override_material(0) if node.mesh != null \
				and node.mesh.get_surface_count() > 0 else null
		row["material"] = String(material.resource_name) if material != null else null
	nodes.append(row)
	for signal_row in node.get_signal_list():
		for connection in node.get_signal_connection_list(signal_row["name"]):
			var target: Object = connection["callable"].get_object()
			if target is Node and base.is_ancestor_of(target) or target == base:
				connections.append({"from": String(base.get_path_to(node)), "signal": String(signal_row["name"]),
					"to": String(base.get_path_to(target)), "method": String(connection["callable"].get_method())})
	for child in node.get_children():
		_walk(child, base, nodes, connections)
