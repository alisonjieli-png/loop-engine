"""Package tests for one threejs_modules component (standard library only; nothing here runs JavaScript).

inspect_module.py reads the package as text: file digests and review bounds, the root ES module's exports against
the contract, the standalone rules (no import, network, storage, evaluation, worker, process or page-global API),
the contract uniforms in the GLSL, node test and README coverage of every export, and the demo's export. These tests
require a clean report for this package, and run each check on a known-wrong copy (a renamed export, an extra or
default export, an added import, a network call, an undeclared uniform, an export the tests never name, a removed
README section, a demo without its export, a changed digest, an oversized file) that it must refuse, so a check that
accepts everything fails here. test_contract.mjs and the item's own test_*.mjs run the module with node --test.
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import inspect_module

ROOT = Path(__file__).resolve().parent
CARD = json.loads((ROOT / "component.json").read_text(encoding="utf-8"))
CONTRACT = CARD["contract"]


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.module_text = (ROOT / CONTRACT["module"]).read_text(encoding="utf-8")
        self.demo_text = (ROOT / CONTRACT["demo"]["file"]).read_text(encoding="utf-8")
        self.readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.names = [row["name"] for row in CONTRACT["exports"]]
        self.tests = [path.read_text(encoding="utf-8") for path in inspect_module.item_tests(ROOT)]

    def test_the_package_inspects_clean(self):
        report = inspect_module.inspect_package(ROOT)
        self.assertEqual(report["problems"], {key: [] for key in report["problems"]})
        self.assertTrue(report["passed"])
        self.assertEqual(sorted(report["exports"]), sorted(self.names))

    def test_known_wrong_exports_are_refused(self):
        first = self.names[0]
        renamed = re.sub(rf"^(export\s+(?:async\s+)?(?:function|class|const)\s*\*?\s*){re.escape(first)}\b",
                         rf"\g<1>{first}Renamed", self.module_text, count=1, flags=re.MULTILINE)
        self.assertNotEqual(renamed, self.module_text)
        self.assertNotEqual(inspect_module.export_problems(renamed, CONTRACT), [])
        self.assertNotEqual(inspect_module.export_problems(self.module_text + "\nexport let extra = 1;\n", CONTRACT), [])
        self.assertNotEqual(inspect_module.export_problems(self.module_text + "\nexport default 1;\n", CONTRACT), [])

    def test_known_wrong_dependencies_are_refused(self):
        refused = inspect_module.forbidden_problems
        self.assertIn("imports another module", refused("import * as THREE from 'three';\n" + self.module_text))
        self.assertIn("uses the network", refused(self.module_text + "\nfetch('data.bin');\n"))
        self.assertIn("evaluates code", refused(self.module_text + "\neval('1');\n"))
        self.assertIn("uses browser storage", refused(self.module_text + "\nlocalStorage.x = 1;\n"))
        self.assertIn("touches page globals", refused(self.module_text + "\nwindow.x = 1;\n"))
        self.assertIn("touches a process or host runtime", refused(self.module_text + "\nprocess.exit(1);\n"))

    def test_known_wrong_uniform_is_refused(self):
        wrong = dict(CONTRACT, uniforms=list(CONTRACT.get("uniforms", [])) + [{"name": "uNeverDeclared",
                                                                                "type": "float"}])
        self.assertEqual(inspect_module.uniform_problems(self.module_text, wrong),
                         ["uniform float uNeverDeclared is not declared in the module"])

    def test_known_wrong_coverage_readme_and_demo_are_refused(self):
        first = self.names[0]
        untested = [re.sub(rf"\b{re.escape(first)}\b", "somethingElse", text) for text in self.tests]
        self.assertNotEqual(inspect_module.coverage_problems(untested, CONTRACT["module"], self.names), [])
        self.assertNotEqual(inspect_module.coverage_problems([], CONTRACT["module"], self.names), [])
        damaged = self.readme.replace("## Limits", "## Notes")
        self.assertNotEqual(inspect_module.readme_problems(damaged, CARD["title"], self.names), [])
        self.assertNotEqual(inspect_module.demo_problems(self.demo_text.replace("export function", "function"),
                                                         CONTRACT["demo"]["export"]), [])

    def test_known_wrong_files_are_refused(self):
        changed = json.loads(json.dumps(CARD))
        changed["files"][0]["sha256"] = "0" * 64
        self.assertNotEqual(inspect_module.digest_problems(changed, ROOT), [])
        folder = Path(tempfile.mkdtemp())
        try:
            (folder / "large.bin").write_bytes(b"\0" * (inspect_module.MAXIMUM_FILE_BYTES + 1))
            self.assertNotEqual(inspect_module.bound_problems(folder), [])
        finally:
            shutil.rmtree(folder)

    def test_the_command_line_reports_and_exits(self):
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            status = inspect_module.main([str(ROOT)])
        self.assertEqual(status, 0)
        self.assertTrue(json.loads(printed.getvalue())["passed"])


if __name__ == "__main__":
    unittest.main()
