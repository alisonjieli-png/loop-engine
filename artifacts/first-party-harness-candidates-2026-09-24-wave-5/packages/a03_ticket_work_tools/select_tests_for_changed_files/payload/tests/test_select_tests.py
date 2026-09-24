"""Tests for scripts/select_tests.py. Effects: writes a synthetic repository inside tempfile.TemporaryDirectory() and starts the script as a subprocess; writes nothing else.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent.parent
SCRIPT = PAYLOAD / "scripts" / "select_tests.py"
EXAMPLE = PAYLOAD / "examples" / "selection-output.json"

FILES = {
    "pyproject.toml": "[project]\nname = 'shop'\n",
    "README.md": "# Shop\n",
    "src/shop/__init__.py": "",
    "src/shop/prices.py": "def parse_price(text):\n    return int(text)\n",
    "src/shop/checkout.py": "from shop.prices import parse_price\n",
    "src/shop/report.py": "from . import formatting\n",
    "src/shop/formatting.py": "WIDTH = 10\n",
    "src/shop/plugins.py": "import importlib\n\n\ndef load(name):\n    return importlib.import_module(name)\n",
    "src/shop/fixtures_data.py": "ROWS = []\n",
    "tests/conftest.py": "import shop.fixtures_data\n",
    "tests/helpers.py": "def make_cart():\n    return []\n",
    "tests/test_prices.py": "from shop.prices import parse_price\n",
    "tests/test_checkout.py": "from shop import checkout\n",
    "tests/test_report.py": "import shop.report\n",
    "tests/test_uses_helper.py": "from helpers import make_cart\n",
    "tests/test_legacy.py": "from shop.legacy_rates import RATE\n",
    "tests/unit/test_cli.py": "SCRIPT = 'scripts/tool.py'\n",
    "tests/test_rules.py": "RULES = 'data/rules.json'\n",
    "scripts/tool.py": "print('tool')\n",
    "data/rules.json": "{}\n",
}

DIFF = """diff --git a/src/shop/legacy_rates.py b/src/shop/legacy_rates.py
deleted file mode 100644
index 1111111..0000000
--- a/src/shop/legacy_rates.py
+++ /dev/null
@@ -1 +0,0 @@
-RATE = 1
diff --git a/src/shop/formatting.py b/src/shop/format_rules.py
similarity index 90%
rename from src/shop/formatting.py
rename to src/shop/format_rules.py
diff --git a/src/shop/prices.py b/src/shop/prices.py
index 2222222..3333333 100644
--- a/src/shop/prices.py
+++ b/src/shop/prices.py
@@ -1,3 +1,3 @@
--- a removed line that starts with two dashes
+++ an added line that starts with two plus signs
 def parse_price(text):
