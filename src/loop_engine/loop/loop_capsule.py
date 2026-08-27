"""Passive intelligence references, packages, and governed loading.

Search returns small ``IntelligenceItemRef`` values. A selected reference may
be loaded by an Intelligence-role Loop, but neither the reference nor its
package is a runtime. Legacy LoopRef and LoopCapsule spellings are exact class
aliases for immutable record compatibility only.
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
class IntelligenceItemHandshake:
    """Compatibility facts for selecting one passive intelligence item."""
    item_id: str
    layer: str
    supported_modes: tuple[str, ...] = ("deterministic",)
    input_contract: str = "unit_request"
    output_contract: str = "item"
    effects: tuple[str, ...] = ()
    cost_class: str = "free"
    maturity: str = "candidate"
    version: str = "1.0.0"

    def compatible_with(self, *, need_mode: str = "", need_output: str = ""
                        ) -> bool:
        if need_mode and need_mode not in self.supported_modes:
            return False
        if need_output and need_output != self.output_contract:
            return False
        return True

    @property
    def loop_id(self) -> str:
        """Pre-1.0 reader alias for ``item_id``."""
        return self.item_id

    @property
    def role(self) -> str:
        """Pre-1.0 reader alias; the value has always identified a layer."""
        return self.layer

    @property
    def modes(self) -> tuple[str, ...]:
        """Pre-1.0 reader alias for ``supported_modes``."""
        return self.supported_modes


@dataclass(frozen=True)
class IntelligenceItemRef:
    """Body-free address and compatibility facts for one intelligence item."""
    item_ref: str
    handshake: IntelligenceItemHandshake
    payload_ref: str = ""
    payload_digest: str = ""
    digest: str = ""
    score: float = 0.0
    source: str = ""

    def as_dict(self) -> dict:
        return {"intelligence_item_ref": self.item_ref,
                "layer": self.handshake.layer,
                "supported_modes": list(self.handshake.supported_modes),
                "digest": self.digest,
                "payload_ref": self.payload_ref,
                "payload_digest": self.payload_digest,
                "score": self.score, "source": self.source,
                "maturity": self.handshake.maturity,
                "input_contract": self.handshake.input_contract,
                "output_contract": self.handshake.output_contract,
                "effects": list(self.handshake.effects),
                "cost_class": self.handshake.cost_class,
                "version": self.handshake.version}

    @classmethod
    def from_dict(cls, body: dict) -> "IntelligenceItemRef":
        item_ref = body.get("intelligence_item_ref", body.get("loop_ref", ""))
        layer = body.get("layer", body.get("role", ""))
        handshake = IntelligenceItemHandshake(
            item_id=str(item_ref).rsplit("/", 1)[-1],
            layer=layer,
            supported_modes=tuple(body.get(
                "supported_modes", body.get("modes") or ("deterministic",))),
            input_contract=body.get("input_contract", "unit_request"),
            output_contract=body.get("output_contract", "item"),
            effects=tuple(body.get("effects") or ()),
            cost_class=body.get("cost_class", "free"),
            maturity=body.get("maturity", "candidate"),
            version=body.get("version", "1.0.0"))
        return cls(item_ref=item_ref, handshake=handshake,
                   payload_ref=body.get("payload_ref", ""),
                   payload_digest=body.get("payload_digest", ""),
                   digest=body.get("digest", ""),
                   score=float(body.get("score", 0.0)),
                   source=body.get("source", ""))

    @property
    def loop_ref(self) -> str:
        """Pre-1.0 reader alias for ``item_ref``."""
        return self.item_ref


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
class IntelligenceItemPackage:
    """The persisted, lazy package for one reusable intelligence item.

    ``payload_ref`` is a REFERENCE. The payload itself is materialised only
    when the capsule is invoked, so registering a million loops costs a
    million rows rather than a million live objects."""
    item_id: str
    layer: str
    handshake: IntelligenceItemHandshake
    payload_ref: str
    payload_digest: str = ""
    provenance: str = ""
    lifecycle: str = "candidate"
    facets: dict = field(default_factory=dict)
    _payload: object = None                 # resolved lazily; never persisted

    def __post_init__(self):
        if self.layer not in INTELLIGENCE_LOOP_KINDS:
            raise ValueError(
                f"intelligence layer {self.layer!r} is not registered: "
                f"{tuple(INTELLIGENCE_LOOP_KINDS)} — fail closed, never guess")
        if self.lifecycle not in CAPSULE_LIFECYCLE:
            raise ValueError(f"lifecycle {self.lifecycle!r} not in "
                             f"{CAPSULE_LIFECYCLE}")

    @property
    def digest(self) -> str:
        return _digest({"item_id": self.item_id, "layer": self.layer,
                        "payload_ref": self.payload_ref,
                        "payload_digest": self.payload_digest,
                        "version": self.handshake.version})

    @property
    def materialised(self) -> bool:
        """Has the payload actually been loaded? Laziness is checkable."""
        return self._payload is not None

    def to_ref(self, *, score: float = 0.0, source: str = "") -> IntelligenceItemRef:
        return IntelligenceItemRef(
                       item_ref=f"intelligence://{self.layer}/{self.item_id}",
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
        return {"record_type": "intelligence_item_package/v2",
                "item_id": self.item_id,
                "layer": self.layer, "payload_ref": self.payload_ref,
                "payload_digest": self.payload_digest,
                "digest": self.digest, "lifecycle": self.lifecycle,
                "provenance": self.provenance, "facets": dict(self.facets),
                "handshake": {
                              "supported_modes":
                                  list(self.handshake.supported_modes),
                              "output_contract":
                                  self.handshake.output_contract,
                              "maturity": self.handshake.maturity,
                              "version": self.handshake.version}}

    @property
    def loop_id(self) -> str:
        """Pre-1.0 reader alias for ``item_id``."""
        return self.item_id

    @property
    def role(self) -> str:
        """Pre-1.0 reader alias for ``layer``."""
        return self.layer


def intelligence_package_from_record(
        rec, *, layer: str = "context_intelligence"
        ) -> IntelligenceItemPackage:
    """Project one store row into a lazy intelligence package."""
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
    output_contract = ("code_asset_ref" if layer == "code_intelligence"
                       else "context_item")
    effects = facets.get("effects") or "pure"
    effect_values = (tuple(effects) if isinstance(effects, (tuple, list))
                     else () if effects == "pure" else (str(effects),))
    return IntelligenceItemPackage(
        item_id=str(rid), layer=layer,
        handshake=IntelligenceItemHandshake(
                                item_id=str(rid), layer=layer,
                                supported_modes=modes,
                                output_contract=output_contract,
                                effects=effect_values, maturity=maturity),
        payload_ref=str(body.get("payload_ref")
                        or f"content://{layer}/{rid}"),
        payload_digest=str(body.get("payload_digest")
                           or body.get("body_digest") or ""),
        provenance=str(title)[:120], lifecycle=lifecycle,
        facets=facets)


def intelligence_refs_for_records(
        records, *, layer: str = "context_intelligence",
        scores=None) -> list:
    """Project store rows into ranked body-free intelligence references."""
    scores = scores or {}
    caps = [intelligence_package_from_record(r, layer=layer) for r in records]
    return [c.to_ref(score=float(scores.get(c.item_id, 0.0)), source=layer)
            for c in caps]


def intelligence_refs_for_hits(
        hits, *, layer: str = "context_intelligence") -> list:
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
        package = intelligence_package_from_record(card, layer=layer)
        refs.append(package.to_ref(score=float(
            hit.get("score", hit.get("rrf", 0.0))),
            source=hit.get("source", layer)))
    return refs


@dataclass(frozen=True)
class MaterializedPayload:
    """A resolved external payload plus the digest the resolver observed."""
    value: object
    digest: str
    local_ref: str = ""


@dataclass(frozen=True)
class IntelligenceLoadRequest:
    """Passive selected reference and resolver for one governed load."""

    ref: IntelligenceItemRef
    resolver: object | None = None


@dataclass(frozen=True)
class IntelligenceLoadContext:
    """Optional Loop ownership context for one intelligence load."""

    ledger: object | None = None
    parent: object | None = None


def load_intelligence_ref(
        request: IntelligenceLoadRequest,
        context: IntelligenceLoadContext | None = None) -> dict:
    """Resolve a selected reference inside its intelligence access loop.

    Returns the serve dict, and asserts the digest of what ran matches the
    digest of what was chosen — so a ref cannot be swapped between selection
    and invocation.
    """
    if not isinstance(request, IntelligenceLoadRequest):
        raise TypeError("load_intelligence_ref needs IntelligenceLoadRequest")
    selected_context = context or IntelligenceLoadContext()
    ref = request.ref
    item_id = ref.item_ref.rsplit("/", 1)[-1]
    layer = ref.handshake.layer
    package = IntelligenceItemPackage(item_id=item_id, layer=layer,
                          handshake=ref.handshake,
                          payload_ref=ref.payload_ref
                          or f"content://{layer}/{item_id}",
                          payload_digest=ref.payload_digest,
                          lifecycle="registered")
    if ref.digest and package.digest != ref.digest:
        raise ValueError(
            f"ref {ref.item_ref} was chosen at digest {ref.digest[:12]}… but "
            f"resolves to {package.digest[:12]}… — the thing chosen is not "
            "the thing about to run")
    observed = {"digest": "", "local_ref": ""}

    def resolve_inside_loop():
        payload = package.materialise(request.resolver)
        if isinstance(payload, MaterializedPayload):
            if ref.payload_digest and payload.digest != ref.payload_digest:
                raise ValueError(
                    f"payload digest mismatch for {ref.item_ref}: selected "
                    f"{ref.payload_digest[:12]}, loaded {payload.digest[:12]}")
            observed["digest"] = payload.digest
            observed["local_ref"] = payload.local_ref
            return payload.value
        if ref.payload_digest:
            raise ValueError(
                f"resolver for {ref.item_ref} must return MaterializedPayload "
                "so the external body digest can be verified")
        return payload

    out = serve_pillar(
        layer, item_id, resolve_inside_loop,
        ledger=selected_context.ledger, parent=selected_context.parent)
    if out.get("error") is not None:
        raise ValueError(f"failed to load {ref.item_ref}") \
            from out["error"]
    out["intelligence_item_ref"] = ref.item_ref
    out["digest"] = package.digest
    out["payload_digest"] = observed["digest"]
    out["local_ref"] = observed["local_ref"]
    return out


@dataclass(frozen=True)
class IntelligenceReframeRequest:
    """Passive input for loading and model-reframing one selected item."""

    ref: IntelligenceItemRef
    resolver: object
    task: str
    reframe: object


def reframe_intelligence_ref(
        request: IntelligenceReframeRequest,
        context: IntelligenceLoadContext | None = None) -> dict:
    """Read the original item, then reframe it in a separate model loop.

    The source item stays unchanged. The workflow is hybrid by composition:
    deterministic intelligence access followed by one explicit model-led loop.
    """
    selected_context = context or IntelligenceLoadContext()
    original = load_intelligence_ref(
        IntelligenceLoadRequest(request.ref, request.resolver),
        selected_context)
    from .encapsulate import as_model_loop
    framed = as_model_loop(
        f"reframe {request.ref.handshake.layer} for task",
        lambda: request.reframe(original["value"], request.task),
        ledger=selected_context.ledger, parent=selected_context.parent)
    return {"record_type": "reframed_intelligence/v1",
            "source_intelligence_item_ref": request.ref.item_ref,
            "original": original["value"], "value": framed["value"],
            "access_loop_id": original["loop_id"],
            "reframe_loop_id": framed["loop_id"],
            "workflow_mode": "hybrid", "source_unchanged": True}


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    from ..core.store_serve import StoreRecord
    from .recursive_loop import LoopLedger
    from ..core.run_history import to_canonical_events

    recs = [StoreRecord("q.leak", "question",
                        "has leakage been checked before scoring?",
                        body={}, tags=("data_quality",)),
            StoreRecord("q.dupes", "question", "are duplicate rows removed?",
                        body={}, tags=("data_quality",))]

    # 1. SEARCH RETURNS LOOPS: refs carry an address and a handshake, and NO
    # content.  This is the charter's rule and also the cost property — a
    # caller ranks and filters without materialising anything.
    refs = intelligence_refs_for_records(recs, scores={"q.leak": 0.9})
    ref_json = json.dumps([r.as_dict() for r in refs])
    check("search_returns_refs_that_carry_no_content",
          len(refs) == 2 and all(isinstance(r, IntelligenceItemRef) for r in refs)
          and "leakage" not in ref_json and "duplicate" not in ref_json
          and refs[0].item_ref.startswith(
              "intelligence://context_intelligence/")
          and refs[0].handshake.layer == "context_intelligence",
          "two refs, addresses + handshakes, zero payload text")

    # 2. LAZY: a capsule holds a REFERENCE until something invokes it.
    cap = intelligence_package_from_record(recs[0])
    lazy_before = not cap.materialised
    cap.materialise(lambda ref: "resolved payload")
    check("capsules_are_lazy_until_invoked",
          lazy_before and cap.materialised
          and cap.payload_ref == "content://context_intelligence/q.leak",
          "payload is a reference until materialise() is called")

    # 3. INVOCATION IS THE ONLY PATH TO CONTENT, and it goes through the loop
    # — the retrieval lands on the caller's ledger as a canonical family.
    lg = LoopLedger()
    out = load_intelligence_ref(IntelligenceLoadRequest(
        refs[0], lambda _ref: "has leakage been checked?"),
        IntelligenceLoadContext(ledger=lg))
    fams = {c["type"] for c in to_canonical_events(lg.events)}
    check("invoking_a_ref_runs_the_loop_and_returns_content",
          out["value"] == "has leakage been checked?"
          and out["intelligence_item_ref"] == refs[0].item_ref
          and "intelligence.context.retrieved" in fams
          and out["model_calls"] == 0,
          f"content only via invocation; families {sorted(fams)[:2]}…")

    # 4. ADVERSARIAL: a ref cannot be swapped between choosing and running.
    # A digest mismatch is refused rather than quietly serving something else.
    swapped = IntelligenceItemRef(item_ref=refs[0].item_ref,
                      handshake=refs[0].handshake, digest="0" * 64)
    refused = False
    try:
        load_intelligence_ref(IntelligenceLoadRequest(
            swapped, lambda _ref: "other"))
    except ValueError:
        refused = True
    # and an unknown role fails closed at capsule construction
    bad_role = False
    try:
        IntelligenceItemPackage(item_id="x", layer="vibes",
                    handshake=IntelligenceItemHandshake("x", "vibes"),
                    payload_ref="c://x")
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
    round_trip = IntelligenceItemRef.from_dict(refs[0].as_dict())
    check("loop_ref_json_round_trip_preserves_materialization_identity",
          round_trip == refs[0]
          and round_trip.payload_ref.endswith("q.leak"))

    # 7. optional task reframing is a second explicit model loop. The source
    # item remains unchanged and the two loop identities remain separate.
    reframe_ledger = LoopLedger()
    reframed = reframe_intelligence_ref(IntelligenceReframeRequest(
        refs[0], lambda _payload_ref: "has leakage been checked?",
        task="review a customer import",
        reframe=lambda source, task: f"For {task}: {source}"),
        IntelligenceLoadContext(ledger=reframe_ledger))
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


# Exact pre-1.0 compatibility aliases. They resolve to canonical objects and
# never own identity, execution, or persistence authority.
LoopHandshake = IntelligenceItemHandshake
LoopRef = IntelligenceItemRef
LoopCapsule = IntelligenceItemPackage
capsule_from_record = intelligence_package_from_record
refs_for_records = intelligence_refs_for_records
refs_for_hits = intelligence_refs_for_hits
materialize_ref_as_loop = load_intelligence_ref
invoke_ref = load_intelligence_ref
reframe_ref_with_model = reframe_intelligence_ref


__all__ = (
    "ExternalPayloadRef", "IntelligenceItemHandshake",
    "IntelligenceItemPackage", "IntelligenceItemRef",
    "IntelligenceLoadContext", "IntelligenceLoadRequest",
    "IntelligenceReframeRequest", "MaterializedPayload",
    "intelligence_package_from_record", "intelligence_refs_for_hits",
    "intelligence_refs_for_records", "load_intelligence_ref",
    "reframe_intelligence_ref",
)
