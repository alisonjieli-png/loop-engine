"""Verifier, effect authorization, and catalog-backed semantic trusted state.

Model output never enters this store directly. An approved verifier and effect
controller must issue matching records before the store performs one
compare-and-swap commit or returns an idempotent replay.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping

from .semantic_runtime_records import (
    CommittedSemanticResult,
    SemanticCandidateOutput,
    SemanticContextPack,
    SemanticEffectAuthorization,
    SemanticLoopContract,
    SemanticRuntimeContractError,
    SemanticVerificationRecord,
    TrustedStateSnapshot,
    semantic_digest,
)


class SemanticStateError(RuntimeError):
    """Trusted semantic state could not be read or changed safely."""


class SemanticStateConflict(SemanticStateError):
    """A state delta used a stale version or conflicting idempotency key."""


@dataclass(frozen=True)
class SemanticVerifier:
    """Independent deterministic verifier for one public semantic contract."""

    verifier_id: str
    version: str
    policy_digest: str
    evaluator: Callable[
        [SemanticLoopContract, SemanticCandidateOutput, object,
         SemanticContextPack], Mapping[str, object]] = field(
             repr=False, compare=False)
    _token: object = field(
        default_factory=object, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if (not self.verifier_id.strip() or not self.version.strip()
                or len(self.policy_digest) != 64
                or not callable(self.evaluator)):
            raise SemanticRuntimeContractError(
                "semantic verifier configuration is invalid")

    def verify(
            self, contract: SemanticLoopContract,
            candidate: SemanticCandidateOutput,
            input_value: object,
            context: SemanticContextPack) -> SemanticVerificationRecord:
        if candidate.contract_digest != contract.contract_digest:
            raise SemanticRuntimeContractError(
                "verifier received a candidate for another contract")
        decision = self.evaluator(contract, candidate, input_value, context)
        if not isinstance(decision, Mapping) or set(decision) != {
                "structurally_valid", "contract_valid", "evidence_valid",
                "postconditions_valid", "accepted", "abstained", "reasons",
                "evidence_refs"}:
            raise SemanticRuntimeContractError(
                "semantic verifier returned an invalid decision shape")
        identity = semantic_digest({
            "candidate_digest": candidate.digest,
            "verifier_id": self.verifier_id,
            "verifier_version": self.version,
            "policy_digest": self.policy_digest,
        })[:24]
        return SemanticVerificationRecord(
            "verification." + identity, candidate.digest,
            self.verifier_id, self.version,
            bool(decision["structurally_valid"]),
            bool(decision["contract_valid"]),
            bool(decision["evidence_valid"]),
            bool(decision["postconditions_valid"]),
            bool(decision["accepted"]), bool(decision["abstained"]),
            tuple(decision["reasons"] or ()),
            tuple(decision["evidence_refs"] or ()), self._token)

    def issued(self, record: SemanticVerificationRecord) -> bool:
        return (isinstance(record, SemanticVerificationRecord)
                and record._authority_token is self._token
                and record.verifier_id == self.verifier_id
                and record.verifier_version == self.version)


@dataclass(frozen=True)
class SemanticEffectController:
    """Admit no effect beyond the exact semantic contract and approval refs."""

    controller_id: str
    policy_digest: str
    external_effect_consumer: "Callable[[SemanticCandidateOutput], tuple[str, ...]] | None" = field(
        default=None, repr=False, compare=False)
    _token: object = field(
        default_factory=object, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if (not self.controller_id.strip() or len(self.policy_digest) != 64
                or self.external_effect_consumer is not None
                and not callable(self.external_effect_consumer)):
            raise SemanticRuntimeContractError(
                "semantic effect controller configuration is invalid")

    def authorize(
            self, contract: SemanticLoopContract,
            candidate: SemanticCandidateOutput) -> SemanticEffectAuthorization:
        delta = candidate.proposed_delta
        declared = set(delta.declared_effects)
        permitted = set(contract.draft.permitted_effects)
        prohibited = set(contract.draft.prohibited_effects)
        reasons = []
        if not declared <= permitted:
            reasons.append("declared effect exceeds contract authority")
        if declared & prohibited:
            reasons.append("declared effect is explicitly prohibited")
        if delta.writes and not declared:
            reasons.append("state writes require a declared effect")
        effect_refs: tuple[str, ...] = ()
        if declared and not reasons:
            if self.external_effect_consumer is None:
                reasons.append("external effect approval is unavailable")
            else:
                effect_refs = tuple(self.external_effect_consumer(candidate))
                if not effect_refs:
                    reasons.append("external effect approval returned no record")
        allowed = not reasons
        identity = semantic_digest({
            "candidate_digest": candidate.digest,
            "delta_digest": delta.digest,
            "controller_id": self.controller_id,
            "policy_digest": self.policy_digest,
            "effect_refs": list(effect_refs),
            "allowed": allowed,
        })[:24]
        return SemanticEffectAuthorization(
            "effect-authorization." + identity,
            candidate.digest, delta.digest, self.controller_id, allowed,
            effect_refs, tuple(reasons), self._token)

    def issued(self, record: SemanticEffectAuthorization) -> bool:
        return (isinstance(record, SemanticEffectAuthorization)
                and record._authority_token is self._token
                and record.controller_id == self.controller_id)


class CatalogTrustedSemanticState:
    """Revisioned semantic state through the existing CatalogStore contract."""

    def __init__(self, store) -> None:
        if any(not callable(getattr(store, name, None))
               for name in ("get", "put")):
            raise SemanticStateError(
                "trusted semantic state requires a writable CatalogStore")
        self.store = store

    @staticmethod
    def _record_id(state_id: str) -> str:
        return f"semantic_trusted_state.{state_id}"

    def initialize(
            self, state_id: str, values=()) -> TrustedStateSnapshot:
        snapshot = TrustedStateSnapshot(state_id, 0, tuple(values), ())
        record = self._record(snapshot)
        existing = self.store.get(record["record_id"])
        if existing is None:
            self.store.put(record)
            return snapshot
        loaded = self.snapshot(state_id)
        if loaded.values != snapshot.values:
            raise SemanticStateConflict(
                "trusted state identity already has different initial values")
        return loaded

    def snapshot(self, state_id: str) -> TrustedStateSnapshot:
        record = self.store.get(self._record_id(state_id))
        if record is None or record.get("artifact_kind") != \
                "semantic_trusted_state":
            raise SemanticStateError("trusted semantic state is unavailable")
        attributes = dict(record.get("attributes") or {})
        try:
            snapshot = TrustedStateSnapshot(
                state_id, int(record["record_version"]),
                tuple(sorted(dict(attributes["values"]).items())),
                tuple(sorted(dict(
                    attributes["committed_idempotency"]).items())))
        except (KeyError, TypeError, ValueError) as exc:
            raise SemanticStateError(
                "trusted semantic state record is malformed") from exc
        if attributes.get("state_digest") != snapshot.digest:
            raise SemanticStateError(
                "trusted semantic state digest does not match")
        return snapshot

    def commit(
            self, candidate: SemanticCandidateOutput,
            verification: SemanticVerificationRecord,
            authorization: SemanticEffectAuthorization,
            verifier: SemanticVerifier,
            effect_controller: SemanticEffectController
            ) -> CommittedSemanticResult:
        if (not verifier.issued(verification)
                or not effect_controller.issued(authorization)
                or verification.candidate_digest != candidate.digest
                or authorization.candidate_digest != candidate.digest
                or not verification.accepted or verification.abstained
                or not authorization.allowed):
            raise SemanticStateError(
                "trusted commit requires issued verification and authorization")
        delta = candidate.proposed_delta
        before = self.snapshot(delta.base_state_id)
        committed = dict(before.committed_idempotency)
        existing = committed.get(delta.idempotency_key)
        if existing is not None:
            if existing != candidate.digest:
                raise SemanticStateConflict(
                    "idempotency key already names another candidate")
            return self._commit_result(
                candidate, verification, authorization, before, before, True)
        if before.version != delta.base_state_version:
            raise SemanticStateConflict(
                "proposed state delta is based on a stale version")
        values = dict(before.values)
        values.update(dict(delta.writes))
        committed[delta.idempotency_key] = candidate.digest
        after = TrustedStateSnapshot(
            before.state_id, before.version + 1,
            tuple(sorted(values.items())), tuple(sorted(committed.items())))
        self.store.put(
            self._record(after),
            precondition={"record_version": str(before.version)})
        return self._commit_result(
            candidate, verification, authorization, before, after, False)

    @staticmethod
    def _commit_result(
            candidate, verification, authorization, before, after,
            replayed) -> CommittedSemanticResult:
        identity = semantic_digest({
            "candidate_digest": candidate.digest,
            "verification_digest": verification.digest,
            "authorization_digest": authorization.digest,
            "state_before": before.digest, "state_after": after.digest,
        })[:24]
        return CommittedSemanticResult(
            "semantic-commit." + identity, candidate.digest,
            verification.digest, authorization.digest,
            before, after, replayed)

    @classmethod
    def _record(cls, snapshot: TrustedStateSnapshot) -> dict:
        return {
            "record_id": cls._record_id(snapshot.state_id),
            "record_version": str(snapshot.version),
            "intelligence_layer": "runtime_history_solution",
            "source_collection": "runtime",
            "artifact_kind": "semantic_trusted_state",
            "lifecycle": "registered",
            "namespace": "run:semantic",
            "attributes": {
                "values": dict(snapshot.values),
                "committed_idempotency": dict(
                    snapshot.committed_idempotency),
                "state_digest": snapshot.digest,
            },
        }


__all__ = (
    "CatalogTrustedSemanticState", "SemanticEffectController",
    "SemanticStateConflict", "SemanticStateError", "SemanticVerifier",
)
