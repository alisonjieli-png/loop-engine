"""Digest-bound product outcome storage within one saved-run bundle.

Run History owns immutable Loop events. This module binds the final solve
result to the same run manifest without adding another history authority.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from .run_history import RunHistory


PRODUCT_OUTCOME_FILENAME = "outcome.json"
PRODUCT_OUTCOME_RECORD_TYPES = ("solve_outcome/v3", "solve_outcome/v4")


def _error(message: str):
    from .run_history import RunHistoryIntegrityError
    return RunHistoryIntegrityError(message)


@dataclass(frozen=True)
class ProductOutcomeRef:
    """Digest-bound product result stored inside one saved run directory."""

    path: str
    content_digest: str
    record_type: str
    terminal_code: str
    solved: bool

    def __post_init__(self) -> None:
        if (self.path != PRODUCT_OUTCOME_FILENAME
                or not _is_digest(self.content_digest)
                or self.record_type not in PRODUCT_OUTCOME_RECORD_TYPES
                or not self.terminal_code):
            raise _error("product outcome reference is malformed")

    def to_dict(self) -> dict:
        return {
            "record_type": "product_outcome_ref/v1",
            "path": self.path,
            "content_digest": self.content_digest,
            "outcome_record_type": self.record_type,
            "terminal_code": self.terminal_code,
            "solved": self.solved,
        }


@dataclass(frozen=True)
class SavedRunBundle:
    """One verified Run History plus its optional bound product outcome."""

    history: "RunHistory"
    outcome: "dict | None" = None
    outcome_ref: "ProductOutcomeRef | None" = None


def _is_digest(value: str) -> bool:
    return (len(str(value)) == 64
            and all(char in "0123456789abcdef" for char in str(value)))


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False, default=str)


def _product_outcome_ref(value: Mapping) -> ProductOutcomeRef:
    body = dict(value)
    if body.get("record_type") != "product_outcome_ref/v1":
        raise _error(
            "manifest product outcome is not a product_outcome_ref/v1")
    return ProductOutcomeRef(
        str(body.get("path") or ""),
        str(body.get("content_digest") or ""),
        str(body.get("outcome_record_type") or ""),
        str(body.get("terminal_code") or ""),
        bool(body.get("solved")))


def _validate_product_outcome(value: Mapping, run_id: str) -> dict:
    body = dict(value)
    if (body.get("record_type") not in PRODUCT_OUTCOME_RECORD_TYPES
            or body.get("run_id") != run_id
            or not isinstance(body.get("solved"), bool)
            or not str(body.get("terminal_code") or "")
            or body.get("terminal_code") != body.get("status")
            or not isinstance(body.get("artifacts"), list)
            or not isinstance(body.get("verification"), dict)):
        raise _error("saved product outcome violates its solve outcome contract")
    if (body.get("record_type") == "solve_outcome/v4"
            and not isinstance(body.get("questions"), list)):
        raise _error("solve_outcome/v4 questions must be a list")
    return body


def _load_history(root: str, run_id: str):
    """Read Run History through its governed Intelligence Loop."""
    from .run_history import RunHistory, RunHistoryIntegrityError
    from ..loop.intelligence_loops import serve_historical_intelligence

    def handler():
        return RunHistory.load(root, run_id)

    value = serve_historical_intelligence(
        f"product-outcome:{run_id}", handler)["value"]
    if not isinstance(value, RunHistory):
        raise RunHistoryIntegrityError(
            f"saved run {run_id!r} could not be verified")
    return value


def bind_product_outcome(root: str, run_id: str,
                         outcome: Mapping) -> ProductOutcomeRef:
    """Finalize one saved run with one exact product outcome reference."""
    _load_history(root, run_id)
    body = _validate_product_outcome(outcome, run_id)
    run_dir = os.path.join(root, run_id)
    outcome_path = os.path.join(run_dir, PRODUCT_OUTCOME_FILENAME)
    encoded = _canonical_json(body)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    ref = ProductOutcomeRef(
        PRODUCT_OUTCOME_FILENAME, digest, str(body["record_type"]),
        str(body["terminal_code"]), bool(body["solved"]))
    if os.path.exists(outcome_path):
        with open(outcome_path, encoding="utf-8") as stream:
            existing = _validate_product_outcome(json.load(stream), run_id)
        if hashlib.sha256(_canonical_json(existing).encode(
                "utf-8")).hexdigest() != digest:
            raise _error("saved run already has a different product outcome")
    else:
        with open(outcome_path, "x", encoding="utf-8") as stream:
            json.dump(body, stream, indent=1, ensure_ascii=False,
                      allow_nan=False, default=str)
            stream.write("\n")
    manifest_path = os.path.join(run_dir, "manifest.json")
    with open(manifest_path, encoding="utf-8") as stream:
        manifest = json.load(stream)
    prior = manifest.get("product_outcome")
    if prior and _product_outcome_ref(prior) != ref:
        raise _error("run manifest already binds a different product outcome")
    manifest["product_outcome"] = ref.to_dict()
    handle, temporary = tempfile.mkstemp(
        prefix="manifest-", suffix=".json", dir=run_dir, text=True)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(manifest, stream, indent=1)
            stream.write("\n")
        os.replace(temporary, manifest_path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return ref


def load_saved_run_bundle(root: str, run_id: str) -> SavedRunBundle:
    """Load and verify events, manifest, and the optional product outcome."""
    history = _load_history(root, run_id)
    manifest_path = os.path.join(root, run_id, "manifest.json")
    with open(manifest_path, encoding="utf-8") as stream:
        manifest = json.load(stream)
    raw_ref = manifest.get("product_outcome")
    if raw_ref is None:
        return SavedRunBundle(history)
    ref = _product_outcome_ref(raw_ref)
    outcome_path = os.path.join(root, run_id, ref.path)
    if not os.path.isfile(outcome_path):
        raise _error("run manifest references a missing product outcome")
    with open(outcome_path, encoding="utf-8") as stream:
        outcome = _validate_product_outcome(json.load(stream), run_id)
    observed = hashlib.sha256(_canonical_json(outcome).encode(
        "utf-8")).hexdigest()
    if observed != ref.content_digest:
        raise _error(
            "saved product outcome does not match its manifest digest")
    if (outcome["terminal_code"] != ref.terminal_code
            or outcome["solved"] != ref.solved):
        raise _error(
            "saved product outcome summary differs from its manifest")
    return SavedRunBundle(history, outcome, ref)


__all__ = (
    "PRODUCT_OUTCOME_FILENAME", "PRODUCT_OUTCOME_RECORD_TYPES",
    "ProductOutcomeRef", "SavedRunBundle",
    "bind_product_outcome", "load_saved_run_bundle")
