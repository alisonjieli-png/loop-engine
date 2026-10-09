extends SceneTree
## Exercise an articulated asset in Godot and write what happened as JSON.
##   godot --headless --path PROJECT --script res://articulation_probe.gd -- OUT.json load ASSET.gltf MANIFEST.json [SAVE.tscn]
##   godot --headless --path PROJECT --script res://articulation_probe.gd -- OUT.json reopen SCENE.tscn
## For every joint: the node's global transform and world pivot at the lower and upper limits, and the values applied
## for an overshoot and an undershoot. For every clip of the JointPlayer (not the glTF's own AnimationPlayer): the pose
## at the clip's end.

const ArticulatedAsset := preload("res://articulated_asset.gd")


func _initialize() -> void:
	_run()


func _run() -> void:
	await process_frame
	var args := OS.get_cmdline_user_args()
	var result := {"mode": args[1]}
	var asset: Node3D = null
	if args[1] == "load":
		asset = ArticulatedAsset.new()
		asset.name = "Articulated"
		root.add_child(asset)
		result["load_error"] = asset.load_asset(args[2], args[3])
	else:
		var packed = load(args[2])
		if packed is PackedScene:
			asset = packed.instantiate()
			root.add_child(asset)
			result["load_error"] = OK
		else:
			result["load_error"] = ERR_CANT_OPEN
	await process_frame
	if asset != null:
		result["errors"] = asset.errors
	if result["load_error"] == OK:
		result["joints"] = _exercise(asset)
		if args[1] == "load":
			asset.build_animation_player()
		result["clips"] = _play_clips(asset)
		if args[1] == "load" and args.size() > 4:
			result["save_error"] = asset.save_scene(args[4])
	var file := FileAccess.open(args[0], FileAccess.WRITE)
	file.store_string(JSON.stringify(result))
	file.close()
	quit(0)


func _vec(value: Vector3) -> Array:
	return [value.x, value.y, value.z]


func _pose(asset: Node3D, name: String) -> Dictionary:
	var transform: Transform3D = asset.joint_node(name).global_transform
	return {"origin": _vec(transform.origin), "x": _vec(transform.basis.x), "y": _vec(transform.basis.y),
		"z": _vec(transform.basis.z), "world_pivot": _vec(transform * asset.joint_pivot(name))}


func _exercise(asset: Node3D) -> Dictionary:
	var rows := {}
	for name in asset.joint_names():
		var limits: Array = asset.joint_limits(name)
		var row := {}
		for label in ["lower", "upper"]:
			var applied: float = asset.set_joint(name, limits[0] if label == "lower" else limits[1])
			row[label] = _pose(asset, name)
			row[label]["applied"] = applied
		var span: float = limits[1] - limits[0]
		row["overshoot_applied"] = asset.set_joint(name, limits[1] + span)
		row["undershoot_applied"] = asset.set_joint(name, limits[0] - span)
		asset.reset_joints()
		rows[name] = row
	return rows


func _play_clips(asset: Node3D) -> Dictionary:
	var rows := {}
	var player := asset.get_node_or_null("JointPlayer") as AnimationPlayer
	if player == null:
		return rows
	for clip in player.get_animation_list():
		var animation := player.get_animation(clip)
		player.play(clip)
		player.seek(animation.length, true)
		var joint_name := String(clip).rsplit("_", true, 1)[0]
		var row := _pose(asset, joint_name)
		row["length"] = animation.length
		rows[String(clip)] = row
		player.stop()
		asset.reset_joints()
	return rows
