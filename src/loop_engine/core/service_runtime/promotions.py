"""Promotion codes: paid service access granted by a code instead of a payment.

This is an internal service adapter over the existing catalogue authority and
the existing entitlement path. It adds no runtime type, no second store and no
graph vertex. A promotion code is a passive typed record. Redeeming one writes
the same `service_entitlement` record that `set_operator_entitlement` writes,
with its own source, so a comped account stays separate from a paying one in
every record and in every report.

The surface is two host-installed objects. `PromotionCodeAdministration` is the
operator side: create, list, suspend and expire. `PromotionRedemption` is the
customer side: one authenticated account offers one code and receives the
entitlement that the code declares. Nothing here reads meaning out of the code
text; every effect comes from a separate typed field of the stored record.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import re
import secrets
import uuid

from .records import ENTITLEMENTS, ServicePrincipal, ServiceRuntimeError, digest, identifier, text
from .runtime import (BILLING_POLICY, BODIES, CODE_GRANT_SOURCE, COMPED_SOURCES, ENTITLEMENT, PROMOTION_ACCOUNT,
                      PROMOTION_CODE, PROMOTION_REDEMPTION, REVENUE_BEARING_SOURCES, SCHEMAS, ServiceRuntime)

PROMOTION_POLICY_VERSION = "service_promotion_policy/v1"
PROMOTION_GRANT_VERSION = "service_promotion_grant/v1"
PROMOTION_DEFINITION_VERSION = "service_promotion_code_definition/v1"
PROMOTION_STATE_VERSION = "service_promotion_code_state/v1"
PROMOTION_REQUEST_VERSION = "service_promotion_redemption_request/v1"
PROMOTION_RESULT_VERSION = "service_promotion_redemption_result/v1"
PROMOTION_LISTING_VERSION = "service_promotion_code_listing/v1"
PROMOTION_CODE_VIEW_VERSION = "service_promotion_code_view/v1"

#: Exact reasons. They stay inside this process and reach an operator. They are
#: never returned to the person who offered a code.
REASON_UNKNOWN_CODE = "unknown_code"
REASON_SUSPENDED = "code_suspended"
REASON_NOT_STARTED = "code_has_not_started"
REASON_EXPIRED = "code_expired"
REASON_EXHAUSTED = "code_redemptions_exhausted"
REASON_ALREADY_REDEEMED = "account_already_redeemed_this_code"
REASON_PAID_SUBSCRIPTION = "account_already_has_paid_access_from_a_payment"
REASON_ACCESS_REVOKED = "account_body_access_revoked_by_the_host"
REASON_NOT_AUTHENTICATED = "no_authenticated_account"
REASON_NOT_INSTALLED = "redemption_not_installed"

#: The word in the reason vocabulary that names no refusal at all.
NO_REFUSAL = ""
#: Every state condition a code itself can fail, in the order they are reported.
CODE_STATE_REASONS = (REASON_UNKNOWN_CODE, REASON_SUSPENDED, REASON_NOT_STARTED, REASON_EXPIRED, REASON_EXHAUSTED)

#: Disclosed refusals. Every reason that depends on the code itself discloses
#: one word, so an attempt cannot tell a code this service never issued from a
#: real code that has run out. The reasons that depend on the account are told
#: apart, because they describe the caller's own account and disclose no code.
CODE_UNUSABLE = "promotion_code_unusable"
ALREADY_REDEEMED = "promotion_code_already_redeemed_by_this_account"
PAID_ACCESS_ACTIVE = "paid_subscription_active"
REDEMPTION_FORBIDDEN = "promotion_redemption_forbidden"
ACCOUNT_REQUIRED = "promotion_redemption_requires_an_account"
REDEMPTION_UNAVAILABLE = "promotion_redemption_unavailable"
DISCLOSED_REFUSAL = {
    **{reason: CODE_UNUSABLE for reason in CODE_STATE_REASONS},
    REASON_ALREADY_REDEEMED: ALREADY_REDEEMED, REASON_PAID_SUBSCRIPTION: PAID_ACCESS_ACTIVE,
    REASON_ACCESS_REVOKED: REDEMPTION_FORBIDDEN, REASON_NOT_AUTHENTICATED: ACCOUNT_REQUIRED,
    REASON_NOT_INSTALLED: REDEMPTION_UNAVAILABLE}

GRANT_LIMITATIONS = (
    "A redeemed code grants the recorded service entitlement until the recorded moment, and nothing else.",
    "It grants no model allowance, no spending authority and no permission to execute code.",
    "It is not a payment. The record names a promotion code grant and is never counted as revenue.")

_CODE_TEXT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{7,127}")
LONGEST_LABEL = 100
LONGEST_APPROVAL = 200
SHORTEST_GRANT_SECONDS = 3600
LONGEST_GRANT_SECONDS = 366 * 24 * 3600
MOST_REDEMPTIONS = 100_000
DISPLAY_LIMIT = 500


def code_digest(value):
    """The stored identity of a code. The code text itself is never stored."""
    if not isinstance(value, str) or _CODE_TEXT.fullmatch(value) is None:
        raise ServiceRuntimeError("invalid_promotion_code",
                                  "a promotion code is 8 to 128 letters, digits, hyphens or underscores")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class PromotionRefused(ServiceRuntimeError):
    """One refusal with two separate words.

    `code` is what the caller is told. `reason` is the exact reason; it is kept
    for the operator and for the checks and it never leaves this process.
    """

    def __init__(self, reason):
        if reason not in DISCLOSED_REFUSAL:
            raise ServiceRuntimeError("unsupported_promotion_refusal")
        super().__init__(DISCLOSED_REFUSAL[reason], "promotion code refused")
        self.reason = reason


@dataclass(frozen=True)
class PromotionPolicy:
    """Host settings. Redemption is served only when the host enables it."""

    redemption_enabled: bool = False
    maximum_listed_codes: int = DISPLAY_LIMIT
    record_type: str = PROMOTION_POLICY_VERSION

    def __post_init__(self):
        if self.record_type != PROMOTION_POLICY_VERSION:
            raise ServiceRuntimeError("unsupported_promotion_policy")
        if (type(self.redemption_enabled) is not bool or type(self.maximum_listed_codes) is not int
                or not 1 <= self.maximum_listed_codes <= 10_000):
            raise ServiceRuntimeError("invalid_promotion_policy")


@dataclass(frozen=True)
class PromotionGrant:
    """Exactly what one redemption gives, in separate fields.

    Nothing here is read from the code text, the label or the approval note.
    """

    entitlement: str = BODIES
    seconds: int = 30 * 24 * 3600
    record_type: str = PROMOTION_GRANT_VERSION

    def __post_init__(self):
        if self.record_type != PROMOTION_GRANT_VERSION:
            raise ServiceRuntimeError("unsupported_promotion_grant")
        if self.entitlement not in ENTITLEMENTS or self.entitlement != BODIES:
            raise ServiceRuntimeError("unsupported_promotion_grant",
                                      "a promotion code grants the body entitlement; metadata is already free")
        if type(self.seconds) is not int or not SHORTEST_GRANT_SECONDS <= self.seconds <= LONGEST_GRANT_SECONDS:
            raise ServiceRuntimeError("invalid_promotion_grant",
                                      "a promotion grant lasts from one hour to one year")


@dataclass(frozen=True)
class PromotionCodeDefinition:
    """One operator-created code. Every effect is a separate declared field."""

    code: str = field(repr=False)
    label: str
    grant: PromotionGrant
    redemptions_allowed: int
    repeat_allowed_for_one_account: bool
    starts_at: int
    expires_at: int
    approved_by: str
    approval_ref: str
    record_type: str = PROMOTION_DEFINITION_VERSION

    def __post_init__(self):
        if self.record_type != PROMOTION_DEFINITION_VERSION:
            raise ServiceRuntimeError("unsupported_promotion_definition")
        code_digest(self.code)
        if not isinstance(self.grant, PromotionGrant):
            raise ServiceRuntimeError("invalid_promotion_grant")
        text(self.label, "promotion label")
        text(self.approved_by, "promotion approver")
        text(self.approval_ref, "promotion approval reference")
        if (len(self.label) > LONGEST_LABEL or len(self.approved_by) > LONGEST_APPROVAL
                or len(self.approval_ref) > LONGEST_APPROVAL):
            raise ServiceRuntimeError("invalid_promotion_definition")
        if type(self.repeat_allowed_for_one_account) is not bool:
            raise ServiceRuntimeError("invalid_promotion_definition",
                                      "repeat redemption is an explicit Boolean choice")
        if type(self.redemptions_allowed) is not int or not 1 <= self.redemptions_allowed <= MOST_REDEMPTIONS:
            raise ServiceRuntimeError("invalid_promotion_definition",
                                      "a code allows between one and one hundred thousand redemptions")
        for name in ("starts_at", "expires_at"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ServiceRuntimeError("invalid_promotion_window", f"{name} must be an epoch second")
        if self.starts_at >= self.expires_at:
            raise ServiceRuntimeError("invalid_promotion_window", "a code starts before it expires")

    @property
    def digest(self):
        return code_digest(self.code)


@dataclass(frozen=True)
class PromotionCodeState:
    """Every state condition of one code, all evaluated, and the first refusal.

    `promotion_code_state` fills every field for every attempt, including an
    attempt with a code this service never issued. A caller that stopped at the
    first condition would leave the later fields unset and fail its check.
    """

    known: bool
    suspended: bool
    not_started: bool
    expired: bool
    exhausted: bool
    record_type: str = PROMOTION_STATE_VERSION

    @property
    def reason(self):
        matched = {REASON_UNKNOWN_CODE: not self.known, REASON_SUSPENDED: self.suspended,
                   REASON_NOT_STARTED: self.not_started, REASON_EXPIRED: self.expired,
                   REASON_EXHAUSTED: self.exhausted}
        return next((name for name in CODE_STATE_REASONS if matched[name]), NO_REFUSAL)

    @property
    def redeemable(self):
        """True when no state condition of the code itself refuses it."""
        return self.reason == NO_REFUSAL


#: The stand-in that an unknown code is evaluated against, so that a guess runs
#: exactly the comparisons a real code runs. Its fields make every condition
#: true, and `known` is the only field that names it as a stand-in.
ABSENT_CODE = {"record_type": SCHEMAS[PROMOTION_CODE], "code_id": "", "enabled": False,
               "starts_at": 1, "expires_at": 0, "redemptions_allowed": 0, "redemptions_used": 0,
               "repeat_allowed_for_one_account": False, "approval_ref": "", "approved_by": "",
               "grant": asdict(PromotionGrant())}


def promotion_code_state(payload, now) -> PromotionCodeState:
    """Evaluate every state condition of one code against the current moment."""
    known = payload is not ABSENT_CODE
    return PromotionCodeState(
        known=known,
        suspended=payload.get("enabled") is not True,
        not_started=now < payload.get("starts_at", 0),
        expired=now >= payload.get("expires_at", 0),
        exhausted=payload.get("redemptions_used", 0) >= payload.get("redemptions_allowed", 0))


@dataclass(frozen=True)
class PromotionRedemptionRequest:
    """One offered code under one request identity. The code stays out of repr."""

    code: str = field(repr=False)
    request_id: str
    record_type: str = PROMOTION_REQUEST_VERSION

    def __post_init__(self):
        if self.record_type != PROMOTION_REQUEST_VERSION:
            raise ServiceRuntimeError("unsupported_version")
        code_digest(self.code)
        identifier(self.request_id, "request identity")

    @classmethod
    def from_dict(cls, value):
        if (not isinstance(value, dict) or set(value) - {"record_type", "code", "request_id"}
                or value.get("record_type") != PROMOTION_REQUEST_VERSION):
            raise ServiceRuntimeError("invalid_promotion_request")
        try:
            return cls(**value)
        except TypeError:
            raise ServiceRuntimeError("invalid_promotion_request") from None

    @property
    def digest(self):
        return code_digest(self.code)

    def identity(self):
        """The request identity covers the offered code, not only its name."""
        return digest({"record_type": self.record_type, "request_id": self.request_id,
                       "code_digest": self.digest})


def _code_view(payload, now, redemptions=()):
    """The operator view of one code. It never holds the code text."""
    state = promotion_code_state(payload, now)
    return {"record_type": PROMOTION_CODE_VIEW_VERSION, "code_id": payload["code_id"],
            "label": payload["label"], "grant": payload["grant"],
            "redemptions_allowed": payload["redemptions_allowed"],
            "redemptions_used": payload["redemptions_used"],
            "repeat_allowed_for_one_account": payload["repeat_allowed_for_one_account"],
            "starts_at": payload["starts_at"], "expires_at": payload["expires_at"],
            "approved_by": payload["approved_by"], "approval_ref": payload["approval_ref"],
            "created_at": payload.get("created_at"), "enabled": payload["enabled"],
            "redeemable_now": state.redeemable, "state_reason": state.reason,
            "redeemed_by": sorted(redemptions)}


class PromotionCodeAdministration:
    """Host-side creation and lifecycle of promotion codes.

    This runs where `set_operator_entitlement` runs: in the host process, under
    the host's own write authority. It is not reachable from a request, and it
    never returns or prints a code that the caller did not just supply.
    """

    def __init__(self, runtime: ServiceRuntime, policy: PromotionPolicy = PromotionPolicy()):
        if not isinstance(runtime, ServiceRuntime) or not isinstance(policy, PromotionPolicy):
            raise ServiceRuntimeError("invalid_promotion_policy")
        self.runtime, self.policy = runtime, policy

    def create(self, definition: PromotionCodeDefinition, *, confirmed=False):
        """Write one code record. Creating a code needs explicit confirmation."""
        if not isinstance(definition, PromotionCodeDefinition):
            raise ServiceRuntimeError("invalid_promotion_definition")
        if confirmed is not True:
            raise ServiceRuntimeError("promotion_confirmation_required",
                                      "creating a promotion code requires explicit confirmation")
        catalog = self.runtime._catalog
        now = int(self.runtime._now())
        if definition.expires_at <= now:
            raise ServiceRuntimeError("invalid_promotion_window", "a new code expires in the future")
        code_id = uuid.uuid4().hex
        with catalog.store(write=True) as store:
            held = catalog.read(store, PROMOTION_CODE, definition.digest)
            if held is not None:
                raise ServiceRuntimeError("promotion_code_already_exists")
            row = catalog.record(PROMOTION_CODE, definition.digest, {
                "record_type": SCHEMAS[PROMOTION_CODE], "code_id": code_id,
                "code_digest": definition.digest, "label": definition.label,
                "grant": asdict(definition.grant), "redemptions_allowed": definition.redemptions_allowed,
                "redemptions_used": 0,
                "repeat_allowed_for_one_account": definition.repeat_allowed_for_one_account,
                "starts_at": definition.starts_at, "expires_at": definition.expires_at,
                "approved_by": definition.approved_by, "approval_ref": definition.approval_ref,
                "enabled": True, "created_at": now})
            catalog.commit(store, (row,), (catalog.guard(None, row["record_id"]),))
        return {"record_type": "service_promotion_code_created/v1", "committed": True,
                "code_id": code_id, "label": definition.label,
                "redemptions_allowed": definition.redemptions_allowed,
                "expires_at": definition.expires_at, "grant": asdict(definition.grant),
                "code_returned": False, "limitations": list(GRANT_LIMITATIONS)}

    def _rows(self, store):
        return [(row, self.runtime._payload(row, PROMOTION_CODE))
                for row in self.runtime._catalog.rows_all(store, PROMOTION_CODE)]

    def _redemptions(self, store):
        """Which accounts redeemed which code, from the per-account records."""
        held = {}
        for row in self.runtime._catalog.rows_all(store, PROMOTION_ACCOUNT):
            value = self.runtime._payload(row, PROMOTION_ACCOUNT)
            held.setdefault(value["code_id"], []).append(value["tenant_id"])
        return held

    def inspect(self):
        """Every code with its counts and the accounts that redeemed it."""
        now = int(self.runtime._now())
        with self.runtime._catalog.store() as store:
            rows = self._rows(store)
            redeemed = self._redemptions(store)
        views = [_code_view(value, now, redeemed.get(value["code_id"], ()))
                 for _row, value in sorted(rows, key=lambda pair: -(pair[1].get("created_at") or 0))]
        return {"record_type": PROMOTION_LISTING_VERSION, "codes": views[:self.policy.maximum_listed_codes],
                "total_codes": len(views), "display_limit": self.policy.maximum_listed_codes,
                "redemptions": sum(view["redemptions_used"] for view in views),
                "codes_returned": False,
                "disclosure": "A code is stored as a digest. This listing cannot show a code text."}

    def _change(self, code_id, change, expected):
        identifier(code_id, "promotion code identity")
        catalog = self.runtime._catalog
        with catalog.store(write=True) as store:
            selected = [(row, value) for row, value in self._rows(store) if value["code_id"] == code_id]
            if len(selected) != 1:
                raise ServiceRuntimeError("promotion_code_not_found")
            row, value = selected[0]
            updated = {**row, "record_version": uuid.uuid4().hex, "payload": {**value, **change}}
            catalog.commit(store, (updated,), (catalog.guard(row),))
        return {"record_type": "service_promotion_code_change/v1", "committed": True,
                "code_id": code_id, "operation": expected,
                "code": _code_view(updated["payload"], int(self.runtime._now()))}

    def suspend(self, code_id):
        """Stop new redemptions. Access already granted stays until it expires."""
        return self._change(code_id, {"enabled": False, "suspended_at": int(self.runtime._now())}, "suspend")

    def expire(self, code_id, *, at=None):
        """Close the window. Access already granted stays until it expires."""
        moment = int(self.runtime._now()) if at is None else at
        if type(moment) is not int or moment <= 0:
            raise ServiceRuntimeError("invalid_promotion_window", "an expiry is an epoch second")
        return self._change(code_id, {"expires_at": moment}, "expire")


class PromotionRedemption:
    """Customer-side redemption of one code by one authenticated account.

    The write is one atomic batch over the existing catalogue read-set: the code
    record with its exact revision, the per-account record, the request identity
    and the entitlement commit together or not at all.
    """

    def __init__(self, runtime: ServiceRuntime, policy: PromotionPolicy):
        if not isinstance(runtime, ServiceRuntime) or not isinstance(policy, PromotionPolicy):
            raise ServiceRuntimeError("invalid_promotion_policy")
        self.runtime, self.policy = runtime, policy

    def _paid_by_payment(self, entitlement_row, policy, now):
        """True only when this account's access comes from a provider snapshot."""
        if entitlement_row is None:
            return False
        value = self.runtime._payload(entitlement_row, ENTITLEMENT)
        return (value.get("source") in REVENUE_BEARING_SOURCES
                and self.runtime._entitlement(entitlement_row, policy) == BODIES
                and type(value.get("valid_until")) is int and value["valid_until"] > now)

    def _retained_expiry(self, entitlement_row, now):
        """Comped access the account already holds. A redemption never shortens it."""
        if entitlement_row is None:
            return 0
        value = self.runtime._payload(entitlement_row, ENTITLEMENT)
        until = value.get("valid_until")
        if (value.get("enabled") is True and value.get("entitlement") == BODIES
                and value.get("source") in COMPED_SOURCES and type(until) is int and until > now):
            return until
        return 0

    def redeem(self, principal, request: PromotionRedemptionRequest):
        """Redeem one code for the account that the issued principal names."""
        if not isinstance(request, PromotionRedemptionRequest):
            raise ServiceRuntimeError("invalid_promotion_request")
        if self.policy.redemption_enabled is not True:
            raise PromotionRefused(REASON_NOT_INSTALLED)
        if not isinstance(principal, ServicePrincipal):
            raise PromotionRefused(REASON_NOT_AUTHENTICATED)
        catalog = self.runtime._catalog
        with catalog.store(write=True) as store:
            current, guards = self.runtime._revalidate(store, principal)
            identity = (current.tenant_id, request.request_id)
            held = catalog.read(store, PROMOTION_REDEMPTION, identity)
            if held is not None:
                previous = self.runtime._payload(held, PROMOTION_REDEMPTION)
                if previous.get("request_digest") != request.identity():
                    raise ServiceRuntimeError("promotion_request_identity_conflict")
                return {**previous["result"], "replayed": True}
            now = int(self.runtime._now())
            _tenant_row, tenant = self.runtime._tenant(store, current.tenant_id)
            if tenant.get("body_access_revoked") is not False:
                raise PromotionRefused(REASON_ACCESS_REVOKED)
            entitlement_row = catalog.read(store, ENTITLEMENT, current.tenant_id)
            policy = catalog.read(store, BILLING_POLICY, "stripe")
            if self._paid_by_payment(entitlement_row, policy, now):
                raise PromotionRefused(REASON_PAID_SUBSCRIPTION)
            code_row = catalog.read(store, PROMOTION_CODE, request.digest)
            payload = ABSENT_CODE
            if code_row is not None:
                candidate = self.runtime._payload(code_row, PROMOTION_CODE)
                if secrets.compare_digest(str(candidate.get("code_digest", "")), request.digest):
                    payload = candidate
            state = promotion_code_state(payload, now)
            # The per-account record is read before the state decides, so a code
            # this service never issued performs the same reads as a real code
            # that has run out. The stand-in identity never matches a record.
            account_row = catalog.read(store, PROMOTION_ACCOUNT, (payload["code_id"], current.tenant_id))
            if state.reason:
                raise PromotionRefused(state.reason)
            account = self.runtime._payload(account_row, PROMOTION_ACCOUNT) if account_row is not None else None
            if account is not None and payload["repeat_allowed_for_one_account"] is not True:
                raise PromotionRefused(REASON_ALREADY_REDEEMED)
            result, records, written = self._grant(catalog, current, request, payload, code_row,
                                                   account_row, account, entitlement_row, now)
            unique = {}
            for guard in (*guards, catalog.guard(code_row),
                          catalog.guard(account_row, written["account"]),
                          catalog.guard(None, written["event"])):
                if guard.record_id in unique and unique[guard.record_id] != guard:
                    raise ServiceRuntimeError("concurrent_update")
                unique[guard.record_id] = guard
            catalog.commit(store, records, tuple(unique.values()))
        return {**result, "replayed": False}

    def _grant(self, catalog, current, request, payload, code_row, account_row, account, entitlement_row, now):
        """Build the four rows that one redemption commits together.

        The count is checked again here, against the same payload that is about
        to be written. `promotion_code_state` decides whether an attempt may
        proceed; this is the last line before the write, so a wrong state
        evaluation cannot commit a count past the allowance.
        """
        grant = payload["grant"]
        if payload["redemptions_used"] + 1 > payload["redemptions_allowed"]:
            raise PromotionRefused(REASON_EXHAUSTED)
        valid_until = max(now + grant["seconds"], self._retained_expiry(entitlement_row, now))
        previous = (self.runtime._payload(entitlement_row, ENTITLEMENT) if entitlement_row is not None else {})
        code = {**code_row, "record_version": uuid.uuid4().hex,
                "payload": {**payload, "redemptions_used": payload["redemptions_used"] + 1,
                            "last_redeemed_at": now}}
        account_write = catalog.record(PROMOTION_ACCOUNT, (payload["code_id"], current.tenant_id), {
            "record_type": SCHEMAS[PROMOTION_ACCOUNT], "tenant_id": current.tenant_id,
            "code_id": payload["code_id"], "redemptions": ((account or {}).get("redemptions", 0) + 1),
            "first_redeemed_at": (account or {}).get("first_redeemed_at", now),
            "last_redeemed_at": now}, tenant_id=current.tenant_id)
        entitlement = catalog.record(ENTITLEMENT, current.tenant_id, {
            "record_type": SCHEMAS[ENTITLEMENT], "tenant_id": current.tenant_id, "enabled": True,
            "entitlement": grant["entitlement"], "valid_until": valid_until,
            "source": CODE_GRANT_SOURCE, "promotion_code_id": payload["code_id"],
            "approval_ref": payload["approval_ref"], "approved_by": payload["approved_by"],
            "previous_source": previous.get("source", ""),
            "previous_valid_until": previous.get("valid_until")}, tenant_id=current.tenant_id)
        result = {"record_type": PROMOTION_RESULT_VERSION, "granted": True, "committed": True,
                  "tenant_id": current.tenant_id, "promotion_code_id": payload["code_id"],
                  "label": payload["label"], "entitlement": grant["entitlement"],
                  "valid_until": valid_until, "source": CODE_GRANT_SOURCE, "payment": False,
                  "approval_ref": payload["approval_ref"], "request_id": request.request_id,
                  "limitations": list(GRANT_LIMITATIONS)}
        event = catalog.record(PROMOTION_REDEMPTION, (current.tenant_id, request.request_id), {
            "record_type": SCHEMAS[PROMOTION_REDEMPTION], "tenant_id": current.tenant_id,
            "request_digest": request.identity(), "promotion_code_id": payload["code_id"],
            "result": result, "redeemed_at": now,
            "authentication_record_id": current.authentication_record_id}, tenant_id=current.tenant_id)
        return (result, (code, account_write, entitlement, event),
                {"account": account_write["record_id"], "event": event["record_id"]})


def self_test():
    from .promotion_checks import run_checks
    return run_checks()
