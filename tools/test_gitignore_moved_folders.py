"""The two large local folders stay ignored when they are directories and when they are symbolic links.

The checkout holds two large folders that are not Loop Engine source: taedri.dev, a sibling repository kept as
reference material, and task_database, about 276 GB of task material. On September 27, 2026 both were being moved to
another disk and replaced by symbolic links. .gitignore named them /taedri.dev/ and /task_database/; a pattern that
ends in a slash matches only a directory, and git reads a symbolic link as a file, so after the move each link would
be listed as an untracked path by git status, by `git ls-files --others --exclude-standard` (which the checkpoint,
architecture audit and hardcoding audit tools read) and would be committed by `git add -A`. The patterns now match
the name whatever it is. Each rule runs git on a scratch repository that holds a copy of this checkout's .gitignore,
and has a known-wrong control: the directory-only form lists the link.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GITIGNORE = ROOT / ".gitignore"
#: The folders that may be a directory or a symbolic link at the top of the checkout.
MOVED_FOLDERS = ("taedri.dev", "task_database")


def untracked(repository: Path) -> set:
    """The paths git lists as untracked and not ignored, as the repository's tools ask for them."""
    environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(repository),
                   "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "LANG": "C"}
    completed = subprocess.run(["git", "-C", str(repository), "ls-files", "--others", "--exclude-standard"],
                               capture_output=True, text=True, check=True, env=environment, timeout=60)
    return set(completed.stdout.splitlines())


def scratch_repository(folder: Path, ignore_text: str, *, links: bool) -> Path:
    """A git repository with this .gitignore and each moved folder as a directory or as a link to one elsewhere."""
    repository, elsewhere = folder / "checkout", folder / "other-disk"
    repository.mkdir(parents=True)
    environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(folder),
                   "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    subprocess.run(["git", "init", "-q", str(repository)], check=True, env=environment, timeout=60)
    (repository / ".gitignore").write_text(ignore_text, encoding="utf-8")
    for name in MOVED_FOLDERS:
        target = (elsewhere / name) if links else (repository / name)
        (target / "inner").mkdir(parents=True)
        (target / "inner" / "task.json").write_text("{}", encoding="utf-8")
        if links:
            (repository / name).symlink_to(target, target_is_directory=True)
    return repository


class MovedFolderIgnoreTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="gitignore-moved-"))
        self.ignore_text = GITIGNORE.read_text(encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_each_folder_is_ignored_as_a_symbolic_link(self):
        repository = scratch_repository(self.folder, self.ignore_text, links=True)
        self.assertTrue(all((repository / name).is_symlink() for name in MOVED_FOLDERS))
        self.assertEqual(untracked(repository), {".gitignore"})

    def test_each_folder_is_ignored_as_a_directory(self):
        repository = scratch_repository(self.folder, self.ignore_text, links=False)
        self.assertEqual(untracked(repository), {".gitignore"})

    def test_the_patterns_hold_only_the_top_level_names(self):
        repository = scratch_repository(self.folder, self.ignore_text, links=True)
        for relative in ("docs/task_database.md", "src/task_database/reader.py", "notes/taedri.dev"):
            (repository / relative).parent.mkdir(parents=True, exist_ok=True)
            (repository / relative).write_text("x", encoding="utf-8")
        self.assertEqual(untracked(repository), {".gitignore", "docs/task_database.md", "src/task_database/reader.py",
                                                 "notes/taedri.dev"})

    def test_known_wrong_a_directory_only_pattern_lists_the_link(self):
        wrong = self.ignore_text
        for name in MOVED_FOLDERS:
            self.assertIn(f"\n/{name}\n", wrong)
            wrong = wrong.replace(f"\n/{name}\n", f"\n/{name}/\n", 1)
        directories = scratch_repository(self.folder / "directories", wrong, links=False)
        self.assertEqual(untracked(directories), {".gitignore"})
        repository = scratch_repository(self.folder / "links", wrong, links=True)
        self.assertEqual(untracked(repository), {".gitignore", *MOVED_FOLDERS})


if __name__ == "__main__":
    unittest.main()
