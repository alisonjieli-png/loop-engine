"""Known-wrong checks for complete, candidate-only native package preparation."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
import unittest
from contextlib import closing
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from loop_engine.catalog.stores.sqlite_store import SQLiteRecordStore
from loop_engine.core.service_runtime.catalogue_packages import (
    CataloguePackage,
)
from tools.prepare_harness_candidates import PreparationError
from tools.stage_intelligence_candidates import (
    CandidateStageRequest,
    compile_candidates,
    stage_candidates,
)
from tools.test_prepare_harness_candidates import CandidatePreparerChecks


def file_record(path, body, role, media_type="text/plain"):
    return {"path": path, "digest": hashlib.sha256(body).hexdigest(), "size_bytes": len(body),
            "media_type": media_type, "role": role, "content_base64": base64.b64encode(body).decode("ascii")}


class NativeCandidatePreparerChecks(unittest.TestCase):
    def setUp(self):
        self.fixture = CandidatePreparerChecks("test_wrong_revision_and_existing_output_refuse")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.repository = self.fixture.repository
        self.output = self.fixture.output
        self.root = self.fixture.root
        self.proposals = deepcopy(self.fixture.proposals)
        self.proposals["record_type"] = "harness_candidate_batch_proposals/v2"
        row = self.proposals["proposals"][0]
        row.pop("body")
        row.update(kind="tool", styles=["claude"], dependencies=["python>=3.12"],
                   producer={"producer_identity": "Original fixture author", "family": "fixture",
                             "method_identity": "original_fixture_authoring/v1"},
                   declared_effects=["spawns_process"], files=[
                       file_record("AGENTS.md", b"# Assignment\nInspect input.json first.\n", "instruction_file"),
                       file_record(".claude-plugin/plugin.json", b'{"name":"fixture-tool"}', "plugin_manifest", "application/json"),
                       file_record("scripts/check.py", b"print('fixture')\n", "executable_tool", "text/x-python"),
                       file_record("contracts/result.schema.json", b'{"type":"object"}', "configuration", "application/schema+json"),
                       file_record("assets/example.bin", b"\x00\xff\x10", "skill_asset", "application/octet-stream"),
                   ])

    def prepare(self, record=None):
        return self.fixture._prepare(self.proposals if record is None else record)

    def population(self):
        return json.loads((self.output / "specifications-001.json").read_text())

    def request(self):
        return CandidateStageRequest(self.repository, "fixture.native", True, self.output)

    def test_complete_tree_uses_canonical_package_and_preserves_binary_bytes(self):
        report = self.prepare()
        self.assertEqual(report["candidates"], 1)
        self.assertEqual(report["payload_files"], 5)
        self.assertFalse(report["approved"])
        row = self.population()["specifications"][0]
        package = CataloguePackage.from_dict(row["package"])
        self.assertEqual(row["package_digest"], package.package_digest)
        for file in self.proposals["proposals"][0]["files"]:
            self.assertEqual((self.output / row["package_root"] / file["path"]).read_bytes(),
                             base64.b64decode(file["content_base64"]))
        self.assertEqual((self.output / row["body_path"]).read_bytes(), package.document())
        self.assertFalse((self.output / "reviews.json").exists())
        self.assertFalse((self.output / "host-release").exists())

    def test_native_population_stages_atomically_as_candidates_only(self):
        self.prepare()
        request = self.request()
        records = compile_candidates(self.population(), request)
        self.assertEqual(records[0]["payload"]["dependencies"], ["python>=3.12"])
        self.assertEqual(records[0]["payload"]["producer"]["family"], "fixture")
        self.assertEqual(records[0]["payload"]["license_state"], "pending_review")
        with closing(SQLiteRecordStore(str(self.root / "native.sqlite"))) as store:
            self.assertTrue(stage_candidates(store, records, request).committed)
            self.assertEqual(store.get(records[0]["record_id"]), records[0])
        self.assertFalse(records[0]["payload"]["execution_available"])

    def test_corrupt_payload_digest_refuses_before_output(self):
        self.proposals["proposals"][0]["files"][0]["digest"] = "0" * 64
        with self.assertRaisesRegex(PreparationError, "native_file_bytes_mismatch"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_executable_effect_cannot_be_omitted(self):
        self.proposals["proposals"][0]["declared_effects"] = []
        with self.assertRaisesRegex(PreparationError, "package_executable_effect_undeclared"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_case_collision_and_file_parent_collision_refuse(self):
        for path in ("agents.MD", "AGENTS.md/nested.txt", "../escape", ".git/config"):
            record = deepcopy(self.proposals)
            record["proposals"][0]["files"].append(file_record(path, b"other", "other"))
            with self.subTest(path=path), self.assertRaises(PreparationError):
                self.prepare(record)
            self.assertFalse(self.output.exists())

    def test_duplicate_package_under_new_identity_refuses_inflated_count(self):
        other = deepcopy(self.proposals["proposals"][0])
        other["id"] = "different_identity"
        other["title"] = "Different title"
        self.proposals["proposals"].append(other)
        with self.assertRaisesRegex(PreparationError, "duplicate_native_package"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_unknown_producer_dependency_or_approval_field_refuses(self):
        changes = [{"producer": {"family": "fixture"}}, {"dependencies": [None]},
                   {"approved": True}, {"files": []}]
        for change in changes:
            record = deepcopy(self.proposals)
            record["proposals"][0].update(change)
            with self.subTest(change=change), self.assertRaises(PreparationError):
                self.prepare(record)
            self.assertFalse(self.output.exists())

    def test_staging_requires_explicit_package_root(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "package_root_required"):
            compile_candidates(self.population(), CandidateStageRequest(self.repository, "fixture.native"))

    def test_staging_rechecks_changed_missing_and_extra_files(self):
        self.prepare()
        row = self.population()["specifications"][0]
        target = self.output / row["package_root"] / "AGENTS.md"
        original = target.read_bytes()
        target.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "native_file_bytes_mismatch"):
            compile_candidates(self.population(), self.request())
        target.unlink()
        with self.assertRaisesRegex(ValueError, "native_package_inventory_mismatch"):
            compile_candidates(self.population(), self.request())
        target.write_bytes(original)
        (target.parent / "unexpected.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "native_package_inventory_mismatch"):
            compile_candidates(self.population(), self.request())

    def test_staging_rejects_symlinks_and_fifos_before_read(self):
        self.prepare()
        row = self.population()["specifications"][0]
        target = self.output / row["package_root"] / "AGENTS.md"
        target.unlink()
        target.symlink_to(self.repository / "LICENSE")
        with self.assertRaisesRegex(ValueError, "native_package_not_regular"):
            compile_candidates(self.population(), self.request())
        target.unlink()
        os.mkfifo(target)
        with self.assertRaisesRegex(ValueError, "native_package_not_regular"):
            compile_candidates(self.population(), self.request())

    def test_staging_rejects_forged_manifest_body_and_producer(self):
        self.prepare()
        population = self.population()
        row = population["specifications"][0]
        (self.output / row["body_path"]).write_text("{}")
        with self.assertRaisesRegex(ValueError, "native_package_document_mismatch"):
            compile_candidates(population, self.request())

    def test_old_stage_reader_refuses_native_population_version(self):
        self.prepare()
        self.assertEqual(self.population()["record_type"], "candidate_intelligence_specifications/v3")
        population = self.population()
        population["record_type"] = "candidate_intelligence_specifications/v1"
        with self.assertRaises(ValueError):
            compile_candidates(population, self.request())

    def test_producer_method_is_required_and_staging_refuses_unknown_effect(self):
        record = deepcopy(self.proposals)
        del record["proposals"][0]["producer"]["method_identity"]
        with self.assertRaisesRegex(PreparationError, "native_producer_invalid"):
            self.prepare(record)
        self.prepare()
        population = self.population()
        population["specifications"][0]["declared_effects"].append("invented_permission")
        with self.assertRaisesRegex(ValueError, "native_effects_invalid"):
            compile_candidates(population, self.request())

    def test_duplicate_json_fields_refuse_before_output(self):
        from tools.prepare_harness_candidates import PreparationRequest, prepare
        raw = json.dumps(self.proposals)
        raw = raw.replace('"files": [', '"files": [], "files": [', 1)
        self.fixture.input.write_text(raw)
        with self.assertRaisesRegex(PreparationError, "proposals_unreadable"):
            prepare(PreparationRequest(self.repository, self.fixture.input, self.output, True))
        self.assertFalse(self.output.exists())

    def test_review_and_generator_share_canonical_preparation_exception_in_either_import_order(self):
        for first in ("tools.generate_original_native_candidates", "candidate_review.native"):
            with self.subTest(first=first):
                script = '''import importlib,sys
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[1] + '/tools')
importlib.import_module(sys.argv[2])
from tools import prepare_harness_candidates as factory
from tools import native_harness_candidates as native
from candidate_review import native as reader
assert factory.__name__ == 'tools.prepare_harness_candidates'
assert reader.PreparationError is factory.PreparationError
assert native.preparation is factory
assert 'prepare_harness_candidates' not in sys.modules
from tools import stage_intelligence_candidates as stage
from tools import ingest_outside_material as ingestion
assert ingestion.CandidateStageRequest is stage.CandidateStageRequest
assert 'stage_intelligence_candidates' not in sys.modules
'''
                result = subprocess.run([sys.executable, "-c", script, str(ROOT), first],
                    cwd=self.repository,
                    env={"PATH": os.environ["PATH"], "PYTHONPATH": str(ROOT / "src")},
                    capture_output=True, text=True, timeout=30, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_documented_script_invocation_works_without_repository_on_pythonpath(self):
        self.fixture.input.write_text(json.dumps(self.proposals))
        result = subprocess.run([sys.executable, str(ROOT / "tools/prepare_harness_candidates.py"),
            "--repository", ".", "--proposals", str(self.fixture.input),
            "--output", str(self.output), "--authorize-preparation"], cwd=self.repository,
            env={"PATH": os.environ["PATH"], "PYTHONPATH": str(ROOT / "src")},
            capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["payload_files"], 5)

    def test_script_refusal_is_typed_json_without_traceback(self):
        self.proposals["proposals"][0]["files"][0]["digest"] = "0" * 64
        self.fixture.input.write_text(json.dumps(self.proposals))
        for invocation in ([str(ROOT / "tools/prepare_harness_candidates.py")],
                           ["-m", "tools.prepare_harness_candidates"]):
            with self.subTest(invocation=invocation):
                pythonpath = str(ROOT / "src")
                if invocation[0] == "-m":
                    pythonpath += os.pathsep + str(ROOT)
                result = subprocess.run([sys.executable, *invocation,
                    "--repository", str(self.repository), "--proposals", str(self.fixture.input),
                    "--output", str(self.output), "--authorize-preparation"], cwd=self.root,
                    env={"PATH": os.environ["PATH"], "PYTHONPATH": pythonpath},
                    capture_output=True, text=True, timeout=30, check=False)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stderr, "")
                self.assertIn("native_file_bytes_mismatch", json.loads(result.stdout)["refusal"])


if __name__ == "__main__":
    unittest.main()
