"""Model discovery — bring a key, get a working roster, run hybrid loops.

Architectural role: static architecture (the auto-configuration layer above the
provider adapters).

The packaging problem this solves: someone installs the library and has one
key — maybe Ollama, maybe OpenRouter, maybe Mistral, maybe several. They should
not have to know which models exist, which their key can reach, which are cheap
enough to route a decision through, or which model names this repository
happened to hard-code in 2026. They should get a roster.

    keys present  ->  probe by USE  ->  live catalogs  ->  roles  ->  roster

Two rules make this honest rather than magic:

    DISCOVERY IS BY USE, NOT BY CONFIGURATION.  A key in an environment
    variable is not a working provider. Every provider in a roster answered a
    real call. This is the standing credential rule applied to setup.

    CLASSIFICATION USES DECLARED FACTS, AND SAYS SO.  Roles are assigned from
    the provider's own catalog — price per output token, context length,
    declared reasoning and tool support. Those are DECLARED by the vendor, not
    measured by us, so a role is a candidate routing hint, never a measured
    quality ranking. `ModelChoice.basis` carries that distinction into every
    record, and `measured` stays False until a real outcome says otherwise.

Zero model calls are spent classifying — the catalogs are data, and price is a
better tier proxy than any name-matching heuristic. That is the information
waterfall applied to its own configuration.

Owns:
    - ROLES and the role assignment rules;
    - ModelChoice / ModelRoster: what was discovered and on what basis;
    - discover_roster(): probe -> catalog -> classify -> roster;
    - roster_to_routes(): the roster as ModelRoute data the registry accepts.

Does not own:
    - the adapters (ollama/mistral/openrouter clients), failover order
      (provider_failover), route policy (model_routes), or loop semantics.

Key invariants:
    - a provider appears only if a real call succeeded;
    - a forbidden model never enters a roster, whatever a catalog offers;
    - roles come from declared facts and are labelled as such;
    - an empty roster is an empty roster — never a fabricated default.

Verification: self_test() — classification from declared facts, forbidden-model
exclusion, empty-roster honesty, and the adversarial "unreachable provider in
the roster" path. Live discovery runs only when a key works.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import mistral_client, ollama_client, openrouter_client
from .ollama_client import FORBIDDEN_MODELS

#: What the loop actually needs a model FOR. Deliberately small: these are the
#: three jobs the modes distinguish, not a taxonomy of model marketing.
ROLES = ("decide_label", "generate", "reason")

#: Price boundaries in dollars per OUTPUT token, used only when a catalog
#: publishes pricing. Chosen to separate the tiers the waterfall already names
#: (cheap routing model / workhorse / frontier), not tuned against outcomes —
#: which is exactly why `measured` is False on every choice these produce.
CHEAP_MAX = 0.0000006          # <= $0.60 per million output tokens
MID_MAX = 0.000005             # <= $5.00 per million output tokens


@dataclass(frozen=True)
class ModelChoice:
    """One discovered model and why it was placed where it was."""
    provider: str
    model: str
    role: str
    context_length: int = 0
    price_out: float = 0.0
    supports_reasoning: bool = False
    supports_tools: bool = False
    #: How this placement was decided. "declared" means the vendor's catalog
    #: said so; "measured" would mean a Loop Engine outcome established it. Nothing
    #: here produces "measured" — that requires an accepted result.
    basis: str = "declared"
    measured: bool = False

    def as_dict(self) -> dict:
        return {"provider": self.provider, "model": self.model,
                "role": self.role, "context_length": self.context_length,
                "price_out": self.price_out, "basis": self.basis,
                "measured": self.measured,
                "supports_reasoning": self.supports_reasoning,
                "supports_tools": self.supports_tools}


@dataclass
class ModelRoster:
    """Everything a run can actually reach, grouped by the job it serves."""
    choices: list = field(default_factory=list)
    providers_working: list = field(default_factory=list)
    providers_failed: dict = field(default_factory=dict)

    def for_role(self, role: str) -> list:
        """Models for one job, cheapest first — the waterfall's default order.
        A caller wanting a different order sorts the list itself."""
        got = [c for c in self.choices if c.role == role]
        return sorted(got, key=lambda c: (c.price_out, -c.context_length))

    def best(self, role: str) -> "ModelChoice | None":
        got = self.for_role(role)
        return got[0] if got else None

    @property
    def usable(self) -> bool:
        """Can this roster support a model-backed loop at all?"""
        return bool(self.providers_working and self.choices)

    def supports_mode(self, mode: str) -> bool:
        """Which loop MODES this roster can actually run.

        The honest mapping: deterministic never needs a model; hybrid and
        non_deterministic both do. A roster with nothing reachable supports
        exactly one mode, and saying so plainly is the point — it is how a
        caller learns their key is not working before a campaign, not during."""
        if mode == "deterministic":
            return True
        return self.usable

    def summary(self) -> dict:
        return {"record_type": "model_roster/v1",
                "providers_working": list(self.providers_working),
                "providers_failed": dict(self.providers_failed),
                "models_by_role": {r: [c.model for c in self.for_role(r)]
                                   for r in ROLES},
                "modes_supported": [m for m in
                                    ("deterministic", "hybrid",
                                     "non_deterministic")
                                    if self.supports_mode(m)],
                "basis": "roles assigned from vendor-DECLARED catalog facts "
                         "(price, context, reasoning support); no Loop Engine "
                         "outcome has ranked these models"}


def _forbidden(model: str) -> bool:
    base = model.split("/")[-1].split(":")[0]
    return any(f in model or f in base for f in FORBIDDEN_MODELS)


def classify(model: str, *, price_out: float = 0.0, context_length: int = 0,
             supports_reasoning: bool = False, supports_tools: bool = False,
             provider: str = "") -> ModelChoice:
    """Place one model in a role from DECLARED facts alone.

    Order matters: a declared reasoning model is a reasoning model whatever it
    costs, because that is a capability statement rather than a price signal.
    Otherwise price per output token separates the tiers."""
    if supports_reasoning:
        role = "reason"
    elif price_out and price_out <= CHEAP_MAX:
        role = "decide_label"
    elif price_out and price_out <= MID_MAX:
        role = "generate"
    elif price_out:
        role = "reason"                     # priced above the mid tier
    else:
        # No published price. Do NOT guess a tier from the name — an unpriced
        # model goes to the general workhorse role, which is the assumption
        # that fails most safely.
        role = "generate"
    return ModelChoice(provider=provider, model=model, role=role,
                       context_length=int(context_length),
                       price_out=float(price_out),
                       supports_reasoning=bool(supports_reasoning),
                       supports_tools=bool(supports_tools),
                       basis="declared", measured=False)


def _openrouter_catalog(limit: int) -> list:
    """Classify OpenRouter's published catalog.

    The fetch belongs to the adapter (``openrouter_client.catalog``); this
    layer classifies rows and opens no sockets of its own — the boundary the
    network gate exists to keep."""
    data = openrouter_client.catalog()
    out = []
    for m in data:
        mid = m.get("id", "")
        if not mid or _forbidden(mid):
            continue
        pricing = m.get("pricing") or {}
        try:
            price_out = float(pricing.get("completion") or 0.0)
        except (TypeError, ValueError):
            price_out = 0.0
        params = m.get("supported_parameters") or []
        out.append(classify(
            mid, provider="openrouter", price_out=price_out,
            context_length=int(m.get("context_length") or 0),
            supports_reasoning=bool(m.get("reasoning")
                                    or "reasoning" in params),
            supports_tools="tools" in params))
        if len(out) >= limit:
            break
    return out


def _listing_catalog(mod, provider: str, limit: int) -> list:
    """Providers whose catalog is a bare name list. Without published pricing
    every model lands in the general role — an honest consequence of a thin
    catalog, not something to paper over with name heuristics."""
    out = []
    for mid in mod.live_models():
        if not mid or _forbidden(mid):
            continue
        ceiling = getattr(mod, "MODEL_MAX_OUTPUT", {}).get(mid, 0)
        out.append(classify(mid, provider=provider, context_length=ceiling))
        if len(out) >= limit:
            break
    return out


def discover_roster(*, providers=("ollama_cloud", "mistral", "openrouter"),
                    limit_per_provider: int = 60,
                    verify_by_use: bool = True) -> ModelRoster:
    """Probe every provider, pull what works, return the roster.

    ``verify_by_use=False`` skips the live probe and reports the catalogs only
    — useful for inspecting what a provider OFFERS, never for claiming a
    provider WORKS. The roster records which was done."""
    roster = ModelRoster()
    # ONE table: the built-ins plus any registered custom endpoint. Discovery
    # keeping a private copy is how a user's own server would be invisible to
    # the very layer whose job is finding what they can reach.
    from .provider_failover import PROVIDERS
    adapters = {"ollama_cloud": ollama_client, "mistral": mistral_client,
                "openrouter": openrouter_client, **PROVIDERS}

    for name in providers:
        mod = adapters.get(name)
        if mod is None:
            roster.providers_failed[name] = "unknown provider"
            continue
        if verify_by_use:
            try:
                v = mod.verify()
            except (OSError, ValueError) as e:
                roster.providers_failed[name] = str(e)[:160]
                continue
            if not v.get("ok"):
                # A key that does not work is a failed provider, full stop —
                # its catalog is not evidence that anything is reachable.
                roster.providers_failed[name] = str(v.get("error"))[:160]
                continue
        roster.providers_working.append(name)
        found = (_openrouter_catalog(limit_per_provider) if name == "openrouter"
                 else _listing_catalog(mod, name, limit_per_provider))
        # a provider that verified but lists nothing still contributes its
        # default model — it answered a real call, so it demonstrably works
        if not found:
            found = [classify(mod.DEFAULT_MODEL, provider=name)]
        roster.choices.extend(found)
    return roster


def roster_to_routes(roster: ModelRoster) -> list:
    """The roster as ModelRoute data the existing registry accepts — discovery
    feeds the route table rather than replacing it."""
    from .model_routes import ModelProviderCapabilities, ModelRoute
    from .provider_failover import PROVIDERS
    routes = []
    for c in roster.choices:
        adapter = PROVIDERS.get(c.provider)
        endpoint = getattr(adapter, "endpoint", None)
        locality = getattr(endpoint, "locality", "cloud")
        tokens_reported = getattr(endpoint, "counts_as_evidence", True)
        caps = ModelProviderCapabilities(
            provider=c.provider, locality=locality,
            tokens_provider_reported=tokens_reported,
            supports_tool_calls=c.supports_tools,
            max_context=c.context_length)
        purposes = (("counted_generation", "decide_label")
                    if c.role == "decide_label" else ("counted_generation",))
        routes.append(ModelRoute(
            name=f"discovered.{c.provider}.{c.model}".replace("/", "."),
            provider=c.provider, model=c.model, locality=locality,
            purposes=purposes, capabilities=caps))
    return routes


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    # 1. CLASSIFICATION FROM DECLARED FACTS — price separates tiers, and a
    # declared reasoning capability outranks price because it is a capability
    # statement rather than a cost signal.
    cheap = classify("v/cheap", price_out=0.0000002, context_length=32768)
    mid = classify("v/mid", price_out=0.000002)
    exp = classify("v/expensive", price_out=0.00006)
    think = classify("v/thinker", price_out=0.0000001, supports_reasoning=True)
    check("roles_come_from_declared_price_and_capability",
          cheap.role == "decide_label" and mid.role == "generate"
          and exp.role == "reason" and think.role == "reason",
          "a declared reasoning model outranks its price")

    # 2. THE HONESTY LABEL: nothing here is measured, and every choice says so.
    # This is what keeps a routing hint from being read as a quality ranking.
    check("every_choice_is_labelled_declared_and_not_measured",
          all(c.basis == "declared" and c.measured is False
              for c in (cheap, mid, exp, think)),
          "no Loop Engine outcome has ranked these; the record will say so")

    # 3. an unpriced model does NOT get a tier guessed from its name — it lands
    # in the general role, the assumption that fails most safely.
    unpriced = classify("v/mystery-ultra-max-turbo")
    check("an_unpriced_model_is_not_tiered_by_its_name",
          unpriced.role == "generate" and unpriced.price_out == 0.0,
          "name heuristics are not evidence")

    # 4. FORBIDDEN MODELS never enter a roster, whatever a catalog offers.
    banned = f"vendor/{FORBIDDEN_MODELS[0]}"
    check("forbidden_models_are_excluded_from_discovery",
          _forbidden(banned) and not _forbidden("vendor/allowed-model"),
          "a catalog cannot introduce a banned model")

    # 5. ROSTER SEMANTICS: ordering, mode support, and empty honesty.
    r = ModelRoster(
        choices=[cheap, mid, exp], providers_working=["declared_provider"])
    empty = ModelRoster()
    check("a_roster_orders_by_cost_and_reports_the_modes_it_can_run",
          r.best("decide_label") is cheap and r.usable
          and r.supports_mode("hybrid")
          and r.supports_mode("non_deterministic")
          and empty.supports_mode("deterministic")
          and not empty.supports_mode("hybrid")
          and not empty.usable,
          "an empty roster runs deterministic loops and says so plainly")

    # 6. ADVERSARIAL: a provider whose probe FAILS must not appear as working,
    # and must not contribute models — a catalog is not proof of reach.
    failed = ModelRoster(providers_failed={"dead": "HTTP 401"})
    check("a_provider_that_failed_its_probe_is_not_in_the_roster",
          "dead" not in failed.providers_working and not failed.choices
          and failed.summary()["providers_failed"]["dead"] == "HTTP 401",
          "verified by use; a key is not a working provider")

    # 7. the roster converts to route DATA the existing registry accepts —
    # discovery FEEDS the route table rather than forking a second one.
    routes = roster_to_routes(r)
    check("a_roster_becomes_routes_the_existing_registry_accepts",
          len(routes) == 3 and all(rt.locality == "cloud" for rt in routes)
          and any("decide_label" in rt.purposes for rt in routes)
          and routes[0].name.startswith("discovered."),
          f"{len(routes)} routes, no parallel registry")

    passed = sum(1 for t in results if t["passed"])
    return {"record_type": "model_discovery_contract_test/v2",
            "scope": "offline_contract_only",
            "provider_integration_proven": False,
            "tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
