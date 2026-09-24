"""Tests for scripts/map_layout.py. Effects: writes synthetic folder trees inside tempfile.TemporaryDirectory() and starts the script as a subprocess; writes nothing else.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent.parent
SCRIPT = PAYLOAD / "scripts" / "map_layout.py"
EXAMPLE = PAYLOAD / "examples" / "layout-output.json"

TREE = ["README.md", "pyproject.toml", "Makefile", ".env", ".gitignore", "package-lock.json",
        "src/shop/__init__.py", "src/shop/prices.py", "src/shop/export.py", "src/shop/io/reader.py",
        "src/shop/io/writer.py", "src/shop/data/__init__.py", "src/shop/data/loader.py", "src/shop/proto/msg_pb2.py",
        "tests/test_prices.py", "tests/conftest.py", "tests/fixtures/sample.json", "docs/index.md", "docs/guide.md",
        ".github/workflows/ci.yml", "build/lib/shop/prices.py", "build/lib/shop/export.py", "node_modules/pkg/index.js",
        ".venv/pyvenv.cfg", ".venv/lib/x.py", "env2/pyvenv.cfg", "env2/lib/y.py", "data/sample.csv",
        "data/big.parquet", "assets/logo.png", ".git/HEAD", "config/app.yaml", "certs/server.pem",
        "src/shop/__pycache__/prices.cpython-312.pyc", "tests/__pycache__/conftest.cpython-312.pyc"]

PATH_LIST = ["README.md", "pyproject.toml", "app/__init__.py", "app/api/routes.py", "app/api/schemas.py",
             "app/core/settings.py", "app/core/security.py", "tests/test_routes.py", "tests/test_security.py",
             "docs/setup.md", "dist/app-0.1.0.tar.gz", "node_modules/left-pad/index.js", "scripts/seed.sh"]


def make_tree(root: Path, paths) -> None:
    for relative in paths:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")


class MapLayout(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "repo"
        make_tree(self.root, TREE)
        (self.base / "outside").mkdir()
        (self.base / "outside" / "secret_notes.py").write_text("x\n", encoding="utf-8")
        os.symlink(self.base / "outside", self.root / "src" / "linked")

    def tearDown(self):
        self.temp.cleanup()

    def run_raw(self, *arguments, data=None):
        done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments], input=data,
                              capture_output=True, text=True, timeout=60)
        return done.returncode, json.loads(done.stdout), done.stdout

    def run_script(self, *arguments, data=None):
        code, result, _text = self.run_raw(*arguments, data=data)
        return code, result

    def records(self, result):
        return {item["path"]: item for item in result["folders"]}

    def test_marks_categories_and_skips_dependency_folders(self):
        code, result = self.run_script("--root", str(self.root), "--folder-records")
        self.assertEqual((code, result["status"]), (0, "ok"))
        records = self.records(result)
        self.assertEqual(records["src"]["category"], "source")
        self.assertEqual(records["src/shop/data"]["category"], "source")
        self.assertEqual(records["tests"]["category"], "test")
        self.assertEqual(records["docs"]["category"], "docs")
        self.assertEqual(records["data"]["category"], "data")
        self.assertEqual(records[".github"]["category"], "config")
        skipped = {item["name"]: item for item in result["skipped"]}
        self.assertEqual(sorted(skipped), [".git", ".venv", "__pycache__", "env2", "node_modules"])
        self.assertEqual(skipped["__pycache__"]["places"], 2)
        self.assertEqual(result["totals"]["files"], 27)
        self.assertEqual(result["sensitive_files"], {"count": 2, "paths": [".env", "certs/server.pem"]})
        self.assertEqual(result["key_files"]["readme"], ["README.md"])
        self.assertIn("pyproject.toml", result["key_files"]["build_and_config"])
        self.assertEqual(result["key_files"]["ci"], [".github/workflows/"])
        self.assertEqual(result["largest_source_folders"][0], {"path": "src/shop", "source_files": 7})
        self.assertEqual(result["test_file_folders"], [{"path": "tests", "test_files_here": 2},
                                                       {"path": "tests/fixtures", "test_files_here": 1}])
        self.assertTrue(result["tree"][0].startswith("./ [source] 27 files"))

    def test_known_wrong_generated_copy_is_not_offered_as_source(self):
        code, result = self.run_script("--root", str(self.root), "--folder-records")
        self.assertEqual(code, 0)
        records = self.records(result)
        self.assertEqual(records["build"]["category"], "generated")
        self.assertEqual(records["build/lib"]["category"], "generated")
        self.assertFalse(any(item["path"].startswith("build") for item in result["largest_source_folders"]))
        build_line = next(line for line in result["tree"] if line.strip().startswith("build/"))
        self.assertIn("not expanded", build_line)
        self.assertFalse(any(line.strip().startswith("lib/") for line in result["tree"]))

    def test_code_folders_open_before_bigger_data_folders(self):
        runs = [f"artifacts/run_{index:02d}/{name}" for index in range(20) for name in ("a.json", "b.json", "notes.md")]
        make_tree(self.base / "mixed", runs + ["src/app/core/engine.py", "src/app/core/rules.py",
                                               "src/app/api/routes.py", "tests/test_engine.py"])
        code, result = self.run_script("--root", str(self.base / "mixed"), "--max-lines", "8")
        self.assertEqual(code, 0)
        stripped = [line.strip() for line in result["tree"]]
        self.assertTrue(any(line.startswith("app/ [source]") for line in stripped))
        self.assertTrue(any(line.startswith("core/ [source]") for line in stripped))
        self.assertFalse(any(line.startswith("run_") for line in stripped))
        self.assertTrue(any(line.startswith("... 20 more folders here") for line in stripped))

    def test_hidden_folder_lines_name_the_exact_focus_value(self):
        wide = self.base / "wide"
        make_tree(wide, [f"src/pkg/part_{index:02d}/code.py" for index in range(30)])
        pattern = r"^\.\.\. \d+ more folders here; use --focus src/pkg to open them$"
        for arguments in ((), ("--focus", "src")):
            with self.subTest(arguments=arguments):
                code, result = self.run_script("--root", str(wide), "--max-lines", "6", *arguments)
                self.assertEqual(code, 0)
                self.assertTrue(any(re.match(pattern, line.strip()) for line in result["tree"]), result["tree"])
        make_tree(self.base / "flat", [f"area_{index:02d}/code.py" for index in range(12)])
        code, result = self.run_script("--root", str(self.base / "flat"), "--max-lines", "5")
        self.assertTrue(any(re.match(r"^\.\.\. \d+ more folders here; raise --max-lines to list them$", line.strip())
                            for line in result["tree"]), result["tree"])

    def test_default_output_is_short_and_folder_records_are_opt_in(self):
        make_tree(self.root, [f"src/pkg/module_{index:03d}/code.py" for index in range(200)])
        code, result, text = self.run_raw("--root", str(self.root))
        self.assertEqual(code, 0)
        self.assertNotIn("folders", result)
        self.assertLessEqual(len(text.splitlines()), 110)
        code, result = self.run_script("--root", str(self.root), "--folder-records")
        self.assertIn("src/pkg/module_199", self.records(result))

    def test_test_files_are_found_where_they_sit(self):
        make_tree(self.base / "tooling", ["tools/build_index.py", "tools/sync.py", "tools/export.py",
                                          "tools/test_build_index.py", "tools/test_sync.py", "src/lib/core.py"])
        code, result = self.run_script("--root", str(self.base / "tooling"))
        self.assertEqual(code, 0)
        self.assertEqual(result["test_file_folders"], [{"path": "tools", "test_files_here": 2}])

    def test_line_budget_keeps_totals_exact(self):
        make_tree(self.root, [f"src/pkg/module_{index:02d}/code.py" for index in range(30)])
        code, result = self.run_script("--root", str(self.root), "--max-lines", "10")
        self.assertEqual(code, 0)
        self.assertLessEqual(len(result["tree"]), 10)
        self.assertGreater(result["omitted_tree_folders"], 0)
        self.assertEqual(result["totals"]["files"], 57)

    def test_focus_maps_one_folder_and_refuses_escapes(self):
        code, result = self.run_script("--root", str(self.root), "--focus", "src", "--folder-records")
        self.assertEqual(code, 0)
        self.assertTrue(result["tree"][0].startswith("src/ [source]"))
        self.assertIn("src/shop/io", self.records(result))
        for focus in ("../outside", "src/linked", "/etc", "missing"):
            with self.subTest(focus=focus):
                code, result = self.run_script("--root", str(self.root), "--focus", focus)
                self.assertEqual((code, result["status"]), (2, "refused"))

    def test_symbolic_links_are_counted_and_not_followed(self):
        code, result = self.run_script("--root", str(self.root))
        self.assertEqual(result["totals"]["links"], 1)
        self.assertNotIn("secret_notes", json.dumps(result))

    def test_path_list_matches_the_example_output(self):
        code, result = self.run_script("--root", str(self.base), "--paths-from", "-", data="\n".join(PATH_LIST) + "\n")
        self.assertEqual(code, 0)
        result["root"] = "."
        expected = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        self.assertEqual(result, expected)

    def test_path_list_forms_and_refusals(self):
        code, result = self.run_script("--paths-from", "-", data="\x00".join(PATH_LIST))
        self.assertEqual((code, result["totals"]["files"]), (0, 12))
        for bad in ("../outside/notes.txt\n", "/abs/file.py\n", '"quoted name.py"\n', "a/./b.py\n"):
            with self.subTest(bad=bad):
                code, result = self.run_script("--paths-from", "-", data=bad)
                self.assertEqual((code, result["status"]), (2, "refused"))

    def test_folder_without_code_is_reported(self):
        docs_only = self.base / "notes"
        make_tree(docs_only, ["a.md", "b/c.md"])
        code, result = self.run_script("--root", str(docs_only))
        self.assertEqual((code, result["status"]), (1, "no_source_found"))

    def test_entry_bound_refuses_instead_of_cutting(self):
        code, result = self.run_script("--root", str(self.root), "--max-entries", "3")
        self.assertEqual((code, result["status"]), (2, "refused"))

    def test_skill_file_names_this_script(self):
        text = (PAYLOAD / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("scripts/map_layout.py", text)
        self.assertIn("examples/layout-output.json", text)


if __name__ == "__main__":
    unittest.main()
