"""Local capability discovery and standardized invocation.

The directory stores machine-readable handshakes and registered endpoints.
Loops can inspect operations, contracts, effects, locality, cost, access, and
failure behavior before choosing a capability. Custom Plugin discovery reads
local handshake cards and returns Code Intelligence LoopRefs without executing
an endpoint.

Invocation is separate. A selected endpoint may use a declared fallback, but
the result records which fallback layer changed. Effectful invocation belongs
inside ``loop.capability_loops``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from typing import Callable, Sequence

from .capability_invocation import CapabilityInvocationPolicy, capability_handshake_digest
from .model_ontology import ModelProfile, TOOL_MODEL_USES, validate_tool_model_use

SURFACE_KINDS = ("string_store", "code_node_registry", "static_component")
OPERATIONS = ("search", "get", "list", "invoke", "validate", "compose",
              "run", "resolve", "materialize")
FALLBACK_LAYERS = ("search_mode", "surface", "semantic")


class HandshakeError(RuntimeError):
    """An unknown surface, or a negotiation that cannot be satisfied."""


@dataclass(frozen=True)
class CapabilityHandshake:
    """What a resource surface DECLARES about itself — read before it is used."""
    surface: str
    surface_kind: str
    functionality: str                  # plain-English: what this surface does
    operations: tuple                   # the ops it supports
    query_fields: tuple = ()            # searchable fields (for search surfaces)
    ranking: tuple = ("lexical",)      # ranking methods available
    embeddings: bool = False           # deterministic no-embedding search always works
    accepts: tuple = ()                # asset kinds it takes (string / code node)
    returns: tuple = ()
    protocol_version: str = "1.0.0"
    health: str = "ok"
    input_schema: str = "any"
    output_schema: str = "any"
    locality: str = "local_machine"
    effects: tuple = ("pure",)
    cost_class: str = "free"
    auth_method: str = "none"
    secret_ref: str = ""
    retention_default: str = "ephemeral"
    idempotency: str = "read_only"
    timeout_seconds: float = 0.0
    max_response_bytes: int = 0
    quota_policy: str = "unknown"
    rate_limit_policy: str = "provider_reported"
    retry_policy: str = "caller_controlled"
    data_egress: tuple = ()
    privacy_class: str = "unknown"
    license_terms: str = "unknown"
    pricing_snapshot_ref: str = ""
    provider_version: str = ""
    last_verified_at: str = ""
    model_use: str = TOOL_MODEL_USES[0]   # none, calls_service, or embeds_small
    model_profile: "ModelProfile | None" = None

    def __post_init__(self):
        if self.surface_kind not in SURFACE_KINDS:
            raise ValueError(f"surface_kind must be one of {SURFACE_KINDS}")
        bad = [o for o in self.operations if o not in OPERATIONS]
        if bad:
            raise ValueError(f"unknown operations {bad}; valid {OPERATIONS}")
        from .facets import EFFECTS, LOCALITY, COST_CLASSES
        if self.locality not in LOCALITY:
            raise ValueError(f"locality must be one of {LOCALITY}")
        if self.cost_class not in COST_CLASSES:
            raise ValueError(f"cost_class must be one of {COST_CLASSES}")
        if any(effect not in EFFECTS for effect in self.effects):
            raise ValueError(f"effects must be drawn from {EFFECTS}")
        if self.timeout_seconds < 0 or self.max_response_bytes < 0:
            raise ValueError("timeout and response-size limits cannot be negative")
        validate_tool_model_use(self.model_use, self.model_profile)

    def supports(self, operation: str) -> bool:
        return operation in self.operations and self.health == "ok"

    def describe(self) -> dict:
        """The machine-readable handshake the practitioner consults."""
        return asdict(self)


@dataclass
class CallResult:
    surface: str
    operation: str
    ok: bool
    value: object = None
    used_fallback: bool = False
    note: str = ""
    fallback_layer: str = ""            # one of FALLBACK_LAYERS when a fallback ran


@dataclass
class Endpoint:
    operation: str
    fn: Callable
    fallback: "tuple | None" = None     # (surface, operation) if this one fails


@dataclass
class CapabilityQuery:
    """Search by NEED, never by implementation name."""
    obligation: str
    desired_capability: str
    preferred_class: str = "either"     # string | code | either
    inputs: tuple = ()
    output_role: str = ""
    tags: tuple = ()
    namespaces: tuple = ("run", "project", "core")
    max_cost: float = float("inf")
    maturity: str = "any"
    optimize_for: str = "quality"
    fallback_policy: str = "code_then_string"
    # facet constraints (see facets.py): require is hard + fail-closed,
    # exclude is hard on evidence, prefer only ranks.
    require_facets: dict = field(default_factory=dict)
    prefer_facets: dict = field(default_factory=dict)
    exclude_facets: dict = field(default_factory=dict)

    def as_search_text(self) -> str:
        return " ".join((self.desired_capability, *self.tags,
                         self.output_role)).strip()


@dataclass
class CapabilityMatch:
    """One result, keeping its source surface and exact identity."""
    resource_id: str
    asset_class: str                    # string | code
    source_surface: str
    capability: str = ""
    match_explanation: str = ""
    maturity: str = "candidate"
    est_cost: float = 1.0
    availability: str = "ok"
    invocation: str = ""                # "surface.operation"
    fallbacks: tuple = ()
    facets: dict = field(default_factory=dict)
    facet_score: int = 0                # prefer-facet matches (rank only)
    item_ref: object = None


@dataclass
class CapabilitySnapshot:
    """A COMPACT, versioned view of what is available — given to the practitioner
    each pass so it has full capability awareness WITHOUT loading every resource."""
    snapshot_id: str
    surfaces_available: tuple
    surfaces_degraded: tuple
    search_modes: tuple
    string_stores: tuple
    code_registries: tuple
    static_services: tuple
    gaps: tuple = ()

    def render(self) -> str:
        """The model-facing summary — enough for decide_next / how to reason,
        never the full catalog."""
        lines = ["AVAILABLE CAPABILITIES (snapshot " + self.snapshot_id + ")"]
        if self.string_stores:
            lines.append("Strings: " + ", ".join(self.string_stores)
                         + " — search: " + ", ".join(self.search_modes) + ".")
        if self.code_registries:
            lines.append("Code nodes: " + ", ".join(self.code_registries)
                         + " — searchable and invokable.")
        if self.static_services:
            lines.append("Static services: " + ", ".join(self.static_services)
                         + ".")
        if self.surfaces_degraded:
            lines.append("Degraded/unavailable: "
                         + ", ".join(self.surfaces_degraded) + ".")
        if self.gaps:
            lines.append("Known gaps: " + ", ".join(self.gaps) + ".")
        return "\n".join(lines)


class CapabilityDirectory:
    """The standardized directory of surfaces the practitioner can search + call."""

    def __init__(self):
        self._hs: dict = {}                         # surface -> handshake
        self._ep: dict = {}                         # (surface, op) -> Endpoint
        self._default_fallback: dict = {}           # surface -> (surface, op)

    def register(self, handshake: CapabilityHandshake,
                 endpoints: "Sequence[Endpoint]" = (), *,
                 default_fallback: "tuple | None" = None,
                 replace: bool = False) -> None:
        if handshake.surface in self._hs and not replace:
            raise HandshakeError(
                f"surface {handshake.surface!r} is already registered")
        self._hs[handshake.surface] = handshake
        for ep in endpoints:
            self._ep[(handshake.surface, ep.operation)] = ep
        if default_fallback:
            self._default_fallback[handshake.surface] = default_fallback

    def available(self) -> list:
        return list(self._hs.values())

    def for_kind(self, surface_kind: str) -> list:
        return [h for h in self._hs.values() if h.surface_kind == surface_kind]

    def handshake(self, surface: str) -> CapabilityHandshake:
        if surface not in self._hs:
            raise HandshakeError(f"no surface {surface!r}; have "
                                 f"{sorted(self._hs)}")
        return self._hs[surface]

    def discover(self, operation: str, *,
                 surface_kind: "str | None" = None) -> list:
        """Which surfaces support this operation (optionally of one kind)."""
        return [h.surface for h in self._hs.values()
                if h.supports(operation)
                and (surface_kind is None or h.surface_kind == surface_kind)]

    def search_core(self, need: str, *,
                    top_n: "int | None" = None) -> list:
        """Search local handshake cards without invoking any capability."""
        from ..loop.loop_capsule import IntelligenceItemPackage, IntelligenceItemHandshake
        terms = set(str(need).lower().replace("_", " ").split())
        ranked = []
        for handshake in self._hs.values():
            text = " ".join((handshake.surface, handshake.functionality,
                             *handshake.operations, *handshake.query_fields,
                             *handshake.returns)).lower().replace("_", " ")
            tokens = set(text.split())
            score = len(terms & tokens)
            if score <= 0:
                continue
            digest = capability_handshake_digest(handshake)
            item_handshake = IntelligenceItemHandshake(
                item_id=handshake.surface, layer="code_intelligence",
                supported_modes=("deterministic",),
                input_contract="capability_request",
                output_contract="capability_handshake", effects=(),
                cost_class="free", maturity="registered",
                version=handshake.protocol_version)
            package = IntelligenceItemPackage(
                item_id=handshake.surface, layer="code_intelligence",
                handshake=item_handshake,
                payload_ref=f"capability://{handshake.surface}",
                payload_digest=digest,
                provenance="core", lifecycle="registered",
                facets={"surface_kind": handshake.surface_kind,
                        "handshake_digest": digest})
            ranked.append((score, handshake.surface,
                           package.to_ref(score=float(score),
                                          source="core")))
        ordered = sorted(ranked, key=lambda item: (-item[0], item[1]))
        return [item[2] for item in (
            ordered if top_n is None else ordered[:top_n])]

    # --- negotiation: does a surface support what a task needs? -------------

    def negotiate(self, surface: str,
                  required_ops: "Sequence[str]") -> dict:
        """Check a surface supports the required operations; name the fallback for
        any it does not — the practitioner negotiates before it commits."""
        h = self.handshake(surface)
        missing = [o for o in required_ops if not h.supports(o)]
        fallbacks = {}
        for o in missing:
            fb = self._fallback_for(surface, o)
            if fb:
                fallbacks[o] = fb
        return {"surface": surface, "ok": not missing, "missing": missing,
                "fallbacks": fallbacks}

    # --- standardized call, with declared fallback --------------------------

    def _fallback_for(self, surface: str, operation: str) -> "tuple | None":
        ep = self._ep.get((surface, operation))
        if ep and ep.fallback:
            return ep.fallback
        return self._default_fallback.get(surface)

    def _fallback_layer(self, from_s: str, from_op: str,
                        to_s: str, to_op: str) -> str:
        """Which of the three layers a fallback crossed."""
        if from_s == to_s:
            return "search_mode"            # same surface, another mechanism
        a, b = self._hs.get(from_s), self._hs.get(to_s)
        if a and b and a.surface_kind == b.surface_kind:
            return "surface"                # same capability class, another backend
        return "semantic"                   # a materially different method

    def call(self, surface: str, operation: str, *, ledger=None,
             policy: CapabilityInvocationPolicy | None = None,
             **kwargs) -> CallResult:
        """Invoke a bound callable; optional policy pins identity and blocks fallback.
        Ledger events retain start, completion, failure, and fallback identity."""
        if policy is not None and type(policy) is not CapabilityInvocationPolicy:
            raise TypeError("capability invocation policy must use its typed contract")
        policy = CapabilityInvocationPolicy() if policy is None else policy
        if ledger is not None:
            ledger.record(loop_id="", event="tool_invocation_started",
                          surface=surface, operation=operation)
        if surface not in self._hs:
            if ledger is not None:
                ledger.record(loop_id="", event="tool_invocation_failed",
                              surface=surface, operation=operation,
                              reason="no such surface")
            raise HandshakeError(f"no surface {surface!r}")
        ep = self._ep.get((surface, operation))
        function = ep.fn if ep is not None else None
        allow_fallback = policy.bind(self._hs[surface], function)
        if ep is None:
            fb = self._fallback_for(surface, operation) if allow_fallback else None
            if fb:
                r = self.call(fb[0], fb[1], ledger=ledger, **kwargs)
                return CallResult(surface, operation, r.ok, r.value, True,
                                  f"unsupported → fallback {fb[0]}.{fb[1]}",
                                  self._fallback_layer(surface, operation,
                                                       fb[0], fb[1]))
            if ledger is not None:
                ledger.record(loop_id="", event="tool_invocation_failed",
                              surface=surface, operation=operation,
                              reason="unsupported and no fallback")
            return CallResult(surface, operation, False, None, False,
                              "unsupported and no fallback declared")
        try:
            value = function(**kwargs)
            value_ok = (value.get("ok", True) if isinstance(value, dict)
                        else getattr(value, "ok", True))
            if not value_ok:
                note = (value.get("error_code") or value.get("error") or
                        "capability returned a typed failure") \
                    if isinstance(value, dict) else "capability returned failure"
                if ledger is not None:
                    ledger.record(loop_id="", event="tool_invocation_failed",
                                  surface=surface, operation=operation,
                                  reason=str(note)[:120])
                return CallResult(surface, operation, False, value, False,
                                  str(note))
            if ledger is not None:
                ledger.record(loop_id="", event="tool_invocation_completed",
                              surface=surface, operation=operation)
            return CallResult(surface, operation, True, value)
        except Exception as e:
            fb = (ep.fallback or self._default_fallback.get(surface)) if allow_fallback else None
            if fb:
                r = self.call(fb[0], fb[1], ledger=ledger, **kwargs)
                return CallResult(surface, operation, r.ok, r.value, True,
                                  f"error → fallback {fb[0]}.{fb[1]}: {e}",
                                  self._fallback_layer(surface, operation,
                                                       fb[0], fb[1]))
            if ledger is not None:
                ledger.record(loop_id="", event="tool_invocation_failed",
                              surface=surface, operation=operation,
                              reason=type(e).__name__)
            return CallResult(surface, operation, False, None, False,
                              f"error: {e}")

    def snapshot(self, *, gaps: "Sequence[str]" = (),
                 ledger=None) -> CapabilitySnapshot:
        """A compact, versioned view of what is available NOW — the practitioner
        gets this each pass instead of the full catalog (no context bloat).

        With a ledger attached the snapshot lands on the run's timeline as
        ``capability.snapshot.created``: what the loop could see when it
        decided is part of why it decided, so it belongs in the evidence."""
        avail = [h for h in self._hs.values() if h.health == "ok"]
        degraded = [h.surface for h in self._hs.values() if h.health != "ok"]
        modes = set()
        for h in avail:
            if "search" in h.operations:
                modes.update(h.ranking)
                modes.update(("exact_id", "metadata"))
        sid = "snap." + hashlib.sha256(
            "|".join(sorted(h.surface + h.protocol_version for h in avail))
            .encode()).hexdigest()[:10]
        by = lambda k: tuple(h.surface for h in avail if h.surface_kind == k)
        snap = CapabilitySnapshot(
            snapshot_id=sid,
            surfaces_available=tuple(h.surface for h in avail),
            surfaces_degraded=tuple(degraded),
            search_modes=tuple(sorted(modes)),
            string_stores=by("string_store"),
            code_registries=by("code_node_registry"),
            static_services=by("static_component"), gaps=tuple(gaps))
        if ledger is not None:
            ledger.record(loop_id="", event="capability.snapshot.created",
                          snapshot_id=snap.snapshot_id,
                          available=len(snap.surfaces_available),
                          degraded=len(snap.surfaces_degraded),
                          gaps=len(snap.gaps))
        return snap

    def search_by_need(self, query: "CapabilityQuery") -> list:
        """Federate a need across every searchable surface; return matches that
        keep their source surface + exact identity, ranked with the two-rail bias
        (prefer the exact zero-token code node unless a string was requested).

        This discovery path may execute only local, pure search endpoints.
        Network, secret-reading, metered, or externally hosted capabilities are
        represented by their local handshake cards and invoked only after an
        explicit selection through ``run_capability_as_loop``.
        """
        from ..core.asset_class import classify_record
        from ..core.facets import FacetFilter, facet_match
        flt = FacetFilter(require=dict(query.require_facets),
                          prefer=dict(query.prefer_facets),
                          exclude=dict(query.exclude_facets))
        text = query.as_search_text()
        matches: list = []
        for h in self._hs.values():
            if "search" not in h.operations:
                continue
            if h.locality != "local_machine" or tuple(h.effects) != ("pure",):
                continue
            ep = self._ep.get((h.surface, "search"))
            if ep is None:
                continue
            try:
                res = ep.fn(query=text)
            except Exception:
                continue
            for hit in (res.get("hits", []) if isinstance(res, dict) else []):
                # facets ride on the hit itself or inside its body record.
                hf = dict(hit.get("facets")
                          or (hit.get("body") or {}).get("facets") or {})
                score = 0
                if not flt.is_empty():
                    eligible, score, _why = facet_match(hf, flt)
                    if not eligible:
                        continue        # blocked/excluded by facet, never folder
                matches.append(CapabilityMatch(
                    resource_id=hit.get("record_id", ""),
                    asset_class=classify_record(hit),
                    source_surface=h.surface,
                    capability=query.desired_capability,
                    match_explanation=f"lexical match on {h.surface}",
                    invocation=f"{h.surface}.get",
                    facets=hf, facet_score=score))
        pref = query.preferred_class

        def rank(m):
            class_rank = ((0 if m.asset_class == "string" else 1)
                          if pref == "string"
                          else (0 if m.asset_class == "code" else 1))
            return (class_rank, -m.facet_score)   # code-first, then prefer-facets
        matches.sort(key=rank)
        return matches

    def serve(self, operation: str, *, prefer_kind: "str | None" = None,
              **kwargs) -> CallResult:
        """The two-rail bias in one call: find a code-node/static surface for the
        operation and use it; if none exists, fall back to the LLM-call pipeline
        (the string rail).  Prefer the exact zero-token path; ask the model only
        when nothing serves the need."""
        surfaces = self.discover(operation, surface_kind=prefer_kind)
        if surfaces:
            return self.call(surfaces[0], operation, **kwargs)
        if "llm_pipeline" in self._hs:
            r = self.call("llm_pipeline", "invoke", **kwargs)
            return CallResult("llm_pipeline", operation, r.ok, r.value, True,
                              "no code node serves this → asked the LLM (string "
                              "rail)")
        return CallResult("", operation, False, None, False,
                          "no surface and no LLM fallback")


def _search_endpoint(store):
    """The directory's search endpoint, bound through a Context Loop.

    Owner rule (2026-08-24): search returns loops and serving means running
    loops, so the endpoint a caller reaches must itself cross an envelope
    rather than hand back a bare store call."""
    from ..loop.intelligence_loops import search_as_loop

    def _search(**kw):
        return search_as_loop(store, kw.pop("query", ""), **kw)["value"]
    return _search


def _get_endpoint(store):
    """Fetch one selected resource through its intelligence access loop."""
    from ..loop.intelligence_loops import serve_record_as_loop

    def _get(**kw):
        return serve_record_as_loop(
            store, kw.get("record_id", ""),
            pillar=kw.get("pillar", "context_intelligence"))["value"]
    return _get


@dataclass(frozen=True)
class SurfaceRegistration:
    """One surface a code intelligence package offers to a directory.

    The package declares the handshake and endpoints; the directory registers
    them as declared. This keeps the dependency direction from code nodes to
    core: core never imports the package that owns the surface.
    """
    handshake: CapabilityHandshake
    endpoints: tuple = ()
    default_fallback: "tuple | None" = None

    def __post_init__(self):
        if not isinstance(self.handshake, CapabilityHandshake):
            raise HandshakeError("a surface registration needs a CapabilityHandshake")
        endpoints = tuple(self.endpoints)
        if any(not isinstance(item, Endpoint) for item in endpoints):
            raise HandshakeError("surface endpoints must be Endpoint records")
        if any(item.operation not in self.handshake.operations for item in endpoints):
            raise HandshakeError("every endpoint operation must be declared by the handshake")
        object.__setattr__(self, "endpoints", endpoints)


def default_directory(*, store=None,
                      llm_invoke: "Callable | None" = None,
                      surfaces: "Sequence[SurfaceRegistration]" = ()) -> CapabilityDirectory:
    """A directory of the standard surfaces the practitioner has: the search DAG,
    the string bank, the contract + logic code-node registries, the LLM-call
    pipeline, and the model gateway.  ``store`` wires real search; ``llm_invoke``
    is the string-rail fallback (a stub by default — no real model call here).
    ``surfaces`` adds typed registrations that code intelligence packages own."""
    d = CapabilityDirectory()

    def _llm(**kw):
        return (llm_invoke(**kw) if llm_invoke
                else {"asked_model": True,
                      "note": "would call the LLM-call pipeline (string rail)"})

    # the LLM-call pipeline — the ultimate string-rail fallback.
    d.register(CapabilityHandshake(
        "llm_pipeline", "static_component",
        "the LLM-call pipeline: ReasoningRequest → prompt assembly → invocation",
        operations=("invoke",), accepts=("string",), returns=("string",)),
        [Endpoint("invoke", _llm)])

    # the one search DAG over ALL resources (strings + code nodes).
    if store is not None:
        d.register(CapabilityHandshake(
            "resource_search", "static_component",
            "one strict search over every stored resource (strings and code "
            "nodes), tier-gated",
            operations=("search", "get"),
            query_fields=("title", "tags", "body"), ranking=("lexical",),
            embeddings=False, returns=("string", "code")),
            [Endpoint("search", _search_endpoint(store)),
             Endpoint("get", _get_endpoint(store))])

    # the string bank — the strings database.
    d.register(CapabilityHandshake(
        "string_bank", "string_store",
        "the strings database: personas, considerations, warnings, questions — "
        "composed into prompts",
        operations=("search", "compose"),
        query_fields=("tags", "applicability"), returns=("string",)),
        [],
        default_fallback=("resource_search", "search"))

    # the contract registry — code nodes that VALIDATE.
    d.register(CapabilityHandshake(
        "contract_registry", "code_node_registry",
        "runtime contracts: code nodes that admit/reject a result deterministically",
        operations=("get", "validate"), accepts=("code",)),
        [], default_fallback=("resource_search", "search"))

    # the logic registry — code nodes that DECIDE.
    d.register(CapabilityHandshake(
        "logic_registry", "code_node_registry",
        "logic rules: code nodes that decide deterministically over a context",
        operations=("get", "run"), accepts=("code",)),
        [], default_fallback=("llm_pipeline", "invoke"))

    # the model gateway.
    d.register(CapabilityHandshake(
        "model_gateway", "static_component",
        "provider-neutral model routes (cloud-only for counted generation)",
        operations=("resolve",)),
        [Endpoint("resolve", _model_resolve)])

    # surfaces supplied by code intelligence packages, registered as declared.
    for registration in surfaces:
        if not isinstance(registration, SurfaceRegistration):
            raise HandshakeError("surfaces must be typed SurfaceRegistration records")
        d.register(registration.handshake, registration.endpoints,
                   default_fallback=registration.default_fallback)
    return d


def _model_resolve(*, purpose="counted_generation", **kw):
    from ..core.model_routes import RouteRegistry, resolve_route
    return resolve_route(RouteRegistry(), purpose=purpose)


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    from .capability_directory_checks import run_checks
    return run_checks()
