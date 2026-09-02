"""Model routes — provider-neutral model wiring; local is wired but policy-gated.

Owner rule (2026-08-23): local models can be a configurable system — we don't
need them right now, but *the wiring should be there* and support flexibility.
This module is that wiring: a model call goes through a named ``ModelRoute``, and
a route is DATA (provider + model + locality + what it's permitted for), not a
hard-coded branch.  Adding a provider is adding a route; enabling local is
flipping one policy flag — no code change.

The current policy stays CLOUD-ONLY for counted generation (the hard model rule:
benchmark/savings token counts must be provider-reported, and local runs are
unreproducible across machines).  But that is expressed as a POLICY over route
DATA, not baked into the call path:

  * ``counted_generation`` (benchmarks, savings, large authoring) -> CLOUD ONLY,
    unless ``RoutePolicy.allow_local_counted_generation`` is explicitly set.
  * ``decide_label`` (the narrow SLM waterfall: classify, route, score, draft) ->
    local ALLOWED — a local model may decide or label, never be the large
    generation workhorse.
  * ``embedding`` -> local allowed (embeddings are local; settled).

``kimi-k3`` is forbidden on every route, always.  This is the harness; the model
roster is data (the sanctioned Ollama Cloud set + a wired-but-disabled local
route), so an open-source consumer swaps the registry without touching the loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ..core.ollama_client import FORBIDDEN_MODELS, DEFAULT_MODEL

LOCALITIES = ("cloud", "organization", "local")
# What a model call is FOR — the axis the cloud-only rule actually turns on.
PURPOSES = (
    "counted_generation", "decide_label", "generation", "reasoning", "code",
    "vision", "tool_use", "embedding", "reranking", "query_rewrite",
    "structured_extract",
)


class RouteViolation(RuntimeError):
    """A model route the active policy forbids — refused with the reason."""


@dataclass(frozen=True)
class ModelProviderCapabilities:
    """A provider's machine-readable handshake (spec-style): declared, never
    assumed from a provider name."""
    provider: str
    locality: str                      # cloud | local
    tokens_provider_reported: bool     # are usage counts admissible as evidence?
    supports_structured_output: bool = False
    supports_tool_calls: bool = False
    max_context: int = 0

    def __post_init__(self):
        if self.locality not in LOCALITIES:
            raise ValueError(f"locality must be one of {LOCALITIES}")


@dataclass(frozen=True)
class ModelRoute:
    """One named way to reach a model.  DATA — the call path reads it, never
    hard-codes it."""
    name: str
    provider: str
    model: str
    locality: str = "cloud"
    # Which purposes this route DECLARES it can serve (policy still decides).
    purposes: tuple = ("counted_generation",)
    capabilities: "ModelProviderCapabilities | None" = None

    def __post_init__(self):
        if self.locality not in LOCALITIES:
            raise ValueError(f"locality must be one of {LOCALITIES}")
        base = self.model.split("/")[-1].split(":")[0]
        if any(f in self.model or f in base for f in FORBIDDEN_MODELS):
            raise ValueError(f"model {self.model!r} is forbidden by policy")
        for p in self.purposes:
            if p not in PURPOSES:
                raise ValueError(f"unknown purpose {p!r}; valid: {PURPOSES}")


@dataclass
class RoutePolicy:
    """The flexibility switches.  Defaults encode the current CLOUD-ONLY rule;
    every switch is here so enabling local is a config change, not a code edit."""
    allow_local_counted_generation: bool = False   # HARD rule: cloud-only now
    allow_local_decide_label: bool = True          # narrow SLM exception: allowed
    allow_local_embedding: bool = True             # embeddings are local
    allow_local_query_rewrite: bool = False        # off until a local route
    allow_local_structured_extract: bool = False   #   proves it on fixtures


class RouteRegistry:
    """The routes available to a run — data, swappable wholesale for open-source
    consumers."""

    def __init__(self, routes: "Sequence[ModelRoute] | None" = None):
        self._by_name: dict = {}
        for r in (routes if routes is not None else default_routes()):
            self._by_name[r.name] = r

    def add(self, route: ModelRoute) -> None:
        self._by_name[route.name] = route

    def get(self, name: str) -> ModelRoute:
        if name not in self._by_name:
            raise KeyError(f"no route named {name!r}; have "
                           f"{sorted(self._by_name)}")
        return self._by_name[name]

    def all(self) -> list:
        return list(self._by_name.values())

    def for_purpose(self, purpose: str, *,
                    policy: "RoutePolicy | None" = None) -> list:
        """Every route the policy PERMITS for this purpose — cheapest wiring for
        'which model can I use here?'."""
        pol = policy or RoutePolicy()
        out = []
        for r in self._by_name.values():
            if purpose not in r.purposes:
                continue
            try:
                screen_route(r, purpose=purpose, policy=pol)
            except RouteViolation:
                continue
            out.append(r)
        return out


def default_routes() -> list:
    """The sanctioned roster as route DATA: Ollama Cloud models (cloud, counted
    generation) plus ONE wired-but-policy-disabled local route and a local
    embedding route.  The local routes prove the wiring exists; policy keeps them
    off for counted generation."""
    cloud_caps = ModelProviderCapabilities(
        provider="ollama_cloud", locality="cloud",
        tokens_provider_reported=True, supports_structured_output=True,
        max_context=131072)
    routes = [
        ModelRoute("cloud.default", "ollama_cloud", DEFAULT_MODEL, "cloud",
                   purposes=("counted_generation", "decide_label"),
                   capabilities=cloud_caps),
        ModelRoute("cloud.hard", "ollama_cloud", "deepseek-v4-pro:0813",
                   "cloud", purposes=("counted_generation",),
                   capabilities=cloud_caps),
        ModelRoute("cloud.glm", "ollama_cloud", "glm-5.3-flash", "cloud",
                   purposes=("counted_generation",), capabilities=cloud_caps),
    ]
    # The other sanctioned hosted providers.  Added 2026-08-24 after a single
    # provider's 429 stopped every model-backed arm: provider plurality is what
    # keeps a campaign running when one vendor says no.  Both report tokens, so
    # both are admissible for counted generation.
    mistral_caps = ModelProviderCapabilities(
        provider="mistral", locality="cloud", tokens_provider_reported=True,
        supports_structured_output=True, max_context=131072)
    routes.append(ModelRoute(
        "cloud.mistral", "mistral", "mistral-small-latest", "cloud",
        purposes=("counted_generation", "decide_label"),
        capabilities=mistral_caps))
    routes.append(ModelRoute(
        "cloud.mistral.large", "mistral", "mistral-large-latest", "cloud",
        purposes=("counted_generation",), capabilities=mistral_caps))

    # OpenRouter aggregates many upstreams behind one key — a failover peer and
    # a breadth surface.  Its key was dead when this route was added; a route is
    # a declared way to reach a model, not a claim that the credential works.
    openrouter_caps = ModelProviderCapabilities(
        provider="openrouter", locality="cloud", tokens_provider_reported=True,
        supports_structured_output=True, supports_tool_calls=True,
        max_context=131072)
    routes.append(ModelRoute(
        "cloud.openrouter", "openrouter", "deepseek/deepseek-chat", "cloud",
        purposes=("counted_generation", "decide_label"),
        capabilities=openrouter_caps))
    routes.append(ModelRoute(
        "cloud.openrouter.reasoning", "openrouter", "deepseek/deepseek-r1",
        "cloud", purposes=("counted_generation",),
        capabilities=openrouter_caps))

    # Wired-but-disabled: a local small-model route, present so 'local' is a real
    # object the policy governs — NOT permitted for counted generation by default.
    local_caps = ModelProviderCapabilities(
        provider="ollama_local", locality="local",
        tokens_provider_reported=False, max_context=8192)
    routes.append(ModelRoute(
        "local.slm", "ollama_local", "qwen3.5:local-slm", "local",
        purposes=("decide_label",), capabilities=local_caps))
    routes.append(ModelRoute(
        "local.embed", "ollama_local", "local-feature-hash", "local",
        purposes=("embedding",), capabilities=local_caps))
    return routes


def screen_route(route: ModelRoute, *, purpose: str,
                 policy: "RoutePolicy | None" = None) -> ModelRoute:
    """The one gate every model call passes.  Enforces the cloud-only rule as a
    policy over route data, and refuses with a plain-English reason.

    A local route may serve narrow decide/label and embedding by default; it may
    serve *counted generation* only when the policy explicitly permits it — the
    wiring is here, the switch is off."""
    pol = policy or RoutePolicy()
    if purpose not in PURPOSES:
        raise RouteViolation(f"unknown purpose {purpose!r}; valid: {PURPOSES}")
    # kimi-k3 (and any forbidden family) — never, on any route, any purpose.
    base = route.model.split("/")[-1].split(":")[0]
    if any(f in route.model or f in base for f in FORBIDDEN_MODELS):
        raise RouteViolation(f"model {route.model!r} is forbidden by policy")
    if purpose not in route.purposes:
        raise RouteViolation(
            f"route {route.name!r} does not serve {purpose!r} "
            f"(serves {route.purposes})")
    if route.locality == "local":
        if purpose == "counted_generation" \
                and not pol.allow_local_counted_generation:
            raise RouteViolation(
                "CLOUD-ONLY policy: counted generation (benchmarks, savings, "
                "large authoring) must use a cloud route whose tokens are "
                "provider-reported; local route "
                f"{route.name!r} is refused.  The wiring exists — set "
                "RoutePolicy.allow_local_counted_generation to enable it "
                "deliberately.")
        if purpose == "decide_label" and not pol.allow_local_decide_label:
            raise RouteViolation(
                f"local decide/label disabled by policy for {route.name!r}")
        if purpose == "embedding" and not pol.allow_local_embedding:
            raise RouteViolation(
                f"local embedding disabled by policy for {route.name!r}")
        if purpose == "query_rewrite" \
                and not pol.allow_local_query_rewrite:
            raise RouteViolation(
                f"local query rewrite disabled by policy for {route.name!r}")
        if purpose == "structured_extract" \
                and not pol.allow_local_structured_extract:
            raise RouteViolation(
                f"local structured extract disabled by policy for "
                f"{route.name!r}")
    return route


def resolve_route(registry: RouteRegistry, *, purpose: str,
                  prefer: str = "", policy: "RoutePolicy | None" = None
                  ) -> ModelRoute:
    """Pick the route for a purpose: the preferred one if it passes the gate,
    else the first permitted route.  Raises if nothing is permitted."""
    pol = policy or RoutePolicy()
    if prefer:
        return screen_route(registry.get(prefer), purpose=purpose, policy=pol)
    permitted = registry.for_purpose(purpose, policy=pol)
    if not permitted:
        raise RouteViolation(
            f"no route permitted for purpose {purpose!r} under the active "
            f"policy")
    return permitted[0]


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    reg = RouteRegistry()

    # 1. a route is DATA; the default registry carries cloud routes plus a
    # wired local route (the flexibility is present as an object).
    localities = {r.name: r.locality for r in reg.all()}
    check("local_is_wired_as_a_real_route_object",
          "local.slm" in localities and localities["local.slm"] == "local"
          and any(v == "cloud" for v in localities.values()),
          f"routes: {localities}")

    # 2. CLOUD-ONLY holds by default: a local route that DECLARES counted
    # generation is still REFUSED for it, with a reason that names the switch.
    denied = ""
    local_cg = ModelRoute("local.cg", "ollama_local", "qwen3.5:local", "local",
                          purposes=("counted_generation",))
    try:
        screen_route(local_cg, purpose="counted_generation")
    except RouteViolation as e:
        denied = str(e)
    check("cloud_only_refuses_local_counted_generation_by_default",
          "CLOUD-ONLY" in denied and "allow_local_counted_generation" in denied,
          denied[:90])

    # 3. but the WIRING supports flipping it — one policy flag, no code change.
    ok = screen_route(
        ModelRoute("local.big", "ollama_local", "qwen3.5:local", "local",
                   purposes=("counted_generation",)),
        purpose="counted_generation",
        policy=RoutePolicy(allow_local_counted_generation=True))
    check("the_switch_exists_local_counted_generation_is_enableable",
          ok.locality == "local",
          "allow_local_counted_generation=True permits it deliberately")

    # 4. the narrow SLM exception: local decide/label is allowed by default.
    dl = screen_route(reg.get("local.slm"), purpose="decide_label")
    check("local_decide_label_is_allowed_the_slm_waterfall_exception",
          dl.name == "local.slm",
          "a local model may decide/label, never be the generation workhorse")

    # 4b. Bounded local jobs are their own purposes with their own switches:
    # off by default (fail-closed like counted generation), enableable per
    # policy once a local route proves itself on fixtures.
    rewrite_refused = ""
    try:
        screen_route(
            ModelRoute("local.rw", "ollama_local", "qwen3.5:local", "local",
                       purposes=("query_rewrite",)),
            purpose="query_rewrite")
    except RouteViolation as e:
        rewrite_refused = str(e)
    rewrite_ok = screen_route(
        ModelRoute("local.rw2", "ollama_local", "qwen3.5:local", "local",
                   purposes=("query_rewrite",)),
        purpose="query_rewrite",
        policy=RoutePolicy(allow_local_query_rewrite=True))
    extract_refused = ""
    try:
        screen_route(
            ModelRoute("local.se", "ollama_local", "qwen3.5:local", "local",
                       purposes=("structured_extract",)),
            purpose="structured_extract")
    except RouteViolation as e:
        extract_refused = str(e)
    check("bounded_local_purposes_are_fail_closed_then_enableable",
          "disabled by policy" in rewrite_refused
          and rewrite_ok.locality == "local"
          and "disabled by policy" in extract_refused,
          "query_rewrite and structured_extract follow the same switch "
          "pattern as every other purpose")

    # 5. kimi-k3 can never be a route, any purpose, any locality.
    bad = 0
    try:
        ModelRoute("x", "ollama_cloud", "kimi-k3:cloud")
    except ValueError:
        bad += 1
    check("kimi_k3_can_never_be_routed", bad == 1,
          "the forbidden family is refused at construction")

    # 6. resolve_route picks a permitted cloud route for counted generation.
    r = resolve_route(reg, purpose="counted_generation")
    check("counted_generation_resolves_to_a_cloud_route",
          r.locality == "cloud",
          f"resolved {r.name} ({r.locality})")

    # 7. the provider handshake is declared, not assumed.
    caps = reg.get("cloud.default").capabilities
    check("provider_capabilities_are_a_declared_handshake",
          caps is not None and caps.tokens_provider_reported is True
          and caps.locality == "cloud",
          "cloud tokens are provider-reported (admissible as evidence)")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "model_routes_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
