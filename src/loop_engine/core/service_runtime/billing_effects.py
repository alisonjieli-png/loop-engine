"""Durable exact identities for explicitly authorized billing-session effects.

Records use the existing scoped catalogue and atomic read-set contract. They
retain uncertainty and provider identifiers, never credentials or portal URLs.
This service does not activate subscriptions or create another persistence engine.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
import hashlib
import hmac
import json
import re
import secrets
import uuid

from .records import BILLING_MANAGE_SCOPE, ServiceRuntimeError, canonical, digest, identifier
from .runtime import BILLING_POLICY, CUSTOMER, ServiceRuntime

SESSION_POLICY_KIND = "service_billing_session_policy"
#: Version two holds the session terms alone, a `billing_session_terms/v1`
#: document: what a customer is offered, what they are charged and where they
#: return. Version one held every field of the host session configuration, so a
#: changed timeout, or a field a release added with a default that changes
#: nothing, changed its digest and stopped checkout until the policy was
#: installed again. A release reads only the version it writes.
SESSION_POLICY_VERSION = "service_billing_session_policy/v2"
SESSION_TERMS_VERSION = "billing_session_terms/v1"
#: Each record version has its own slot. A release reads and writes only the
#: slot of the version it understands, so it never overwrites a record that an
#: older release still reads, and a rollback finds its own record where it left
#: it. The version one slot was the bare provider name, "stripe".
SESSION_POLICY_IDENTITY = ("stripe", SESSION_POLICY_VERSION)
SESSION_EFFECT_KIND = "service_billing_session_effect"
SESSION_EFFECT_VERSION = "service_billing_session_effect/v1"
EFFECT_SPEC_VERSION = "billing_session_effect_spec/v1"
SESSION_OPERATIONS = ("checkout", "portal")
CHECKOUT_OPERATION, PORTAL_OPERATION = SESSION_OPERATIONS
EFFECT_PENDING, EFFECT_CONFIRMED, EFFECT_UNKNOWN = ("pending", "confirmed", "unknown")
EFFECT_NOT_ATTEMPTED = "not_attempted"
# The provider documents a minimum 24-hour idempotency-key retention period.
# Callers must choose a strictly shorter reconciliation window.
PROVIDER_MINIMUM_IDEMPOTENCY_RETENTION_SECONDS = 24 * 3600


def exact_digest(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ServiceRuntimeError("invalid_effect_digest")


@dataclass(frozen=True)
class BillingSessionPolicyDefinition:
    """An immutable host policy snapshot, separate from its installation."""

    policy_json: str
    price_ids: tuple[str, ...]

    def __post_init__(self):
        value = json.loads(self.policy_json)
        if not isinstance(value, dict):
            raise ServiceRuntimeError("invalid_session_policy")
        # Only a terms document is a policy. A whole host configuration, the
        # shape version one stored, is refused rather than read as terms.
        if value.get("record_type") != SESSION_TERMS_VERSION:
            raise ServiceRuntimeError("unsupported_session_policy")
        prices = tuple(self.price_ids)
        if len(prices) != len(set(prices)):
            raise ServiceRuntimeError("duplicate_session_price")
        for price in prices:
            identifier(price, "session Price")
        object.__setattr__(self, "policy_json", canonical(value))
        object.__setattr__(self, "price_ids", prices)

    @property
    def digest(self):
        return digest({"policy": json.loads(self.policy_json), "price_ids": self.price_ids})


@dataclass(frozen=True)
class BillingSessionEffectSpec:
    tenant_id: str
    request_id: str
    operation: str
    account_id: str
    customer_id: str
    policy_digest: str
    parameters_digest: str
    record_type: str = EFFECT_SPEC_VERSION

    def __post_init__(self):
        if self.record_type != EFFECT_SPEC_VERSION or self.operation not in SESSION_OPERATIONS:
            raise ServiceRuntimeError("unsupported_session_effect")
        for name in ("tenant_id", "request_id", "account_id", "customer_id"):
            identifier(getattr(self, name), name)
        exact_digest(self.policy_digest)
        exact_digest(self.parameters_digest)

    @property
    def digest(self):
        return digest(asdict(self))


@dataclass(frozen=True)
class BillingSessionReservation:
    """Issued internally for one reserved attempt, never accepted from HTTP."""

    spec: BillingSessionEffectSpec
    record_id: str
    attempt_id: str
    idempotency_key: str = field(repr=False)
    retry_before: int
    previously_confirmed: bool
    attempt_number: int
    authority_guards: tuple = field(repr=False)
    _issuer: object = field(repr=False, compare=False)
    _proof: str = field(default="", repr=False, compare=False)


def _guards(*groups):
    result = {}
    for group in groups:
        for guard in group:
            previous = result.setdefault(guard.record_id, guard)
            if previous != guard:
                raise ServiceRuntimeError("concurrent_update")
    return tuple(result.values())


class BillingSessionEffectStore:
    """Exact effect reservation and reconciliation over the existing catalogue."""

    def __init__(self, runtime: ServiceRuntime):
        if not isinstance(runtime, ServiceRuntime):
            raise ServiceRuntimeError("invalid_session_runtime")
        self.runtime, self._catalog, self._issuer = runtime, runtime._catalog, object()
        self._proof_key = secrets.token_bytes(32)

    def _proof(self, reservation):
        document = {"spec": asdict(reservation.spec), "record_id": reservation.record_id,
                    "attempt_id": reservation.attempt_id, "idempotency_key": reservation.idempotency_key,
                    "retry_before": reservation.retry_before, "previously_confirmed": reservation.previously_confirmed,
                    "attempt_number": reservation.attempt_number,
                    "guards": [asdict(guard) for guard in reservation.authority_guards]}
        return hmac.new(self._proof_key, canonical(document).encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def _payload(row, record_type):
        if row is None or row.get("payload", {}).get("record_type") != record_type:
            raise ServiceRuntimeError("session_record_unavailable")
        return row["payload"]

    def configure_policy(self, definition: BillingSessionPolicyDefinition, *, expected_version=None):
        if not isinstance(definition, BillingSessionPolicyDefinition):
            raise ServiceRuntimeError("invalid_session_policy")
        with self._catalog.store(write=True) as store:
            billing = self._catalog.read(store, BILLING_POLICY, "stripe")
            financial = self.runtime._payload(billing, BILLING_POLICY)
            if not set(definition.price_ids) <= set(financial["policy"]["allowed_price_ids"]):
                raise ServiceRuntimeError("session_price_not_in_billing_policy")
            wanted = {"record_type": SESSION_POLICY_VERSION, "policy": json.loads(definition.policy_json),
                      "policy_digest": definition.digest, "billing_policy_digest": financial["policy_digest"]}
            held = self._catalog.read(store, SESSION_POLICY_KIND, SESSION_POLICY_IDENTITY)
            if held is not None:
                if self._payload(held, SESSION_POLICY_VERSION) == wanted:
                    return {"committed": True, "record_version": held["record_version"], "policy_digest": definition.digest}
                if expected_version != held["record_version"]:
                    raise ServiceRuntimeError("session_policy_revision_required")
            elif expected_version is not None:
                raise ServiceRuntimeError("session_policy_revision_required")
            row = self._catalog.record(SESSION_POLICY_KIND, SESSION_POLICY_IDENTITY, wanted)
            self._catalog.commit(store, (row,), (self._catalog.guard(billing), self._catalog.guard(held, row["record_id"])))
        return {"committed": True, "record_version": row["record_version"], "policy_digest": definition.digest}

    def held_policy(self):
        """The stored session policy of this release's version, for an operator report. This reads.

        It returns the record version, which a later write names as its exact
        expected revision, and the two digests the record holds, or None when
        the slot of this version is empty.
        """
        with self._catalog.store() as store:
            row = self._catalog.read(store, SESSION_POLICY_KIND, SESSION_POLICY_IDENTITY)
        if row is None:
            return None
        held = self._payload(row, SESSION_POLICY_VERSION)
        return {"record_version": row["record_version"], "policy_digest": held["policy_digest"],
                "billing_policy_digest": held["billing_policy_digest"]}

    def _policy(self, store, expected_digest):
        row = self._catalog.read(store, SESSION_POLICY_KIND, SESSION_POLICY_IDENTITY)
        held = self._payload(row, SESSION_POLICY_VERSION)
        financial = self._catalog.read(store, BILLING_POLICY, "stripe")
        if (held["policy_digest"] != expected_digest or self.runtime._payload(financial, BILLING_POLICY)["policy_digest"]
                != held["billing_policy_digest"]):
            raise ServiceRuntimeError("session_policy_changed")
        return row, financial

    def policy_available(self, expected_digest):
        with self._catalog.store() as store:
            self._policy(store, expected_digest)
        return True

    def begin(self, principal, spec: BillingSessionEffectSpec, *, lease_seconds, reconciliation_seconds):
        if not isinstance(spec, BillingSessionEffectSpec):
            raise ServiceRuntimeError("invalid_session_effect")
        if (type(lease_seconds) is not int or lease_seconds <= 0 or type(reconciliation_seconds) is not int
                or not lease_seconds < reconciliation_seconds < PROVIDER_MINIMUM_IDEMPOTENCY_RETENTION_SECONDS):
            raise ServiceRuntimeError("invalid_session_effect_allowance")
        now = self.runtime._now()
        with self._catalog.store(write=True) as store:
            current, authority = self.runtime._revalidate(store, principal)
            if current.tenant_id != spec.tenant_id or BILLING_MANAGE_SCOPE not in current.scopes:
                raise ServiceRuntimeError("scope_required")
            customer = self._catalog.read(store, CUSTOMER, (spec.account_id, spec.customer_id))
            if self.runtime._payload(customer, CUSTOMER)["tenant_id"] != current.tenant_id:
                raise ServiceRuntimeError("billing_customer_binding_mismatch")
            policy, financial = self._policy(store, spec.policy_digest)
            scope = _guards(authority, (self._catalog.guard(customer), self._catalog.guard(policy), self._catalog.guard(financial)))
            identity = (current.tenant_id, spec.request_id)
            previous = self._catalog.read(store, SESSION_EFFECT_KIND, identity)
            if previous is None:
                state = {"record_type": SESSION_EFFECT_VERSION, "spec": asdict(spec), "spec_digest": spec.digest,
                         "created_at": now, "retry_before": now + reconciliation_seconds,
                         "idempotency_key": "le-session-" + uuid.uuid4().hex, "attempts": 0,
                         "status": EFFECT_PENDING, "provider_session_id": ""}
            else:
                state = dict(self._payload(previous, SESSION_EFFECT_VERSION))
                if state["spec_digest"] != spec.digest or state["spec"] != asdict(spec):
                    raise ServiceRuntimeError("session_request_identity_conflict")
                if now >= state["retry_before"]:
                    raise ServiceRuntimeError("session_reconciliation_window_exhausted")
                if state.get("lease_until", 0) > now:
                    raise ServiceRuntimeError("session_operation_in_progress")
            attempt_id = uuid.uuid4().hex
            state.update(attempt_id=attempt_id, lease_until=now + lease_seconds,
                         attempts=state["attempts"] + 1, last_attempt_at=now)
            row = self._catalog.record(SESSION_EFFECT_KIND, identity, state, tenant_id=current.tenant_id)
            self._catalog.commit(store, (row,), _guards(scope, (self._catalog.guard(previous, row["record_id"]),)))
        reservation = BillingSessionReservation(spec=spec, record_id=row["record_id"], attempt_id=attempt_id,
            idempotency_key=state["idempotency_key"], retry_before=state["retry_before"],
            previously_confirmed=state["status"] == EFFECT_CONFIRMED, attempt_number=state["attempts"],
            authority_guards=scope, _issuer=self._issuer)
        return replace(reservation, _proof=self._proof(reservation))

    def _reserved(self, store, reservation):
        if not isinstance(reservation, BillingSessionReservation) or reservation._issuer is not self._issuer:
            raise ServiceRuntimeError("unissued_session_reservation")
        if not isinstance(reservation._proof, str) or not hmac.compare_digest(reservation._proof, self._proof(reservation)):
            raise ServiceRuntimeError("unissued_session_reservation")
        row = self._catalog.read_id(store, reservation.record_id, kind=SESSION_EFFECT_KIND)
        state = self._payload(row, SESSION_EFFECT_VERSION)
        if (state["spec_digest"] != reservation.spec.digest or state["attempt_id"] != reservation.attempt_id
                or state["idempotency_key"] != reservation.idempotency_key):
            raise ServiceRuntimeError("session_reservation_changed")
        return row, state

    def authorize_dispatch(self, principal, reservation):
        """Recheck current authority and every reserved read-set guard before POST."""
        with self._catalog.store() as store:
            current, _ = self.runtime._revalidate(store, principal)
            if BILLING_MANAGE_SCOPE not in current.scopes or current.tenant_id != reservation.spec.tenant_id:
                raise ServiceRuntimeError("scope_required")
            _row, state = self._reserved(store, reservation)
            if self.runtime._now() >= min(state["lease_until"], state["retry_before"]):
                raise ServiceRuntimeError("session_reservation_expired")
            for guard in reservation.authority_guards:
                actual = store.get(guard.record_id)
                if (guard.must_not_exist and actual is not None) or (not guard.must_not_exist
                        and (actual is None or actual["record_version"] != guard.record_version)):
                    raise ServiceRuntimeError("session_authority_changed")

    def finish(self, reservation, *, provider_session_id="", response_digest="", diagnostic_code="", attempted=True):
        """Retain an already attempted outcome even if later caller authority expires."""
        if type(attempted) is not bool:
            raise ServiceRuntimeError("invalid_effect_outcome")
        if provider_session_id:
            identifier(provider_session_id, "provider session identity")
            exact_digest(response_digest)
        with self._catalog.store(write=True) as store:
            held, current = self._reserved(store, reservation)
            state = dict(current)
            if provider_session_id:
                if state["provider_session_id"] and state["provider_session_id"] != provider_session_id:
                    raise ServiceRuntimeError("provider_idempotency_identity_changed")
                state.update(status=EFFECT_CONFIRMED, provider_session_id=provider_session_id,
                             response_digest=response_digest, diagnostic_code="")
            else:
                state.update(status=EFFECT_CONFIRMED if state["provider_session_id"] else
                             EFFECT_UNKNOWN if attempted else EFFECT_NOT_ATTEMPTED,
                             diagnostic_code=diagnostic_code or "provider_commit_unknown")
            state.update(lease_until=0, attempt_id="", completed_at=self.runtime._now())
            updated = {**held, "record_version": uuid.uuid4().hex, "payload": state}
            self._catalog.commit(store, (updated,), (self._catalog.guard(held),))
        return {"record_type": "billing_session_effect_outcome/v1", "effect_ref": held["record_id"],
                "status": state["status"], "provider_session_id": state["provider_session_id"],
                "retry_before": state["retry_before"]}
