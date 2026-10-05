"""The decision ledger: one canonical, append-only record of every complete generated batch decision.

```text
Decision ledger (one JSON-lines file that every sampled review reads)
├── line 1   generated_batch_decision_ledger/v1: the header that makes a file a decision ledger
└── line 2+  generated_batch_decision_entry/v1: one complete batch decision each, in recorded order
    ├── sequence, and the SHA-256 of the line before it, so a changed, removed or reordered line breaks the
    │   chain at the line after it; the review record of the run that appended the last line keeps the
    │   ledger's digest after that append
    ├── batch, generator (supply line and generator version, at any code revision) and outcome
    ├── decision: the generated_batch_sampling_decision/v1 the written rule returned, as the review kept it
    ├── plan: batch size, sample size, acceptance number, mode and policy digest
    ├── frame: the exact qualified population: its digest, size and qualifier revision, and for a withheld
    │   batch every member as identity, store version and package digest
    └── source: the review run (seed, start, reviewer, producer family, review record) and its qualification
```

The acceptance rule's guarantee is about one sampled review of one population: a batch with 5 percent or more
defective components is accepted with probability at most 5 percent. While the defect history was an optional
file, a withheld batch could be sampled again with a fresh seed and planned as if its generator had no record,
and each new sample was another such chance, so repeated sampling of a batch near the tolerance would
eventually pass. A sampled review therefore reads this ledger, and a review that may call a model cannot run
without it:

- before any model call it refuses a missing ledger, a file that is not one, and a ledger that does not read
  exactly: a torn last line, an unknown record or field, a broken chain, or withheld members that do not hash
  to their frame's digest;
- it refuses every selected batch whose exact frame already has a complete decision, and every batch that
  holds a component (by identity or by package digest) of a withheld frame;
- its plans read each generator's history from the ledger, so a recorded defect rate sets the sample size of
  that generator's later batches at any code revision;
- it holds the ledger's exclusive lock from that check until its decisions are appended in one synced write,
  so two runs never sample one frame at once.

A complete decision is one an admissible review made about a batch its reviewer was asked about: the reviewer
passed both calibrations in the same run, the run was not a measurement, and the written rule decided the
batch, whatever its outcome and whatever withheld it. A batch the run stopped before (no call of its own, and
none of its sampled components answered in the mixed calibration batch) learned nothing about its components
and stays undecided. A decided frame proceeds only through a full review of every component or after the
generator changes so the frame differs; the sampled review never samples it again. Nothing here calls a model
or reads the import store, and the only file it writes is the ledger it is given.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path

from tools.candidate_review.records import SHA256, canonical_bytes

from . import sampling

HEADER_RECORD = "generated_batch_decision_ledger/v1"
ENTRY_RECORD = "generated_batch_decision_entry/v1"
HEADER_FIELDS = ("record_type", "created_at", "created_by")
ENTRY_FIELDS = ("record_type", "sequence", "previous_sha256", "recorded_at", "batch", "generator", "outcome",
                "decision", "plan", "frame", "source")
PLAN_FIELDS = ("batch_size", "sample_size", "acceptance_number", "mode", "policy_sha256")
FRAME_FIELDS = ("sha256", "size", "qualifier", "members")
QUALIFIER_FIELDS = ("tool", "version", "code_revision", "uncommitted_changes")
SOURCE_FIELDS = ("kind", "review", "review_sha256", "review_record_type", "seed", "started_at", "reviewer",
                 "producer_family", "qualification", "qualification_sha256")
#: Who wrote an entry: the sampled review run that decided the batch, or the backfill from its review record.
RUN_SOURCE, BACKFILL_SOURCE = "sampled_review_run", "backfill"
OUTCOMES = (sampling.ACCEPTED, sampling.WITHHELD)
PLAN_MODES = (sampling.ZERO_ACCEPTANCE, sampling.OBSERVED_RATE, sampling.EVERY_COMPONENT,
              sampling.GENERATOR_ABOVE_TOLERANCE)
#: The fields of a decision the ledger reads, with the type each must have.
DECISION_TYPES = {"batch": str, "outcome": str, "reasons": list, "sampled": int, "decided": int, "defective": int,
                  "sample_complete": bool, "acceptance_number": int, "decided_at": str, "run_id": str}
BACKFILL_CREATOR = "tools/qualify_generated_components.py decisions-backfill"


class DecisionLedgerError(ValueError):
    """A stable refusal code and an operator message; nothing was sampled, called or written."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def refuse(code: str, message: str):
    raise DecisionLedgerError(code, message)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _exact(value, name: str, fields) -> dict:
    if type(value) is not dict:
        refuse("decision_ledger_row_invalid", f"{name} must be a JSON object")
    unknown, missing = sorted(set(value) - set(fields)), sorted(set(fields) - set(value))
    if unknown or missing:
        refuse("decision_ledger_row_invalid", f"{name} carries unknown fields {unknown} or lacks {missing}")
    return value


