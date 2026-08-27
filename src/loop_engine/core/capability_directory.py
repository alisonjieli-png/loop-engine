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
import json
from dataclasses import dataclass, field, asdict
from typing import Callable, Sequence

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

    def search_core(self, need: str, *, top_n: int = 8) -> list:
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
            digest = hashlib.sha256(json.dumps(
                handshake.describe(), sort_keys=True, default=str).encode()
                                    ).hexdigest()
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
        return [item[2] for item in sorted(
            ranked, key=lambda item: (-item[0], item[1]))[:top_n]]

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
             **kwargs) -> CallResult:
        """Invoke an endpoint uniformly.  On a missing operation or an error,
        follow the declared fallback (a bias) rather than crashing — recording
        WHICH of the three fallback layers was crossed.

        With a ``ledger`` the invocation lands on the run's timeline as
        ``tool.invocation.started`` and then ``.completed`` or ``.failed`` —
        a tool call is an operational boundary and should not be invisible."""
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
        if ep is None:
            fb = self._fallback_for(surface, operation)
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
            value = ep.fn(**kwargs)
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
        except Exception as e:                                  # noqa: BLE001
            fb = ep.fallback or self._default_fallback.get(surface)
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

    # --- the compact snapshot + search-by-need ------------------------------

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
            except Exception:                                   # noqa: BLE001
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


def default_directory(*, store=None,
                      llm_invoke: "Callable | None" = None) -> CapabilityDirectory:
    """A directory of the standard surfaces the practitioner has: the search DAG,
    the string bank, the contract + logic code-node registries, the LLM-call
    pipeline, and the model gateway.  ``store`` wires real search; ``llm_invoke``
    is the string-rail fallback (a stub by default — no real model call here)."""
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
    return d


