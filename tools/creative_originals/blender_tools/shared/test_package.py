"""Checks one Blender tool package against its contract card, without Blender.

The card (component.json) names the tool module, its entry points, its parameters and the known answers of its
pure core at the default parameters. These tests import the module with the standard library only, run the core,
check every description it returns with meshcheck and graphcheck, and refuse known-wrong inputs: a parameter
outside its declared range, an unknown parameter, a face with an out-of-range index, a broken node link and
keyframes out of order.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import json
import math
import sys
import unittest
from pathlib import Path

import graphcheck
import meshcheck

ROOT = Path(__file__).resolve().parent
CARD = json.loads((ROOT / "component.json").read_text(encoding="utf-8"))
CONTRACT = CARD["contract"]
OUTPUTS = CONTRACT["outputs"]
MODULE = importlib.import_module(CONTRACT["module"])
DEFAULTS = {row["name"]: row["default"] for row in CONTRACT["parameters"]}
TETRAHEDRON = ([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)],
               [[0, 2, 1], [0, 1, 3], [1, 2, 3], [0, 3, 2]])


def core(**overrides):
    values = copy.deepcopy(DEFAULTS)
    values.update(overrides)
    return getattr(MODULE, CONTRACT["entry_points"]["core"])(**values)


def meshes(result):
    """(name, mesh) pairs of every mesh description in a core result."""
    found = []
    if "vertices" in result:
        found.append((OUTPUTS.get("object", "mesh"), result))
    for part in result.get("parts", []):
        found.append((part["name"], part))
    return found


def as_text(spec, value):
    if spec["type"] == "bool":
        return "true" if value else "false"
    if spec["type"] == "vector":
        return ",".join(repr(float(item)) for item in value)
    if spec["type"] == "float":
        return repr(float(value))
    return str(value)


def close(expected, found, tolerance=1e-6):
    if isinstance(expected, bool) or isinstance(expected, str) or expected is None:
        return expected == found
    if isinstance(expected, (int, float)):
        return isinstance(found, (int, float)) and abs(expected - found) <= tolerance * max(1.0, abs(expected))
    if isinstance(expected, (list, tuple)):
        return (isinstance(found, (list, tuple)) and len(expected) == len(found)
                and all(close(a, b, tolerance) for a, b in zip(expected, found)))
    if isinstance(expected, dict):
        return isinstance(found, dict) and all(key in found and close(value, found[key], tolerance)
                                               for key, value in expected.items())
    return False


def measured(result):
    """The quantities the card's at_defaults block may pin, measured on a core result."""
    values = {}
    found = meshes(result)
    if found:
        values["vertices"] = sum(len(mesh["vertices"]) for _name, mesh in found)
        values["faces"] = sum(len(mesh["faces"]) for _name, mesh in found)
        values["triangles"] = sum(meshcheck.triangle_count(mesh["faces"]) for _name, mesh in found)
        if OUTPUTS.get("closed"):
            values["volume"] = sum(meshcheck.signed_volume(mesh["vertices"], mesh["faces"]) for _name, mesh in found)
    if "vertices" in result and result["vertices"]:
        values["bounds"] = meshcheck.bounds(result["vertices"])
        values["euler"] = meshcheck.euler_characteristic(result["vertices"], result["faces"])
    if "parts" in result:
        values["parts"] = len(result["parts"])
    if "trees" in result:
        values["nodes"] = sum(len(tree["nodes"]) for tree in result["trees"])
        values["links"] = sum(len(tree["links"]) for tree in result["trees"])
    if "channels" in result:
        values["channels"] = len(result["channels"])
        values["keys"] = sum(len(channel["keys"]) for channel in result["channels"])
    for key in ("objects", "drivers", "bones", "curves"):
        if key in result:
            values[key] = len(result[key])
    if "settings" in result:
        values["settings"] = len(result["settings"])
    if "report" in result:
        values["report"] = result["report"]
    return values


