"""Package tests for one geometry_4d item, driven by component.json.

The card's contract declares the item's known answers (counts, radii, volumes), its CLI parameters and the
example files the CLI regenerates. These tests check the shared fourd toolkit against exact answers, the item's
declared invariants and known-wrong controls, the polytope and rotation hooks when the item has them, every
packaged glTF with the structural checker, and that the CLI rebuilds each example byte for byte.
Known-wrong controls: a polytope with one vertex moved fails regularity, a glTF with an out-of-range index or a
wrong buffer length is refused, a scaled matrix is not a rotation.
"""
import base64
import contextlib
import copy
import hashlib
import importlib
import io
import itertools
import json
import math
import os
import struct
import tempfile
import unittest
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import fourd

ROOT = Path(__file__).resolve().parent
CARD = json.loads((ROOT / "component.json").read_text(encoding="utf-8"))
CONTRACT = CARD["contract"]
IDENTITY = CARD["job"]["identity"]


def _module():
    return importlib.import_module(IDENTITY)


def _close(actual, expected, tolerance=1e-6):
    if isinstance(expected, bool) or isinstance(actual, bool):
        return actual is expected
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if isinstance(expected, int) and isinstance(actual, int):
            return actual == expected
        return math.isfinite(actual) and abs(actual - expected) <= tolerance * max(1.0, abs(expected))
    if isinstance(expected, (list, tuple)) and isinstance(actual, (list, tuple)):
        return len(actual) == len(expected) and all(_close(a, b, tolerance) for a, b in zip(actual, expected))
    if isinstance(expected, dict) and isinstance(actual, dict):
        return set(actual) >= set(expected) and all(_close(actual[key], expected[key], tolerance) for key in expected)
    return actual == expected


def _tesseract():
    vertices = [tuple(point) for point in itertools.product((-1.0, 1.0), repeat=4)]
    normals = [tuple(sign if axis == index else 0.0 for axis in range(4)) for index in range(4) for sign in (-1.0, 1.0)]
    return fourd.polytope_from_facets(vertices, normals)


def _with_index(document, value):
    """A copy of the document whose first index is replaced (to build an out-of-range control)."""
    broken = copy.deepcopy(document)
    for mesh in broken["meshes"]:
        for primitive in mesh["primitives"]:
            if "indices" in primitive:
                data = bytearray(fourd.buffer_bytes(broken)[0])
                accessor = broken["accessors"][primitive["indices"]]
                view = broken["bufferViews"][accessor["bufferView"]]
                code = "<H" if accessor["componentType"] == 5123 else ("<B" if accessor["componentType"] == 5121 else "<I")
                struct.pack_into(code, data, view.get("byteOffset", 0) + accessor.get("byteOffset", 0), value)
                broken["buffers"][0]["uri"] = fourd.DATA_PREFIX + base64.b64encode(bytes(data)).decode("ascii")
                return broken
    return None


