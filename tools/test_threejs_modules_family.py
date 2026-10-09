"""The threejs_modules creative family without a browser: every item record reads, every package passes its own
tests on its exact bytes (test_package.py with the system interpreter, the root test_*.mjs files with node --test),
and each package's tests fail once its module's exports are replaced by the throwing mutant qualification builds.

The native verifier (headless Chrome with WebGL 2 and the pinned three.js build) needs a browser and is not run here;
its evidence is checked by tools/creative_originals/check.py where the browser exists. The packages are assembled
with assemble.source_files and a contract card without native evidence, which the tests do not read.

Known-wrong control: a module whose first exported function returns a wrong value fails its own package tests, so
a test suite that accepts everything cannot pass here.
"""
from __future__ import annotations

import concurrent.futures
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tools", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.component_qualification.checks import POLICY_PATH, javascript_mutant  # noqa: E402
from tools.creative_originals import assemble, records  # noqa: E402

FAMILY = "threejs_modules"
FAMILY_DIRECTORY = ROOT / "tools" / "creative_originals" / FAMILY
NODE = assemble.sandbox_node()
WORKERS = 4
#: The first exported function of a module, and the start of its body, for the known-wrong control.
FIRST_FUNCTION = re.compile(r"^(export\s+function\s+\w+\s*\([^)]*\)\s*\{)", re.MULTILINE)


def write_package(target: Path, identity: str) -> dict:
    family = records.read_family(FAMILY_DIRECTORY)
    item = records.read_item(FAMILY_DIRECTORY, identity, family)
    files = assemble.source_files(FAMILY_DIRECTORY, identity, family, item)
    for path, data, _role, _source in files:
        destination = target / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    card = assemble.component_card(family, item, files, None, "test")
    (target / records.COMPONENT_NAME).write_bytes(assemble.json_bytes(card))
    return item


def replacement() -> str:
    return json.loads(Path(POLICY_PATH).read_text(encoding="utf-8"))["mutation"]["javascript_replacement"]


class ThreejsModulesFamilyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(tempfile.mkdtemp(prefix="threejs-modules-"))
        cls.family = records.read_family(FAMILY_DIRECTORY)
        cls.identities = records.item_identities(FAMILY_DIRECTORY)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def test_every_item_record_reads_and_names_its_module(self):
        self.assertGreaterEqual(len(self.identities), 3)
        titles = set()
        for identity in self.identities:
            item = records.read_item(FAMILY_DIRECTORY, identity, self.family)
            contract = item["contract"]
            self.assertEqual(contract["module"], f"{identity}.mjs", identity)
            self.assertEqual(contract["tests"], [f"test_{identity}.mjs"], identity)
            self.assertEqual(contract["demo"], {**contract["demo"], "file": "demo/scene.mjs", "export": "demo"})
            self.assertNotIn(item["title"].lower(), titles)
            titles.add(item["title"].lower())

    @unittest.skipUnless(NODE, "node is not installed where the qualification sandbox looks for it")
    def test_every_package_passes_its_tests_and_fails_on_its_mutant(self):
        text = replacement()

        def run(identity):
            package = self.root / "packages" / identity
            item = write_package(package, identity)
            passed = assemble.run_package_tests(package)
            module = package / item["contract"]["module"]
            mutant, replaced = javascript_mutant(module.read_text(encoding="utf-8"), text)
            module.write_text(mutant, encoding="utf-8")
            broken = assemble.run_package_tests(package)
            return identity, passed, replaced, broken

        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
            for identity, passed, replaced, broken in pool.map(run, self.identities):
                with self.subTest(identity=identity):
                    self.assertEqual(passed["state"], "passed", passed.get("output_tail", "")[-1500:])
                    self.assertGreaterEqual(passed["node_counts"]["pass"], 2)
                    self.assertGreater(replaced, 0)
                    self.assertEqual(broken["state"], "failed", "the tests accept a module whose exports throw")
                    self.assertGreater(broken["node_counts"]["fail"], 0)

    @unittest.skipUnless(NODE, "node is not installed where the qualification sandbox looks for it")
    def test_known_wrong_a_module_returning_a_wrong_value_fails(self):
        package = self.root / "wrong" / "toon_band_material"
        item = write_package(package, "toon_band_material")
        module = package / item["contract"]["module"]
        text = module.read_text(encoding="utf-8")
        wrong, count = FIRST_FUNCTION.subn(r"\1 return 0.123456;", text, count=1)
        self.assertEqual(count, 1)
        module.write_text(wrong, encoding="utf-8")
        result = assemble.run_package_tests(package)
        self.assertEqual(result["state"], "failed")
        self.assertGreater(result["node_counts"]["fail"], 0, "the node tests themselves refuse the wrong value")


if __name__ == "__main__":
    unittest.main()
