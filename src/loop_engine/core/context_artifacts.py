"""Digest-addressed storage and explicit context compaction.

Large tool output should not remain in an active model context. It also must
not disappear when a shorter representation is made. This module stores the
raw value first, returns a stable content reference, and optionally keeps a
small value inline. Compaction creates a second artifact that points back to
the unchanged raw artifact.

The built-in compactor is deterministic. Model-written summaries belong in a
non-deterministic Loop and must implement the same result contract.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from .runtime_observer import RuntimeObservationServices


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class ContextArtifactRef:
    """A stable reference to content stored by its SHA-256 digest."""

    digest: str
    byte_count: int
    media_type: str = "text/plain"
    encoding: str = "utf-8"
    artifact_kind: str = "raw_output"

    def __post_init__(self):
        if (len(self.digest) != 64
                or any(char not in "0123456789abcdef" for char in self.digest)):
            raise ValueError("artifact digest must be a lowercase SHA-256 value")
        if self.byte_count < 0:
            raise ValueError("artifact byte_count cannot be negative")
        if not self.media_type:
            raise ValueError("artifact media_type cannot be empty")
        if not self.artifact_kind:
            raise ValueError("artifact_kind cannot be empty")

    @property
    def object_key(self) -> str:
        """Return a portable key that does not expose the store root."""
        return f"sha256/{self.digest[:2]}/{self.digest}"

    def to_dict(self) -> dict:
        return {
            "digest": self.digest,
            "byte_count": self.byte_count,
            "media_type": self.media_type,
            "encoding": self.encoding,
            "artifact_kind": self.artifact_kind,
            "object_key": self.object_key,
        }

    @classmethod
    def from_dict(cls, value: dict) -> "ContextArtifactRef":
        return cls(
            digest=str(value["digest"]),
            byte_count=int(value["byte_count"]),
            media_type=str(value.get("media_type", "text/plain")),
            encoding=str(value.get("encoding", "utf-8")),
            artifact_kind=str(value.get("artifact_kind", "raw_output")),
        )


@dataclass(frozen=True)
class ContextArtifactStoreSpec:
    """Configuration for one local content-addressed artifact store."""

    root: str
    namespace: str = "context"

    def __post_init__(self):
        if not self.root:
            raise ValueError("an artifact store needs an explicit root")
        if not self.namespace or "/" in self.namespace or "\\" in self.namespace:
            raise ValueError("artifact namespace must be one path segment")


class ContextArtifactStore:
    """Store immutable context artifacts under an explicit local root."""

    def __init__(self, spec: ContextArtifactStoreSpec):
        self.spec = spec
        self._root = Path(spec.root).expanduser().resolve()
        self._objects = self._root / spec.namespace / "objects"
        self._objects.mkdir(parents=True, exist_ok=True)

    def put(self, value: bytes, *, media_type: str = "application/octet-stream",
            encoding: str = "binary", artifact_kind: str = "raw_output"
            ) -> ContextArtifactRef:
        """Store bytes once and return their stable content reference."""
        if not isinstance(value, bytes):
            raise TypeError("artifact value must be bytes")
        digest = _sha256(value)
        target = self._path_for_digest(digest)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            existing = target.read_bytes()
            if _sha256(existing) != digest:
                raise RuntimeError("an existing artifact failed digest validation")
        else:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{digest}.", dir=str(target.parent))
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(value)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary_name, target)
            finally:
                if os.path.exists(temporary_name):
                    os.unlink(temporary_name)
        return ContextArtifactRef(
            digest=digest,
            byte_count=len(value),
            media_type=media_type,
            encoding=encoding,
            artifact_kind=artifact_kind,
        )

    def put_text(self, value: str, *, media_type: str = "text/plain",
                 artifact_kind: str = "raw_output") -> ContextArtifactRef:
        return self.put(
            value.encode("utf-8"),
            media_type=media_type,
            encoding="utf-8",
            artifact_kind=artifact_kind,
        )

    def get(self, reference: ContextArtifactRef) -> bytes:
        """Load and verify an artifact. Missing or changed data fails closed."""
        path = self._path_for_digest(reference.digest)
        try:
            value = path.read_bytes()
        except OSError as exc:
            raise FileNotFoundError(
                f"context artifact {reference.digest} is unavailable") from exc
        if len(value) != reference.byte_count or _sha256(value) != reference.digest:
            raise RuntimeError(
                f"context artifact {reference.digest} failed integrity validation")
        return value

    def get_text(self, reference: ContextArtifactRef) -> str:
        if reference.encoding.lower() != "utf-8":
            raise ValueError("get_text only accepts UTF-8 artifacts")
        return self.get(reference).decode("utf-8")

    def _path_for_digest(self, digest: str) -> Path:
        if (len(digest) != 64
                or any(char not in "0123456789abcdef" for char in digest)):
            raise ValueError("artifact digest must be a lowercase SHA-256 value")
        return self._objects / digest[:2] / digest


class ContextTokenCounter(Protocol):
    """A deterministic token-counting contract used by offload policy."""

    counter_id: str

    def count(self, text: str) -> int: ...


@dataclass(frozen=True)
class Utf8ChunkTokenCounter:
    """A stable estimate for policy decisions, not a provider token count."""

    bytes_per_token: int = 4
    counter_id: str = "utf8_bytes_div_4_v1"

    def __post_init__(self):
        if self.bytes_per_token < 1:
            raise ValueError("bytes_per_token must be positive")

    def count(self, text: str) -> int:
        byte_count = len(text.encode("utf-8"))
        return math.ceil(byte_count / self.bytes_per_token)


@dataclass(frozen=True)
class ContextOffloadPolicy:
    """Thresholds that decide whether raw text also stays inline."""

    max_inline_bytes: int = 32_768
    max_inline_tokens: int = 8_192

    def __post_init__(self):
        if self.max_inline_bytes < 0 or self.max_inline_tokens < 0:
            raise ValueError("context offload thresholds cannot be negative")


@dataclass(frozen=True)
class ContextPayload:
    """A raw artifact reference plus optional inline text for small values."""

    raw: ContextArtifactRef
    estimated_tokens: int
    token_counter_id: str
    inline_text: "str | None" = None
    offloaded: bool = False

    def __post_init__(self):
        if self.estimated_tokens < 0:
            raise ValueError("estimated_tokens cannot be negative")
        if self.offloaded and self.inline_text is not None:
            raise ValueError("offloaded context cannot also carry inline text")
        if not self.offloaded and self.inline_text is None:
            raise ValueError("inline context needs inline_text")

    def to_dict(self) -> dict:
        return {
            "raw": self.raw.to_dict(),
            "estimated_tokens": self.estimated_tokens,
            "token_counter_id": self.token_counter_id,
            "inline_text": self.inline_text,
            "offloaded": self.offloaded,
        }


@dataclass(frozen=True)
class ContextArtifactServices:
    """Store and runtime observer passed together to context operations."""

    store: ContextArtifactStore
    runtime: "RuntimeObservationServices | None" = None

    def __post_init__(self):
        if not isinstance(self.store, ContextArtifactStore):
            raise TypeError("context services need a ContextArtifactStore")
        if self.runtime is None:
            from .runtime_observer import RuntimeObservationServices
            object.__setattr__(self, "runtime", RuntimeObservationServices())


class ContextArtifactManager:
    """Capture raw context before applying the inline/offload policy."""

    def __init__(self, services: "ContextArtifactServices | ContextArtifactStore",
                 policy: "ContextOffloadPolicy | None" = None,
                 token_counter: "ContextTokenCounter | None" = None):
        self.services = (services if isinstance(services, ContextArtifactServices)
                         else ContextArtifactServices(services))
        self.store = self.services.store
        self.policy = policy or ContextOffloadPolicy()
        self.token_counter = token_counter or Utf8ChunkTokenCounter()

    def capture(self, text: str, *, media_type: str = "text/plain",
                artifact_kind: str = "raw_output") -> ContextPayload:
        raw_bytes = text.encode("utf-8")
        raw = self.store.put(
            raw_bytes,
            media_type=media_type,
            encoding="utf-8",
            artifact_kind=artifact_kind,
        )
        token_count = self.token_counter.count(text)
        offloaded = (
            len(raw_bytes) > self.policy.max_inline_bytes
            or token_count > self.policy.max_inline_tokens
        )
        payload = ContextPayload(
            raw=raw,
            estimated_tokens=token_count,
            token_counter_id=self.token_counter.counter_id,
            inline_text=None if offloaded else text,
            offloaded=offloaded,
        )
        from .runtime_observer import RuntimeObservation
        self.services.runtime.emit(RuntimeObservation(
            "context_artifact_stored",
            {"digest": raw.digest, "byte_count": raw.byte_count,
             "media_type": raw.media_type,
             "artifact_kind": raw.artifact_kind,
             "estimated_tokens": token_count,
             "token_counter_id": self.token_counter.counter_id,
             "offloaded": offloaded}))
        return payload


@dataclass(frozen=True)
class CompactionRequest:
    """Input contract for one explicit deterministic compaction Loop."""

    raw: ContextArtifactRef
    max_summary_bytes: int = 4_096
    strategy: str = "head_tail_v1"
    loop_profile: str = "context.compaction.deterministic.v1"

    def __post_init__(self):
        if self.max_summary_bytes < 64:
            raise ValueError("max_summary_bytes must be at least 64")
        if not self.strategy or not self.loop_profile:
            raise ValueError("compaction needs a strategy and Loop profile")


@dataclass(frozen=True)
class CompactionResult:
    """A shorter artifact that retains the canonical raw reference."""

    raw: ContextArtifactRef
    compacted: ContextArtifactRef
    strategy: str
    loop_profile: str
    omitted_bytes: int

    def __post_init__(self):
        if self.raw.digest == self.compacted.digest and self.omitted_bytes > 0:
            raise ValueError("a shortened artifact must differ from the raw one")
        if self.omitted_bytes < 0:
            raise ValueError("omitted_bytes cannot be negative")

    def to_dict(self) -> dict:
        return {
            "raw": self.raw.to_dict(),
            "compacted": self.compacted.to_dict(),
            "strategy": self.strategy,
            "loop_profile": self.loop_profile,
            "omitted_bytes": self.omitted_bytes,
        }


class DeterministicCompactor(Protocol):
    """Pure compaction service called inside an Intelligence Loop."""

    profile_id: str

    def run(self, request: CompactionRequest) -> CompactionResult: ...


class HeadTailCompactor:
    """Keep bounded UTF-8-safe text from both ends of a raw artifact."""

    profile_id = "context.compaction.deterministic.v1"

    def __init__(self, services: "ContextArtifactServices | ContextArtifactStore"):
        self.services = (services if isinstance(services, ContextArtifactServices)
                         else ContextArtifactServices(services))
        self.store = self.services.store

    def run(self, request: CompactionRequest) -> CompactionResult:
        if request.strategy != "head_tail_v1":
            raise ValueError("HeadTailCompactor supports head_tail_v1 only")
        if request.loop_profile != self.profile_id:
            raise ValueError("compaction request has an incompatible Loop profile")
        raw = self.store.get(request.raw)
        if len(raw) <= request.max_summary_bytes:
            compacted = self.store.put(
                raw,
                media_type=request.raw.media_type,
                encoding=request.raw.encoding,
                artifact_kind="deterministic_compaction",
            )
            result = CompactionResult(
                raw=request.raw,
                compacted=compacted,
                strategy=request.strategy,
                loop_profile=request.loop_profile,
                omitted_bytes=0,
            )
            self._observe(result)
            return result

        marker = b"\n\n[content omitted; use raw artifact reference]\n\n"
        content_budget = request.max_summary_bytes - len(marker)
        if content_budget < 2:
            raise ValueError("max_summary_bytes is too small for the marker")
        head_size = content_budget // 2
        tail_size = content_budget - head_size
        compacted_bytes = (
            _valid_utf8_prefix(raw[:head_size])
            + marker
            + _valid_utf8_suffix(raw[-tail_size:])
        )
        compacted = self.store.put(
            compacted_bytes,
            media_type="text/plain",
            encoding="utf-8",
            artifact_kind="deterministic_compaction",
        )
        result = CompactionResult(
            raw=request.raw,
            compacted=compacted,
            strategy=request.strategy,
            loop_profile=request.loop_profile,
            omitted_bytes=len(raw) - len(compacted_bytes),
        )
        self._observe(result)
        return result

    def _observe(self, result: CompactionResult) -> None:
        from .runtime_observer import RuntimeObservation
        self.services.runtime.emit(RuntimeObservation(
            "context_compaction_completed",
            {"raw_digest": result.raw.digest,
             "compacted_digest": result.compacted.digest,
             "compacted_bytes": result.compacted.byte_count,
             "omitted_bytes": result.omitted_bytes,
             "strategy": result.strategy,
             "loop_profile": result.loop_profile}))


# Compatibility for callers that imported the early service name. The object
# is a pure compactor, not a second runtime. New callers use
# ``compact_context_as_loop``.
HeadTailCompactionLoop = HeadTailCompactor


def compact_context_as_loop(
        request: CompactionRequest, *,
        services: "ContextArtifactServices | ContextArtifactStore",
        parent=None, ledger=None) -> CompactionResult:
    """Run deterministic compaction through the universal Loop runtime."""
    selected = (services if isinstance(services, ContextArtifactServices)
                else ContextArtifactServices(services))
    active_ledger = ledger or getattr(selected.runtime, "ledger", None)
    from ..loop.intelligence_loops import serve_context_intelligence
    wrapped = serve_context_intelligence(
        "context.compaction.deterministic.v1",
        lambda: HeadTailCompactor(selected).run(request),
        ledger=active_ledger,
        parent=parent,
        query_hint="compact selected context without changing raw content",
        profile_id="intelligence.context.frame",
    )
    if wrapped.get("error") is not None:
        raise wrapped["error"]
    result = wrapped["value"]
    if not isinstance(result, CompactionResult):
        raise TypeError("context compaction Loop returned the wrong contract")
    return result


def _valid_utf8_prefix(value: bytes) -> bytes:
    return value.decode("utf-8", errors="ignore").encode("utf-8")


def _valid_utf8_suffix(value: bytes) -> bytes:
    # Removing leading continuation bytes prevents a partial character from
    # consuming the first complete character under errors="ignore".
    start = 0
    while start < len(value) and value[start] & 0xC0 == 0x80:
        start += 1
    return value[start:].decode("utf-8", errors="ignore").encode("utf-8")


def self_test() -> dict:
    """Exercise raw preservation, threshold offload, and compaction offline."""
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    with tempfile.TemporaryDirectory() as directory:
        store = ContextArtifactStore(ContextArtifactStoreSpec(directory))
        from .runtime_observer import RuntimeObservationServices
        from ..loop.recursive_loop import LoopLedger
        ledger = LoopLedger()
        services = ContextArtifactServices(
            store, RuntimeObservationServices(ledger=ledger))
        manager = ContextArtifactManager(
            services,
            ContextOffloadPolicy(max_inline_bytes=16, max_inline_tokens=4),
        )
        small = manager.capture("small")
        large_text = "alpha beta gamma delta " * 20
        large = manager.capture(large_text)
        check(
            "small_context_stays_inline_and_has_a_canonical_raw_artifact",
            not small.offloaded and small.inline_text == "small"
            and store.get_text(small.raw) == "small",
            "small context remains convenient without losing its raw object",
        )
        check(
            "large_context_is_offloaded_by_deterministic_thresholds",
            large.offloaded and large.inline_text is None
            and store.get_text(large.raw) == large_text,
            "large context leaves the active payload but remains retrievable",
        )

        same = store.put_text(large_text)
        check(
            "the_same_raw_value_has_the_same_portable_reference",
            same.digest == large.raw.digest
            and same.object_key == large.raw.object_key,
            "content addressing deduplicates without including the local root",
        )

        compacted = compact_context_as_loop(
            CompactionRequest(raw=large.raw, max_summary_bytes=128),
            services=services)
        compacted_text = store.get_text(compacted.compacted)
        check(
            "compaction_keeps_separate_raw_and_shorter_artifact_references",
            compacted.raw.digest == large.raw.digest
            and compacted.compacted.digest != large.raw.digest
            and len(compacted_text.encode("utf-8")) <= 128
            and store.get_text(compacted.raw) == large_text,
            "a shorter view never replaces or mutates the canonical raw value",
        )

        incompatible_failed = False
        try:
            compact_context_as_loop(CompactionRequest(
                raw=large.raw, max_summary_bytes=128,
                loop_profile="context.compaction.model.v1"),
                services=services)
        except ValueError:
            incompatible_failed = True
        check(
            "compaction_refuses_an_incompatible_loop_profile",
            incompatible_failed,
            "profile handshakes prevent one compactor from claiming another method",
        )
        check(
            "context_services_emit_safe_capture_and_compaction_events",
            [event["event"] for event in ledger.events].count(
                "context_compaction_completed") == 1
            and any(event["event"] == "init" for event in ledger.events)
            and any(event["event"] == "terminal" for event in ledger.events)
            and all("inline_text" not in event and "content" not in event
                    for event in ledger.events)
            and next(event for event in ledger.events
                     if event["event"] == "context_compaction_completed")[
                         "raw_digest"] == large.raw.digest,
            "the Loop ledger receives digest metadata and no artifact body",
        )

        object_path = store._path_for_digest(large.raw.digest)
        object_path.write_bytes(b"changed")
        failed_closed = False
        try:
            store.get(large.raw)
        except RuntimeError:
            failed_closed = True
        check(
            "changed_artifact_data_fails_integrity_validation",
            failed_closed,
            "a digest reference cannot silently resolve to changed data",
        )

    passed = sum(1 for item in results if item["passed"])
    return {
        "suite": "context_artifacts",
        "total": len(results),
        "passed": passed,
        "all_passed": passed == len(results),
        "tests": results,
        "failed": [item for item in results if not item["passed"]],
        "results": results,
    }


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
