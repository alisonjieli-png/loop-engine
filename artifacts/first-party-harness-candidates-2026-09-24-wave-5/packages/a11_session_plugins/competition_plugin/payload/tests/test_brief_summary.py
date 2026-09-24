"""Tests for scripts/brief_summary.py, the session start hook for Claude Code and Gemini CLI."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "brief_summary.py"
EXAMPLE = ROOT / "examples" / "competition"
EXAMPLES = ROOT / "examples"
BRIEF = Path(".baltor/competition/brief.json")
NOTES = Path(".baltor/state/competition-plugin/experiments.jsonl")


def hook(harness: str, payload: bytes, root: Path) -> subprocess.CompletedProcess:
    variable = "CLAUDE_PROJECT_DIR" if harness == "claude_code" else "GEMINI_PROJECT_DIR"
    return subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--harness", harness], input=payload,
                          capture_output=True, timeout=60,
                          env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), variable: str(root)})


def start_event(source: str = "startup", **extra) -> bytes:
    event = {"session_id": "t", "transcript_path": "/nonexistent", "cwd": "/", "hook_event_name": "SessionStart",
             "source": source}
    event.update(extra)
    return json.dumps(event).encode()


def context_of(finished) -> str:
    return json.loads(finished.stdout)["hookSpecificOutput"]["additionalContext"]


class BriefSummaryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def copy_example(self) -> dict:
        (self.root / BRIEF).parent.mkdir(parents=True)
        shutil.copyfile(EXAMPLE / BRIEF, self.root / BRIEF)
        return json.loads((self.root / BRIEF).read_text(encoding="utf-8"))

    def test_claude_code_summary_names_metric_validation_and_limits(self):
        finished = hook("claude_code", (EXAMPLES / "claude_code-sessionstart-startup.json").read_bytes(), EXAMPLE)
        self.assertEqual(finished.returncode, 0, finished.stderr)
        answer = json.loads(finished.stdout)
        self.assertEqual(answer["hookSpecificOutput"]["hookEventName"], "SessionStart")
        text = context_of(finished)
        for expected in ("Metric: rmse, lower is better.", "Validation: group_kfold, 5 folds, groups by store_id.",
                         "Daily submission limit: 3.", "Experiment notes: 0.", "/competition-plugin:experiment-note",
                         "Rules: Use only the supplied data files; Keep the row order of the sample submission.",
                         "never upload yourself"):
            self.assertIn(expected, text)

    def test_gemini_summary_uses_the_gemini_output_shape(self):
        finished = hook("gemini_cli", (EXAMPLES / "gemini_cli-sessionstart-startup.json").read_bytes(), EXAMPLE)
        answer = json.loads(finished.stdout)
        self.assertEqual(set(answer), {"hookSpecificOutput"})
        self.assertEqual(set(answer["hookSpecificOutput"]), {"additionalContext"})
        self.assertIn("/experiment-note", answer["hookSpecificOutput"]["additionalContext"])

    def test_unexpected_events_fail_open(self):
        for harness, name in (("claude_code", "claude_code-sessionstart-malformed.json"),
                              ("gemini_cli", "gemini_cli-sessionstart-malformed.json")):
            finished = hook(harness, (EXAMPLES / name).read_bytes(), EXAMPLE)
            self.assertEqual((finished.returncode, finished.stdout.strip()), (0, b"{}"))
            self.assertIn(b"refused", finished.stderr)
        finished = hook("claude_code", b"\x00not json", EXAMPLE)
        self.assertEqual(finished.stdout.strip(), b"{}")

    def test_missing_brief_tells_the_session_to_stop(self):
        text = context_of(hook("claude_code", start_event(), self.root))
        self.assertIn("no brief at .baltor/competition/brief.json", text)
        self.assertIn("Stop and report", text)

    def test_brief_with_an_invalid_metric_is_not_summarized(self):
        # Known-wrong case: a brief whose metric direction is prose, not minimize or maximize.
        brief = self.copy_example()
        brief["metric"]["direction"] = "lower"
        (self.root / BRIEF).write_text(json.dumps(brief), encoding="utf-8")
        text = context_of(hook("claude_code", start_event(), self.root))
        self.assertIn("could not be read (metric_invalid)", text)
        self.assertNotIn("Metric:", text)

    def test_notes_count_latest_and_unreadable_lines(self):
        self.copy_example()
        (self.root / NOTES).parent.mkdir(parents=True)
        lines = [json.dumps({"record_type": "experiment_note/v1", "experiment_id": "exp-1", "cv_mean": 13.2}),
                 "{not json",
                 json.dumps({"record_type": "experiment_note/v1", "experiment_id": "exp-2", "cv_mean": 12.75})]
        (self.root / NOTES).write_text("\n".join(lines) + "\n", encoding="utf-8")
        text = context_of(hook("gemini_cli", start_event(), self.root))
        self.assertIn("Experiment notes: 2; latest exp-2, cv mean 12.75; 1 unreadable lines, report them.", text)

    def test_transcript_is_never_read_and_nothing_is_written(self):
        self.copy_example()
        transcript = self.root / "transcript.jsonl"
        transcript.write_text("TRANSCRIPT-MARKER-5519\n", encoding="utf-8")
        before = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*"))
        finished = hook("claude_code", start_event(transcript_path=str(transcript)), self.root)
        after = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*"))
        self.assertNotIn(b"TRANSCRIPT-MARKER-5519", finished.stdout)
        self.assertEqual(before, after)

    def test_summary_is_bounded(self):
        brief = self.copy_example()
        brief["rules"] = ["R" * 200] * 20
        (self.root / BRIEF).write_text(json.dumps(brief), encoding="utf-8")
        self.assertLessEqual(len(context_of(hook("claude_code", start_event(), self.root))), 2500)


if __name__ == "__main__":
    unittest.main()
