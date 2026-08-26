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

Verification: self_test() covers data contracts and refusals that happen before
provider use.  Ordered live failover requires separately authorized provider
calls and is not claimed by the offline suite.
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
#: records; Mistral second because it is verified live; OpenRouter last
#: because its key was dead when this was written (2026-08-24) — an order is a
#: measured preference, not a ranking of quality.
DEFAULT_ORDER = ("ollama_cloud", "mistral", "openrouter")


@dataclass(frozen=True)
class ProviderAttempt:
    """One provider's answer to one call — including the refusals, which are
    the part a record usually loses."""
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
        """The report shape: counts always carry their provider."""
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
    materially different record from "a model answered"."""
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
    """Offline data-contract and pre-contact refusal checks only."""
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    unknown = call_with_failover("q", order=("not_configured",))
    check("an_unknown_provider_is_a_typed_refusal",
          not unknown.ok and len(unknown.attempts) == 1
          and "unknown provider" in unknown.attempts[0].error,
          "no provider boundary was invoked")

    banned = call_with_failover(
        "q", order=("ollama_cloud",),
        models={"ollama_cloud": f"vendor/{FORBIDDEN_MODELS[0]}"})
    check("a_forbidden_model_is_refused_before_provider_use",
          not banned.ok and len(banned.attempts) == 1
          and "forbidden" in banned.attempts[0].error
          and banned.attempts[0].prompt_tokens == 0
          and banned.attempts[0].eval_tokens == 0)

    failed = FailoverResult(attempts=[
        ProviderAttempt("ollama_cloud", "m1", False, error="rate limited"),
        ProviderAttempt("mistral", "m2", False, error="unavailable"),
    ])
    check("the_failure_result_preserves_every_declared_attempt",
          not failed.ok and failed.text == "" and failed.provider == ""
          and [item.provider for item in failed.attempts]
          == ["ollama_cloud", "mistral"])

    attributed = FailoverResult(
        text="answer", provider="mistral", model="mistral-small-latest",
        ok=True, prompt_tokens=7, eval_tokens=5,
        attempts=[ProviderAttempt(
            "mistral", "mistral-small-latest", True, 7, 5)])
    check("usage_data_keeps_provider_and_model_attribution",
          attributed.total_tokens == 12
          and attributed.usage_record()["provider"] == "mistral"
          and attributed.usage_record()["providers_tried"] == ["mistral"])

    check("every_registered_adapter_exposes_the_full_model_contract",
          set(PROVIDERS) == {"ollama_cloud", "mistral", "openrouter"}
          and all(
              hasattr(adapter, "chat_maxout")
              and hasattr(adapter, "DEFAULT_MODEL")
              and hasattr(adapter, "verify")
              and hasattr(adapter, "output_capability_for")
              for adapter in PROVIDERS.values()))

    passed = sum(1 for test in results if test["passed"])
    return {
        "record_type": "provider_failover_contract_test/v2",
        "scope": "offline_contract_only",
        "provider_integration_proven": False,
        "tests": results,
        "passed": passed,
        "total": len(results),
        "all_passed": passed == len(results),
    }