def _text(value, name: str) -> str:
    if type(value) is not str or not value.strip():
        refuse("decision_ledger_row_invalid", f"{name} must be text")
    return value


def _count(value, name: str, low: int = 0) -> int:
    if type(value) is not int or value < low:
        refuse("decision_ledger_row_invalid", f"{name} must be a whole number of at least {low}")
    return value


def _digest(value, name: str, *, empty: bool = False) -> "str | None":
    if empty and value is None:
        return None
    if type(value) is not str or SHA256.fullmatch(value) is None:
        refuse("decision_ledger_row_invalid", f"{name} must be a SHA-256 digest")
    return value


def read_header(value) -> dict:
    if type(value) is not dict or value.get("record_type") != HEADER_RECORD:
        refuse("decision_ledger_not_a_ledger", f"the first line is not a {HEADER_RECORD} header")
    header = _exact(value, "the ledger header", HEADER_FIELDS)
    _text(header["created_at"], "created_at")
    _text(header["created_by"], "created_by")
    return header


def read_entry(value, *, sequence: int, previous_sha256: str) -> dict:
    """One entry, exactly as the writer must have written it; every inconsistency refuses the whole ledger."""
    entry = _exact(value, f"ledger entry {sequence}", ENTRY_FIELDS)
    if entry["record_type"] != ENTRY_RECORD:
        refuse("decision_ledger_row_invalid", f"ledger entry {sequence} is not a {ENTRY_RECORD}")
    if entry["sequence"] != sequence or type(entry["sequence"]) is not int:
        refuse("decision_ledger_chain_broken", f"line {sequence + 1} holds sequence {entry['sequence']!r}")
    if entry["previous_sha256"] != previous_sha256:
        refuse("decision_ledger_chain_broken", f"entry {sequence} does not follow the line before it")
    _text(entry["recorded_at"], "recorded_at")
    batch = _text(entry["batch"], "batch")
    if entry["generator"] != sampling.generator_of(batch):
        refuse("decision_ledger_row_invalid", f"entry {sequence} names a generator its batch does not")
    if entry["outcome"] not in OUTCOMES:
        refuse("decision_ledger_row_invalid", f"entry {sequence} has an outcome other than {list(OUTCOMES)}")
    plan = _exact(entry["plan"], "plan", PLAN_FIELDS)
    size = _count(plan["batch_size"], "batch_size", 1)
    sample_size = _count(plan["sample_size"], "sample_size", 1)
    if sample_size > size or plan["mode"] not in PLAN_MODES:
        refuse("decision_ledger_row_invalid", f"entry {sequence} has a plan outside its batch")
    _count(plan["acceptance_number"], "acceptance_number")
    _digest(plan["policy_sha256"], "policy_sha256")
    decision = entry["decision"]
    if type(decision) is not dict or decision.get("record_type") != sampling.DECISION_RECORD or any(
            type(decision.get(name)) is not kind for name, kind in DECISION_TYPES.items()):
        refuse("decision_ledger_row_invalid", f"entry {sequence} does not hold a {sampling.DECISION_RECORD}")
    if (decision["batch"], decision["outcome"], decision["sampled"], decision["acceptance_number"]) != (
            batch, entry["outcome"], sample_size, plan["acceptance_number"]) or not (
            0 <= decision["defective"] <= decision["decided"] <= decision["sampled"]) or (
            decision["sample_complete"] != (decision["decided"] == decision["sampled"])):
        refuse("decision_ledger_row_invalid", f"entry {sequence}'s decision disagrees with its batch and plan")
    _read_frame(entry["frame"], entry["outcome"], size, sequence)
    source = _exact(entry["source"], "source", SOURCE_FIELDS)
    if source["kind"] not in (RUN_SOURCE, BACKFILL_SOURCE) or source["review_record_type"] != sampling.REVIEW_RECORD:
        refuse("decision_ledger_row_invalid", f"entry {sequence} names an unknown source")
    _digest(source["review_sha256"], "review_sha256", empty=source["kind"] == RUN_SOURCE)
    _digest(source["qualification_sha256"], "qualification_sha256")
    for name in ("review", "seed", "started_at", "reviewer", "producer_family", "qualification"):
        _text(source[name], name)
    return entry