class ToolkitTests(unittest.TestCase):
    """Exact answers for the shared fourd toolkit."""

    def test_vectors_and_matrices(self):
        self.assertEqual(fourd.dot((1, 2, 3, 4), (5, 6, 7, 8)), 70)
        self.assertEqual(fourd.norm((1, 2, 2, 4)), 5.0)
        self.assertEqual(fourd.cross4((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0)), (0.0, 0.0, 0.0, 1.0))
        self.assertAlmostEqual(fourd.determinant([[2, 0, 0, 0], [0, 3, 0, 0], [0, 0, 4, 1], [0, 0, 1, 1]]), 18.0)
        self.assertEqual(fourd.solve([[2, 0], [0, 4]], [2, 2]), (1.0, 0.5))
        self.assertEqual(fourd.rank([(1, 0, 0, 0), (2, 0, 0, 0), (0, 1, 0, 0)]), 2)
        self.assertEqual(len(fourd.null_space([(1, 0, 0, 0), (0, 1, 0, 0)])), 2)
        self.assertEqual(fourd.affine_dimension([(0, 0, 0, 0), (1, 0, 0, 0), (2, 0, 0, 0)]), 1)
        self.assertEqual(fourd.centroid([(0, 0), (2, 4)]), (1.0, 2.0))
        self.assertEqual(fourd.transpose(fourd.matmul(fourd.identity(2), ((1, 2), (3, 4)))), ((1, 3), (2, 4)))

    def test_rotations(self):
        turn = fourd.plane_rotation("xy", math.pi / 2)
        image = fourd.matvec(turn, (1, 0, 0, 0))
        self.assertTrue(all(abs(a - b) < 1e-12 for a, b in zip(image, (0, 1, 0, 0))))
        for plane in fourd.PLANES:
            self.assertTrue(fourd.is_rotation(fourd.plane_rotation(plane, 0.7)))
        matrix = fourd.rotation_matrix("xw=0.6,yz=0.3,zw=30deg")
        self.assertTrue(fourd.is_rotation(matrix))
        self.assertAlmostEqual(fourd.norm(fourd.matvec(matrix, (1, 2, 3, 4))), math.sqrt(30))
        self.assertFalse(fourd.is_rotation(tuple(fourd.scale(row, 1.01) for row in matrix)), "a scaled matrix")
        self.assertFalse(fourd.is_rotation(((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, -1))), "a reflection")
        for bad in ("xq=1", "xw=nan", "xw"):
            with self.assertRaises(ValueError):
                fourd.parse_rotation(bad)
        left = (math.cos(0.4), math.sin(0.4), 0.0, 0.0)
        isoclinic = fourd.quaternion_pair_matrix(left, (1.0, 0.0, 0.0, 0.0))
        self.assertTrue(fourd.is_rotation(isoclinic))
        for point in ((1, 0, 0, 0), (0, 0, 1, 0), (1, 2, 3, 4)):
            self.assertAlmostEqual(fourd.angle_between(point, fourd.matvec(isoclinic, point)), 0.4)
        quaternion = fourd.quat_from_axis_angle((0, 0, 1), math.pi / 2)
        turned = fourd.quat_mul(fourd.quat_mul(quaternion, fourd.point_to_quaternion((1, 0, 0, 0))),
                                fourd.quat_conjugate(quaternion))
        self.assertTrue(all(abs(a - b) < 1e-12 for a, b in zip(fourd.quaternion_to_point(turned), (0, 1, 0, 0))))
        self.assertAlmostEqual(fourd.norm(fourd.quat_normalize((3, 0, 4, 0))), 1.0)
        self.assertTrue(fourd.is_rotation(fourd.orthonormalize([[1.001, 0.002, 0, 0], [0, 1, 0, 0.003],
                                                                [0, 0, 1, 0], [0, 0, 0, 0.998]])))

    def test_projections(self):
        self.assertEqual(fourd.perspective((1, 0, 0, 1), 3.0), (1.5, 0.0, 0.0))
        self.assertEqual(fourd.stereographic((1.0, 0.0, 0.0, 0.0)), (1.0, 0.0, 0.0))
        self.assertEqual(fourd.stereographic((0.0, 0.0, 0.0, -1.0)), (0.0, 0.0, 0.0))
        self.assertEqual(fourd.orthographic((1, 2, 3, 4)), (1, 2, 3))
        with self.assertRaises(ValueError):
            fourd.perspective((0, 0, 0, 3.5), 3.0)
        projected = fourd.project_points([(1, 0, 0, 0), (0, 1, 0, 0)], "stereographic")
        self.assertEqual(len(projected), 2)

    def test_polytopes_and_slices(self):
        tesseract = _tesseract()
        self.assertEqual(fourd.f_vector(tesseract), (16, 32, 24, 8))
        self.assertEqual(fourd.euler_characteristic(tesseract), 0)
        self.assertEqual(fourd.polytope_problems(tesseract), [])
        self.assertTrue(fourd.regularity_report(tesseract)["regular"])
        self.assertEqual(len(fourd.cell_vertex_sets(tesseract)), 8)
        self.assertEqual(fourd.schlafli_symbol(tesseract), (4, 3, 3))
        self.assertAlmostEqual(fourd.hypervolume(tesseract), 16.0)
        self.assertAlmostEqual(fourd.cell_volume(tesseract, 0), 8.0)
        moved = dict(tesseract, vertices=[fourd.scale(tesseract["vertices"][0], 1.05)] + tesseract["vertices"][1:])
        self.assertFalse(fourd.regularity_report(moved)["regular"], "a moved vertex must fail regularity")
        self.assertEqual(fourd.edges_by_length(tesseract["vertices"]), sorted(tesseract["edges"]))
        cube = fourd.slice_polytope(tesseract, (0, 0, 0, 1), 0.0)
        self.assertEqual((len(cube["points3"]), len(cube["faces"]), len(cube["edges"])), (8, 6, 12))
        self.assertAlmostEqual(cube["volume"], 8.0)
        octahedron = fourd.slice_polytope(tesseract, (1, 1, 1, 1), 0.0)
        self.assertEqual((len(octahedron["points3"]), len(octahedron["faces"])), (6, 8))
        self.assertAlmostEqual(octahedron["volume"], 32.0 / 3.0)
        self.assertEqual(fourd.hyperplane_basis((0, 0, 0, 1))[0], (1.0, 0.0, 0.0, 0.0))
        record = fourd.polytope_record(tesseract, "tesseract")
        self.assertEqual(fourd.f_vector(fourd.polytope_from_record(json.loads(json.dumps(record)))), (16, 32, 24, 8))
        record["faces"][0] = [0, 1, 999]
        with self.assertRaises(ValueError):
            fourd.polytope_from_record(record)
        self.assertAlmostEqual(fourd.polyhedron_volume(cube["points3"], cube["faces"]), 8.0)
        self.assertGreater(fourd.dot(fourd.polygon_normal([(0, 0, 0), (1, 0, 0), (0, 1, 0)]), (0, 0, 1)), 0)

    def test_coxeter_groups(self):
        expected = {"A4": 5, "B4": 16, "F4": 24, "H4": 600}
        for group, count in expected.items():
            roots = fourd.simple_roots(group)
            gram = fourd.coxeter_gram(group)
            for i in range(4):
                for j in range(4):
                    self.assertAlmostEqual(fourd.dot(roots[i], roots[j]), gram[i][j])
            self.assertEqual(len(fourd.orbit(fourd.wythoff_point(roots, {0}), roots)), count)
            weights = fourd.fundamental_weights(roots)
            self.assertAlmostEqual(fourd.dot(fourd.normalize(roots[1]), weights[1]), 1.0)
        self.assertEqual(fourd.reflect((1, 2, 3, 4), (0, 0, 0, 1)), (1, 2, 3, -4))
        self.assertEqual(fourd.point_key((0.123456789, -0.0)), (0.12345679, 0.0))
        self.assertEqual(fourd.GROUP_ORDERS["H4"], 14400)

    def test_meshes(self):
        tubes = fourd.tube_mesh([(0, 0, 0), (0, 0, 1)], [(0, 1)], 0.1, sides=6)
        self.assertEqual(len(tubes["positions"]), 12)
        self.assertTrue(all(abs(fourd.norm(normal) - 1.0) < 1e-12 for normal in tubes["normals"]))
        sphere = fourd.sphere_mesh((1, 2, 3), 0.5)
        self.assertEqual((len(sphere["positions"]), len(sphere["indices"]) // 3), (12, 20))
        self.assertEqual(fourd.mesh_euler_characteristic(sphere), 2)
        wire = fourd.wireframe_mesh([(0, 0, 0), (1, 0, 0)], [(0, 1)], 0.05, sides=4)
        self.assertEqual(len(wire["positions"]), 8 + 24)
        faces = fourd.polygon_mesh([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [[0, 1, 2, 3]], color=(1, 0, 0, 1))
        self.assertEqual(len(faces["indices"]), 6)
        self.assertEqual(fourd.mesh_bounds(faces), ((0, 0, 0), (1, 1, 0)))
        self.assertEqual(fourd.line_mesh([(0, 0, 0), (1, 1, 1)], [(0, 1)])["mode"], 1)
        self.assertEqual(fourd.point_mesh([(0, 0, 0)])["mode"], 0)
        self.assertEqual(len(fourd.merge_meshes([faces, faces])["positions"]), 8)
        self.assertEqual(fourd.depth_color(0.0)[3], 1.0)
        self.assertEqual(len(fourd.depth_colors([0.0, 1.0, 2.0])), 3)
        colours = fourd.palette(5)
        self.assertEqual(len(set(colours)), 5)
        self.assertTrue(all(0.0 <= value <= 1.0 for colour in colours for value in colour))
        tesseract = _tesseract()
        tubes = fourd.projected_wireframe(tesseract["vertices"], tesseract["edges"], fourd.plane_rotation("xw", 0.5),
                                          eye_distance=4.0, sides=4)
        self.assertEqual(len(tubes["colors"]), len(tubes["positions"]))
        lines = fourd.projected_wireframe(tesseract["vertices"], tesseract["edges"], style="lines", eye_distance=4.0)
        self.assertEqual((lines["mode"], len(lines["indices"])), (1, 64))
        exploded = fourd.cell_mesh(fourd.project_points(tesseract["vertices"], "perspective", eye_distance=4.0),
                                   tesseract, 0.7, colors=fourd.palette(8))
        self.assertEqual((len(exploded["positions"]), len(exploded["indices"])), (8 * 6 * 4, 8 * 6 * 6))
        self.assertTrue(all(fourd.dot(normal, normal) > 0.99 for normal in exploded["normals"]))
        self.assertEqual(fourd.facing_cells(tesseract, tesseract["vertices"], "perspective", 4.0), [7])
        self.assertEqual(fourd.facing_cells(tesseract, tesseract["vertices"], "orthographic"), [7])
        turned = fourd.rotate_points(fourd.plane_rotation("xw", 0.6), tesseract["vertices"])
        self.assertEqual(len(fourd.facing_cells(tesseract, turned, "perspective", 4.0)), 2)
        self.assertEqual(fourd.cell_normals(tesseract)[7], (0.0, 0.0, 0.0, 1.0))
        circle = [(math.cos(2 * math.pi * k / 24), math.sin(2 * math.pi * k / 24), 0.3 * math.sin(6 * math.pi * k / 24))
                  for k in range(24)]
        ring = fourd.curve_tube(circle, 0.1, 5, closed=True, colors=[(1, 0, 0, 1)] * 24)
        self.assertEqual((len(ring["positions"]), len(ring["indices"]) // 3), (120, 240))
        self.assertEqual(fourd.mesh_euler_characteristic(ring), 0, "a closed tube is a torus")
        self.assertEqual(len(fourd.curve_tube(circle, 0.1, 5)["indices"]) // 3, 230)
        surface = fourd.marching_tetrahedra(lambda p: fourd.norm(p) - 0.8, (-1, -1, -1), (1, 1, 1), (6, 6, 6))
        self.assertEqual(fourd.mesh_euler_characteristic(surface), 2, "a sphere isosurface is closed")
        self.assertTrue(all(abs(fourd.norm(point) - 0.8) < 0.06 for point in surface["positions"]))

    def test_gltf_writer_and_checker(self):
        tesseract = _tesseract()
        points = fourd.project_points(tesseract["vertices"], "perspective", eye_distance=4.0)
        mesh = fourd.wireframe_mesh(points, tesseract["edges"], 0.04, sides=5,
                                    colors=fourd.depth_colors([v[3] for v in tesseract["vertices"]]))
        triangle = {"positions": [(0, 0, 0), (1, 0, 0), (0, 1, 0)], "normals": [(0, 0, 1)] * 3, "indices": [0, 1, 2],
                    "mode": 4, "name": "morph", "targets": [{"positions": [(0, 0, 0), (1, 0, 0), (0, 0, 0)]}]}
        document = fourd.gltf_document([dict(mesh, name="wire"), triangle], animations=[
            {"name": "grow", "channels": [{"node": 1, "path": "weights", "times": [0, 1], "values": [[0.0], [1.0]]}]}])
        self.assertEqual(fourd.validate_gltf(document), [])
        summary = fourd.gltf_summary(document)
        self.assertEqual((summary["meshes"], summary["morph_targets"], summary["animations"]), (2, 1, 1))
        self.assertEqual(len(fourd.accessor_values(document, 0)), len(mesh["positions"]))
        broken = _with_index(document, 65000)
        self.assertTrue(any("out of range" in problem for problem in fourd.validate_gltf(broken)))
        longer = copy.deepcopy(document)
        longer["buffers"][0]["byteLength"] += 4
        self.assertTrue(fourd.validate_gltf(longer), "a wrong buffer length is refused")
        late = copy.deepcopy(document)
        late["animations"][0]["samplers"][0]["output"] = late["animations"][0]["samplers"][0]["input"]
        late["meshes"][1]["primitives"][0]["targets"].append(dict(late["meshes"][1]["primitives"][0]["targets"][0]))
        self.assertTrue(fourd.validate_gltf(late), "a target and weight count mismatch is refused")
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "check.gltf")
            size = fourd.write_gltf(path, document)
            self.assertEqual(size, os.path.getsize(path))
            self.assertEqual(fourd.validate_gltf(fourd.read_gltf(path)), [])
            with self.assertRaises(ValueError):
                fourd.write_gltf(path, broken)
        self.assertTrue(fourd.gltf_text(document).endswith("\n"))
        line = {"positions": [(0, 0, 0), (1, 0, 0)], "indices": [0, 1], "mode": 1, "name": "turning"}
        frames = [[(0, 0, 0), (math.cos(a), math.sin(a), 0)] for a in (0.0, 0.5, 1.0)]
        animated, animation = fourd.morph_animation(line, frames, [0.0, 0.5, 1.0], "turn")
        moving = fourd.gltf_document([animated], animations=[animation])
        self.assertEqual(fourd.validate_gltf(moving), [])
        self.assertEqual(fourd.gltf_summary(moving)["morph_targets"], 2)
        with self.assertRaises(ValueError):
            fourd.morph_animation(line, frames, [0.0, 1.0, 0.5])
        png = fourd.png_bytes(2, 1, bytes([255, 0, 0, 0, 0, 255]))
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", png[16:24]), (2, 1))


class ItemTests(unittest.TestCase):
    """The item against its own contract card."""

    @classmethod
    def setUpClass(cls):
        cls.module = _module()

    def test_card_files(self):
        for row in CARD["files"]:
            data = (ROOT / row["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"], row["path"])
        self.assertTrue((ROOT / "README.md").read_text(encoding="utf-8").startswith("# " + CARD["title"] + "\n"))
        self.assertEqual(CARD["dimension"], "4d")
        for name in CONTRACT["entry_points"]:
            self.assertTrue(callable(getattr(self.module, name, None)), f"entry point {name}")

    def test_declared_invariants(self):
        actual = self.module.invariants()
        declared = CONTRACT["invariants"]
        self.assertTrue(declared, "the contract declares known answers")
        for key, expected in declared.items():
            self.assertIn(key, actual)
            self.assertTrue(_close(actual[key], expected), f"{key}: computed {actual[key]!r}, declared {expected!r}")

    def test_known_wrong_controls(self):
        results = self.module.controls()
        self.assertTrue(results, "at least one known-wrong control")
        for name, refused in results.items():
            self.assertIs(refused, True, f"control {name} was not refused")

    def test_polytope_hook(self):
        if not hasattr(self.module, "polytope"):
            self.skipTest("no polytope hook")
        polytope = self.module.polytope()
        self.assertEqual(fourd.polytope_problems(polytope), [])
        self.assertEqual(fourd.euler_characteristic(polytope), 0)
        counts = dict(zip(("vertices", "edges", "faces", "cells"), fourd.f_vector(polytope)))
        for key, value in counts.items():
            if key in CONTRACT["invariants"]:
                self.assertEqual(value, CONTRACT["invariants"][key], key)
        report = fourd.regularity_report(polytope)
        if CONTRACT["invariants"].get("regular") is True:
            self.assertTrue(report["regular"])
            moved = dict(polytope, vertices=[fourd.add(polytope["vertices"][0], (0.01, 0.0, 0.0, 0.0))]
                         + list(polytope["vertices"][1:]))
            self.assertFalse(fourd.regularity_report(moved)["regular"], "one moved vertex fails regularity")
        if "circumradius" in CONTRACT["invariants"]:
            self.assertAlmostEqual(report["circumradius"], CONTRACT["invariants"]["circumradius"], places=6)
        if "edge_length" in CONTRACT["invariants"]:
            self.assertAlmostEqual(report["edge_length"], CONTRACT["invariants"]["edge_length"], places=6)
        dropped = dict(polytope, edges=list(polytope["edges"])[1:])
        self.assertTrue(fourd.polytope_problems(dropped), "a dropped edge is a structural problem")

    def test_rotation_hook(self):
        if not hasattr(self.module, "rotations"):
            self.skipTest("no rotations hook")
        matrices = self.module.rotations()
        self.assertTrue(matrices)
        probe = (0.3, -1.2, 0.7, 2.0)
        for matrix in matrices:
            self.assertTrue(fourd.is_rotation(matrix, 1e-9))
            self.assertAlmostEqual(fourd.determinant(matrix), 1.0)
            self.assertAlmostEqual(fourd.norm(fourd.matvec(matrix, probe)), fourd.norm(probe))
        self.assertFalse(fourd.is_rotation(tuple(fourd.scale(row, 1.02) for row in matrices[0])))

    def _check_output(self, path, declared):
        suffix = Path(path).suffix
        data = Path(path).read_bytes()
        if suffix == ".gltf":
            document = json.loads(data.decode("utf-8"))
            self.assertEqual(fourd.validate_gltf(document), [], path)
            summary = fourd.gltf_summary(document)
            for key in ("meshes", "vertices", "triangles", "lines", "points", "morph_targets", "animations"):
                if key in declared:
                    self.assertEqual(summary[key], declared[key], f"{path} {key}")
            broken = _with_index(document, 4000000000 if summary["vertices"] >= 65535 else 65534)
            if broken is not None:
                self.assertTrue(fourd.validate_gltf(broken), "an out-of-range index must be refused")
        elif suffix == ".json":
            record = json.loads(data.decode("utf-8"))
            if record.get("record_type") == fourd.POLYTOPE_RECORD:
                polytope = fourd.polytope_from_record(record)
                if "f_vector" in declared:
                    self.assertEqual(list(fourd.f_vector(polytope)), declared["f_vector"])
        elif suffix == ".svg":
            self.assertTrue(ElementTree.fromstring(data).tag.endswith("svg"))
        elif suffix == ".png":
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            if "width" in declared:
                self.assertEqual(struct.unpack(">II", data[16:24]), (declared["width"], declared["height"]))
        return data

    def test_packaged_outputs_rebuild_exactly(self):
        outputs = CONTRACT.get("outputs", [])
        for declared in outputs:
            packaged = ROOT / declared["path"]
            data = self._check_output(packaged, declared)
            if packaged.suffix == ".gltf":
                self.assertLessEqual(len(data), fourd.MAXIMUM_EXAMPLE_BYTES, "examples stay under 200 KiB")
            if "command" in declared:
                with tempfile.TemporaryDirectory() as folder:
                    target = os.path.join(folder, Path(declared["path"]).name)
                    with contextlib.redirect_stdout(io.StringIO()):
                        status = self.module.main(list(declared["command"]) + ["--out", target])
                    self.assertIn(status, (0, None))
                    self.assertEqual(Path(target).read_bytes(), data, f"{declared['path']} rebuilds byte for byte")

    def test_cli(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as caught:
            self.module.main(["--help"])
        self.assertEqual(caught.exception.code, 0)
        for parameter in CONTRACT.get("parameters", []):
            self.assertIn(parameter["flag"], output.getvalue(), f"declared parameter {parameter['flag']}")
        example = CONTRACT.get("cli_example")
        if example:
            with tempfile.TemporaryDirectory() as folder:
                arguments = list(example)
                position = arguments.index("--out")
                arguments[position + 1] = os.path.join(folder, Path(arguments[position + 1]).name)
                with contextlib.redirect_stdout(io.StringIO()):
                    status = self.module.main(arguments)
                self.assertIn(status, (0, None))
                self._check_output(arguments[position + 1], CONTRACT.get("cli_expect", {}))
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            self.module.main(["--no-such-flag"])
        self.assertNotEqual(caught.exception.code, 0, "an unknown flag is refused")

    def test_godot_files(self):
        scenes = [row["path"] for row in CARD["files"] if row["path"].endswith(".tscn")]
        if not scenes:
            self.skipTest("no Godot scene")
        for scene in scenes:
            text = (ROOT / scene).read_text(encoding="utf-8")
            self.assertTrue(text.startswith("[gd_scene"))
            for line in text.splitlines():
                if line.startswith("[ext_resource"):
                    path = line.split('path="res://', 1)[1].split('"', 1)[0]
                    self.assertTrue((ROOT / path).is_file(), f"{scene} references {path}")
        reference = self.module.godot_reference()
        flat = json.dumps(reference, allow_nan=False)
        self.assertTrue(flat)
        script = (ROOT / f"{IDENTITY}.gd").read_text(encoding="utf-8")
        self.assertIn("static func reference_values", script)


if __name__ == "__main__":
    unittest.main()
