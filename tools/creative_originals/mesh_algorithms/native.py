"""Native verifier for the mesh_algorithms family.

For one item:

1. copy the item's declared files and the family's shared files into the workspace, as the package holds them;
2. run the item's command line with its default parameters under the system interpreter (the one package tests
   use) and under the verifier's interpreter, each writing a .gltf;
3. verify both files with meshkit's strict glTF reader, compare them with the command line's own summary and
   with each other (identical topology, positions within float32 noise);
4. compare every example model the item ships with the fresh output;
5. load the fresh file and every shipped example in Godot 4 headless with GLTFDocument and generate_scene, and
   compare each mesh instance's surfaces (primitive type, vertex count, index count), the scene bounds and the
   animation count with the Python result;
6. render one model at 256 x 256 with the compatibility renderer (OpenGL 3, Xvfb) with a directional light and a
   camera framed on its bounds, and refuse a near-uniform capture or one where the model covers almost nothing.

Godot exits 0 even after an error, so every engine output is scanned for error lines. A check that cannot run is
a failed check, never a pass.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from tools.creative_originals import pngio
from tools.creative_originals.assemble import LOCAL_SANDBOX_ENVIRONMENT, SANDBOX_PYTHON

FAMILY_DIRECTORY = Path(__file__).resolve().parent
#: The variable naming the user runtime folder, where systemd-run --user finds the user bus.
RUNTIME_DIRECTORY_VARIABLE = "XDG_RUNTIME_DIR"
LOAD_MARK = "MESH_ALGORITHMS_LOAD "
RENDER_MARK = "MESH_ALGORITHMS_RENDER "
BACKGROUND = (33, 36, 43)
RENDERER = "gl_compatibility, OpenGL 3 driver, Mesa llvmpipe under Xvfb"
GODOT_PRIMITIVE = {0: 0, 1: 1, 3: 2, 4: 3, 5: 4}
_LOCK = threading.Lock()
_MESHKIT = None

PROJECT = """config_version=5

[application]

config/name="mesh_algorithms_check"

[rendering]

renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
"""

LOAD_SCRIPT = r'''extends SceneTree
# Load every glTF named after "--" with GLTFDocument and print one JSON line describing each scene.

func _initialize():
	var results = []
	for path in OS.get_cmdline_user_args():
		var document = GLTFDocument.new()
		var state = GLTFState.new()
		var error = document.append_from_file(path, state)
		var row = {"file": path.get_file(), "error": error, "instances": [], "meshes": 0, "animations": 0, "aabb": []}
		if error == OK:
			var scene = document.generate_scene(state)
			if scene == null:
				row["error"] = -1
			else:
				var unique = {}
				var box = [null]
				_collect(scene, Transform3D.IDENTITY, row, unique, box)
				row["meshes"] = unique.size()
				if box[0] != null:
					var b = box[0]
					row["aabb"] = [b.position.x, b.position.y, b.position.z, b.end.x, b.end.y, b.end.z]
				scene.free()
		results.append(row)
	print("MESH_ALGORITHMS_LOAD " + JSON.stringify(results))
	quit(0)

func _collect(node, parent, row, unique, box):
	var world = parent
	if node is Node3D:
		world = parent * node.transform
	if node is MeshInstance3D and node.mesh != null:
		var mesh = node.mesh
		unique[mesh.get_instance_id()] = true
		var surfaces = []
		for s in mesh.get_surface_count():
			var arrays = mesh.surface_get_arrays(s)
			var indices = arrays[Mesh.ARRAY_INDEX]
			var index_count = -1
			if indices != null:
				index_count = indices.size()
			surfaces.append([mesh.surface_get_primitive_type(s), arrays[Mesh.ARRAY_VERTEX].size(), index_count])
		row["instances"].append(surfaces)
		var placed = world * mesh.get_aabb()
		if box[0] == null:
			box[0] = placed
		else:
			box[0] = box[0].merge(placed)
	if node is AnimationPlayer:
		row["animations"] += node.get_animation_list().size()
	for child in node.get_children():
		_collect(child, world, row, unique, box)
'''

RENDER_SCRIPT = r'''extends SceneTree
# Render the glTF named after "--" at the window size and save the frame as PNG.

func _initialize():
	_render.call_deferred()

func _gather(node, found):
	if node is MeshInstance3D and node.mesh != null:
		found.append(node)
	for child in node.get_children():
		_gather(child, found)

func _render():
	var arguments = OS.get_cmdline_user_args()
	var document = GLTFDocument.new()
	var state = GLTFState.new()
	var error = document.append_from_file(arguments[0], state)
	if error != OK:
		print("MESH_ALGORITHMS_RENDER " + JSON.stringify({"error": error}))
		quit(1)
		return
	var scene = document.generate_scene(state)
	root.add_child(scene)
	var found = []
	_gather(scene, found)
	var box = AABB()
	var first = true
	for instance in found:
		var placed = instance.global_transform * instance.mesh.get_aabb()
		if first:
			box = placed
			first = false
		else:
			box = box.merge(placed)
		for s in instance.mesh.get_surface_count():
			var arrays = instance.mesh.surface_get_arrays(s)
			if arrays[Mesh.ARRAY_COLOR] != null:
				var original = instance.mesh.surface_get_material(s)
				var shown = StandardMaterial3D.new()
				if original != null:
					shown = original.duplicate()
				shown.vertex_color_use_as_albedo = true
				instance.set_surface_override_material(s, shown)
	var world = WorldEnvironment.new()
	var environment = Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color8(33, 36, 43)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.62, 0.64, 0.70)
	environment.ambient_light_energy = 0.55
	world.environment = environment
	root.add_child(world)
	var key = DirectionalLight3D.new()
	root.add_child(key)
	key.look_at_from_position(Vector3.ZERO, Vector3(-0.55, -1.0, -0.4), Vector3.UP)
	var fill = DirectionalLight3D.new()
	fill.light_energy = 0.35
	root.add_child(fill)
	fill.look_at_from_position(Vector3.ZERO, Vector3(0.7, -0.25, 0.6), Vector3.UP)
	var center = box.get_center()
	var radius = max(box.size.length() * 0.5, 0.0001)
	var direction = Vector3(1.0, 0.8, 1.4).normalized()
	if box.size.y < 0.05 * max(box.size.x, box.size.z):
		direction = Vector3(0.35, 1.5, 1.0).normalized()
	var camera = Camera3D.new()
	camera.fov = 38.0
	root.add_child(camera)
	var distance = radius / sin(deg_to_rad(camera.fov * 0.5)) * 1.02
	camera.near = max(distance * 0.005, 0.0001)
	camera.far = distance * 4.0
	camera.look_at_from_position(center + direction * distance, center, Vector3.UP)
	camera.current = true
	for frame in 4:
		await process_frame
	await RenderingServer.frame_post_draw
	var image = root.get_texture().get_image()
	image.convert(Image.FORMAT_RGB8)
	image.save_png(arguments[1])
	print("MESH_ALGORITHMS_RENDER " + JSON.stringify({"error": 0, "instances": found.size(), "width": image.get_width(), "height": image.get_height()}))
	quit(0)
'''


def _meshkit():
    global _MESHKIT
    with _LOCK:
        if _MESHKIT is None:
            path = FAMILY_DIRECTORY / "shared" / "meshkit.py"
            specification = importlib.util.spec_from_file_location("mesh_algorithms_meshkit_native", path)
            module = importlib.util.module_from_spec(specification)
            specification.loader.exec_module(module)
            _MESHKIT = module
    return _MESHKIT


def _check(name, passed, detail):
    return {"name": name, "state": "passed" if passed else "failed", "detail": detail}


def _error_lines(text):
    return [line.strip()[:240] for line in text.splitlines() if "ERROR" in line or "Parse Error" in line][:6]


def _run_generator(python, package, module, output, home):
    try:
        completed = subprocess.run([python, "-E", "-s", "-B", module + ".py", "--output", str(output)], cwd=package,
                                   env=LOCAL_SANDBOX_ENVIRONMENT.variables(home), capture_output=True, text=True,
                                   timeout=300)
    except subprocess.TimeoutExpired:
        return None, {"error": "timed out after 300 s"}
    version = subprocess.run([python, "-E", "-s", "-B", "-c", "import sys; print(sys.version.split()[0])"],
                             capture_output=True, text=True, timeout=60).stdout.strip()
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    summary = None
    if completed.returncode == 0 and lines:
        try:
            summary = json.loads(lines[-1])
        except ValueError:
            summary = None
    detail = {"interpreter": version, "exit": completed.returncode}
    if summary is None:
        detail["stderr_tail"] = completed.stderr[-600:]
    else:
        detail["summary"] = {key: summary[key] for key in ("meshes", "nodes", "animations", "vertices", "triangles",
                                                           "lines") if key in summary}
    return summary, detail


def _shape(read):
    return [[(p["mode"], p["vertex_count"], p["index_count"]) for p in mesh["primitives"]] for mesh in read["meshes"]]


def _compare(meshkit, first, second):
    """Topology must be identical; positions may differ by float noise. Returns (same, worst difference)."""
    if _shape(first) != _shape(second):
        return False, None
    worst = 0.0
    scale = 1.0
    for mesh_a, mesh_b in zip(first["meshes"], second["meshes"]):
        for prim_a, prim_b in zip(mesh_a["primitives"], mesh_b["primitives"]):
            if prim_a["indices"] != prim_b["indices"]:
                return False, None
            for p, q in zip(prim_a["positions"], prim_b["positions"]):
                for a, b in zip(p, q):
                    worst = max(worst, abs(a - b))
                    scale = max(scale, abs(a))
    return worst <= 1e-6 * scale, worst


def _expected_scene(meshkit, path):
    """Per mesh instance surfaces, the world bounds and the animation count Godot should report."""
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    read = meshkit.read_gltf(document)
    worlds = meshkit.node_world_matrices(document)
    nodes = document.get("nodes", [])
    reachable, stack = [], list(read["scene_nodes"])
    while stack:
        number = stack.pop()
        reachable.append(number)
        stack.extend(nodes[number].get("children", []))
    instances, low, high = [], [float("inf")] * 3, [float("-inf")] * 3
    for number in sorted(reachable):
        node = nodes[number]
        if "mesh" not in node:
            continue
        mesh = read["meshes"][node["mesh"]]
        instances.append(sorted([GODOT_PRIMITIVE.get(p["mode"], -1), p["vertex_count"],
                                 p["index_count"] if p["index_count"] is not None else -1] for p in mesh["primitives"]))
        for primitive in document["meshes"][node["mesh"]]["primitives"]:
            accessor = document["accessors"][primitive["attributes"]["POSITION"]]
            for corner in range(8):
                point = tuple(accessor["max"][k] if corner >> k & 1 else accessor["min"][k] for k in range(3))
                placed = meshkit.transform_point(worlds[number], point)
                for k in range(3):
                    low[k] = min(low[k], placed[k])
                    high[k] = max(high[k], placed[k])
    return {"instances": sorted(instances), "aabb": low + high, "animations": read["animations"],
            "meshes": len({nodes[n]["mesh"] for n in reachable if "mesh" in nodes[n]})}


def _godot_environment():
    runtime = os.environ.get(RUNTIME_DIRECTORY_VARIABLE)
    # engines.run starts a memory-capped systemd user scope; systemd-run needs the real runtime folder to reach
    # the user manager, which the isolated environment otherwise replaces.
    return {RUNTIME_DIRECTORY_VARIABLE: runtime} if runtime else None


def verify(context):
    meshkit = _meshkit()
    engines = context.engines
    workspace = Path(context.workspace)
    item = context.item
    module = item["contract"]["module"]
    package = workspace / "package"
    package.mkdir()
    for row in item["files"]:
        target = package / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(context.item_dir / row["path"], target)
    for row in context.family["shared_files"]:
        shutil.copyfile(context.shared_dir / row["path"], package / row["path"])
    checks = []

    outputs, reads = {}, {}
    for label, python in (("system", SANDBOX_PYTHON), ("verifier", sys.executable)):
        output = workspace / f"fresh_{label}.gltf"
        summary, detail = _run_generator(python, package, module, output, workspace)
        passed = summary is not None and output.is_file()
        checks.append(_check(f"generator_runs_{label}_python", passed, detail))
        if passed:
            outputs[label] = (output, summary)
    if len(outputs) != 2:
        return {"engine": {}, "checks": checks, "preview": None}

    structure = {}
    for label, (output, summary) in outputs.items():
        try:
            read = meshkit.read_gltf(output)
        except meshkit.GltfError as error:
            structure[label] = {"error": error.reason, "detail": error.detail[:200]}
            continue
        reads[label] = read
        agrees = (summary.get("vertices"), summary.get("triangles"), summary.get("lines")) == (
            read["vertex_count"], read["triangle_count"], read["line_count"])
        structure[label] = {"meshes": len(read["meshes"]), "nodes": read["nodes"], "animations": read["animations"],
                            "vertices": read["vertex_count"], "triangles": read["triangle_count"],
                            "lines": read["line_count"], "matches_summary": agrees}
    passed = len(reads) == 2 and all(row.get("matches_summary") for row in structure.values())
    checks.append(_check("gltf_strict_structure", passed, structure["system"] if passed else structure))
    if not passed:
        return {"engine": {}, "checks": checks, "preview": None}

    same, worst = _compare(meshkit, reads["system"], reads["verifier"])
    identical = outputs["system"][0].read_bytes() == outputs["verifier"][0].read_bytes()
    checks.append(_check("interpreters_agree", same, {"bytes_identical": identical, "largest_position_difference": worst}))

    examples = [row["path"] for row in item["files"] if row["path"].endswith(".gltf")]
    for example in examples:
        try:
            shipped = meshkit.read_gltf(package / example)
            agree, difference = _compare(meshkit, shipped, reads["system"])
            detail = {"file": example, "matches": agree, "largest_position_difference": difference,
                      "bytes_identical": (package / example).read_bytes() == outputs["system"][0].read_bytes()}
        except meshkit.GltfError as error:
            agree, detail = False, {"file": example, "error": error.reason}
        checks.append(_check("example_matches_generator", agree, detail))

    try:
        engine = engines.locate("godot")
    except engines.EngineUnavailable as error:
        checks.append(_check("godot_available", False, {"error": str(error)[:300]}))
        return {"engine": {}, "checks": checks, "preview": None}
    identity = dict(engine.identity(), renderer=RENDERER)
    project = workspace / "godot"
    project.mkdir()
    (project / "project.godot").write_text(PROJECT, encoding="utf-8")
    (project / "load.gd").write_text(LOAD_SCRIPT, encoding="utf-8")
    (project / "render.gd").write_text(RENDER_SCRIPT, encoding="utf-8")
    targets = [outputs["system"][0]] + [package / example for example in examples]
    loaded = engines.run(engine, ["--headless", "--path", str(project), "--script", "res://load.gd", "--",
                                  *[str(path) for path in targets]], workspace=workspace, timeout=120,
                         environment=_godot_environment())
    text = loaded["stdout"] + "\n" + loaded["stderr"]
    rows = None
    for line in loaded["stdout"].splitlines():
        if line.startswith(LOAD_MARK):
            try:
                rows = json.loads(line[len(LOAD_MARK):])
            except ValueError:
                rows = None
    problems, compared = _error_lines(text), []
    if rows is None or len(rows) != len(targets):
        problems.append("no load report")
    else:
        for path, row in zip(targets, rows):
            expected = _expected_scene(meshkit, path)
            actual_instances = sorted(sorted(surface) for surface in row["instances"])
            bounds_ok = bool(row["aabb"]) and all(
                abs(a - b) <= 1e-4 * max(1.0, abs(b)) for a, b in zip(row["aabb"], expected["aabb"]))
            entry = {"file": path.name if path.parent == package else "fresh_output.gltf", "error": row["error"],
                     "instances": len(actual_instances),
                     "surfaces_match": actual_instances == expected["instances"],
                     "bounds_match": bounds_ok, "animations": row["animations"],
                     "animations_match": row["animations"] == expected["animations"]}
            if not entry["surfaces_match"]:
                entry["godot"] = actual_instances[:4]
                entry["python"] = expected["instances"][:4]
            compared.append(entry)
            if row["error"] != 0 or not (entry["surfaces_match"] and bounds_ok and entry["animations_match"]):
                problems.append(f"{entry['file']} differs")
    passed = loaded["returncode"] == 0 and not loaded["timed_out"] and not problems
    checks.append(_check("godot_headless_gltf_load", passed,
                         {"files": compared, "problems": problems, "returncode": loaded["returncode"]}))

    preview = None
    shown = package / examples[0] if examples else outputs["system"][0]
    capture = workspace / "capture.png"
    rendered = engines.run(engine, ["--path", str(project), "--rendering-driver", "opengl3", "--audio-driver", "Dummy",
                                    "--resolution", "256x256", "--script", "res://render.gd", "--", str(shown),
                                    str(capture)], workspace=workspace, timeout=120, display=True,
                           environment=_godot_environment())
    problems = _error_lines(rendered["stdout"] + "\n" + rendered["stderr"])
    detail = {"file": shown.name if shown.parent == package else "fresh_output.gltf", "returncode": rendered["returncode"]}
    passed = False
    if rendered["returncode"] == 0 and not rendered["timed_out"] and capture.is_file() and not problems:
        try:
            image = pngio.decode(capture.read_bytes())
            width, height, channels = image["width"], image["height"], image["channels"]
            pixels = image["pixels"]
            rgb = bytearray()
            covered = 0
            means = [0.0, 0.0, 0.0]
            squares = [0.0, 0.0, 0.0]
            count = width * height
            for index in range(count):
                base = index * channels
                r, g, b = pixels[base], pixels[base + 1], pixels[base + 2]
                rgb += bytes((r, g, b))
                if max(abs(r - BACKGROUND[0]), abs(g - BACKGROUND[1]), abs(b - BACKGROUND[2])) > 10:
                    covered += 1
                for k, value in enumerate((r, g, b)):
                    means[k] += value
                    squares[k] += value * value
            deviation = [max(0.0, squares[k] / count - (means[k] / count) ** 2) ** 0.5 for k in range(3)]
            coverage = covered / count
            detail.update({"size": [width, height], "coverage": round(coverage, 4),
                           "channel_deviation": [round(d, 2) for d in deviation]})
            passed = (width, height) == (256, 256) and coverage >= 0.01 and max(deviation) >= 3.0
            if passed:
                preview = pngio.encode(width, height, bytes(rgb), 3)
        except pngio.PngError as error:
            detail["png_error"] = error.reason
    else:
        detail["problems"] = problems or [rendered["stderr"][-300:]]
    checks.append(_check("godot_compatibility_render", passed, detail))
    return {"engine": identity, "checks": checks, "preview": preview}
