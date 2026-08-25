"""LoopRef and LoopCapsule — search returns LOOPS, and a loop persists as a package.

Architectural role: loop (the reference and package layer beneath search).

Two charter requirements that were still missing (§18, §20):

    SEARCH RETURNS LOOPS.  Search and capability resolution return ranked
    LoopRefs and handshakes — not payloads for the caller to interpret.
    Serving means invoking the selected loop.

    EVERY REUSABLE INTELLIGENCE ITEM IS A LAZY, VERSIONED LOOP CAPSULE.

Before this, search returned hits *through* a loop envelope — better than a
bare store read, but the caller still received content. Now it receives a
`LoopRef`: an address plus the handshake needed to decide whether to invoke
it. Content arrives only when the caller runs the loop.

The distinction matters for cost as much as doctrine: a `LoopRef` carries
identity, compatibility, mode support, cost class and digest — enough to
choose — without materialising the payload. Capsules load lazily, so a
million registered loops cost a million small rows, not a million live
objects.

Owns:
    - LoopRef: the address + handshake a search returns;
    - LoopHandshake: what a loop declares about itself before invocation;
    - LoopCapsule: the persisted package (spec + handshake + binding +
      payload reference + provenance + digest + lifecycle);
    - capsule_from_record() / refs_for_records(): the store's rows as
      capsules and refs;
    - invoke_ref(): the only way content is obtained from a ref.

Does not own:
    - the runtime (recursive_loop), the envelopes (encapsulate), the serving
      semantics (intelligence_loops), or any store.

Key invariants:
    - a ref carries NO payload; content requires invoking the loop;
    - a capsule is lazy — the payload is a reference until invoked;
    - every ref names its digest, so "the thing I chose" and "the thing I ran"
      are checkable against each other;
    - an unknown role fails closed.

Verification: self_test() — refs carry no content, invocation is the only
path to it, digests match across choose/run, and laziness is asserted rather
than assumed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .intelligence_loops import INTELLIGENCE_LOOP_KINDS, serve_pillar

#: Lifecycle of a persisted capsule.  A capsule is not trusted because it
#: exists; it is trusted because it reached `registered` through a gate.
CAPSULE_LIFECYCLE = ("draft", "candidate", "validated", "registered",
                     "deprecated", "retired")


def _digest(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


@dataclass(frozen=True)
class LoopHandshake:
    """What a loop declares about itself, so a caller can decide BEFORE
    invoking it.  Compatibility is negotiated, never assumed from a name."""
    loop_id: str
    role: str
    modes: tuple = ("deterministic",)
    input_contract: str = "unit_request"
    output_contract: str = "item"
    effects: str = "pure"
    cost_class: str = "free"
    maturity: str = "candidate"
    version: str = "1.0.0"

    def compatible_with(self, *, need_mode: str = "", need_output: str = ""
                        ) -> bool:
        if need_mode and need_mode not in self.modes:
            return False
        if need_output and need_output != self.output_contract:
            return False
        return True


@dataclass(frozen=True)
class LoopRef:
    """The address of a loop plus its handshake. Carries NO content.

    This is what a search returns.  A caller ranks refs, filters them by
    handshake, chooses one, and only then invokes it — which is what makes
    "search returns loops" a cost property and not only a doctrine one."""
    loop_ref: str
    handshake: LoopHandshake
    payload_ref: str = ""
    payload_digest: str = ""
    digest: str = ""
    score: float = 0.0
    source: str = ""

    def as_dict(self) -> dict:
        return {"loop_ref": self.loop_ref, "role": self.handshake.role,
                "modes": list(self.handshake.modes), "digest": self.digest,
                "payload_ref": self.payload_ref,
                "payload_digest": self.payload_digest,
                "score": self.score, "source": self.source,
                "maturity": self.handshake.maturity,
                "input_contract": self.handshake.input_contract,
                "output_contract": self.handshake.output_contract,
                "effects": self.handshake.effects,
                "cost_class": self.handshake.cost_class,
                "version": self.handshake.version}

    @classmethod
    def from_dict(cls, body: dict) -> "LoopRef":
        handshake = LoopHandshake(
            loop_id=str(body["loop_ref"]).rsplit("/", 1)[-1],
            role=body["role"], modes=tuple(body.get("modes") or ("deterministic",)),
            input_contract=body.get("input_contract", "unit_request"),
            output_contract=body.get("output_contract", "item"),
            effects=body.get("effects", "pure"),
            cost_class=body.get("cost_class", "free"),
            maturity=body.get("maturity", "candidate"),
            version=body.get("version", "1.0.0"))
        return cls(loop_ref=body["loop_ref"], handshake=handshake,
                   payload_ref=body.get("payload_ref", ""),
                   payload_digest=body.get("payload_digest", ""),
                   digest=body.get("digest", ""),
                   score=float(body.get("score", 0.0)),
                   source=body.get("source", ""))


@dataclass(frozen=True)
class ExternalPayloadRef:
    """A large body or artifact stored outside a search row."""
    uri: str
    digest: str
    size_bytes: int = 0
    media_type: str = "application/octet-stream"
    storage: str = "external"
    immutable: bool = True

    def __post_init__(self):
        if not self.uri or not self.digest:
            raise ValueError("an external payload needs a URI and digest")
        if len(self.digest) != 64 or any(
                character not in "0123456789abcdef" for character in self.digest):
            raise ValueError("external payload digest must be lowercase SHA-256 hex")
        if self.size_bytes < 0:
            raise ValueError("size_bytes cannot be negative")

    def to_dict(self) -> dict:
        return {"uri": self.uri, "digest": self.digest,
                "size_bytes": self.size_bytes, "media_type": self.media_type,
                "storage": self.storage, "immutable": self.immutable}


@dataclass
class LoopCapsule:
    """The persisted package for one reusable loop.

    ``payload_ref`` is a REFERENCE. The payload itself is materialised only
    when the capsule is invoked, so registering a million loops costs a
    million rows rather than a million live objects."""
    loop_id: str
    role: str
    handshake: LoopHandshake
    payload_ref: str
    payload_digest: str = ""
    provenance: str = ""
    lifecycle: str = "candidate"
    facets: dict = field(default_factory=dict)
    _payload: object = None                 # resolved lazily; never persisted

    def __post_init__(self):
        if self.role not in INTELLIGENCE_LOOP_KINDS:
            raise ValueError(
                f"capsule role {self.role!r} is not one of the four pillars "
                f"{tuple(INTELLIGENCE_LOOP_KINDS)} — fail closed, never guess")
        if self.lifecycle not in CAPSULE_LIFECYCLE:
            raise ValueError(f"lifecycle {self.lifecycle!r} not in "
                             f"{CAPSULE_LIFECYCLE}")

    @property
    def digest(self) -> str:
        return _digest({"loop_id": self.loop_id, "role": self.role,
                        "payload_ref": self.payload_ref,
                        "payload_digest": self.payload_digest,
                        "version": self.handshake.version})

    @property
    def materialised(self) -> bool:
        """Has the payload actually been loaded? Laziness is checkable."""
        return self._payload is not None

    def to_ref(self, *, score: float = 0.0, source: str = "") -> LoopRef:
        return LoopRef(loop_ref=f"loop://{self.role}/{self.loop_id}",
                       handshake=self.handshake, payload_ref=self.payload_ref,
                       payload_digest=self.payload_digest,
                       digest=self.digest,
                       score=score, source=source)

    def materialise(self, resolver=None):
        """Load the payload. Called by invocation, never by search."""
        if self._payload is None:
            self._payload = (resolver(self.payload_ref) if resolver
                             else self.payload_ref)
        return self._payload

    def to_record(self) -> dict:
        return {"record_type": "loop_capsule/v1", "loop_id": self.loop_id,
                "role": self.role, "payload_ref": self.payload_ref,
                "payload_digest": self.payload_digest,
                "digest": self.digest, "lifecycle": self.lifecycle,
                "provenance": self.provenance, "facets": dict(self.facets),
                "handshake": {"modes": list(self.handshake.modes),
                              "output_contract":
                                  self.handshake.output_contract,
                              "maturity": self.handshake.maturity,
                              "version": self.handshake.version}}


def capsule_from_record(rec, *, role: str = "string_intelligence"
                        ) -> LoopCapsule:
    """One store row as a lazy capsule."""
    def read(name, default=None):
        if hasattr(rec, name):
            return getattr(rec, name)
        return rec.get(name, default) if isinstance(rec, dict) else default

    rid = read("record_id", "unknown")
    title = read("title", "")
    body = dict(read("body", {}) or {})
    facets = dict(body.get("facets") or {})
    maturity = str(body.get("maturity") or facets.get("lifecycle")
                   or getattr(rec, "tier", "candidate"))
    lifecycle = maturity if maturity in CAPSULE_LIFECYCLE else (
        "registered" if maturity in ("core", "implemented", "committed")
        else "candidate")
    execution_mode = str(facets.get("execution_mode") or "")
    modes = (("deterministic",) if execution_mode in ("", "code_only")
             else ("deterministic", "hybrid") if execution_mode == "hybrid"
             else ("non_deterministic",))
    output_contract = ("code_asset_ref" if role == "code_intelligence"
                       else "context_item")
    effects = facets.get("effects") or "pure"
    effects_text = (",".join(effects) if isinstance(effects, (tuple, list))
                    else str(effects))
    return LoopCapsule(
        loop_id=str(rid), role=role,
        handshake=LoopHandshake(loop_id=str(rid), role=role,
                                modes=modes,
                                output_contract=output_contract,
                                effects=effects_text, maturity=maturity),
        payload_ref=str(body.get("payload_ref")
                        or f"content://{role}/{rid}"),
        payload_digest=str(body.get("payload_digest")
                           or body.get("body_digest") or ""),
        provenance=str(title)[:120], lifecycle=lifecycle,
        facets=facets)


def refs_for_records(records, *, role: str = "string_intelligence",
                     scores=None) -> list:
    """A store's rows as ranked LoopRefs — the shape a search returns."""
    scores = scores or {}
    caps = [capsule_from_record(r, role=role) for r in records]
    return [c.to_ref(score=float(scores.get(c.loop_id, 0.0)), source=role)
            for c in caps]