def _read_frame(value, outcome: str, size: int, sequence: int) -> dict:
    frame = _exact(value, "frame", FRAME_FIELDS)
    digest = _digest(frame["sha256"], "frame sha256")
    if frame["size"] != size:
        refuse("decision_ledger_row_invalid", f"entry {sequence}'s frame size differs from its batch size")
    qualifier = _exact(frame["qualifier"], "qualifier", QUALIFIER_FIELDS)
    for name in ("tool", "version", "code_revision"):
        _text(qualifier[name], name)
    if qualifier["uncommitted_changes"] is not False:
        refuse("decision_ledger_row_invalid", f"entry {sequence}'s frame names an uncommitted qualifier")
    members = frame["members"]
    if outcome == sampling.ACCEPTED:
        if members is not None:
            refuse("decision_ledger_row_invalid", f"entry {sequence} lists members for an accepted frame")
        return frame
    if type(members) is not list or len(members) != size or any(
            type(row) is not list or len(row) != 3 or not all(type(part) is str and part for part in row)
            for row in members):
        refuse("decision_ledger_frame_invalid", f"entry {sequence} must list each withheld member exactly")
    if members != sorted(members) or len({row[0] for row in members}) != size or _members_digest(members) != digest:
        refuse("decision_ledger_frame_invalid", f"entry {sequence}'s members do not hash to its frame digest")
    return frame


def _members_digest(members) -> str:
    """The frame digest of member rows, exactly as ``sampling.frame_digest`` computes it from records."""
    return _sha256(json.dumps(members, separators=(",", ":")).encode())


def decision_key(entry: dict) -> tuple:
    """What makes two entries the same decision: one review run's verdict on one frame."""
    source = entry["source"]
    return (source["seed"], source["started_at"], entry["batch"], entry["frame"]["sha256"],
            entry["decision"]["run_id"])


