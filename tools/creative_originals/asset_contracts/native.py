"""Native verifier for asset_contracts: each checker's facts agree with Godot 4 and Blender on the same files.

For every item the verifier rebuilds the package layout in its workspace (the item's files and the shared files),
runs the item's command line on every fixture its contract lists, and requires each known-good fixture to pass
and each known-wrong fixture to fail with its declared codes. It then opens the same files in the pinned engines
and compares what the engines read (counts, names, hierarchy, world boxes, clips, bones, images) with what the
checker reported, and records how each engine reacts to each known-wrong file: refused, loaded with errors,
accepted silently, hung or crashed. Procedure items run their procedure in an engine and check the engine's own
output with the item's checker.

The engine scripts live in native_support/. Godot runs headless (the GLTFDocument API needs no renderer) unless an
item captures a preview; Blender runs in background mode with factory settings. Godot exits 0 even after errors,
so its output is scanned for ERROR lines; Blender's for Traceback and Error lines.
"""
from __future__ import annotations

import importlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from tools.creative_originals.assemble import LOCAL_SANDBOX_ENVIRONMENT, SANDBOX_PYTHON

SUPPORT = Path(__file__).resolve().parent / "native_support"
GODOT_PROJECT = ('config_version=5\n\n[application]\nconfig/name="asset_contracts_native"\n\n[rendering]\n'
                 'renderer/rendering_method="gl_compatibility"\n')
TOLERANCE = 1e-4


def close(left, right, tolerance: float = TOLERANCE) -> bool:
    """Numbers or nested lists equal within ``tolerance`` (absolute, plus a relative share for large values)."""
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(close(a, b, tolerance) for a, b in zip(left, right))
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(left - right) <= tolerance + 1e-5 * max(abs(left), abs(right))
    return left == right


def box_close(left: dict, right, tolerance: float = TOLERANCE) -> bool:
    if isinstance(right, (list, tuple)):
        right = {"min": list(right[0]), "max": list(right[1])}
    return close(left["min"], right["min"], tolerance) and close(left["max"], right["max"], tolerance)


def error_lines(text: str, markers=("ERROR", "SCRIPT ERROR", "Parse Error")) -> list:
    return [line.strip()[:220] for line in text.splitlines() if any(marker in line for marker in markers)]


