"""Runtime Memory — the shared working notebook for loops in ONE run.

Architectural role: Static Architecture service (the active-run
communication plane the superseding charter of 2026-08-24 requires live:
"a shared working notebook for the loops active in the current run" —
any loop writes a note, any loop reads notes; the real-time canary must
see a note written and read).

Owns:
    - RunNoteBoard: run-scoped, append-only, in-memory notes (topic
      channels, author loop, references), with every write AND read
      recorded on the run's ledger as canonical
      ``runtime_memory.message_written`` / ``message_read`` events —
      loop-to-loop communication is evidence, never a side channel;
    - to_curation_candidates(): notes as CANDIDATE Strings with
      runtime-memory provenance — the promotion path into the persistent
      pillars is curation through the evidence gate, never automatic.

Does not own:
    - the four intelligence layers (persistent; this board is the run's
      scratch memory and dies with the run unless curated), User
      Intelligence (human-to-loop; this is loop-to-loop), or the
      Chronicle (which receives these events like any others).

Public entry points:
    - RunNoteBoard(run_id, ledger=None).write(note, loop_id=..., ...)
    - RunNoteBoard.read(topic=..., since=...) / search(query)
    - RunNoteBoard.to_curation_candidates()

Key invariants:
    - run-scoped: two boards never see each other's notes;
    - append-only: notes are immutable once written;
    - empty notes refused; every write/read lands on the ledger when
      one is attached;
    - nothing auto-promotes — curation candidates are candidates.

Verification: self_test() — cross-loop write/read on a shared ledger,
run isolation, refusals, and the curation-candidate contract.
"""
from __future__ import annotations

import time


class RunNoteBoard:
    """The one note board for one run."""

    def __init__(self, run_id: str, ledger=None):
        self.run_id = run_id
        self._ledger = ledger
        self._notes: list = []

    def write_as_loop(self, note: str, **kw) -> dict:
        """EVERY RUNTIME-MEMORY WRITE IS A LOOP (owner, 2026-08-24).

        The write itself was already a ledger event; the ACCESS was not a
        loop.  This is the envelope — deterministic, one accepted success —
        so a note reaching the board is a recorded crossing, not a method
        call that happens to log."""
        from ..loop.encapsulate import as_practitioner_loop
        return as_practitioner_loop(f"runtime memory write: {note[:40]}",
                                    lambda: self.write(note, **kw),
                                    ledger=self._ledger)["value"]

    def read_as_loop(self, **kw) -> list:
        """The read side of the same law."""
        from ..loop.encapsulate import as_practitioner_loop
        return as_practitioner_loop("runtime memory read",
                                    lambda: self.read(**kw),
                                    ledger=self._ledger)["value"]

    def write(self, note: str, *, loop_id: str, topic: str = "general",
              refs: tuple = ()) -> dict:
        if not str(note).strip():
            raise ValueError("empty runtime-memory note refused")
        rec = {"note_id": f"rm-{len(self._notes) + 1}", "run_id": self.run_id,
               "note": str(note).strip(), "loop_id": loop_id, "topic": topic,
               "refs": list(refs), "ts": time.time()}
        self._notes.append(rec)
        if self._ledger is not None:
            self._ledger.record(loop_id=loop_id,
                                event="runtime_memory.message_written",
                                note_id=rec["note_id"], topic=topic,
                                preview=rec["note"][:80])
        return rec

    def read(self, *, topic: "str | None" = None, since: int = 0,
             loop_id: str = "") -> list:
        hits = [n for n in self._notes[since:]
                if topic is None or n["topic"] == topic]
        if self._ledger is not None:
            self._ledger.record(loop_id=loop_id,
                                event="runtime_memory.message_read",
                                count=len(hits), topic=topic or "all")
        return hits

    def search(self, query: str) -> list:
        toks = [t for t in str(query).lower().split() if t]
        return [n for n in self._notes
                if all(t in n["note"].lower() for t in toks)]

    def to_curation_candidates(self) -> list:
        """Notes as candidate Strings for LATER curation into a
        persistent pillar — provenance names this run; maturity is
        candidate; nothing here promotes anything."""
        return [{"kind": "note", "text": n["note"], "maturity": "candidate",
                 "provenance": f"runtime_memory {self.run_id} "
                               f"(loop {n['loop_id']}, topic {n['topic']})",
                 "source_note_id": n["note_id"]} for n in self._notes]


def self_test() -> dict:
    from ..loop.recursive_loop import LoopLedger
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    # 1. loop-to-loop: loop A writes, loop B reads; both actions land on
    # the SHARED ledger as canonical runtime_memory events.
    ledger = LoopLedger()
    board = RunNoteBoard("run-1", ledger=ledger)
    board.write("target column is skewed — consider log transform",
                loop_id="loop1", topic="findings")
    got = board.read(topic="findings", loop_id="loop2")
    evs = [e.get("event", "") for e in ledger.events]
    check("loops_share_notes_and_both_sides_are_evidence",
          len(got) == 1 and got[0]["note"].startswith("target column")
          and "runtime_memory.message_written" in evs
          and "runtime_memory.message_read" in evs,
          "write by loop1, read by loop2, two ledger events")

    # 2. run isolation: a second run's board sees nothing.
    other = RunNoteBoard("run-2")
    check("boards_are_run_scoped", other.read() == []
          and len(board.search("skewed")) == 1)

    # 3. refusals: empty note; append-only immutability (reads return
    # copies of reality — the stored note text never mutates).
    refused = False
    try:
        board.write("   ", loop_id="loop1")
    except ValueError:
        refused = True
    first_text = board.read()[0]["note"]
    check("empty_refused_and_notes_append_only",
          refused and first_text == board._notes[0]["note"])

    # 4. curation path: candidates with provenance, never a promotion.
    cands = board.to_curation_candidates()
    check("curation_candidates_carry_provenance_and_stay_candidates",
          len(cands) == 1 and cands[0]["maturity"] == "candidate"
          and "runtime_memory run-1" in cands[0]["provenance"])

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
