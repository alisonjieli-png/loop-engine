"""Persistence - durable, append-only stores for every knowledge plane.

The intelligence the loop accumulates - notes and records - must survive
across runs, or the system relearns everything each time.  This module
persists each plane to an append-only JSONL store and reloads it, keeping
the same discipline the in-memory stores enforce: records are appended,
never rewritten, and objects rebuild byte-faithfully from their own
serialization (the round-trip is a test).

Everything here is content-preserving and deterministic - no timestamps or
randomness are minted here (an object that needs a timestamp carries one it
was given), so a reloaded store is identical to the one that wrote it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ..strings.notes import Note, NoteStore


def append_record_as_loop(path, kind: str, record, *, ledger=None):
    """EVERY PERSISTENCE WRITE IS A LOOP (owner, 2026-08-24).

    Appending to a durable store crosses a boundary, so it crosses through an
    envelope: deterministic, one accepted success, recorded.  The append's own
    append-only semantics are unchanged — this adds the crossing, not new
    authority."""
    from ..loop.encapsulate import as_practitioner_loop
    return as_practitioner_loop(f"persist {kind}",
                                lambda: append_record(path, kind, record),
                                ledger=ledger)["value"]


def append_record(path: str | Path, kind: str, record: Mapping[str, Any]
                  ) -> None:
    """Append one typed record as a JSONL line.  The record-kind lives under the
    reserved key ``_rk`` so it never collides with a field named ``kind`` in the
    record itself (a Note, for example, has its own ``kind``)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"_rk": kind, **dict(record)},
                                ensure_ascii=False, default=str) + "\n")


def read_records(path: str | Path, kind: str | None = None) -> list[dict]:
    """Read all records (optionally of one record-kind) from a JSONL store."""
    p = Path(path)
    if not p.exists():
        return []
    out: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if kind is None or rec.get("_rk") == kind:
            out.append(rec)
    return out


# --- notes ---------------------------------------------------------------
def persist_note(path: str | Path, note: Note) -> None:
    append_record(path, "note", note.to_dict())


def _note_from_dict(d: Mapping[str, Any]) -> Note:
    return Note(id=d["id"], template_id=d["template_id"], kind=d["kind"],
                author=d["author"], fields=dict(d.get("fields", {})),
                free_text=d.get("free_text", ""),
                refs=tuple(d.get("refs", ())), status=d.get("status",
                                                            "personal"),
                weight=float(d.get("weight", 0.0)),
                review=dict(d.get("review", {})),
                created_ts=d.get("created_ts", ""))


def load_notes(path: str | Path) -> NoteStore:
    """Rebuild a NoteStore from its append-only log — the LAST record per note id
    wins (status advances are appended), preserving the promotion history."""
    store = NoteStore()
    latest: dict[str, Note] = {}
    order: list[str] = []
    for rec in read_records(path, "note"):
        note = _note_from_dict(rec)
        if note.id not in latest:
            order.append(note.id)
        latest[note.id] = note
    for nid in order:
        note = latest[nid]
        if note.status in ("institutional", "published"):
            store.institutional[nid] = note
        else:
            store.personal[nid] = note
        store.history.append({"event": "load", "note": nid,
                             "status": note.status})
    return store


# ---------------------------------------------------------------------------
# Self-test — deterministic, uses a temp dir, no model, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    import tempfile
    from ..strings.notes import NoteTemplate, fill_note

    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    tmp = Path(tempfile.mkdtemp(prefix="wn-persist-"))

    # Notes round-trip, including a promotion (personal -> institutional).
    tmpl = NoteTemplate("t.exp", "experiment_sheet",
                        required_fields=("hypothesis", "result"))
    note = fill_note(tmpl, "practitioner",
                     {"hypothesis": "leakage", "result": "cv dropped"},
                     free_text="validation matters", refs=("log://r4",))
    npath = tmp / "notes.jsonl"
    persist_note(npath, note)                       # personal
    from dataclasses import replace
    persist_note(npath, replace(note, status="institutional", weight=0.7))
    nstore = load_notes(npath)
    check("notes_round_trip_and_the_latest_status_wins",
          note.id in nstore.institutional
          and nstore.institutional[note.id].weight == 0.7
          and nstore.institutional[note.id].fields["hypothesis"] == "leakage",
          "a note persisted personal then institutional reloads as "
          "institutional (the latest appended status wins), fields intact - "
          "append-only history preserved on disk")

    # Append-only: a second write adds a record, never replaces.
    persist_note(npath, note)
    check("stores_are_append_only",
          len(read_records(npath, "note")) == 3,
          "writing a record again appends a third line rather than replacing - "
          "the store is append-only on disk")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "persistence_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
