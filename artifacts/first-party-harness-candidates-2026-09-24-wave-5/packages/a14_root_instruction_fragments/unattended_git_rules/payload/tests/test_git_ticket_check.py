"""Tests for scripts/git_ticket_check.py. Effects: creates git repositories only inside temporary folders and starts git and the script as local processes; no network."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
SCRIPT = PACKAGE / "scripts" / "git_ticket_check.py"
GIT = shutil.which("git")


@unittest.skipIf(GIT is None, "git is not installed")
class GitTicketCheck(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        base = Path(self.folder.name)
        (base / "home").mkdir()
        (base / "gitconfig").write_text("", encoding="utf-8")
        self.environment = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(base / "home"), "LC_ALL": "C",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": str(base / "gitconfig"),
            "GIT_AUTHOR_NAME": "Night Runner", "GIT_AUTHOR_EMAIL": "runner@example.invalid",
            "GIT_COMMITTER_NAME": "Night Runner", "GIT_COMMITTER_EMAIL": "runner@example.invalid",
        }
        self.root = base / "work"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("symbolic-ref", "HEAD", "refs/heads/main")
        self.write("src/parse.py", "def parse(text):\n    return text\n")
        self.write("AGENTS.md", "# Project rules\n")
        self.git("add", "src/parse.py", "AGENTS.md")
        self.git("commit", "-q", "-m", "Initial layout")
        self.write(".baltor/unattended-git-rules/LICENSE", "placed by the host\n")

    def tearDown(self):
        self.folder.cleanup()

    def git(self, *arguments):
        return subprocess.run([GIT, "-c", "commit.gpgsign=false", *arguments], cwd=self.root, env=self.environment,
                              capture_output=True, text=True, timeout=60, check=True).stdout.strip()

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def check(self, *arguments):
        finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments], cwd=self.root,
                                  env=self.environment, capture_output=True, text=True, timeout=120)
        return finished.returncode, json.loads(finished.stdout)

    def codes(self, answer):
        return {violation["code"] for violation in answer.get("violations", [])}

    def fix_and_commit(self, message="ABC-7: Keep surrounding spaces out of parsed text"):
        self.write("src/parse.py", "def parse(text):\n    return text.strip()\n")
        self.git("add", "--", "src/parse.py")
        self.git("commit", "-q", "-m", message)

    def test_one_clean_ticket_commit_passes(self):
        status, answer = self.check("begin", "--ticket", "ABC-7")
        self.assertEqual((status, answer["result"]), (0, "begun"))
        self.write("src/parse.py", "def parse(text):\n    return text.strip()\n")
        self.git("add", "--", "src/parse.py")
        status, answer = self.check("verify", "--ticket", "ABC-7")
        self.assertEqual((status, answer["result"], answer["staged"]), (0, "pass", ["src/parse.py"]))
        self.assertIn("commit once", answer["next"])
        self.assertIn("verify --ticket ABC-7 --require-commit", answer["next"])
        self.git("commit", "-q", "-m", "ABC-7: Keep surrounding spaces out of parsed text")
        status, answer = self.check("verify", "--ticket", "ABC-7", "--require-commit")
        self.assertEqual((status, answer["result"], answer["commits_since_base"]), (0, "pass", 1), answer)
        self.assertEqual(answer["commit_paths"], ["src/parse.py"])

    def test_unstaging_a_file_staged_by_mistake_is_allowed(self):
        self.check("begin", "--ticket", "ABC-7")
        self.write("src/parse.py", "def parse(text):\n    return text.strip()\n")
        self.write("scratch.txt", "notes\n")
        self.git("add", "--", "src/parse.py", "scratch.txt")
        self.git("restore", "--staged", "--", "scratch.txt")
        self.git("commit", "-q", "-m", "ABC-7: Keep surrounding spaces out of parsed text")
        status, answer = self.check("verify", "--ticket", "ABC-7", "--require-commit")
        self.assertEqual((status, answer["result"]), (0, "pass"), answer)
        self.assertEqual(answer["new_untracked_files"], ["scratch.txt"])

    def test_amended_commit_is_refused(self):
        """Known-wrong case: the ticket commit is rewritten with --amend."""
        self.check("begin", "--ticket", "ABC-7")
        self.fix_and_commit()
        self.git("commit", "-q", "--amend", "-m", "ABC-7: Reworded")
        status, answer = self.check("verify", "--ticket", "ABC-7", "--require-commit")
        self.assertEqual((status, answer["result"]), (1, "fail"))
        self.assertIn("head_moved_by_other_command", self.codes(answer))
        self.assertIn("Do not try to repair the history", answer["next"])

    def test_second_commit_is_refused(self):
        self.check("begin", "--ticket", "ABC-7")
        self.fix_and_commit()
        self.write("src/parse.py", "def parse(text):\n    return text.strip().lower()\n")
        self.git("commit", "-q", "-am", "ABC-7: More")
        status, answer = self.check("verify", "--ticket", "ABC-7")
        self.assertIn("too_many_commits", self.codes(answer))

    def test_commit_without_ticket_key_is_refused(self):
        self.check("begin", "--ticket", "ABC-7")
        self.fix_and_commit("Keep surrounding spaces out of parsed text")
        status, answer = self.check("verify", "--ticket", "ABC-7")
        self.assertEqual(status, 1)
        self.assertIn("commit_missing_ticket_key", self.codes(answer))

    def test_similar_ticket_key_does_not_count(self):
        self.check("begin", "--ticket", "ABC-7")
        self.fix_and_commit("ABC-71: Another ticket")
        status, answer = self.check("verify", "--ticket", "ABC-7")
        self.assertIn("commit_missing_ticket_key", self.codes(answer))

    def test_longer_dotted_key_does_not_count(self):
        """Known-wrong case: the message names ABC-7.2, a different ticket whose key starts with ABC-7."""
        self.check("begin", "--ticket", "ABC-7")
        self.fix_and_commit("ABC-7.2: Another ticket")
        status, answer = self.check("verify", "--ticket", "ABC-7")
        self.assertIn("commit_missing_ticket_key", self.codes(answer))

    def test_key_before_a_final_full_stop_counts(self):
        self.check("begin", "--ticket", "ABC-7")
        self.fix_and_commit("Keep surrounding spaces out of parsed text for ABC-7.")
        status, answer = self.check("verify", "--ticket", "ABC-7", "--require-commit")
        self.assertEqual((status, answer["result"]), (0, "pass"), answer)

    def test_reset_to_older_history_is_refused(self):
        self.write("README.md", "notes\n")
        self.git("add", "README.md")
        self.git("commit", "-q", "-m", "Add notes")
        self.check("begin", "--ticket", "ABC-7")
        self.git("reset", "-q", "--hard", "HEAD~1")
        status, answer = self.check("verify", "--ticket", "ABC-7")
        self.assertEqual(status, 1)
        self.assertIn("history_rewritten", self.codes(answer))

    def test_moved_remote_tracking_reference_is_refused(self):
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.check("begin", "--ticket", "ABC-7")
        self.fix_and_commit()
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        status, answer = self.check("verify", "--ticket", "ABC-7", "--require-commit")
        self.assertIn("remote_refs_changed", self.codes(answer))

    def test_new_branch_and_new_tag_are_refused(self):
        """Known-wrong case: rule 5 forbids creating branches and tags."""
        self.check("begin", "--ticket", "ABC-7")
        self.fix_and_commit()
        self.git("branch", "side")
        self.git("tag", "t1")
        status, answer = self.check("verify", "--ticket", "ABC-7", "--require-commit")
        self.assertEqual(status, 1)
        self.assertTrue({"branch_created", "tag_created"} <= self.codes(answer), answer)

    def test_branch_of_another_worktree_is_allowed(self):
        self.check("begin", "--ticket", "ABC-7")
        self.git("worktree", "add", "-q", "-b", "step-8", str(self.root.parent / "other-step"))
        self.fix_and_commit()
        status, answer = self.check("verify", "--ticket", "ABC-7", "--require-commit")
        self.assertEqual((status, answer["result"]), (0, "pass"), answer)

    def test_deleted_branch_and_moved_tag_are_refused(self):
        self.git("branch", "keep")
        self.git("tag", "v1")
        self.check("begin", "--ticket", "ABC-7")
        self.fix_and_commit()
        self.git("branch", "-q", "-D", "keep")
        self.git("tag", "-f", "v1", "HEAD")
        status, answer = self.check("verify", "--ticket", "ABC-7")
        self.assertTrue({"branch_deleted", "tag_moved_or_deleted"} <= self.codes(answer), answer)

    def test_stash_is_refused(self):
        self.check("begin", "--ticket", "ABC-7")
        self.write("src/parse.py", "def parse(text):\n    return text.strip()\n")
        self.git("stash", "-q")
        status, answer = self.check("verify", "--ticket", "ABC-7")
        self.assertEqual(status, 1)
        self.assertIn("stash_used", self.codes(answer))

    def test_harness_files_in_the_commit_are_refused(self):
        self.check("begin", "--ticket", "ABC-7")
        self.write("src/parse.py", "def parse(text):\n    return text.strip()\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "ABC-7: Everything")
        status, answer = self.check("verify", "--ticket", "ABC-7")
        self.assertIn("commit_includes_harness_files", self.codes(answer))

    def test_changes_made_before_the_ticket_are_protected(self):
        self.write("AGENTS.md", "# Project rules\n\n## Section placed by the host\n")
        status, answer = self.check("begin", "--ticket", "ABC-7")
        self.assertEqual((status, answer["preexisting"]), (0, ["AGENTS.md"]))
        self.git("checkout", "--", "AGENTS.md")
        status, answer = self.check("verify", "--ticket", "ABC-7")
        self.assertIn("preexisting_change_altered", self.codes(answer))

    def test_committing_a_change_made_before_the_ticket_is_refused(self):
        self.write("AGENTS.md", "# Project rules\n\n## Section placed by the host\n")
        self.check("begin", "--ticket", "ABC-7")
        self.write("src/parse.py", "def parse(text):\n    return text.strip()\n")
        self.git("commit", "-q", "-am", "ABC-7: Fix and more")
        status, answer = self.check("verify", "--ticket", "ABC-7")
        self.assertIn("commit_includes_preexisting_changes", self.codes(answer))

    def test_uncommitted_change_fails_the_required_commit(self):
        self.check("begin", "--ticket", "ABC-7")
        self.fix_and_commit()
        self.write("src/parse.py", "def parse(text):\n    return text\n")
        status, answer = self.check("verify", "--ticket", "ABC-7", "--require-commit")
        self.assertIn("uncommitted_ticket_changes", self.codes(answer))
        status, answer = self.check("verify", "--ticket", "ABC-7")
        self.assertEqual(status, 0)
        self.assertIn("Do not make a second commit", answer["next"])

    def test_missing_commit_fails_the_required_commit(self):
        self.check("begin", "--ticket", "ABC-7")
        status, answer = self.check("verify", "--ticket", "ABC-7", "--require-commit")
        self.assertIn("missing_commit", self.codes(answer))
        self.assertIn("--no-change", self.check("verify", "--ticket", "ABC-7")[1]["next"])

    def test_ticket_that_needs_no_change_passes_with_no_change(self):
        self.check("begin", "--ticket", "ABC-7")
        status, answer = self.check("verify", "--ticket", "ABC-7", "--no-change")
        self.assertEqual((status, answer["result"], answer["commits_since_base"]), (0, "pass", 0), answer)
        self.assertIn("changed nothing", answer["next"])

    def test_no_change_refuses_a_commit_or_a_change(self):
        self.check("begin", "--ticket", "ABC-7")
        self.write("src/parse.py", "def parse(text):\n    return text.strip()\n")
        status, answer = self.check("verify", "--ticket", "ABC-7", "--no-change")
        self.assertIn("uncommitted_ticket_changes", self.codes(answer))
        self.git("commit", "-q", "-am", "ABC-7: Keep surrounding spaces out of parsed text")
        status, answer = self.check("verify", "--ticket", "ABC-7", "--no-change")
        self.assertEqual(status, 1)
        self.assertIn("unexpected_commit", self.codes(answer))
        status, answer = self.check("verify", "--ticket", "ABC-7", "--no-change", "--require-commit")
        self.assertEqual((status, answer["code"]), (2, "arguments_invalid"))

    def test_git_clean_of_an_owner_file_is_refused(self):
        """Known-wrong case: git clean removes a file the owner had not committed yet."""
        self.write(".git/info/exclude", ".baltor/\n")
        self.write("notes/owner-draft.md", "unsaved owner work\n")
        self.check("begin", "--ticket", "ABC-7")
        self.fix_and_commit()
        self.git("clean", "-q", "-f", "-d")
        self.assertFalse((self.root / "notes" / "owner-draft.md").exists())
        status, answer = self.check("verify", "--ticket", "ABC-7", "--require-commit")
        self.assertEqual(status, 1)
        self.assertIn("preexisting_untracked_removed", self.codes(answer))

    def test_begin_refuses_a_tree_with_other_changes(self):
        self.write("src/parse.py", "def parse(text):\n    return None\n")
        status, answer = self.check("begin", "--ticket", "ABC-7")
        self.assertEqual((status, answer["code"]), (1, "tree_not_clean"))
        status, answer = self.check("begin", "--ticket", "ABC-7", "--allow-changed", "src/parse.py")
        self.assertEqual((status, answer["code"]), (2, "arguments_invalid"))

    def host_list(self, paths):
        self.write(".baltor/unattended-git-rules/host-placed.json",
                   json.dumps({"record_type": "unattended_git_host_placed/v1", "paths": paths}) + "\n")

    def test_settings_file_the_host_merged_is_accepted_and_protected(self):
        """The host merged a settings fragment into a tracked .claude/settings.json before the step."""
        self.write(".claude/settings.json", "{}\n")
        self.git("add", ".claude/settings.json")
        self.git("commit", "-q", "-m", "Add settings")
        self.write(".claude/settings.json", '{"permissions": {"deny": ["Bash(git push:*)"]}}\n')
        status, answer = self.check("begin", "--ticket", "ABC-7")
        self.assertEqual((status, answer["code"]), (1, "tree_not_clean"))
        self.host_list([".claude/settings.json"])
        status, answer = self.check("begin", "--ticket", "ABC-7")
        self.assertEqual((status, answer["preexisting"]), (0, [".claude/settings.json"]), answer)
        self.write("src/parse.py", "def parse(text):\n    return text.strip()\n")
        self.git("commit", "-q", "-am", "ABC-7: Fix and settings")
        status, answer = self.check("verify", "--ticket", "ABC-7")
        self.assertIn("commit_includes_preexisting_changes", self.codes(answer))

    def test_host_listed_folder_covers_the_files_below_it(self):
        self.write(".claude/skills/demo/SKILL.md", "old\n")
        self.git("add", ".claude/skills/demo/SKILL.md")
        self.git("commit", "-q", "-m", "Add a skill")
        self.write(".claude/skills/demo/SKILL.md", "new\n")
        self.host_list([".claude/skills/"])
        status, answer = self.check("begin", "--ticket", "ABC-7")
        self.assertEqual(status, 0, answer)

    def test_host_list_in_a_workspace_below_the_repository_top(self):
        self.write("pkg/.claude/settings.json", "{}\n")
        self.git("add", "pkg/.claude/settings.json")
        self.git("commit", "-q", "-m", "Add package settings")
        self.write("pkg/.claude/settings.json", '{"permissions": {}}\n')
        self.write("pkg/.baltor/unattended-git-rules/host-placed.json",
                   json.dumps({"record_type": "unattended_git_host_placed/v1", "paths": [".claude/settings.json"]}) + "\n")
        finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "begin", "--ticket", "ABC-7"],
                                  cwd=self.root / "pkg", env=self.environment, capture_output=True, text=True, timeout=120)
        answer = json.loads(finished.stdout)
        self.assertEqual((finished.returncode, answer["result"]), (0, "begun"), answer)
        self.assertIn("pkg/.claude/settings.json", answer["preexisting"])

    def test_unusable_host_list_is_refused(self):
        self.write("src/parse.py", "def parse(text):\n    return None\n")
        for paths in (["../outside.txt"], ["."], [".baltor/other.json"], ["/etc/hosts"], [7]):
            self.host_list(paths)
            status, answer = self.check("begin", "--ticket", "ABC-7")
            self.assertEqual((status, answer["code"]), (2, "host_placed_invalid"), paths)
        self.write(".baltor/unattended-git-rules/host-placed.json", '{"record_type": "other/v1", "paths": []}\n')
        status, answer = self.check("begin", "--ticket", "ABC-7")
        self.assertEqual((status, answer["code"]), (2, "host_placed_invalid"))
        self.assertIn("Do not edit it", answer["next"])

    def test_begin_refuses_an_operation_in_progress(self):
        head = self.git("rev-parse", "HEAD")
        git_folder = Path(self.git("rev-parse", "--absolute-git-dir"))
        (git_folder / "MERGE_HEAD").write_text(head + "\n", encoding="utf-8")
        status, answer = self.check("begin", "--ticket", "ABC-7")
        self.assertEqual((status, answer["code"]), (1, "operation_in_progress"))

    def test_begin_twice_points_to_verify(self):
        self.check("begin", "--ticket", "ABC-7")
        status, answer = self.check("begin", "--ticket", "ABC-7")
        self.assertEqual((status, answer["code"]), (1, "ticket_already_begun"))
        self.assertIn("verify --ticket ABC-7", answer["next"])

    def test_refused_inputs(self):
        status, answer = self.check("verify", "--ticket", "ABC-7")
        self.assertEqual((status, answer["code"]), (2, "state_missing"))
        status, answer = self.check("begin", "--ticket", "../ABC")
        self.assertEqual((status, answer["code"]), (2, "ticket_invalid"))
        with tempfile.TemporaryDirectory() as plain:
            status, answer = self.check("begin", "--ticket", "ABC-7", "--root", plain)
            self.assertEqual((status, answer["code"]), (2, "not_a_repository"))

    def test_instruction_section_names_this_script(self):
        text = (PACKAGE / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("python3 -I -B .baltor/unattended-git-rules/scripts/git_ticket_check.py", text)
        self.assertIn("verify --ticket KEY --no-change", text)
        self.assertEqual((PACKAGE / "GEMINI.md").read_bytes(), (PACKAGE / "AGENTS.md").read_bytes())
        self.assertEqual((PACKAGE / "CLAUDE.md").read_text(encoding="utf-8"), "@AGENTS.md\n")


if __name__ == "__main__":
    unittest.main()
