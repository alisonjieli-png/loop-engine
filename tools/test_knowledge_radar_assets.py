"""Checks every knowledge radar asset (decision helpers and tools) the way the package path will read it.

Each asset folder must declare exactly its files, use only the Python standard
library, carry valid self-contained JSON Schema contracts, keep its skill
metadata inside the native profile, link only to files it ships, and pass its
own test with a known-wrong case, with no network. A tool must declare the
network effect; a helper must not.
"""
from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "src", ROOT, ROOT / "tools"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import yaml  # noqa: E402

from knowledge_radar import packages  # noqa: E402

ASSETS = ROOT / "tools/knowledge_radar/assets"
STANDARD = set(getattr(sys, "stdlib_module_names", ())) or {"json", "sys", "re", "argparse", "datetime", "pathlib"}
DYNAMIC = {"eval", "exec", "compile", "__import__", "import_module"}
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")


def asset_folders():
    return sorted(path for path in ASSETS.iterdir() if path.is_dir() and (path / "asset.json").is_file())


class AssetChecks(unittest.TestCase):
    def test_there_are_helpers_and_tools(self):
        kinds = {json.loads((folder / "asset.json").read_text())["kind"] for folder in asset_folders()}
        self.assertEqual(kinds, {"decision_helper", "tool"})

    def test_each_asset_declares_exactly_its_files(self):
        for folder in asset_folders():
            with self.subTest(asset=folder.name):
                declaration, bodies = packages.read_asset(ROOT, folder.name)
                self.assertEqual(bodies["LICENSE"], (ROOT / "LICENSE").read_bytes())
                self.assertIn(declaration["entrypoint"], bodies)
                self.assertIn(declaration["test"], bodies)
                effects = set(declaration["declared_effects"])
                self.assertIn("spawns_process", effects)
                if declaration["kind"] == "tool":
                    self.assertIn("network", effects)
                    self.assertIsNone(declaration["data_file"])
                else:
                    self.assertNotIn("network", effects)
                    self.assertTrue(declaration["data_file"].startswith("references/"))

    def test_known_wrong_an_undeclared_file_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "tools/knowledge_radar/assets/choose_model"
            shutil.copytree(ASSETS / "choose_model", target, ignore=shutil.ignore_patterns("__pycache__"))
            (target / "scripts/extra.py").write_text("print('not declared')\n")
            with self.assertRaises(packages.PackagingError):
                packages.read_asset(root, "choose_model")

    def test_code_uses_only_the_standard_library_and_no_dynamic_execution(self):
        for folder in asset_folders():
            local = {path.stem for path in folder.rglob("*.py")}
            for path in folder.rglob("*.py"):
                if "__pycache__" in path.parts:
                    continue
                with self.subTest(file=str(path.relative_to(ASSETS))):
                    tree = ast.parse(path.read_text(encoding="utf-8"))
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                            for name in names:
                                root_name = name.split(".")[0]
                                self.assertTrue(root_name in STANDARD or root_name in local, name)
                        if isinstance(node, ast.Call):
                            name = node.func.id if isinstance(node.func, ast.Name) else (
                                node.func.attr if isinstance(node.func, ast.Attribute) else "")
                            self.assertNotIn(name, DYNAMIC)

    def test_contracts_are_self_contained_json_schemas(self):
        import jsonschema
        for folder in asset_folders():
            for path in sorted((folder / "contracts").glob("*.json")):
                with self.subTest(file=str(path.relative_to(ASSETS))):
                    schema = json.loads(path.read_text(encoding="utf-8"))
                    self.assertEqual(schema.get("$schema"), "https://json-schema.org/draft/2020-12/schema")
                    jsonschema.Draft202012Validator.check_schema(schema)
                    refs = re.findall(r'"\$ref":\s*"([^"]*)"', path.read_text(encoding="utf-8"))
                    self.assertTrue(all(ref.startswith("#") for ref in refs))

    def test_skill_metadata_and_links_stay_inside_the_package(self):
        for folder in asset_folders():
            declaration = json.loads((folder / "asset.json").read_text())
            shipped = {entry["path"] for entry in declaration["files"]} | ({declaration["data_file"]} if declaration["data_file"] else set())
            text = (folder / "SKILL.md").read_text(encoding="utf-8")
            with self.subTest(asset=folder.name):
                self.assertTrue(text.startswith("---\n"))
                header = yaml.safe_load(text.split("---", 2)[1])
                self.assertLessEqual(set(header), {"name", "description", "license", "compatibility", "metadata"})
                self.assertRegex(header["name"], r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
                self.assertLessEqual(len(header["description"]), 1024)
                for target in LINK.findall(text):
                    if not target.startswith(("https://", "http://", "#", "mailto:")):
                        self.assertIn(target.split("#", 1)[0], shipped, target)

    def test_text_files_hold_no_dashes_or_hidden_characters(self):
        for folder in asset_folders():
            for path in folder.rglob("*"):
                if path.is_file() and path.suffix in (".md", ".py", ".json") and "__pycache__" not in path.parts:
                    text = path.read_text(encoding="utf-8")
                    with self.subTest(file=str(path.relative_to(ASSETS))):
                        self.assertNotIn("—", text)
                        self.assertNotIn("–", text)
                        self.assertNotIn("<!--", text)
                        self.assertFalse(any(ord(character) in (0x200B, 0x200E, 0x200F, 0x202E, 0xFEFF) for character in text))

    def test_each_asset_passes_its_own_test_with_a_known_wrong_case(self):
        for folder in asset_folders():
            declaration = json.loads((folder / "asset.json").read_text())
            with self.subTest(asset=folder.name):
                with tempfile.TemporaryDirectory() as temporary:
                    copy = Path(temporary) / folder.name
                    shutil.copytree(folder, copy, ignore=shutil.ignore_patterns("__pycache__"))
                    result = subprocess.run([sys.executable, "-I", "-B", declaration["test"]], cwd=copy,
                                            capture_output=True, text=True, timeout=120, env={"PATH": "/usr/bin:/bin"})
                self.assertEqual(result.returncode, 0, result.stderr[-500:])
                summary = json.loads([line for line in result.stdout.splitlines() if line.startswith("{")][-1])
                self.assertEqual(summary["failed"], 0)
                self.assertGreaterEqual(summary["known_wrong_rejected"], 1)


if __name__ == "__main__":
    unittest.main()
