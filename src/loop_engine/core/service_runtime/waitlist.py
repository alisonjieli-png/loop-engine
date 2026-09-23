"""The public waiting list, its operator review and the invitation it leads to.

Kind: internal service adapter over the existing catalogue authority. Anyone
may leave an email address and a short note about what they want to do. An
operator reads the list and decides. An approved person is invited, and the
invitation carries a discount code that the payment provider honours at
checkout. Nothing here creates an account, sends an email, or charges anyone:
those are separate authorized effects owned by the operator command.

One entry is one address. The entry holds the address in plain text because an
operator has to read it to decide and the invitation is sent to it. The
records live in the same service collection as every other service record, in
the host's namespace, and are written through the same atomic batch contract.

A fifth operation, `forget`, erases the address and the note from an entry and
moves it to the removed state, so the service can honour a request to be taken
off the list without anyone rewriting a record row by hand. It leaves the
one-way digest of the address and the decision history. It does not change the
flood guard's count, which ends with its window. It does not apply to an
address that reached the joined state: that address belongs to an account, and
an account is removed under its own contract. The same person may ask again
afterwards, and the new request replaces the removed entry.

Four refusals matter, and each one has its own code:

```text
join refusals
├── waitlist_address_invalid        the address is not a usable email address
├── waitlist_address_already_listed this address is on the list already
├── waitlist_address_has_account    this address already has an account
└── waitlist_source_flooded         one source sent too many in the window
```

The flood guard counts accepted entries for one source inside a window. It
does not count refused attempts: the transport's existing failed-attempt limit
for each client address already counts those, and the two must not be mixed.
The guard is active only when the transport supplies a source key, which the
host's request limit settings decide, and the host names the secret that keys
the source digest. Without a declared source a proxy would make every caller
look like one source, so the count is recorded as not taken rather than taken
from a value that means nothing.

That has a price the host has to know: until the host declares where the
client address comes from and names the secret, this guard counts nobody, and
only the one entry for each address limits what a stranger can leave. The
host declares both in its own settings, and
`docs/guides/waiting-list-and-invitations.md` says what to set for a service
behind a proxy.

What the guard stores about a network address is bounded by the published
privacy notice, which promises a keyed one-way digest, never the address, and
nothing kept past the one-hour window:

```text
source record, service_waitlist_source/v2
├── named by HMAC-SHA256 of the source key under the host secret that
│   source_secret_ref names; never by the address, and never by a digest
│   anyone could recompute from a guessed address
├── holds the times of accepted entries inside the window and nothing else
└── every request removes the times that have left the window from every
    source record; a record with no time left keeps its version and an empty
    list, because the catalogue store has no removal operation
```

A host that names no secret takes no count, and the entry records
`no_source_secret`, as a host that declares no source records
`no_declared_source`. It never falls back to a plain digest. A named secret
that cannot be read, or one shorter than 32 characters, refuses the request
before any write. The reader refuses the first record version, which was named
by the address itself; this release never counts or rewrites such a record.
The window is at most one hour, the period the privacy notice promises.

A listing shows the address and the note, so it requires the administration
scope. A person who leaves an address learns only the state of their own
request, which is the state they just created.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import re
import uuid

from .records import ACCESS_MANAGE_SCOPE, ServiceRuntimeError, digest, text
from .runtime import ServiceRuntime

POLICY_VERSION = "service_waitlist_policy/v1"
REQUEST_VERSION = "service_waitlist_request/v1"
RESULT_VERSION = "service_waitlist_result/v1"
DECISION_VERSION = "service_waitlist_decision/v1"
LISTING_VERSION = "service_waitlist_listing/v1"
ENTRY_VIEW_VERSION = "service_waitlist_entry_view/v1"
ENTRY_SCHEMA = "service_waitlist_entry/v1"
#: Version two is named by a keyed digest of the source and holds only the times
#: inside the window. Version one was named by the address itself and kept its
#: times until the same address returned, so this release refuses it.
SOURCE_SCHEMA = "service_waitlist_source/v2"
SOURCE_FIELDS = frozenset({"record_type", "accepted", "window_seconds"})
ENTRY, SOURCE = "service_waitlist_entry", "service_waitlist_source"
WAITING, INVITED, JOINED, DECLINED, REMOVED = "waiting", "invited", "joined", "declined", "removed"
STATES = (WAITING, INVITED, JOINED, DECLINED, REMOVED)
INVITE, DECLINE, RECORD_JOIN, RECORD_DELIVERY = "invite", "decline", "record_join", "record_delivery"
FORGET = "forget"
OPERATIONS = (INVITE, DECLINE, RECORD_JOIN, RECORD_DELIVERY, FORGET)
#: The fields `forget` erases. Everything else in the entry is about the
#: service's own decisions, not about the person who wrote to it.
ERASED_BY_FORGET = ("email", "note")
#: (current state, operation) -> the state the entry holds afterwards.
TRANSITIONS = {(WAITING, INVITE): INVITED, (WAITING, DECLINE): DECLINED, (INVITED, DECLINE): DECLINED,
               (INVITED, RECORD_JOIN): JOINED, (INVITED, RECORD_DELIVERY): INVITED,
               (WAITING, FORGET): REMOVED, (INVITED, FORGET): REMOVED, (DECLINED, FORGET): REMOVED}
DELIVERY_STATES = ("not_attempted", "unknown", "sent")
ADDRESS_INVALID = "waitlist_address_invalid"
ADDRESS_LISTED = "waitlist_address_already_listed"
ADDRESS_HAS_ACCOUNT = "waitlist_address_has_account"
SOURCE_FLOODED = "waitlist_source_flooded"
NOT_FOUND = "waitlist_entry_not_found"
TRANSITION_REFUSED = "waitlist_transition_refused"
DIRECTORY_UNAVAILABLE = "waitlist_account_directory_unavailable"
COUNTED_SOURCE, UNCOUNTED_SOURCE = "counted", "no_declared_source"
UNKEYED_SOURCE = "no_source_secret"
SOURCE_SECRET_UNAVAILABLE = "waitlist_source_secret_unavailable"
SOURCE_SECRET_UNUSABLE = "waitlist_source_secret_unusable"
#: The host names its source secret as an environment reference, the same
#: form every other host secret takes, and never as the value itself.
ENVIRONMENT_REFERENCE = re.compile(r"env:[A-Za-z0-9_./:-]+")
#: A shorter secret could be guessed together with the address it keys.
SHORTEST_SOURCE_SECRET = 32
#: The published privacy notice promises that the times kept for an address
#: are removed once the one-hour window has passed, so no host may set more.
LONGEST_SOURCE_WINDOW_SECONDS = 3600
LONGEST_ADDRESS = 254
LONGEST_LOCAL_PART = 64
# The same address shape that tools/invite_beta_user.py accepts. An address
# this list takes has to be one the invitation command can use, so widening
# one without the other would accept a request that can never be invited.
_HOST_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_ADDRESS = re.compile(r"[a-z0-9_%+-]+(?:\.[a-z0-9_%+-]+)*@(?=[a-z0-9.-]{4,253}\Z)"
                      + _HOST_LABEL + r"(?:\." + _HOST_LABEL + r")+")
# Payment providers publish promotion codes in this shape: letters, digits and
# separators that a person can read out loud without a spelling mistake.
_DISCOUNT_CODE = re.compile(r"[A-Z0-9][A-Z0-9_-]{2,63}")
_REQUEST_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")


def _positive(value, lowest, highest, code):
    if type(value) is not int or not lowest <= value <= highest:
        raise ServiceRuntimeError(code, "a waiting list limit is outside its supported range")
    return value


def keyed_source_digest(secret, source_key):
    """The keyed one-way digest that stands for one source in every stored record.

    HMAC-SHA256 under the host secret. The record version is part of the
    message, so the same secret gives unrelated digests to another purpose.
    Without the secret nobody can test a guessed address against a record.
    """
    return hmac.new(secret.encode("utf-8"), (SOURCE_SCHEMA + "\n" + source_key).encode("utf-8"),
                    hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class WaitlistPolicy:
    """Passive host-installed limits. A request cannot widen any of them.

    `source_secret_ref` names the secret that keys the flood guard's source
    digest, as an environment reference written `env:NAME`. Empty means the
    host names no secret, and then the guard takes no count at all.
    """

    writes_authorized: bool = False
    accepted_for_each_source: int = 5
    source_window_seconds: int = 3600
    longest_note_characters: int = 280
    longest_listing: int = 200
    source_secret_ref: str = field(default="", repr=False)
    record_type: str = POLICY_VERSION

    def __post_init__(self):
        if self.record_type != POLICY_VERSION or type(self.writes_authorized) is not bool:
            raise ServiceRuntimeError("invalid_waitlist_policy")
        if not isinstance(self.source_secret_ref, str) or (
                self.source_secret_ref and ENVIRONMENT_REFERENCE.fullmatch(self.source_secret_ref) is None):
            raise ServiceRuntimeError("invalid_waitlist_policy",
                                      "the source secret is named as an environment reference, env:NAME")
        _positive(self.accepted_for_each_source, 1, 1000, "invalid_waitlist_policy")
        _positive(self.source_window_seconds, 60, LONGEST_SOURCE_WINDOW_SECONDS, "invalid_waitlist_policy")
        _positive(self.longest_note_characters, 1, 2000, "invalid_waitlist_policy")
        _positive(self.longest_listing, 1, 1000, "invalid_waitlist_policy")


@dataclass(frozen=True)
class WaitlistAccountDirectory:
    """One host-installed answer: does this address already have an account?

    The service does not hold account addresses. The identity provider does.
    A host that can ask it installs this directory; a host that cannot leaves
    it out, and then only an address whose own entry reached the joined state
    is known to have an account. An unusable answer refuses the request
    instead of admitting an address the directory was meant to exclude.
    """

    holds_address: object = field(repr=False)
    source: str = "identity_provider"

    def __post_init__(self):
        if not callable(self.holds_address):
            raise ServiceRuntimeError("invalid_waitlist_account_directory")
        text(self.source, "account directory source")

    def answers(self, address):
        try:
            answer = self.holds_address(address)
        except Exception:
            raise ServiceRuntimeError(DIRECTORY_UNAVAILABLE) from None
        if type(answer) is not bool:
            raise ServiceRuntimeError(DIRECTORY_UNAVAILABLE)
        return answer


@dataclass(frozen=True)
class WaitlistRequest:
    """One public request to be told when the service is ready for a new account."""

    email: str
    note: str = ""
    source_key: str = ""
    longest_note_characters: int = 280
    record_type: str = REQUEST_VERSION

    def __post_init__(self):
        if self.record_type != REQUEST_VERSION:
            raise ServiceRuntimeError("unsupported_waitlist_request")
        if not isinstance(self.email, str) or not isinstance(self.note, str):
            raise ServiceRuntimeError(ADDRESS_INVALID, "an email address and an optional note are required")
        address = self.email.strip().lower()
        if (len(address) > LONGEST_ADDRESS or not _ADDRESS.fullmatch(address)
                or len(address.split("@")[0]) > LONGEST_LOCAL_PART):
            raise ServiceRuntimeError(ADDRESS_INVALID, "that email address is not one this service can write to")
        note = self.note.strip()
        if len(note) > self.longest_note_characters or any(ord(character) < 32 for character in note):
            raise ServiceRuntimeError("waitlist_note_invalid", "the note is too long or holds control characters")
        if not isinstance(self.source_key, str) or len(self.source_key) > 64:
            raise ServiceRuntimeError("invalid_waitlist_source")
        object.__setattr__(self, "email", address)
        object.__setattr__(self, "note", note)

    @classmethod
    def from_dict(cls, payload, source_key="", *, longest_note_characters=280):
        """Build a request from public JSON. Unknown fields and a wrong version refuse."""
        if not isinstance(payload, dict):
            raise ServiceRuntimeError("unsupported_waitlist_request")
        if set(payload) - {"record_type", "email", "note"} or payload.get("record_type") != REQUEST_VERSION:
            raise ServiceRuntimeError("unsupported_waitlist_request")
        return cls(payload.get("email", ""), payload.get("note", ""), source_key,
                   longest_note_characters=longest_note_characters)


@dataclass(frozen=True)
class WaitlistDecision:
    """One operator decision about one entry, replayable under its own identity."""

    operation: str
    entry_ref: str
    request_id: str
    discount_code: str = ""
    invitation_ref: str = ""
    delivery: str = ""
    expected_version: str = ""
    record_type: str = DECISION_VERSION

    def __post_init__(self):
        if self.record_type != DECISION_VERSION or self.operation not in OPERATIONS:
            raise ServiceRuntimeError("unsupported_waitlist_decision")
        for name in ("entry_ref", "request_id"):
            if not isinstance(getattr(self, name), str) or not _REQUEST_ID.fullmatch(getattr(self, name)):
                raise ServiceRuntimeError("invalid_waitlist_decision", f"{name} is not a supported identity")
        if self.operation == INVITE and not _DISCOUNT_CODE.fullmatch(self.discount_code or ""):
            raise ServiceRuntimeError("waitlist_invitation_discount_required",
                                      "an invitation carries a discount code the payment provider honours")
        if self.operation != INVITE and self.discount_code:
            raise ServiceRuntimeError("invalid_waitlist_decision", "only an invitation carries a discount code")
        if self.operation == RECORD_DELIVERY and self.delivery not in ("unknown", "sent"):
            raise ServiceRuntimeError("invalid_waitlist_decision", "a delivery record states sent or unknown")
        if self.operation != RECORD_DELIVERY and self.delivery:
            raise ServiceRuntimeError("invalid_waitlist_decision", "only a delivery record states delivery")
        for name in ("invitation_ref", "expected_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or len(value) > 128 or any(ord(item) < 32 for item in value):
                raise ServiceRuntimeError("invalid_waitlist_decision", f"{name} must be short printable text")

    def identity(self):
        return digest([self.record_type, self.operation, self.entry_ref, self.request_id,
                       self.discount_code, self.invitation_ref, self.delivery])

    @classmethod
    def from_dict(cls, payload):
        if not isinstance(payload, dict) or set(payload) - {
                "record_type", "operation", "entry_ref", "request_id", "discount_code",
                "invitation_ref", "delivery", "expected_version"}:
            raise ServiceRuntimeError("unsupported_waitlist_decision")
        return cls(payload.get("operation", ""), payload.get("entry_ref", ""), payload.get("request_id", ""),
                   payload.get("discount_code", ""), payload.get("invitation_ref", ""),
                   payload.get("delivery", ""), payload.get("expected_version", ""))


class ServiceWaitlist:
    """Catalogue-backed waiting list, used by governed HTTP operations."""

    def __init__(self, runtime: ServiceRuntime, policy: WaitlistPolicy = WaitlistPolicy(), *,
                 account_directory: WaitlistAccountDirectory | None = None, secret_resolver=None):
        if (not isinstance(runtime, ServiceRuntime) or not isinstance(policy, WaitlistPolicy)
                or (account_directory is not None and not isinstance(account_directory, WaitlistAccountDirectory))
                or (secret_resolver is not None and not callable(secret_resolver))
                or (policy.source_secret_ref and secret_resolver is None)):
            raise ServiceRuntimeError("invalid_waitlist_policy")
        self.runtime, self.policy, self.account_directory = runtime, policy, account_directory
        self._secrets = secret_resolver

    @staticmethod
    def _entry(row):
        payload = row.get("payload") if row is not None else None
        if not isinstance(payload, dict) or payload.get("record_type") != ENTRY_SCHEMA:
            raise ServiceRuntimeError("unsupported_or_corrupt_record")
        if payload.get("state") not in STATES:
            raise ServiceRuntimeError("unsupported_or_corrupt_record")
        return payload

    def _view(self, row):
        payload = self._entry(row)
        return {"record_type": ENTRY_VIEW_VERSION, "entry_ref": row["record_id"],
                "entry_version": row["record_version"],
                **{name: payload.get(name) for name in (
                    "email", "note", "state", "created_at", "decided_at", "discount_code",
                    "invitation_ref", "delivery", "source_counted")}}

    def _authorize(self, store, principal):
        current, guards = self.runtime._revalidate(store, principal)
        if ACCESS_MANAGE_SCOPE not in current.scopes:
            raise ServiceRuntimeError("waitlist_administration_forbidden")
        return current, guards

    @staticmethod
    def _source_payload(row):
        """The payload of one source record of the current version, or a refusal.

        The field set is exact, so a record that carries anything beyond its
        times is refused rather than read around, and the first version, which
        was named by the address itself, is refused rather than rewritten.
        """
        payload = row.get("payload") if row is not None else None
        if (not isinstance(payload, dict) or payload.get("record_type") != SOURCE_SCHEMA
                or set(payload) != SOURCE_FIELDS or not isinstance(payload["accepted"], list)
                or any(type(value) not in (int, float) for value in payload["accepted"])):
            raise ServiceRuntimeError("unsupported_or_corrupt_record")
        return payload

    def _source_secret(self):
        """Read the host secret at use, the way every other host secret is read. It is never stored."""
        try:
            value = self._secrets(self.policy.source_secret_ref)
        except Exception:
            raise ServiceRuntimeError(SOURCE_SECRET_UNAVAILABLE,
                                      "the secret that keys the source digest cannot be read") from None
        if (not isinstance(value, str) or len(value) < SHORTEST_SOURCE_SECRET
                or any(character.isspace() or not character.isprintable() for character in value)):
            raise ServiceRuntimeError(SOURCE_SECRET_UNUSABLE,
                                      "the secret that keys the source digest is too short or not plain text")
        return value

    def _keyed_source(self, source_key):
        """The keyed digest that names one source's record, or None when the host names no secret."""
        if not self.policy.source_secret_ref:
            return None
        return keyed_source_digest(self._source_secret(), source_key)

    def _forget_expired_sources(self, store, catalog, now):
        """Remove every count that has left the window, from every source record.

        It runs on every request to join, whether or not that request is
        counted, so a source that never returns does not keep its times until
        it does. A record with no count left keeps its version and an empty
        list: the catalogue store has no removal operation, and the record's
        name is a keyed digest that nobody without the host secret can link to
        an address. Another writer that changed one of these records first is
        not an error here. That writer ran the same sweep, and the next request
        sweeps again. An unknown commit is reported, never assumed.
        """
        oldest = now - self.policy.source_window_seconds
        changed, guards = [], []
        for row in catalog.rows_all(store, SOURCE):
            payload = self._source_payload(row)
            kept = [value for value in payload["accepted"] if value > oldest]
            if kept != payload["accepted"]:
                changed.append({**row, "record_version": uuid.uuid4().hex,
                                "payload": {**payload, "accepted": kept}})
                guards.append(catalog.guard(row))
        if not changed:
            return 0
        try:
            catalog.commit(store, changed, guards)
        except ServiceRuntimeError as error:
            if error.code != "concurrent_update":
                raise
            return 0
        return len(changed)

    def _source_guard(self, store, catalog, request, now):
        """Count accepted entries for one source inside the window; refuse an obvious flood."""
        if not request.source_key:
            return None, None, UNCOUNTED_SOURCE
        keyed = self._keyed_source(request.source_key)
        if keyed is None:
            return None, None, UNKEYED_SOURCE
        row = catalog.read(store, SOURCE, keyed)
        payload = self._source_payload(row) if row is not None else {"accepted": []}
        oldest = now - self.policy.source_window_seconds
        accepted = [value for value in payload["accepted"] if value > oldest]
        if len(accepted) >= self.policy.accepted_for_each_source:
            raise ServiceRuntimeError(SOURCE_FLOODED, "this source has sent too many requests; try again later")
        changed = catalog.record(SOURCE, keyed, {
            "record_type": SOURCE_SCHEMA, "accepted": [*accepted, now][-self.policy.accepted_for_each_source:],
            "window_seconds": self.policy.source_window_seconds})
        return changed, catalog.guard(row, changed["record_id"]), COUNTED_SOURCE

    def join(self, request: WaitlistRequest):
        """Record one public request to be invited. Every refusal has its own code."""
        if not isinstance(request, WaitlistRequest):
            raise ServiceRuntimeError("unsupported_waitlist_request")
        if self.policy.writes_authorized is not True:
            raise ServiceRuntimeError("waitlist_writes_not_authorized")
        catalog, now = self.runtime._catalog, self.runtime._now()
        with catalog.store(write=True) as store:
            self._forget_expired_sources(store, catalog, now)
            existing = catalog.read(store, ENTRY, request.email)
            held = self._entry(existing).get("state") if existing is not None else None
            if held == JOINED:
                raise ServiceRuntimeError(ADDRESS_HAS_ACCOUNT, "that address already has an account")
            if self.account_directory is not None and self.account_directory.answers(request.email):
                raise ServiceRuntimeError(ADDRESS_HAS_ACCOUNT, "that address already has an account")
            # A removed entry holds nothing the person wrote, so the same
            # person may ask again and their new request replaces it.
            if existing is not None and held != REMOVED:
                raise ServiceRuntimeError(ADDRESS_LISTED, "that address is on the list already")
            source_row, source_guard, counted = self._source_guard(store, catalog, request, now)
            identity = catalog.identity(ENTRY, request.email)
            entry = catalog.record(ENTRY, request.email, {
                "record_type": ENTRY_SCHEMA, "email": request.email, "note": request.note, "state": WAITING,
                "created_at": now, "decided_at": None, "discount_code": "", "invitation_ref": "",
                "delivery": DELIVERY_STATES[0], "source_counted": counted, "decision_request_id": "",
                "address_digest": digest([request.email])})
            records = (entry,) if source_row is None else (entry, source_row)
            entry_guard = catalog.guard(existing, identity)
            guards = (entry_guard,) if source_guard is None else (entry_guard, source_guard)
            catalog.commit(store, records, guards)
            return {"record_type": RESULT_VERSION, "committed": True, "state": WAITING,
                    "entry_ref": identity, "review": "a person reads every request and decides",
                    "source_counted": counted}

    def inspect(self, principal, *, states=(WAITING,)):
        """List the entries in the selected states for an operator who may read them."""
        selected = tuple(states)
        if not selected or any(state not in STATES for state in selected) or len(set(selected)) != len(selected):
            raise ServiceRuntimeError("unsupported_waitlist_state")
        catalog = self.runtime._catalog
        with catalog.store() as store:
            self._authorize(store, principal)
            rows = catalog.rows(store, ENTRY, "")
            views = sorted((self._view(row) for row in rows), key=lambda view: (view["created_at"], view["entry_ref"]))
            counts = {state: sum(1 for view in views if view["state"] == state) for state in STATES}
            chosen = [view for view in views if view["state"] in selected]
            return {"record_type": LISTING_VERSION, "states": list(selected), "counts": counts,
                    "matched": len(chosen), "entries": chosen[:self.policy.longest_listing],
                    "truncated": len(chosen) > self.policy.longest_listing}

    def decide(self, principal, decision: WaitlistDecision):
        """Apply one operator decision. The same request identity never writes twice."""
        if not isinstance(decision, WaitlistDecision):
            raise ServiceRuntimeError("unsupported_waitlist_decision")
        if self.policy.writes_authorized is not True:
            raise ServiceRuntimeError("waitlist_writes_not_authorized")
        catalog, now = self.runtime._catalog, self.runtime._now()
        with catalog.store(write=True) as store:
            current, guards = self._authorize(store, principal)
            row = catalog.read_id(store, decision.entry_ref, kind=ENTRY)
            if row is None:
                raise ServiceRuntimeError(NOT_FOUND)
            payload = self._entry(row)
            if payload.get("decision_request_id") == decision.request_id:
                if payload.get("decision_digest") != decision.identity():
                    raise ServiceRuntimeError("waitlist_decision_identity_conflict")
                return {"record_type": RESULT_VERSION, "committed": True, "replayed": True,
                        "state": payload["state"], "entry": self._view(row), "request_id": decision.request_id}
            if decision.expected_version and decision.expected_version != row["record_version"]:
                raise ServiceRuntimeError("concurrent_update", "the entry changed; read the list again")
            state = TRANSITIONS.get((payload["state"], decision.operation))
            if state is None:
                raise ServiceRuntimeError(TRANSITION_REFUSED,
                                          "that decision does not follow from the state the entry holds")
            # Removal erases what the person wrote. The entry itself stays, so
            # that the decision history and the flood count keep their meaning,
            # and it keeps only the one-way digest of the address it started
            # from. An entry whose address has an account is not removed here:
            # that address belongs to the account, not to the waiting list.
            erased = {name: "" for name in ERASED_BY_FORGET} if decision.operation == FORGET else {}
            changed = {**row, "record_version": uuid.uuid4().hex, "payload": {
                **payload, **erased, "state": state, "decided_at": now, "decided_by": current.key_id,
                "decision_request_id": decision.request_id, "decision_digest": decision.identity(),
                "discount_code": decision.discount_code or payload.get("discount_code", ""),
                "invitation_ref": decision.invitation_ref or payload.get("invitation_ref", ""),
                "delivery": decision.delivery or payload.get("delivery", DELIVERY_STATES[0])}}
            catalog.commit(store, (changed,), (*guards, catalog.guard(row)))
            return {"record_type": RESULT_VERSION, "committed": True, "replayed": False, "state": state,
                    "entry": self._view(changed), "request_id": decision.request_id}


def join_request(waitlist, payload, source_key):
    """Build one public request against the installed list, or say no list is installed."""
    if waitlist is None:
        raise ServiceRuntimeError("waitlist_unavailable", "this service does not keep a waiting list")
    return WaitlistRequest.from_dict(payload, source_key,
                                     longest_note_characters=waitlist.policy.longest_note_characters)


def administer_waitlist(waitlist, current, payload):
    """Read the whole list, or apply one decision, for an operator whose sign-in was checked again.

    The transport checks the administration scope before it reads a body. This
    checks it again on the authentication that is current at the moment of the
    work, so a scope that was withdrawn in between cannot read an address.
    """
    if waitlist is None:
        raise ServiceRuntimeError("waitlist_unavailable", "this service does not keep a waiting list")
    if ACCESS_MANAGE_SCOPE not in current.effective_scopes:
        raise ServiceRuntimeError("waitlist_administration_forbidden")
    return (waitlist.inspect(current.principal, states=STATES) if payload is None
            else waitlist.decide(current.principal, WaitlistDecision.from_dict(payload)))
