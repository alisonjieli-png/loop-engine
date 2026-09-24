"""Tests for scripts/session_start.py, the session start hook for Claude Code and Cursor."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "session_start.py"
EXAMPLE = ROOT / "examples" / "night"
EXAMPLES = ROOT / "examples"
RESULTS = Path(".baltor/state/overnight-ticket-plugin/results")


def hook(harness: str, payload: bytes, root=None, variable: str = "CLAUDE_PROJECT_DIR", cwd=None):
    environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    if root is not None:
        environment[variable] = str(root)
    return subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--harness", harness], input=payload,
                          capture_output=True, timeout=60, env=environment, cwd=cwd)


def claude_event(**extra) -> bytes:
    event = {"session_id": "test-session", "transcript_path": "/nonexistent/transcript.jsonl", "cwd": "/",
             "hook_event_name": "SessionStart", "source": "startup"}
    event.update(extra)
    return json.dumps(event).encode()


def make_night(root: Path, tickets=("T-1", "T-2"), title="A title", handoffs=()) -> None:
    items = [{"position": index, "id": ticket, "title": title} for index, ticket in enumerate(tickets, start=1)]
    queue = json.dumps({"record_type": "night_queue/v1", "items": items}).encode()
    (root / ".baltor" / "night").mkdir(parents=True)
    (root / ".baltor" / "night" / "queue.json").write_bytes(queue)
    (root / RESULTS).mkdir(parents=True)
    for position, (ticket, handoff) in enumerate(handoffs, start=1):
        saved = {"record_type": "overnight_ticket_result/v1", "queue_sha256": hashlib.sha256(queue).hexdigest(),
                 "ticket_id": ticket, "position": position, "outcome": "fixed", "summary": "Done.", "evidence": [],
                 "changed_files": [], "handoff": handoff, "closed_at": "2026-09-23T01:00:00Z"}
        (root / RESULTS / f"{ticket}.json").write_text(json.dumps(saved), encoding="utf-8")


def context_of(finished) -> str:
    answer = json.loads(finished.stdout)
    if "hookSpecificOutput" in answer:
        return answer["hookSpecificOutput"]["additionalContext"]
    return answer["additional_context"]


class SessionStartTests(unittest.TestCase):
    def test_claude_code_startup_names_next_ticket_check_and_last_handoff(self):
        payload = (EXAMPLES / "claude_code-sessionstart-startup.json").read_bytes()
        finished = hook("claude_code", payload, EXAMPLE)
        self.assertEqual(finished.returncode, 0, finished.stderr)
        answer = json.loads(finished.stdout)
        self.assertEqual(answer["hookSpecificOutput"]["hookEventName"], "SessionStart")
        text = context_of(finished)
        self.assertIn("Next ticket: 2 of 3, T-102: Totals row counts refunds twice.", text)
        self.assertIn("The ticket's check command: python3 -m unittest tests.test_totals", text)
        self.assertIn("The totals row counts each refund once.", text)
        self.assertIn("Last handoff, from T-101 (fixed): Date output lives in src/export.py", text)
        self.assertIn("/overnight-ticket-plugin:night-status", text)

    def test_ticket_without_a_title_is_named_by_its_id(self):
        with tempfile.TemporaryDirectory() as directory:
            make_night(Path(directory), tickets=("T-7",), title="")
            finished = hook("claude_code", claude_event(), directory)
        self.assertIn("Next ticket: 1 of 1, T-7 (the queue gives no title).", context_of(finished))

    def test_cursor_session_start_uses_the_cursor_output_field(self):
        payload = (EXAMPLES / "cursor-sessionstart-startup.json").read_bytes()
        finished = hook("cursor", payload, EXAMPLE, variable="CURSOR_PROJECT_DIR")
        self.assertEqual(finished.returncode, 0, finished.stderr)
        answer = json.loads(finished.stdout)
        self.assertEqual(set(answer), {"additional_context"})
        self.assertIn("T-102", answer["additional_context"])
        self.assertIn("night-status command", answer["additional_context"])

    def test_unexpected_event_fails_open_with_an_empty_object(self):
        for harness, name in (("claude_code", "claude_code-sessionstart-malformed.json"),
                              ("cursor", "cursor-sessionstart-malformed.json")):
            finished = hook(harness, (EXAMPLES / name).read_bytes(), EXAMPLE)
            self.assertEqual(finished.returncode, 0)
            self.assertEqual(finished.stdout.strip(), b"{}")
            self.assertIn(b"refused", finished.stderr)

    def test_unreadable_and_oversized_input_fail_open(self):
        for payload in (b"not json", b"\xff\xfe", b'{"a": 1, "a": 2}', b"[" * 5000,
                        b'{"x": "' + b"a" * (1024 * 1024 + 8) + b'"}'):
            finished = hook("claude_code", payload, EXAMPLE)
            self.assertEqual(finished.returncode, 0)
            self.assertEqual(finished.stdout.strip(), b"{}")

    def test_missing_queue_is_said_plainly(self):
        with tempfile.TemporaryDirectory() as directory:
            finished = hook("claude_code", claude_event(), Path(directory))
        self.assertIn("no night queue", context_of(finished))

    def test_unreadable_queue_tells_the_session_to_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            night = Path(directory) / ".baltor" / "night"
            night.mkdir(parents=True)
            (night / "queue.json").write_text('{"record_type": "night_queue/v2", "items": []}', encoding="utf-8")
            finished = hook("claude_code", claude_event(), Path(directory))
        text = context_of(finished)
        self.assertIn("could not be read (unsupported_queue_record_type)", text)
        self.assertIn("Stop and report", text)

    def test_long_title_and_handoff_are_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            make_night(Path(directory), title="T" * 200, handoffs=[("T-1", "H" * 600)])
            text = context_of(hook("claude_code", claude_event(), Path(directory)))
        self.assertLessEqual(len(text), 2000)
        self.assertLessEqual(text.count("H"), 600)

    def test_transcript_is_never_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_night(root)
            transcript = root / "transcript.jsonl"
            transcript.write_text("TRANSCRIPT-MARKER-7431\n", encoding="utf-8")
            finished = hook("claude_code", claude_event(transcript_path=str(transcript)), root)
        self.assertNotIn(b"TRANSCRIPT-MARKER-7431", finished.stdout)

    def test_all_tickets_closed_stops_new_ticket_work(self):
        with tempfile.TemporaryDirectory() as directory:
            make_night(Path(directory), tickets=("T-1",), handoffs=[("T-1", "Nothing left.")])
            text = context_of(hook("claude_code", claude_event(source="resume"), Path(directory)))
        self.assertIn("All 1 tickets have result records", text)

    def test_hook_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_night(root, handoffs=[("T-1", "Next session notes.")])
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            hook("claude_code", claude_event(), root, cwd=directory)
            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
