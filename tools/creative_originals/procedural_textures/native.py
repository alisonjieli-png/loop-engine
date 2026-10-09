"""Native verification of a procedural texture item: generate, decode, check seams, render in Godot, build in Blender.

verify(context) copies the item and the shared files into a package folder, runs the item's command line under
the sandbox interpreter at 256 x 256 (default preset, seed 0) and records the measured time. A subprocess in the
package decodes every declared map with pngio and measures its wrap-around seams and its normal vectors. The maps
are then copied to res://baltor/textures/<identity>/ in a Godot 4 project, imported (--headless --import), and the
item's own material.tres is loaded and rendered under Xvfb with the Compatibility renderer: first on a sphere and a
tiled plane (the preview), then as a close-up of the plane at about one texel per pixel. Metering frames set the
tone-map exposure before each saved frame, so white and black materials do not clip; the close-up must show texture
detail far above an untextured control. Finally the item's blender_material.py builds its Principled BSDF material
from the same maps in Blender's background mode. Godot exits 0 even on errors, so every run's output is scanned for
ERROR lines and marker lines.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import time
from pathlib import Path

from tools.creative_originals import pngio as PNG
from tools.creative_originals.assemble import SANDBOX_PYTHON, SandboxEnvironment
from tools.creative_originals.records import FAILED, PASSED

INTERPRETER = SANDBOX_PYTHON
#: The environment the item's command line and the map analysis run with, as the qualification sandbox starts them.
SANDBOX = SandboxEnvironment()
SIZE = 256
SEED = 0
DEFAULT_PRESET = "default"
MAP_NAMES = (ALBEDO, NORMAL, ROUGHNESS, METALLIC, HEIGHT, AO, EMISSIVE) = (
    "albedo", "normal", "roughness", "metallic", "height", "ao", "emissive")
#: Maps decoded as sRGB colour; every other map is linear data.
SRGB_MAPS = (ALBEDO, EMISSIVE)
#: Maps that may legitimately hold one value (a whole-metal or whole-dielectric surface).
MAPS_THAT_MAY_BE_FLAT = (METALLIC,)
#: Blender node types and colour spaces the material check reads.
BSDF_NODE, OUTPUT_NODE = "ShaderNodeBsdfPrincipled", "ShaderNodeOutputMaterial"
TERMINAL_NODES = (BSDF_NODE, OUTPUT_NODE)
SURFACE_SOCKET = "Surface"
BLENDER_SPACES = (SRGB_SPACE, DATA_SPACE) = ("sRGB", "Non-Color")
TEXTURE_PROPERTIES = {ALBEDO: "albedo_texture", NORMAL: "normal_texture", ROUGHNESS: "roughness_texture",
                      METALLIC: "metallic_texture", HEIGHT: "heightmap_texture", AO: "ao_texture",
                      EMISSIVE: "emission_texture"}
BLENDER_TARGETS = {ALBEDO: (BSDF_NODE, "Base Color"), NORMAL: (BSDF_NODE, "Normal"),
                   ROUGHNESS: (BSDF_NODE, "Roughness"), METALLIC: (BSDF_NODE, "Metallic"),
                   HEIGHT: (OUTPUT_NODE, "Displacement"), EMISSIVE: (BSDF_NODE, "Emission Color")}
#: Output lines that mark a failed engine or interpreter run (Godot exits 0 even on a shader error).
ERROR_MARKERS = ("ERROR", "Shader compilation failed", "Traceback")
#: Variables passed through to engine runs so the memory-capped systemd scope can reach the user's service manager.
ENGINE_PASSTHROUGH = ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS")
#: The separator of the NAME=WIDTHxHEIGHT entries the capture script prints.
ENTRY_SEPARATOR = "="
#: Least mean neighbour difference (8-bit luminance) of the close-up for a textured surface. An untextured grey
#: material in the same scene measured 0.001 on October 9, 2026; the smoothest real item, brushed metal, 0.85.
CLOSE_UP_DETAIL = 0.25

PROJECT = """; Engine configuration file.
config_version=5

