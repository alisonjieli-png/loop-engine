"""Original components: exact source closure, execution, contracts and honest counts."""
from __future__ import annotations

import base64
import hashlib
import inspect
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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

    def test_image_crop_preserves_aspect_and_never_reveals_empty_edges(self):
        for width, height in ((400, 200), (200, 400), (301, 199)):
            for frame_width, frame_height in ((16, 9), (9, 16), (1, 1)):
                for focus_x, focus_y in ((0, 0), (0.5, 0.5), (1, 1)):
                    for zoom in (1, 1.2, 3):
                        x, y, w, h = primitives.focal_crop(width, height, frame_width, frame_height,
                                                            zoom, focus_x, focus_y)
                        self.assertGreaterEqual(x, 0)
                        self.assertGreaterEqual(y, 0)
                        self.assertLessEqual(x + w, width + 1e-9)
                        self.assertLessEqual(y + h, height + 1e-9)
                        self.assertAlmostEqual(w / h, frame_width / frame_height)
        self.assertEqual(primitives.focal_crop(400, 200, 1, 1, 2, 1, 0), [300, 0, 100, 100])

    def test_subject_safe_axis_refuses_an_impossible_crop(self):
        for focus in (0, 0.5, 1):
            origin, lower, upper = primitives.subject_safe_axis(400, 200, 180, 300, focus)
            self.assertEqual((lower, upper), (100, 180))
            self.assertLessEqual(origin, 180)
            self.assertGreaterEqual(origin + 200, 300)
        with self.assertRaises(ValueError):
            primitives.subject_safe_axis(400, 100, 180, 300, 0.5)

    def test_focal_crop_avoids_unrepresentable_intermediate_scale(self):
        for extent, frame in ((1e308, 1e-308), (1e-308, 1e308)):
            with self.subTest(extent=extent, frame=frame):
                result = primitives.focal_crop(extent, extent, frame, frame, 1, 0.5, 0.5)
                self.assertEqual(result, [0, 0, extent, extent])
        self.assertEqual(primitives.focal_crop(8e307, 4e307, 2e-308, 1e-308, 2, 0, 0),
                         [0, 0, 4e307, 2e307])

    def test_subject_safe_axis_refuses_a_wider_subject_despite_origin_rounding(self):
        start = 1e6
        end = math.nextafter(start, math.inf)
        self.assertGreater(end - start, 1e-10)
        with self.assertRaisesRegex(ValueError, "subject cannot fit"):
            primitives.subject_safe_axis(1e7, 1e-10, start, end, 0.5)

    def test_crop_extreme_binary_scales_preserve_relative_aspect_and_bounds(self):
        for image_exponent in (-1022, -900, 0, 900, 1023):
            for frame_exponent in (-1022, -900, 0, 900, 1022):
                extent = math.ldexp(1.0, image_exponent)
                frame = math.ldexp(1.0, frame_exponent)
                for frame_ratio in (0.5, 1, 2):
                    for zoom in (1, 2, 4):
                        for focus in (0, 0.5, 1):
                            with self.subTest(image=image_exponent, frame=frame_exponent,
                                              aspect=frame_ratio, zoom=zoom, focus=focus):
                                x, y, width, height = primitives.focal_crop(
                                    extent, extent, frame * frame_ratio, frame, zoom, focus, 1 - focus)
                                self.assertTrue(all(math.isfinite(v) for v in (x, y, width, height)))
                                self.assertGreater(width, 0)
                                self.assertGreater(height, 0)
                                self.assertGreaterEqual(x, 0)
                                self.assertGreaterEqual(y, 0)
                                self.assertLessEqual(x + width, extent)
                                self.assertLessEqual(y + height, extent)
                                self.assertEqual(width / height, frame_ratio)
        with self.assertRaises(ValueError):
            primitives.focal_crop(math.ulp(0.0), math.ulp(0.0), 1, 1, 2, 0, 0)

    def test_subject_interval_is_feasible_exactly_when_the_whole_subject_fits(self):
        for image in range(1, 9):
            for crop in range(1, image + 1):
                for start in range(image):
                    for end in range(start + 1, image + 1):
                        for focus in (0, 0.3, 0.5, 1):
                            with self.subTest(image=image, crop=crop, start=start, end=end, focus=focus):
                                if end - start > crop:
                                    with self.assertRaises(ValueError):
                                        primitives.subject_safe_axis(image, crop, start, end, focus)
                                    continue
                                origin, lower, upper = primitives.subject_safe_axis(image, crop, start, end, focus)
                                self.assertEqual(lower, max(0, end - crop))
                                self.assertEqual(upper, min(start, image - crop))
                                self.assertLessEqual(lower, origin)
                                self.assertLessEqual(origin, upper)
                                self.assertGreaterEqual(origin, 0)
                                self.assertLessEqual(origin + crop, image)
                                self.assertLessEqual(origin, start)
                                self.assertGreaterEqual(origin + crop, end)

    def test_focal_crop_refuses_unrepresentable_aspect_not_a_distorted_rectangle(self):
        extent = math.ulp(0.0)
        with self.assertRaisesRegex(ValueError, "aspect"):
            primitives.focal_crop(extent, extent, 2, 3, 1, 0, 0)

    def test_new_helpers_reject_boolean_shape_and_nonfinite_arguments(self):
        examples = {"focal_crop": [400, 200, 1, 1, 2, 0.5, 0.5],
                    "subject_safe_axis": [400, 200, 180, 300, 0.5],
                    "frame_progress": [1, 30]}
        for name, arguments in examples.items():
            operation = getattr(primitives, name)
            for port in range(len(arguments)):
                for invalid in (True, False, None, "1", [], {}, math.inf, -math.inf, math.nan):
                    trial = list(arguments)
                    trial[port] = invalid
                    with self.subTest(name=name, port=port, invalid=invalid), self.assertRaises((ValueError, TypeError)):
                        operation(*trial)
            for trial in (arguments[:-1], arguments + [1]):
                with self.subTest(name=name, arity=len(trial)), self.assertRaises(TypeError):
                    operation(*trial)

    def test_frame_progress_large_integers_remain_bounded_and_endpoint_inclusive(self):
        for count in (2, 3, 30, 30000, 2 ** 53 + 1, 10 ** 400):
            frames = sorted({0, 1, (count - 1) // 2, count - 2, count - 1})
            progress = [primitives.frame_progress(frame, count) for frame in frames]
            self.assertEqual(progress[0], 0)
            self.assertEqual(progress[-1], 1)
            self.assertEqual(progress, sorted(progress))
            self.assertTrue(all(0 <= value <= 1 and math.isfinite(value) for value in progress))

    def test_camera_regressions_reject_mechanism_specific_wrong_controls(self):
        def overflowing_crop(width, height, frame_width, frame_height, zoom, focus_x, focus_y):
            scale = min(width / frame_width, height / frame_height) / zoom
            width, height = frame_width * scale, frame_height * scale
            return [0, 0, width, height]

        def rounded_interval(image_extent, crop_extent, subject_start, subject_end, focus):
            lower = max(0, subject_end - crop_extent)
            upper = min(subject_start, image_extent - crop_extent)
            if lower > upper:
                raise ValueError("subject cannot fit inside this crop")
            return [max(lower, min(upper, focus * image_extent - crop_extent / 2)), lower, upper]

        controls = (
            ("focal_crop", overflowing_crop, "test_focal_crop_avoids_unrepresentable_intermediate_scale"),
            ("subject_safe_axis", rounded_interval,
             "test_subject_safe_axis_refuses_a_wider_subject_despite_origin_rounding"),
            ("frame_progress", lambda frame, frame_count: frame / frame_count,
             "test_discrete_frame_progress_reaches_both_endpoints"),
        )
        for name, operation, check in controls:
            result = unittest.TestResult()
            with self.subTest(component=name), patch.object(primitives, name, operation):
                type(self)(check).run(result)
                self.assertGreater(len(result.failures) + len(result.errors), 0)

    def test_discrete_frame_progress_reaches_both_endpoints(self):
        self.assertEqual(primitives.frame_progress(0, 1), 0)
        self.assertEqual(primitives.frame_progress(0, 30), 0)
        self.assertEqual(primitives.frame_progress(29, 30), 1)
        with self.assertRaises(ValueError):
            primitives.frame_progress(30, 30)
        with self.assertRaises(ValueError):
            primitives.frame_progress(0, 2.5)

    def test_camera_contract_names_frame_counts_and_normalized_focus(self):
        from tools.creative_components.catalogue import input_property
        self.assertEqual(input_property("frame_progress", "frame_count")["type"], "integer")
        self.assertEqual(input_property("focal_crop", "focus_x")["maximum"], 1)
        self.assertEqual(input_property("focal_crop", "zoom")["minimum"], 1)

    def test_camera_packages_keep_typed_shapes_and_refuse_bad_launcher_requests(self):
        from jsonschema import Draft202012Validator

        with tempfile.TemporaryDirectory() as temporary:
            for name in ("focal_crop", "subject_safe_axis", "frame_progress"):
                folder = Path(temporary) / name
                folder.mkdir()
                for row in package_files(name, b"fixture license", "a" * 40, {}):
                    target = folder / row["path"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(base64.b64decode(row["content_base64"]))
                contract = json.loads((folder / "contracts/operation.json").read_text())
                fixtures = json.loads((folder / "verification/fixtures.json").read_text())
                input_validator = Draft202012Validator(contract["input"])
                output_validator = Draft202012Validator(contract["output"])
                for row in fixtures["accepted"]:
                    with self.subTest(component=name, arguments=row["arguments"]):
                        input_validator.validate(row["arguments"])
                        result = subprocess.run([sys.executable, "-B", "run.py"], cwd=folder,
                                                input=json.dumps(row["arguments"]), capture_output=True,
                                                text=True, timeout=10, check=False,
                                                env={"PATH": str(Path(sys.executable).parent)})
                        self.assertEqual(result.returncode, 0, result.stderr)
                        output_validator.validate(json.loads(result.stdout))
                arguments = fixtures["accepted"][0]["arguments"]
                first = next(iter(arguments))
                for wrong in ([], {**arguments, first: True}, {**arguments, "unknown": 1},
                              {key: value for key, value in arguments.items() if key != first}):
                    with self.subTest(component=name, wrong=wrong):
                        self.assertFalse(input_validator.is_valid(wrong))
                        result = subprocess.run([sys.executable, "-B", "run.py"], cwd=folder,
                                                input=json.dumps(wrong), capture_output=True, text=True,
                                                timeout=10, check=False,
                                                env={"PATH": str(Path(sys.executable).parent)})
                        self.assertNotEqual(result.returncode, 0)
                        self.assertEqual(result.stdout, "")
                self.assertFalse(output_validator.is_valid({"result": [0] if name != "frame_progress" else []}))

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
