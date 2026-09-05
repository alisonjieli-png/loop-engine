"""Exact output capture for the existing external-harness boundary.

Internal serialization and artifact publication only; no independent runtime,
provider call, acceptance authority, or store is introduced.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .context_artifacts import ContextArtifactManager


def _serialize_harness_output(value: object) -> tuple[str, str]:
    """Return one deterministic text body for ContextArtifactManager."""
    from .external_harness import HarnessError
    if isinstance(value, str):
        return value, "text/plain"
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        value = model_dump(mode="json")
    try:
        text = json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise HarnessError(
            "external harness output is not text or JSON-compatible") from exc
    return text, "application/json"


def _capture_harness_output(
        result,
        manager: "ContextArtifactManager") -> None:
    """Store raw output first, then keep inline data or publish only its ref."""
    from .external_harness import HarnessArtifactRef, HarnessError

    if result.output is None:
        return
    if isinstance(result.output, HarnessArtifactRef):
        from .context_artifacts import ContextArtifactRef
        stored = ContextArtifactRef(
            result.output.digest, result.output.size_bytes or 0,
            media_type=result.output.media_type,
            artifact_kind="external_harness_output")
        manager.store.get(stored)
        if result.output.uri != stored.object_key:
            raise HarnessError(
                "external harness artifact URI does not match its digest")
        if result.output not in result.artifacts:
            result.artifacts = (*result.artifacts, result.output)
        return
    body, media_type = _serialize_harness_output(result.output)
    payload = manager.capture(
        body, media_type=media_type,
        artifact_kind="external_harness_output")
    reference = HarnessArtifactRef(
        artifact_id=f"context-output:{payload.raw.digest}",
        uri=payload.raw.object_key,
        digest=payload.raw.digest,
        media_type=payload.raw.media_type,
        size_bytes=payload.raw.byte_count)
    if all(item.digest != reference.digest for item in result.artifacts):
        result.artifacts = (*result.artifacts, reference)
    if payload.offloaded:
        result.output = reference
    else:
        # Reconstruct from captured bytes, not a producer-owned SDK object.
        result.output = json.loads(body) if media_type == "application/json" else body
