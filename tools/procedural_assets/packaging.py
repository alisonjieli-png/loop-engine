"""Native candidate packages for parameterized assets and range-test references.

Two test groups per constructor keep packages below the existing 64-file cap.
They are not separate generator capabilities. Shared code remains byte-identical.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from tools.creative_components.packaging import file_record, json_bytes

from .catalogue import FAMILIES, construct, parameter_schema, reference_cases
from .geometry import gltf, inspect_mesh, preview

SOURCES = ("tools/procedural_assets/__init__.py", "tools/procedural_assets/geometry.py",
           "tools/procedural_assets/catalogue.py", "tools/procedural_assets/packaging.py",
           "tools/procedural_assets/ART-DIRECTION-TEMPLATES.md")
LIMITS = ("Static original blockout and range-test reference. No textures, UVs, skinning, rig, animation, "
          "collision qualification, anatomical accuracy, cloth, suspension or fluid simulation. "
          "Sun is visible geometry, not a light. Previews are mesh-derived SVGs, not native-engine renders. "
          "Parts may intentionally overlap. No independent approval or measured creative advantage.")
RUNNER = '''"""Read one declared sizing request; print a self-contained glTF document."""
import json
import sys
from assetkit.catalogue import construct
from assetkit.geometry import gltf
from pathlib import Path

if __name__ == "__main__":
    card = json.loads((Path(__file__).parent / "contract.json").read_text())
    raw = sys.stdin.buffer.read(4097)
    if len(raw) > 4096:
        raise ValueError("request_limit")
    parameters = json.loads(raw)
    if type(parameters) is not dict or set(parameters) != {"width", "height", "depth"}:
        raise ValueError("sizing_fields_required")
    print(json.dumps(gltf(construct(card["family"], **parameters)), allow_nan=False))
'''
CHECKS = '''"""Structural checks and a deliberately broken triangle; not aesthetic approval."""
import json
from pathlib import Path
import unittest
from assetkit.catalogue import construct
from assetkit.geometry import inspect_mesh

ROOT = Path(__file__).parent
CARD = json.loads((ROOT / "contract.json").read_text())

class AssetTests(unittest.TestCase):
    def test_range_references(self):
        for path in sorted((ROOT / "references").glob("*/recipe.json")):
            row = json.loads(path.read_text())
            actual = inspect_mesh(construct(CARD["family"], **row["parameters"]))
            self.assertEqual(actual, row["structural_check"])
            self.assertGreater(actual["triangles"], 0)

    def test_refuses_bad_values_and_broken_geometry(self):
        parameters = {k: v["default"] for k, v in CARD["parameters"]["properties"].items()}
        for name in parameters:
            for wrong in (0, -1, True, None, "1", float("nan"), float("inf"), 100000):
                with self.assertRaises((ValueError, TypeError)):
                    construct(CARD["family"], **{**parameters, name: wrong})
        parts = construct(CARD["family"], **parameters)
        parts[0]["triangles"][0] = [0, 0, 0]
        with self.assertRaises(ValueError):
            inspect_mesh(parts)

if __name__ == "__main__":
    unittest.main()
'''


def proposals(repository, revision):
    repository = Path(repository)
    here = Path(__file__).resolve().parents[2]
    if any((repository / name).read_bytes() != (here / name).read_bytes() for name in SOURCES):
        raise ValueError("generator_source_mismatch")
    licence = (repository / "LICENSE").read_bytes()
    digests = {name: hashlib.sha256((repository / name).read_bytes()).hexdigest() for name in SOURCES}
    rows = []
    for family, (title, _defaults, category) in FAMILIES.items():
        cases = list(reference_cases(family))
        for group, selected in (("axis_ranges", cases[:7]), ("range_corners", cases[7:])):
            card = {"record_type": "procedural_asset_constructor/v1", "family": family,
                    "capability_type": "procedural_generator", "execution_mode": "deterministic_code",
                    "engine": {"identity": "baltor.original_static_mesh", "version": "1.0.0",
                               "source_digests": {name: digests[name] for name in SOURCES[:3]}},
                    "reproducibility": {"tested": "same constructor and parameters in one Python environment",
                                        "random_source": "none", "gpu_required": False, "cross_platform_bytes": "not_qualified"},
                    "reference_group": group, "purpose": title, "parameters": parameter_schema(family),
                    "output": "glTF 2.0 embedded buffer, static meshes", "coordinate_system": {
                        "units": "metres", "handedness": "right", "up": "+Y", "front": "-Z"},
                    "effects": ["reads_fs", "spawns_process"], "implementation_sha256": digests[SOURCES[2]],
                    "limits": LIMITS, "qualification": "candidate_only"}
            files = [("assetkit/__init__.py", b'"""Original asset constructor package."""\n', "other", "text/x-python"),
                     ("assetkit/geometry.py", (repository / SOURCES[1]).read_bytes(), "executable_tool", "text/x-python"),
                     ("assetkit/catalogue.py", (repository / SOURCES[2]).read_bytes(), "executable_tool", "text/x-python"),
                     ("run.py", RUNNER.encode(), "executable_tool", "text/x-python"),
                     ("test_asset.py", CHECKS.encode(), "executable_tool", "text/x-python"),
                     ("contract.json", json_bytes(card), "other", "application/json"),
                     ("provenance.json", json_bytes({"source_revision": revision, "source_digests": digests,
                         "authoring": "original_assistant_authored", "generator": "procedural_assets/v1"}), "other", "application/json"),
                     ("AGENTS.md", (f"# {title}\n\nRead contract.json before source. Change width, height and depth in metres; "
                         "send their JSON object to `python -B run.py`. The output is glTF, with no external resources. "
                         "Run `python -B test_asset.py` for geometry and refusal checks. "
                         f"This package holds {group.replace('_', ' ')} examples of the same constructor, not new implementations. "
                         f"{LIMITS}\n").encode(), "instruction_file", "text/markdown"),
                     ("ART-DIRECTION-TEMPLATES.md", (repository / SOURCES[4]).read_bytes(), "instruction_file", "text/markdown"),
                     ("LICENSE", licence, "other", "text/plain")]
            for case, parameters in selected:
                parts = construct(family, **parameters)
                stem = "references/" + case + "/"
                files.append((stem + "recipe.json", json_bytes({"record_type": "procedural_asset_reference/v1",
                    "family": family, "case": case, "parameters": parameters, "structural_check": inspect_mesh(parts),
                    "source_model": "model.gltf", "views": ["front.svg", "side.svg", "top.svg", "isometric.svg"],
                    "synthetic": True, "limits": LIMITS}), "skill_asset", "application/json"))
                files.append((stem + "model.gltf", json_bytes(gltf(parts)), "skill_asset", "model/gltf+json"))
                for view in ("front", "side", "top", "isometric"):
                    files.append((stem + view + ".svg", preview(parts, family.replace("_", " "), view).encode(), "skill_asset", "image/svg+xml"))
            rows.append({"id": "asset_" + family + "_" + group, "title": title + ": " + group.replace("_", " "),
                         "purpose": title + "; a parameterized constructor and structural sizing references, not a production-ready game asset.",
                         "sources": list(SOURCES), "layer": "code", "family": "procedural_asset_references", "kind": "tool",
                         "search_tags": sorted({"parametric", "glTF", category, family, "reference"}), "tags": {"language": ["en"]},
                         "symbols": [family], "declared_effects": ["reads_fs", "spawns_process"], "styles": ["codex"],
                         "dependencies": ["python>=3.10"], "producer": {"producer_identity": "Baltor original procedural asset factory",
                            "family": "openai", "method_identity": "procedural_assets/v1"}, "files": [file_record(*row) for row in files]})
    return {"record_type": "harness_candidate_batch_proposals/v2", "source_revision": revision,
            "license": {"expression": "MIT", "path": "LICENSE", "sha256": hashlib.sha256(licence).hexdigest()},
            "sources": digests, "proposals": rows}
