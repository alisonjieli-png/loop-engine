"""Record types for the private conversation-mining index.

Everything this module writes is local-only evidence for internal idea
generation. A record here is not a candidate, a lead, a review, an admission
or a publication; it is a pointer back to where an owner said something, so a
planner can turn owner direction into search queries and interrogation seeds.

Record types:
- ``owner_signal_record/v2``: one extracted owner-intent line with its
  source location, the phrases it yielded, and the dimensions it maps to.
- ``conversation_mining_run/v1``: one mining run over a set of transcript
  files: files read, rows emitted, refusals, and the sensitive-content
  drops the guards made.

Privacy rules this module enforces on every write:
- Extracted text passes the same ``words()`` normalisation and secret-pattern
  screen the query multiplier uses before it is stored.
- A source path may be an absolute local path; it is never a URL and never
  leaves the machine.
- Nothing here calls a network, writes outside ``--root``, or stages a
  candidate.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

SIGNAL_RECORD = "owner_signal_record/v2"
RUN_RECORD = "conversation_mining_run/v1"

#: The kinds of owner intent this miner recognises. Intent is the owner's own
#: words; a request is a demand; a pain is a complaint about a tool or result;
#: a reference names a product, repository or link to investigate.
INTENT_KINDS = ("request", "pain", "preference", "decision", "reference")

#: Where a line was found. Local files only, identified by an opaque locator
#: that never leaves the filesystem.
SOURCES = ("claude_code_jsonl", "codex_rollout_jsonl", "chatgpt_export_json", "prompt_log_text")

_ID = re.compile(r"[a-z][a-z0-9_]{0,47}\Z")
_LOCATOR = re.compile(r"[A-Za-z0-9][A-Za-z0-9/_.@:-]{0,199}\Z")


class ConversationMiningError(ValueError):
    """A record that fails its own shape. The caller refuses the whole batch."""


def _require(condition, code):
    if not condition:
        raise ConversationMiningError(code)


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


@dataclass(frozen=True)
class Signal:
    """One extracted owner-intent line, normalised and screened."""
    source: str            # one of SOURCES
    locator: str           # opaque local file/session identifier
    intent: str            # one of INTENT_KINDS
    phrases: tuple         # normalised phrases that passed the screen
    dimensions: tuple      # multiplier dimension ids this signal maps to
    weight: int            # repetition weight; more = stronger demand
    recorded_at: str       # Source time, or mining time when the source is undated
    references: tuple = ()

    def record(self) -> dict:
        _require(self.source in SOURCES, "signal_source_unknown")
        _require(type(self.locator) is str and _LOCATOR.fullmatch(self.locator), "signal_locator_invalid")
        _require(self.intent in INTENT_KINDS, "signal_intent_unknown")
        _require(isinstance(self.phrases, tuple) and all(type(p) is str and p for p in self.phrases),
                 "signal_phrases_invalid")
        _require(isinstance(self.dimensions, tuple) and all(type(d) is str and _ID.fullmatch(d) for d in self.dimensions), "signal_dimension_invalid")
        _require(type(self.weight) is int and 1 <= self.weight <= 1000, "signal_weight_range")
        _require(type(self.recorded_at) is str and self.recorded_at, "signal_time_missing")
        from knowledge_radar.query_matrix import SECRET_PATTERNS, words
        from knowledge_radar.community_intake import public_url
        phrases = tuple(words(value) for value in self.phrases)
        _require(isinstance(self.references, tuple), "signal_references_invalid")
        references = tuple(public_url(value) for value in self.references)
        _require(not any(pattern.search(value) for value in references for pattern in SECRET_PATTERNS),
                 "signal_reference_sensitive")
        _require(bool(phrases or references), "signal_empty")
        rec = {"record_type": SIGNAL_RECORD, "source": self.source, "locator": self.locator,
               "intent": self.intent, "phrases": sorted(set(phrases)), "references": sorted(set(references)),
               "dimensions": sorted(set(self.dimensions)), "weight": self.weight,
               "recorded_at": self.recorded_at}
        rec["signal_digest"] = _digest({k: v for k, v in rec.items()})
        return rec


def read_signal(value):
    """Validate the current record and its digest; preserve old indexes without auto-reading them."""
    fields = {"record_type", "source", "locator", "intent", "phrases", "references", "dimensions",
              "weight", "recorded_at", "signal_digest"}
    _require(type(value) is dict and set(value) == fields and value["record_type"] == SIGNAL_RECORD,
             "signal_shape_or_version")
    _require(all(type(value[k]) is list for k in ("phrases", "references", "dimensions")), "signal_lists_invalid")
    checked = Signal(value["source"], value["locator"], value["intent"], tuple(value["phrases"]),
                     tuple(value["dimensions"]), value["weight"], value["recorded_at"], tuple(value["references"])).record()
    _require(checked == value, "signal_digest_or_normalization")
    return checked


@dataclass(frozen=True)
class RunRecord:
    """One mining run: what was read, what was produced, what was refused."""
    run_id: str
    files_read: tuple
    signals_emitted: int
    sensitive_dropped: int
    phrases_emitted: int
    dimensions_touched: tuple
    started_at: str
    finished_at: str
    read_errors: int = 0
    timestamp_excluded: int = 0
    truncated_turns: int = 0
    capped_files: int = 0

    def record(self) -> dict:
        _require(type(self.run_id) is str and self.run_id, "run_id_missing")
        _require(isinstance(self.files_read, tuple), "run_files_invalid")
        _require(self.signals_emitted >= 0 and self.phrases_emitted >= 0 and self.sensitive_dropped >= 0,
                 "run_counts_negative")
        _require(all(type(value) is int and value >= 0 for value in
                     (self.read_errors, self.timestamp_excluded, self.truncated_turns, self.capped_files)),
                 "run_exclusion_counts_invalid")
        _require(all(_ID.match(d) for d in self.dimensions_touched), "run_dimension_invalid")
        rec = {"record_type": RUN_RECORD, "run_id": self.run_id, "files_read": sorted(self.files_read),
               "signals_emitted": self.signals_emitted, "sensitive_dropped": self.sensitive_dropped,
               "phrases_emitted": self.phrases_emitted, "dimensions_touched": sorted(set(self.dimensions_touched)),
               "started_at": self.started_at, "finished_at": self.finished_at,
               "read_errors": self.read_errors, "timestamp_excluded": self.timestamp_excluded,
               "truncated_turns": self.truncated_turns, "capped_files": self.capped_files}
        rec["run_digest"] = _digest({k: v for k, v in rec.items()})
        return rec
