"""Native verifier for geometry_4d items.

For one item: stage the item and shared files as a Godot project; rebuild every declared example with the item's
own CLI under the sandbox interpreter (/usr/bin/python3 -E -s -B) and require identical bytes; check each glTF with
the shared structural checker; load every glTF in headless Godot through GLTFDocument and compare meshes, surfaces,
primitive types, vertex counts, blend shapes and animation tracks with the file; for an item with a Godot scene,
call the GDScript reference_values() and compare it with the Python godot_reference(), then run the scene for a
number of frames; finally render a 256x256 preview under Xvfb with the compatibility renderer (the scene itself,
or the glTF with a camera and lights) and refuse a near-uniform capture. Godot exits 0 on script errors, so every
run's output is scanned for error lines.
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
import shutil
import subprocess
import uuid
from pathlib import Path

from tools.creative_originals.assemble import LOCAL_SANDBOX_ENVIRONMENT, SANDBOX_PYTHON

#: The user session variables systemd-run --user needs to reach the user manager. engines.run gives the engine an
#: isolated runtime folder instead, so these are passed through to keep its memory-capped scope working.
USER_BUS_VARIABLES = ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS")
ERROR_MARKERS = ("ERROR", "Parse Error", "Failed to load", "Cannot call", "Invalid call", "Invalid access")
PREVIEW = 256

PROJECT = """config_version=5

[application]
config/name="geometry_4d_verify"

[rendering]
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
"""

INSPECT = r"""extends SceneTree

func _mesh_info(node: MeshInstance3D) -> Dictionary:
	var mesh: Mesh = node.mesh
	var surfaces := []
	for s in range(mesh.get_surface_count()):
		var arrays: Array = mesh.surface_get_arrays(s)
		var index_array = arrays[Mesh.ARRAY_INDEX]
		var colour_array = arrays[Mesh.ARRAY_COLOR]
		surfaces.append({"primitive": mesh.surface_get_primitive_type(s),
			"vertices": arrays[Mesh.ARRAY_VERTEX].size(),
			"indices": index_array.size() if index_array != null else 0,
			"colors": colour_array != null and colour_array.size() > 0})
	var blend := 0
	if mesh is ArrayMesh:
		blend = mesh.get_blend_shape_count()
	return {"name": String(node.name), "surfaces": surfaces, "blend_shapes": blend}

func _init() -> void:
	var reports := []
	for path in OS.get_cmdline_user_args():
		var document := GLTFDocument.new()
		var state := GLTFState.new()
		var error := document.append_from_file(path, state)
		if error != OK:
			print("INSPECT_FAILED ", path.get_file(), " ", error)
			continue
		var scene: Node = document.generate_scene(state)
		var meshes := []
		if scene is MeshInstance3D:
			meshes.append(_mesh_info(scene))
		for node in scene.find_children("*", "MeshInstance3D", true, false):
			meshes.append(_mesh_info(node))
		var animations := []
		for player in scene.find_children("*", "AnimationPlayer", true, false):
			for name in player.get_animation_list():
				var animation: Animation = player.get_animation(name)
				animations.append({"name": String(name), "length": animation.length, "tracks": animation.get_track_count()})
		reports.append({"file": path.get_file(), "meshes": meshes, "animations": animations})
		scene.free()
	print("INSPECT ", JSON.stringify(reports))
	quit(0)
"""

REFERENCE = r"""extends SceneTree

func _init() -> void:
	var args := OS.get_cmdline_user_args()
	var script = load(args[0])
	var values = script.reference_values()
	print("REFERENCE ", JSON.stringify(values))
	var packed: PackedScene = load(args[1])
	var scene: Node = packed.instantiate()
	root.add_child(scene)
	for i in range(int(args[2])):
		await process_frame
	var status = {}
	if scene.has_method("status"):
		status = scene.call("status")
	print("SCENE ", JSON.stringify(status))
	scene.queue_free()
	await process_frame
	quit(0)
"""

CAPTURE = r"""extends SceneTree

