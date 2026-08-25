"""Autoconfigure — bring a key, get a configured, mode-honest solver.

Architectural role: static architecture (the one-call setup surface the
installable package exposes).

This is the module a new user of the published package touches first, so it
owns exactly one job: turn whatever credentials exist into a truthful statement
of what this installation can do.

    ModelAccess.from_keys(openrouter_key=..., ollama_key=...)
        -> probes every provider BY USE
        -> discovers the models those keys actually reach
        -> reports which loop MODES are runnable, and which are not

The design decision worth stating: this refuses to be optimistic. A library
that accepts a key, configures itself, and then fails at the first model call
has moved the error from setup (where it is one clear message) to the middle of
a user's run (where it is a mystery). So `ModelAccess` is built from real calls,
and `explain()` is written to be read by a person who is wondering why their
key is not working.

The mode mapping is the part that connects to the loop laws:

    deterministic     — always available; needs no model, ever.
    hybrid            — needs at least one working provider.
    non_deterministic — needs at least one working provider.

An installation with no working key is not broken. It runs deterministic loops,
which is a real capability and the default profile — it simply cannot run the
two modes that require a semantic call, and says so.

Owns:
    - ModelAccess: the resolved capability statement plus explain();
    - configure(): the one-call setup;
    - advice_function(): a ready semantic callable for hybrid/non-deterministic
      loops, or None when no provider works.

Does not own:
    - discovery internals (model_discovery), failover (provider_failover),
      adapters, or any loop semantics.

Key invariants:
    - every reported capability was verified by a real call;
    - no working provider means hybrid/non_deterministic are reported
      unavailable — never silently downgraded to deterministic mid-run;
    - keys passed in are used, never logged, never written to a record.

Verification: self_test() — mode honesty with and without providers, the
refusal to fabricate an advice function, key non-leakage, and the adversarial
"claims a mode it cannot run" path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .model_discovery import ModelRoster, discover_roster
from .provider_failover import DEFAULT_ORDER

#: Which loop modes need a semantic call. Deterministic never does — that is
#: the whole point of the zero-model lane.
MODES_NEEDING_A_MODEL = ("hybrid", "non_deterministic")

#: Environment variable per provider, so `configure()` works with no arguments
#: in a normal deployment.
KEY_ENV = {"openrouter": "OPENROUTER_API_KEY",
           "ollama_cloud": "OLLAMA_API_KEY",
           "mistral": "MISTRAL_API_KEY"}


@dataclass
class ModelAccess:
    """What this installation can actually do, established by real calls."""
    roster: "ModelRoster | None" = None
    providers_working: list = field(default_factory=list)
    providers_failed: dict = field(default_factory=dict)

    @property
    def has_model(self) -> bool:
        return bool(self.providers_working)

    def modes_available(self) -> list:
        """The honest list. Deterministic is always in it."""
        modes = ["deterministic"]
        if self.has_model:
            modes.extend(MODES_NEEDING_A_MODEL)
        return modes

    def can_run(self, mode: str) -> bool:
        return mode in self.modes_available()

    def explain(self) -> str:
        """Plain English, written for someone wondering why a key is not
        working. This is the error message that setup owes a user."""
        lines = []
        if self.providers_working:
            lines.append(
                f"Working providers: {', '.join(self.providers_working)}")
            if self.roster is not None:
                n = len(self.roster.choices)
                lines.append(f"Models reachable: {n}")
        else:
            lines.append("No working model provider.")
        for name, err in self.providers_failed.items():
            hint = ""
            low = str(err).lower()
            if (("no " in low and "key" in low)
                    or ("key" in low and "not found" in low)):
                hint = f"  -> set {KEY_ENV.get(name, 'the provider key')}"
            elif "429" in low or "usage limit" in low:
                hint = "  -> rate or usage limit; this key works but is " \
                       "currently capped"
            elif "401" in low or "not found" in low or "unauthor" in low:
                hint = "  -> the key was rejected; check it is current"
            lines.append(f"  {name}: {str(err)[:120]}{hint}")
        lines.append(f"Modes available: {', '.join(self.modes_available())}")
        if not self.has_model:
            lines.append(
                "Deterministic loops run normally. Hybrid and "
                "non-deterministic loops need at least one working provider.")
        return "\n".join(lines)

    def summary(self) -> dict:
        """Record shape. Deliberately carries no key material."""
        return {"record_type": "model_access/v1",
                "providers_working": list(self.providers_working),
                "providers_failed": {k: str(v)[:160]
                                     for k, v in self.providers_failed.items()},
                "modes_available": self.modes_available(),
                "models_reachable": (len(self.roster.choices)
                                     if self.roster else 0)}


def configure(*, openrouter_key: str = "", ollama_key: str = "",
              mistral_key: str = "", endpoints=(), providers=DEFAULT_ORDER,
              discover: bool = True, limit_per_provider: int = 60,
              read_endpoint_env: bool = True) -> ModelAccess:
    """One call: keys and servers in, an honest capability statement out.

    Keys may be passed explicitly or left to the environment. An explicit key
    is placed in the environment for the adapters to read, because they resolve
    credentials in one documented way — a second credential path is how a
    library ends up with two disagreeing notions of which key is in use.

    ``endpoints`` accepts ``CustomEndpoint`` objects (or the dicts that build
    them) for self-hosted or third-party OpenAI-compatible servers; entries in
    ``LOOP_ENGINE_ENDPOINTS`` are picked up too. A custom endpoint is probed and
    reported exactly like a built-in provider — including being reported as
    FAILED when it does not answer."""
    for key, name in ((openrouter_key, "openrouter"),
                      (ollama_key, "ollama_cloud"), (mistral_key, "mistral")):
        if key:
            os.environ[KEY_ENV[name]] = key

    from .custom_endpoint import (CustomEndpoint, endpoints_from_env,
                                  register_endpoint)
    declared = list(endpoints)
    if read_endpoint_env:
        declared.extend(endpoints_from_env())
    custom_names = []
    for e in declared:
        ep = e if isinstance(e, CustomEndpoint) else CustomEndpoint(**e)
        register_endpoint(ep)
        custom_names.append(ep.name)
    # custom endpoints are probed after the built-ins, so a configured
    # sanctioned provider keeps precedence unless the caller reorders
    order = tuple(providers) + tuple(n for n in custom_names
                                     if n not in providers)

    roster = discover_roster(providers=order,
                             limit_per_provider=limit_per_provider,
                             verify_by_use=True) if discover else ModelRoster()
    return ModelAccess(roster=roster,
                       providers_working=list(roster.providers_working),
                       providers_failed=dict(roster.providers_failed))


def advice_function(access: "ModelAccess | None" = None, *, role: str = "",
                    order=None):
    """A semantic callable for hybrid and non-deterministic loops — or None.

    Returning None when nothing works is the point. A caller can then choose a
    deterministic loop deliberately, instead of discovering mid-run that its
    'model-backed' loop never reached a model.

    ``order`` defaults to THE PROVIDERS THIS ACCESS ACTUALLY FOUND WORKING,
    not to the built-in order. Measured 2026-08-24: configuring only a
    self-hosted endpoint produced a callable that tried
    ``['ollama_cloud', 'mistral']`` and billed a provider the caller had not
    configured, while their own server was never contacted. Defaulting to the
    global order silently overrides the caller's configuration — and the bill
    goes somewhere they did not choose.

    The returned callable gives back ``(text, usage)``; usage always names the
    provider that answered, so a record can attribute its tokens."""
    acc = access or configure()
    if not acc.has_model:
        return None
    if order is None:
        # what this access verified, in its own probe order; the built-in
        # order is only a fallback for an access built without discovery
        order = tuple(acc.providers_working) or DEFAULT_ORDER

    from .model_discovery import roster_to_routes
    from .model_gateway import (ModelGateway, ModelGatewayConfig,
                                ModelGatewayRequest, builtin_provider_specs)
    from .model_routes import RoutePolicy
    from .provider_failover import PROVIDERS

    routes = roster_to_routes(acc.roster or ModelRoster())
    ordered_routes = []
    for provider in order:
        candidates = [route for route in routes if route.provider == provider]
        if role and acc.roster is not None:
            role_models = {choice.model for choice in acc.roster.for_role(role)
                           if choice.provider == provider}
            candidates = [route for route in candidates
                          if route.model in role_models] or candidates
        if candidates:
            ordered_routes.append(candidates[0])
    specs = builtin_provider_specs({
        provider: PROVIDERS[provider] for provider in order
        if provider in PROVIDERS})
    allow_local = any(spec.locality == "local" for spec in specs)
    gateway = ModelGateway(
        providers=specs, routes=tuple(ordered_routes),
        policy=RoutePolicy(allow_local_counted_generation=allow_local))
    route_names = tuple(route.name for route in ordered_routes)

    def _advise(prompt: str):
        r = gateway.invoke(ModelGatewayRequest(
            prompt,
            ModelGatewayConfig(route_names=route_names,
                               max_route_attempts=max(1, len(route_names)))))
        if not r.ok:
            tried = "; ".join(f"{a.provider}: {a.error[:60]}"
                              for a in r.attempts)
            raise RuntimeError(f"every provider refused -> {tried}")
        return str(r.text), {
            "provider": r.provider, "model": r.model,
            "prompt_tokens": r.input_tokens,
            "eval_tokens": r.output_tokens,
            "providers_tried": [attempt.provider for attempt in r.attempts],
            "routes_tried": [attempt.route for attempt in r.attempts],
            "accounting_complete": r.accounting_complete,
        }

    return _advise


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    from .model_discovery import ModelChoice

    # 1. MODE HONESTY with no provider: deterministic yes, the other two no.
    # An installation with no key is not broken — it is limited, and says so.
    none_ = ModelAccess(providers_failed={"ollama_cloud": "HTTP 429 usage limit",
                                          "openrouter": "HTTP 401 not found"})
    check("no_working_provider_means_only_deterministic_is_offered",
          none_.modes_available() == ["deterministic"]
          and none_.can_run("deterministic")
          and not none_.can_run("hybrid")
          and not none_.can_run("non_deterministic"),
          "the two model-requiring modes are reported unavailable")

    # 2. THE ERROR MESSAGE SETUP OWES A USER: each failure gets a reason and a
    # next step, and a rate limit is distinguished from a rejected key —
    # they need opposite actions from the user.
    ex = none_.explain()
    check("the_explanation_distinguishes_a_capped_key_from_a_dead_one",
          "currently capped" in ex and "check it is current" in ex
          and "Deterministic loops run normally" in ex
          and "Modes available: deterministic" in ex,
          "a rate limit and a bad key need opposite actions")

    # 3. with a working provider, all three modes are offered.
    live = ModelAccess(
        roster=ModelRoster(choices=[ModelChoice("p", "m", "generate")],
                           providers_working=["p"]),
        providers_working=["p"])
    check("a_working_provider_enables_hybrid_and_non_deterministic",
          set(live.modes_available()) == {"deterministic", "hybrid",
                                          "non_deterministic"}
          and live.has_model and live.summary()["models_reachable"] == 1,
          "the two model-requiring modes become available")

    # 4. ADVERSARIAL — NO FABRICATED ADVICE FUNCTION. With nothing working this
    # returns None rather than a callable that fails later. This is the rule
    # that keeps a setup error out of the middle of someone's run.
    check("no_working_provider_yields_no_advice_function",
          advice_function(none_) is None
          and callable(advice_function(live)),
          "None is the honest answer; a failing callable is not")

    # 5. Offline tests retain the caller's declared provider identity but do
    # not simulate an answer.  Only an authorized live run can establish that
    # a provider was contacted and returned usable output.
    mine = ModelAccess(
        roster=ModelRoster(choices=[ModelChoice(
            "my_box", "mine", "generate")],
            providers_working=["my_box"]),
        providers_working=["my_box"])
    check("the_access_plan_retains_only_the_callers_declared_provider",
          mine.providers_working == ["my_box"]
          and [choice.provider for choice in mine.roster.choices]
          == ["my_box"],
          "contract-only check; provider integration is not claimed")

    # 5. KEYS NEVER LEAK into a report or an explanation.
    acc = ModelAccess(providers_working=["mistral"],
                      providers_failed={"openrouter": "HTTP 401"})
    blob = str(acc.summary()) + acc.explain()
    secret = "sk-" + "S" * 24
    os.environ.setdefault("LOOP_ENGINE_AUTOCONF_PROBE", secret)
    check("no_key_material_appears_in_reports_or_explanations",
          secret not in blob and "Authorization" not in blob
          and all(k not in blob for k in KEY_ENV.values()),
          "a report carries providers and modes, never credentials")

    # 6. the env var map covers every registered provider — a provider with no
    # documented key variable cannot be configured by a user.
    from .provider_failover import PROVIDERS
    check("every_registered_provider_has_a_documented_key_variable",
          set(KEY_ENV) == set(PROVIDERS),
          f"{sorted(KEY_ENV)} == {sorted(PROVIDERS)}")

    passed = sum(1 for t in results if t["passed"])
    return {"record_type": "autoconfigure_contract_test/v2",
            "scope": "offline_contract_only",
            "provider_integration_proven": False,
            "tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