"""


class SelectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for relative, text in FILES.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def run_script(self, *arguments, data=None):
        done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--root", str(self.root), *arguments],
                              input=data, capture_output=True, text=True, timeout=60)
        return done.returncode, json.loads(done.stdout)

    def test_direct_and_indirect_importers_match_the_example(self):
        code, result = self.run_script("--changed", "src/shop/prices.py")
        self.assertEqual((code, result["status"]), (0, "selected"))
        self.assertEqual(result["test_paths"], ["tests/test_checkout.py", "tests/test_prices.py"])
        expected = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        self.assertEqual(result, expected)

    def test_known_wrong_name_matching_misses_the_indirect_test(self):
        code, result = self.run_script("--changed", "src/shop/prices.py")
        by_name_only = [path for path in result["test_paths"] if "prices" in path]
        self.assertEqual(by_name_only, ["tests/test_prices.py"])
        checkout = next(item for item in result["selected_tests"] if item["path"] == "tests/test_checkout.py")
        self.assertEqual(checkout["reasons"][0]["via"],
                         ["tests/test_checkout.py", "src/shop/checkout.py", "src/shop/prices.py"])

    def test_relative_import_conftest_and_helper_module(self):
        code, result = self.run_script("--changed", "src/shop/formatting.py")
        self.assertEqual(result["test_paths"], ["tests/test_report.py"])
        code, result = self.run_script("--changed", "src/shop/fixtures_data.py")
        self.assertEqual(len(result["test_paths"]), 7)
        code, result = self.run_script("--changed", "tests/helpers.py")
        self.assertEqual(result["test_paths"], ["tests/test_uses_helper.py"])

    def test_package_init_reaches_every_importer(self):
        code, result = self.run_script("--changed", "src/shop/__init__.py")
        self.assertEqual(code, 0)
        self.assertIn("tests/test_prices.py", result["test_paths"])
        self.assertIn("tests/test_report.py", result["test_paths"])

    def test_script_and_data_files_are_matched_by_name_in_test_text(self):
        code, result = self.run_script("--changed", "scripts/tool.py", "data/rules.json")
        self.assertEqual((code, result["test_paths"]), (0, ["tests/test_rules.py", "tests/unit/test_cli.py"]))
        bases = {reason["basis"] for item in result["selected_tests"] for reason in item["reasons"]}
        self.assertEqual(bases, {"file name in test text"})

    def test_diff_with_delete_rename_and_look_alike_hunk_lines(self):
        (self.root / "src/shop/format_rules.py").write_text("WIDTH = 10\n", encoding="utf-8")
        (self.root / "src/shop/formatting.py").unlink()
        code, result = self.run_script("--diff", "-", data=DIFF)
        changes = {item["path"]: item["change"] for item in result["changed"]}
        self.assertEqual(changes, {"src/shop/format_rules.py": "renamed", "src/shop/formatting.py": "renamed",
                                   "src/shop/legacy_rates.py": "deleted", "src/shop/prices.py": "modified"})
        for path in ("tests/test_legacy.py", "tests/test_report.py", "tests/test_prices.py"):
            self.assertIn(path, result["test_paths"])
        self.assertEqual([item["path"] for item in result["untested_changes"]], ["src/shop/format_rules.py"])
        self.assertEqual((code, result["status"]), (0, "selected"))

    def test_diff_combined_with_a_new_untracked_file(self):
        (self.root / "tests/test_totals.py").write_text("from shop.formatting import WIDTH\n", encoding="utf-8")
        diff = DIFF.split("diff --git a/src/shop/prices.py")[0]
        code, result = self.run_script("--diff", "-", "--changed", "tests/test_totals.py", data=diff)
        self.assertIn("tests/test_totals.py", result["test_paths"])
        self.assertEqual(result["changed"][-1], {"path": "tests/test_totals.py", "change": "modified",
                                                 "kind": "python", "tests": 1})

    def test_name_status_list(self):
        code, result = self.run_script("--changed-from", "-", data="M\tsrc/shop/prices.py\nD\tsrc/shop/legacy_rates.py\n")
        self.assertEqual(code, 0)
        self.assertIn("tests/test_legacy.py", result["test_paths"])

    def test_documentation_only_needs_no_tests(self):
        code, result = self.run_script("--changed", "README.md")
        self.assertEqual((code, result["status"], result["test_paths"]), (0, "no_code_changed", []))

    def test_untraced_changes_recommend_the_full_suite(self):
        for changed in ("pyproject.toml", "nope/missing.py"):
            with self.subTest(changed=changed):
                code, result = self.run_script("--changed", changed)
                self.assertEqual((code, result["status"]), (1, "full_suite_recommended"))

    def test_known_wrong_project_configuration_is_not_narrowed_to_one_test(self):
        (self.root / "tests/test_packaging.py").write_text("PYPROJECT = 'pyproject.toml'\n", encoding="utf-8")
        code, result = self.run_script("--changed", "pyproject.toml", "requirements-dev.txt")
        self.assertEqual((code, result["status"]), (1, "full_suite_recommended"))
        self.assertEqual({item["path"]: item["kind"] for item in result["changed"]},
                         {"pyproject.toml": "project_config", "requirements-dev.txt": "project_config"})
        self.assertEqual(result["test_paths"], [])
        code, result = self.run_script("--changed", "src/shop/plugins.py")
        self.assertEqual((code, result["status"]), (1, "none_selected"))
        self.assertEqual(result["dynamic_import_files"], ["src/shop/plugins.py"])

    def test_unparsed_file_forces_the_full_suite_unless_allowed(self):
        (self.root / "tests/test_broken.py").write_text("def broken(:\n", encoding="utf-8")
        code, result = self.run_script("--changed", "src/shop/prices.py")
        self.assertEqual((code, result["status"]), (1, "full_suite_recommended"))
        self.assertEqual(result["unreadable_files"][0]["path"], "tests/test_broken.py")
        code, result = self.run_script("--changed", "src/shop/prices.py", "--allow-unparsed")
        self.assertEqual((code, result["status"]), (0, "selected"))

    def test_refused_inputs(self):
        for arguments in (["--changed", "../outside.py"], ["--changed", "/srv/other/file.py"],
                          ["--diff", "../changes.diff"], ["--diff", "-", "--changed-from", "-"], []):
            with self.subTest(arguments=arguments):
                code, result = self.run_script(*arguments)
                self.assertEqual((code, result["status"]), (2, "refused"))

    def test_skill_file_names_this_script(self):
        text = (PAYLOAD / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("scripts/select_tests.py", text)
        self.assertIn("examples/selection-output.json", text)


if __name__ == "__main__":
    unittest.main()