func _init() -> void:
	var args := OS.get_cmdline_user_args()
	var mode: String = args[0]
	var source: String = args[1]
	var output: String = args[2]
	var holder := Node3D.new()
	root.add_child(holder)
	if mode == "scene":
		var packed: PackedScene = load(source)
		var scene: Node = packed.instantiate()
		if scene.get("preview_time") != null:
			scene.set("preview_time", float(args[3]))
		holder.add_child(scene)
	else:
		var document := GLTFDocument.new()
		var state := GLTFState.new()
		var error := document.append_from_file(source, state)
		if error != OK:
			print("CAPTURE_FAILED ", error)
			quit(1)
			return
		var model: Node = document.generate_scene(state)
		holder.add_child(model)
		var nodes := model.find_children("*", "MeshInstance3D", true, false)
		if model is MeshInstance3D:
			nodes.append(model)
		for node in nodes:
			var mesh: Mesh = node.mesh
			for s in range(mesh.get_surface_count()):
				var arrays: Array = mesh.surface_get_arrays(s)
				var colours = arrays[Mesh.ARRAY_COLOR]
				var primitive: int = mesh.surface_get_primitive_type(s)
				var base = mesh.surface_get_material(s)
				var material: StandardMaterial3D = base.duplicate() if base is StandardMaterial3D else StandardMaterial3D.new()
				if colours != null and colours.size() > 0:
					material.vertex_color_use_as_albedo = true
				if primitive == Mesh.PRIMITIVE_LINES or primitive == Mesh.PRIMITIVE_POINTS:
					material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
					material.use_point_size = true
					material.point_size = 3.0
				node.set_surface_override_material(s, material)
		var center := Vector3(float(args[3]), float(args[4]), float(args[5]))
		var reach := float(args[6])
		var at_time := float(args[7])
		for player in model.find_children("*", "AnimationPlayer", true, false):
			var names: PackedStringArray = player.get_animation_list()
			if names.size() > 0:
				player.play(names[0])
				player.seek(at_time, true)
				player.pause()
		var environment := WorldEnvironment.new()
		var settings := Environment.new()
		settings.background_mode = Environment.BG_COLOR
		settings.background_color = Color(0.055, 0.06, 0.08)
		settings.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		settings.ambient_light_color = Color(0.62, 0.64, 0.72)
		settings.ambient_light_energy = 0.55
		environment.environment = settings
		holder.add_child(environment)
		var key := DirectionalLight3D.new()
		key.transform = Transform3D(Basis.from_euler(Vector3(deg_to_rad(-48.0), deg_to_rad(35.0), 0.0)), Vector3.ZERO)
		holder.add_child(key)
		var fill := DirectionalLight3D.new()
		fill.light_energy = 0.35
		fill.transform = Transform3D(Basis.from_euler(Vector3(deg_to_rad(-20.0), deg_to_rad(-140.0), 0.0)), Vector3.ZERO)
		holder.add_child(fill)
		var camera := Camera3D.new()
		camera.fov = 40.0
		camera.near = 0.01
		camera.far = 1000.0
		var direction := Vector3(0.85, 0.55, 1.3).normalized()
		var span: float = reach / tan(deg_to_rad(20.0)) * 1.08
		camera.transform = Transform3D(Basis(), center + direction * span).looking_at(center, Vector3.UP)
		holder.add_child(camera)
		camera.current = true
	for i in range(8):
		await process_frame
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	image.save_png(output)
	print("CAPTURED ", image.get_width(), "x", image.get_height())
	holder.queue_free()
	await process_frame
	quit(0)
