extends SceneTree
# What Godot itself reads from glTF files, written as JSON for the asset_contracts native verifier.
#   godot --headless --path PROJECT --script res://inspect_gltf.gd -- OUTPUT.json FILE...
# For each file: the GLTFDocument load result, the GLTFState counts and names, then the generated scene:
# world boxes of mesh nodes, blend shapes, skeleton bones and AnimationPlayer clips with sampled tracks.

const SAMPLES := 5


func _initialize() -> void:
	_run()


func _run() -> void:
	await process_frame
	var args := OS.get_cmdline_user_args()
	var results := []
	for index in range(1, args.size()):
		results.append(await _inspect(args[index]))
	var file := FileAccess.open(args[0], FileAccess.WRITE)
	file.store_string(JSON.stringify(results))
	file.close()
	quit(0)


func _vec(value: Vector3) -> Array:
	return [value.x, value.y, value.z]


func _quat(value: Quaternion) -> Array:
	return [value.x, value.y, value.z, value.w]


func _inspect(path: String) -> Dictionary:
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	var error := document.append_from_file(path, state)
	var facts := {"path": path, "error": error}
	if error != OK:
		return facts
	var gltf_nodes := state.get_nodes()
	var nodes := []
	for index in gltf_nodes.size():
		var node: GLTFNode = gltf_nodes[index]
		nodes.append({"index": index, "name": node.original_name, "godot_name": String(node.resource_name),
			"parent": node.parent, "mesh": node.mesh, "skin": node.skin, "children": Array(node.children)})
	facts["nodes"] = nodes
	facts["counts"] = {"meshes": state.get_meshes().size(), "nodes": gltf_nodes.size(),
		"materials": state.get_materials().size(), "animations": state.get_animations().size(),
		"skins": state.get_skins().size(), "textures": state.get_textures().size(),
		"images": state.get_images().size()}
	var materials := []
	for material in state.get_materials():
		materials.append(String(material.resource_name))
	facts["materials"] = materials
	var mesh_names := []
	for mesh in state.get_meshes():
		mesh_names.append(mesh.original_name)
	facts["mesh_names"] = mesh_names
	var animations := []
	for animation in state.get_animations():
		animations.append({"name": animation.original_name, "godot_name": String(animation.resource_name),
			"loop": animation.loop})
	facts["gltf_animations"] = animations
	var skins := []
	for skin in state.get_skins():
		skins.append({"name": String(skin.resource_name), "joints": Array(skin.joints),
			"inverse_binds": skin.inverse_binds.size()})
	facts["skins"] = skins
	var scene := document.generate_scene(state)
	if scene == null:
		facts["scene_error"] = "generate_scene returned null"
		return facts
	root.add_child(scene)
	await process_frame
	var bounds := {}
	var materials_by_node := {}
	var shapes := {}
	var transforms := {}
	var paths := {}
	for index in gltf_nodes.size():
		var parent: int = gltf_nodes[index].parent
		var own := String(gltf_nodes[index].resource_name)
		paths[index] = own if parent < 0 or not paths.has(parent) else paths[parent] + "/" + own
	for index in gltf_nodes.size():
		var node = scene.get_node_or_null(NodePath(paths[index]))
		if node == null:
			node = scene.find_child(String(gltf_nodes[index].resource_name), true, false)
		if node == null:
			continue
		if node is Node3D:
			var basis: Basis = node.global_transform.basis
			transforms[str(index)] = {"origin": _vec(node.global_transform.origin),
				"x": _vec(basis.x), "y": _vec(basis.y), "z": _vec(basis.z), "scene_name": String(node.name),
				"scene_path": String(scene.get_path_to(node)),
				"extras": node.get_meta("extras") if node.has_meta("extras") else null}
		if node is MeshInstance3D and node.mesh != null:
			var box: AABB = node.global_transform * node.get_aabb()
			bounds[str(index)] = {"min": _vec(box.position), "max": _vec(box.end)}
			var names := []
			for shape in node.mesh.get_blend_shape_count():
				names.append(String(node.mesh.get_blend_shape_name(shape)))
			shapes[str(index)] = names
			var surface_materials := []
			for surface in node.mesh.get_surface_count():
				var material: Material = node.mesh.surface_get_material(surface)
				surface_materials.append(String(material.resource_name) if material != null else null)
			materials_by_node[str(index)] = surface_materials
	facts["world_bounds"] = bounds
	facts["blend_shapes"] = shapes
	facts["surface_materials"] = materials_by_node
	facts["node_transforms"] = transforms
	var skeletons := []
	for skeleton in scene.find_children("*", "Skeleton3D", true, false):
		var bones := []
		for bone in skeleton.get_bone_count():
			bones.append({"name": skeleton.get_bone_name(bone), "parent": skeleton.get_bone_parent(bone),
				"rest_origin": _vec(skeleton.get_bone_rest(bone).origin)})
		skeletons.append({"name": String(skeleton.name), "bones": bones})
	facts["skeletons"] = skeletons
	var clips := []
	for player in scene.find_children("*", "AnimationPlayer", true, false):
		var base: Node = player.get_node(player.root_node)
		for name in player.get_animation_list():
			var animation: Animation = player.get_animation(name)
			var tracks := []
			for track in animation.get_track_count():
				var track_path: NodePath = animation.track_get_path(track)
				var target := NodePath(track_path.get_concatenated_names())
				var row := {"path": String(track_path), "type": animation.track_get_type(track),
					"keys": animation.track_get_key_count(track),
					"resolved": base.get_node_or_null(target) != null, "samples": []}
				for step in SAMPLES:
					var time := animation.length * step / (SAMPLES - 1)
					var kind := animation.track_get_type(track)
					if kind == Animation.TYPE_POSITION_3D:
						row["samples"].append(_vec(animation.position_track_interpolate(track, time)))
					elif kind == Animation.TYPE_ROTATION_3D:
						row["samples"].append(_quat(animation.rotation_track_interpolate(track, time)))
					elif kind == Animation.TYPE_SCALE_3D:
						row["samples"].append(_vec(animation.scale_track_interpolate(track, time)))
					elif kind == Animation.TYPE_BLEND_SHAPE:
						row["samples"].append(animation.blend_shape_track_interpolate(track, time))
				tracks.append(row)
			clips.append({"name": String(name), "length": animation.length, "tracks": tracks})
	facts["clips"] = clips
	root.remove_child(scene)
	scene.free()
	return facts