def refs_for_hits(hits, *, role: str = "string_intelligence") -> list:
    """Build refs from body-free search cards without serving any record."""
    refs = []
    for hit in hits:
        card = {
            "record_id": hit["record_id"], "title": hit.get("title", ""),
            "tier": hit.get("tier", "core"),
            "body": {"payload_ref": hit.get("payload_ref", ""),
                     "payload_digest": hit.get("payload_digest", ""),
                     "maturity": hit.get("maturity", hit.get("tier", "core")),
                     "version": hit.get("version", "1.0.0"),
                     "facets": dict(hit.get("facets") or {})}}
        capsule = capsule_from_record(card, role=role)
        refs.append(capsule.to_ref(score=float(
            hit.get("score", hit.get("rrf", 0.0))),
            source=hit.get("source", role)))
    return refs


@dataclass(frozen=True)
class MaterializedPayload:
    """A resolved external payload plus the digest the resolver observed."""
    value: object
    digest: str
    local_ref: str = ""


def materialize_ref_as_loop(ref: LoopRef, resolver=None, *, ledger=None,
                            parent=None) -> dict:
    """Resolve a selected reference inside its intelligence access loop.

    Returns the serve dict, and asserts the digest of what ran matches the
    digest of what was chosen — so a ref cannot be swapped between selection
    and invocation.
    """
    loop_id = ref.loop_ref.rsplit("/", 1)[-1]
    role = ref.handshake.role
    capsule = LoopCapsule(loop_id=loop_id, role=role,
                          handshake=ref.handshake,
                          payload_ref=ref.payload_ref
                          or f"content://{role}/{loop_id}",
                          payload_digest=ref.payload_digest,
                          lifecycle="registered")
    if ref.digest and capsule.digest != ref.digest:
        raise ValueError(
            f"ref {ref.loop_ref} was chosen at digest {ref.digest[:12]}… but "
            f"resolves to {capsule.digest[:12]}… — the thing chosen is not "
            "the thing about to run")
    observed = {"digest": "", "local_ref": ""}

    def resolve_inside_loop():
        payload = capsule.materialise(resolver)
        if isinstance(payload, MaterializedPayload):
            if ref.payload_digest and payload.digest != ref.payload_digest:
                raise ValueError(
                    f"payload digest mismatch for {ref.loop_ref}: selected "
                    f"{ref.payload_digest[:12]}, loaded {payload.digest[:12]}")
            observed["digest"] = payload.digest
            observed["local_ref"] = payload.local_ref
            return payload.value
        if ref.payload_digest:
            raise ValueError(
                f"resolver for {ref.loop_ref} must return MaterializedPayload "
                "so the external body digest can be verified")
        return payload

    out = serve_pillar(role, loop_id, resolve_inside_loop, ledger=ledger,
                       parent=parent)
    if out.get("error") is not None:
        raise ValueError(f"failed to materialize {ref.loop_ref}") \
            from out["error"]
    out["loop_ref"] = ref.loop_ref
    out["digest"] = capsule.digest
    out["payload_digest"] = observed["digest"]
    out["local_ref"] = observed["local_ref"]
    return out