"""


def _engine_run(engines, engine, arguments, workspace, display=False, timeout=180):
    """engines.run with the user bus variables, which its systemd-run memory scope needs to start."""
    environment = {name: os.environ[name] for name in USER_BUS_VARIABLES if os.environ.get(name)}
    return engines.run(engine, arguments, workspace=workspace, display=display, timeout=timeout,
                       environment=environment)


def _check(name, passed, detail):
    return {"name": name, "state": "passed" if passed else "failed", "detail": detail}


def _errors(outcome):
    text = (outcome.get("stdout") or "") + "\n" + (outcome.get("stderr") or "")
    return [line.strip() for line in text.splitlines() if any(marker in line for marker in ERROR_MARKERS)][:8]


def _line(outcome, prefix):
    for line in (outcome.get("stdout") or "").splitlines():
        if line.startswith(prefix):
            return line[len(prefix):]
    return None


def _load_fourd(shared_dir):
    specification = importlib.util.spec_from_file_location(f"fourd_native_{uuid.uuid4().hex}", shared_dir / "fourd.py")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _python(stage, arguments, timeout=240):
    completed = subprocess.run([SANDBOX_PYTHON, "-E", "-s", "-B", *arguments], cwd=stage,
                               env=LOCAL_SANDBOX_ENVIRONMENT.variables(stage), capture_output=True, text=True,
                               timeout=timeout)
    return completed.returncode, completed.stdout, completed.stderr[-1500:]


def _close(actual, expected, tolerance=1e-4):
    if isinstance(expected, bool) or isinstance(actual, bool):
        return actual == expected
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return math.isfinite(actual) and abs(actual - expected) <= tolerance * max(1.0, abs(expected))
    if isinstance(expected, (list, tuple)) and isinstance(actual, (list, tuple)):
        return len(actual) == len(expected) and all(_close(a, b, tolerance) for a, b in zip(actual, expected))
    if isinstance(expected, dict) and isinstance(actual, dict):
        return set(actual) == set(expected) and all(_close(actual[key], expected[key], tolerance) for key in expected)
    return actual == expected


def _expected_meshes(fourd, document):
    """What Godot should report per mesh node: surfaces with primitive type and vertex count, blend shapes."""
    godot_primitive = {0: 0, 1: 1, 3: 2, 4: 3, 5: 4}
    accessors = document["accessors"]
    rows = []
    for node in document.get("nodes", []):
        if "mesh" not in node:
            continue
        mesh = document["meshes"][node["mesh"]]
        surfaces = []
        for primitive in mesh["primitives"]:
            surfaces.append({"primitive": godot_primitive.get(primitive.get("mode", 4), -1),
                             "vertices": accessors[primitive["attributes"]["POSITION"]]["count"]})
        rows.append({"surfaces": surfaces, "blend_shapes": len(mesh["primitives"][0].get("targets", []))})
    tracks = []
    for animation in document.get("animations", []):
        count = 0
        for channel in animation["channels"]:
            if channel["target"]["path"] == "weights":
                node = document["nodes"][channel["target"]["node"]]
                count += len(document["meshes"][node["mesh"]]["primitives"][0].get("targets", []))
            else:
                count += 1
        times = fourd.accessor_values(document, animation["samplers"][0]["input"])
        tracks.append({"tracks": count, "length": max(times)})
    return rows, tracks


def _posed_bounds(fourd, document, at_time):
    """Bounds of every mesh at an animation time (morph weights interpolated, node translations applied)."""
    buffers = fourd.buffer_bytes(document)
    weights = {}
    for animation in document.get("animations", [])[:1]:
        for channel in animation["channels"]:
            if channel["target"]["path"] != "weights":
                continue
            sampler = animation["samplers"][channel["sampler"]]
            times = fourd.accessor_values(document, sampler["input"], buffers)
            values = fourd.accessor_values(document, sampler["output"], buffers)
            count = len(values) // len(times)
            rows = [values[index * count:(index + 1) * count] for index in range(len(times))]
            if at_time <= times[0]:
                current = rows[0]
            elif at_time >= times[-1]:
                current = rows[-1]
            else:
                step = max(index for index in range(len(times)) if times[index] <= at_time)
                fraction = (at_time - times[step]) / (times[step + 1] - times[step])
                current = [a + (b - a) * fraction for a, b in zip(rows[step], rows[step + 1])]
                if sampler.get("interpolation") == "STEP":
                    current = rows[step]
            weights[channel["target"]["node"]] = current
    low, high = [math.inf] * 3, [-math.inf] * 3
    for node_index, node in enumerate(document.get("nodes", [])):
        if "mesh" not in node:
            continue
        offset = node.get("translation", [0.0, 0.0, 0.0])
        mesh = document["meshes"][node["mesh"]]
        node_weights = weights.get(node_index, mesh.get("weights", []))
        for primitive in mesh["primitives"]:
            positions = fourd.accessor_values(document, primitive["attributes"]["POSITION"], buffers)
            for target, weight in zip(primitive.get("targets", []), node_weights):
                if weight:
                    deltas = fourd.accessor_values(document, target["POSITION"], buffers)
                    positions = [tuple(p + weight * d for p, d in zip(point, delta))
                                 for point, delta in zip(positions, deltas)]
            for point in positions:
                for axis in range(3):
                    value = point[axis] + offset[axis]
                    low[axis] = min(low[axis], value)
                    high[axis] = max(high[axis], value)
    return low, high


def _image_spread(path):
    from tools.creative_originals import pngio
    image = pngio.decode(path.read_bytes())
    channels, pixels = image["channels"], image["pixels"]
    count = image["width"] * image["height"]
    background = pixels[0:3]
    differing = 0
    for index in range(0, len(pixels), channels):
        if max(abs(pixels[index + c] - background[c]) for c in range(3)) > 24:
            differing += 1
    stats = pngio.statistics(image)
    spread = max(row["maximum"] - row["minimum"] for row in stats["channels"][:3])
    return {"width": image["width"], "height": image["height"], "coverage": round(differing / count, 4),
            "channel_range": spread}


def verify(context):
    engines = context.engines
    engine = engines.locate("godot")
    item, identity = context.item, context.item["identity"]
    contract = item["contract"]
    stage = Path(context.workspace) / "project"
    stage.mkdir(parents=True)
    for row in item["files"]:
        target = stage / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(context.item_dir) / row["path"], target)
    for row in context.family["shared_files"]:
        shutil.copyfile(Path(context.shared_dir) / row["path"], stage / row["path"])
    (stage / "project.godot").write_text(PROJECT)
    fourd = _load_fourd(Path(context.shared_dir))
    checks = []
    record = {**engine.identity(), "renderer": "gl_compatibility (opengl3, Mesa llvmpipe under Xvfb)"}

    # 1. The item's CLI rebuilds every declared example byte for byte under the sandbox interpreter.
    rebuilt = stage / "_rebuilt"
    rebuilt.mkdir()
    gltf_files = []
    for declared in contract.get("outputs", []):
        packaged = stage / declared["path"]
        if "command" in declared:
            target = rebuilt / Path(declared["path"]).name
            code, _out, error = _python(stage, [f"{identity}.py", *declared["command"], "--out", str(target)])
            same = code == 0 and target.is_file() and target.read_bytes() == packaged.read_bytes()
            checks.append(_check(f"cli_rebuilds_{Path(declared['path']).stem}", same,
                                 {"returncode": code, "bytes": packaged.stat().st_size, "stderr": error[-400:]}))
        if packaged.suffix == ".gltf":
            document = json.loads(packaged.read_text())
            problems = fourd.validate_gltf(document)
            size = packaged.stat().st_size
            checks.append(_check(f"gltf_structure_{packaged.stem}", not problems and size <= fourd.MAXIMUM_EXAMPLE_BYTES,
                                 {"problems": problems[:5], "bytes": size, "summary": fourd.gltf_summary(document)}))
            gltf_files.append(packaged)
    example = contract.get("cli_example")
    if example:
        arguments = list(example)
        position = arguments.index("--out")
        target = rebuilt / ("cli_" + Path(arguments[position + 1]).name)
        arguments[position + 1] = str(target)
        code, _out, error = _python(stage, [f"{identity}.py", *arguments])
        checks.append(_check("cli_example_runs", code == 0 and target.is_file(),
                             {"returncode": code, "stderr": error[-400:]}))
        if target.suffix == ".gltf" and target.is_file():
            problems = fourd.validate_gltf(json.loads(target.read_text()))
            checks.append(_check("cli_example_gltf_structure", not problems, {"problems": problems[:5]}))
            gltf_files.append(target)

    # 2. Godot loads every glTF at run time and sees what the file declares.
    if gltf_files:
        (stage / "_verify_inspect.gd").write_text(INSPECT)
        outcome = _engine_run(engines, engine, ["--headless", "--path", str(stage), "--script",
                                                "res://_verify_inspect.gd", "--", *[str(path) for path in gltf_files]],
                              context.workspace)
        errors = _errors(outcome)
        text = _line(outcome, "INSPECT ")
        reports = json.loads(text) if text else []
        by_file = {report["file"]: report for report in reports}
        for path in gltf_files:
            document = json.loads(path.read_text())
            expected_meshes, expected_tracks = _expected_meshes(fourd, document)
            report = by_file.get(path.name)
            seen_meshes = [{"surfaces": [{"primitive": s["primitive"], "vertices": s["vertices"]} for s in mesh["surfaces"]],
                            "blend_shapes": mesh["blend_shapes"]} for mesh in report["meshes"]] if report else None
            key = lambda row: json.dumps(row, sort_keys=True)
            same_meshes = report is not None and sorted(map(key, seen_meshes)) == sorted(map(key, expected_meshes))
            seen_tracks = [{"tracks": row["tracks"], "length": round(row["length"], 4)} for row in report["animations"]] \
                if report else None
            want_tracks = [{"tracks": row["tracks"], "length": round(row["length"], 4)} for row in expected_tracks]
            same_tracks = report is not None and sorted(map(key, seen_tracks)) == sorted(map(key, want_tracks))
            checks.append(_check(f"godot_loads_{path.stem}", same_meshes and same_tracks and not errors
                                 and outcome["returncode"] == 0,
                                 {"meshes": len(expected_meshes),
                                  "vertices": sum(s["vertices"] for row in expected_meshes for s in row["surfaces"]),
                                  "blend_shapes": sum(row["blend_shapes"] for row in expected_meshes),
                                  "animation_tracks": [row["tracks"] for row in want_tracks],
                                  "godot_meshes": seen_meshes if not same_meshes else "matched",
                                  "godot_animations": seen_tracks if not same_tracks else "matched",
                                  "errors": errors, "seconds": outcome["seconds"]}))

    # 3. A Godot scene item: the GDScript reproduces the Python numbers and the scene runs.
    script = stage / f"{identity}.gd"
    scene = stage / "demo.tscn"
    if script.is_file() and scene.is_file():
        code, out, error = _python(stage, ["-c", f"import json, {identity}; print(json.dumps({identity}.godot_reference()))"])
        python_values = json.loads(out) if code == 0 else None
        (stage / "_verify_reference.gd").write_text(REFERENCE)
        outcome = _engine_run(engines, engine, ["--headless", "--path", str(stage), "--script",
                                                "res://_verify_reference.gd", "--", f"res://{identity}.gd",
                                                "res://demo.tscn", "90"], context.workspace)
        errors = _errors(outcome)
        text = _line(outcome, "REFERENCE ")
        godot_values = json.loads(text) if text else None
        checks.append(_check("gdscript_matches_python", python_values is not None and godot_values is not None
                             and _close(godot_values, python_values) and not errors,
                             {"keys": sorted(python_values) if isinstance(python_values, dict) else None,
                              "python_error": error[-300:] if code else "",
                              "godot": godot_values if not _close(godot_values, python_values) else "matched",
                              "errors": errors}))
        status_text = _line(outcome, "SCENE ")
        status = json.loads(status_text) if status_text else None
        checks.append(_check("scene_runs_headless", status is not None and not errors and outcome["returncode"] == 0
                             and status.get("ok", True) is True,
                             {"frames": 90, "status": status, "errors": errors, "seconds": outcome["seconds"]}))

    # 4. Preview under Xvfb with the compatibility renderer.
    (stage / "_verify_capture.gd").write_text(CAPTURE)
    capture = stage / "_preview.png"
    preview_time = float(contract.get("preview_time", 0.0))
    if scene.is_file():
        arguments = ["scene", "res://demo.tscn", str(capture), repr(preview_time)]
    elif gltf_files:
        source = gltf_files[0]
        document = json.loads(source.read_text())
        animations = document.get("animations", [])
        at_time = preview_time
        if animations and "preview_time" not in contract:
            at_time = 0.45 * max(fourd.accessor_values(document, animations[0]["samplers"][0]["input"]))
        low, high = _posed_bounds(fourd, document, at_time)
        center = [(a + b) / 2.0 for a, b in zip(low, high)]
        reach = max(0.05, 0.5 * math.sqrt(sum((b - a) ** 2 for a, b in zip(low, high))))
        arguments = ["gltf", str(source), str(capture), *[repr(value) for value in center], repr(reach), repr(at_time)]
    else:
        checks.append(_check("preview_source", False, {"reason": "no scene and no glTF to render"}))
        return {"engine": record, "checks": checks, "preview": None}
    outcome = _engine_run(engines, engine, ["--path", str(stage), "--rendering-driver", "opengl3", "--resolution",
                                            f"{PREVIEW}x{PREVIEW}", "--script", "res://_verify_capture.gd", "--",
                                            *arguments], context.workspace, display=True)
    errors = _errors(outcome)
    preview = None
    if capture.is_file():
        spread = _image_spread(capture)
        varied = spread["coverage"] >= 0.01 and spread["channel_range"] >= 40
        checks.append(_check("preview_render", varied and not errors and spread["width"] == PREVIEW,
                             {**spread, "mode": arguments[0], "errors": errors, "seconds": outcome["seconds"]}))
        if varied and not errors:
            preview = capture.read_bytes()
    else:
        checks.append(_check("preview_render", False, {"errors": errors, "stdout": (outcome.get("stdout") or "")[-600:],
                                                       "stderr": (outcome.get("stderr") or "")[-600:]}))
    return {"engine": record, "checks": checks, "preview": preview}
