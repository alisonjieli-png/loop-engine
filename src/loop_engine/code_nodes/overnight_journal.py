"""The night's own record, written before each effect and after it.

A run that is killed at 3am has to be resumable in the morning without
doing anything twice. That needs one property the ordinary run record does
not have: the moment an effect is *about* to happen is written down before
it happens, so a process that dies in the middle leaves a record saying an
effect was started and never finished.

Three states, and the middle one is the whole point:

    intended     the entry was written, the effect has not run yet
    committed    the effect ran and its outcome is recorded
    unknown      the process died between the two, so whether the effect
                 happened cannot be read off the record

A resume may repeat an effect only when the effect was declared repeatable
at the moment it was intended. Calling a local model again is repeatable:
it costs time and nothing else. Writing a file is repeatable only against
the exact content digest that was intended, so a resume can see the file
already holds it. Anything else in the unknown state stops the resume and
becomes a question for a person, because replaying a committed external
effect silently is the failure this whole record exists to prevent.

The file is JSON lines, appended and flushed to the operating system on
every entry, so a killed process keeps every entry it finished writing.
Nothing here runs an effect; it only records one.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

JOURNAL_FILENAME = "journal.jsonl"
ENTRY_RECORD_TYPE = "overnight_journal_entry/v1"

#: Effects a night may record, and whether a resume may repeat one whose
#: outcome was never written. The value is the reason, so a reader never
#: has to infer why a repeat was allowed.
REPEATABLE_EFFECTS = {
    "model_call": (
        "a local model call costs time and nothing outside this machine, so "
        "repeating one is safe"),
    "gate_run": (
        "the declared gate is an observation; running it again observes "
        "again"),
    "workspace_write": (
        "repeatable only against the exact content digest that was "
        "intended, so a resume can see the file already holds it"),
}

#: Effects with a consequence outside this machine. None is declared today;
#: the table exists so that adding one cannot be done by forgetting to.
EXTERNAL_EFFECTS: dict = {}


class JournalError(ValueError):
    """A journal entry that cannot be written or read as written."""


def content_digest(text: str) -> str:
    """sha256 over the exact bytes an effect intended to write."""
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EffectToken:
    """The handle returned when an effect was written down as intended."""

    sequence: int
    kind: str
    effect_key: str


class OvernightJournal:
    """Append-only entries for one night, readable by a later process."""

    def __init__(self, directory) -> None:
        self.directory = Path(directory)
        self.path = self.directory / JOURNAL_FILENAME
        self._sequence = 0
        for entry in self.read():
            self._sequence = max(self._sequence, int(entry.get("sequence", 0)))

    def append(self, kind: str, **fields) -> dict:
        """Write one entry and flush it, so an interruption keeps it."""
        if not str(kind).strip():
            raise JournalError("every journal entry names its kind")
        self._sequence += 1
        entry = {"record_type": ENTRY_RECORD_TYPE,
                 "sequence": self._sequence, "kind": str(kind),
                 "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 **fields}
        self.directory.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return entry

    def read(self) -> list:
        """Every entry written so far; a torn last line is dropped, not guessed."""
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except (OSError, ValueError):
            return []
        entries = []
        for line in lines:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if isinstance(entry, dict) and entry.get("record_type") == \
                    ENTRY_RECORD_TYPE:
                entries.append(entry)
        return entries

    def intend_effect(self, kind: str, effect_key: str, *,
                      repeatable: bool, detail: dict = None) -> EffectToken:
        """Record that an effect is about to run, before it runs."""
        if kind not in REPEATABLE_EFFECTS and kind not in EXTERNAL_EFFECTS:
            raise JournalError(
                f"unknown effect kind {kind!r}; declared kinds are "
                + ", ".join(sorted(set(REPEATABLE_EFFECTS) | set(
                    EXTERNAL_EFFECTS))))
        if type(repeatable) is not bool:
            raise JournalError(
                "an effect states whether a resume may repeat it; there is "
                "no default")
        if repeatable and kind in EXTERNAL_EFFECTS:
            raise JournalError(
                f"{kind} has a consequence outside this machine and can "
                "never be declared repeatable")
        if not str(effect_key).strip():
            raise JournalError(
                "an effect needs a key a later process can match it by")
        entry = self.append(
            "effect", effect_key=str(effect_key), effect_kind=str(kind),
            commitment="intended", repeatable=bool(repeatable),
            reason=REPEATABLE_EFFECTS.get(kind, ""),
            detail=dict(detail or {}))
        return EffectToken(int(entry["sequence"]), str(kind), str(effect_key))

    def commit_effect(self, token: EffectToken, outcome: dict) -> dict:
        """Record that the effect finished, with what it produced."""
        if not isinstance(token, EffectToken):
            raise JournalError("commit_effect takes the token intend returned")
        return self.append(
            "effect", effect_key=token.effect_key, effect_kind=token.kind,
            commitment="committed", intended_sequence=token.sequence,
            outcome=dict(outcome or {}))

    def effect_states(self) -> dict:
        """Every effect key, with the state the record actually supports."""
        states: dict = {}
        for entry in self.read():
            if entry.get("kind") != "effect":
                continue
            key = str(entry.get("effect_key") or "")
            commitment = str(entry.get("commitment") or "")
            if commitment == "intended":
                states[key] = {
                    "effect_kind": str(entry.get("effect_kind") or ""),
                    "commitment": "unknown",
                    "repeatable": bool(entry.get("repeatable")),
                    "detail": dict(entry.get("detail") or {}),
                    "outcome": {}}
            elif commitment == "committed" and key in states:
                states[key]["commitment"] = "committed"
                states[key]["outcome"] = dict(entry.get("outcome") or {})
        return states

    def unfinished_effects(self) -> list:
        """Effects the record cannot say happened, worst first.

        A resume reads this and does exactly two things: repeat the ones
        that were declared repeatable, and stop on anything else.
        """
        unfinished = [{"effect_key": key, **value}
                      for key, value in self.effect_states().items()
                      if value["commitment"] == "unknown"]
        return sorted(unfinished, key=lambda item: (item["repeatable"],
                                                    item["effect_key"]))

    def resume_plan(self) -> dict:
        """What a resume may do, and what it must ask a person about."""
        unfinished = self.unfinished_effects()
        blocking = [item for item in unfinished if not item["repeatable"]]
        return {
            "record_type": "overnight_resume_plan/v1",
            "entries": len(self.read()),
            "unfinished_effects": unfinished,
            "may_repeat": [item["effect_key"] for item in unfinished
                           if item["repeatable"]],
            "blocked_on": [item["effect_key"] for item in blocking],
            "can_resume": not blocking,
            "sentence": (
                "Every unfinished effect was declared repeatable, so this "
                "night can be resumed without doing anything twice."
                if not blocking else
                "This night cannot be resumed on its own: "
                + ", ".join(item["effect_key"] for item in blocking)
                + " was started and its outcome was never recorded. Only a "
                "person can say whether it happened."),
        }

    def committed_write_digests(self) -> dict:
        """Path to content digest for every workspace write that finished."""
        digests = {}
        for key, value in self.effect_states().items():
            if value["effect_kind"] != "workspace_write" \
                    or value["commitment"] != "committed":
                continue
            path = str(value["detail"].get("path") or "")
            if path:
                digests[path] = str(value["detail"].get("digest") or "")
        return digests


def self_test() -> dict:
    """Every guard beside the interruption it exists to survive."""
    import tempfile

    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": str(detail)[:220]})

    def refuses(name, call, fragment):
        try:
            call()
        except JournalError as error:
            check(name, fragment in str(error), str(error))
        else:
            check(name, False, "accepted a known wrong entry")

    with tempfile.TemporaryDirectory() as folder:
        journal = OvernightJournal(folder)
        check("a_fresh_journal_has_nothing_to_resume",
              journal.resume_plan()["can_resume"] is True
              and journal.resume_plan()["unfinished_effects"] == [])

        token = journal.intend_effect("model_call", "step-1/call-1",
                                      repeatable=True)
        check("an_effect_written_down_but_not_finished_reads_as_unknown",
              journal.effect_states()["step-1/call-1"]["commitment"]
              == "unknown")
        journal.commit_effect(token, {"ok": True, "eval_tokens": 18})
        check("a_finished_effect_reads_as_committed_with_its_outcome",
              journal.effect_states()["step-1/call-1"]["commitment"]
              == "committed"
              and journal.effect_states()["step-1/call-1"]["outcome"][
                  "eval_tokens"] == 18)

        # The known wrong case this whole record exists for: a process that
        # died between the intent and the outcome.
        journal.intend_effect("model_call", "step-2/call-1", repeatable=True)
        reopened = OvernightJournal(folder)
        plan = reopened.resume_plan()
        check("a_later_process_reads_the_interrupted_effect_from_disk",
              plan["may_repeat"] == ["step-2/call-1"]
              and plan["can_resume"] is True, plan["sentence"])

        # A write that was intended and never confirmed blocks the resume.
        journal.intend_effect(
            "workspace_write", "step-3/write-1", repeatable=False,
            detail={"path": "/tmp/x", "digest": content_digest("hello")})
        blocked = OvernightJournal(folder).resume_plan()
        check("an_unrepeatable_effect_that_never_finished_stops_the_resume",
              blocked["can_resume"] is False
              and blocked["blocked_on"] == ["step-3/write-1"]
              and "Only a person can say" in blocked["sentence"],
              blocked["sentence"])

        check("the_numbering_continues_across_processes",
              OvernightJournal(folder).append("note", text="later")[
                  "sequence"] > len(journal.read()) - 1)

        refuses("an_effect_kind_nobody_declared_is_refused",
                lambda: journal.intend_effect("send_email", "k",
                                              repeatable=True),
                "unknown effect kind")
        refuses("an_effect_that_does_not_say_whether_it_repeats_is_refused",
                lambda: journal.intend_effect("model_call", "k",
                                              repeatable=None),
                "there is no default")
        refuses("an_effect_without_a_key_cannot_be_matched_later",
                lambda: journal.intend_effect("model_call", "  ",
                                              repeatable=True),
                "a key a later process can match")
        refuses("an_entry_without_a_kind_is_refused",
                lambda: journal.append("  "), "names its kind")

        # A torn last line is what a hard kill actually leaves behind.
        whole_entries = len(OvernightJournal(folder).read())
        with open(Path(folder) / JOURNAL_FILENAME, "a", encoding="utf-8") as h:
            h.write('{"record_type": "overnight_journal_entry/v1", "seq')
        after = OvernightJournal(folder)
        check("a_torn_last_line_is_dropped_rather_than_guessed_at",
              len(after.read()) == whole_entries and whole_entries >= 5
              and after.resume_plan()["can_resume"] is False,
              f"{whole_entries} whole entries before the tear")

    check("no_external_effect_is_declared_repeatable_by_accident",
          all(kind not in REPEATABLE_EFFECTS for kind in EXTERNAL_EFFECTS))
    check("the_same_bytes_digest_the_same_way",
          content_digest("hello") == content_digest("hello")
          and content_digest("hello") != content_digest("hello "))
    passed = sum(item["passed"] for item in tests)
    return {"name": "overnight_journal", "tests": tests,
            "passed": passed, "total": len(tests)}
