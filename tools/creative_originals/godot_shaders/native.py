"""Native verifier of the godot_shaders family: compile and render each item in Godot's Compatibility renderer.

For one item the verifier builds a throwaway Godot project in the workspace, copies the item's shader, material and
demo scene to ``res://baltor/godot_shaders/<identity>/`` and runs the pinned Godot build under Xvfb with the OpenGL 3
driver. A ``SceneTree`` script instantiates ``demo.tscn``, renders a fixed number of frames at a fixed 60 frames per
second, saves the frame, then removes the item's shader from the scene (the material is taken off a surface or a
canvas item; a full-screen pass, a particle system or a sky is hidden or replaced by a flat background), renders
again and saves the second frame.

Godot exits 0 even when a shader fails to compile, so a pass needs every check below:

* ``contract_static``: the shader, material and scene agree with the item contract (shared ``inspect_shader``).
* ``engine_run``: the engine ran to the end inside the time limit and exited 0.
* ``engine_log_clean``: no ``SHADER ERROR``, ``Shader compilation failed``, ``SCRIPT ERROR``, ``Parse Error`` or
  ``ERROR:`` line, and no warning that names the item's files. ``HARMLESS_LINES`` lists the exceptions (none so far).
* ``shader_in_scene``: the demo scene really uses the item's shader (found on at least one node).
* ``capture_written``: the capture script printed its marker and both frames decode as 256 x 256 PNG images.
* ``render_not_uniform``: the frame with the shader is not flat: some colour channel has a standard deviation of at
  least ``MINIMUM_DEVIATION`` and the most common colour covers at most ``MAXIMUM_MODE_SHARE`` of the pixels.
* ``shader_changes_pixels``: at least ``MINIMUM_CHANGED_PIXELS`` pixels differ by ``CHANGE_THRESHOLD`` or more (in
  some channel, out of 255) between the frame with the shader and the frame without it.

The preview is the frame with the shader. Nothing here shows behaviour in the Forward+ or Mobile renderers.
"""
from __future__ import annotations

import collections
import importlib
import importlib.util
import math
import os
import re
import shutil
from pathlib import Path

RESOLUTION = 256
RENDERER = "opengl3 compatibility (Mesa llvmpipe, Xvfb)"
PLACEMENT_ROOT = "baltor/godot_shaders"
ITEM_FILE_SUFFIXES = (".gdshader", ".tres", ".tscn")
#: Frames rendered before the first capture, per usage; particles need time to fill their volume.
FRAMES = {"particle_process_material": 90}
DEFAULT_FRAMES = 12
TIMEOUT_SECONDS = 120
ERROR_MARKERS = ("SHADER ERROR", "Shader compilation failed", "SCRIPT ERROR", "Parse Error", "ERROR:")
#: Engine lines that contain an error marker but do not concern the item. Each entry is a regular expression and the
#: reason it is safe. None has been needed on this host: every error line fails the item.
HARMLESS_LINES = ()
MINIMUM_DEVIATION = 2.0
MAXIMUM_MODE_SHARE = 0.99
CHANGE_THRESHOLD = 10
MINIMUM_CHANGED_PIXELS = 256
MARKER_DONE = "BALTOR_CAPTURE_DONE"
MARKER_USERS = "BALTOR_SHADER_USERS"
#: Render threads llvmpipe may use per engine run (LP_NUM_THREADS), so two parallel runs leave the shared host room.
LLVMPIPE_THREADS = 4
#: The user session variables systemd-run --user needs to reach the user manager (see run_environment).
USER_BUS_VARIABLES = ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS")

PROJECT = """config_version=5

[application]
config/name="baltor_godot_shaders_check"

[audio]
driver/driver="Dummy"

[display]
window/size/viewport_width=256
window/size/viewport_height=256

[rendering]
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
"""

