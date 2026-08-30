"""OpenRouter client — the second sanctioned hosted model surface.

Architectural role: static architecture (a model provider adapter).

Why this module exists, concretely: on 2026-08-24 the Ollama Cloud key hit its
session usage limit mid-campaign and every model-backed arm stopped. A single
provider is a single point of failure for the only thing the loop cannot do
without — a semantic call. Provider plurality is not a convenience feature; it
is what keeps a measurement campaign running when one vendor says 429.

OpenRouter is an aggregating gateway: one key, one OpenAI-compatible endpoint,
many upstream models. That makes it a good failover peer AND a good breadth
surface — the same route registry can reach models no single vendor offers.

This mirrors ``ollama_client`` deliberately, down to returning the SAME
``ChatResult``. A caller must not need to know which provider answered; only
the record needs to know, and it records it. The two clients differ in wire
format and nothing else that a loop can observe.

Owns:
    - chat() / chat_maxout(): one call to OpenRouter's /chat/completions,
      returning text plus PROVIDER-REPORTED token counts;
    - load_api_key() / live_models(): key resolution and the live catalog;
    - verify(): a real call, because a key is verified by USE, never by status.

Does not own:
    - which provider a run SHOULD use (model_routes owns routes and policy),
      failover order (provider_failover), or any loop semantics.

Key invariants:
    - forbidden models are refused here too — a second provider must not
      become a way around a model ban;
    - never raises: a failure returns ok=False with the reason, so a resolver
      falls back rather than crashing the loop;
    - token counts are provider-reported or absent — never estimated, because
      an estimated count is inadmissible as evidence;
    - cloud locality, so counted generation is permitted by the cloud-only rule.

Verification: self_test() covers offline contracts and refusals only.  Real
provider integration uses a separately authorized live verification path.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .ollama_client import ChatResult, FORBIDDEN_MODELS
from .model_capabilities import (
    ModelOutputCapability, ModelOutputLimitMismatch,
    UnknownModelOutputLimit, require_declared_maximum,
)

API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS_URL = "https://openrouter.ai/api/v1/models"

#: A reasonable default. OpenRouter names models ``vendor/model``.
DEFAULT_MODEL = "deepseek/deepseek-chat"

# OpenRouter publishes ``top_provider.max_completion_tokens`` in its live
# Models API.  A static copy drifts as aliases and upstream routing change, so
# generation resolves this field from the provider catalog at call time.
MODEL_OUTPUT_CAPABILITIES = {}
MODEL_MAX_OUTPUT = {}


def output_capability_for(model: str) -> ModelOutputCapability:
    for row in catalog():
        if str(row.get("id", "")) != model:
            continue
        maximum = (row.get("top_provider") or {}).get(
            "max_completion_tokens")
        if isinstance(maximum, int) and maximum > 0:
            return ModelOutputCapability(
                maximum,
                "OpenRouter Models API top_provider.max_completion_tokens",
                endpoint=API_URL,
                observed_at=datetime.now(timezone.utc).isoformat())
        break
    raise UnknownModelOutputLimit(
        "unknown_model_output_limit: OpenRouter Models API did not declare "
        f"top_provider.max_completion_tokens for {model!r}")


def max_output_for(model: str) -> int:
    """Compatibility accessor with no invented fallback."""
    return output_capability_for(model).maximum_output_tokens


def _forbidden(model: str) -> bool:
    """A model ban is a policy fact, not a provider fact — it must hold on
    EVERY provider, or a second provider becomes a way around the ban."""
    base = model.split("/")[-1].split(":")[0]
    return any(f in model or f in base for f in FORBIDDEN_MODELS)


def load_api_key(env_path: "str | Path | None" = None) -> "str | None":
    """OPENROUTER_API_KEY from the environment, else from .env."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key.strip()
    p = Path(env_path) if env_path else Path(__file__).resolve()
    if not env_path:
        for parent in p.parents:
            cand = parent / ".env"
            if cand.exists():
                p = cand
                break
        else:
            return None
    try:
        for line in Path(p).read_text().splitlines():
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        return None
    return None


