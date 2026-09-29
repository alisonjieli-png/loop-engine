"""Original components: exact source closure, execution, contracts and honest counts."""
from __future__ import annotations

import base64
import hashlib
import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tools import native_harness_candidates as native
from tools import prepare_harness_candidates as factory
from tools.creative_components import primitives
from tools.creative_components.catalogue import CASES
from tools.creative_components.packaging import SOURCES, package_files, proposals

ROOT = Path(__file__).resolve().parents[1]


class CreativeComponentTests(unittest.TestCase):
    def test_every_public_implementation_has_independent_fixtures(self):
        names = {name for name, value in vars(primitives).items()
                 if inspect.isfunction(value) and not name.startswith("_")}
        self.assertEqual(names, set(CASES))
        self.assertGreaterEqual(len(names), 30)

    def test_native_metadata_contract_accepts_every_proposal(self):
        document = proposals(ROOT, "a" * 40)
        normalized = native._proposal_metadata(document)
        factory._compile(normalized, "a" * 40, document["sources"], "MIT")
        packages, unique_files = set(), set()
        for row in document["proposals"]:
            package, _bodies = native._files(row["files"], row["declared_effects"])
            packages.add(package.package_digest)
            unique_files.update(entry.digest for entry in package.files)
            self.assertEqual(row["kind"], "tool")
            self.assertFalse(any(file["path"] == "SKILL.md" for file in row["files"]))
        self.assertEqual(len(packages), len(CASES))
        self.assertLess(len(unique_files), len(CASES) * 8, "shared files must not inflate distinct counts")

    def test_every_package_passes_existing_native_format_and_effect_checks(self):
        from tools.candidate_review.configuration import PanelConfiguration
        from tools.candidate_review.native import NativeReviewFile
        from tools.candidate_review.native_prechecks import (
            NativeEffectsRules,
            NativeFormatRules,
        )
        from tools.candidate_review.prechecks import PrecheckContext
        configuration = PanelConfiguration.from_dict(json.loads(
            (ROOT / "tools/candidate_review/resources/panel.json").read_text()))
        for row in proposals(ROOT, "a" * 40)["proposals"]:
            package, bodies = native._files(row["files"], row["declared_effects"])
            files = tuple(NativeReviewFile(entry, bodies[entry.path]) for entry in package.files)
            request = SimpleNamespace(files=files, package=package, dependencies=row["dependencies"],
                                      item={"reference": {"styles": row["styles"],
                                                          "declared_effects": row["declared_effects"]}},
                                      duplicate_material=b"\n".join(bodies.values()), identity=row["id"], cited_sources=())
            with self.subTest(component=row["id"]):
                self.assertEqual(NativeFormatRules({}, configuration.policy).findings(request, None), [])
                self.assertEqual(NativeEffectsRules({}, configuration.policy).findings(
                    request, PrecheckContext(configuration.policy, ())), [])

    def test_each_isolated_package_executes_examples_and_known_wrong_controls(self):
        with tempfile.TemporaryDirectory() as temporary:
            for name in CASES:
                folder = Path(temporary) / name
                folder.mkdir()
                files = package_files(name, b"fixture license", "a" * 40, {})
                for row in files:
                    target = folder / row["path"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(base64.b64decode(row["content_base64"]))
                with self.subTest(component=name):
                    result = subprocess.run([sys.executable, "-B", "test_component.py"], cwd=folder,
                                            capture_output=True, text=True, timeout=10, check=False,
                                            env={"PATH": str(Path(sys.executable).parent)})
                    self.assertEqual(result.returncode, 0, result.stderr)
                    contract = json.loads((folder / "contracts/operation.json").read_text())
                    self.assertEqual(hashlib.sha256((folder / "implementation.py").read_bytes()).hexdigest(),
                                     contract["implementation"]["sha256"])
                    fixtures = json.loads((folder / "verification/fixtures.json").read_text())
                    run = subprocess.run([sys.executable, "-B", "run.py"], cwd=folder, capture_output=True,
                                         input=json.dumps(fixtures["accepted"][0]["arguments"]), text=True, timeout=10,
                                         check=False)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertIn("result", json.loads(run.stdout))

    def test_committed_source_gate_is_used_before_writing(self):
        from tools.build_creative_components import build
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "run"
            with self.assertRaisesRegex(ValueError, "not authorized"):
                build(ROOT, folder)
            self.assertFalse(folder.exists())
        self.assertEqual(len(SOURCES), 3)

    def test_color_round_trip_and_pan_power(self):
        for number in range(101):
            value = number / 100
            self.assertAlmostEqual(primitives.linear_to_srgb(primitives.srgb_to_linear(value)), value, places=7)
            gains = primitives.equal_power_pan(2 * value - 1)
            self.assertAlmostEqual(sum(gain * gain for gain in gains), 1)
        direction = primitives.normalize_three(1.7e308, 1.7e308, 1.7e308)
        self.assertAlmostEqual(sum(value * value for value in direction), 1)

    def test_real_factory_materializes_only_pinned_source_and_counts_shared_files_once(self):
        from tools.build_creative_components import build
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = root / "repository"
            repository.mkdir()
            for name in (*SOURCES, "LICENSE"):
                destination = repository / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((ROOT / name).read_bytes())
            for args in (("init", "-q", "-b", "main"), ("add", "."),
                         ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                          "commit", "-qm", "original creative fixture")):
                subprocess.run(["git", "-C", str(repository), *args], check=True, capture_output=True)
            report = build(repository, root / "run", authorized=True)
            self.assertEqual(report["candidates"], len(CASES))
            self.assertEqual(report["payload_files"], 8 * len(CASES))
            self.assertLess(report["unique_payload_digests"], report["payload_files"])
            self.assertFalse(report["approved"])
            source = repository / SOURCES[0]
            source.write_bytes(source.read_bytes() + b"\n# modified\n")
            with self.assertRaisesRegex(ValueError, "differs"):
                build(repository, root / "refused", authorized=True)
            self.assertFalse((root / "refused").exists())

    def test_creative_operations_compose_in_existing_solution_loops_without_source_rewrite(self):
        from loop_engine import LoopLedger
        from loop_engine.code_nodes.solution_canvas import (
            SolutionLoopSpec,
            SolutionSpec,
            run_solution,
        )
        before = (ROOT / SOURCES[0]).read_bytes()
        registry = {
            "frame_time": lambda value, params: primitives.frame_time(value, params["rate"]),
            "progress": lambda value, params: primitives.segment_progress(value, params["start"], params["duration"]),
            "easing": lambda value, params: primitives.quadratic_out(value),
        }
        for duration, expected in ((2, 0.75), (4, 0.4375)):
            spec = SolutionSpec("creative.motion.sample", permitted_loop_modes=("deterministic",), loops=(
                SolutionLoopSpec("clock", "frame_time", params={"rate": 30},
                                 input_role="creative.frame/v1", output_role="creative.seconds/v1"),
                SolutionLoopSpec("segment", "progress", params={"start": 0, "duration": duration},
                                 input_role="creative.seconds/v1", output_role="creative.progress/v1"),
                SolutionLoopSpec("ease", "easing", input_role="creative.progress/v1",
                                 output_role="creative.progress/v1")))
            ledger = LoopLedger()
            self.assertTrue(spec.graph.validate().valid)
            self.assertAlmostEqual(run_solution(spec, registry, 30, ledger=ledger), expected)
            self.assertGreater(len(ledger.events), 0)
        self.assertEqual((ROOT / SOURCES[0]).read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