[application]
config/name="procedural_texture_preview"

[rendering]
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
"""

CAPTURE = """extends SceneTree
# Loads res://material.tres, renders it on a sphere and a tiled plane and saves that frame; then hides the sphere,
# moves the camera over the plane until one texel covers about one pixel and saves a close-up. Before each saved
# frame, three metering frames set the tone-map exposure so the frame's mean brightness sits near mid-grey, as a
# camera's automatic exposure would, so neither a white nor a black material clips. Prints marker lines.

const TARGET := 0.45
var frames := 0
var out_path := ""
var close_path := ""
var camera: Camera3D
var sphere: MeshInstance3D
var environment: Environment

func _initialize() -> void:
	out_path = OS.get_cmdline_user_args()[0]
	close_path = OS.get_cmdline_user_args()[1]
	var material = load("res://material.tres")
	if material == null or not (material is StandardMaterial3D):
		print("BALTOR_MATERIAL_MISSING")
		quit(3)
		return
	var loaded := []
	for prop in ["albedo_texture", "normal_texture", "roughness_texture", "metallic_texture", "ao_texture", "heightmap_texture", "emission_texture"]:
		var texture = material.get(prop)
		if texture != null:
			loaded.append("%s=%dx%d" % [prop, texture.get_width(), texture.get_height()])
	print("BALTOR_TEXTURES ", ",".join(loaded))
	var world := Node3D.new()
	root.add_child(world)
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.sky_top_color = Color(0.32, 0.42, 0.58)
	sky_material.sky_horizon_color = Color(0.66, 0.68, 0.70)
	sky_material.ground_horizon_color = Color(0.45, 0.43, 0.40)
	sky_material.ground_bottom_color = Color(0.20, 0.19, 0.18)
	var sky := Sky.new()
	sky.sky_material = sky_material
	environment = Environment.new()
	environment.background_mode = Environment.BG_SKY
	environment.sky = sky
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	environment.ambient_light_energy = 0.8
	environment.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	var holder := WorldEnvironment.new()
	holder.environment = environment
	world.add_child(holder)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-40, -35, 0)
	sun.light_energy = 1.3
	sun.shadow_enabled = true
	world.add_child(sun)
	camera = Camera3D.new()
	camera.fov = 46
	world.add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 2.0, 3.2), Vector3(0.0, 0.5, 0.0))
	camera.current = true
	var sphere_material = material.duplicate()
	sphere_material.uv1_scale = material.uv1_scale * Vector3(2, 1, 1)
	sphere = MeshInstance3D.new()
	var sphere_mesh := SphereMesh.new()
	sphere_mesh.radius = 0.72
	sphere_mesh.height = 1.44
	sphere_mesh.radial_segments = 64
	sphere_mesh.rings = 32
	sphere.mesh = sphere_mesh
	sphere.material_override = sphere_material
	sphere.position = Vector3(-0.1, 0.72, 0.0)
	world.add_child(sphere)
	var plane_material = material.duplicate()
	plane_material.uv1_scale = material.uv1_scale * Vector3(3, 3, 1)
	var plane := MeshInstance3D.new()
	var plane_mesh := PlaneMesh.new()
	plane_mesh.size = Vector2(6, 6)
	plane.mesh = plane_mesh
	plane.material_override = plane_material
	world.add_child(plane)

func _process(_delta: float) -> bool:
	# The waits live in helper coroutines: a _process that awaits returns early, which ends the main loop.
	frames += 1
	if frames == 4 or frames == 8 or frames == 12 or frames == 24 or frames == 28 or frames == 32:
		_meter()
	elif frames == 16:
		_save_overview()
	elif frames == 36:
		_save_close_up()
	return false