def catalog(api_key: "str | None" = None) -> list:
    """The full catalog rows — id, pricing, context, declared capabilities.

    This lives HERE rather than in the discovery layer because HTTP belongs to
    a provider adapter: discovery classifies what an adapter fetches, and does
    not open sockets of its own.

    OpenRouter serves this without a key, so a caller can inspect what a
    provider OFFERS before holding a credential — which is not the same as
    proving anything is reachable."""
    key = api_key if api_key is not None else load_api_key()
    req = urllib.request.Request(
        MODELS_URL, headers={"Authorization": f"Bearer {key}"} if key else {})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return list(json.loads(r.read()).get("data", []))
    except (urllib.error.URLError, OSError, ValueError):
        return []


def live_models(api_key: "str | None" = None) -> list:
    """The provider's live catalog as bare names — negotiated, never assumed."""
    return sorted(m.get("id", "") for m in catalog(api_key))


def zero_cost_models(rows: "list | None" = None) -> list[dict]:
    """Return current free, structured models with declared output limits."""
    choices = []
    for row in catalog() if rows is None else rows:
        if not isinstance(row, dict) or _forbidden(str(row.get("id", ""))):
            continue
        pricing = row.get("pricing") or {}
        maximum = (row.get("top_provider") or {}).get(
            "max_completion_tokens")
        parameters = row.get("supported_parameters") or ()
        try:
            zero_cost = (float(pricing.get("prompt") or 0) == 0
                         and float(pricing.get("completion") or 0) == 0)
        except (TypeError, ValueError):
            zero_cost = False
        if (not row.get("id") or not zero_cost
                or not isinstance(maximum, int) or maximum < 1
                or not ({"structured_outputs", "response_format"}
                        & set(parameters))):
            continue
        choices.append(row)
    return sorted(
        choices,
        key=lambda row: (-int((row.get("top_provider") or {}).get(
                                  "max_completion_tokens") or 0),
                         -int(row.get("context_length") or 0),
                         str(row.get("id"))))


def select_zero_cost_model(rows: "list | None" = None) -> str:
    """Select a free model from live declared facts, not a frozen name."""
    choices = zero_cost_models(rows)
    if not choices:
        raise UnknownModelOutputLimit(
            "OpenRouter has no current zero-cost structured model with a "
            "declared maximum output")
    return str(choices[0]["id"])


