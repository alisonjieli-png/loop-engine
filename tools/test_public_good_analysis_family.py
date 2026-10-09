"""The public_good_analysis family through the creative_originals supply line: every item built at this checkout's
revision, every static qualification check on the exact stored bytes, and the sandbox and mutation checks on every
item when bubblewrap is available.

Known-wrong control: when the family's shared test module is replaced by one that cannot fail, a broken item would
pass its own tests, and the mutation check refuses it.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tools", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from supply_lines import creative_originals as line  # noqa: E402
from supply_lines.records import CREATIVE_ORIGINALS  # noqa: E402
from tools.component_qualification import checks, components  # noqa: E402
from tools.component_qualification.sandbox import SandboxSettings  # noqa: E402

FAMILY = "public_good_analysis"
#: The items built for the owner's DueCare datasets; the others were built for dataset shapes of the inventory.
DUECARE_ITEMS = ("judge_agreement", "labelled_score_summary", "paired_arm_lift", "redistribution_rights_filter",
                 "shard_manifest_audit", "split_leakage_check")
SHAPE_ITEMS = ("building_energy_use_intensity", "migration_deaths_and_missing", "rate_per_100k",
               "service_request_resolution_times")
REVISION = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
SANDBOX = SandboxSettings()
HAS_SANDBOX = bool(REVISION) and SANDBOX.works()


def generate(root: Path):
    return line.generate(code_revision=REVISION, licence_text=(ROOT / "LICENSE").read_bytes(),
                         generated_on="2026-10-09", retrieved_at="2026-10-09T00:00:00Z", evidence_root=None,
                         only_families=[FAMILY], root=root)


def component(folder: Path, built):
    payload, bodies = built
    target = folder / payload["record_id"]
    for entry in payload["package"]["files"]:
        path = target / entry["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(bodies[entry["digest"]])
    (target / "candidate.json").write_text(json.dumps(payload), encoding="utf-8")
    return components.from_folder(target)


class PublicGoodAnalysisFamilyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(tempfile.mkdtemp())
        cls.built, cls.refused, _facts, cls.summary = generate(line.FAMILIES_ROOT)
        cls.components = {built[0]["repository"]["identity"]: component(cls.root / "packages", built)
                          for built in cls.built}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root)

    def test_every_item_is_built_and_none_refused(self):
        self.assertEqual(self.refused, [])
        self.assertEqual(self.summary[FAMILY], {"items": 10, "built": 10, "refused": 0})
        self.assertEqual(sorted(self.components), sorted(DUECARE_ITEMS + SHAPE_ITEMS))
        for payload, _bodies in self.built:
            self.assertEqual(payload["line"], CREATIVE_ORIGINALS)
            self.assertEqual((payload["kind"], payload["component_form"]["form"]), ("code_module", "function"))
            paths = {row["path"] for row in payload["files"]}
            self.assertLessEqual({"kit_schema.py", "test_package.py", "component.json", "LICENSE",
                                  "examples/known_answers.json"}, paths)
            self.assertEqual(payload["tests"]["files"], ["test_package.py"])

    def test_every_card_names_its_dataset_shape_and_an_sdg_proposal(self):
        for identity, item in self.components.items():
            contract = json.loads(item.text("component.json"))["contract"]
            self.assertEqual(contract["sdg"]["status"], "proposal", identity)
            datasets = contract["derived_from"]["kaggle_datasets"]
            if identity in DUECARE_ITEMS:
                self.assertTrue(datasets and all(name.split("/")[1].startswith("duecare-") for name in datasets),
                                identity)
            else:
                self.assertEqual(datasets, [], identity)
                self.assertTrue(contract["sdg"]["indicators"] or contract["sdg"]["targets"], identity)

    def test_every_static_check_passes_on_the_stored_bytes(self):
        context = checks.QualificationContext.load(ROOT)
        context.duplicates = checks.duplicate_findings(list(self.components.values()), context.policy)
        for identity, item in self.components.items():
            for check in checks.CHECKS:
                if check.check_id in ("sandbox", "mutation"):
                    continue
                result = check.run(item, context)
                self.assertEqual(result.status, checks.PASSED, (identity, check.check_id, result.findings))

    @unittest.skipUnless(HAS_SANDBOX, "bubblewrap and the system interpreter are needed for the sandbox checks")
    def test_sandbox_and_mutation_pass_on_every_item(self):
        context = checks.QualificationContext.load(ROOT, sandbox_settings=SANDBOX, work_root=self.root / "work")
        by_id = {check.check_id: check for check in checks.CHECKS}
        for identity, item in self.components.items():
            for check_id in ("sandbox", "mutation"):
                result = by_id[check_id].run(item, context)
                self.assertEqual(result.status, checks.PASSED, (identity, check_id, result.findings))

    @unittest.skipUnless(HAS_SANDBOX, "bubblewrap and the system interpreter are needed for the sandbox checks")
    def test_known_wrong_a_test_module_that_cannot_fail_is_caught(self):
        families = self.root / "families"
        shutil.copytree(line.FAMILIES_ROOT / FAMILY, families / FAMILY,
                        ignore=shutil.ignore_patterns("__pycache__"))
        (families / FAMILY / "shared" / "test_package.py").write_text(
            "import unittest\n\n\nclass PackageTests(unittest.TestCase):\n"
            "    def test_nothing(self):\n        self.assertTrue(True)\n", encoding="utf-8")
        built, refused, _facts, _summary = generate(families)
        self.assertEqual(refused, [])
        weak = component(self.root / "weak", next(row for row in built
                                                  if row[0]["repository"]["identity"] == "rate_per_100k"))
        context = checks.QualificationContext.load(ROOT, sandbox_settings=SANDBOX, work_root=self.root / "work-weak")
        by_id = {check.check_id: check for check in checks.CHECKS}
        self.assertEqual(by_id["sandbox"].run(weak, context).status, checks.PASSED)
        self.assertEqual(by_id["mutation"].run(weak, context).status, checks.REFUSED)


if __name__ == "__main__":
    unittest.main()
