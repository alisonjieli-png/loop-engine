"""What an outside service can do for a run, recorded without its credentials.

A growing share of useful work is not code this repository holds. It is a
service someone else operates, reached over the network, that books, sends,
pays, looks up, or files something. A run that wants to use one needs facts
that no local capability record carries: who operates it, how a caller proves
it may call, what a call costs, how often it may be called, whether calling
twice does the work twice, and under whose terms.

WHAT THIS IS NOT
It is not a credential store. An entry names the credential the host holds,
never the value, and text that matches this repository's own secret patterns
is refused before the record exists. It is not an execution path either:
selecting, ranking, and comparing entries reaches nothing, so discovery stays
effect free and a run that only looks has done nothing to the world.

THREE AUTHORITIES, KEPT APART
Reaching the network, spending money, and changing state outside this system
are three different permissions. An entry declares each one, and a step that
holds fewer is not offered the entry at all, with the reason recorded. An
instruction that describes an authority the step lacks teaches the step to
try, and the same is true of an offer.

QUALIFICATION IS NOT SELF DECLARED
An entry arrives as a candidate. It becomes qualified only when a reviewer who
is not its producer says so, and the review names what it checked. A service
that answers a probe well has shown that it answered a probe.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .facets import EFFECTS

RECORD_TYPE = "external_service_capability/v1"
OFFER_RECORD_TYPE = "external_service_offer/v1"
REVIEW_RECORD_TYPE = "external_service_review/v1"
#: How a caller proves it may call. The secret itself never appears in a record.
AUTHENTICATION_KINDS = ("none", "api_key", "oauth", "signed_request", "mutual_tls")
#: Whether calling twice does the work twice.
IDEMPOTENCY = ("unknown", "idempotent", "at_most_once", "no_overwrite")
#: Candidate until a different process says otherwise.
QUALIFICATION = ("candidate", "qualified", "withdrawn")
#: Reaching a service over the network is the one effect every entry declares.
NETWORK_EFFECT = "network"
DIGEST_LENGTH = 64


class ExternalServiceError(ValueError):
    """An entry is missing a fact a caller needs, or carries something it must not."""


@dataclass(frozen=True)
class CallAuthority:
    """The three permissions an outside call can need, declared separately."""

    network: bool = False
    spend: bool = False
    external_mutation: bool = False

    def covers(self, other: "CallAuthority") -> bool:
        """True when this authority is at least what the other one asks for."""
        return ((self.network or not other.network)
                and (self.spend or not other.spend)
                and (self.external_mutation or not other.external_mutation))

    def missing(self, other: "CallAuthority") -> tuple[str, ...]:
        names = []
        if other.network and not self.network:
            names.append("network")
        if other.spend and not self.spend:
            names.append("spend")
        if other.external_mutation and not self.external_mutation:
            names.append("external_mutation")
        return tuple(names)


#: A credential reference names a credential; a long unbroken token is a value.
OPAQUE_TOKEN_LENGTH = 24


def _looks_like_a_value(text: str) -> bool:
    """True when a supposed reference looks like the secret itself.

    The repository's seven secret patterns catch the shapes they were written
    for. A key from a provider nobody has written a pattern for still looks
    like a key: a long unbroken run of token characters with no separator that
    a human name would have. That is refused too, because a reference someone
    can read aloud is the point.
    """
    import re
    return bool(re.search(r"[A-Za-z0-9+/=_-]{%d,}" % OPAQUE_TOKEN_LENGTH,
                          re.sub(r"[.:/\s]", " ", text)))


def _secret_shaped(text: str) -> str:
    """The first secret pattern the text matches, or an empty string."""
    import re
    from .model_call_records import default_secret_patterns
    for pattern in default_secret_patterns():
        if re.search(pattern, text):
            return pattern
    return ""


@dataclass(frozen=True)
class ExternalServiceCapability:
    """One thing an outside service can do, with the facts a caller needs first."""

    identity: str
    operator: str
    purpose: str
    endpoint_ref: str
    contract_ref: str
    authentication: str = AUTHENTICATION_KINDS[0]
    credential_ref: str = ""
    requires: CallAuthority = field(default_factory=CallAuthority)
    declared_effects: tuple[str, ...] = (NETWORK_EFFECT,)
    idempotency: str = IDEMPOTENCY[0]
    price_note: str = ""
    price_source: str = ""
    rate_limit_note: str = ""
    terms_ref: str = ""
    qualification: str = QUALIFICATION[0]
    observed_note: str = ""

    def __post_init__(self) -> None:
        for name in ("identity", "operator", "purpose", "endpoint_ref", "contract_ref"):
            if not str(getattr(self, name)).strip():
                raise ExternalServiceError(
                    f"an external service entry needs its {name}")
        if self.authentication not in AUTHENTICATION_KINDS:
            raise ExternalServiceError(
                f"authentication must be one of {AUTHENTICATION_KINDS}")
        if self.idempotency not in IDEMPOTENCY:
            raise ExternalServiceError(f"idempotency must be one of {IDEMPOTENCY}")
        if self.qualification not in QUALIFICATION:
            raise ExternalServiceError(f"qualification must be one of {QUALIFICATION}")
        if not isinstance(self.requires, CallAuthority):
            raise ExternalServiceError("required authority must be the typed record")
        unknown = [effect for effect in self.declared_effects if effect not in EFFECTS]
        if unknown:
            raise ExternalServiceError(
                f"{unknown} is not drawn from the declared effects {EFFECTS}")
        if NETWORK_EFFECT not in self.declared_effects or not self.requires.network:
            raise ExternalServiceError(
                f"{self.identity!r} is reached over the network, so it declares the "
                f"{NETWORK_EFFECT!r} effect and requires network authority")
        if self.authentication != AUTHENTICATION_KINDS[0] and not self.credential_ref.strip():
            raise ExternalServiceError(
                f"{self.identity!r} authenticates with {self.authentication!r}, so it must "
                "name the credential the host holds; the value itself never appears here")
        if self.credential_ref.strip() and _looks_like_a_value(self.credential_ref):
            raise ExternalServiceError(
                f"{self.identity!r} names a credential that reads like the credential itself; "
                "an entry carries the name the host resolves, never the value")
        if self.requires.spend and not self.price_note.strip():
            raise ExternalServiceError(
                f"{self.identity!r} spends money, so it must carry the price it was read "
                "with; an unknown price is not a small price")
        if self.price_note.strip() and not self.price_source.strip():
            raise ExternalServiceError(
                f"{self.identity!r} states a price, so it must name where that price was read")
        found = _secret_shaped(json.dumps(self.to_dict(), sort_keys=True))
        if found:
            raise ExternalServiceError(
                f"{self.identity!r} carries text matching a secret pattern; an entry names "
                "the credential the host holds and never its value")

    def to_dict(self) -> dict:
        return {"record_type": RECORD_TYPE, "identity": self.identity,
                "operator": self.operator, "purpose": self.purpose,
                "endpoint_ref": self.endpoint_ref, "contract_ref": self.contract_ref,
                "authentication": self.authentication, "credential_ref": self.credential_ref,
                "requires": {"network": self.requires.network, "spend": self.requires.spend,
                             "external_mutation": self.requires.external_mutation},
                "declared_effects": list(self.declared_effects),
                "idempotency": self.idempotency, "price_note": self.price_note,
                "price_source": self.price_source, "rate_limit_note": self.rate_limit_note,
                "terms_ref": self.terms_ref, "qualification": self.qualification,
                "observed_note": self.observed_note}

    @property
    def digest(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True).encode("utf-8")).hexdigest()

    def reference(self) -> dict:
        """What a step sees before it decides: facts, never a credential."""
        row = self.to_dict()
        row["digest"] = self.digest
        row["callable_without_review"] = self.qualification == QUALIFICATION[1]
        return row


@dataclass
class ExternalServiceCatalogue:
    """The outside services this deployment knows about, as candidates by default."""

    entries: dict = field(default_factory=dict)

    def register(self, entry: ExternalServiceCapability) -> None:
        if not isinstance(entry, ExternalServiceCapability):
            raise ExternalServiceError("only a typed entry can be registered")
        if entry.qualification == QUALIFICATION[1]:
            raise ExternalServiceError(
                f"{entry.identity!r} cannot register as qualified; an entry arrives as a "
                "candidate and a separate review promotes it")
        self.entries[entry.identity] = entry

    def qualify(self, identity: str, *, reviewer: str, producer: str,
                checked: tuple[str, ...]) -> dict:
        """Promote a candidate, only on a review by someone other than its producer."""
        entry = self.entries.get(identity)
        if entry is None:
            raise ExternalServiceError(f"no entry named {identity!r}")
        if not reviewer.strip() or not producer.strip():
            raise ExternalServiceError("a review names its reviewer and the producer")
        if reviewer.strip() == producer.strip():
            raise ExternalServiceError(
                f"{reviewer!r} produced this entry, so it cannot also qualify it")
        if not checked:
            raise ExternalServiceError("a review names what it checked")
        from dataclasses import replace
        self.entries[identity] = replace(entry, qualification=QUALIFICATION[1])
        return {"record_type": REVIEW_RECORD_TYPE, "identity": identity,
                "reviewer": reviewer, "producer": producer, "checked": list(checked),
                "qualification": QUALIFICATION[1],
                "digest": self.entries[identity].digest}


def offer(catalogue: ExternalServiceCatalogue, *, authority: CallAuthority | None = None,
          include_candidates: bool = False) -> dict:
    """What this step may call, with everything withheld named and explained.

    Nothing here reaches a service. An entry the step cannot afford by
    authority is withheld, and so is a candidate unless the caller explicitly
    asked to see candidates, because retrieval is not promotion.
    """
    held = authority or CallAuthority()
    if not isinstance(held, CallAuthority):
        raise ExternalServiceError("authority must be the typed record")
    offered, withheld = [], []
    for entry in sorted(catalogue.entries.values(), key=lambda item: item.identity):
        if entry.qualification != QUALIFICATION[1] and not include_candidates:
            withheld.append({"identity": entry.identity,
                             "reason": f"{entry.qualification}, and candidates were not asked for"})
            continue
        missing = held.missing(entry.requires)
        if missing:
            withheld.append({
                "identity": entry.identity,
                "reason": f"needs {list(missing)}, which this step does not hold"})
            continue
        offered.append(entry.reference())
    return {"record_type": OFFER_RECORD_TYPE,
            "authority": {"network": held.network, "spend": held.spend,
                          "external_mutation": held.external_mutation},
            "candidates_included": bool(include_candidates),
            "offered": offered, "withheld": withheld,
            "spending_offered": sum(1 for row in offered if row["requires"]["spend"])}


def self_test() -> dict:
    """An entry names its authority and price, never a secret, and never promotes itself."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except ExternalServiceError:
            return True
        except Exception:  # noqa: BLE001 - a crash is not a typed refusal
            return False
        return False

    lookup = ExternalServiceCapability(
        "service.postal.lookup", "an address service operator",
        "Resolve a postal address to its components",
        "route.postal_lookup", "contract.address_components/v1",
        authentication="api_key", credential_ref="host.credential.postal_lookup",
        requires=CallAuthority(network=True), idempotency="idempotent",
        rate_limit_note="documented as sixty calls a minute",
        terms_ref="terms.postal_lookup")
    booking = ExternalServiceCapability(
        "service.travel.book", "a travel service operator",
        "Book a seat and pay for it",
        "route.travel_book", "contract.travel_booking/v1",
        authentication="oauth", credential_ref="host.credential.travel",
        requires=CallAuthority(network=True, spend=True, external_mutation=True),
        idempotency="at_most_once", price_note="documented at a fee per booking",
        price_source="the operator's published price page, read 2026-09-18")
    catalogue = ExternalServiceCatalogue()
    catalogue.register(lookup)
    catalogue.register(booking)
    check("an_entry_declares_the_network_a_credential_reference_and_a_price_source",
          lookup.requires.network and lookup.credential_ref.startswith("host.credential")
          and len(lookup.digest) == DIGEST_LENGTH
          and refuses(lambda: ExternalServiceCapability(
              "x", "operator", "purpose", "route", "contract",
              requires=CallAuthority(network=False)))
          and refuses(lambda: ExternalServiceCapability(
              "x", "operator", "purpose", "route", "contract",
              authentication="api_key", requires=CallAuthority(network=True)))
          and refuses(lambda: ExternalServiceCapability(
              "x", "operator", "purpose", "route", "contract",
              requires=CallAuthority(network=True, spend=True)))
          and refuses(lambda: ExternalServiceCapability(
              "x", "operator", "purpose", "route", "contract",
              requires=CallAuthority(network=True), price_note="a fee")),
          lookup.digest[:12])
    check("an_entry_that_carries_a_secret_shaped_value_is_refused_before_it_exists",
          refuses(lambda: ExternalServiceCapability(
              "x", "operator", "purpose", "route", "contract",
              authentication="api_key",
              # Assembled rather than written out, so the fixture exercises the
              # refusal without putting a key shaped literal in the source.
              credential_ref="sk-" + "0123456789abcdef" * 2,
              requires=CallAuthority(network=True)))
          and refuses(lambda: ExternalServiceCapability(
              "x", "operator", "purpose", "route", "contract",
              authentication="api_key",
              credential_ref="Zm9vYmFy" + "YmF6cXV4MDEyMzQ1Njc4OQ",
              requires=CallAuthority(network=True)))
          and not _looks_like_a_value("host.credential.postal_lookup")
          and _looks_like_a_value("0123456789abcdef" * 2)
          # A value in any other field is caught by the repository's own patterns,
          # assembled here so the source carries no secret shaped literal.
          and refuses(lambda: ExternalServiceCapability(
              "x", "operator", "purpose", "route", "contract",
              requires=CallAuthority(network=True),
              rate_limit_note="password" + " = " + "'" + "hunter2222" + "'")))
    check("an_entry_arrives_as_a_candidate_and_cannot_promote_itself",
          lookup.qualification == "candidate"
          and refuses(lambda: catalogue.register(ExternalServiceCapability(
              "service.self", "operator", "purpose", "route", "contract",
              requires=CallAuthority(network=True), qualification="qualified")))
          and refuses(lambda: catalogue.qualify(
              "service.postal.lookup", reviewer="same", producer="same",
              checked=("contract",)))
          and refuses(lambda: catalogue.qualify(
              "service.postal.lookup", reviewer="a reviewer", producer="a producer",
              checked=()))
          and refuses(lambda: catalogue.qualify(
              "absent", reviewer="a reviewer", producer="a producer", checked=("x",))))
    hidden = offer(catalogue, authority=CallAuthority(network=True))
    review = catalogue.qualify("service.postal.lookup", reviewer="an independent reviewer",
                               producer="the importing process",
                               checked=("typed contract", "declared authority", "terms"))
    reading = offer(catalogue, authority=CallAuthority(network=True))
    check("a_candidate_is_withheld_until_a_different_process_qualifies_it",
          not hidden["offered"] and len(hidden["withheld"]) == 2
          and review["reviewer"] != review["producer"]
          and [row["identity"] for row in reading["offered"]] == ["service.postal.lookup"]
          and reading["offered"][0]["callable_without_review"] is True,
          str(hidden["withheld"][0]["reason"]))
    spending = catalogue.qualify("service.travel.book", reviewer="an independent reviewer",
                                 producer="the importing process",
                                 checked=("typed contract", "price", "idempotency"))
    without_money = offer(catalogue, authority=CallAuthority(network=True))
    with_money = offer(catalogue, authority=CallAuthority(
        network=True, spend=True, external_mutation=True))
    check("a_service_that_spends_or_changes_outside_state_is_withheld_from_a_step_that_cannot",
          spending["qualification"] == "qualified"
          and [row["identity"] for row in without_money["withheld"]] == ["service.travel.book"]
          and "spend" in without_money["withheld"][0]["reason"]
          and len(with_money["offered"]) == 2 and with_money["spending_offered"] == 1
          and refuses(lambda: offer(catalogue, authority={"network": True})),
          without_money["withheld"][0]["reason"])
    check("a_reference_carries_the_facts_a_caller_needs_and_no_credential_value",
          all("credential_ref" in row and row.get("price_source") is not None
              for row in with_money["offered"])
          and all(not _secret_shaped(json.dumps(row)) for row in with_money["offered"])
          and with_money["offered"][1]["idempotency"] == "at_most_once"
          and CallAuthority(network=True).covers(CallAuthority(network=True))
          and not CallAuthority(network=True).covers(
              CallAuthority(network=True, spend=True)),
          str(with_money["offered"][1]["rate_limit_note"]))
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "external_service_intelligence_test/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}
