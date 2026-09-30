"""Structural, sizing, refusal and portable package checks for original asset references."""
from __future__ import annotations

import base64
import copy
import json
import math
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from jsonschema import Draft202012Validator

from tools import native_harness_candidates as native
from tools import prepare_harness_candidates as factory
from tools.procedural_assets.catalogue import (
    FAMILIES,
    construct,
    parameter_schema,
    reference_cases,
)
from tools.procedural_assets.geometry import gltf, inspect_mesh, preview
from tools.procedural_assets.packaging import proposals

ROOT = Path(__file__).resolve().parents[1]


class ProceduralAssetTests(unittest.TestCase):
    def test_website_previews_are_exact_outputs_of_the_original_constructor(self):
        for family, filename in (("bear", "procedural-bear-preview.svg"), ("conifer", "procedural-tree-preview.svg")):
            title, dimensions, _category = FAMILIES[family]
            expected = preview(construct(family, *dimensions), title, "isometric") + "\n"
            path = ROOT / "src/loop_engine/core/service_runtime/web_assets" / filename
            self.assertEqual(path.read_text(encoding="utf-8"), expected)

    def test_range_cases_have_valid_parameters_and_finite_nondegenerate_geometry(self):
        for family in FAMILIES:
            cases = list(reference_cases(family))
            self.assertEqual(len(cases), 15)
            self.assertEqual(len({json.dumps(p, sort_keys=True) for _name, p in cases}), 15)
            for name, parameters in cases:
                with self.subTest(family=family, case=name):
                    Draft202012Validator(parameter_schema(family)).validate(parameters)
                    parts = construct(family, **parameters)
                    checked = inspect_mesh(parts)
                    self.assertGreater(checked["triangles"], 0)
                    self.assertFalse(checked["visual_approved"])
                    self.assertEqual(parts, construct(family, **parameters))
                    self.assertTrue(all(checked["bounds_m"][1][i] > checked["bounds_m"][0][i] for i in range(3)))

    def test_box_house_and_water_have_independent_geometric_answers(self):
        from tools.procedural_assets.geometry import box
        cube = box("unit", [0, 1, 0], [2, 2, 2], [1, 1, 1])
        report = inspect_mesh([cube])
        self.assertEqual(report["bounds_m"], [[-1, 0, -1], [1, 2, 1]])
        self.assertEqual(report["triangles"], 12)
        house = construct("house", 6, 5, 7)
        self.assertEqual(inspect_mesh(house)["parts"], 5)
        self.assertEqual(max(v[1] for p in house for v in p["vertices"]), 5)
        water = construct("water_surface", 8, 0.3, 8)
        self.assertEqual(len(water[0]["triangles"]), 288)
        self.assertAlmostEqual(water[0]["vertices"][3][1], 0.15)

    def test_parameters_change_geometry_without_changing_its_constructor(self):
        for family, (_title, dimensions, _kind) in FAMILIES.items():
            baseline = construct(family, *dimensions)
            for axis in range(3):
                changed = list(dimensions)
                changed[axis] *= 1.2
                revised = construct(family, *changed)
                self.assertNotEqual(baseline, revised)
                self.assertEqual([p["triangles"] for p in baseline], [p["triangles"] for p in revised])

    def test_invalid_dimensions_unknown_families_and_mutated_meshes_fail(self):
        for family, (_title, dimensions, _kind) in FAMILIES.items():
            for bad in (0, -1, True, None, "1", math.nan, math.inf, 999999):
                with self.assertRaises((TypeError, ValueError)):
                    construct(family, bad, dimensions[1], dimensions[2])
        with self.assertRaises(ValueError):
            construct("unknown", 1, 1, 1)
        good = construct("bear", 0.7, 1, 0.55)
        for wrong in ([0, 0, 0], [0, 1, 999999], [False, 1, 2]):
            mutated = copy.deepcopy(good)
            mutated[0]["triangles"][0] = wrong
            with self.assertRaises(ValueError):
                inspect_mesh(mutated)
        mutated = copy.deepcopy(good)
        mutated[0]["vertices"][0][0] = math.nan
        with self.assertRaises(ValueError):
            inspect_mesh(mutated)

    def test_embedded_gltf_has_matching_buffers_valid_ranges_and_unit_normals(self):
        for family, (_title, dimensions, _kind) in FAMILIES.items():
            document = gltf(construct(family, *dimensions))
            self.assertEqual(document["asset"]["version"], "2.0")
            data = base64.b64decode(document["buffers"][0]["uri"].split(",", 1)[1], validate=True)
            self.assertEqual(document["buffers"][0]["byteLength"], len(data))
            for mesh in document["meshes"]:
                attributes = mesh["primitives"][0]["attributes"]
                for key, index in attributes.items():
                    accessor = document["accessors"][index]
                    view = document["bufferViews"][accessor["bufferView"]]
                    start, size = view["byteOffset"], view["byteLength"]
                    self.assertEqual(start % 4, 0)
                    self.assertEqual(size, accessor["count"] * 12)
                    vectors = list(struct.iter_unpack("<fff", data[start:start + size]))
                    for vector in vectors:
                        self.assertTrue(all(math.isfinite(value) for value in vector))
                        if key == "NORMAL":
                            self.assertAlmostEqual(sum(value * value for value in vector), 1, places=5)
            for view in ("front", "side", "top", "isometric"):
                svg = preview(construct(family, *dimensions), '<bad & title>', view)
                document_svg = ElementTree.fromstring(svg)
                self.assertGreater(len(document_svg.findall("{http://www.w3.org/2000/svg}polygon")), 0)
                self.assertNotIn("<bad", svg)

    def test_packages_fit_existing_contract_and_run_in_isolation(self):
        record = proposals(ROOT, "a" * 40)
        normalized = native._proposal_metadata(record)
        factory._compile(normalized, "a" * 40, record["sources"], "MIT")
        self.assertEqual(len(record["proposals"]), 24)
        digests, placements, families = set(), 0, set()
        with tempfile.TemporaryDirectory() as temporary:
            for row in record["proposals"]:
                package, bodies = native._files(row["files"], row["declared_effects"])
                digests.update(file.digest for file in package.files)
                placements += len(package.files)
                self.assertLessEqual(len(package.files), 64)
                folder = Path(temporary) / row["id"]
                for path, body in bodies.items():
                    destination = folder / path
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(body)
                card = json.loads(bodies["contract.json"])
                families.add(card["family"])
                check = subprocess.run([sys.executable, "-B", "test_asset.py"], cwd=folder, capture_output=True, timeout=30, check=False)
                self.assertEqual(check.returncode, 0, check.stderr.decode())
                parameters = {k: v["default"] for k, v in card["parameters"]["properties"].items()}
                run = subprocess.run([sys.executable, "-B", "run.py"], cwd=folder, input=json.dumps(parameters).encode(), capture_output=True, timeout=30, check=False)
                self.assertEqual(run.returncode, 0, run.stderr.decode())
                self.assertEqual(json.loads(run.stdout)["asset"]["version"], "2.0")
        self.assertEqual(families, set(FAMILIES))
        self.assertLess(len(digests), placements)
        self.assertGreater(len(digests), 1000)


if __name__ == "__main__":
    unittest.main()
