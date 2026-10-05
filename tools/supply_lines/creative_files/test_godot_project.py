"""Offline tests of this editable Godot project: it parses, and every resource it references is present or pinned.

project/ holds the project's text files byte for byte and creative.json pins its media files. Known wrong: a copy
of the project with a referenced file removed, with a reference to a file that does not exist, and with a
project.godot that does not parse must each be reported. When Godot 4 is installed and the media files have been
fetched (python creative_fetch.py fetch project-media .), Godot itself imports the project headless.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import godot_project_check as check  # noqa: E402

MANIFEST = json.loads((HERE / "creative.json").read_text(encoding="utf-8"))
PROJECT = HERE / "project"


def _media_fetched() -> bool:
    for variant in MANIFEST["variants"]:
        for item in variant["files"]:
            path = HERE.joinpath(*item["path"].split("/"))
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                return False
    return True


class GodotProjectTest(unittest.TestCase):
    def test_the_project_parses_and_every_reference_is_present_or_pinned(self):
        self.assertEqual(check.problems(PROJECT, MANIFEST), [])

    def test_the_manifest_names_the_main_scene_and_the_scripts_that_exist(self):
        project = MANIFEST["asset"]["project"]
        config = check.read_config((PROJECT / "project.godot").read_text(encoding="utf-8"))
        self.assertEqual(project["main_scene"], check.main_scene(config))
        for path in project["scripts"]:
            self.assertTrue((PROJECT / path).is_file(), path)
        if project.get("main_scene_path"):
            self.assertTrue((PROJECT / project["main_scene_path"]).is_file()
                            or project["main_scene_path"] in check.pinned_paths(MANIFEST))

    def test_known_wrong_a_removed_or_invented_reference_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "project"
            shutil.copytree(PROJECT, copy)
            (copy / "baltor_check_known_wrong.tscn").write_text(
                '[gd_scene format=3]\n\n[ext_resource type="Texture2D" path="res://no/such/file.png" id="1"]\n',
                encoding="utf-8")
            found = check.problems(copy, MANIFEST)
            self.assertTrue(any("res://no/such/file.png" in problem for problem in found), found)
            present = sorted(path for path in check.references(PROJECT) if (PROJECT / path).is_file())
            if present:
                (copy / present[0]).unlink()
                self.assertTrue(any(f"res://{present[0]}" in problem for problem in check.problems(copy, MANIFEST)))

    def test_known_wrong_a_project_file_that_does_not_parse_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "project"
            shutil.copytree(PROJECT, copy)
            (copy / "project.godot").write_text("config_version=5\nthis line is not a key\n", encoding="utf-8")
            self.assertTrue(check.problems(copy, MANIFEST))
            (copy / "project.godot").unlink()
            self.assertEqual(check.problems(copy, MANIFEST), ["project.godot is missing"])

    @unittest.skipUnless((shutil.which("godot") or shutil.which("godot4")) and _media_fetched(),
                         "Godot 4 is not installed, or the media files are not fetched")
    def test_godot_imports_the_project_headless(self):
        godot = shutil.which("godot") or shutil.which("godot4")
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "project"
            shutil.copytree(PROJECT, copy)
            done = subprocess.run([godot, "--headless", "--path", str(copy), "--import"], capture_output=True,
                                  text=True, timeout=600, check=False)
        self.assertEqual(done.returncode, 0, done.stderr[-800:])
        self.assertNotIn("SCRIPT ERROR", done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
