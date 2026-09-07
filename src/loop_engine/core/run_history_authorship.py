"""Authorship for Run History events: who may emit what, provably.

WHAT THE DIGEST CHAIN DOES NOT DO
Run History chains every event's digest to the previous one, so the ORDER
of events cannot be altered after the fact. Nothing in that chain says who
appended an event. Three consecutive reviews recorded the consequence: a
step handler can append a ``verify`` event reading "independent verification
passed", a ``model_invocation`` for a model that was never called, and a
``terminal`` for a Loop it does not own, and the run ends COMPLETED with its
history ACCEPTED. The chain is intact because the forger appended in order.

TWO HALVES
1. A per-run key, created by the runtime at run start and held in memory
   only. It is never written to Run History, a manifest, or any record a
   model can read. Every event body is tagged with an HMAC under that key.
   A reader holding the key can tell an event the runtime signed from one
   anything else appended.
2. A recorder facade, the only object a handler is given. It is bound to one
   loop id and to the event kinds that Loop's definition registered. It
   refuses any other kind, refuses a loop_id field that is not its own, and
   returns the signed event for the ledger to append. A handler cannot get
   at the key or the ledger through it.

WHAT THIS DOES NOT CLOSE
A handler that owns a Loop can still lie INSIDE an event kind it is allowed
to emit. That is the model's own output, and it is the verification
problem, not the authorship one. This module makes "who said it" a fact;
"is it true" stays with the gate.

COMPATIBILITY
A RunHistory built without a key behaves exactly as before, so the existing
suite is unaffected, but its manifest says ``authorship: unverified`` so a
reader can tell the two apart instead of assuming.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass, field

AUTHORSHIP_TAG_FIELD = "authorship_tag"
AUTHORSHIP_VERSION = "hmac-sha256/v1"

#: Fields the ledger assigns when it appends. They are excluded from what is
#: signed, because the facade signs BEFORE the ledger knows the sequence
#: number, the timestamp, or the previous digest. Everything a handler
#: controls is inside the signature; nothing the ledger controls is.
ENVELOPE_FIELDS = frozenset({"run_id", "sequence_number", "ts", "prev_digest",
                             "event_digest"})


def signable_projection(body: dict) -> dict:
    """The handler-controlled part of an event body, tag removed.

    Both the signer and the verifier reduce an event to this before hashing,
    so a tag computed on the facade's side verifies against the event the
    ledger actually stored. ``detail`` is copied without the tag it may carry
    after storage.
    """
    projected = {k: v for k, v in body.items()
                 if k not in ENVELOPE_FIELDS and k != AUTHORSHIP_TAG_FIELD}
    detail = projected.get("detail")
    if isinstance(detail, dict) and AUTHORSHIP_TAG_FIELD in detail:
        projected["detail"] = {k: v for k, v in detail.items()
                               if k != AUTHORSHIP_TAG_FIELD}
    return projected


class RunAuthorshipError(ValueError):
    """An event's authorship could not be established or was refused."""


def canonical_body(body: dict) -> bytes:
    """The bytes that are signed: sorted keys, compact, no NaN, the tag removed.

    The tag is removed before signing so verification can recompute over
    exactly what was signed. Everything else in the body is covered,
    including the digest chain fields, so re-parenting a signed event under
    a different predecessor breaks the tag as well as the chain.
    """
    stripped = {k: v for k, v in body.items() if k != AUTHORSHIP_TAG_FIELD}
    return json.dumps(stripped, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False,
                      default=str).encode("utf-8")


@dataclass(frozen=True)
class RunAuthorityKey:
    """The per-run signing key. Lives in the runtime's memory and nowhere else."""

    run_id: str
    _secret: bytes = field(repr=False, compare=False)

    @classmethod
    def create(cls, run_id: str) -> "RunAuthorityKey":
        if not str(run_id).strip():
            raise RunAuthorshipError("an authority key needs its run id")
        return cls(run_id=str(run_id), _secret=secrets.token_bytes(32))

    def sign(self, body: dict) -> str:
        return hmac.new(self._secret, canonical_body(signable_projection(body)),
                        hashlib.sha256).hexdigest()

    def verify(self, body: dict, tag: str) -> bool:
        if not isinstance(tag, str) or len(tag) != 64:
            return False
        return hmac.compare_digest(self.sign(body), tag)

    def __getstate__(self):
        # Refuse to be pickled, copied into a record, or otherwise leave
        # memory by accident. A key that reaches a model-visible record is a
        # key the model can sign with.
        raise RunAuthorshipError(
            "the run authority key does not leave the runtime's memory")

    def to_dict(self):
        raise RunAuthorshipError(
            "the run authority key is never serialized; record its run_id only")