CAPTURE = """extends SceneTree
## Renders a demo scene with the item's shader, removes the shader, renders again and saves both frames.
## Arguments after "--": SCENE SHADER OUT_WITH OUT_WITHOUT FRAMES MODE

var _shader_path := ""


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() < 6:
		print("BALTOR_CAPTURE_FAILED arguments")
		quit(2)
		return
	_shader_path = args[1]
	var packed := load(args[0]) as PackedScene
	if packed == null:
		print("BALTOR_CAPTURE_FAILED scene_not_loaded")
		quit(3)
		return
	var scene := packed.instantiate()
	root.add_child(scene)
	var users: Array = []
	_collect(scene, users)
	print("BALTOR_SHADER_USERS ", users.size())
	for i in int(args[4]):
		await process_frame
	await RenderingServer.frame_post_draw
	var with_shader := root.get_texture().get_image()
	with_shader.convert(Image.FORMAT_RGB8)
	with_shader.save_png(args[2])
	_strip(users, args[5])
	for i in 6:
		await process_frame
	await RenderingServer.frame_post_draw
	var without_shader := root.get_texture().get_image()
	without_shader.convert(Image.FORMAT_RGB8)
	without_shader.save_png(args[3])
	print("BALTOR_CAPTURE_DONE ", with_shader.get_width(), "x", with_shader.get_height())
	quit(0)


func _is_ours(material) -> bool:
	return material is ShaderMaterial and material.shader != null and material.shader.resource_path == _shader_path


func _ours(material) -> bool:
	var current = material
	while current != null:
		if _is_ours(current):
			return true
		current = current.next_pass
	return false


func _collect(node, users: Array) -> void:
	if node is GPUParticles3D or node is GPUParticles2D:
		if _ours(node.process_material):
			users.append(node)
	elif node is CanvasItem:
		if _ours(node.material):
			users.append(node)
	elif node is GeometryInstance3D:
		if _ours(node.material_override):
			users.append(node)
	elif node is WorldEnvironment:
		var environment = node.environment
		if environment != null and environment.sky != null and _ours(environment.sky.sky_material):
			users.append(node)
	for child in node.get_children():
		_collect(child, users)


func _without_ours(material):
	if _is_ours(material):
		return null
	var copy = material.duplicate()
	var current = copy
	while current != null:
		if current.next_pass != null and _is_ours(current.next_pass):
			current.next_pass = current.next_pass.next_pass
		else:
			current = current.next_pass
	return copy


func _strip(users: Array, mode: String) -> void:
	for node in users:
		if node is WorldEnvironment:
			node.environment.background_mode = Environment.BG_COLOR
			node.environment.background_color = Color(0.0, 0.0, 0.0)
		elif mode == "hide":
			node.visible = false
		elif node is CanvasItem:
			node.material = null
		elif node is GeometryInstance3D:
			node.material_override = _without_ours(node.material_override)
"""


def _sibling(context, name: str):
    """A framework module next to engines.py (pngio), imported through the framework package."""
    package = context.engines.__name__.rsplit(".", 1)[0]
    return importlib.import_module(f"{package}.{name}")


def _inspector(shared_dir: Path):
    specification = importlib.util.spec_from_file_location("godot_shaders_inspect_shader",
                                                           Path(shared_dir) / "inspect_shader.py")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def strip_mode(contract: dict) -> str:
    """How the second frame removes the shader: 'hide' its nodes or 'remove' the material from them."""
    usage = contract.get("usage", "")
    if usage in ("post_process_quad", "canvas_screen_overlay", "particle_process_material"):
        return "hide"
    return "remove"


def log_problems(text: str, placement: str) -> list:
    """Engine output lines that fail an item: error markers, and warnings that name the item's files."""
    problems = []
    for line in text.splitlines():
        if any(marker in line for marker in ERROR_MARKERS) or ("WARNING" in line and placement in line):
            if not any(re.search(pattern, line) for pattern, _reason in HARMLESS_LINES):
                problems.append(line.strip()[:300])
    return problems


def image_statistics(image: dict) -> dict:
    """Standard deviation per RGB channel and the share of the most common colour of an 8-bit decoded image."""
    channels, pixels = image["channels"], image["pixels"]
    count = image["width"] * image["height"]
    deviations = []
    for channel in range(min(channels, 3)):
        values = pixels[channel::channels]
        mean = sum(values) / count
        deviations.append(round(math.sqrt(sum((value - mean) ** 2 for value in values) / count), 3))
    colours = collections.Counter(pixels[index:index + 3] for index in range(0, len(pixels), channels))
    mode_share = colours.most_common(1)[0][1] / count
    return {"deviation_rgb": deviations, "mode_share": round(mode_share, 4), "distinct_colours": len(colours)}


def changed_pixels(first: dict, second: dict) -> dict:
    """How many pixels differ by at least CHANGE_THRESHOLD in some channel, and the mean absolute difference."""
    a, b = first["pixels"], second["pixels"]
    ca, cb = first["channels"], second["channels"]
    count = first["width"] * first["height"]
    changed, total = 0, 0
    for index in range(count):
        pa, pb = index * ca, index * cb
        difference = max(abs(a[pa] - b[pb]), abs(a[pa + 1] - b[pb + 1]), abs(a[pa + 2] - b[pb + 2]))
        total += difference
        if difference >= CHANGE_THRESHOLD:
            changed += 1
    return {"changed_pixels": changed, "changed_share": round(changed / count, 4),
            "mean_max_channel_difference": round(total / count, 3)}


def run_environment() -> dict:
    """Extra environment for the engine run.

    engines.run gives the engine an isolated HOME and XDG folders. When it wraps the run in a memory-capped
    ``systemd-run --user`` scope, systemd-run itself needs the real user runtime folder and session bus, which the
    isolated XDG_RUNTIME_DIR hides (it then exits 1 before Godot starts). They are passed through here. llvmpipe is
    held to four threads so two parallel runs leave the shared host room."""
    environment = {"LP_NUM_THREADS": str(LLVMPIPE_THREADS)}
    for key in USER_BUS_VARIABLES:
        if os.environ.get(key):
            environment[key] = os.environ[key]
    return environment