def _write_all(descriptor: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        view = view[os.write(descriptor, view):]


def _read_all(descriptor: int) -> bytes:
    size, chunks, offset = os.fstat(descriptor).st_size, [], 0
    while offset < size:
        chunk = os.pread(descriptor, size - offset, offset)
        if not chunk:
            break
        chunks.append(chunk)
        offset += len(chunk)
    return b"".join(chunks)


def create(path, *, created_at: str, created_by: str) -> None:
    """Write a new ledger that holds only its header; an existing file is never replaced."""
    line = canonical_bytes(read_header({"record_type": HEADER_RECORD, "created_at": created_at,
                                        "created_by": created_by})) + b"\n"
    try:
        descriptor = os.open(Path(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o644)
    except FileExistsError:
        refuse("decision_ledger_exists", f"{path} exists; a ledger is created once and then only appended to")
    try:
        _write_all(descriptor, line)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class DecisionLedger:
    """One ledger file, read and checked whole. Opened for append, it holds the file's exclusive lock until
    closed, and appends are one write, synced before the append returns."""

    def __init__(self, path: Path, descriptor: int, writable: bool, data: bytes) -> None:
        self.path, self._descriptor, self.writable = Path(path), descriptor, writable
        self.header, self.entries, self._data = None, [], b""
        self._by_frame, self._withheld_identity, self._withheld_digest, self.keys = {}, {}, {}, set()
        self._last_sha256 = ""
        self._load(data)

    @classmethod
    def open(cls, path, *, for_append: bool) -> "DecisionLedger":
        path = Path(path)
        if path.is_symlink():
            refuse("decision_ledger_unsafe", f"{path} is a link; the ledger is read and appended only as itself")
        if not path.is_file():
            refuse("decision_ledger_missing", f"no decision ledger at {path}; create it with decisions-backfill")
        try:
            descriptor = os.open(path, (os.O_RDWR | os.O_APPEND if for_append else os.O_RDONLY)
                                 | getattr(os, "O_NOFOLLOW", 0))
        except OSError as error:
            refuse("decision_ledger_unreadable", f"{path} cannot be opened: {error.strerror}")
        try:
            if for_append:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    refuse("decision_ledger_busy", f"another sampled review or backfill holds {path}")
            ledger = cls(path, descriptor, for_append, _read_all(descriptor))
        except BaseException:
            os.close(descriptor)
            raise
        if not for_append:
            os.close(descriptor)
            ledger._descriptor = None
        return ledger

    def close(self) -> None:
        if self._descriptor is not None:
            os.close(self._descriptor)  # closing the descriptor releases the lock
            self._descriptor = None

    def __enter__(self) -> "DecisionLedger":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    @property
    def sha256(self) -> str:
        return _sha256(self._data)

    def _load(self, data: bytes) -> None:
        if not data:
            refuse("decision_ledger_not_a_ledger", f"{self.path} is empty; a decision ledger begins with its header")
        if not data.endswith(b"\n"):
            refuse("decision_ledger_truncated", "the last ledger line was not completed; inspect the ledger "
                                                "before any sampled review runs")
        for number, line in enumerate(data[:-1].split(b"\n"), 1):
            try:
                value = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                refuse("decision_ledger_not_a_ledger" if number == 1 else "decision_ledger_row_unreadable",
                       f"line {number} of {self.path} is not JSON")
            if number == 1:
                self.header = read_header(value)
            if canonical_bytes(value) != line:
                refuse("decision_ledger_row_unreadable", f"line {number} is not in the ledger's canonical form")
            if number > 1:
                self._index(read_entry(value, sequence=number - 1, previous_sha256=self._last_sha256))
            self._last_sha256 = _sha256(line)
        self._data = data

    def _index(self, entry: dict) -> None:
        self.entries.append(entry)
        self.keys.add(decision_key(entry))
        self._by_frame.setdefault(entry["frame"]["sha256"], []).append(entry)
        for identity, _version, digest in entry["frame"]["members"] or ():
            self._withheld_identity.setdefault(identity, entry)
            self._withheld_digest.setdefault(digest, entry)

    def history_rows(self) -> list:
        """Every recorded decision as ``GeneratorHistory.from_decisions`` reads it, keyed by its generator."""
        return [{"generator": entry["generator"], "sample_complete": entry["decision"]["sample_complete"],
                 "sampled": entry["decision"]["sampled"], "defective": entry["decision"]["defective"]}
                for entry in self.entries]

    def summary(self, policy: "sampling.SamplingPolicy | None" = None) -> dict:
        """What the ledger holds, for an operator's report: each decision, and each generator's recorded history
        with the observed rate the plan reads (None while the history is shorter than the policy's minimum)."""
        policy, rows = policy or sampling.SamplingPolicy(), self.history_rows()
        generators = {}
        for generator in sorted({entry["generator"] for entry in self.entries}):
            history = sampling.GeneratorHistory.from_decisions(generator, rows)
            rate = history.observed_rate(policy)
            generators[generator] = {"batches_with_complete_samples": history.batches, "sampled": history.sampled,
                                     "defective": history.defective, "observed_rate": rate,
                                     "at_or_above_tolerance": rate is not None
                                     and rate >= policy.tolerance_defect_rate}
        return {"ledger": str(self.path), "sha256": self.sha256, "entries": len(self.entries),
                "decisions": [{"sequence": entry["sequence"], "batch": entry["batch"], "outcome": entry["outcome"],
                               "frame_size": entry["frame"]["size"], "sampled": entry["decision"]["sampled"],
                               "decided": entry["decision"]["decided"], "defective": entry["decision"]["defective"],
                               "decided_at": entry["decision"]["decided_at"]} for entry in self.entries],
                "generators": generators}

    def refusals(self, frames: dict) -> dict:
        """Batch to the reasons it may not be sampled: its exact frame was decided, or it holds a component of
        a withheld frame. ``frames`` maps each batch to its qualification records."""
        refused = {}
        for batch, records in sorted(frames.items()):
            reasons, exact = [], self._by_frame.get(sampling.frame_digest(records), [])
            for entry in exact:
                reasons.append(f"its exact frame was {entry['outcome']} on {entry['decision']['decided_at']} "
                               f"(ledger entry {entry['sequence']})")
            shared, settled = {}, {entry["sequence"] for entry in exact}
            for record in records:
                for entry in (self._withheld_identity.get(record["identity"]),
                              self._withheld_digest.get(record["package_digest"])):
                    if entry is not None and entry["sequence"] not in settled:
                        shared.setdefault(entry["sequence"], (entry, set()))[1].add(record["identity"])
            for _sequence, (entry, identities) in sorted(shared.items()):
                reasons.append(f"{len(identities)} of its components were in the frame of {entry['batch']} "
                               f"withheld on {entry['decision']['decided_at']} (ledger entry {entry['sequence']})")
            if reasons:
                refused[batch] = reasons
        return refused

    def append(self, entries) -> dict:
        """Append complete decisions in one synced write; returns their sequences and the ledger's new digest."""
        if self._descriptor is None or not self.writable:
            refuse("decision_ledger_not_locked", "only a ledger opened for append, and still locked, is appended")
        if os.fstat(self._descriptor)[1:3] != os.stat(self.path, follow_symlinks=False)[1:3]:
            refuse("decision_ledger_replaced", f"{self.path} was replaced while this run held the ledger")
        if _read_all(self._descriptor) != self._data:
            refuse("decision_ledger_changed", f"{self.path} changed while this run held its lock")
        lines, previous, written = [], self._last_sha256, []
        for offset, entry in enumerate(entries):
            row = {**entry, "record_type": ENTRY_RECORD, "sequence": len(self.entries) + offset + 1,
                   "previous_sha256": previous}
            line = canonical_bytes(read_entry(row, sequence=row["sequence"], previous_sha256=previous))
            lines.append(line + b"\n")
            written.append(row)
            previous = _sha256(line)
        payload = b"".join(lines)
        _write_all(self._descriptor, payload)
        os.fsync(self._descriptor)
        self._data += payload
        self._last_sha256 = previous
        for row in written:
            self._index(row)
        return {"sequences": [row["sequence"] for row in written], "sha256": self.sha256,
                "entries": len(self.entries)}


def open_for_review(path, authorized: bool) -> "DecisionLedger | None":
    """The ledger a sampled review reads. A review that may call a model needs one and holds its lock."""
    if path is None:
        if authorized:
            refuse("decision_ledger_required", "a sampled review that may call a model needs the decision ledger "
                                               "(--decisions); without it a withheld batch could be sampled again "
                                               "and planned without its generator's recorded defect rate")
        return None
    return DecisionLedger.open(path, for_append=authorized)


def file_sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def entry_for(review: dict, batch: str, frame_records, *, kind: str, review_path, review_sha256: "str | None",
              qualification_sha256: str, recorded_at: str) -> dict:
    """The entry of one batch decision a review record holds, its frame rebuilt from the qualification records
    and checked against the digest the review bound. The sequence and chain are added when it is appended."""
    batch_entry = review["batches"][batch]
    decision, plan = batch_entry.get("decision") or {}, batch_entry["plan"]
    rows = sampling.frame_rows(frame_records)
    digest = _members_digest(rows)
    if digest != batch_entry.get("frame_sha256") or len(rows) != plan.get("batch_size"):
        refuse("frame_mismatch", f"{batch}: the qualification records do not rebuild the frame the review bound")
    qualifiers = {tuple(record["qualifier"].get(name) for name in QUALIFIER_FIELDS) for record in frame_records}
    if len(qualifiers) != 1:
        refuse("frame_mismatch", f"{batch}: the frame's records name more than one qualifier")
    return {"recorded_at": recorded_at, "batch": batch, "generator": sampling.generator_of(batch),
            "outcome": decision.get("outcome"), "decision": decision,
            "plan": {name: plan.get(name) for name in PLAN_FIELDS},
            "frame": {"sha256": digest, "size": len(rows), "qualifier": dict(zip(QUALIFIER_FIELDS, qualifiers.pop())),
                      "members": ([list(row) for row in rows] if decision.get("outcome") == sampling.WITHHELD
                                  else None)},
            "source": {"kind": kind, "review": str(review_path), "review_sha256": review_sha256,
                       "review_record_type": review.get("record_type"), "seed": review.get("seed"),
                       "started_at": review.get("started_at"), "reviewer": review.get("reviewer"),
                       "producer_family": review.get("producer_family"),
                       "qualification": str(review.get("qualification")),
                       "qualification_sha256": qualification_sha256}}


def _frames(path: Path, batches: set) -> tuple:
    """The qualified records of the named batches, and the qualification file's digest, in one streamed read."""
    frames, digest = {batch: [] for batch in batches}, hashlib.sha256()
    with open(path, "rb") as stream:
        for line in stream:
            digest.update(line)
            record = json.loads(line)
            if record.get("batch") in frames and record.get("outcome") == "qualified":
                frames[record["batch"]].append(record)
    return frames, digest.hexdigest()


def backfill(ledger_path, reviews, *, recorded_at: str, created_by: str = BACKFILL_CREATOR) -> dict:
    """Record the complete decisions of earlier sampled review records; create the ledger when it is absent.

    Each review is read with the qualification run its record names, and every frame is rebuilt from that
    run's records and checked against the digest the review bound, before anything is written. A review of
    version 1 binds no exact population and is refused. A decision counts only when its review was
    admissible; a run that stopped, measured or was not calibrated is listed as skipped with its reason.
    Decisions the ledger already holds are not appended again, so a second backfill writes nothing, and an
    existing ledger is only appended to."""
    candidates, skipped = [], []
    for review_path in map(Path, reviews):
        data = review_path.read_bytes()
        review = json.loads(data)
        if review.get("record_type") != sampling.REVIEW_RECORD:
            refuse("review_version_unsupported", f"{review_path} is {review.get('record_type')!r}; only "
                                                 f"{sampling.REVIEW_RECORD} binds the exact population it decided")
        decided = {batch for batch, entry in review["batches"].items()
                   if (entry.get("decision") or {}).get("outcome") in OUTCOMES}
        frames, qualification_sha256 = _frames(Path(review["qualification"]) / "qualification.jsonl", decided)
        for batch, entry in sorted(review["batches"].items()):
            if batch not in decided:
                skipped.append({"review": str(review_path), "batch": batch, "reason": "no batch decision"
                                + (f" (the run stopped: {review['stopped']})" if review.get("stopped") else "")})
            elif review.get("admissible") is not True:
                skipped.append({"review": str(review_path), "batch": batch, "reason": "not a complete decision: "
                                + "; ".join(review.get("admissibility_reasons") or ["the review is not admissible"])})
            else:
                candidates.append(entry_for(review, batch, frames[batch], kind=BACKFILL_SOURCE,
                                            review_path=review_path, review_sha256=_sha256(data),
                                            qualification_sha256=qualification_sha256, recorded_at=recorded_at))
    unique = {}
    for value in candidates:  # a review named twice is one review
        unique.setdefault(decision_key(value), value)
    candidates = sorted(unique.values(), key=lambda value: (value["decision"]["decided_at"], value["batch"]))
    for position, value in enumerate(candidates, 1):  # every entry is checked before any file is written
        read_entry({**value, "record_type": ENTRY_RECORD, "sequence": position, "previous_sha256": "0" * 64},
                   sequence=position, previous_sha256="0" * 64)
    created = not os.path.lexists(ledger_path)
    if created:
        create(ledger_path, created_at=recorded_at, created_by=created_by)
    with DecisionLedger.open(ledger_path, for_append=True) as ledger:
        fresh = [value for value in candidates if decision_key(value) not in ledger.keys]
        appended = ledger.append(fresh)
        return {"created": created,
                "appended": [{"sequence": sequence, "batch": value["batch"], "outcome": value["outcome"]}
                             for sequence, value in zip(appended["sequences"], fresh)],
                "already_recorded": len(candidates) - len(fresh), "skipped": skipped, **ledger.summary()}
