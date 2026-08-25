"""Provider failover — one semantic call, several providers, honest attribution.

Architectural role: static architecture (the resolver above the provider
adapters).

The 2026-08-24 lesson, paid for in a stalled campaign: a single model provider
is a single point of failure for the only capability the loop cannot supply
itself. When Ollama Cloud returned 429 ("session usage limit"), every
model-backed arm stopped — not because the loop was wrong, but because one
vendor said no.

This module makes that a routing event instead of a stop. It tries providers in
a declared order and returns the first success, and it records WHICH provider
answered, because a token count with no provider attached is not evidence.

The rule that keeps it honest — and it is the whole reason this module is
small and boring:

    FAILOVER IS NOT FALLBACK TO SILENCE.

    If every provider refuses, this returns a failed result naming every
    attempt. It NEVER degrades to a deterministic answer and reports it as a
    model call. A model arm that never reached a model has no model result;
    that must be visible, not smoothed over.

Owns:
    - PROVIDERS: the adapter table (provider name -> module);
    - ProviderAttempt / FailoverResult: what was tried, what answered, the cost;
    - call_with_failover(): the ordered attempt itself;
    - available_providers(): which credentials actually work, verified by USE.

Does not own:
    - the adapters (ollama_client, openrouter_client, mistral_client), route
      policy (model_routes), or any loop semantics.

Key invariants:
    - the answering provider is always named in the result;
    - counts stay provider-reported and are attributed per provider;
    - total failure is a failure, never a silent deterministic substitution;
    - a forbidden model is refused before any provider is contacted.

Verification: self_test() — order is honoured, the first success wins, total
failure names every attempt, and the adversarial "quietly succeed with no
provider" path is refused.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import mistral_client, ollama_client, openrouter_client
from .ollama_client import FORBIDDEN_MODELS

#: The adapter table. Adding a provider is adding a row plus its module — the
#: call path reads this, and never branches on a provider name.
PROVIDERS = {
    "ollama_cloud": ollama_client,
    "mistral": mistral_client,
    "openrouter": openrouter_client,
}

#: Default order. Ollama first because its counts drive the existing campaign
#: receipts; Mistral second because it is verified live; OpenRouter last
#: because its key was dead when this was written (2026-08-24) — an order is a
#: measured preference, not a ranking of quality.
DEFAULT_ORDER = ("ollama_cloud", "mistral", "openrouter")


@dataclass(frozen=True)
class ProviderAttempt:
    """One provider's answer to one call — including the refusals, which are
    the part a receipt usually loses."""
    provider: str
    model: str
    ok: bool
    prompt_tokens: int = 0
    eval_tokens: int = 0
    error: str = ""

    def as_dict(self) -> dict:
        return {"provider": self.provider, "model": self.model, "ok": self.ok,
                "prompt_tokens": self.prompt_tokens,
                "eval_tokens": self.eval_tokens, "error": self.error[:200]}


@dataclass
class FailoverResult:
    """The answer plus the full attempt history."""
    text: str = ""
    provider: str = ""
    model: str = ""
    ok: bool = False
    prompt_tokens: int = 0
    eval_tokens: int = 0
    attempts: list = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.eval_tokens

    def as_dict(self) -> dict:
        return {"ok": self.ok, "provider": self.provider, "model": self.model,
                "prompt_tokens": self.prompt_tokens,
                "eval_tokens": self.eval_tokens,
                "total_tokens": self.total_tokens,
                "attempts": [a.as_dict() for a in self.attempts]}

    def usage_record(self) -> dict:
        """The shape a receipt stores: counts ALWAYS carry their provider."""
        return {"provider": self.provider, "model": self.model,
                "prompt_tokens": self.prompt_tokens,
                "eval_tokens": self.eval_tokens,
                "providers_tried": [a.provider for a in self.attempts]}


def call_with_failover(prompt: str, *, order=DEFAULT_ORDER, models=None,
                       system: str = "", timeout: float = 900.0,
                       maxout: bool = True, ledger=None,
                       loop_id: str = "provider.failover") -> FailoverResult:
    """Try providers in order; return the first success, naming who answered.

    ``models`` optionally maps provider -> model name; a provider not named
    uses its own default. Every attempt is recorded, successes and refusals
    alike, because "we tried three providers and the third worked" is a
    materially different receipt from "a model answered"."""
    models = models or {}
    res = FailoverResult()

    for name in order:
        mod = PROVIDERS.get(name)
        if mod is None:
            res.attempts.append(ProviderAttempt(
                provider=name, model="", ok=False,
                error=f"unknown provider {name!r}; have {sorted(PROVIDERS)}"))
            continue
        model = models.get(name, mod.DEFAULT_MODEL)
        # policy before contact: a banned model is never sent anywhere
        base = model.split("/")[-1].split(":")[0]
        if any(f in model or f in base for f in FORBIDDEN_MODELS):
            res.attempts.append(ProviderAttempt(
                provider=name, model=model, ok=False,
                error=f"model {model!r} is forbidden by policy"))
            continue

        fn = mod.chat_maxout if maxout else mod.chat
        r = fn(prompt, model=model, system=system, timeout=timeout)
        res.attempts.append(ProviderAttempt(
            provider=name, model=r.model, ok=bool(r.ok),
            prompt_tokens=r.prompt_tokens, eval_tokens=r.eval_tokens,
            error=r.error))
        if ledger is not None:
            # literal event kinds in both arms: a computed kind cannot have its
            # canonical family checked, so the conformance gate refuses one
            _u = {"model": r.model, "provider": name,
                  "prompt_tokens": r.prompt_tokens,
                  "eval_tokens": r.eval_tokens}
            if r.ok:
                ledger.record(loop_id=loop_id, event="model_led", **_u)
            else:
                ledger.record(loop_id=loop_id,
                              event="model_invocation_failed", **_u)
        if r.ok and str(r.text).strip():
            res.text, res.provider, res.model, res.ok = (
                str(r.text), name, r.model, True)
            res.prompt_tokens, res.eval_tokens = (r.prompt_tokens,
                                                  r.eval_tokens)
            return res

    # EVERY provider refused. This is a failure and stays one — the caller
    # must not be able to mistake it for an answer.
    return res


def available_providers(order=DEFAULT_ORDER) -> dict:
    """Which credentials actually WORK — verified by a real call, never by a
    status field or the presence of a key."""
    out = {}
    for name in order:
        mod = PROVIDERS.get(name)
        if mod is None:
            out[name] = {"ok": False, "error": "unknown provider"}
            continue
        try:
            out[name] = mod.verify()
        except (OSError, ValueError) as e:      # never let a probe crash a run
            out[name] = {"ok": False, "error": str(e)[:200]}
    return out


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    from ..loop.recursive_loop import LoopLedger
    from .ollama_client import ChatResult

    # A stub provider module: enough surface for the resolver, no network.
    class _Stub:
        DEFAULT_MODEL = "stub/model"

        def __init__(self, ok, text="answer", tokens=(7, 5)):
            self._ok, self._text, self._t = ok, text, tokens

        def chat_maxout(self, prompt, *, model="", system="", timeout=0):
            return ChatResult(text=self._text if self._ok else "", model=model,
                              prompt_tokens=self._t[0] if self._ok else 0,
                              eval_tokens=self._t[1] if self._ok else 0,
                              ok=self._ok,
                              error="" if self._ok else "stub refused")
        chat = chat_maxout

    saved = dict(PROVIDERS)
    try:
        PROVIDERS.clear()
        PROVIDERS.update({"first": _Stub(False), "second": _Stub(True),
                          "third": _Stub(True, "should not be reached")})

        lg = LoopLedger()
        r = call_with_failover("q", order=("first", "second", "third"),
                               ledger=lg)

        # 1. ORDER IS HONOURED and the FIRST SUCCESS WINS — the third provider
        # is never contacted, which is what makes an order meaningful.
        check("failover_tries_in_order_and_stops_at_the_first_success",
              r.ok and r.provider == "second" and r.text == "answer"
              and len(r.attempts) == 2
              and [a.provider for a in r.attempts] == ["first", "second"],
              "third provider never contacted")

        # 2. THE REFUSAL IS KEPT. A receipt that shows only the success hides
        # that a provider was down — exactly the fact worth knowing later.
        check("refusals_are_recorded_alongside_the_success",
              r.attempts[0].ok is False and "refused" in r.attempts[0].error
              and r.usage_record()["providers_tried"] == ["first", "second"]
              and r.usage_record()["provider"] == "second",
              "counts always carry the provider that produced them")

        # 3. the ledger sees both the failure and the success as model events
        evs = [(e.get("event"), e.get("provider")) for e in lg.events
               if e.get("event", "").startswith("model_")]
        check("both_the_failure_and_the_success_reach_the_ledger",
              ("model_invocation_failed", "first") in evs
              and ("model_led", "second") in evs,
              f"{len(evs)} model events recorded")

        # 4. ADVERSARIAL — TOTAL FAILURE STAYS A FAILURE. This is the rule the
        # module exists to enforce: no silent degradation to a non-model answer.
        PROVIDERS.update({"first": _Stub(False), "second": _Stub(False)})
        dead = call_with_failover("q", order=("first", "second"))
        check("total_failure_is_a_failure_naming_every_attempt",
              dead.ok is False and dead.text == "" and dead.provider == ""
              and len(dead.attempts) == 2
              and dead.total_tokens == 0,
              "a model arm that reached no model reports no model result")

        # 5. a forbidden model is refused BEFORE any provider is contacted, and
        # an unknown provider is a recorded refusal rather than a crash
        banned = call_with_failover(
            "q", order=("second",),
            models={"second": f"vendor/{FORBIDDEN_MODELS[0]}"})
        unknown = call_with_failover("q", order=("nope",))
        check("forbidden_models_and_unknown_providers_are_refused_safely",
              banned.ok is False
              and "forbidden" in banned.attempts[0].error
              and unknown.ok is False
              and "unknown provider" in unknown.attempts[0].error,
              "policy is checked before contact; nothing raises")
    finally:
        PROVIDERS.clear()
        PROVIDERS.update(saved)

    # 6. the real table is intact after the stub swap, and every adapter
    # exposes the contract the resolver depends on
    check("every_registered_adapter_exposes_the_resolver_contract",
          set(PROVIDERS) == {"ollama_cloud", "mistral", "openrouter"}
          and all(hasattr(m, "chat_maxout") and hasattr(m, "DEFAULT_MODEL")
                  and hasattr(m, "verify") for m in PROVIDERS.values()),
          f"{len(PROVIDERS)} providers: {sorted(PROVIDERS)}")

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