def _check(name: str, passed: bool, detail: dict) -> dict:
    return {"name": name, "state": "passed" if passed else "failed", "detail": detail}


def verify(context) -> dict:
    """Compile and render one item; return the engine identity, the checks and the preview PNG bytes."""
    engines = context.engines
    pngio = _sibling(context, "pngio")
    inspect = _inspector(context.shared_dir)
    item, identity = context.item, context.item["identity"]
    contract = item["contract"]
    checks = []

    static = inspect.check_item_files(context.item_dir, identity, contract)
    checks.append(_check("contract_static", not static["problems"], {"problems": static["problems"][:20]}))

    engine = engines.locate("godot")
    project = Path(context.workspace) / "project"
    placement_dir = project / PLACEMENT_ROOT / identity
    placement_dir.mkdir(parents=True)
    for row in item["files"]:
        if row["path"].endswith(ITEM_FILE_SUFFIXES):
            shutil.copyfile(Path(context.item_dir) / row["path"], placement_dir / row["path"])
    (project / "project.godot").write_text(PROJECT, encoding="utf-8")
    (project / "capture.gd").write_text(CAPTURE, encoding="utf-8")
    placement = f"res://{PLACEMENT_ROOT}/{identity}/"
    with_path, without_path = Path(context.workspace) / "with_shader.png", Path(context.workspace) / "without.png"
    frames = FRAMES.get(contract.get("usage"), DEFAULT_FRAMES)
    arguments = ["--path", str(project), "--rendering-driver", "opengl3", "--audio-driver", "Dummy",
                 "--resolution", f"{RESOLUTION}x{RESOLUTION}", "--fixed-fps", "60", "--script", "res://capture.gd",
                 "--", f"{placement}demo.tscn", f"{placement}{identity}.gdshader", str(with_path), str(without_path),
                 str(frames), strip_mode(contract)]
    outcome = engines.run(engine, arguments, workspace=Path(context.workspace), display=True,
                          timeout=TIMEOUT_SECONDS, environment=run_environment())
    log = (outcome.get("stdout") or "") + "\n" + (outcome.get("stderr") or "")
    ran = outcome.get("returncode") == 0 and not outcome.get("timed_out")
    run_detail = {"returncode": outcome.get("returncode"), "timed_out": outcome.get("timed_out"),
                  "error": outcome.get("error")}
    if not ran:
        run_detail["log_tail"] = log.strip()[-1500:]
    checks.append(_check("engine_run", ran, run_detail))
    problems = log_problems(log, placement)
    checks.append(_check("engine_log_clean", not problems, {"error_lines": problems[:12]}))
    users = re.findall(rf"^{MARKER_USERS} (\d+)", log, re.M)
    checks.append(_check("shader_in_scene", bool(users) and int(users[-1]) >= 1,
                         {"nodes_using_shader": int(users[-1]) if users else None}))

    images, preview = {}, None
    marker = bool(re.search(rf"^{MARKER_DONE} {RESOLUTION}x{RESOLUTION}", log, re.M))
    detail = {"marker": marker}
    for key, path in (("with", with_path), ("without", without_path)):
        try:
            data = path.read_bytes()
            image = pngio.decode(data)
            if (image["width"], image["height"], image["bit_depth"]) != (RESOLUTION, RESOLUTION, 8) \
                    or image["channels"] < 3:
                raise pngio.PngError("dimensions_invalid", f"{image['width']}x{image['height']}")
            images[key] = image
            if key == "with":
                preview = data
        except (OSError, pngio.PngError) as error:
            detail[key] = f"{type(error).__name__}: {error}"[:200]
    checks.append(_check("capture_written", marker and len(images) == 2, detail))

    if "with" in images:
        stats = image_statistics(images["with"])
        flat = max(stats["deviation_rgb"]) < MINIMUM_DEVIATION or stats["mode_share"] > MAXIMUM_MODE_SHARE
        checks.append(_check("render_not_uniform", not flat, stats))
    else:
        checks.append(_check("render_not_uniform", False, {"reason": "no frame"}))
    if len(images) == 2:
        change = changed_pixels(images["with"], images["without"])
        change["strip_mode"] = strip_mode(contract)
        checks.append(_check("shader_changes_pixels", change["changed_pixels"] >= MINIMUM_CHANGED_PIXELS, change))
    else:
        checks.append(_check("shader_changes_pixels", False, {"reason": "frames missing"}))

    passed = all(check["state"] == "passed" for check in checks)
    return {"engine": engine.identity() | {"renderer": RENDERER}, "checks": checks,
            "preview": preview if passed else None}