def chat(prompt: str, *, model: str = DEFAULT_MODEL, system: str = "",
         max_tokens: "int | None" = None, temperature: float = 0.7,
         timeout: float = 90.0, api_key: "str | None" = None,
         output_capability: "ModelOutputCapability | None" = None) -> ChatResult:
    """One OpenRouter chat call. Never raises — a failure returns ok=False with
    the reason, so a resolver can fall back rather than crash the loop."""
    if _forbidden(model):
        return ChatResult(text="", model=model, ok=False,
                          error=f"model {model!r} is forbidden by policy on "
                                "every provider")
    key = api_key if api_key is not None else load_api_key()
    if not key:
        return ChatResult(text="", model=model, ok=False,
                          error="no OPENROUTER_API_KEY in environment or .env")
    try:
        capability = output_capability or output_capability_for(model)
        maximum = require_declared_maximum(max_tokens, capability)
    except (UnknownModelOutputLimit, ModelOutputLimitMismatch) as exc:
        return ChatResult(text="", model=model, ok=False, error=str(exc))
    messages = ([{"role": "system", "content": system}] if system else []) \
        + [{"role": "user", "content": prompt}]
    payload = {"model": model, "messages": messages,
               "max_tokens": maximum, "temperature": temperature,
               # ask the gateway for native upstream usage rather than its
               # own estimate — an estimated count is not admissible evidence
               "usage": {"include": True}}
    req = urllib.request.Request(
        API_URL, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 # OpenRouter attributes traffic by these; harmless if unset
                 "HTTP-Referer": "https://github.com/alisonjieli-png/loop-engine",
                 "X-Title": "Loop Engine"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read()[:300].decode("utf-8", "replace")
        except OSError:
            pass
        return ChatResult(text="", model=model, ok=False,
                          error=f"HTTP {e.code}: {detail}")
    except (urllib.error.URLError, OSError, ValueError) as e:
        return ChatResult(text="", model=model, ok=False, error=str(e)[:300])

    choices = body.get("choices") or []
    text = (choices[0].get("message", {}).get("content", "")
            if choices else "")
    usage = body.get("usage") or {}
    return ChatResult(
        text=str(text), model=str(body.get("model", model)),
        # provider-reported ONLY; a missing count stays 0 rather than estimated
        prompt_tokens=int(usage.get("prompt_tokens", 0)),
        eval_tokens=int(usage.get("completion_tokens", 0)),
        ok=bool(text), num_predict_used=maximum,
        error="" if text else "provider returned no text")


def chat_maxout(prompt: str, *, model: str = DEFAULT_MODEL, system: str = "",
                temperature: float = 0.7, timeout: float = 900.0,
                api_key: "str | None" = None, backoff: float = 0.9,
                floor_frac: float = 0.3, max_attempts: int = 1,
                max_output_tokens: "int | None" = None,
                output_capability: "ModelOutputCapability | None" = None
                ) -> ChatResult:
    """Make one call at the source-backed model maximum."""
    del backoff, floor_frac
    if max_attempts != 1:
        return ChatResult(
            "", model, ok=False,
            error="physical model retries require an explicit outer call budget")
    return chat(
        prompt, model=model, system=system, max_tokens=max_output_tokens,
        temperature=temperature, timeout=timeout, api_key=api_key,
        output_capability=output_capability)


def verify(model: str = DEFAULT_MODEL) -> dict:
    """Verify the credential BY USE — a real call, never a status field."""
    r = chat("Reply with one word: READY", model=model, timeout=60)
    return {"provider": "openrouter", "model": r.model, "ok": r.ok,
            "prompt_tokens": r.prompt_tokens, "eval_tokens": r.eval_tokens,
            "error": r.error[:200], "text": r.text[:80]}


def self_test() -> dict:
    """Offline contract and refusal tests.  No provider is contacted."""
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    # 1. A missing key is reported, never crashed on. api_key="" means "no key"
    # explicitly, so this path is testable without touching the environment.
    r = chat("hi", api_key="")
    check("a_missing_key_returns_a_reason_not_an_exception",
          r.ok is False and "OPENROUTER_API_KEY" in r.error
          and r.prompt_tokens == 0,
          "a resolver can fall back; nothing raises")

    # 2. THE POLICY RULE: a forbidden model is refused on THIS provider too.
    # A second provider must not become a route around a model ban.
    # The banned name is READ from the policy list rather than written here, so
    # this test covers whatever is currently forbidden, not one hard-coded name.
    bad = chat("hi", model=f"vendor/{FORBIDDEN_MODELS[0]}", api_key="x")
    check("forbidden_models_are_refused_on_every_provider",
          bad.ok is False and "forbidden" in bad.error
          and all(_forbidden(f"vendor/{f}") for f in FORBIDDEN_MODELS),
          "a model ban is a policy fact, not a provider fact")

    # 3. Same ChatResult contract as the Ollama surface — this is what lets a
    # failover swap providers without any caller noticing.
    check("returns_the_same_result_contract_as_the_other_provider",
          isinstance(r, ChatResult) and hasattr(r, "total_tokens")
          and r.to_dict()["total_tokens"] == 0,
          "identical shape means failover is invisible to callers")

    # 4. Unknown stays unknown.  No fallback number can silently truncate or
    # produce a provider rejection.
    check("no_static_default_can_replace_live_catalog_capability_discovery",
          not MODEL_OUTPUT_CAPABILITIES and not MODEL_MAX_OUTPUT,
          "the provider catalog supplies max_completion_tokens at call time")

    free_rows = [
        {"id": "vendor/free-small", "pricing": {"prompt": "0",
         "completion": "0"}, "context_length": 100,
         "top_provider": {"max_completion_tokens": 40},
         "supported_parameters": ["structured_outputs"]},
        {"id": "vendor/free-wide", "pricing": {"prompt": "0",
         "completion": "0"}, "context_length": 200,
         "top_provider": {"max_completion_tokens": 80},
         "supported_parameters": ["response_format"]},
        {"id": "vendor/paid", "pricing": {"prompt": "1",
         "completion": "2"}, "context_length": 300,
         "top_provider": {"max_completion_tokens": 120},
         "supported_parameters": ["structured_outputs"]},
    ]
    check("zero_cost_selection_uses_live_price_contract_and_capacity",
          select_zero_cost_model(free_rows) == "vendor/free-wide"
          and [row["id"] for row in zero_cost_models(free_rows)]
              == ["vendor/free-wide", "vendor/free-small"],
          "paid rows and rows without a declared structured output are absent")

    passed = sum(1 for t in results if t["passed"])
    return {"record_type": "openrouter_client_contract_test/v2",
            "scope": "offline_contract_only",
            "provider_integration_proven": False,
            "tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
