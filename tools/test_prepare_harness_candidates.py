"""Known-wrong checks for offline, candidate-only harness batch preparation."""
from __future__ import annotations

from copy import deepcopy
from contextlib import closing
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from tools.prepare_harness_candidates import PreparationError, PreparationRequest, prepare  # noqa: E402
from tools.stage_intelligence_candidates import (  # noqa: E402
    CandidateStageRequest, compile_candidates, stage_candidates,
)
from loop_engine.catalog.stores.sqlite_store import SQLiteRecordStore  # noqa: E402


def _git(repository: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repository), *args], capture_output=True,
                            text=True, check=True, timeout=20)
    return result.stdout.strip()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class CandidatePreparerChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repository = self.root / "repository"
        self.repository.mkdir()
        _git(self.repository, "init", "-q")
        _git(self.repository, "config", "user.name", "Fixture")
        _git(self.repository, "config", "user.email", "fixture@example.invalid")
        (self.repository / "LICENSE").write_bytes((ROOT / "LICENSE").read_bytes())
        source = self.repository / "source.py"
        source.write_text("def inspect(value):\n    return value\n", encoding="utf-8")
        _git(self.repository, "add", "LICENSE", "source.py")
        _git(self.repository, "commit", "-qm", "fixture")
        self.revision = _git(self.repository, "rev-parse", "HEAD")
        self.input = self.root / "proposals.json"
        self.output = self.root / "prepared"
        self.proposals = {
            "record_type": "harness_candidate_batch_proposals/v1",
            "source_revision": self.revision,
            "license": {"expression": "MIT", "path": "LICENSE",
                        "sha256": _sha((self.repository / "LICENSE").read_bytes())},
            "sources": {"source.py": _sha(source.read_bytes())},
            "proposals": [self._proposal(1)],
        }

    def _proposal(self, number: int) -> dict:
        identity = f"inspect_value_{number:04d}"
        title = f"Inspect value {number:04d}"
        return {"id": identity, "title": title,
                "purpose": f"Inspect fixture value {number:04d}. Use for a batch-preparation test.",
                "body": f"# {title}\n\nFixture candidate {number:04d}; it has no measured task value.\n",
                "sources": ["source.py"], "layer": "code", "family": "code_reference",
                "search_tags": ["fixture", "inspection"], "tags": {"language": ["en"]},
                "symbols": ["inspect"]}

    def _prepare(self, proposals=None, output=None):
        self.input.write_text(json.dumps(proposals or self.proposals), encoding="utf-8")
        return prepare(PreparationRequest(self.repository, self.input, output or self.output, True))

    def test_one_item_matches_existing_refresh_and_staging_shapes(self):
        report = self._prepare()
        self.assertEqual(report["candidates"], 1)
        self.assertEqual(report["population_files"], ["specifications-001.json"])
        self.assertFalse(report["approved"])
        items = json.loads((self.output / "items.json").read_text(encoding="utf-8"))
        self.assertEqual(items["record_type"], "starter_catalogue_candidate_items/v2")
        self.assertEqual(items["publication"], "not_published")
        reference = items["items"][0]["reference"]
        self.assertEqual(reference["family"], "harness")
        self.assertEqual(reference["source_layer"], "harness_local")
        self.assertEqual(reference["tags"]["lifecycle"], ["candidate"])
        self.assertEqual(reference["digest"], _sha((self.output / "bodies" /
                                                    "inspect_value_0001.md").read_bytes()))
        specs = json.loads((self.output / "specifications-001.json").read_text(encoding="utf-8"))
        compiled = compile_candidates(specs, CandidateStageRequest(self.repository, "fixture.candidates"))
        self.assertEqual(len(compiled), 1)
        self.assertEqual(compiled[0]["lifecycle"], "candidate")
        import importlib.util
        module_path = ROOT / "examples/29_intelligence_service/starter-catalogue/refresh.py"
        specification = importlib.util.spec_from_file_location("catalogue_refresh_fixture", module_path)
        module = importlib.util.module_from_spec(specification)
        sys.modules[specification.name] = module
        specification.loader.exec_module(module)
        populations, loaded_items, bodies = module.load_catalogue(self.output)
        self.assertEqual(module.stale_identities(populations, loaded_items, bodies), [])

    def test_one_thousand_synthetic_candidates_are_bounded_to_twenty_population_files(self):
        proposals = deepcopy(self.proposals)
        proposals["proposals"] = [self._proposal(index) for index in range(1, 1001)]
        report = self._prepare(proposals)
        self.assertEqual(report["candidates"], 1000)
        self.assertEqual(len(report["population_files"]), 20)
        self.assertEqual(len(list((self.output / "bodies").glob("*.md"))), 1000)
        with closing(SQLiteRecordStore(str(self.root / "candidate-review.db"))) as store:
            for name in report["population_files"]:
                population = json.loads((self.output / name).read_text(encoding="utf-8"))
                self.assertEqual(len(population["specifications"]), 50)
                request = CandidateStageRequest(self.repository, "fixture.candidates", True)
                records = compile_candidates(population, request)
                self.assertEqual(len(records), 50)
                self.assertTrue(stage_candidates(store, records, request).committed)
            self.assertEqual(len(store.export()["records"]), 1000)
        import importlib.util
        module_path = ROOT / "examples/29_intelligence_service/starter-catalogue/refresh.py"
        specification = importlib.util.spec_from_file_location("catalogue_refresh_large_fixture", module_path)
        module = importlib.util.module_from_spec(specification)
        sys.modules[specification.name] = module
        specification.loader.exec_module(module)
        populations, loaded_items, bodies = module.load_catalogue(self.output)
        self.assertEqual(module.stale_identities(populations, loaded_items, bodies), [])
        self.assertFalse((self.output / "reviews.json").exists())
        self.assertFalse((self.output / "host-release").exists())
        with self.assertRaisesRegex(PreparationError, "output_already_exists"):
            self._prepare(proposals)

    def test_stale_source_and_declared_digest_mismatch_refuse_before_output(self):
        (self.repository / "source.py").write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(PreparationError, "source_bytes_changed"):
            self._prepare()
        self.assertFalse(self.output.exists())
        _git(self.repository, "checkout", "--", "source.py")
        proposals = deepcopy(self.proposals)
        proposals["sources"]["source.py"] = "0" * 64
        with self.assertRaisesRegex(PreparationError, "source_digest_mismatch"):
            self._prepare(proposals)
        self.assertFalse(self.output.exists())

    def test_unknown_or_false_license_refuses(self):
        for change in ({"expression": "UNKNOWN"}, {"sha256": "0" * 64}):
            proposals = deepcopy(self.proposals)
            proposals["license"].update(change)
            with self.subTest(change=change), self.assertRaises(PreparationError):
                self._prepare(proposals)
            self.assertFalse(self.output.exists())

    def test_unsafe_duplicate_or_unapproved_lifecycle_refuses(self):
        for identity in ("../escape", "bad__name", "Uppercase", "bad-name"):
            proposals = deepcopy(self.proposals)
            proposals["proposals"][0]["id"] = identity
            with self.subTest(identity=identity), self.assertRaises(PreparationError):
                self._prepare(proposals)
        proposals = deepcopy(self.proposals)
        proposals["proposals"].append(deepcopy(proposals["proposals"][0]))
        with self.assertRaisesRegex(PreparationError, "duplicate_identity"):
            self._prepare(proposals)
        proposals = deepcopy(self.proposals)
        proposals["proposals"][0]["tags"]["lifecycle"] = ["qualified"]
        with self.assertRaises(PreparationError):
            self._prepare(proposals)
        self.assertFalse(self.output.exists())

    def test_symlink_and_path_escape_refuse(self):
        (self.repository / "linked.py").symlink_to(self.repository / "source.py")
        for source in ("linked.py", "../source.py", "/etc/passwd", ".git/config"):
            proposals = deepcopy(self.proposals)
            proposals["sources"] = {source: _sha((self.repository / "source.py").read_bytes())}
            proposals["proposals"][0]["sources"] = [source]
            with self.subTest(source=source), self.assertRaises(PreparationError):
                self._prepare(proposals)
        self.assertFalse(self.output.exists())

    def test_wrong_revision_and_existing_output_refuse(self):
        proposals = deepcopy(self.proposals)
        proposals["source_revision"] = "0" * 40
        with self.assertRaisesRegex(PreparationError, "revision_mismatch"):
            self._prepare(proposals)
        self.output.mkdir()
        with self.assertRaisesRegex(PreparationError, "output_already_exists"):
            self._prepare()

    def test_no_write_authority_and_symlinked_output_parent_refuse(self):
        self.input.write_text(json.dumps(self.proposals), encoding="utf-8")
        with self.assertRaisesRegex(PreparationError, "preparation_not_authorized"):
            prepare(PreparationRequest(self.repository, self.input, self.output))
        linked_parent = self.root / "linked-parent"
        linked_parent.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(PreparationError, "unsafe_output_path"):
            self._prepare(output=linked_parent / "candidate-output")
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