def _model_resolve(*, purpose="counted_generation", **kw):
    from ..core.model_routes import RouteRegistry, resolve_route
    return resolve_route(RouteRegistry(), purpose=purpose)


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    from ..core.store_serve import SolverStore, StoreRecord
    from ..core.facets import code_facets, string_facets
    store = SolverStore(core_records=[
        StoreRecord("n.vif", "node", "compute variance inflation factor",
                    body={"kind": "node",
                          "facets": code_facets(
                              execution_mode="code_only",
                              determinism="deterministic",
                              locality="local_machine", effects=("pure",),
                              role="detect")},
                    tags=("stats", "collinearity")),
        StoreRecord("n.vif_api", "node",
                    "compute variance inflation factor via hosted stats API",
                    body={"kind": "node",
                          "facets": code_facets(
                              execution_mode="code_only",
                              determinism="deterministic",
                              locality="api_calling", effects=("network",),
                              cost_class="metered", role="detect")},
                    tags=("stats", "collinearity")),
        StoreRecord("s.warn", "context", "watch for temporal leakage",
                    body={"string_kind": "warning",
                          "facets": string_facets(
                              category="risk", subcategory="leakage",
                              job_position="risk_officer")},
                    tags=("leakage",))])
    d = default_directory(store=store)

    # 1. the practitioner KNOWS what is available, by surface kind.
    kinds = {h.surface: h.surface_kind for h in d.available()}
    check("practitioner_knows_the_available_surfaces",
          kinds.get("string_bank") == "string_store"
          and kinds.get("contract_registry") == "code_node_registry"
          and kinds.get("llm_pipeline") == "static_component"
          and kinds.get("resource_search") == "static_component",
          f"{len(kinds)} surfaces across strings / code nodes / static")

    # 2. the HANDSHAKE tells it HOW to call + WHAT is available (never assumed).
    hs = d.handshake("resource_search")
    check("handshake_declares_operations_and_search_fields",
          hs.supports("search") and "title" in hs.query_fields
          and not hs.embeddings and hs.functionality,
          "operations, query fields, ranking, and functionality are declared")

    # 3. discover: which surfaces support an operation.
    searchers = d.discover("search")
    validators = d.discover("validate", surface_kind="code_node_registry")
    check("discover_finds_surfaces_by_operation",
          "resource_search" in searchers and "string_bank" in searchers
          and validators == ["contract_registry"],
          f"search: {searchers}; validate: {validators}")

    # 4. negotiate: a supported op is ok; an unsupported one names a fallback.
    ok_neg = d.negotiate("resource_search", ["search", "get"])
    bad_neg = d.negotiate("contract_registry", ["validate", "search"])
    check("negotiate_reports_support_and_fallbacks",
          ok_neg["ok"] and not bad_neg["ok"]
          and bad_neg["missing"] == ["search"]
          and bad_neg["fallbacks"]["search"] == ("resource_search", "search"),
          "the practitioner negotiates before committing")

    # 5. a standardized CALL actually invokes the endpoint (real search).
    r = d.call("resource_search", "search", query="variance inflation collinearity")
    check("standardized_call_invokes_the_endpoint",
          r.ok and not r.used_fallback and r.value
          and any("vif" in h["record_id"] for h in r.value["hits"]),
          "call('resource_search','search',...) returns real hits")

    # 6. a missing operation follows the declared FALLBACK (a bias, not a crash).
    r2 = d.call("contract_registry", "search",
                query="temporal leakage warning")
    check("missing_operation_follows_the_declared_fallback",
          r2.ok and r2.used_fallback
          and "resource_search" in r2.note,
          "contract_registry has no search → fell back to resource_search")

    # 7. serve = the two-rail bias: no code node for a need → the LLM pipeline.
    served = d.serve("summarize")             # nothing supports 'summarize'... but
    # 'summarize' is not a standard op; discover returns [], so it asks the LLM.
    check("serve_falls_back_to_the_llm_when_no_code_node_serves",
          served.used_fallback and served.surface == "llm_pipeline"
          and served.value.get("asked_model"),
          "prefer a code node; ask the model (string rail) only when none serves")

    # 8. an unknown surface raises (no silent guessing).
    bad = False
    try:
        d.handshake("nope")
    except HandshakeError:
        bad = True
    check("unknown_surface_raises", bad, "a capability is never assumed")

    # 9. the COMPACT snapshot: versioned, by kind, and rendered for the model —
    # full awareness WITHOUT loading the catalog.
    snap = d.snapshot(gaps=("no medical-literature graph registered",))
    txt = snap.render()
    check("compact_capability_snapshot_is_versioned_and_rendered",
          snap.snapshot_id.startswith("snap.")
          and "string_bank" in snap.string_stores
          and "contract_registry" in snap.code_registries
          and "AVAILABLE CAPABILITIES" in txt and "Known gaps" in txt
          and len(txt) < 700,
          f"snapshot {snap.snapshot_id}: compact model-facing summary")

    # 10. search BY NEED (not by filename): matches keep their source surface +
    # asset class, ranked code-first (the zero-token bias).
    q = CapabilityQuery(obligation="assess redundancy",
                        desired_capability="assess feature collinearity",
                        tags=("collinearity", "stats"), preferred_class="either")
    ms = d.search_by_need(q)
    check("search_by_need_returns_matches_with_provenance",
          ms and ms[0].source_surface == "resource_search"
          and ms[0].asset_class == "code" and ms[0].resource_id,
          f"{len(ms)} match(es); first is a code node from "
          f"{ms[0].source_surface if ms else '—'}")

    # 10b. FACET BLOCKING: require locality=local_machine drops the API-calling
    # variant of the same capability — blocked by facet, never by folder.
    q_local = CapabilityQuery(
        obligation="assess redundancy",
        desired_capability="assess feature collinearity",
        tags=("collinearity", "stats"),
        require_facets={"locality": "local_machine"})
    ms_local = d.search_by_need(q_local)
    ids_local = {m.resource_id for m in ms_local}
    check("require_facet_blocks_api_calling_by_facet_not_folder",
          "n.vif" in ids_local and "n.vif_api" not in ids_local,
          f"local-only search kept {sorted(ids_local)}")

    # 10c. EXCLUDE by evidence: effects=network excluded; the pure node stays.
    q_off = CapabilityQuery(
        obligation="assess redundancy",
        desired_capability="assess feature collinearity",
        tags=("collinearity", "stats"),
        exclude_facets={"effects": "network",
                        "locality": ("api_calling", "external_resources")})
    ids_off = {m.resource_id for m in d.search_by_need(q_off)}
    check("offline_exclusion_drops_network_node_keeps_pure",
          "n.vif" in ids_off and "n.vif_api" not in ids_off,
          f"offline search kept {sorted(ids_off)}")

    # 10d. PREFER is a soft rank: preferring the metered API node reorders it
    # first WITHOUT dropping the local one.
    q_pref = CapabilityQuery(
        obligation="assess redundancy",
        desired_capability="assess feature collinearity",
        tags=("collinearity", "stats"),
        prefer_facets={"locality": "api_calling"})
    ms_pref = d.search_by_need(q_pref)
    code_hits = [m for m in ms_pref if m.asset_class == "code"]
    check("prefer_facet_reorders_without_excluding",
          {m.resource_id for m in code_hits} >= {"n.vif", "n.vif_api"}
          and code_hits[0].resource_id == "n.vif_api",
          "both nodes present; preferred one ranked first")

    # 10e. job-position lens on Context Intelligence.
    q_job = CapabilityQuery(
        obligation="warn about leakage",
        desired_capability="temporal leakage warning",
        tags=("leakage",), preferred_class="string",
        require_facets={"job_position": "risk_officer"})
    ms_job = d.search_by_need(q_job)
    check("job_position_lens_focuses_context_intelligence",
          ms_job and ms_job[0].resource_id == "s.warn"
          and ms_job[0].facets.get("job_position") == "risk_officer",
          "search focused one position's intelligence")

    # 11. the SEMANTIC fallback layer: a code registry with no such op falls
    # back to the LLM pipeline — a materially different method, labelled.
    r3 = d.call("logic_registry", "search", query="how to decide collinearity")
    check("semantic_fallback_layer_is_labelled",
          r3.used_fallback and r3.fallback_layer == "semantic",
          "code node → LLM pipeline is a semantic fallback (a new method)")

    # D-4: what the loop COULD see when it decided is part of why it decided,
    # so the snapshot belongs on the timeline.  Without a ledger the behaviour
    # is byte-identical — visibility is opt-in, never a behaviour change.
    from ..loop.recursive_loop import LoopLedger
    from ..core.run_history import to_canonical_events
    _lg = LoopLedger()
    _quiet = d.snapshot()
    _loud = d.snapshot(ledger=_lg)
    _fams = [c["type"] for c in to_canonical_events(_lg.events)]
    check("the_capability_snapshot_lands_on_the_timeline",
          _loud.snapshot_id == _quiet.snapshot_id
          and _fams == ["capability.snapshot.created"]
          and _lg.events[0]["snapshot_id"] == _loud.snapshot_id,
          f"snapshot {_loud.snapshot_id} recorded; identical without a ledger")

    static_refs = d.search_core(
        "provider neutral model routes")
    check("core_search_returns_local_loop_refs_without_calls",
          static_refs and static_refs[0].item_ref.endswith("model_gateway")
          and static_refs[0].source == "core"
          and static_refs[0].handshake.layer == "code_intelligence")

    unsafe_calls = []
    d.register(CapabilityHandshake(
        "remote_fixture_search", "static_component",
        "search a remote fixture service", operations=("search",),
        locality="api_calling", effects=("network",), cost_class="metered"),
        [Endpoint("search", lambda query: unsafe_calls.append(query) or {
            "hits": []})])
    remote_refs = d.search_core("remote fixture search")
    d.search_by_need(CapabilityQuery(
        obligation="find fixture", desired_capability="remote fixture search"))
    check("federated_discovery_never_executes_effectful_search_endpoints",
          remote_refs and not unsafe_calls
          and remote_refs[0].item_ref.endswith("remote_fixture_search"),
          "effectful capability is discoverable as a local ref, not called")

    duplicate_refused = False
    try:
        d.register(d.handshake("model_gateway"))
    except HandshakeError:
        duplicate_refused = True
    check("duplicate_static_surface_registration_is_refused",
          duplicate_refused)

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "capability_directory_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
