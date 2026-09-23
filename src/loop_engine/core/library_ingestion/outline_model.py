"""Engine model_outline of the library_outline engine slot, through Ollama Cloud.

It asks one model for one sentence that states the purpose of a source text
in the model's own words, then refuses the sentence if it repeats any run
of five words from the source. Every call is recorded as
library_model_call/v1 with the model asked for and the model that answered,
the route, the digest of the prompt, the provider-reported token usage
(unknown stays unknown, never zero) and the outcome. Given a record path,
the engine appends each record there the moment the call returns, so a run
that stops halfway still leaves the record of every call it made. A 429 answer with a
stated wait pauses within a declared total and is tried once more. The
engine stops before its declared call ceiling; the pipeline then uses the
deterministic engine for the rest and records why. It is eligible only with
explicit model authority, a named model and a positive ceiling. The key is
read by core.ollama_client at call time and never reaches a record.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .candidates import OUTLINE_RECORD_TYPE, read_outline
from .outline_deterministic import copies_source
from .record_rules import bytes_digest, canonical_digest, now_utc
from .rendering_types import RenderRefused
from .topics import topic_words

MODEL_CALL_RECORD_TYPE = "library_model_call/v1"
ROUTE = "ollama_cloud:/api/chat"
SYSTEM = "You describe what a text is for, in one plain sentence of your own words."
PROMPT = ("State in one sentence of at most 40 words what task the text below helps an AI coding "
          "assistant do. Use your own words; do not quote the text. Reply with the sentence only.\n\n")
EXCERPT_CHARACTERS = 6000
_KIND_WORDS = {"skill": "skill", "instruction_file": "instruction file", "tool": "connection file"}


class CallCeilingReached(RuntimeError):
    """The declared model call ceiling would be exceeded; no call was made."""


class OutlineCallFailed(RuntimeError):
    """The model call did not return a usable sentence; the reason is recorded."""


def _chat():
    from ..ollama_client import chat

    return chat


class ModelOutline:
    """One model call per outline, recorded, bounded and checked against the source."""

    engine_id = "model_outline"
    engine_version = "1.0.0"
    engine_kind = "outline_writer"
    effects = ("network",)
    third_party = "Ollama Cloud chat interface through core.ollama_client"

    def __init__(self, model: str, call_ceiling: int, *, maximum_pause_seconds: float = 120.0,
                 chat=None, sleep=time.sleep, record_path=None) -> None:
        self.model, self.call_ceiling = model, call_ceiling
        self.maximum_pause_seconds, self.paused = maximum_pause_seconds, 0.0
        self.chat, self.sleep = chat or _chat(), sleep
        self.record_path = None if record_path is None else Path(record_path)
        self.calls: list = []

    @classmethod
    def availability(cls, settings: dict):
        if settings.get("model_calls_authorized") is not True:
            return False, "authority_missing"
        if not settings.get("outline_model") or int(settings.get("model_call_ceiling") or 0) <= 0:
            return False, "not_configured"
        return True, "available"

    @classmethod
    def from_settings(cls, settings: dict, resources: dict):
        """Construct from declared settings and the run's resources; nothing starts here."""
        return cls(settings["outline_model"], int(settings["model_call_ceiling"]),
                   maximum_pause_seconds=float(settings.get("maximum_pause_seconds") or 120.0),
                   record_path=settings.get("model_call_log") or None)

    def describe(self) -> dict:
        return {"engine_id": self.engine_id, "engine_version": self.engine_version, "model": self.model,
                "route": ROUTE, "call_ceiling": self.call_ceiling, "calls": len(self.calls)}

    def _record(self, prompt: str, source_digest: str, started: str, elapsed: float, result,
                outcome: str) -> dict:
        # Only a response names the model that answered; a refused or failed call names none.
        answered = getattr(result, "model", None) if getattr(result, "response_received", False) else None
        row = {"record_type": MODEL_CALL_RECORD_TYPE, "sequence": len(self.calls) + 1,
               "engine_id": self.engine_id, "model_requested": self.model,
               "model_reported": answered or None, "route": ROUTE,
               "prompt_digest": bytes_digest(prompt.encode("utf-8")), "source_digest": source_digest,
               "started_at": started, "elapsed_ms": round(elapsed, 1),
               "usage": {"prompt_tokens": getattr(result, "prompt_tokens", None),
                         "completion_tokens": getattr(result, "eval_tokens", None)},
               "usage_reported": bool(getattr(result, "usage_reported", False)), "outcome": outcome,
               "error_class": (getattr(result, "error", "") or "").split(":")[0][:80]}
        row["call_digest"] = canonical_digest(row)
        self.calls.append(row)
        if self.record_path is not None:
            with self.record_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
        return row

    def _call(self, prompt: str, source_digest: str):
        if len(self.calls) >= self.call_ceiling:
            raise CallCeilingReached(f"the declared ceiling of {self.call_ceiling} model calls is reached")
        started, clock = now_utc(), time.monotonic()
        result = self.chat(prompt, model=self.model, system=SYSTEM, temperature=0.2, timeout=180.0)
        outcome = "ok" if result.ok else ("rate_limited" if str(result.error).startswith("HTTP 429")
                                          else "error")
        return result, self._record(prompt, source_digest, started, (time.monotonic() - clock) * 1000,
                                    result, outcome)

    def outline(self, candidate: dict, source_text: str) -> dict:
        prompt = PROMPT + source_text[:EXCERPT_CHARACTERS]
        source_digest = candidate["provenance"]["source_digest"]
        result, row = self._call(prompt, source_digest)
        rows = [row]
        wait = getattr(result, "retry_after_seconds", None)
        if row["outcome"] == "rate_limited" and wait is not None \
                and self.paused + wait <= self.maximum_pause_seconds:
            self.paused += wait
            self.sleep(wait)
            result, row = self._call(prompt, source_digest)
            rows.append(row)
        if not result.ok:
            raise OutlineCallFailed(row["outcome"])
        sentence = " ".join(str(result.text).strip().strip('"').split())[:300]
        if not sentence or copies_source(sentence, source_text):
            raise RenderRefused("outline_would_copy_source_text", "the model's sentence repeats the source")
        kind = _KIND_WORDS[candidate["kind"]]
        purpose = (f"{sentence} Write an original {kind} for this purpose; use no sentence, list or example "
                   "from the source.")
        record = {"record_type": OUTLINE_RECORD_TYPE,
                  "outline_key": canonical_digest({"candidate": candidate["candidate_key"],
                                                   "engine": self.engine_id, "model": self.model}),
                  "kind": candidate["kind"], "native_format": candidate["native_format"],
                  "source_name": candidate["name"][:128],
                  "topic_words": topic_words(candidate["name"], source_text[:4000]),
                  "abstract_purpose": purpose[:600], "provenance": candidate["provenance"],
                  "generator": {"engine_id": self.engine_id, "engine_version": self.engine_version},
                  "text_included": False, "model_calls": [item["call_digest"] for item in rows]}
        return read_outline(record)