def invoke_ref(ref: LoopRef, resolver=None, *, ledger=None, parent=None) -> dict:
    """Compatibility name for ``materialize_ref_as_loop``."""
    return materialize_ref_as_loop(ref, resolver, ledger=ledger, parent=parent)


def reframe_ref_with_model(ref: LoopRef, resolver, *, task: str, reframe,
                           ledger=None, parent=None) -> dict:
    """Read the original item, then reframe it in a separate model loop.

    The source item stays unchanged. The workflow is hybrid by composition:
    deterministic intelligence access followed by one explicit model-led loop.
    """
    original = invoke_ref(ref, resolver, ledger=ledger, parent=parent)
    from .encapsulate import as_model_loop
    framed = as_model_loop(
        f"reframe {ref.handshake.role} for task",
        lambda: reframe(original["value"], task), ledger=ledger, parent=parent)
    return {"record_type": "reframed_intelligence/v1",
            "source_loop_ref": ref.loop_ref,
            "original": original["value"], "value": framed["value"],
            "access_loop_id": original["loop_id"],
            "reframe_loop_id": framed["loop_id"],
            "workflow_mode": "hybrid", "source_unchanged": True}


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    from ..static_architecture.store_serve import StoreRecord
    from .recursive_loop import LoopLedger
    from ..static_architecture.chronicle import to_canonical_events

    recs = [StoreRecord("q.leak", "question",
                        "has leakage been checked before scoring?",
                        body={}, tags=("data_quality",)),
            StoreRecord("q.dupes", "question", "are duplicate rows removed?",
                        body={}, tags=("data_quality",))]

    # 1. SEARCH RETURNS LOOPS: refs carry an address and a handshake, and NO
    # content.  This is the charter's rule and also the cost property — a
    # caller ranks and filters without materialising anything.
    refs = refs_for_records(recs, scores={"q.leak": 0.9})
    ref_json = json.dumps([r.as_dict() for r in refs])
    check("search_returns_refs_that_carry_no_content",
          len(refs) == 2 and all(isinstance(r, LoopRef) for r in refs)
          and "leakage" not in ref_json and "duplicate" not in ref_json
          and refs[0].loop_ref.startswith("loop://string_intelligence/")
          and refs[0].handshake.role == "string_intelligence",
          "two refs, addresses + handshakes, zero payload text")

    # 2. LAZY: a capsule holds a REFERENCE until something invokes it.
    cap = capsule_from_record(recs[0])
    lazy_before = not cap.materialised
    cap.materialise(lambda ref: "resolved payload")
    check("capsules_are_lazy_until_invoked",
          lazy_before and cap.materialised
          and cap.payload_ref == "content://string_intelligence/q.leak",
          "payload is a reference until materialise() is called")

    # 3. INVOCATION IS THE ONLY PATH TO CONTENT, and it goes through the loop
    # — the retrieval lands on the caller's ledger as a canonical family.
    lg = LoopLedger()
    out = invoke_ref(refs[0], lambda r: "has leakage been checked?",
                     ledger=lg)
    fams = {c["type"] for c in to_canonical_events(lg.events)}
    check("invoking_a_ref_runs_the_loop_and_returns_content",
          out["value"] == "has leakage been checked?"
          and out["loop_ref"] == refs[0].loop_ref
          and "intelligence.string.retrieved" in fams
          and out["model_calls"] == 0,
          f"content only via invocation; families {sorted(fams)[:2]}…")

    # 4. ADVERSARIAL: a ref cannot be swapped between choosing and running.
    # A digest mismatch is refused rather than quietly serving something else.
    swapped = LoopRef(loop_ref=refs[0].loop_ref,
                      handshake=refs[0].handshake, digest="0" * 64)
    refused = False
    try:
        invoke_ref(swapped, lambda r: "other")
    except ValueError:
        refused = True
    # and an unknown role fails closed at capsule construction
    bad_role = False
    try:
        LoopCapsule(loop_id="x", role="vibes",
                    handshake=LoopHandshake("x", "vibes"), payload_ref="c://x")
    except ValueError:
        bad_role = True
    check("digest_mismatch_and_unknown_role_are_refused",
          refused and bad_role,
          "the thing chosen must be the thing that runs")

    # 5. handshake compatibility is checkable BEFORE invoking — the point of
    # returning a handshake rather than a payload.
    hs = refs[0].handshake
    check("handshakes_let_a_caller_choose_before_invoking",
          hs.compatible_with(need_mode="deterministic")
          and not hs.compatible_with(need_mode="non_deterministic")
          and hs.compatible_with(need_output="context_item"),
          "mode and output compatibility decided from the ref alone")

    # 6. typed refs survive a JSON round trip without gaining payload content.
    round_trip = LoopRef.from_dict(refs[0].as_dict())
    check("loop_ref_json_round_trip_preserves_materialization_identity",
          round_trip == refs[0]
          and round_trip.payload_ref.endswith("q.leak"))

    # 7. optional task reframing is a second explicit model loop. The source
    # item remains unchanged and the two loop identities remain separate.
    reframe_ledger = LoopLedger()
    reframed = reframe_ref_with_model(
        refs[0], lambda payload_ref: "has leakage been checked?",
        task="review a customer import",
        reframe=lambda source, task: f"For {task}: {source}",
        ledger=reframe_ledger)
    check("model_reframing_is_a_separate_loop_and_keeps_source_unchanged",
          reframed["workflow_mode"] == "hybrid"
          and reframed["source_unchanged"]
          and reframed["original"] == "has leakage been checked?"
          and reframed["value"].startswith("For review a customer import")
          and reframed["access_loop_id"] != reframed["reframe_loop_id"]
          and len(reframe_ledger.loops()) == 2)

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
