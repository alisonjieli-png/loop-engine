"""Native verifier of the blender_tools family: every tool runs in the real Blender three ways, then reopens.

verify(context) runs three fresh Blender processes (background mode, factory settings, an isolated HOME) in the
item's workspace:

1. addon: installs the item's module from its exact bytes as a legacy add-on, enables it, builds the declared
   fixture, saves base.blend, runs the operator with the default parameters, compares the scene with the
   expectations that the module's pure core computes, saves addon.blend, evaluates animation samples and
   simulations, then disables the add-on and confirms that the operator is gone.
2. script: runs the module as a script on base.blend with the defaults given as command line arguments
   (blender --background base.blend --python TOOL.py -- --name value ... --output script.blend).
3. reopen: a process that never loads the tool opens addon.blend and script.blend, compares both with the same
   expectations, exports glTF (GLTF_SEPARATE) when the scene holds meshes and checks the .gltf JSON and its
   .bin buffer, then renders a small Cycles CPU preview.

Run inside Blender as ``blender --background --python native.py -- STAGE ARGUMENTS.json``, this same file performs
one stage and prints one line, ``BALTOR_STAGE_RESULT {json}``.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

RESULT_PREFIX = "BALTOR_STAGE_RESULT "
PREVIEW_SECONDS = 15.0
ERROR_MARKERS = ("Traceback (most recent call last)", "Error:")
OBJECT_TYPES_WITH_SURFACES = {"MESH", "CURVE", "SURFACE", "META", "FONT", "CURVES", "POINTCLOUD", "VOLUME"}
# Object.type values the Blender stages test one at a time, and the Driver.type of a driver that runs Python.
OBJECT_TYPE_MESH = "MESH"
OBJECT_TYPE_CURVE = "CURVE"
OBJECT_TYPE_SURFACE = "SURFACE"
OBJECT_TYPE_META = "META"
OBJECT_TYPE_FONT = "FONT"
OBJECT_TYPE_ARMATURE = "ARMATURE"
OBJECT_TYPE_LIGHT = "LIGHT"
DRIVER_TYPE_SCRIPTED = "SCRIPTED"
# The scene an item's operator runs on, verification.fixture in its contract: what the module's own fixture
# function builds, an empty scene, or one primitive mesh named Subject.
FIXTURE_MODULE = "module"
FIXTURE_NONE = "none"
FIXTURE_SPHERE = "sphere"
FIXTURE_MONKEY = "monkey"
FIXTURE_CUBE = "cube"
FIXTURE_PLANE = "plane"
# The environment variable that names the caller's user runtime folder, where the systemd user bus lives.
RUNTIME_FOLDER_VARIABLE = "XDG_RUNTIME_DIR"
# Parameter types whose values _arguments_text() writes in a form of their own; it writes the others with str().
PARAMETER_TYPE_BOOL = "bool"
PARAMETER_TYPE_FLOAT = "float"
PARAMETER_TYPE_VECTOR = "vector"


# ----------------------------------------------------------------------------------------------- verifier side
def _arguments_text(spec, value):
    if spec["type"] == PARAMETER_TYPE_BOOL:
        return "true" if value else "false"
    if spec["type"] == PARAMETER_TYPE_VECTOR:
        return ",".join(repr(float(item)) for item in value)
    if spec["type"] == PARAMETER_TYPE_FLOAT:
        return repr(float(value))
    return str(value)


def _stage_output(run):
    text = (run.get("stdout") or "") + "\n" + (run.get("stderr") or "")
    result = None
    for line in text.splitlines():
        if line.startswith(RESULT_PREFIX):
            try:
                result = json.loads(line[len(RESULT_PREFIX):])
            except ValueError:
                result = None
    errors = [line.strip()[:200] for line in text.splitlines() if any(marker in line for marker in ERROR_MARKERS)]
    return result, errors, text


def _check(name, passed, detail):
    return {"name": name, "state": "passed" if passed else "failed", "detail": detail}


def _preview_png(path: Path, pngio):
    """The rendered PNG re-encoded as 8-bit RGB without metadata, or (None, reason)."""
    if not path.is_file():
        return None, "no preview file"
    try:
        image = pngio.decode(path.read_bytes())
    except pngio.PngError as error:
        return None, f"preview unreadable: {error.reason}"
    if image["bit_depth"] != 8 or image["channels"] not in (3, 4):
        return None, f"preview format {image['channels']} channels at {image['bit_depth']} bits"
    channels, pixels = image["channels"], image["pixels"]
    if channels == 4:
        pixels = bytes(value for index, value in enumerate(pixels) if index % 4 != 3)
    spread = [max(pixels[channel::3]) - min(pixels[channel::3]) for channel in range(3)]
    if max(spread) < 8:
        return None, "preview is uniform"
    return pngio.encode(image["width"], image["height"], pixels, 3), None


def _runtime_environment():
    """engines.run probes systemd-run with the caller's environment but runs it with XDG_RUNTIME_DIR moved into
    the workspace, where the user bus is missing; passing the real runtime folder keeps the memory-capped scope."""
    import os
    folder = os.environ.get(RUNTIME_FOLDER_VARIABLE) or f"/run/user/{os.getuid()}"
    return {RUNTIME_FOLDER_VARIABLE: folder} if Path(folder, "bus").exists() else {}


def verify(context):
    from tools.creative_originals import pngio

    engine = context.engines.locate("blender")
    environment = _runtime_environment()
    workspace = Path(context.workspace)
    item, contract = context.item, context.item["contract"]
    identity = item["identity"]
    module_file = Path(context.item_dir) / f"{contract['module']}.py"
    native_file = Path(__file__).resolve()
    arguments = {"identity": identity, "module": contract["module"], "module_file": str(module_file),
                 "workspace": str(workspace), "contract": contract, "item_dir": str(context.item_dir)}
    (workspace / "arguments.json").write_text(json.dumps(arguments), encoding="utf-8")
    base = ["--background", "--factory-startup"]
    checks, details = [], {}

    run_a = context.engines.run(engine, [*base, "--python", str(native_file), "--", "addon",
                                         str(workspace / "arguments.json")], workspace=workspace, timeout=180,
                                environment=environment)
    stage_a, errors_a, text_a = _stage_output(run_a)
    if stage_a is None:
        checks.append(_check("addon_stage", False, {"returncode": run_a.get("returncode"),
                                                    "timed_out": run_a.get("timed_out"),
                                                    "errors": errors_a[:5], "tail": text_a[-1500:]}))
        return {"engine": engine.identity() | {"renderer": "background (Cycles CPU for previews)"},
                "checks": checks, "preview": None}
    checks.append(_check("addon_install_and_enable", stage_a.get("enabled") is True and stage_a.get(
        "operator_registered") is True, {"installed_as": stage_a.get("installed_as"),
                                         "operator": contract["entry_points"]["operator"]}))
    checks.append(_check("operator_runs_with_defaults", stage_a.get("operator") == ["FINISHED"],
                         {"result": stage_a.get("operator"), "fixture": stage_a.get("fixture"),
                          "error": stage_a.get("error")}))
    checks.append(_check("blender_data_matches_core", stage_a.get("mismatches") == [] and stage_a.get(
        "dynamic_mismatches") == [], {"mismatches": (stage_a.get("mismatches") or [])[:8],
                                      "dynamic_mismatches": (stage_a.get("dynamic_mismatches") or [])[:8],
                                      "summary": stage_a.get("summary"), "compared": stage_a.get("compared")}))
    checks.append(_check("addon_disable_unregisters", stage_a.get("disabled") is True,
                         {"operator_after_disable": stage_a.get("operator_after_disable")}))

    script_arguments = []
    for spec in contract["parameters"]:
        script_arguments += ["--" + spec["name"], _arguments_text(spec, spec["default"])]
    run_b = context.engines.run(engine, [*base, str(workspace / "base.blend"), "--python", str(module_file), "--",
                                         *script_arguments, "--output", str(workspace / "script.blend")],
                                workspace=workspace, timeout=180,
                                environment=environment)
    _stage_b, errors_b, text_b = _stage_output(run_b)
    script_saved = (workspace / "script.blend").is_file()
    checks.append(_check("script_mode_runs", run_b.get("returncode") == 0 and script_saved and not errors_b,
                         {"returncode": run_b.get("returncode"), "saved": script_saved, "errors": errors_b[:5],
                          "seconds": run_b.get("seconds")}))

    run_c = context.engines.run(engine, [*base, "--python", str(native_file), "--", "reopen",
                                         str(workspace / "arguments.json")], workspace=workspace, timeout=240,
                                environment=environment)
    stage_c, errors_c, text_c = _stage_output(run_c)
    if stage_c is None:
        checks.append(_check("reopen_stage", False, {"returncode": run_c.get("returncode"),
                                                     "errors": errors_c[:5], "tail": text_c[-1500:]}))
        return {"engine": engine.identity() | {"renderer": "background (Cycles CPU for previews)"},
                "checks": checks, "preview": None}
    for label in ("addon", "script"):
        row = stage_c.get(label) or {}
        checks.append(_check(f"clean_reopen_{label}_file", row.get("mismatches") == [] and row.get(
            "dynamic_mismatches") == [] and row.get("tool_loaded") is False,
            {"mismatches": (row.get("mismatches") or [])[:8], "dynamic_mismatches": (row.get(
                "dynamic_mismatches") or [])[:8], "tool_loaded": row.get("tool_loaded"),
             "summary": row.get("summary")}))
    gltf = stage_c.get("gltf")
    if gltf is not None:
        checks.append(_check("gltf_separate_export", gltf.get("problems") == [] and gltf.get("meshes", 0) > 0,
                             {key: gltf.get(key) for key in ("meshes", "nodes", "accessors", "materials",
                                                            "bin_bytes", "checked_objects", "problems")}))
    all_errors = errors_a + errors_b + errors_c
    checks.append(_check("engine_output_clean", not all_errors, {"errors": all_errors[:6]}))

    preview, reason = None, None
    render = stage_c.get("preview") or {}
    if render.get("seconds") is not None and render["seconds"] <= PREVIEW_SECONDS:
        preview, reason = _preview_png(workspace / "preview.png", pngio)
    else:
        reason = render.get("error") or f"render took {render.get('seconds')} s"
    details["preview"] = {"seconds": render.get("seconds"), "note": reason, "camera": render.get("camera")}
    checks[-1]["detail"]["preview"] = details["preview"]
    for name in ("base.blend", "addon.blend", "script.blend", "addon.blend1", "script.blend1", "base.blend1"):
        target = workspace / name
        if target.exists():
            target.unlink()
    for name in workspace.glob("export*"):
        name.unlink()
    return {"engine": engine.identity() | {"renderer": "background (Cycles CPU for previews)"},
            "checks": checks, "preview": preview}


# ------------------------------------------------------------------------------------------------ Blender side
def _plain(value):
    """A Blender value as JSON data: vectors, colours and arrays as lists, IDs by name."""
    import bpy
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, bpy.types.ID):
        return value.name
    if isinstance(value, bpy.types.bpy_struct):
        return getattr(value, "name", None) or type(value).__name__
    try:
        return [_plain(item) for item in value]
    except TypeError:
        return str(value)


def _same(expected, found, tolerance):
    if isinstance(expected, bool) or isinstance(expected, str) or expected is None:
        return expected == found
    if isinstance(expected, (int, float)):
        return (isinstance(found, (int, float)) and not isinstance(found, bool)
                and abs(expected - found) <= tolerance * max(1.0, abs(expected)))
    if isinstance(expected, (list, tuple)):
        return (isinstance(found, (list, tuple)) and len(expected) == len(found)
                and all(_same(a, b, tolerance) for a, b in zip(expected, found)))
    if isinstance(expected, dict):
        return isinstance(found, dict) and all(key in found and _same(value, found[key], tolerance)
                                               for key, value in expected.items())
    return False


def _fcurves(owner):
    """F-curves of an ID's action in Blender 4.2 to 5.x (legacy list or the slot's channel bag)."""
    data = getattr(owner, "animation_data", None)
    if data is None or data.action is None:
        return []
    action = data.action
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    from bpy_extras import anim_utils
    bag = anim_utils.action_get_channelbag_for_slot(action, data.action_slot)
    return list(bag.fcurves) if bag is not None else []


def _owners(obj):
    owners = [("", obj)]
    if obj.data is not None:
        owners.append(("data:", obj.data))
        keys = getattr(obj.data, "shape_keys", None)
        if keys is not None:
            owners.append(("shape_keys:", keys))
    return owners


def _mesh_bounds(mesh):
    count = len(mesh.vertices)
    if not count:
        return None
    flat = [0.0] * (3 * count)
    mesh.vertices.foreach_get("co", flat)
    return [[min(flat[axis::3]) for axis in range(3)], [max(flat[axis::3]) for axis in range(3)]]


def _measure_object(bpy, obj, spec):
    found = {"type": obj.type, "parent": obj.parent.name if obj.parent else None,
             "modifiers": [modifier.type for modifier in obj.modifiers],
             "constraints": [constraint.type for constraint in obj.constraints],
             "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
             "location": list(obj.location), "rotation_euler": list(obj.rotation_euler), "scale": list(obj.scale),
             "dimensions": list(obj.dimensions), "children": sorted(child.name for child in obj.children),
             "collections": sorted(collection.name for collection in obj.users_collection),
             "vertex_groups": [group.name for group in obj.vertex_groups], "hide_render": obj.hide_render,
             "data_name": obj.data.name if obj.data is not None else None,
             "instance_collection": obj.instance_collection.name if obj.instance_collection else None}
    if obj.type == OBJECT_TYPE_MESH:
        mesh = obj.data
        found.update(vertices=len(mesh.vertices), faces=len(mesh.polygons), edges=len(mesh.edges),
                     bounds=_mesh_bounds(mesh), uv_layers=[layer.name for layer in mesh.uv_layers],
                     color_attributes=[attribute.name for attribute in mesh.color_attributes],
                     shape_keys=[key.name for key in mesh.shape_keys.key_blocks] if mesh.shape_keys else [],
                     smooth_faces=sum(1 for polygon in mesh.polygons if polygon.use_smooth),
                     sharp_edges=sum(1 for edge in mesh.edges if edge.use_edge_sharp),
                     material_indices=sorted({polygon.material_index for polygon in mesh.polygons}))
    if obj.type in (OBJECT_TYPE_CURVE, OBJECT_TYPE_SURFACE):
        found.update(splines=len(obj.data.splines), points=sum(len(spline.bezier_points) or len(spline.points)
                                                                for spline in obj.data.splines))
    if obj.type == OBJECT_TYPE_ARMATURE:
        found["bones"] = sorted(bone.name for bone in obj.data.bones)
    if obj.type == OBJECT_TYPE_META:
        found["elements"] = len(obj.data.elements)
    if obj.type == OBJECT_TYPE_FONT:
        found["body"] = obj.data.body
    if "evaluated_vertices" in spec or "evaluated_faces" in spec or "evaluated_bounds" in spec:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        found.update(evaluated_vertices=len(mesh.vertices), evaluated_faces=len(mesh.polygons),
                     evaluated_bounds=_mesh_bounds(mesh))
        evaluated.to_mesh_clear()
    keyframes, drivers, simple = {}, 0, True
    for prefix, owner in _owners(obj):
        for curve in _fcurves(owner):
            keyframes[f"{prefix}{curve.data_path}[{curve.array_index}]"] = len(curve.keyframe_points)
        data = getattr(owner, "animation_data", None)
        if data is not None:
            for curve in data.drivers:
                drivers += 1
                driver = curve.driver
                if driver.type == DRIVER_TYPE_SCRIPTED and not driver.is_simple_expression:
                    simple = False
    found.update(keyframes=keyframes, drivers=drivers, drivers_simple=simple)
    found["attributes"] = {}
    for path in spec.get("attributes", {}):
        try:
            found["attributes"][path] = _plain(obj.path_resolve(path))
        except (ValueError, AttributeError, TypeError) as error:
            found["attributes"][path] = f"<unresolved: {error}>"
    found["custom"] = {key: _plain(obj[key]) for key in spec.get("custom", {}) if key in obj.keys()}
    return found


def _tree_summary(tree, output_types):
    types = {}
    for node in tree.nodes:
        types[node.bl_idname] = types.get(node.bl_idname, 0) + 1
    outputs = [node for node in tree.nodes if node.bl_idname in output_types]
    return {"nodes": len(tree.nodes), "links": len(tree.links), "node_types": types,
            "invalid_links": sum(1 for link in tree.links if not link.is_valid),
            "output_linked": any(socket.is_linked for node in outputs for socket in node.inputs)}


def _compare_tree(problems, label, tree, spec, output_types, extra=None):
    if tree is None:
        problems.append(f"{label}: no node tree")
        return
    summary = _tree_summary(tree, output_types)
    summary.update(extra or {})
    if summary["invalid_links"]:
        problems.append(f"{label}: {summary['invalid_links']} invalid links")
    for key, value in spec.items():
        if key == "tolerance":
            continue
        if not _same(value, summary.get(key), 1e-6):
            problems.append(f"{label}.{key}: expected {value}, found {summary.get(key)}")


def _compositor_tree(scene):
    if hasattr(scene, "compositing_node_group"):
        return scene.compositing_node_group
    return scene.node_tree if getattr(scene, "use_nodes", False) else None


def compare_static(bpy, expectations):
    """Differences between the open file and the expectations that do not need frame changes."""
    problems, compared = [], 0
    scene = bpy.context.scene
    for name, spec in expectations.get("objects", {}).items():
        obj = bpy.data.objects.get(name)
        if obj is None:
            problems.append(f"object missing: {name}")
            continue
        found = _measure_object(bpy, obj, spec)
        tolerance = spec.get("tolerance", 1e-4)
        for key, value in spec.items():
            if key == "tolerance":
                continue
            compared += 1
            if not _same(value, found.get(key, "<not measured>"), tolerance):
                problems.append(f"{name}.{key}: expected {value}, found {found.get(key, '<not measured>')}")
    output_types = {"materials": ("ShaderNodeOutputMaterial",), "worlds": ("ShaderNodeOutputWorld",)}
    for collection_name, outputs in output_types.items():
        for name, spec in expectations.get(collection_name, {}).items():
            datablock = getattr(bpy.data, collection_name).get(name)
            compared += 1
            if datablock is None:
                problems.append(f"{collection_name} missing: {name}")
                continue
            _compare_tree(problems, f"{collection_name}[{name}]", datablock.node_tree, spec, outputs,
                          {"users": datablock.users, "fake_user": datablock.use_fake_user})
    for name, spec in expectations.get("node_groups", {}).items():
        group = bpy.data.node_groups.get(name)
        compared += 1
        if group is None:
            problems.append(f"node group missing: {name}")
            continue
        _compare_tree(problems, f"node_groups[{name}]", group, spec, ("NodeGroupOutput",))
    if "compositor" in expectations:
        compared += 1
        _compare_tree(problems, "compositor", _compositor_tree(scene), expectations["compositor"],
                      ("NodeGroupOutput", "CompositorNodeComposite"))
    for name, spec in expectations.get("images", {}).items():
        image = bpy.data.images.get(name)
        compared += 1
        if image is None:
            problems.append(f"image missing: {name}")
            continue
        found = {"size": list(image.size), "source": image.source, "filepath_set": bool(image.filepath)}
        for key, value in spec.items():
            if not _same(value, found.get(key), 1e-6):
                problems.append(f"images[{name}].{key}: expected {value}, found {found.get(key)}")
    for name, spec in expectations.get("collections", {}).items():
        collection = bpy.data.collections.get(name)
        compared += 1
        if collection is None:
            problems.append(f"collection missing: {name}")
            continue
        found = {"objects": len(collection.objects), "children": sorted(child.name for child in collection.children),
                 "object_names": sorted(obj.name for obj in collection.objects)}
        for key, value in spec.items():
            if not _same(value, found.get(key), 1e-6):
                problems.append(f"collections[{name}].{key}: expected {value}, found {found.get(key)}")
    for name, spec in expectations.get("texts", {}).items():
        text = bpy.data.texts.get(name)
        compared += 1
        if text is None:
            problems.append(f"text missing: {name}")
            continue
        body = text.as_string()
        for fragment in spec.get("contains", []):
            if fragment not in body:
                problems.append(f"texts[{name}] lacks {fragment!r}")
    scene_spec = expectations.get("scene", {})
    for path, value in scene_spec.get("attributes", {}).items():
        compared += 1
        try:
            found = _plain(scene.path_resolve(path))
        except (ValueError, AttributeError, TypeError) as error:
            found = f"<unresolved: {error}>"
        if not _same(value, found, scene_spec.get("tolerance", 1e-4)):
            problems.append(f"scene.{path}: expected {value}, found {found}")
    for key in ("camera", "world"):
        if key in scene_spec:
            compared += 1
            found = getattr(scene, key).name if getattr(scene, key) is not None else None
            if found != scene_spec[key]:
                problems.append(f"scene.{key}: expected {scene_spec[key]}, found {found}")
    for key, value in expectations.get("counts", {}).items():
        compared += 1
        found = len(getattr(bpy.data, key))
        if found != value:
            problems.append(f"bpy.data.{key}: expected {value}, found {found}")
    return problems, compared


def compare_dynamic(bpy, expectations):
    """Animation samples after frame changes, then simulations stepped frame by frame."""
    problems = []
    scene = bpy.context.scene
    for sample in expectations.get("samples", []):
        obj = bpy.data.objects.get(sample["object"])
        if obj is None:
            problems.append(f"sample object missing: {sample['object']}")
            continue
        scene.frame_set(sample["frame"])
        try:
            if sample["path"] == "matrix_world.translation":
                value = list(obj.matrix_world.translation)
            else:
                value = _plain(obj.path_resolve(sample["path"]))
        except (ValueError, AttributeError, TypeError) as error:
            problems.append(f"sample {sample['object']}.{sample['path']}: {error}")
            continue
        if sample.get("index") is not None and isinstance(value, list):
            value = value[sample["index"]]
        if not _same(sample["value"], value, sample.get("tolerance", 1e-3)):
            problems.append(f"{sample['object']}.{sample['path']}[{sample.get('index')}] at frame {sample['frame']}:"
                            f" expected {sample['value']}, found {value}")
    simulation = expectations.get("simulate")
    if simulation:
        import mathutils
        start = scene.frame_start
        scene.frame_set(start)
        before = {}
        for check in simulation["checks"]:
            obj = bpy.data.objects.get(check["object"])
            if obj is not None:
                before[check["object"]] = _world_points(bpy, obj, mathutils)
        for frame in range(start, start + simulation["frames"] + 1):
            scene.frame_set(frame)
        for check in simulation["checks"]:
            obj = bpy.data.objects.get(check["object"])
            if obj is None:
                problems.append(f"simulated object missing: {check['object']}")
                continue
            points = _world_points(bpy, obj, mathutils)
            lowest = min(point.z for point in points)
            if check["kind"] == "rests_above" and lowest < check["z"] - check.get("tolerance", 0.05):
                problems.append(f"{check['object']} fell to z {lowest:.4f}, below {check['z']}")
            if check["kind"] in ("rests_above", "falls") and "below" in check and lowest > check["below"]:
                problems.append(f"{check['object']} stayed at z {lowest:.4f}, above {check['below']}")
            if check["kind"] == "moves":
                moved = max((a - b).length for a, b in zip(points, before.get(check["object"], points)))
                if moved < check["distance"]:
                    problems.append(f"{check['object']} moved {moved:.4f} m, less than {check['distance']}")
        scene.frame_set(start)
    return problems


def _world_points(bpy, obj, mathutils):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    if obj.type == OBJECT_TYPE_MESH:
        mesh = evaluated.to_mesh()
        points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        evaluated.to_mesh_clear()
        if points:
            return points
    return [evaluated.matrix_world @ mathutils.Vector(corner) for corner in evaluated.bound_box]


def scene_summary(bpy):
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == OBJECT_TYPE_MESH]
    return {"objects": len(bpy.context.scene.objects), "meshes": len(meshes),
            "vertices": sum(len(obj.data.vertices) for obj in meshes),
            "faces": sum(len(obj.data.polygons) for obj in meshes), "materials": len(bpy.data.materials),
            "node_groups": len(bpy.data.node_groups), "actions": len(bpy.data.actions),
            "cameras": len(bpy.data.cameras), "lights": len(bpy.data.lights), "images": len(bpy.data.images)}


def _fixture(bpy, module, contract, workspace):
    kind = contract.get("verification", {}).get("fixture", FIXTURE_NONE)
    if kind == FIXTURE_MODULE:
        getattr(module, contract["entry_points"]["fixture"])(bpy.context)
        return kind
    if kind == FIXTURE_NONE:
        return kind
    if kind == FIXTURE_SPHERE:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1.0, location=(0.0, 0.0, 1.0))
    elif kind == FIXTURE_MONKEY:
        bpy.ops.mesh.primitive_monkey_add(size=2.0, location=(0.0, 0.0, 1.0))
    elif kind == FIXTURE_CUBE:
        bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0.0, 0.0, 1.0))
    elif kind == FIXTURE_PLANE:
        bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0.0, 0.0, 0.0))
    else:
        raise ValueError(f"unknown fixture {kind}")
    subject = bpy.context.active_object
    subject.name = subject.data.name = "Subject"
    if kind in (FIXTURE_SPHERE, FIXTURE_MONKEY):
        subject.data.polygons.foreach_set("use_smooth", [True] * len(subject.data.polygons))
        subject.data.update()
    return kind


def stage_addon(arguments):
    import addon_utils
    import bpy
    workspace, contract = Path(arguments["workspace"]), arguments["contract"]
    name = arguments["module"]
    result = {"stage": "addon"}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_install(filepath=arguments["module_file"], overwrite=True)
    installed = Path(bpy.utils.user_resource("SCRIPTS", path="addons")) / f"{name}.py"
    result["installed_as"] = str(installed.relative_to(workspace)) if installed.is_file() else None

    def refuse(error):
        raise error

    module = addon_utils.enable(name, default_set=True, handle_error=refuse)
    result["enabled"] = module is not None and addon_utils.check(name)[1]
    group, operator_name = contract["entry_points"]["operator"].split(".")
    operator = getattr(getattr(bpy.ops, group), operator_name)
    try:
        operator.get_rna_type()
        result["operator_registered"] = True
    except KeyError:
        result["operator_registered"] = False
    result["fixture"] = _fixture(bpy, module, contract, workspace)
    bpy.ops.wm.save_as_mainfile(filepath=str(workspace / "base.blend"))
    try:
        result["operator"] = sorted(operator())
    except RuntimeError as error:
        result["operator"], result["error"] = ["ERROR"], str(error)[:400]
    expectations = getattr(module, contract["entry_points"].get("expectations", "expectations"))()
    (workspace / "expectations.json").write_text(json.dumps(expectations), encoding="utf-8")
    result["mismatches"], result["compared"] = compare_static(bpy, expectations)
    result["summary"] = scene_summary(bpy)
    bpy.ops.wm.save_as_mainfile(filepath=str(workspace / "addon.blend"))
    result["dynamic_mismatches"] = compare_dynamic(bpy, expectations)
    addon_utils.disable(name, default_set=True)
    try:
        operator.get_rna_type()
        result["operator_after_disable"] = "present"
    except KeyError:
        result["operator_after_disable"] = "absent"
    result["disabled"] = not addon_utils.check(name)[1] and result["operator_after_disable"] == "absent"
    return result


def _gltf_check(bpy, workspace):
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == OBJECT_TYPE_MESH and len(obj.data.polygons)]
    if not meshes:
        return None
    target = workspace / "export.gltf"
    bpy.ops.export_scene.gltf(filepath=str(target), export_format="GLTF_SEPARATE", use_selection=False,
                              export_apply=False, export_animations=False, export_cameras=True, export_lights=True)
    document = json.loads(target.read_text(encoding="utf-8"))
    problems = []
    if document.get("asset", {}).get("version") != "2.0":
        problems.append("asset.version is not 2.0")
    buffers = []
    for index, buffer in enumerate(document.get("buffers", [])):
        data = (workspace / buffer.get("uri", "")).read_bytes() if buffer.get("uri") else b""
        if len(data) != buffer.get("byteLength"):
            problems.append(f"buffer {index}: {len(data)} bytes, declared {buffer.get('byteLength')}")
        buffers.append(len(data))
    views = document.get("bufferViews", [])
    for index, view in enumerate(views):
        if view.get("buffer", -1) >= len(buffers) or view.get("byteOffset", 0) + view["byteLength"] > buffers[
                view["buffer"]]:
            problems.append(f"bufferView {index} exceeds its buffer")
    sizes = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
    widths = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
    accessors = document.get("accessors", [])
    for index, accessor in enumerate(accessors):
        view = views[accessor["bufferView"]] if accessor.get("bufferView", -1) < len(views) else None
        if view is None or accessor.get("count", 0) < 1:
            problems.append(f"accessor {index} has no data")
            continue
        element = sizes[accessor["type"]] * widths[accessor["componentType"]]
        stride = view.get("byteStride", element)
        if accessor.get("byteOffset", 0) + stride * (accessor["count"] - 1) + element > view["byteLength"]:
            problems.append(f"accessor {index} exceeds its bufferView")
    nodes = {node.get("name"): node for node in document.get("nodes", [])}
    checked = 0
    for obj in meshes:
        node = nodes.get(obj.name)
        if node is None or "mesh" not in node:
            problems.append(f"no glTF mesh node for {obj.name}")
            continue
        lows, highs = [], []
        for primitive in document["meshes"][node["mesh"]]["primitives"]:
            position = accessors[primitive["attributes"]["POSITION"]]
            if "min" not in position or "max" not in position:
                problems.append(f"{obj.name}: POSITION lacks min and max")
                continue
            lows.append(position["min"])
            highs.append(position["max"])
        if not lows:
            continue
        low = [min(row[axis] for row in lows) for axis in range(3)]
        high = [max(row[axis] for row in highs) for axis in range(3)]
        box = _mesh_bounds(obj.data)
        expected_low = [box[0][0], box[0][2], -box[1][1]]
        expected_high = [box[1][0], box[1][2], -box[0][1]]
        scale = max(1.0, max(abs(value) for value in expected_low + expected_high))
        if any(abs(a - b) > 1e-4 * scale for a, b in zip(low + high, expected_low + expected_high)):
            problems.append(f"{obj.name}: glTF bounds {low} {high} differ from Blender {expected_low} {expected_high}")
        checked += 1
    return {"meshes": len(document.get("meshes", [])), "nodes": len(document.get("nodes", [])),
            "accessors": len(accessors), "materials": len(document.get("materials", [])), "bin_bytes": sum(buffers),
            "checked_objects": checked, "problems": problems[:10]}


def _preview(bpy, workspace, contract):
    import mathutils
    config = contract.get("verification", {}).get("preview", {})
    if config.get("enabled", True) is False:
        return {"seconds": None, "error": "preview disabled for this item"}
    scene = bpy.context.scene
    if "frame" in config:
        scene.frame_set(config["frame"])
    depsgraph = bpy.context.evaluated_depsgraph_get()
    corners = []
    for obj in scene.objects:
        if obj.type in OBJECT_TYPES_WITH_SURFACES and not obj.hide_render and obj.visible_get():
            evaluated = obj.evaluated_get(depsgraph)
            points = []
            if obj.type == OBJECT_TYPE_MESH:
                mesh = evaluated.to_mesh()
                stride = max(1, len(mesh.vertices) // 4000)
                points = [evaluated.matrix_world @ mesh.vertices[index].co
                          for index in range(0, len(mesh.vertices), stride)]
                evaluated.to_mesh_clear()
            corners += points or [evaluated.matrix_world @ mathutils.Vector(corner) for corner in evaluated.bound_box]
    if not corners:
        corners = [mathutils.Vector((-1.0, -1.0, 0.0)), mathutils.Vector((1.0, 1.0, 1.0))]
    low = mathutils.Vector([min(point[axis] for point in corners) for axis in range(3)])
    high = mathutils.Vector([max(point[axis] for point in corners) for axis in range(3)])
    center, radius = (low + high) / 2.0, max((high - low).length / 2.0, 0.05)
    if config.get("floor"):
        floor_mesh = bpy.data.meshes.new("Preview Floor")
        size = radius * config.get("floor_size", 3.0)
        floor_mesh.from_pydata([(center.x - size, center.y - size, low.z), (center.x + size, center.y - size, low.z),
                                (center.x + size, center.y + size, low.z), (center.x - size, center.y + size, low.z)],
                               [], [(0, 1, 2, 3)])
        floor = bpy.data.objects.new("Preview Floor", floor_mesh)
        material = bpy.data.materials.new("Preview Floor")
        material.diffuse_color = (0.35, 0.35, 0.35, 1.0)
        if material.node_tree is None:
            material.use_nodes = True
        shader = next(node for node in material.node_tree.nodes if node.bl_idname == "ShaderNodeBsdfPrincipled")
        shader.inputs["Base Color"].default_value = (0.35, 0.35, 0.35, 1.0)
        shader.inputs["Roughness"].default_value = 0.8
        floor_mesh.materials.append(material)
        scene.collection.objects.link(floor)
    camera_name = config.get("camera")
    if camera_name and bpy.data.objects.get(camera_name) is not None:
        scene.camera = bpy.data.objects[camera_name]
    elif not (config.get("scene_camera") and scene.camera is not None):
        camera_data = bpy.data.cameras.new("Preview Camera")
        camera = bpy.data.objects.new("Preview Camera", camera_data)
        scene.collection.objects.link(camera)
        direction = mathutils.Vector(config.get("view", (1.0, -1.35, 0.8))).normalized()
        right = direction.cross(mathutils.Vector((0.0, 0.0, 1.0)))
        right = right.normalized() if right.length > 1e-6 else mathutils.Vector((1.0, 0.0, 0.0))
        up = right.cross(direction).normalized()
        reach = math.tan(camera_data.angle / 2.0) * config.get("fill", 0.86)
        distance = max(max((point - center).dot(direction) + abs((point - center).dot(axis)) / reach
                           for axis in (right, up)) for point in corners)
        distance = max(distance, radius * 0.5)
        camera.location = center + direction * distance
        camera.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
        camera_data.clip_start = max(0.001, min(0.1, distance * 0.01))
        camera_data.clip_end = distance + radius * 4.0 + 100.0
        scene.camera = camera
    if config.get("lights", "auto") == "auto" and not any(obj.type == OBJECT_TYPE_LIGHT for obj in scene.objects):
        sun_data = bpy.data.lights.new("Preview Sun", "SUN")
        sun_data.energy = config.get("sun", 3.0)
        sun_data.angle = math.radians(8.0)
        sun = bpy.data.objects.new("Preview Sun", sun_data)
        sun.rotation_euler = (math.radians(40.0), math.radians(15.0), math.radians(35.0))
        scene.collection.objects.link(sun)
    if scene.world is None:
        world = bpy.data.worlds.new("Preview World")
        if world.node_tree is None:
            world.use_nodes = True
        background = next(node for node in world.node_tree.nodes if node.bl_idname == "ShaderNodeBackground")
        background.inputs["Color"].default_value = (0.05, 0.055, 0.065, 1.0)
        background.inputs["Strength"].default_value = config.get("world_strength", 1.0)
        scene.world = world
    render = scene.render
    render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = config.get("samples", 16)
    scene.cycles.time_limit = 10.0
    scene.cycles.use_denoising = False
    render.resolution_x = render.resolution_y = config.get("resolution", 192)
    render.resolution_percentage = 100
    render.film_transparent = False
    render.threads_mode = "FIXED"
    render.threads = 4
    render.image_settings.file_format = "PNG"
    render.image_settings.color_mode = "RGB"
    render.image_settings.color_depth = "8"
    render.filepath = str(workspace / "preview.png")
    started = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    return {"seconds": round(time.perf_counter() - started, 3), "camera": scene.camera.name if scene.camera else None}


def stage_reopen(arguments):
    import bpy
    workspace, contract = Path(arguments["workspace"]), arguments["contract"]
    expectations = json.loads((workspace / "expectations.json").read_text(encoding="utf-8"))
    result = {"stage": "reopen"}
    for label in ("script", "addon"):
        path = workspace / f"{label}.blend"
        if not path.is_file():
            result[label] = {"mismatches": [f"{label}.blend was not saved"], "dynamic_mismatches": [],
                             "tool_loaded": arguments["module"] in sys.modules}
            continue
        bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
        mismatches, compared = compare_static(bpy, expectations)
        row = {"mismatches": mismatches, "compared": compared, "summary": scene_summary(bpy)}
        row["dynamic_mismatches"] = compare_dynamic(bpy, expectations)
        row["tool_loaded"] = arguments["module"] in sys.modules
        result[label] = row
    if (workspace / "addon.blend").is_file():
        bpy.ops.wm.open_mainfile(filepath=str(workspace / "addon.blend"), load_ui=False)
        result["gltf"] = _gltf_check(bpy, workspace)
        try:
            result["preview"] = _preview(bpy, workspace, contract)
        except Exception as error:  # a failed preview is reported, never a pass of anything else
            result["preview"] = {"seconds": None, "error": f"{type(error).__name__}: {error}"[:300]}
    return result


def _stage_main():
    arguments_after = sys.argv[sys.argv.index("--") + 1:]
    stage, path = arguments_after[0], arguments_after[1]
    arguments = json.loads(Path(path).read_text(encoding="utf-8"))
    handler = {"addon": stage_addon, "reopen": stage_reopen}[stage]
    try:
        result = handler(arguments)
    except Exception as error:
        import traceback
        traceback.print_exc()
        result = {"stage": stage, "fatal": f"{type(error).__name__}: {error}"[:500]}
    print(RESULT_PREFIX + json.dumps(result), flush=True)


if __name__ == "__main__":
    _stage_main()
