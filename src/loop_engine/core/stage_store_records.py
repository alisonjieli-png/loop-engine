"""Strict passive parsing helpers for the stage-observation JSONL store.

This module owns no storage, retrieval, execution, or evidence authority. It
only validates current rows, performs the explicit legacy migration, restores
immutable outcome vectors, and computes stable fallback identities.
"""
from __future__ import annotations

import hashlib
import json
import math
import os

from .outcome_vector import SIGNAL_SCOPES, OutcomeVector
from .outcome_vector import observe as observe_outcome


def occurrence_id(run_id: str, semantic_digest: str, position: int) -> str:
    """Create a bounded exact occurrence ID when the owner supplies none."""
    material = json.dumps(
        {"run_id": run_id, "semantic_digest": semantic_digest,
         "position": position},
        sort_keys=True, separators=(",", ":"))
    return "stage-occurrence:sha256:" + hashlib.sha256(
        material.encode("utf-8")).hexdigest()


def legacy_occurrence_id(path: str, row_number: int, value: dict) -> str:
    """Give an old row an identity without pretending it originally had one."""
    material = json.dumps(
        {"source_path": os.path.abspath(path), "row_number": row_number,
         "stored": value}, sort_keys=True, separators=(",", ":"), default=str)
    return "legacy-stage-occurrence:sha256:" + hashlib.sha256(
        material.encode("utf-8")).hexdigest()


def unique_text(values) -> tuple[str, ...]:
    """Keep non-empty text in first-seen order."""
    seen = set()
    answer = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            answer.append(value)
    return tuple(answer)


def complete_sum(values) -> int | None:
    """Sum provider usage only when every physical attempt reported it."""
    items = tuple(values)
    if not items or any(value is None for value in items):
        return None
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0
           for value in items):
        raise ValueError(
            "physical model usage must be non-negative integers or unknown")
    return sum(items)


def text_sequence(value, name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise TypeError(f"{name} must be a sequence, not text")
    try:
        items = tuple(value or ())
    except TypeError as exc:
        raise TypeError(f"{name} must be a sequence") from exc
    if (any(not isinstance(item, str) or not item for item in items)
            or len(items) != len(set(items))):
        raise ValueError(f"{name} must contain unique non-empty text")
    return items


def outcome_from(value: dict, *, strict: bool = False) -> OutcomeVector:
    """Restore a current vector or migrate one legacy run-level Boolean."""
    stored = value.get("outcome")
    if isinstance(stored, dict):
        if strict:
            expected = {
                "record_type", "credit", "granularity", "known", "unknown",
                "contradictions", "reading", *SIGNAL_SCOPES}
            if set(stored) != expected \
                    or stored.get("record_type") != "outcome_vector/v1":
                raise ValueError("v2 stage outcome fields do not match")
        signals = {name: stored.get(name) for name in SIGNAL_SCOPES}
        if any(item is not None and not isinstance(item, bool)
               for item in signals.values()):
            raise TypeError("stage outcome signals must be bool or null")
        contradictions = text_sequence(
            stored.get("contradictions", ()), "outcome contradictions")
        if any(name not in SIGNAL_SCOPES for name in contradictions):
            raise ValueError("outcome contradiction names an unknown signal")
        vector = OutcomeVector(**signals, contradictions=contradictions)
        if strict:
            derived = vector.to_dict()
            for name in ("credit", "granularity", "known", "unknown",
                         "reading"):
                if stored.get(name) != derived[name]:
                    raise ValueError(
                        f"stored outcome {name} does not match its signals")
        return vector
    if strict:
        raise ValueError("a v2 stage record needs an outcome vector")
    legacy = value.get("helped")
    if legacy is not None and not isinstance(legacy, bool):
        raise TypeError("legacy helped must be bool or null")
    return observe_outcome(OutcomeVector(), task_outcome=legacy)


def _nonnegative_count(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _optional_nonnegative(value, name: str, *, integer: bool = False):
    if value is None:
        return None
    expected = int if integer else (int, float)
    if (isinstance(value, bool) or not isinstance(value, expected)
            or value < 0
            or (not integer and not math.isfinite(float(value)))):
        kind = "integer" if integer else "finite number"
        raise ValueError(f"{name} must be a non-negative {kind} or null")
    return value


def validate_v2_record(value: dict) -> None:
    """Validate the exact current JSONL contract before constructing a row."""
    expected = {
        "record_type", "digest", "motif", "shape", "responsibility",
        "run_id", "occurrence_id", "observation_ref", "semantic_call_id",
        "owner_loop_id", "response_shape", "model_route", "model_provider",
        "model_name", "model_routes", "model_attempt_loop_ids",
        "pass_number", "outcome", "helped", "gateway_calls", "model_calls",
        "elapsed_seconds", "input_tokens", "output_tokens", "usage_complete",
    }
    if set(value) != expected:
        raise ValueError("stage_observation/v2 fields do not match")
    required_text = ("digest", "motif", "responsibility", "occurrence_id",
                     "observation_ref")
    optional_text = ("run_id", "semantic_call_id", "owner_loop_id",
                     "response_shape", "model_route", "model_provider",
                     "model_name")
    if any(not isinstance(value.get(name), str) or not value[name]
           for name in required_text):
        raise ValueError("v2 stage identity fields need non-empty text")
    if any(not isinstance(value.get(name), str) for name in optional_text):
        raise TypeError("v2 optional stage text fields must be text")
    if not isinstance(value.get("shape"), list):
        raise TypeError("v2 stage shape must be a JSON list")
    text_sequence(value.get("model_routes"), "model_routes")
    text_sequence(value.get("model_attempt_loop_ids"),
                  "model_attempt_loop_ids")
    _nonnegative_count(value.get("pass_number"), "pass_number")
    _nonnegative_count(value.get("gateway_calls"), "gateway_calls")
    _nonnegative_count(value.get("model_calls"), "model_calls")
    _optional_nonnegative(value.get("elapsed_seconds"), "elapsed_seconds")
    _optional_nonnegative(value.get("input_tokens"), "input_tokens",
                          integer=True)
    _optional_nonnegative(value.get("output_tokens"), "output_tokens",
                          integer=True)
    if value.get("helped") is not None and not isinstance(
            value.get("helped"), bool):
        raise TypeError("helped must be bool or null")
    if not isinstance(value.get("usage_complete"), bool):
        raise TypeError("usage_complete must be boolean")


def validate_legacy_record(value: dict) -> None:
    """Recognize only the exact fields needed by the explicit v1 migration."""
    required = {"digest", "motif", "shape", "responsibility"}
    if not required.issubset(value):
        raise ValueError("legacy stage record is missing identity fields")
    if any(not isinstance(value.get(name), str) or not value[name]
           for name in ("digest", "motif", "responsibility")):
        raise ValueError("legacy stage identity fields need non-empty text")
    if not isinstance(value.get("shape"), list):
        raise TypeError("legacy stage shape must be a JSON list")
    if "run_id" in value and not isinstance(value.get("run_id"), str):
        raise TypeError("legacy stage run_id must be text")


def hashable(value):
    """Restore nested JSON lists as indexable tuples."""
    if isinstance(value, list):
        return tuple(hashable(item) for item in value)
    return value


def refuses_unknown_signal(store, observation) -> bool:
    """Test helper proving an unknown outcome signal is rejected."""
    try:
        store.observe(observation, invented_signal=True)
    except ValueError:
        return True
    return False


__all__ = (
    "complete_sum", "hashable", "legacy_occurrence_id", "occurrence_id",
    "outcome_from", "refuses_unknown_signal", "unique_text",
    "validate_legacy_record",
    "validate_v2_record")