class Session:
    """One item's verification: its package copy, its checker, the engines and the checks recorded so far."""

    def __init__(self, context) -> None:
        self.context, self.identity = context, context.item["identity"]
        self.workspace = Path(context.workspace)
        self.engines_module = context.engines
        self.checks, self.used = [], {}
        self.package = self.workspace / "package"
        self.package.mkdir()
        for row in context.item["files"]:
            target = self.package / row["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(context.item_dir) / row["path"], target)
        for row in context.family["shared_files"]:
            shutil.copyfile(Path(context.shared_dir) / row["path"], self.package / row["path"])
        self.contract = context.item["contract"]

    # Records ------------------------------------------------------------------------------------------

    def check(self, name: str, passed: bool, detail) -> bool:
        self.checks.append({"name": name, "state": "passed" if passed else "failed", "detail": self.clean(detail)})
        return passed

    def clean(self, value):
        """``value`` with this host's folders replaced, so a record names no home folder and repeats exactly."""
        if isinstance(value, str):
            for folder, label in ((str(self.package), "<package>"), (str(self.workspace), "<workspace>"),
                                  (str(Path(__file__).resolve().parent), "<family>"), (str(Path.home()), "~")):
                value = value.replace(folder, label)
            return value
        if isinstance(value, dict):
            return {str(self.clean(key)): self.clean(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.clean(item) for item in value]
        return value

    def result(self, preview: "bytes | None" = None) -> dict:
        names = sorted(self.used)
        engine = {"name": "_and_".join(names) or "python", "version": "; ".join(
            f"{name} {self.used[name].version}" for name in names) or sys.version.split()[0],
                  "renderer": "headless", "builds": {name: self.used[name].identity() for name in names}}
        return {"engine": engine, "checks": self.checks, "preview": preview}

    # The item's own command line --------------------------------------------------------------------

    def checker(self, argv: list, module: "str | None" = None) -> tuple:
        """(report or None, exit status, stderr tail) of the item's command line under the sandbox interpreter."""
        script = self.package / f"{module or self.identity}.py"
        arguments = [str(self.package / value) if not str(value).startswith("-") and (self.package / value).exists()
                     else str(value) for value in argv]
        done = subprocess.run([SANDBOX_PYTHON, "-E", "-s", "-B", str(script), *arguments], cwd=self.package,
                              capture_output=True, text=True, timeout=300,
                              env=LOCAL_SANDBOX_ENVIRONMENT.variables(self.workspace))
        try:
            report = json.loads(done.stdout)
        except ValueError:
            report = None
        return report, done.returncode, done.stderr[-600:]

    def run_fixtures(self) -> dict:
        """Run every contract fixture; record checker_matches_contract; return {" ".join(argv): row}."""
        rows, problems = {}, []
        for fixture in self.contract["fixtures"]:
            report, status, stderr = self.checker(fixture["argv"])
            codes = sorted({failure["code"] for failure in report["failures"]}) if report else None
            row = {"argv": fixture["argv"], "expect": fixture["expect"], "status": status, "codes": codes,
                   "report": report}
            if report is None:
                problems.append({"argv": fixture["argv"], "problem": "no JSON report", "stderr": stderr})
            elif fixture["expect"] == "pass" and (status != 0 or not report["ok"]):
                problems.append({"argv": fixture["argv"], "problem": "known-good fixture failed", "codes": codes})
            elif fixture["expect"] == "fail" and (status != 1 or not set(fixture["codes"]) <= set(codes)):
                problems.append({"argv": fixture["argv"], "problem": "known-wrong fixture not refused as declared",
                                 "declared": fixture["codes"], "codes": codes})
            rows[" ".join(fixture["argv"])] = row
        self.check("checker_matches_contract", not problems, {
            "fixtures": [{"argv": row["argv"], "expect": row["expect"], "status": row["status"], "codes": row["codes"]}
                         for row in rows.values()], "problems": problems})
        return rows

    def path(self, relative: str) -> Path:
        return self.package / relative

    def module(self, name: str):
        """Import a package module (standard library only). Shared modules are byte-identical in every package,
        so one cached copy serves every item; item modules are named after their unique identity."""
        if str(self.package) not in sys.path:
            sys.path.insert(0, str(self.package))
        return importlib.import_module(name)

    # Engines -----------------------------------------------------------------------------------------

    def engine(self, name: str):
        if name not in self.used:
            self.used[name] = self.engines_module.locate(name)
        return self.used[name]

    def godot_project(self) -> Path:
        project = self.workspace / "godot_project"
        if not project.is_dir():
            project.mkdir()
            (project / "project.godot").write_text(GODOT_PROJECT)
            for script in SUPPORT.glob("*.gd"):
                shutil.copyfile(script, project / script.name)
            for script in (self.package / "godot").glob("*.gd") if (self.package / "godot").is_dir() else []:
                shutil.copyfile(script, project / script.name)
        return project

    def godot(self, script: str, arguments: list, timeout: int = 120, display: bool = False,
              project: "Path | None" = None) -> dict:
        project = project or self.godot_project()
        flags = ["--path", str(project), "--script", f"res://{script}"]
        if display:
            flags = ["--rendering-driver", "opengl3", "--resolution", "256x256", *flags]
        else:
            flags = ["--headless", *flags]
        outcome = self.engines_module.run(self.engine("godot"), [*flags, "--", *map(str, arguments)],
                                          workspace=self.workspace, timeout=timeout, display=display)
        outcome["errors"] = error_lines(outcome.get("stdout", "") + "\n" + outcome.get("stderr", ""))
        return outcome

    def godot_inspect(self, files: list, timeout: int = 120, label: str = "godot") -> tuple:
        """(facts per file or None, outcome) from native_support/inspect_gltf.gd."""
        output = self.workspace / f"{label}_facts.json"
        if output.exists():
            output.unlink()
        outcome = self.godot("inspect_gltf.gd", [output, *files], timeout=timeout)
        facts = json.loads(output.read_text()) if output.is_file() else None
        return facts, outcome

    def blender(self, script: Path, arguments: list, timeout: int = 240) -> dict:
        outcome = self.engines_module.run(self.engine("blender"), ["--background", "--factory-startup", "--python",
                                                                   str(script), "--", *map(str, arguments)],
                                          workspace=self.workspace, timeout=timeout)
        outcome["errors"] = error_lines(outcome.get("stdout", "") + "\n" + outcome.get("stderr", ""),
                                        ("Traceback", "Error:"))
        return outcome

    def blender_file(self, blend: Path, script: Path, arguments: list, timeout: int = 180) -> dict:
        """Open a saved .blend (not factory settings) and run a script in it."""
        outcome = self.engines_module.run(self.engine("blender"), ["--background", str(blend), "--python",
                                                                   str(script), "--", *map(str, arguments)],
                                          workspace=self.workspace, timeout=timeout)
        outcome["errors"] = error_lines(outcome.get("stdout", "") + "\n" + outcome.get("stderr", ""),
                                        ("Traceback", "Error:"))
        return outcome

    def blender_inspect(self, files: list, timeout: int = 240, label: str = "blender") -> tuple:
        output = self.workspace / f"{label}_facts.json"
        if output.exists():
            output.unlink()
        outcome = self.blender(SUPPORT / "inspect_gltf_blender.py", [output, *files], timeout=timeout)
        facts = json.loads(output.read_text()) if output.is_file() else None
        return facts, outcome


def outcome_summary(outcome: dict) -> dict:
    return {"returncode": outcome.get("returncode"), "timed_out": outcome.get("timed_out"),
            "errors": outcome.get("errors", [])[:6], "stderr_tail": outcome.get("stderr", "")[-300:]}


def godot_reaction(facts: "dict | None", outcome: dict) -> dict:
    """How Godot treated one file: refused, loaded_with_errors, accepted_silently, timed_out or crashed."""
    if outcome.get("timed_out"):
        state = "timed_out"
    elif outcome.get("returncode") not in (0, None) or facts is None:
        state = "crashed"
    elif facts.get("error") != 0:
        state = "refused"
    elif outcome["errors"]:
        state = "loaded_with_errors"
    else:
        state = "accepted_silently"
    return {"state": state, "error_code": facts.get("error") if facts else None, "errors": outcome["errors"][:3]}


def blender_reaction(facts: dict) -> dict:
    if facts.get("error"):
        return {"state": "refused", "error": facts["error"]}
    return {"state": "accepted_silently", "objects": len(facts.get("objects", [])),
            "actions": sorted(action["name"] for action in facts.get("actions", []))}


def engine_reactions(session: Session, files: list, godot_timeout: int = 25) -> dict:
    """Godot (one process per file, so a hang or crash stays with its file) and Blender (one process) per file."""
    reactions = {}
    for path in files:
        facts, outcome = session.godot_inspect([path], timeout=godot_timeout, label="reaction")
        reactions[str(path)] = {"godot": godot_reaction(facts[0] if facts else None, outcome)}
    facts, outcome = session.blender_inspect(files, label="reactions")
    for path, row in zip(files, facts or [{}] * len(files)):
        reactions[str(path)]["blender"] = blender_reaction(row) if facts else {"state": "crashed",
                                                                              "outcome": outcome_summary(outcome)}
    return reactions


# Comparisons shared by the glTF items ----------------------------------------------------------------------


def morph_nodes(document: dict) -> set:
    nodes, meshes = document.get("nodes", []), document.get("meshes", [])
    return {index for index, node in enumerate(nodes) if isinstance(node.get("mesh"), int)
            and any(primitive.get("targets") for primitive in meshes[node["mesh"]].get("primitives", []))}


def joint_nodes(document: dict) -> set:
    return {joint for skin in document.get("skins", []) for joint in skin.get("joints", [])}


def compare_godot_geometry(gltfio, asset, facts: dict) -> list:
    """Per mesh node: the shared reader's world box against Godot's (meshes with morph targets are skipped,
    because Godot's box includes the morph displacement); per node: world origin against Godot's."""
    problems = []
    expected = gltfio.node_world_bounds(asset)
    skip = morph_nodes(asset.document) | joint_nodes(asset.document)
    for index, box in expected.items():
        if index in skip:
            continue
        found = facts.get("world_bounds", {}).get(str(index))
        if found is None or not box_close(found, box):
            problems.append({"node": index, "reader": box, "godot": found})
    matrices = gltfio.world_matrices(asset.document)
    for index, matrix in matrices.items():
        found = facts.get("node_transforms", {}).get(str(index))
        if index in joint_nodes(asset.document) or found is None:
            continue
        if not close(found["origin"], [matrix[0][3], matrix[1][3], matrix[2][3]]):
            problems.append({"node": index, "reader_origin": [row[3] for row in matrix[:3]], "godot": found["origin"]})
    return problems


def compare_blender_geometry(gltfio, asset, facts: dict) -> list:
    """Every non-joint node is a Blender object of the same name; mesh objects match world box and triangles."""
    problems, objects = [], {row["name"]: row for row in facts.get("objects", []) if not row.get("bone_shape")}
    nodes, joints = asset.items("nodes"), joint_nodes(asset.document)
    bones = {bone["name"] for row in objects.values() for bone in row.get("bones", [])}
    expected = gltfio.node_world_bounds(asset)
    for index, node in enumerate(nodes):
        name = node.get("name")
        if index in joints:
            if name not in bones:
                problems.append({"node": index, "name": name, "problem": "joint is not a Blender bone"})
            continue
        row = objects.get(name)
        if row is None:
            problems.append({"node": index, "name": name, "problem": "no Blender object of this name"})
            continue
        if index in expected:
            if row.get("type") != "MESH" or not box_close(row["world_bounds"], expected[index]):
                problems.append({"node": index, "name": name, "reader": expected[index],
                                 "blender": row.get("world_bounds")})
            elif row["triangles"] != gltfio.mesh_triangles(asset, node["mesh"]):
                problems.append({"node": index, "name": name, "reader_triangles": gltfio.mesh_triangles(
                    asset, node["mesh"]), "blender_triangles": row["triangles"]})
    return problems


# Items ---------------------------------------------------------------------------------------------------


def verify_gltf_structural_validator(session: Session):
    rows = session.run_fixtures()
    gltfio = session.module("gltfio")
    good = [key for key, row in rows.items() if row["expect"] == "pass"]
    bad = [key for key, row in rows.items() if row["expect"] == "fail"]
    paths = [session.path(key) for key in good]
    facts, outcome = session.godot_inspect(paths)
    problems = []
    if facts is None or outcome["errors"]:
        problems.append({"outcome": outcome_summary(outcome)})
    for key, found in zip(good, facts or []):
        reported = rows[key]["report"]["facts"]
        asset = gltfio.load(session.path(key))
        counts = {name: reported["counts"][name] for name in found["counts"]}
        if found["error"] != 0 or counts != found["counts"]:
            problems.append({"fixture": key, "checker_counts": counts, "godot_counts": found["counts"]})
        if [row["name"] for row in found["nodes"]] != reported["node_names"]:
            problems.append({"fixture": key, "checker_nodes": reported["node_names"],
                             "godot_nodes": [row["name"] for row in found["nodes"]]})
        if [row["name"] for row in found["gltf_animations"]] != reported["animation_names"]:
            problems.append({"fixture": key, "checker_clips": reported["animation_names"],
                             "godot_clips": [row["name"] for row in found["gltf_animations"]]})
        lengths = {clip["name"]: clip["length"] for clip in found["clips"]}
        for clip in reported["animations"]:
            if not close(lengths.get(clip["name"], -1.0), clip["duration"]):
                problems.append({"fixture": key, "clip": clip["name"], "checker": clip["duration"],
                                 "godot": lengths.get(clip["name"])})
        if found["materials"] != reported["material_names"]:
            problems.append({"fixture": key, "checker_materials": reported["material_names"],
                             "godot_materials": found["materials"]})
        problems += [{"fixture": key, **row} for row in compare_godot_geometry(gltfio, asset, found)]
    session.check("godot_agrees_on_known_good", not problems, {
        "files": good, "compared": "load result, counts, node, clip and material names, clip lengths, per-node "
                                   "world origins and boxes (meshes with morph targets excluded)",
        "problems": problems[:12]})
    facts, outcome = session.blender_inspect(paths)
    problems = []
    if facts is None or outcome["errors"]:
        problems.append({"outcome": outcome_summary(outcome)})
    for key, found in zip(good, facts or []):
        reported = rows[key]["report"]["facts"]
        asset = gltfio.load(session.path(key))
        if found.get("error"):
            problems.append({"fixture": key, "error": found["error"]})
            continue
        actions = {row["name"]: row["seconds"] for row in found["actions"]}
        for clip in reported["animations"]:
            if not close(actions.get(clip["name"], -1.0), clip["duration"]):
                problems.append({"fixture": key, "clip": clip["name"], "checker": clip["duration"],
                                 "blender": actions.get(clip["name"])})
        if sorted(found["materials"]) != sorted(reported["material_names"]):
            problems.append({"fixture": key, "checker_materials": reported["material_names"],
                             "blender_materials": found["materials"]})
        problems += [{"fixture": key, **row} for row in compare_blender_geometry(gltfio, asset, found)]
    session.check("blender_agrees_on_known_good", not problems, {
        "files": good, "compared": "import result, object and bone names, per-mesh world boxes and triangle "
                                   "counts, material names, action durations", "problems": problems[:12]})
    reactions = engine_reactions(session, [session.path(key) for key in bad])
    summary = {key: {"checker_codes": rows[key]["codes"], **reactions[str(session.path(key))]} for key in bad}
    refused = all(rows[key]["status"] == 1 for key in bad)
    silent = sorted(key for key, row in summary.items() if row["godot"]["state"] == "accepted_silently"
                    and row["blender"]["state"] == "accepted_silently")
    session.check("known_wrong_refused_with_engine_reactions", refused, {
        "fixtures": summary, "accepted_silently_by_both_engines": silent})
    return None


def recovered_against_godot(recovered: dict, found: dict) -> list:
    """The checker's recovered parts and clips against Godot's GLTFState and generated scene (by node index)."""
    problems = []
    if found.get("error") != 0:
        return [{"godot_error": found.get("error")}]
    nodes = found["nodes"]
    for part in recovered["parts"]:
        index = part["index"]
        node = nodes[index]
        parent = nodes[node["parent"]]["name"] if node["parent"] >= 0 else None
        if (node["name"] or None) != part["name"] or (parent or None) != part["parent"]:
            problems.append({"node": index, "checker": [part["name"], part["parent"]], "godot": [node["name"], parent]})
        box = found["world_bounds"].get(str(index))
        if part["bounds_m"] is not None and (box is None or not box_close(box, part["bounds_m"])):
            problems.append({"node": index, "checker_bounds": part["bounds_m"], "godot_bounds": box})
        origin = found["node_transforms"].get(str(index), {}).get("origin")
        if origin is None or not close(origin, part["pivot_m"]):
            problems.append({"node": index, "checker_pivot": part["pivot_m"], "godot_pivot": origin})
        if part["materials"] and found["surface_materials"].get(str(index)) != part["materials"]:
            problems.append({"node": index, "checker_materials": part["materials"],
                             "godot_materials": found["surface_materials"].get(str(index))})
    lengths = {clip["name"]: clip["length"] for clip in found["clips"]}
    if sorted(lengths) != sorted(clip["name"] for clip in recovered["clips"]):
        problems.append({"checker_clips": sorted(clip["name"] for clip in recovered["clips"]),
                         "godot_clips": sorted(lengths)})
    for clip in recovered["clips"]:
        if clip["name"] in lengths and not close(lengths[clip["name"]], clip["length_s"]):
            problems.append({"clip": clip["name"], "checker": clip["length_s"], "godot": lengths[clip["name"]]})
    return problems


def recovered_against_blender(recovered: dict, found: dict) -> list:
    """The checker's recovered parts and clips against Blender's imported objects and actions (by name; parts the
    file leaves unnamed are skipped, because Blender invents a name for them)."""
    if found.get("error"):
        return [{"blender_error": found["error"]}]
    problems, objects = [], {row["name"]: row for row in found["objects"] if not row.get("bone_shape")}
    for part in recovered["parts"]:
        if not part["name"]:
            continue
        row = objects.get(part["name"])
        if row is None:
            problems.append({"part": part["name"], "problem": "no Blender object of this name"})
            continue
        unnamed_parent = part["parent"] is None and part["parent_index"] is not None
        if not unnamed_parent and row["parent"] != part["parent"]:
            problems.append({"part": part["name"], "checker_parent": part["parent"], "blender_parent": row["parent"]})
        if part["bounds_m"] is not None and not box_close(row.get("world_bounds") or {"min": [], "max": []},
                                                          part["bounds_m"]):
            problems.append({"part": part["name"], "checker_bounds": part["bounds_m"],
                             "blender_bounds": row.get("world_bounds")})
        if not close(row["origin"], part["pivot_m"]):
            problems.append({"part": part["name"], "checker_pivot": part["pivot_m"], "blender_pivot": row["origin"]})
        if part["materials"] and row.get("materials") != part["materials"]:
            problems.append({"part": part["name"], "checker_materials": part["materials"],
                             "blender_materials": row.get("materials")})
    actions = {row["name"]: row["end_seconds"] for row in found["actions"]}
    if sorted(actions) != sorted(clip["name"] for clip in recovered["clips"]):
        problems.append({"checker_clips": sorted(clip["name"] for clip in recovered["clips"]),
                         "blender_actions": sorted(actions)})
    for clip in recovered["clips"]:
        if clip["name"] in actions and not close(actions[clip["name"]], clip["length_s"]):
            problems.append({"clip": clip["name"], "checker": clip["length_s"], "blender": actions[clip["name"]]})
    return problems


def verify_gltf_semantic_recovery(session: Session):
    rows = session.run_fixtures()
    assets, reports = [], {}
    for row in rows.values():
        if row["report"] and row["report"]["facts"] and row["argv"][0] not in reports:
            reports[row["argv"][0]] = row["report"]["facts"]
            assets.append(row["argv"][0])
    paths = [session.path(key) for key in assets]
    engine_facts = {}
    for engine, inspect, compare_facts in (("godot", session.godot_inspect, recovered_against_godot),
                                          ("blender", session.blender_inspect, recovered_against_blender)):
        facts, outcome = inspect(paths)
        engine_facts[engine] = facts or [{}]
        problems = [] if facts is not None and not outcome["errors"] else [{"outcome": outcome_summary(outcome)}]
        for key, found in zip(assets, facts or []):
            problems += [{"asset": key, **row} for row in compare_facts(reports[key], found)]
        session.check(f"{engine}_recovers_the_same_facts", not problems, {
            "assets": assets, "compared": "part names and parents, world boxes, pivots, part materials, clip names "
                                          "and play lengths, for known-good and known-wrong assets alike",
            "problems": problems[:12]})

    def shift_pivot(facts):
        facts["node_transforms"]["1"]["origin"][0] += 0.01

    def reparent(facts):
        next(row for row in facts["objects"] if row["name"] == "DoorHandle")["parent"] = "DoorFrame"

    comparator_control(session, [
        ("godot_pivot_moved_1cm", recovered_against_godot, reports[assets[0]], engine_facts["godot"][0], shift_pivot),
        ("blender_handle_reparented", recovered_against_blender, reports[assets[0]], engine_facts["blender"][0],
         reparent)])
    return None


def moving_samples(track: dict) -> bool:
    samples = track.get("samples", [])
    return any(not close(sample, samples[0], 1e-5) for sample in samples[1:])


def clips_against_godot(clips: list, found: dict) -> list:
    """Exported clips (checker facts) against Godot's AnimationPlayer: every clip name, and for clips with a playable
    channel the play length and the number of channels that move. Godot keeps a clip without playable channels as
    an empty 0.001 s clip and drops tracks whose value never changes, so those are not compared."""
    if found.get("error") != 0:
        return [{"godot_error": found.get("error")}]
    problems, godot = [], {clip["name"]: clip for clip in found["clips"]}
    if sorted(godot) != sorted(clip["name"] for clip in clips):
        problems.append({"checker_clips": sorted(clip["name"] for clip in clips), "godot_clips": sorted(godot)})
    for clip in clips:
        played = godot.get(clip["name"])
        playable = [channel for channel in clip["channels"] if channel["resolved"]]
        if played is None or not playable:
            continue
        moving = sum(1 for channel in playable if channel["moving"])
        godot_moving = sum(1 for track in played["tracks"] if track["resolved"] and moving_samples(track))
        if not close(played["length"], clip["length_s"]) or moving != godot_moving:
            problems.append({"clip": clip["name"], "checker": [clip["length_s"], moving],
                             "godot": [played["length"], godot_moving]})
    return problems


def clips_against_blender(clips: list, found: dict) -> list:
    """Exported clips against Blender's imported actions: names and end times of the clips with a playable channel
    (Blender drops a clip none of whose channels has a target)."""
    if found.get("error"):
        return [{"blender_error": found["error"]}]
    actions = {row["name"]: row for row in found["actions"]}
    playable = [clip for clip in clips if any(channel["resolved"] for channel in clip["channels"])]
    problems = []
    if sorted(actions) != sorted(clip["name"] for clip in playable):
        problems.append({"checker_clips": sorted(clip["name"] for clip in playable), "blender_actions": sorted(actions)})
    for clip in playable:
        if clip["name"] in actions and not close(actions[clip["name"]]["end_seconds"], clip["length_s"]):
            problems.append({"clip": clip["name"], "checker": clip["length_s"],
                             "blender": actions[clip["name"]]["end_seconds"]})
    return problems


def comparator_control(session: Session, cases: list) -> None:
    """Each case is (label, comparator, checker facts, engine facts, alteration). The comparator must accept the
    engine facts as they are and reject a copy that the alteration changes: a known-wrong control for the
    comparison itself."""
    rows = []
    for label, comparator, ours, theirs, alter in cases:
        altered = json.loads(json.dumps(theirs))
        alter(altered)
        rows.append({"case": label, "unaltered_problems": len(comparator(ours, theirs)),
                     "altered_problems": len(comparator(ours, altered))})
    session.check("comparator_rejects_altered_engine_facts", all(
        row["unaltered_problems"] == 0 and row["altered_problems"] > 0 for row in rows), {"cases": rows})


def verify_animation_export_trap_checker(session: Session):
    rows = session.run_fixtures()
    exports, clips = [], {}
    for row in rows.values():
        report = row["report"]
        if report and "export_clips" in report["facts"] and row["argv"][0] not in clips:
            clips[row["argv"][0]] = report["facts"]["export_clips"]
            exports.append(row["argv"][0])
    paths = [session.path(key) for key in exports]
    engine_facts = {}
    for engine, inspect, compare_facts in (("godot", session.godot_inspect, clips_against_godot),
                                          ("blender", session.blender_inspect, clips_against_blender)):
        facts, outcome = inspect(paths)
        engine_facts[engine] = facts or []
        problems = [] if facts is not None else [{"outcome": outcome_summary(outcome)}]
        for key, found in zip(exports, facts or []):
            problems += [{"export": key, **row} for row in compare_facts(clips[key], found)]
        session.check(f"{engine}_plays_the_same_clips", not problems, {
            "exports": exports, "compared": "clip names; for clips with a playable channel, play lengths and the number "
                                            "of moving channels (Godot samples five times per clip)" if engine ==
            "godot" else "names and end times of clips with a playable channel", "problems": problems[:12]})
    first = exports[0]
    comparator_control(session, [
        ("godot_length", clips_against_godot, clips[first], engine_facts["godot"][0],
         lambda facts: facts["clips"][0].update(length=facts["clips"][0]["length"] + 0.5)),
        ("blender_clip_dropped", clips_against_blender, clips[first], engine_facts["blender"][0],
         lambda facts: facts["actions"].pop())])
    # The trap itself, reproduced in Blender, then repaired by the item's procedure.
    work = session.workspace / "procedure"
    (work / "default").mkdir(parents=True)
    (work / "fixed").mkdir()
    blend, fixed, declared = work / "trap.blend", work / "fixed.blend", work / "declared.json"
    steps = [session.blender(SUPPORT / "build_trap_scene.py", [blend]),
             session.blender_file(blend, session.path("procedure/declare_clips_blender.py"), [declared]),
             session.blender_file(blend, SUPPORT / "export_gltf.py", [work / "default" / "door.gltf"])]
    report, status, _ = session.checker([str(work / "default" / "door.gltf"), "--declared", str(declared)])
    declared_names = sorted(clip["name"] for clip in json.loads(declared.read_text())["clips"]) \
        if declared.is_file() else None
    codes = sorted({failure["code"] for failure in report["failures"]}) if report else None
    session.check("trap_reproduced_by_blender_default_export", declared_names == ["Close", "Open"] and status == 1
                  and codes == ["clip_missing"] and report["failures"][0]["where"] == "Open", {
                      "declared_clips": declared_names, "exported_clips": [clip["name"] for clip in
                                                                           report["facts"]["export_clips"]]
                      if report else None, "checker_status": status, "checker_codes": codes,
                      "blender_errors": [error for step in steps for error in step["errors"]][:6]})
    steps = [session.blender_file(blend, session.path("procedure/push_actions_to_nla.py"), [fixed]),
             session.blender_file(fixed, SUPPORT / "export_gltf.py", [work / "fixed" / "door.gltf"])]
    report, status, _ = session.checker([str(work / "fixed" / "door.gltf"), "--declared", str(declared)])
    session.check("procedure_fix_exports_every_declared_clip", status == 0 and report is not None and report["ok"], {
        "exported_clips": [clip["name"] for clip in report["facts"]["export_clips"]] if report else None,
        "checker_status": status, "blender_errors": [error for step in steps for error in step["errors"]][:6]})
    facts, outcome = session.godot_inspect([work / "fixed" / "door.gltf"], label="fixed")
    played = {clip["name"]: clip["length"] for clip in (facts[0]["clips"] if facts else [])}
    session.check("godot_plays_the_repaired_export", sorted(played) == ["Close", "Open"] and all(
        close(length, 1.0) for length in played.values()) and not outcome["errors"], {
        "godot_clips": played, "errors": outcome["errors"][:4]})
    return None


def quaternion_close(found, expected, tolerance: float = 1e-3) -> bool:
    """Two unit quaternions describe the same rotation (q and -q are equal)."""
    return close(found, expected, tolerance) or close(found, [-value for value in expected], tolerance)


def axis_angle(axis, degrees: float) -> list:
    import math
    length = math.sqrt(sum(value * value for value in axis))
    half = math.radians(degrees) / 2.0
    return [value / length * math.sin(half) for value in axis] + [math.cos(half)]


def schema_agreement(session: Session, schema_path: str, documents: list) -> None:
    """The package's standard-library schema check (schema_lite) against the jsonschema library, draft 2020-12."""
    import jsonschema
    schema_lite = session.module("schema_lite")
    schema = json.loads(session.path(schema_path).read_text())
    rows, problems = [], []
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except jsonschema.SchemaError as error:
        problems.append({"schema_invalid": str(error)[:300]})
    unsupported = schema_lite.unsupported_keywords(schema)
    if unsupported:
        problems.append({"unsupported_keywords": unsupported[:10]})
    validator = jsonschema.Draft202012Validator(schema)
    for key in documents:
        value = json.loads(session.path(key).read_text())
        ours = not schema_lite.validate(value, schema)
        theirs = validator.is_valid(value)
        rows.append({"document": key, "schema_lite_valid": ours, "jsonschema_valid": theirs})
        if ours != theirs:
            problems.append({"document": key, "schema_lite_valid": ours, "jsonschema_valid": theirs})
    session.check("schema_agrees_with_jsonschema", not problems, {
        "jsonschema_version": __import__("importlib.metadata").metadata.version("jsonschema"),
        "documents": rows, "problems": problems})


def blockout_against_godot(spec: dict, found: dict) -> list:
    if found.get("error") != 0:
        return [{"godot_error": found.get("error")}]
    problems, nodes = [], {row["name"]: row for row in found["nodes"]}
    parts = {part["name"]: part for part in spec["parts"]}
    for name, part in parts.items():
        node = nodes.get(name)
        if node is None:
            problems.append({"part": name, "problem": "no Godot node"})
            continue
        parent = found["nodes"][node["parent"]]["name"] if node["parent"] >= 0 else None
        if parent != part.get("parent"):
            problems.append({"part": name, "spec_parent": part.get("parent"), "godot_parent": parent})
        pivot = part.get("pivot_m", part.get("center_m", [0, 0, 0]))
        origin = found["node_transforms"].get(str(node["index"]), {}).get("origin")
        if origin is None or not close(origin, pivot):
            problems.append({"part": name, "spec_pivot": pivot, "godot_origin": origin})
        if "dimensions_m" in part:
            center = part.get("center_m", pivot)
            box = {"min": [center[i] - part["dimensions_m"][i] / 2 for i in range(3)],
                   "max": [center[i] + part["dimensions_m"][i] / 2 for i in range(3)]}
            found_box = found["world_bounds"].get(str(node["index"]))
            if found_box is None or not box_close(found_box, box):
                problems.append({"part": name, "spec_box": box, "godot_box": found_box})
            wanted = part.get("material")
            first = wanted[0] if isinstance(wanted, list) else wanted
            if first is not None and found["surface_materials"].get(str(node["index"])) != [first]:
                problems.append({"part": name, "spec_material": first,
                                 "godot_materials": found["surface_materials"].get(str(node["index"]))})
    clips = {clip["name"]: clip for clip in found["clips"]}
    for joint in spec.get("joints", []):
        if joint["type"] not in ("revolute", "prismatic"):
            continue
        limits = joint["limits_deg"] if joint["type"] == "revolute" else joint["limits_m"]
        for label, limit in (("lower", limits[0]), ("upper", limits[1])):
            if limit == 0:
                continue
            clip = clips.get(f"{joint['name']}_{label}")
            if clip is None or not clip["tracks"]:
                problems.append({"joint": joint["name"], "limit": label, "problem": "no limit clip in Godot"})
                continue
            last = clip["tracks"][0]["samples"][-1]
            if joint["type"] == "revolute":
                expected = axis_angle(joint["axis"], limit)
                if not quaternion_close(last, expected):
                    problems.append({"joint": joint["name"], "limit": label, "expected_rotation": expected,
                                     "godot_rotation": last})
            else:
                part = parts[joint["part"]]
                parent = parts.get(part.get("parent")) or {}
                rest = [part["pivot_m"][i] - parent.get("pivot_m", [0, 0, 0])[i] for i in range(3)]
                expected = [rest[i] + joint["axis"][i] * limit for i in range(3)]
                if not close(last, expected):
                    problems.append({"joint": joint["name"], "limit": label, "expected_translation": expected,
                                     "godot_translation": last})
    return problems


def blockout_against_blender(spec: dict, found: dict) -> list:
    if found.get("error"):
        return [{"blender_error": found["error"]}]
    problems, objects = [], {row["name"]: row for row in found["objects"]}
    for part in spec["parts"]:
        row = objects.get(part["name"])
        if row is None:
            problems.append({"part": part["name"], "problem": "no Blender object"})
            continue
        pivot = part.get("pivot_m", part.get("center_m", [0, 0, 0]))
        if row["parent"] != part.get("parent") or not close(row["origin"], pivot):
            problems.append({"part": part["name"], "spec": [part.get("parent"), pivot],
                             "blender": [row["parent"], row["origin"]]})
        if "dimensions_m" in part:
            center = part.get("center_m", pivot)
            box = {"min": [center[i] - part["dimensions_m"][i] / 2 for i in range(3)],
                   "max": [center[i] + part["dimensions_m"][i] / 2 for i in range(3)]}
            if not box_close(row.get("world_bounds") or {"min": [], "max": []}, box):
                problems.append({"part": part["name"], "spec_box": box, "blender_box": row.get("world_bounds")})
    actions = {row["name"]: row for row in found["actions"]}
    for joint in spec.get("joints", []):
        if joint["type"] in ("revolute", "prismatic"):
            limits = joint["limits_deg"] if joint["type"] == "revolute" else joint["limits_m"]
            for label, limit in (("lower", limits[0]), ("upper", limits[1])):
                action = actions.get(f"{joint['name']}_{label}")
                if limit != 0 and (action is None or not close(action["end_seconds"], 1.0)):
                    problems.append({"joint": joint["name"], "limit": label, "blender_action": action})
    return problems


def verify_asset_specification_schema(session: Session):
    rows = session.run_fixtures()
    schema_agreement(session, "schema.json", list(rows))
    good = [key for key, row in rows.items() if row["expect"] == "pass"]
    blockouts = []
    for key in good:
        target = session.workspace / (Path(key).name.replace(".spec.json", "") + "_blockout.gltf")
        report, status, stderr = session.checker([key, "--blockout", str(target)])
        if status == 0 and target.is_file():
            blockouts.append((key, target))
        else:
            session.check("blockout_written", False, {"spec": key, "status": status, "stderr": stderr})
    specs = {key: json.loads(session.path(key).read_text()) for key, _target in blockouts}
    for engine, inspect, compare_facts in (("godot", session.godot_inspect, blockout_against_godot),
                                          ("blender", session.blender_inspect, blockout_against_blender)):
        facts, outcome = inspect([target for _key, target in blockouts])
        problems = [] if facts is not None and not outcome["errors"] else [{"outcome": outcome_summary(outcome)}]
        for (key, _target), found in zip(blockouts, facts or []):
            problems += [{"spec": key, **row} for row in compare_facts(specs[key], found)]
        session.check(f"{engine}_realises_each_valid_specification", bool(blockouts) and not problems, {
            "specs": [key for key, _target in blockouts],
            "compared": "part names and parents, pivots, world boxes from centre and dimensions, part materials, "
                        "and each joint limit clip ending at its limit" if engine == "godot" else
            "object names and parents, pivots and world boxes at frame 0, limit actions of 1 s",
            "problems": problems[:12]})
    return None


def pose_matches(found: dict, predicted: dict) -> bool:
    matrix = predicted["world_matrix"]
    columns = {"x": 0, "y": 1, "z": 2}
    return close(found["origin"], [row[3] for row in matrix]) and all(
        close(found[axis], [row[column] for row in matrix]) for axis, column in columns.items()) and \
        close(found["world_pivot"], predicted["world_pivot"])


def articulation_against_godot(predictions: list, found: dict, expect_clips: bool = True) -> list:
    """Godot's measured poses against the checker's forward kinematics, joint by joint and clip by clip."""
    if found.get("load_error") != 0:
        return [{"godot_load_error": found.get("load_error"), "errors": found.get("errors")}]
    problems, joints, clips = [], found.get("joints", {}), found.get("clips", {})
    for joint in predictions:
        measured = joints.get(joint["joint"])
        if measured is None:
            problems.append({"joint": joint["joint"], "problem": "not bound in Godot"})
            continue
        lower, upper = joint["limits"]
        for label, limit in (("lower", lower), ("upper", upper)):
            if not pose_matches(measured[label], joint[label]) or not close(measured[label]["applied"], limit):
                problems.append({"joint": joint["joint"], "limit": label, "godot": measured[label],
                                 "predicted": joint[label]})
            name = f"{joint['joint']}_{label}"
            if expect_clips and limit != 0 and (name not in clips or not pose_matches(clips[name], joint[label])):
                problems.append({"clip": name, "godot": clips.get(name), "predicted": joint[label]})
        if not close(measured["overshoot_applied"], upper) or not close(measured["undershoot_applied"], lower):
            problems.append({"joint": joint["joint"], "clamped_to": [measured["undershoot_applied"],
                                                                     measured["overshoot_applied"]], "limits": [lower, upper]})
        if joint["type"] == "hinge" and not close(measured["lower"]["world_pivot"], measured["upper"]["world_pivot"]):
            problems.append({"joint": joint["joint"], "problem": "the hinge pivot moved in Godot"})
    return problems


def verify_articulation_manifest_godot_builder(session: Session):
    rows = session.run_fixtures()
    schema_agreement(session, "schema.json", sorted({row["argv"][2] for row in rows.values()}))
    good = [row for row in rows.values() if row["expect"] == "pass"]
    bad = [row for row in rows.values() if row["expect"] == "fail"]
    loaded, reopened, saved = [], [], []
    for row in good:
        asset, manifest = row["argv"][0], row["argv"][2]
        stem = Path(asset).stem
        output = session.workspace / f"articulation_{stem}.json"
        outcome = session.godot("articulation_probe.gd", [output, "load", session.path(asset), session.path(manifest),
                                                          f"res://built_{stem}.tscn"])
        found = json.loads(output.read_text()) if output.is_file() else {"load_error": "no output"}
        loaded.append((row, found, outcome))
        saved.append(found.get("save_error"))
        output = session.workspace / f"reopen_{stem}.json"
        outcome = session.godot("articulation_probe.gd", [output, "reopen", f"res://built_{stem}.tscn"])
        reopened.append((row, json.loads(output.read_text()) if output.is_file() else {"load_error": "no output"},
                         outcome))
    problems = []
    for row, found, outcome in loaded:
        problems += [{"asset": row["argv"][0], **item} for item in articulation_against_godot(
            row["report"]["facts"]["joints"], {**found, "clips": {}}, expect_clips=False)]
        if outcome["errors"]:
            problems.append({"asset": row["argv"][0], "errors": outcome["errors"][:4]})
    session.check("godot_moves_each_joint_to_its_limits", bool(loaded) and not problems, {
        "assets": [row["argv"][0] for row, _found, _outcome in loaded],
        "compared": "global origin, basis and world pivot of each moving node at both limits against the checker's "
                    "forward kinematics; values clamped to the limits; hinge pivots fixed", "problems": problems[:10]})
    problems = []
    for row, found, _outcome in loaded:
        problems += [{"asset": row["argv"][0], **item} for item in articulation_against_godot(
            row["report"]["facts"]["joints"], found) if "clip" in item]
    session.check("godot_joint_player_reaches_each_limit", bool(loaded) and not problems, {
        "clips": {row["argv"][0]: sorted(found.get("clips", {})) for row, found, _outcome in loaded},
        "problems": problems[:10]})
    problems = []
    for row, found, outcome in reopened:
        problems += [{"asset": row["argv"][0], **item} for item in articulation_against_godot(
            row["report"]["facts"]["joints"], found)]
        if outcome["errors"]:
            problems.append({"asset": row["argv"][0], "errors": outcome["errors"][:4]})
    session.check("godot_reopens_the_built_scene", all(error == 0 for error in saved) and not problems, {
        "save_errors": saved, "compared": "the saved scene, opened in a new Godot process, binds the same joints, "
                                          "reaches the same poses and plays the same clips", "problems": problems[:10]})
    rejected = []
    for row in bad:
        asset, manifest = row["argv"][0], row["argv"][2]
        output = session.workspace / f"rejected_{Path(manifest).stem}_{Path(asset).stem}.json"
        session.godot("articulation_probe.gd", [output, "load", session.path(asset), session.path(manifest)])
        found = json.loads(output.read_text()) if output.is_file() else {"load_error": "no output"}
        rejected.append({"fixture": row["argv"], "checker_codes": row["codes"], "godot_load_error":
                         found.get("load_error"), "godot_errors": found.get("errors", [])[:2]})
    session.check("godot_builder_refuses_each_known_wrong_binding", all(
        item["godot_load_error"] not in (0, None) and item["godot_errors"] for item in rejected), {"fixtures": rejected})
    gltfio = session.module("gltfio")
    files = sorted({row["argv"][0] for row in good})
    facts, outcome = session.blender_inspect([session.path(key) for key in files])
    problems = [] if facts is not None else [{"outcome": outcome_summary(outcome)}]
    for key, found in zip(files, facts or []):
        asset = gltfio.load(session.path(key))
        matrices = gltfio.world_matrices(asset.document)
        objects = {item["name"]: item for item in found.get("objects", [])}
        report = next(row["report"] for row in good if row["argv"][0] == key)
        for joint in report["facts"]["joints"]:
            index = [node.get("name") for node in asset.items("nodes")].index(joint["node"])
            expected = [matrices[index][line][3] for line in range(3)]
            item = objects.get(joint["node"])
            if item is None or not close(item["origin"], expected):
                problems.append({"asset": key, "node": joint["node"], "expected_origin": expected,
                                 "blender": item and item["origin"]})
    session.check("blender_finds_every_bound_node", not problems, {
        "assets": files, "compared": "each joint's node exists as a Blender object at the same world origin",
        "problems": problems[:10]})
    return None


def unit(vector) -> list:
    import math
    length = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / length for value in vector]


def joint_facts_godot(found: dict, joint: dict) -> dict:
    """One manifest joint as Godot sees the loaded asset: presence, parent, world pivot and axis, extras record."""
    matches = [row for row in found.get("nodes", []) if row["name"] == joint["node"]]
    facts = {"count": len(matches)}
    if len(matches) != 1:
        return facts
    node = matches[0]
    transform = found["node_transforms"].get(str(node["index"]), {})
    parent = found["nodes"][node["parent"]]["name"] if node["parent"] >= 0 else None
    columns = [transform.get("x", [0, 0, 0]), transform.get("y", [0, 0, 0]), transform.get("z", [0, 0, 0])]
    pivot, axis = joint.get("pivot", [0, 0, 0]), joint["axis"]
    facts.update({"parent": parent, "extras": (transform.get("extras") or {}).get("joint"),
                  "world_pivot": [transform.get("origin", [0, 0, 0])[row] + sum(columns[k][row] * pivot[k]
                                                                               for k in range(3)) for row in range(3)],
                  "world_axis": unit([sum(columns[k][row] * axis[k] for k in range(3)) for row in range(3)])})
    return facts


def joint_facts_blender(found: dict, joint: dict) -> dict:
    """One manifest joint as Blender sees the imported asset (converted back to glTF axes)."""
    matches = [row for row in found.get("objects", []) if row["name"] == joint["node"]]
    facts = {"count": len(matches)}
    if len(matches) != 1:
        return facts
    row = matches[0]
    matrix = row["matrix_world"]
    pivot, axis = joint.get("pivot", [0, 0, 0]), joint["axis"]
    local_pivot = [pivot[0], -pivot[2], pivot[1]]
    local_axis = [axis[0], -axis[2], axis[1]]
    world_pivot = [sum(matrix[line][k] * local_pivot[k] for k in range(3)) + matrix[line][3] for line in range(3)]
    world_axis = [sum(matrix[line][k] * local_axis[k] for k in range(3)) for line in range(3)]
    facts.update({"parent": row["parent"], "extras": row.get("custom_properties", {}).get("joint"),
                  "world_pivot": [world_pivot[0], world_pivot[2], -world_pivot[1]],
                  "world_axis": unit([world_axis[0], world_axis[2], -world_axis[1]])})
    return facts


def joint_rows_agree(checker: dict, engine: dict) -> bool:
    if checker["count"] != engine["count"]:
        return False
    if checker["count"] != 1:
        return True
    return checker["parent"] == engine["parent"] and close(checker["world_pivot"], engine["world_pivot"]) and \
        close(checker["world_axis"], engine["world_axis"], 1e-3) and (checker["extras"] is None) == \
        (engine["extras"] is None) and (checker["extras"] is None or close(checker["extras"].get("limits"),
                                                                           engine["extras"].get("limits")))


def verify_articulation_loss_checker(session: Session):
    rows = session.run_fixtures()
    manifest_path = "fixtures/door_reference.articulation.json"
    joints = json.loads(session.path(manifest_path).read_text())["joints"]
    exports, facts_by_export = [], {}
    for row in rows.values():
        report = row["report"]
        if report and report["facts"].get("joints") and row["argv"][0] not in facts_by_export:
            facts_by_export[row["argv"][0]] = {item["joint"]: {"count": item["export"]["count"], **item["export"]}
                                               for item in report["facts"]["joints"]}
            exports.append(row["argv"][0])
    for engine, inspect, convert in (("godot", session.godot_inspect, joint_facts_godot),
                                    ("blender", session.blender_inspect, joint_facts_blender)):
        facts, outcome = inspect([session.path(key) for key in exports])
        problems = [] if facts is not None else [{"outcome": outcome_summary(outcome)}]
        for key, found in zip(exports, facts or []):
            for joint in joints:
                ours, theirs = facts_by_export[key][joint["name"]], convert(found, joint)
                if not joint_rows_agree(ours, theirs):
                    problems.append({"export": key, "joint": joint["name"], "checker": ours, engine: theirs})
        session.check(f"{engine}_sees_the_same_joint_facts", not problems, {
            "exports": exports, "compared": "per manifest joint: node count, parent, world pivot, world axis and the "
                                            "extras joint record", "problems": problems[:8]})
    work = session.workspace / "losses"
    work.mkdir()
    blend = work / "loss.blend"
    manifest = work / "door.articulation.json"
    manifest.write_text(json.dumps({"record_type": "articulation_manifest/v1", "asset": "door.gltf", "joints": [
        {"name": "door_hinge", "type": "hinge", "node": "Door", "axis": [0.0, 1.0, 0.0], "pivot": [0.0, 0.0, 0.0],
         "limits": [0.0, 95.0], "rest": 0.0}]}))
    steps = [session.blender(SUPPORT / "build_loss_scene.py", [blend])]
    for mode in ("reference", "default", "origin", "join"):
        (work / mode).mkdir()
        steps.append(session.blender_file(blend, SUPPORT / "loss_variants.py", [mode, work / mode / "door.gltf"]))
    reference = str(work / "reference" / "door.gltf")
    expected = {"reference": [], "default": ["joint_extras_missing"], "origin": ["pivot_moved"],
                "join": ["joint_node_missing"]}
    results = {}
    for mode in expected:
        report, status, _ = session.checker([str(work / mode / "door.gltf"), "--manifest", str(manifest),
                                             "--reference", reference, "--extras", "required"])
        results[mode] = sorted({failure["code"] for failure in report["failures"]}) if report else None
    session.check("each_blender_loss_is_caught", results == expected, {
        "steps": "built a framed door whose joint record is a custom property, exported it with custom properties "
                 "(reference), with defaults, after origin to geometry, and after joining the door into the frame",
        "checker_codes": results, "expected": expected,
        "blender_errors": [error for step in steps for error in step["errors"]][:6]})
    facts, outcome = session.godot_inspect([work / "reference" / "door.gltf", work / "default" / "door.gltf"],
                                           label="carried")
    joint = json.loads(manifest.read_text())["joints"][0]
    carried = [joint_facts_godot(found, joint).get("extras") for found in facts or [{}, {}]]
    session.check("godot_reads_the_carried_joint_record", facts is not None and carried[0] is not None and
                  close(carried[0].get("limits"), [0.0, 95.0]) and carried[1] is None, {
                      "reference_export_extras": carried[0], "default_export_extras": carried[1]})
    return None


def boxes_by_name(gltfio, path) -> dict:
    asset = gltfio.load(path)
    names = [node.get("name") for node in asset.items("nodes")]
    return {names[index]: box for index, box in gltfio.node_world_bounds(asset).items()}


def engine_boxes(engine: str, found: dict) -> dict:
    if engine == "godot":
        names = {str(row["index"]): row["name"] for row in found.get("nodes", [])}
        return {names[index]: box for index, box in found.get("world_bounds", {}).items()}
    return {row["name"]: row["world_bounds"] for row in found.get("objects", []) if row.get("world_bounds")}


def verify_axes_units_converter(session: Session):
    session.run_fixtures()
    gltfio = session.module("gltfio")
    repairs = {"door_z_up.gltf": ["--from", "z_up_right"], "door_centimetres.gltf": ["--unit-m", "0.01"],
               "door_mirrored.gltf": ["--from", "y_up_left_cw"]}
    outputs, problems = [], []
    for name, options in repairs.items():
        target = session.workspace / f"repaired_{name}"
        report, status, _ = session.checker(["convert", f"fixtures/{name}", str(target), *options,
                                             "--expect-dimensions", "1.1", "2.1", "0.15"])
        if status != 0:
            problems.append({"fixture": name, "codes": report and [f["code"] for f in report["failures"]]})
        outputs.append(target)
    reference = boxes_by_name(gltfio, session.path("fixtures/door.gltf"))
    for engine, inspect in (("godot", session.godot_inspect), ("blender", session.blender_inspect)):
        facts, outcome = inspect([session.path("fixtures/door.gltf"), *outputs], label=f"repairs_{engine}")
        if facts is None:
            problems.append({engine: outcome_summary(outcome)})
            continue
        for path, found in zip(["fixtures/door.gltf", *[item.name for item in outputs]], facts):
            boxes = engine_boxes(engine, found)
            for part, box in reference.items():
                if part not in boxes or not box_close(boxes[part], box):
                    problems.append({"file": path, engine: boxes.get(part), "part": part, "door_box": box})
    session.check("repaired_fixtures_match_the_door_in_both_engines", not problems, {
        "repairs": {name: options for name, options in repairs.items()},
        "compared": "each repaired file passes check and, loaded in Godot and in Blender, gives every part the "
                    "world box the correct door has", "problems": problems[:8]})
    work = session.workspace / "blender_exports"
    outcome = session.blender(SUPPORT / "axes_exports.py", [work])
    expect = ["--expect-dimensions", "0.9", "2.0", "0.04"]
    codes = {}
    for name in ("yup", "zup", "cm"):
        report, _status, _ = session.checker(["check", str(work / name / "door.gltf"), *expect])
        codes[name] = sorted({failure["code"] for failure in report["failures"]}) if report else None
    repaired = {}
    for name, options in (("zup", ["--from", "z_up_right"]), ("cm", ["--unit-m", "0.01"])):
        target = work / f"{name}_repaired.gltf"
        report, status, _ = session.checker(["convert", str(work / name / "door.gltf"), str(target), *options, *expect])
        repaired[name] = status
    expected_codes = {"yup": [], "zup": ["up_axis_mismatch"], "cm": ["unit_scale_mismatch"]}
    session.check("blender_export_mistakes_are_diagnosed_and_repaired",
                  codes == expected_codes and repaired == {"zup": 0, "cm": 0} and not outcome["errors"], {
                      "exports": "Blender 5.2.1 door exported with defaults (yup), with export_yup off (zup), and from "
                                 "a centimetre scene (cm)", "check_codes": codes, "expected": expected_codes,
                      "convert_status": repaired, "blender_errors": outcome["errors"][:4]})
    files = [work / "yup" / "door.gltf", work / "zup_repaired.gltf", work / "cm_repaired.gltf"]
    problems = []
    for engine, inspect in (("godot", session.godot_inspect), ("blender", session.blender_inspect)):
        facts, outcome = inspect(files, label=f"round_trip_{engine}")
        boxes = [engine_boxes(engine, found).get("Door") for found in facts or []]
        if len(boxes) != 3 or boxes[0] is None or not all(box is not None and box_close(box, boxes[0]) for box in boxes):
            problems.append({engine: boxes})
    session.check("round_trip_matches_in_godot_and_blender", not problems, {
        "files": ["yup/door.gltf", "zup_repaired.gltf", "cm_repaired.gltf"],
        "compared": "the Door's world box in Godot and in a Blender re-import equals the correct export's",
        "problems": problems})
    return None


def scene_signature(facts: dict) -> tuple:
    return (sorted((row["path"], row["class"], row.get("material")) for row in facts.get("nodes", [])),
            sorted((row["from"], row["signal"], row["to"], row["method"]) for row in facts.get("connections", [])))


def verify_godot_scene_linter(session: Session):
    rows = session.run_fixtures()
    project = session.workspace / "scene_project"
    shutil.copytree(session.path("fixtures/project"), project)
    shutil.copyfile(SUPPORT / "inspect_scene.gd", project / "inspect_scene.gd")
    inspected = {}
    for key, row in rows.items():
        relative = row["argv"][0][len("fixtures/project/"):]
        output = session.workspace / f"scene_{Path(relative).stem}.json"
        outcome = session.godot("inspect_scene.gd", [output, f"res://{relative}"], timeout=60, project=project)
        facts = json.loads(output.read_text()) if output.is_file() else {"loaded": None}
        inspected[key] = (facts, [line for line in outcome["errors"] if "leaked" not in line and "Pages in use" not in
                                  line and "Leaked instance" not in line])
    problems = []
    for key, row in rows.items():
        if row["expect"] != "pass":
            continue
        facts, errors = inspected[key]
        report = row["report"]["facts"]
        if errors or not facts.get("loaded") or (report["kind"] == "gd_scene" and not facts.get("instantiated")):
            problems.append({"file": key, "loaded": facts.get("loaded"), "errors": errors[:3]})
            continue
        if report["kind"] == "gd_resource":
            continue
        godot_nodes = {node["path"]: node["class"] for node in facts["nodes"]}
        legacy = report["format"] == "2"
        for node in report["nodes"]:
            if node["path"] not in godot_nodes or (node["type"] and not legacy and godot_nodes[node["path"]] !=
                                                   node["type"]):
                problems.append({"file": key, "node": node, "godot": godot_nodes.get(node["path"])})
        connections = {(row["from"], row["signal"], row["to"], row["method"]) for row in facts["connections"]}
        for connection in report["connections"]:
            wanted = (connection["from"], connection["signal"], connection["to"], connection["method"])
            if wanted not in connections:
                problems.append({"file": key, "connection": wanted})
    session.check("godot_loads_known_good_files_as_parsed", not problems, {
        "files": [key for key, row in rows.items() if row["expect"] == "pass"],
        "compared": "no Godot errors; every node the linter parsed exists at its path with its declared class (format "
                    "2 classes are converted by Godot and not compared); every parsed connection is connected",
        "problems": problems[:10]})
    reference = scene_signature(inspected["fixtures/project/scenes/door.tscn"][0])
    reactions, quiet = {}, []
    for key, row in rows.items():
        if row["expect"] != "fail":
            continue
        facts, errors = inspected[key]
        difference = None
        if not facts.get("loaded"):
            state = "load_failed"
        elif "instantiated" in facts and not facts["instantiated"]:
            state = "instantiate_failed"
        elif errors:
            state = "loaded_with_errors"
        elif key.endswith(".tscn") and scene_signature(facts) != reference:
            state = "loaded_silently_changed"
            ours, theirs = scene_signature(facts), reference
            difference = {"nodes": sorted(set(map(tuple, ours[0])) ^ set(map(tuple, theirs[0])))[:4],
                          "connections": sorted(set(ours[1]) ^ set(theirs[1]))[:4]}
        else:
            state = "loaded_unchanged"
            quiet.append(key)
        reactions[key] = {"linter_codes": row["codes"], "godot": state, "godot_errors": errors[:2]}
        if difference is not None:
            reactions[key]["difference"] = difference
    session.check("each_known_wrong_file_has_a_visible_effect_in_godot", not quiet and all(
        rows[key]["status"] == 1 for key in reactions), {"reactions": reactions, "unchanged_in_godot": quiet})
    return None


VERIFIERS = {"gltf_structural_validator": verify_gltf_structural_validator,
             "gltf_semantic_recovery": verify_gltf_semantic_recovery,
             "animation_export_trap_checker": verify_animation_export_trap_checker,
             "asset_specification_schema": verify_asset_specification_schema,
             "articulation_manifest_godot_builder": verify_articulation_manifest_godot_builder,
             "articulation_loss_checker": verify_articulation_loss_checker,
             "axes_units_converter": verify_axes_units_converter,
             "godot_scene_linter": verify_godot_scene_linter}


def verify(context) -> dict:
    session = Session(context)
    function = VERIFIERS.get(session.identity)
    if function is None:
        session.check("native_verifier_defined", False, {"identity": session.identity})
        return session.result()
    preview = function(session)
    return session.result(preview)
