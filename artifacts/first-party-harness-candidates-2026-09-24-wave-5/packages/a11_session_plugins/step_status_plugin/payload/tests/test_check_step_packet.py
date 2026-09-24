"""Tests for scripts/check_step_packet.py. Read-only: they use the shipped example packet and manifests held in memory."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_step_packet.py"
PACKET = ROOT / "examples" / "packet"
MANIFEST = PACKET / ".baltor" / "step" / "packet-manifest.json"
MANIFEST_PATH = ".baltor/step/packet-manifest.json"


def run(*arguments: str) -> tuple[int, dict]:
    finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--root", str(PACKET), *arguments],
                              capture_output=True, text=True, timeout=60,
                              env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")})
    return finished.returncode, json.loads(finished.stdout)


def load():
    spec = importlib.util.spec_from_file_location("packet_check_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def codes(report: dict) -> list[str]:
    return [failure["code"] for failure in report["failures"]]


class CheckStepPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load()
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def resealed(self, files: dict) -> dict:
        """A manifest whose content digest agrees with the given file map, as a careless rewrite would leave it."""
        return {**copy.deepcopy(self.manifest), "files": files, "packet_content_sha256": self.module.content_digest(files)}

    def test_example_packet_passes_and_reports_its_digest(self):
        code, report = run()
        self.assertEqual(code, 0, report)
        self.assertEqual((report["passed"], report["files_checked"], report["failures"]), (True, 5, []))
        self.assertEqual(report["packet_content_sha256"], self.manifest["packet_content_sha256"])
        self.assertEqual(report["step_id"], "list-failing-tests")
        self.assertFalse(report["bound_to_host_digest"])

    def test_host_digest_binds_the_packet(self):
        code, report = run("--expect-content-sha256", self.manifest["packet_content_sha256"])
        self.assertEqual((code, report["bound_to_host_digest"], report["failures"]), (0, True, []))
        code, report = run("--expect-content-sha256", "0" * 64)
        self.assertEqual((code, codes(report)), (1, ["not_the_expected_packet"]))

    def test_packet_file_edited_after_the_manifest_is_caught(self):
        # Known-wrong case: node_context.md was changed after the host wrote the manifest,
        # for example to relax the acceptance. The manifest still records the old bytes.
        files = copy.deepcopy(self.manifest["files"])
        files[".baltor/step/node_context.md"]["sha256"] = "a" * 64
        report = self.module.verify(PACKET, self.resealed(files), None, MANIFEST_PATH)
        self.assertFalse(report["passed"])
        self.assertEqual([(item["code"], item["path"]) for item in report["failures"]],
                         [("digest_differs", ".baltor/step/node_context.md")])

    def test_leftover_file_in_the_packet_folder_is_caught(self):
        # Known-wrong case: a file the manifest does not list sits in the step folder,
        # such as a note or an input left by an earlier step in a reused folder.
        files = {name: row for name, row in self.manifest["files"].items() if not name.endswith("checklist.md")}
        report = self.module.verify(PACKET, self.resealed(files), None, MANIFEST_PATH)
        self.assertEqual([(item["code"], item["path"]) for item in report["failures"]],
                         [("unlisted_file", ".baltor/step/checklist.md")])

    def test_manifest_content_digest_must_match_its_files(self):
        manifest = {**copy.deepcopy(self.manifest), "packet_content_sha256": "b" * 64}
        report = self.module.verify(PACKET, manifest, None, MANIFEST_PATH)
        self.assertEqual(codes(report), ["content_digest_differs"])

    def test_step_id_must_equal_the_task_node_id(self):
        manifest = {**copy.deepcopy(self.manifest), "step_id": "another-step"}
        report = self.module.verify(PACKET, manifest, None, MANIFEST_PATH)
        self.assertEqual(codes(report), ["step_id_differs"])

    def test_missing_and_resized_files_are_failures(self):
        files = copy.deepcopy(self.manifest["files"])
        files[".baltor/step/notes.md"] = {"sha256": "0" * 64, "size_bytes": 3}
        files["AGENTS.md"]["size_bytes"] += 1
        report = self.module.verify(PACKET, self.resealed(files), None, MANIFEST_PATH)
        self.assertEqual(sorted(codes(report)), ["file_missing", "size_differs"])

    def test_manifest_without_a_task_is_a_failure(self):
        files = {name: row for name, row in self.manifest["files"].items() if not name.endswith("task.json")}
        report = self.module.verify(PACKET, self.resealed(files), None, MANIFEST_PATH)
        self.assertEqual(codes(report), ["task_not_listed", "unlisted_file"])

    def test_content_digest_follows_the_file_map(self):
        files = self.manifest["files"]
        self.assertEqual(self.module.content_digest(files), self.manifest["packet_content_sha256"])
        changed = copy.deepcopy(files)
        changed["AGENTS.md"]["size_bytes"] += 1
        self.assertNotEqual(self.module.content_digest(changed), self.manifest["packet_content_sha256"])

    def test_manifest_shape_is_refused_before_files_are_read(self):
        manifest = self.manifest
        without_brief = {key: value for key, value in manifest.items() if key != "brief_sha256"}
        row = {"sha256": "0" * 64, "size_bytes": 1}
        cases = [({**manifest, "record_type": "packet/v9"}, "unsupported_manifest_record_type"),
                 (without_brief, "manifest_fields_differ"),
                 ({**manifest, "owner": "x"}, "manifest_fields_differ"),
                 ({**manifest, "context_version": True}, "manifest_value_invalid"),
                 ({**manifest, "state_version": 0}, "manifest_value_invalid"),
                 ({**manifest, "brief_sha256": "ABC"}, "manifest_value_invalid"),
                 ({**manifest, "step_id": ""}, "manifest_value_invalid"),
                 ({**manifest, "files": {}}, "manifest_files_invalid"),
                 ({**manifest, "files": {"../x.md": row}}, "manifest_path_unsafe"),
                 ({**manifest, "files": {"/etc/x.md": row}}, "manifest_path_unsafe"),
                 ({**manifest, "files": {"AGENTS.md": {"sha256": "0" * 64, "size_bytes": True}}},
                  "manifest_row_invalid")]
        for broken, error in cases:
            with self.assertRaises(self.module.Refused, msg=error) as caught:
                self.module.verify(PACKET, broken, None, MANIFEST_PATH)
            self.assertEqual(caught.exception.code, error)

    def test_unusable_arguments_are_refused(self):
        for arguments, error in ((("--manifest", "none.json"), "manifest_missing"),
                                 (("--manifest", "../outside.json"), "manifest_path_unsafe"),
                                 (("--expect-content-sha256", "ABC"), "expected_digest_invalid")):
            code, report = run(*arguments)
            self.assertEqual((code, report["passed"], report["error"]), (2, False, error))

    def test_duplicate_keys_in_a_manifest_are_refused(self):
        with self.assertRaises(self.module.Refused) as caught:
            self.module.strict_json(b'{"files": {}, "files": {}}')
        self.assertEqual(caught.exception.code, "duplicate_key")


if __name__ == "__main__":
    unittest.main()
