"""Tests for registering a harness by declaration.

The layout checks run anywhere. The sandbox scenarios start the fixture harness,
the custom Loop harness process and, where installed at its pinned version, Pi,
each in Bubblewrap with no network and no model; they are skipped, with the
reason, where Bubblewrap is missing.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

import register_step_harness as tool  # noqa: E402
from loop_engine.core.step_execution import harness_launch  # noqa: E402
from loop_engine.core.step_execution.harness_manifest import StepHarnessManifest, release_manifest_catalog  # noqa: E402
from loop_engine.core.step_execution.launch_checks import sandbox_checks  # noqa: E402


class LayoutChecks(unittest.TestCase):
    def test_every_packaged_manifest_uses_its_layout_profile_native_skill_folder(self):
        for manifest in release_manifest_catalog().manifests:
            with self.subTest(manifest=manifest.engine_ref):
                self.assertTrue(tool.layout_check(manifest)["matches"], tool.layout_check(manifest))

    def test_a_manifest_whose_skill_folder_differs_from_its_profile_is_refused(self):
        """Known wrong: a Codex-layout harness that places skills where Codex never reads them."""
        record = release_manifest_catalog().manifest("fixture.step_harness").to_dict()
        record["layout"]["skills_directory"] = ".codex/skills"
        wrong = StepHarnessManifest.from_dict(record)
        with self.assertRaises(tool.RegistrationRefused) as caught:
            tool.require_layout(wrong)
        self.assertEqual(caught.exception.code, "layout_differs_from_profile")

    def test_a_manifest_file_is_read_by_the_strict_reader(self):
        record = release_manifest_catalog().manifest("pi.print").to_dict()
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "manifest.json"
            path.write_text(json.dumps({**record, "allow_network": True}), encoding="utf-8")
            with self.assertRaises(ValueError):
                tool.read_manifest(path)
            path.write_text(json.dumps(record), encoding="utf-8")
            self.assertEqual(tool.read_manifest(path).content_digest,
                             release_manifest_catalog().manifest("pi.print").content_digest)


@unittest.skipUnless(harness_launch.sandbox_available(), "Bubblewrap and the system Python are required")
class SandboxScenarios(unittest.TestCase):
    def test_the_declared_harnesses_qualify_and_run_through_the_slot(self):
        report = sandbox_checks()
        failed = [item for item in report["tests"] if item["passed"] is not True]
        self.assertEqual(failed, [])


def _pi_at_pin():
    software = tool._pi_software()
    manifest = release_manifest_catalog().manifest("pi.print")
    return (software is not None and harness_launch.sandbox_available()
            and tool.installed_version(manifest, software.executable) == manifest.launch.pinned_version)


@unittest.skipUnless(_pi_at_pin(), "Pi at the manifest's pinned version and Bubblewrap are required")
class PiScenario(unittest.TestCase):
    def test_pi_loads_the_step_instructions_and_its_output_is_read_in_fixture_mode(self):
        software = tool._pi_software()
        with tempfile.TemporaryDirectory(prefix="le-pi-qualify-", dir=str(Path.home())) as root:
            report = tool.qualify(release_manifest_catalog().manifest("pi.print"), software.executable,
                                  software.software_paths, Path(root))
        self.assertEqual((report["qualification"]["decision"], report["qualification"]["ladder_rung"]),
                         ("approved", "step_finished"), report["run"])


if __name__ == "__main__":
    unittest.main()