@dataclass(frozen=True)
class RecorderFacade:
    """What a handler is handed instead of the ledger.

    Bound to one loop id and a closed set of event kinds. Every refusal
    names the legal set: a closed vocabulary refused without stating itself
    leaves the next attempt to guess again.
    """

    key: RunAuthorityKey
    loop_id: str
    allowed_event_types: frozenset
    #: Turns handler fields into the exact body shape the ledger will store
    #: (defaults filled, refs as lists). Injected by the ledger so this
    #: module never imports it; the ledger imports this module.
    normalize: "callable" = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.key, RunAuthorityKey):
            raise RunAuthorshipError("a recorder facade needs a RunAuthorityKey")
        if not str(self.loop_id).strip():
            raise RunAuthorshipError("a recorder facade needs its loop id")
        if not self.allowed_event_types:
            raise RunAuthorshipError(
                f"loop {self.loop_id!r} registers no event kinds; a facade "
                "that may emit nothing is a mistake, not a policy")

    def record(self, event_type: str, **fields) -> dict:
        """Return a signed event body, or refuse by name."""
        if event_type not in self.allowed_event_types:
            raise RunAuthorshipError(
                f"loop {self.loop_id!r} may not emit {event_type!r}; its "
                f"definition registers {sorted(self.allowed_event_types)}")
        claimed = fields.get("loop_id", self.loop_id)
        if claimed != self.loop_id:
            raise RunAuthorshipError(
                f"loop {self.loop_id!r} may not record an event as "
                f"{claimed!r}; a facade emits only for the Loop it is bound to")
        body = {"event_type": event_type, "loop_id": self.loop_id, **fields}
        shaped = self.normalize(body) if self.normalize is not None else body
        body[AUTHORSHIP_TAG_FIELD] = self.key.sign(shaped)
        return body


def verify_authorship(events, key: RunAuthorityKey) -> dict:
    """Report every event whose tag is missing or does not verify.

    ``events`` are mappings (or objects with ``body()``) in history order.
    Returns counts and the sequence numbers of offenders; never raises on a
    bad tag, because the caller decides what a bad tag means for the run.
    """
    unsigned, forged, verified = [], [], 0
    for index, item in enumerate(events):
        body = item.body() if hasattr(item, "body") else dict(item)
        tag = body.get(AUTHORSHIP_TAG_FIELD)
        if tag is None and isinstance(body.get("detail"), dict):
            tag = body["detail"].get(AUTHORSHIP_TAG_FIELD)
        if tag is None:
            unsigned.append(index)
        elif not key.verify(body, tag):
            forged.append(index)
        else:
            verified += 1
    return {"version": AUTHORSHIP_VERSION, "verified": verified,
            "unsigned": unsigned, "forged": forged,
            "ok": not unsigned and not forged}


def self_test() -> dict:
    """Prove signing, refusal by name, tamper detection, and key containment."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": str(detail)[:170]})

    key = RunAuthorityKey.create("run-1")
    facade = RecorderFacade(key, "loop-a", frozenset({"run_step", "custom"}))
    signed = facade.record("run_step", step="act", accepted=True)
    check("a_facade_signs_events_for_its_own_loop",
          key.verify(signed, signed[AUTHORSHIP_TAG_FIELD])
          and signed["loop_id"] == "loop-a")

    for kind, fields, frag in (
            ("verify", {}, "registers ['custom', 'run_step']"),
            ("terminal", {"loop_id": "loop-a"}, "registers"),
            ("run_step", {"loop_id": "loop-b"}, "bound to")):
        try:
            facade.record(kind, **fields)
            check(f"facade_refuses_{kind}_{'foreign' if fields else 'kind'}", False, "accepted")
        except RunAuthorshipError as exc:
            check(f"facade_refuses_{kind}_{'foreign' if fields else 'kind'}",
                  frag in str(exc), str(exc)[:100])

    tampered = dict(signed); tampered["accepted"] = False
    check("changing_a_signed_field_breaks_the_tag",
          not key.verify(tampered, tampered[AUTHORSHIP_TAG_FIELD]))
    other = RunAuthorityKey.create("run-1")
    check("another_runs_key_cannot_verify_this_runs_events",
          not other.verify(signed, signed[AUTHORSHIP_TAG_FIELD]),
          "same run id, different secret")

    forged = {"event_type": "verify", "loop_id": "loop-a",
              "output": "FORGED: independent verification passed"}
    report = verify_authorship([signed, forged, tampered], key)
    check("verify_authorship_names_unsigned_and_forged_events",
          report["verified"] == 1 and report["unsigned"] == [1]
          and report["forged"] == [2] and not report["ok"], str(report))

    for attempt, label in ((lambda: key.to_dict(), "to_dict"),
                           (lambda: __import__("pickle").dumps(key), "pickle")):
        try:
            attempt(); check(f"key_refuses_to_leave_memory_via_{label}", False)
        except RunAuthorshipError:
            check(f"key_refuses_to_leave_memory_via_{label}", True)
    check("key_repr_does_not_contain_the_secret",
          "_secret" not in repr(key) or key._secret.hex() not in repr(key))

    try:
        RecorderFacade(key, "loop-z", frozenset())
        check("a_facade_with_no_event_kinds_is_refused", False)
    except RunAuthorshipError as exc:
        check("a_facade_with_no_event_kinds_is_refused", "mistake" in str(exc))

    return {"module": "core.run_history_authorship", "tests": tests,
            "passed": all(item["passed"] for item in tests)}
