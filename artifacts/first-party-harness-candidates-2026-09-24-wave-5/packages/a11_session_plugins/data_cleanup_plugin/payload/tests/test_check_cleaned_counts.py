"""Tests for scripts/check_cleaned_counts.py in hook mode and in status mode."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_cleaned_counts.py"
EXAMPLE = ROOT / "examples" / "cleanup"
EXAMPLES = ROOT / "examples"
SOURCE = 'id,name,amount\n1,Ana,10\n2,Bo,"1,5"\n3,Cy,"two\nlines"\n4,Di,\n'


def run(arguments, payload: bytes = b"", environment=None, cwd=None) -> subprocess.CompletedProcess:
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    env.update(environment or {})
    return subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments], input=payload, capture_output=True,
                          timeout=60, env=env, cwd=cwd)


def workspace(root: Path, pairs, files: dict) -> None:
    step = root / ".baltor" / "step"
    step.mkdir(parents=True)
    (step / "cleanup-pairs.json").write_text(json.dumps({"record_type": "cleanup_pairs/v1", "pairs": pairs}),
                                             encoding="utf-8")
    for relative, text in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def event(harness: str, path: str, tool: str | None = None) -> bytes:
    if harness == "claude_code":
        value = {"session_id": "t", "transcript_path": "/nonexistent", "cwd": "/", "hook_event_name": "PostToolUse",
                 "tool_name": tool or "Write", "tool_input": {"file_path": path, "content": "x"}, "tool_response": {}}
    else:
        value = {"session_id": "t", "transcript_path": "/nonexistent", "cwd": "/", "hook_event_name": "AfterTool",
                 "timestamp": "2026-09-23T00:00:00Z", "tool_name": tool or "write_file",
                 "tool_input": {"file_path": path, "content": "x"}, "tool_response": {"llmContent": "ok"}}
    return json.dumps(value).encode()


def hook(harness: str, root: Path, path: str, tool: str | None = None) -> dict:
    variable = "CLAUDE_PROJECT_DIR" if harness == "claude_code" else "GEMINI_PROJECT_DIR"
    finished = run(["--harness", harness], event(harness, path, tool), {variable: str(root)})
    assert finished.returncode == 0, finished.stderr
    return json.loads(finished.stdout)


PAIR = {"source": "raw/people.csv", "cleaned": "clean/people.csv"}


class CheckCleanedCountsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def status(self) -> tuple[int, dict]:
        finished = run(["--all", "--root", str(self.root)])
        return finished.returncode, json.loads(finished.stdout)

    def test_example_status_reports_one_match_and_one_lost_row(self):
        finished = run(["--all", "--root", str(EXAMPLE)])
        self.assertEqual(finished.returncode, 1)
        results = json.loads(finished.stdout)["results"]
        self.assertEqual([result["status"] for result in results], ["match", "mismatch"])
        self.assertIn("rows lost: 4 rows, source has 5", results[1]["details"][0])

    def test_quoted_line_break_is_one_row_not_two(self):
        workspace(self.root, [PAIR], {"raw/people.csv": SOURCE, "clean/people.csv": SOURCE})
        code, report = self.status()
        self.assertEqual(code, 0)
        self.assertEqual((report["results"][0]["source_rows"], report["results"][0]["cleaned_rows"]), (4, 4))

    def test_hook_confirms_a_matching_copy_for_claude_code(self):
        workspace(self.root, [PAIR], {"raw/people.csv": SOURCE, "clean/people.csv": SOURCE})
        answer = hook("claude_code", self.root, str(self.root / "clean" / "people.csv"))
        self.assertNotIn("decision", answer)
        self.assertIn("passed", answer["hookSpecificOutput"]["additionalContext"])

    def test_hook_blocks_a_copy_that_lost_the_row_with_an_empty_value(self):
        # Known-wrong case: a cleaning step silently dropped the row whose amount was empty.
        lost = 'id,name,amount\n1,Ana,10\n2,Bo,"1,5"\n3,Cy,"two\nlines"\n'
        workspace(self.root, [PAIR], {"raw/people.csv": SOURCE, "clean/people.csv": lost})
        answer = hook("claude_code", self.root, str(self.root / "clean" / "people.csv"))
        self.assertEqual(answer["decision"], "block")
        self.assertIn("rows lost: 3 rows, source has 4", answer["reason"])

    def test_gemini_answers_with_additional_context_for_both_outcomes(self):
        lost = "id,name,amount\n1,Ana,10\n"
        workspace(self.root, [PAIR], {"raw/people.csv": SOURCE, "clean/people.csv": lost})
        answer = hook("gemini_cli", self.root, "clean/people.csv", tool="replace")
        self.assertEqual(set(answer), {"hookSpecificOutput"})
        self.assertIn("failed", answer["hookSpecificOutput"]["additionalContext"])

    def test_header_changes_are_named(self):
        renamed = SOURCE.replace("id,name,amount", "id,full_name,amount", 1)
        reordered = 'name,id,amount\nAna,1,10\nBo,2,"1,5"\nCy,3,"two\nlines"\nDi,4,\n'
        workspace(self.root, [PAIR, {"source": "raw/people.csv", "cleaned": "clean/reordered.csv"}],
                  {"raw/people.csv": SOURCE, "clean/people.csv": renamed, "clean/reordered.csv": reordered})
        code, report = self.status()
        self.assertEqual(code, 1)
        self.assertEqual(report["results"][0]["details"], ["header lacks ['name']", "header adds ['full_name']"])
        self.assertEqual(report["results"][1]["details"], ["header has the right columns in another order"])

    def test_declared_rename_and_drop_allowance_are_respected(self):
        cleaned = 'id,full_name,amount\n1,Ana,10\n2,Bo,"1,5"\n3,Cy,"two\nlines"\n'
        pair = {**PAIR, "renamed_columns": {"name": "full_name"}, "max_dropped_rows": 1}
        workspace(self.root, [pair], {"raw/people.csv": SOURCE, "clean/people.csv": cleaned})
        code, report = self.status()
        self.assertEqual((code, report["results"][0]["status"]), (0, "match"))
        (self.root / "clean" / "people.csv").write_text("id,full_name,amount\n1,Ana,10\n", encoding="utf-8")
        code, report = self.status()
        self.assertEqual((code, report["results"][0]["status"]), (1, "mismatch"))

    def test_added_rows_are_a_mismatch(self):
        workspace(self.root, [PAIR], {"raw/people.csv": SOURCE, "clean/people.csv": SOURCE + "5,Ed,1\n"})
        code, report = self.status()
        self.assertEqual(code, 1)
        self.assertIn("rows added", report["results"][0]["details"][0])

    def test_write_to_a_source_file_is_flagged(self):
        workspace(self.root, [PAIR], {"raw/people.csv": SOURCE, "clean/people.csv": SOURCE})
        answer = hook("claude_code", self.root, str(self.root / "raw" / "people.csv"), tool="Edit")
        self.assertEqual(answer["decision"], "block")
        self.assertIn("declares as a source", answer["reason"])

    def test_edit_of_the_pairs_file_is_flagged(self):
        workspace(self.root, [PAIR], {"raw/people.csv": SOURCE, "clean/people.csv": SOURCE})
        answer = hook("claude_code", self.root, str(self.root / ".baltor" / "step" / "cleanup-pairs.json"))
        self.assertEqual(answer["decision"], "block")
        self.assertIn("was changed during the step", answer["reason"])

    def test_unrelated_files_and_paths_outside_the_root_are_ignored(self):
        workspace(self.root, [PAIR], {"raw/people.csv": SOURCE, "clean/people.csv": SOURCE})
        for path in (str(self.root / "notes.md"), "/etc/hosts", "../outside/clean/people.csv"):
            finished = run(["--harness", "claude_code"], event("claude_code", path),
                           {"CLAUDE_PROJECT_DIR": str(self.root)})
            self.assertEqual((finished.returncode, finished.stdout.strip()), (0, b"{}"), path)
            self.assertEqual(finished.stderr, b"", "an ignored path is not refused input")

    def test_missing_pairs_file_is_silent_in_the_hook_and_refused_in_status(self):
        self.assertEqual(hook("claude_code", self.root, str(self.root / "clean" / "people.csv")), {})
        code, report = self.status()
        self.assertEqual((code, report["error"]), (2, "pairs_missing"))

    def test_unreadable_pairs_file_is_reported_by_the_hook(self):
        (self.root / ".baltor" / "step").mkdir(parents=True)
        (self.root / ".baltor" / "step" / "cleanup-pairs.json").write_text('{"record_type": "cleanup_pairs/v2", "pairs": []}',
                                                                          encoding="utf-8")
        answer = hook("claude_code", self.root, str(self.root / "clean" / "people.csv"))
        self.assertEqual(answer["decision"], "block")
        self.assertIn("could not run", answer["reason"])

    def test_malformed_events_fail_open(self):
        samples = [("claude_code", (EXAMPLES / "claude_code-posttooluse-malformed.json").read_bytes()),
                   ("gemini_cli", (EXAMPLES / "gemini_cli-aftertool-malformed.json").read_bytes()),
                   ("claude_code", b"not json"), ("gemini_cli", b'{"a": 1, "a": 1}')]
        for harness, payload in samples:
            finished = run(["--harness", harness], payload, {"CLAUDE_PROJECT_DIR": str(EXAMPLE)})
            self.assertEqual(finished.returncode, 0)
            self.assertEqual(finished.stdout.strip(), b"{}")
            self.assertIn(b"refused", finished.stderr)

    def test_unreadable_and_missing_cleaned_files_have_their_own_status(self):
        workspace(self.root, [PAIR, {"source": "raw/people.csv", "cleaned": "clean/absent.csv"}],
                  {"raw/people.csv": SOURCE})
        (self.root / "clean").mkdir()
        (self.root / "clean" / "people.csv").write_bytes("id,name,amount\n1,Jos\xe9,1\n".encode("latin-1"))
        code, report = self.status()
        self.assertEqual(code, 1)
        self.assertEqual([result["status"] for result in report["results"]], ["unreadable", "missing_cleaned"])
        self.assertEqual(report["results"][0]["details"], ["not_utf8"])

    def test_unsafe_pairs_are_refused(self):
        workspace(self.root, [{"source": "../raw.csv", "cleaned": "clean/people.csv"}], {})
        code, report = self.status()
        self.assertEqual((code, report["error"]), (2, "pair_paths_invalid"))

    def test_cleaned_file_linking_outside_the_root_is_unreadable(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        Path(outside.name, "people.csv").write_text(SOURCE, encoding="utf-8")
        workspace(self.root, [PAIR], {"raw/people.csv": SOURCE})
        (self.root / "clean").mkdir()
        os.symlink(Path(outside.name, "people.csv"), self.root / "clean" / "people.csv")
        code, report = self.status()
        self.assertEqual(code, 1)
        self.assertEqual((report["results"][0]["status"], report["results"][0]["details"]), ("unreadable", ["path_leaves_root"]))

    def test_hook_writes_nothing(self):
        workspace(self.root, [PAIR], {"raw/people.csv": SOURCE, "clean/people.csv": "id,name,amount\n"})
        before = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*"))
        hook("claude_code", self.root, str(self.root / "clean" / "people.csv"))
        after = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*"))
        self.assertEqual(before, after)

    def test_shipped_hook_samples_give_the_documented_answers(self):
        environment = {"CLAUDE_PROJECT_DIR": str(EXAMPLE), "GEMINI_PROJECT_DIR": str(EXAMPLE)}
        clean = run(["--harness", "claude_code"], (EXAMPLES / "claude_code-posttooluse-clean-copy.json").read_bytes(), environment)
        self.assertIn("passed", json.loads(clean.stdout)["hookSpecificOutput"]["additionalContext"])
        dropped = run(["--harness", "gemini_cli"], (EXAMPLES / "gemini_cli-aftertool-dropped-row.json").read_bytes(), environment)
        self.assertIn("rows lost", json.loads(dropped.stdout)["hookSpecificOutput"]["additionalContext"])


if __name__ == "__main__":
    unittest.main()
