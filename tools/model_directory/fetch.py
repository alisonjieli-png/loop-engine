"""Restartable, cached and bounded reads of the directory's public sources.

Kind: development tool module. Every request goes through the repository's read-only transport
(`loop_engine.core.library_ingestion.https_transport`): GET only, declared hosts only, no redirect,
no credential, a request ceiling and a log of every request. On top of it this module keeps each
answer in a state folder with the moment it was read, so that:

- a run that stops, for a crash or a reached ceiling, continues where it stopped on the next run;
- an answer younger than its maximum age is reused instead of read again;
- a source that answers with an error keeps its previous answer, with its previous date, and the
  build records that the rows it feeds were kept rather than read today.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from loop_engine.core.library_ingestion.https_transport import HttpsGetTransport
from loop_engine.core.library_ingestion.request_log import (
    PauseExceedsBound, RequestBudget, RequestCeilingReached, RequestLog,
)

#: The only hosts the build reads. Ollama's hosts are absent on purpose: its terms refuse automated access.
HOSTS = ("openrouter.ai", "huggingface.co", "models.dev")
#: Seconds between two requests to one host, which keeps the build well inside each host's published limit.
PAUSE_SECONDS = {"huggingface.co": 0.7, "openrouter.ai": 0.25, "models.dev": 1.0}
READ, CACHED, KEPT, MISSING = "read", "cached", "kept", "missing"


@dataclass(frozen=True)
class Answer:
    """One source answer: the parsed value, the day its bytes were read, and how the build got it."""

    value: object
    read_on: str
    state: str
    address: str

    @property
    def usable(self) -> bool:
        return self.value is not None


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CachedReader:
    """JSON reads through the bounded transport, kept in a state folder between runs."""

    def __init__(self, state: Path, *, maximum_requests: int, offline: bool = False, transport=None,
                 clock=time.monotonic, sleep=time.sleep) -> None:
        self.state = Path(state)
        (self.state / "raw").mkdir(parents=True, exist_ok=True)
        self.log = RequestLog(self.state / "requests.jsonl")
        self.budget = RequestBudget(maximum_requests=maximum_requests, maximum_pause_seconds=1800.0)
        self.transport = transport or HttpsGetTransport(HOSTS, self.budget, self.log, timeout_seconds=90.0,
                                                        maximum_bytes=96 * 1024 * 1024)
        self.offline = offline
        self.stopped = ""
        self.counts = {READ: 0, CACHED: 0, KEPT: 0, MISSING: 0}
        self._clock, self._sleep, self._last = clock, sleep, {}

    def _file(self, host: str, path: str, pairs: list) -> Path:
        key = hashlib.sha256(json.dumps([host, path, pairs]).encode()).hexdigest()
        return self.state / "raw" / host / (key + ".json")

    def get_json(self, host: str, path: str, query=None, *, maximum_age_hours: float = 20.0) -> Answer:
        """The parsed JSON at one address, read now or reused, and the day it was read.

        query is a mapping or a list of (name, value) pairs; a list repeats a name, as the Hugging Face
        Hub API needs for its expand[] fields.
        """
        pairs = [list(item) for item in (query.items() if isinstance(query, dict) else (query or []))]
        address = host + path + ("?" + urlencode([tuple(pair) for pair in pairs]) if pairs else "")
        cache = self._file(host, path, pairs)
        kept = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else None
        if kept is not None:
            age = (_now() - datetime.fromisoformat(kept["read_at"])).total_seconds() / 3600
            if age <= maximum_age_hours or self.offline or self.stopped:
                return self._count(Answer(kept["value"], kept["read_at"][:10], CACHED, address))
        elif self.offline or self.stopped:
            return self._count(Answer(None, "", MISSING, address))
        wait = PAUSE_SECONDS.get(host, 1.0) - (self._clock() - self._last.get(host, -1e9))
        if wait > 0:
            self._sleep(wait)
        try:
            response = self.transport.get(host, path, [tuple(pair) for pair in pairs] or None)
        except (RequestCeilingReached, PauseExceedsBound) as error:
            self.stopped = type(error).__name__
            response = None
        self._last[host] = self._clock()
        value = None
        if response is not None and response.status == 200:
            try:
                value = json.loads(response.body.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                value = None
        if value is not None:
            read_at = _now().replace(microsecond=0).isoformat()
            cache.parent.mkdir(parents=True, exist_ok=True)
            partial = cache.with_suffix(".partial")
            partial.write_text(json.dumps({"address": address, "read_at": read_at, "value": value}), encoding="utf-8")
            partial.replace(cache)
            return self._count(Answer(value, read_at[:10], READ, address))
        if kept is not None:
            return self._count(Answer(kept["value"], kept["read_at"][:10], KEPT, address))
        return self._count(Answer(None, "", MISSING, address))

    def _count(self, answer: Answer) -> Answer:
        self.counts[answer.state] += 1
        return answer

    def summary(self) -> dict:
        return {"answers": dict(self.counts), "requests": self.log.summary(), "stopped_by": self.stopped or None}
