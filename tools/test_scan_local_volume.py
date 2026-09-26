"""The volume inventory reads only, classes each project by typed provenance signals, and writes outside the repository.

Roadmap step S-6.207. Each rule has a known-wrong case: a project whose git remote names another account, whose
licence names another holder, or whose source carries another copyright line is third-party material; a vendored
folder is skipped by name; an output inside this repository is refused; and no file is read beyond its first bytes.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "src")]

import scan_local_volume as scanner  # noqa: E402

MIT = "MIT License\n\nCopyright (c) 2026 Somebody Else\n\nPermission is hereby granted.\n"


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def fixture_volume(root: Path) -> None:
    """Five projects: the owner's, one cloned from another account, one under another holder's licence, one with
    another author's copyright line, and one that only vendored dependencies would make look large."""
    _write(root, "PROJECTS/resizer/README.md", "# Resizer\n\nResize every image in a folder.\n")
    _write(root, "PROJECTS/resizer/main.py", "\"\"\"Resize images.\"\"\"\nimport sys\n\ndef resize(path, width):\n    return path\n")
    _write(root, "PROJECTS/resizer/requirements.txt", "pillow>=10\n")
    _write(root, "PROJECTS/cloned/README.md", "# Cloned\n")
    _write(root, "PROJECTS/cloned/app.py", "print('x')\n")
    _write(root, "PROJECTS/cloned/.git/config", "[remote \"origin\"]\n\turl = https://github.com/someone-else/cloned.git\n")
    _write(root, "PROJECTS/licensed/README.md", "# Licensed\n")
    _write(root, "PROJECTS/licensed/LICENSE", MIT)
    _write(root, "PROJECTS/licensed/tool.py", "print('y')\n")
    _write(root, "PROJECTS/copied/README.md", "# Copied\n")
    _write(root, "PROJECTS/copied/lib.py", "# Copyright (c) 2021 Another Author\nprint('z')\n")
    _write(root, "PROJECTS/own-remote/README.md", "# Own remote\n")
    _write(root, "PROJECTS/own-remote/run.py", "print('w')\n")
    _write(root, "PROJECTS/own-remote/.git/config", "[remote \"origin\"]\n\turl = git@github.com:owner-account/own-remote.git\n")
    _write(root, "PROJECTS/resizer/node_modules/left-pad/index.js", "module.exports = 1;\n")
    _write(root, "PROJECTS/resizer/__pycache__/main.cpython-314.pyc", "binary")
    _write(root, "$RECYCLE.BIN/old.py", "print('gone')\n")


class InventoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.volume = self.root / "volume"
        fixture_volume(self.volume)
        self.output = self.root / "inventory"
        code = scanner.main(["--volume", str(self.volume), "--output", str(self.output),
                             "--owner-account", "owner-account", "--owner-name", "amarel"])
        self.assertEqual(code, 0)
        self.summary = json.loads((self.output / "summary.json").read_text())
        self.projects = {row["path"]: row for row in map(json.loads, (self.output / "projects.jsonl").read_text().splitlines())}

    def test_every_project_is_classed_by_its_typed_signals(self):
        classes = {path.split("/")[-1]: row["provenance_class"] for path, row in self.projects.items()}
        self.assertEqual(classes, {"resizer": scanner.OWNER_DECLARED, "cloned": scanner.THIRD_PARTY_REMOTE,
                                   "licensed": scanner.THIRD_PARTY_LICENCE, "copied": scanner.THIRD_PARTY_COPYRIGHT,
                                   "own-remote": scanner.OWNER_REMOTE})
        self.assertEqual(self.projects["PROJECTS/cloned"]["remote_owners"], ["someone-else"])
        self.assertEqual(self.projects["PROJECTS/licensed"]["licence_holders"], ["Somebody Else"])
        self.assertEqual(self.projects["PROJECTS/copied"]["copyright_holders"], ["Another Author"])
        self.assertEqual(self.summary["projects_by_provenance_class"][scanner.OWNER_DECLARED], 1)
        self.assertIn("declared on September 26, 2026", self.summary["provenance_basis"])

    def test_vendored_and_system_folders_are_skipped_and_nothing_is_copied_or_hashed(self):
        files = [json.loads(line) for path in sorted(self.output.glob("files-*.jsonl"))
                 for line in path.read_text().splitlines()]
        paths = {row["path"] for row in files}
        self.assertNotIn("PROJECTS/resizer/node_modules/left-pad/index.js", paths)
        self.assertNotIn("PROJECTS/resizer/__pycache__/main.cpython-314.pyc", paths)
        self.assertNotIn("$RECYCLE.BIN/old.py", paths)
        self.assertIn("PROJECTS/resizer/main.py", paths)
        self.assertEqual(self.summary["skipped_folders"]["node_modules"], 1)
        self.assertEqual(set(files[0]), {"record_type", "path", "size_bytes", "extension", "language", "modified_at"})
        self.assertFalse(any("sha256" in row or "digest" in row for row in files))
        self.assertEqual(self.projects["PROJECTS/resizer"]["languages"], {"markdown": 1, "python": 1, "text": 1})
        self.assertEqual(self.projects["PROJECTS/resizer"]["source_files"], 1, "prose and data are not code")
        self.assertEqual(set(os.listdir(self.output)), {"files-001.jsonl", "projects.jsonl", "summary.json", "progress.json"})

    def test_known_wrong_an_output_inside_the_repository_is_refused(self):
        target = HERE.parent / "inventory-here"
        code = scanner.main(["--volume", str(self.volume), "--output", str(target)])
        self.assertEqual(code, 2)
        self.assertFalse(target.exists())
        self.assertEqual(scanner.main(["--volume", str(self.root / "missing"), "--output", str(self.root / "x")]), 2)

    def test_known_wrong_without_the_remote_rule_a_clone_would_pass_as_the_owners(self):
        project = dict(self.projects["PROJECTS/cloned"])
        self.assertEqual(scanner._classify(project, {"owner-account"}, {"amarel"}), scanner.THIRD_PARTY_REMOTE)
        self.assertEqual(scanner._classify({**project, "remote_owners": []}, {"owner-account"}, {"amarel"}),
                         scanner.OWNER_DECLARED)
        own = dict(self.projects["PROJECTS/own-remote"])
        self.assertEqual(scanner._classify(own, {"owner-account"}, {"amarel"}), scanner.OWNER_REMOTE)
        self.assertEqual(scanner._classify(own, set(), {"amarel"}), scanner.THIRD_PARTY_REMOTE)

    def test_a_copyright_line_naming_the_owner_keeps_the_owners_class(self):
        project = {**self.projects["PROJECTS/copied"], "copyright_holders": ["Taylor Amarel"], "licence_holders": []}
        self.assertEqual(scanner._classify(project, set(), {"amarel"}), scanner.OWNER_DECLARED)


if __name__ == "__main__":
    unittest.main()