class ContractTests(unittest.TestCase):
    def test_files_match_card(self):
        for row in CARD["files"]:
            data = (ROOT / row["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"], row["path"])

    def test_module_imports_without_blender(self):
        self.assertNotIn("bpy", sys.modules)
        tree = ast.parse((ROOT / f"{CONTRACT['module']}.py").read_text(encoding="utf-8"))
        top = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
        names = {alias.name.split(".")[0] for node in top for alias in node.names} | {
            (node.module or "").split(".")[0] for node in top if isinstance(node, ast.ImportFrom)}
        self.assertFalse(names & {"bpy", "bmesh", "mathutils", "addon_utils", "bpy_extras"}, names)
        self.assertTrue(ast.get_docstring(tree), "the module explains itself")

    def test_addon_surface(self):
        info = MODULE.bl_info
        for key in ("name", "author", "version", "blender", "description", "category", "location"):
            self.assertIn(key, info)
        self.assertGreaterEqual(tuple(info["blender"]), (4, 2, 0))
        self.assertEqual(MODULE.OPERATOR, CONTRACT["entry_points"]["operator"])
        self.assertEqual(CONTRACT["entry_points"]["operator"], "baltor." + CONTRACT["module"])
        for name in ("register", "unregister", "main", "parse_arguments", "parameters", "expectations",
                     *CONTRACT["entry_points"].values()):
            if "." not in name:
                self.assertTrue(callable(getattr(MODULE, name, None)), name)

    def test_parameters_match_card(self):
        declared = json.loads(json.dumps(MODULE.PARAMETERS))
        self.assertEqual(declared, CONTRACT["parameters"])
        self.assertEqual(graphcheck.parameter_problems(CONTRACT["parameters"]), [])
        self.assertEqual(json.loads(json.dumps(MODULE.parameters())), DEFAULTS)

    def test_core_at_defaults(self):
        result = core()
        self.assertEqual(graphcheck.json_problems(result), [])
        self.assertEqual(json.dumps(result, sort_keys=True), json.dumps(core(), sort_keys=True), "deterministic")
        names = [name for name, _mesh in meshes(result)]
        self.assertEqual(len(names), len(set(names)), "mesh names are distinct")
        closed = OUTPUTS.get("closed")
        for name, mesh in meshes(result):
            self.assertEqual(meshcheck.problems(mesh["vertices"], mesh["faces"]), [], name)
            self.assertGreater(len(mesh["faces"]), 0, name)
            if "uv" in mesh:
                self.assertEqual(meshcheck.uv_problems(mesh["faces"], mesh["uv"]), [], name)
            for group, indices in mesh.get("groups", {}).items():
                self.assertTrue(all(0 <= index < len(mesh["vertices"]) for index in indices), group)
            if closed is True or (isinstance(closed, list) and name in closed):
                self.assertEqual(meshcheck.closed_problems(mesh["faces"]), [], name)
                self.assertGreater(meshcheck.signed_volume(mesh["vertices"], mesh["faces"]), 0.0, name)
        for tree in result.get("trees", []):
            self.assertEqual(graphcheck.tree_problems(tree), [], tree.get("name"))
        self.assertEqual(graphcheck.channel_problems(result.get("channels", [])), [])
        self.assertEqual(graphcheck.object_problems(result.get("objects", [])), [])
        self.assertEqual(graphcheck.driver_problems(result.get("drivers", [])), [])
        self.assertEqual(graphcheck.bone_problems(result.get("bones", [])), [])
        self.assertTrue(set(result) <= {"vertices", "faces", "uv", "groups", "smooth", "materials", "face_materials",
                                        "sharp_edges", "parts", "trees", "channels", "objects", "drivers", "bones",
                                        "curves", "settings", "report", "points", "images", "texts"}, sorted(result))

    def test_known_answers_at_defaults(self):
        expected = OUTPUTS.get("at_defaults", {})
        self.assertTrue(expected, "the card pins known answers")
        values = measured(core())
        for key, value in expected.items():
            self.assertIn(key, values)
            self.assertTrue(close(value, values[key]), f"{key}: card {value}, core {values[key]}")

    def test_expectations_follow_core(self):
        expectations = MODULE.expectations()
        self.assertEqual(graphcheck.expectation_problems(expectations), [])
        objects = expectations.get("objects", {})
        for name, mesh in meshes(core()):
            spec = objects.get(name)
            if spec is not None and "vertices" in spec:
                self.assertEqual(spec["vertices"], len(mesh["vertices"]), name)
                self.assertEqual(spec["faces"], len(mesh["faces"]), name)

    def test_script_arguments_round_trip(self):
        argv = []
        for spec in CONTRACT["parameters"]:
            argv += ["--" + spec["name"], as_text(spec, spec["default"])]
        values, output = MODULE.parse_arguments(argv + ["--output", "result.blend"])
        self.assertEqual(json.loads(json.dumps(values)), DEFAULTS)
        self.assertEqual(output, "result.blend")
        with self.assertRaises(ValueError):
            MODULE.parse_arguments(["--no_such_parameter", "1"])

    def test_known_wrong_parameters_are_refused(self):
        with self.assertRaises(ValueError):
            core(no_such_parameter=1)
        for spec in CONTRACT["parameters"]:
            kind, name = spec["type"], spec["name"]
            wrong = []
            if kind in ("int", "float"):
                step = 1 if kind == "int" else max(1e-3, (spec["maximum"] - spec["minimum"]) * 0.01)
                wrong = [spec["minimum"] - step, spec["maximum"] + step, "1"]
            elif kind == "vector":
                wrong = [[spec["maximum"] + 1.0] * 3, [spec["default"][0]] * 2]
            elif kind == "choice":
                wrong = ["not_a_choice"]
            elif kind == "bool":
                wrong = ["yes"]
            elif kind == "string":
                wrong = [7]
            for value in wrong:
                with self.subTest(parameter=name, value=value), self.assertRaises(ValueError):
                    core(**{name: value})

    def test_known_wrong_mesh_is_detected(self):
        found = [mesh for _name, mesh in meshes(core()) if len(mesh["faces"]) > 1]
        vertices, faces = (found[0]["vertices"], found[0]["faces"]) if found else TETRAHEDRON
        self.assertEqual(meshcheck.problems(vertices, faces), [])
        broken = list(faces) + [[0, 1, len(vertices)]]
        self.assertIn("index_out_of_range", {code for code, _ in meshcheck.problems(vertices, broken)})
        flipped = [list(reversed(faces[0]))] + list(faces[1:])
        if meshcheck.is_closed_manifold(faces):
            self.assertIn("orientation_flipped", {code for code, _ in meshcheck.closed_problems(flipped)})
        self.assertIn("open_edge", {code for code, _ in meshcheck.closed_problems(list(faces)[1:])})

    def test_known_wrong_graph_is_detected(self):
        trees = core().get("trees") or [{"name": "probe", "kind": "material", "nodes": [
            {"name": "Emission", "type": "ShaderNodeEmission"}, {"name": "Output", "type": "ShaderNodeOutputMaterial"}],
            "links": [{"from": ["Emission", "Emission"], "to": ["Output", "Surface"]}]}]
        tree = copy.deepcopy(trees[0])
        self.assertEqual(graphcheck.tree_problems(tree), [])
        broken = copy.deepcopy(tree)
        broken["links"].append({"from": ["No Such Node", "Value"], "to": [tree["nodes"][0]["name"], "Value"]})
        self.assertIn("link_node_missing", {code for code, _ in graphcheck.tree_problems(broken)})
        unlinked = copy.deepcopy(tree)
        outputs = {node["name"] for node in tree["nodes"] if node["type"] in graphcheck.OUTPUT_NODES[tree["kind"]]}
        unlinked["links"] = [link for link in tree["links"] if link["to"][0] not in outputs]
        self.assertIn("output_unlinked", {code for code, _ in graphcheck.tree_problems(unlinked)})

    def test_known_wrong_keys_are_detected(self):
        channels = core().get("channels") or [{"target": "probe", "data_path": "location", "index": 0,
                                               "keys": [[1, 0.0], [10, 1.0]]}]
        broken = copy.deepcopy(channels[0])
        broken["keys"] = list(reversed(broken["keys"])) if len(broken["keys"]) > 1 else broken["keys"] * 2
        self.assertEqual(graphcheck.channel_problems([channels[0]]), [])
        self.assertIn("frames_not_increasing", {code for code, _ in graphcheck.channel_problems([broken])})


if __name__ == "__main__":
    unittest.main()
