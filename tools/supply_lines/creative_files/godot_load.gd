extends Node3D
## Loads one fetched variant of a Baltor creative package into the scene (Godot 4).
##
## Fetch a variant into the project first, for example
##     python creative_fetch.py fetch gltf-2k assets/food_apple_01
## copy creative.json and this script into the project, attach the script to a Node3D and set
## asset_folder to the folder the variant was fetched into (res://assets/food_apple_01 above).
## An HDRI becomes the sky and its light, a model is read with GLTFDocument (the glTF variant) or taken
## from the editor's import of an OBJ or FBX file, and a texture or material set becomes a
## StandardMaterial3D on a plane, with the OpenGL normal map Godot expects.

@export_file("*.json") var manifest_path: String = "res://creative.json"
@export_dir var asset_folder: String = "res://assets"
@export var variant_id: String = ""
@export var plane_size: float = 0.0


func _ready() -> void:
	var manifest: Dictionary = read_manifest(manifest_path)
	if manifest.is_empty():
		return
	var chosen: Dictionary = pick_variant(manifest, variant_id)
	if chosen.is_empty():
		push_error("This package has no variant named " + variant_id)
		return
	var files: Dictionary = files_by_role(chosen, asset_folder)
	var kind: String = String(manifest["asset"]["type"])
	if kind == "hdri":
		add_child(environment(String(files.get("environment", ""))))
	elif kind == "model":
		var model: Node = load_model(String(files.get("model", "")))
		if model != null:
			add_child(model)
	else:
		var size: float = plane_size if plane_size > 0.0 else asset_width(manifest)
		add_child(material_plane(files, size))


static func read_manifest(path: String) -> Dictionary:
	var text: String = FileAccess.get_file_as_string(path)
	if text.is_empty():
		push_error("Cannot read the package manifest at " + path)
		return {}
	var parsed = JSON.parse_string(text)
	if parsed is Dictionary:
		return parsed
	push_error("The package manifest at " + path + " is not a JSON object")
	return {}


static func pick_variant(manifest: Dictionary, wanted: String) -> Dictionary:
	var target: String = wanted
	if target == "":
		target = String(manifest.get("default_variant", ""))
	for row in manifest.get("variants", []):
		if String(row.get("id", "")) == target:
			return row
	return {}


static func files_by_role(chosen: Dictionary, folder: String) -> Dictionary:
	var found: Dictionary = {}
	for item in chosen.get("files", []):
		var rows: Array = [item]
		if item.get("unpack", false):
			rows = item.get("members", [])
		for row in rows:
			var role: String = String(row.get("role", ""))
			if role != "" and not found.has(role):
				found[role] = folder.path_join(String(row["path"]))
	return found


static func asset_width(manifest: Dictionary) -> float:
	var dimensions: Array = manifest["asset"].get("dimensions_mm", [])
	if dimensions.size() > 0 and float(dimensions[0]) > 0.0:
		return float(dimensions[0]) / 1000.0
	return 2.0


static func texture(path: String) -> Texture2D:
	if ResourceLoader.exists(path):
		return load(path) as Texture2D
	var image: Image = Image.load_from_file(path)
	if image == null:
		push_error("Fetch the variant first: cannot read " + path)
		return null
	return ImageTexture.create_from_image(image)


static func environment(path: String) -> WorldEnvironment:
	var sky_material := PanoramaSkyMaterial.new()
	sky_material.panorama = texture(path)
	var sky := Sky.new()
	sky.sky_material = sky_material
	var settings := Environment.new()
	settings.background_mode = Environment.BG_SKY
	settings.sky = sky
	settings.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	settings.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	var world := WorldEnvironment.new()
	world.environment = settings
	return world


static func load_model(path: String) -> Node:
	var extension: String = path.get_extension().to_lower()
	if extension == "gltf" or extension == "glb":
		var document := GLTFDocument.new()
		var state := GLTFState.new()
		if document.append_from_file(path, state) != OK:
			push_error("Godot could not read " + path + "; fetch the variant first")
			return null
		return document.generate_scene(state)
	if ResourceLoader.exists(path):
		var resource = load(path)
		if resource is PackedScene:
			return resource.instantiate()
		if resource is Mesh:
			var instance := MeshInstance3D.new()
			instance.mesh = resource
			return instance
	push_error("Fetch a glTF variant to load this model at run time, or let the editor import " + path)
	return null


static func material_plane(files: Dictionary, size: float) -> MeshInstance3D:
	var material := StandardMaterial3D.new()
	if files.has("diffuse"):
		material.albedo_texture = texture(String(files["diffuse"]))
	if files.has("roughness"):
		material.roughness_texture = texture(String(files["roughness"]))
	if files.has("metalness"):
		material.metallic = 1.0
		material.metallic_texture = texture(String(files["metalness"]))
	if files.has("normal_gl"):
		material.normal_enabled = true
		material.normal_texture = texture(String(files["normal_gl"]))
	if files.has("ao"):
		material.ao_enabled = true
		material.ao_texture = texture(String(files["ao"]))
	if files.has("displacement"):
		material.heightmap_enabled = true
		material.heightmap_texture = texture(String(files["displacement"]))
	var plane := PlaneMesh.new()
	plane.size = Vector2(size, size)
	var instance := MeshInstance3D.new()
	instance.mesh = plane
	instance.material_override = material
	return instance