func _meter() -> void:
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	var total := 0.0
	var count := 0
	for y in range(0, image.get_height(), 4):
		for x in range(0, image.get_width(), 4):
			var colour := image.get_pixel(x, y)
			total += 0.2126 * colour.r + 0.7152 * colour.g + 0.0722 * colour.b
			count += 1
	var mean: float = max(total / count, 0.02)
	var step: float = clamp(pow(TARGET / mean, 2.0), 0.25, 4.0)
	environment.tonemap_exposure = clamp(environment.tonemap_exposure * step, 0.02, 8.0)

func _save_overview() -> void:
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	var status := image.save_png(out_path)
	print("BALTOR_CAPTURE ", status, " ", image.get_width(), "x", image.get_height())
	print("BALTOR_EXPOSURE overview=", environment.tonemap_exposure)
	# The plane repeats the tile every 2 units; from about 2.5 units away a 46 degree view spans about one tile.
	sphere.visible = false
	camera.look_at_from_position(Vector3(0.3, 2.3, 0.9), Vector3(0.3, 0.0, 0.0))

func _save_close_up() -> void:
	await RenderingServer.frame_post_draw
	var close := root.get_texture().get_image()
	var close_status := close.save_png(close_path)
	print("BALTOR_CLOSEUP ", close_status, " ", close.get_width(), "x", close.get_height())
	print("BALTOR_EXPOSURE close_up=", environment.tonemap_exposure)
	quit(0)
