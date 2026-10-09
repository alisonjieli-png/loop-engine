"""The creative_originals supply line end to end: a temporary family, its native evidence, the built candidate, and
every qualification check on the exact stored bytes (the sandbox and mutation checks when bubblewrap is available).

Known-wrong controls: an item without evidence, an item edited after its evidence, and a failed native record are
refused by name; a package whose test accepts a broken module fails the mutation check.
"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tools", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from supply_lines import creative_originals as line  # noqa: E402
from supply_lines.records import CREATIVE_ORIGINALS  # noqa: E402
from tools.component_qualification import checks, components  # noqa: E402
from tools.component_qualification.sandbox import SandboxSettings  # noqa: E402
from tools.creative_originals import verify  # noqa: E402
from tools.test_creative_originals import add_item, make_family  # noqa: E402

REVISION = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
SANDBOX = SandboxSettings()
HAS_SANDBOX = bool(REVISION) and SANDBOX.works()


class CreativeOriginalsLineTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.families = self.root / "families"
        self.families.mkdir()
        self.family = make_family(self.families)
        self.evidence = self.root / "evidence"
        with redirect_stdout(io.StringIO()):
            verify.main(["--family", "demo_family", "--root", str(self.families), "--output", str(self.evidence)])

    def tearDown(self):
        shutil.rmtree(self.root)

    def generate(self):
        return line.generate(code_revision=REVISION, licence_text=(ROOT / "LICENSE").read_bytes(),
                             generated_on="2026-10-09", retrieved_at="2026-10-09T00:00:00Z",
                             evidence_root=self.evidence, root=self.families)

    def component(self, built):
        payload, bodies = built
        folder = self.root / "package" / payload["record_id"]
        for entry in payload["package"]["files"]:
            target = folder / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bodies[entry["digest"]])
        (folder / "candidate.json").write_text(json.dumps(payload), encoding="utf-8")
        return components.from_folder(folder)

    def test_candidate_carries_the_contract_card_evidence_and_pinned_sources(self):
        built, refused, _facts, summary = self.generate()
        self.assertEqual(refused, [])
        self.assertEqual(summary["demo_family"], {"items": 1, "built": 1, "refused": 0})
        payload, _bodies = built[0]
        self.assertEqual(payload["line"], CREATIVE_ORIGINALS)
        origins = {row["path"]: row["origin"] for row in payload["files"]}
        self.assertEqual(origins["component.json"], "generated")
        self.assertEqual(origins["verification/native.json"], "generated")
        self.assertEqual(origins["preview.png"], "generated")
        self.assertEqual(origins["shape.txt"], "upstream_verbatim")
        self.assertEqual(origins["LICENSE"], "licence_text")
        upstream = next(row["upstream"] for row in payload["files"] if row["path"] == "tally.py")
        self.assertTrue(upstream["url"].startswith(f"https://raw.githubusercontent.com/{line.REPOSITORY}/{REVISION}/"))
        self.assertIn("spawns_process", payload["declared_effects"])
        media = {row["path"]: row["media_type"] for row in payload["files"]}
        self.assertEqual(media["preview.png"], "image/png")

    def test_every_static_check_passes_on_the_stored_bytes(self):
        built, _refused, _facts, _summary = self.generate()
        component = self.component(built[0])
        context = checks.QualificationContext.load(ROOT)
        context.duplicates = checks.duplicate_findings([component], context.policy)
        for check in checks.CHECKS:
            if check.check_id in ("sandbox", "mutation"):
                continue
            result = check.run(component, context)
            self.assertEqual(result.status, checks.PASSED, (check.check_id, result.findings))

    def test_a_template_states_its_asset_role_where_admission_reads_it(self):
        item = self.family / "items" / "square_item" / "item.json"
        value = json.loads(item.read_text())
        value.update({"form": "template", "asset_role": "editable_source"})
        item.write_text(json.dumps(value))
        with redirect_stdout(io.StringIO()):
            verify.main(["--family", "demo_family", "--root", str(self.families), "--output", str(self.evidence)])
        built, _refused, _facts, _summary = self.generate()
        component = self.component(built[0])
        policy = checks.QualificationContext.load(ROOT).policy
        self.assertEqual(checks.declared_asset_role(component, policy), "editable_source")
        self.assertEqual(checks.asset_role_findings(component, policy), [])
        # Known wrong: a template whose card states no role is refused by name before admission writes it.
        card = json.loads(component.text("component.json"))
        card["asset_role"] = None
        silent = SimpleNamespace(line=component.line, form=component.form,
                                 text=lambda path: json.dumps(card) if path == "component.json" else component.text(path))
        self.assertEqual([code for code, _detail in checks.asset_role_findings(silent, policy)], ["asset_role_undeclared"])

    @unittest.skipUnless(HAS_SANDBOX, "bubblewrap and the system interpreter are needed for the sandbox checks")
    def test_sandbox_and_mutation_pass_and_a_permissive_test_is_caught(self):
        built, _refused, _facts, _summary = self.generate()
        component = self.component(built[0])
        context = checks.QualificationContext.load(ROOT, sandbox_settings=SANDBOX, work_root=self.root / "work")
        by_id = {check.check_id: check for check in checks.CHECKS}
        self.assertEqual(by_id["sandbox"].run(component, context).status, checks.PASSED)
        self.assertEqual(by_id["mutation"].run(component, context).status, checks.PASSED)
        # Known wrong: a test module that cannot fail lets a broken module through, so mutation refuses it.
        shared = self.family / "shared" / "test_package.py"
        shared.write_text("import unittest\nimport tally\n\n\nclass PackageTests(unittest.TestCase):\n"
                          "    def test_nothing(self):\n        self.assertTrue(True)\n")
        with redirect_stdout(io.StringIO()):
            verify.main(["--family", "demo_family", "--root", str(self.families), "--output", str(self.evidence)])
        built, _refused, _facts, _summary = self.generate()
        weak = self.component(built[0])
        self.assertEqual(by_id["mutation"].run(weak, context).status, checks.REFUSED)

    def test_missing_stale_and_failed_evidence_are_refused_by_name(self):
        add_item(self.family, "unverified_item", "Unverified item", [2, 2], 4)
        built, refused, _facts, _summary = self.generate()
        self.assertEqual([row["reason"] for row in refused], ["native_evidence_missing"])
        (self.family / "items" / "square_item" / "README.md").write_text("# Square item\n\nChanged after evidence.\n")
        _built, refused, _facts, _summary = self.generate()
        self.assertEqual(sorted(row["reason"] for row in refused), ["native_evidence_missing", "native_evidence_stale"])
        (self.family / "items" / "square_item" / "shape.txt").write_text("circle\n")
        with redirect_stdout(io.StringIO()):
            verify.main(["--family", "demo_family", "--root", str(self.families), "--output", str(self.evidence),
                         "--item", "square_item"])
        _built, refused, _facts, _summary = self.generate()
        self.assertIn("native_check_failed", [row["reason"] for row in refused])


if __name__ == "__main__":
    unittest.main()