"""

ANALYSE = r'''
import json, math, sys
from pathlib import Path
import pngio, texkit
folder, identity, rows = Path(sys.argv[1]), sys.argv[2], json.loads(sys.argv[3])
report = {}
for row in rows:
    image = pngio.decode((folder / f"{identity}_{row['name']}.png").read_bytes())
    width, height, channels, pixels = image["width"], image["height"], image["channels"], image["pixels"]
    entry = {"size": [width, height], "channels": channels, "bit_depth": image["bit_depth"],
             "seams": texkit.seam_report(pixels, width, height, channels),
             "statistics": pngio.statistics(image)["channels"]}
    if row["name"] == "normal":
        worst, lowest = 0.0, 1.0
        for k in range(0, len(pixels), 3):
            x, y, z = (pixels[k + c] / 127.5 - 1.0 for c in range(3))
            worst = max(worst, abs(math.sqrt(x * x + y * y + z * z) - 1.0))
            lowest = min(lowest, z)
        entry["unit_length_error_max"] = round(worst, 4)
        entry["z_min"] = round(lowest, 4)
    report[row["name"]] = entry
print(json.dumps(report))
'''

BLENDER_CHECK = r'''
import importlib.util, json, sys
from pathlib import Path
arguments = sys.argv[sys.argv.index("--") + 1:]
package, maps = Path(arguments[0]), Path(arguments[1])
specification = importlib.util.spec_from_file_location("blender_material", package / "blender_material.py")
module = importlib.util.module_from_spec(specification)
specification.loader.exec_module(module)
material = module.build_material(str(maps))
report = {"material": material.name, "images": {}, "links": []}
for node in material.node_tree.nodes:
    if node.bl_idname == "ShaderNodeTexImage":
        image = node.image
        samples = len(image.pixels)
        report["images"][node.label] = {"size": list(image.size), "samples": samples,
                                        "colour_space": image.colorspace_settings.name}
for link in material.node_tree.links:
    report["links"].append([link.from_node.name, link.from_node.bl_idname, link.from_node.label,
                            link.from_socket.name, link.to_node.name, link.to_node.bl_idname, link.to_socket.name])
print("BALTOR_BLENDER " + json.dumps(report, sort_keys=True))
'''


def _engine_environment(engines) -> dict:
    """Variables for engines.run. An engines module that declares USER_BUS_VARIABLES reaches the user's service
    manager itself and keeps the engine isolated, so nothing is passed. An older one probes systemd-run with the
    caller's environment but runs it with an isolated one, so the memory-capped scope could not reach the user bus;
    for it the real runtime folder and bus address are passed through (without a user bus nothing changes)."""
    if getattr(engines, "USER_BUS_VARIABLES", None):
        return {}
    return {key: os.environ[key] for key in ENGINE_PASSTHROUGH if os.environ.get(key)}


def _errors(run: dict) -> list:
    lines = (run.get("stdout", "") + "\n" + run.get("stderr", "")).splitlines()
    return [line.strip()[:240] for line in lines if any(marker in line for marker in ERROR_MARKERS)][:8]


def _marker(run: dict, name: str) -> "str | None":
    for line in run.get("stdout", "").splitlines():
        if line.startswith(name + " "):
            return line[len(name) + 1:].strip()
    return None


def _reached(links: list, start: str) -> set:
    """(node type, input) of the BSDF and output sockets that node ``start`` feeds through intermediate nodes."""
    found, pending, seen = set(), [start], set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        for source, _kind, _label, _output, target, target_kind, socket in links:
            if source == current:
                if target_kind in TERMINAL_NODES:
                    found.add((target_kind, socket))
                else:
                    pending.append(target)
    return found


def _luma(image: dict) -> list:
    width, height, channels, pixels = image["width"], image["height"], image["channels"], image["pixels"]
    return [0.2126 * pixels[k] + 0.7152 * pixels[k + 1] + 0.0722 * pixels[k + 2]
            for k in range(0, width * height * channels, channels)]


def _neighbour_detail(luma: list, width: int, height: int, start: int) -> float:
    """Mean absolute luminance difference between neighbouring pixels from row ``start`` down: near zero for an
    untextured surface, whose lighting changes smoothly."""
    detail, count = 0.0, 0
    for y in range(start, height - 1):
        for x in range(width - 1):
            index = y * width + x
            detail += abs(luma[index] - luma[index + 1]) + abs(luma[index] - luma[index + width])
            count += 2
    return detail / max(count, 1)


def _capture_statistics(image: dict, close: dict) -> dict:
    """Luminance spread and distinct colours of the overview frame, the neighbour detail of its bottom third (only
    the textured plane is there) and the neighbour detail of the close-up, where one texel covers about one pixel."""
    width, height, channels, pixels = image["width"], image["height"], image["channels"], image["pixels"]
    luma = _luma(image)
    mean = sum(luma) / len(luma)
    spread = math.sqrt(sum((value - mean) ** 2 for value in luma) / len(luma))
    colours = {bytes(pixels[k:k + 3]) for k in range(0, width * height * channels, channels)}
    return {"luminance_mean": round(mean, 2), "luminance_spread": round(spread, 2), "distinct_colours": len(colours),
            "plane_detail": round(_neighbour_detail(luma, width, height, height * 2 // 3), 3),
            "close_up_detail": round(_neighbour_detail(_luma(close), close["width"], close["height"], 0), 3)}


def verify(context) -> dict:
    item, workspace = context.item, Path(context.workspace)
    identity = item["identity"]
    maps = item["contract"]["maps"]
    names = [row["name"] for row in maps]
    checks = []
    engine = {}

    def record(name: str, passed: bool, detail: dict) -> bool:
        checks.append({"name": name, "state": PASSED if passed else FAILED, "detail": detail})
        return passed

    def result(preview=None) -> dict:
        return {"engine": engine, "checks": checks, "preview": preview}

    package = workspace / "package"
    package.mkdir()
    for row in item["files"]:
        target = package / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(context.item_dir / row["path"], target)
    for row in context.family["shared_files"]:
        shutil.copyfile(context.shared_dir / row["path"], package / row["path"])
    folder = workspace / "maps"
    environment = SANDBOX.variables(workspace)
    version = subprocess.run([INTERPRETER, "-E", "-s", "-B", "-c", "import sys; print(sys.version.split()[0])"],
                             capture_output=True, text=True, timeout=60, env=environment).stdout.strip()
    engine["interpreter"] = {"name": "cpython", "version": version}
    started = time.monotonic()
    completed = subprocess.run([INTERPRETER, "-E", "-s", "-B", f"{identity}.py", "--size", str(SIZE), "--seed",
                                str(SEED), "--preset", DEFAULT_PRESET, "--out", str(folder)], cwd=package,
                               capture_output=True, text=True, timeout=900, env=environment)
    wall = round(time.monotonic() - started, 2)
    summary = {}
    if completed.returncode == 0 and completed.stdout.strip():
        summary = json.loads(completed.stdout.strip().splitlines()[-1])
    files = sorted(path.name for path in folder.glob("*.png")) if folder.is_dir() else []
    expected = sorted(f"{identity}_{name}.png" for name in names)
    if not record("command_line_generates_declared_maps", completed.returncode == 0 and files == expected,
                  {"size": SIZE, "preset": DEFAULT_PRESET, "seed": SEED, "files": files,
                   "generate_seconds": summary.get("generate_seconds"), "write_seconds": summary.get("write_seconds"),
                   "wall_seconds": wall, "stderr_tail": completed.stderr[-400:]}):
        return result()

    analysed = subprocess.run([INTERPRETER, "-E", "-s", "-B", "-c", ANALYSE, str(folder), identity, json.dumps(maps)],
                              cwd=package, capture_output=True, text=True, timeout=600, env=environment)
    if not record("maps_decode", analysed.returncode == 0, {"stderr_tail": analysed.stderr[-400:]}):
        return result()
    report = json.loads(analysed.stdout)
    shapes = {name: [report[name]["size"], report[name]["channels"], report[name]["bit_depth"]] for name in names}
    record("maps_have_declared_size_and_channels",
           all(shapes[row["name"]] == [[SIZE, SIZE], row["channels"], 8] for row in maps), {"maps": shapes})
    seams = {name: {"columns": [report[name]["seams"]["columns"]["seam"], report[name]["seams"]["columns"]["limit"]],
                    "rows": [report[name]["seams"]["rows"]["seam"], report[name]["seams"]["rows"]["limit"]]}
             for name in names}
    record("maps_tile_without_a_seam", all(report[name]["seams"]["passed"] for name in names),
           {"seam_and_limit": seams})
    normal = report[NORMAL]
    record("normal_vectors_unit_length_facing_out",
           normal["unit_length_error_max"] <= 0.025 and normal["z_min"] > 0.0,
           {"unit_length_error_max": normal["unit_length_error_max"], "z_min": normal["z_min"]})
    flat = [name for name in names if all(row["maximum"] - row["minimum"] < 3 for row in report[name]["statistics"])
            and name not in MAPS_THAT_MAY_BE_FLAT]
    record("maps_carry_detail", not flat, {"flat_maps": flat})

    godot = context.engines.locate("godot")
    engine.update(godot.identity())
    engine["renderer"] = "gl_compatibility"
    engine["display"] = "xvfb"
    project = workspace / "godot"
    textures = project / "baltor" / "textures" / identity
    textures.mkdir(parents=True)
    for name in names:
        shutil.copyfile(folder / f"{identity}_{name}.png", textures / f"{identity}_{name}.png")
    shutil.copyfile(context.item_dir / "material.tres", project / "material.tres")
    (project / "project.godot").write_text(PROJECT)
    (project / "capture.gd").write_text(CAPTURE)
    imported = context.engines.run(godot, ["--headless", "--path", str(project), "--import"], workspace=workspace,
                                   timeout=300, environment=_engine_environment(context.engines))
    import_errors = _errors(imported)
    if not record("godot_imports_the_maps", imported["returncode"] == 0 and not imported["timed_out"]
                  and not import_errors and len(list(textures.glob("*.png.import"))) == len(names),
                  {"returncode": imported["returncode"], "seconds": imported["seconds"], "errors": import_errors}):
        return result()
    capture, closeup = workspace / "capture.png", workspace / "closeup.png"
    rendered = context.engines.run(godot, ["--path", str(project), "--rendering-driver", "opengl3", "--audio-driver",
                                           "Dummy", "--resolution", f"{SIZE}x{SIZE}", "--script", "res://capture.gd",
                                           "--", str(capture), str(closeup)], workspace=workspace, display=True,
                                   timeout=300,
                                   environment=_engine_environment(context.engines))
    render_errors = _errors(rendered)
    loaded = dict(part.split(ENTRY_SEPARATOR, 1) for part in (_marker(rendered, "BALTOR_TEXTURES") or "").split(",")
                  if ENTRY_SEPARATOR in part)
    wanted = {TEXTURE_PROPERTIES[name]: f"{SIZE}x{SIZE}" for name in names}
    record("godot_material_template_loads_every_map", loaded == wanted, {"loaded": loaded})
    marker, close_marker = _marker(rendered, "BALTOR_CAPTURE"), _marker(rendered, "BALTOR_CLOSEUP")
    if not record("godot_compatibility_render", rendered["returncode"] == 0 and not rendered["timed_out"]
                  and not render_errors and marker == f"0 {SIZE}x{SIZE}" and close_marker == f"0 {SIZE}x{SIZE}"
                  and capture.is_file() and closeup.is_file(),
                  {"returncode": rendered["returncode"], "seconds": rendered["seconds"], "marker": marker,
                   "close_up_marker": close_marker, "errors": render_errors}):
        return result()
    image = PNG.decode(capture.read_bytes())
    statistics = _capture_statistics(image, PNG.decode(closeup.read_bytes()))
    record("capture_shows_the_textured_surface", statistics["luminance_spread"] > 8.0
           and statistics["distinct_colours"] > 200 and statistics["close_up_detail"] > CLOSE_UP_DETAIL, statistics)
    rgb = bytearray()
    pixels, channels = image["pixels"], image["channels"]
    for k in range(0, image["width"] * image["height"] * channels, channels):
        rgb += pixels[k:k + 3]
    preview = PNG.encode(image["width"], image["height"], bytes(rgb), 3)

    try:
        blender = context.engines.locate("blender")
    except context.engines.EngineUnavailable as error:
        record("blender_builds_the_material", False, {"error": str(error)[:300]})
        return result()
    engine["blender"] = blender.identity()
    script = workspace / "blender_check.py"
    script.write_text(BLENDER_CHECK)
    built = context.engines.run(blender, ["--background", "--factory-startup", "--python-exit-code", "1", "--python",
                                          str(script), "--", str(package), str(folder)], workspace=workspace,
                                timeout=300, environment=_engine_environment(context.engines))
    line = _marker(built, "BALTOR_BLENDER")
    details = {"returncode": built["returncode"], "seconds": built["seconds"], "errors": _errors(built)}
    passed = built["returncode"] == 0 and line is not None and not details["errors"]
    if passed:
        blender_report = json.loads(line)
        images = blender_report["images"]
        expected_spaces = {name: SRGB_SPACE if name in SRGB_MAPS else DATA_SPACE for name in names}
        problems = []
        for name in names:
            entry = images.get(name)
            if entry is None:
                problems.append(f"{name}: no image node")
                continue
            if entry["size"] != [SIZE, SIZE] or entry["samples"] != SIZE * SIZE * 4:
                problems.append(f"{name}: image not loaded at {SIZE}x{SIZE}")
            if entry["colour_space"] != expected_spaces[name]:
                problems.append(f"{name}: colour space {entry['colour_space']}")
            node = next((link[0] for link in blender_report["links"] if link[2] == name), None)
            if name in BLENDER_TARGETS and (node is None or BLENDER_TARGETS[name] not in
                                            _reached(blender_report["links"], node)):
                problems.append(f"{name}: does not reach {BLENDER_TARGETS[name][1]}")
        principled = next((link[0] for link in blender_report["links"] if link[1] == BSDF_NODE), None)
        if principled is None or (OUTPUT_NODE, SURFACE_SOCKET) not in _reached(blender_report["links"], principled):
            problems.append("the Principled BSDF does not reach the material output")
        details.update({"images": sorted(images), "links": len(blender_report["links"]), "problems": problems})
        passed = not problems
    record("blender_builds_the_material", passed, details)
    return result(preview)
