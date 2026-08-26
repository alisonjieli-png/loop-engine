"""Mistral client — the third sanctioned hosted model surface.

Architectural role: static architecture (a model provider adapter).

Mistral is named in the repository model policy alongside Ollama Cloud as a
sanctioned hosted provider. It was already driving the nightly-savings lane;
this module gives the loop the same access through the same contract, so a
campaign can fail over to it rather than stop.

Verified by USE on 2026-08-24: ``mistral-small-latest`` returned HTTP 200 with
provider-reported counts (22 prompt + 3 completion on the probe) at a moment
when the Ollama Cloud key was returning 429. That is the entire argument for
provider plurality, demonstrated rather than asserted.

Mirrors ``ollama_client`` and ``openrouter_client``, returning the SAME
``ChatResult``: a caller must not need to know which provider answered.

Owns:
    - chat() / chat_maxout(): one Mistral call with provider-reported tokens;
    - load_api_key() / live_models() / verify().

Does not own:
    - route policy (model_routes), failover order (provider_failover), or any
      loop semantics.

Key invariants:
    - forbidden models are refused here too;
    - never raises — ok=False carries the reason;
    - token counts are provider-reported or absent, never estimated.

Verification: self_test() covers offline contracts and refusals only.  Real
provider integration uses the separately authorized live verification command.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from .ollama_client import ChatResult, FORBIDDEN_MODELS
from .model_capabilities import (
    ModelOutputCapability, ModelOutputLimitMismatch,
    UnknownModelOutputLimit, require_declared_maximum,
    resolve_output_capability,
)

API_URL = "https://api.mistral.ai/v1/chat/completions"
MODELS_URL = "https://api.mistral.ai/v1/models"

DEFAULT_MODEL = "mistral-small-latest"

# Mistral's public model schema declares maximum context length, not a
# separate maximum completion length.  The chat contract says prompt tokens
# plus max_tokens must fit inside that context.  Without exact prompt
# tokenization, a completion maximum cannot be derived safely, so the built-in
# table remains empty.  A settings profile may add an exact source-backed
# capability for the selected model.
MODEL_OUTPUT_CAPABILITIES = {}
MODEL_MAX_OUTPUT = {
    name: capability.maximum_output_tokens
    for name, capability in MODEL_OUTPUT_CAPABILITIES.items()
}


def output_capability_for(model: str) -> ModelOutputCapability:
    return resolve_output_capability(
        "mistral", model, API_URL, MODEL_OUTPUT_CAPABILITIES)


def max_output_for(model: str) -> int:
    """Compatibility accessor with no invented fallback."""
    return output_capability_for(model).maximum_output_tokens


def _forbidden(model: str) -> bool:
    base = model.split("/")[-1].split(":")[0]
    return any(f in model or f in base for f in FORBIDDEN_MODELS)


def load_api_key(env_path: "str | Path | None" = None) -> "str | None":
    key = os.environ.get("MISTRAL_API_KEY")
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
            if line.startswith("MISTRAL_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        return None
    return None


def live_models(api_key: "str | None" = None) -> list:
    key = api_key if api_key is not None else load_api_key()
    req = urllib.request.Request(
        MODELS_URL, headers={"Authorization": f"Bearer {key}"} if key else {})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read())
        return sorted(m.get("id", "") for m in body.get("data", []))
    except (urllib.error.URLError, OSError, ValueError):
        return []


def chat(prompt: str, *, model: str = DEFAULT_MODEL, system: str = "",
         max_tokens: "int | None" = None, temperature: float = 0.7,
         timeout: float = 90.0, api_key: "str | None" = None,
         output_capability: "ModelOutputCapability | None" = None) -> ChatResult:
    """One Mistral chat call. Never raises."""
    if _forbidden(model):
        return ChatResult(text="", model=model, ok=False,
                          error=f"model {model!r} is forbidden by policy on "
                                "every provider")
    try:
        capability = output_capability or output_capability_for(model)
        maximum = require_declared_maximum(max_tokens, capability)
    except (UnknownModelOutputLimit, ModelOutputLimitMismatch) as exc:
        return ChatResult(text="", model=model, ok=False, error=str(exc))
    key = api_key if api_key is not None else load_api_key()
    if not key:
        return ChatResult(text="", model=model, ok=False,
                          error="no MISTRAL_API_KEY in environment or .env")

    messages = ([{"role": "system", "content": system}] if system else []) \
        + [{"role": "user", "content": prompt}]
    req = urllib.request.Request(
        API_URL,
        data=json.dumps({"model": model, "messages": messages,
                         "max_tokens": maximum,
                         "temperature": temperature}).encode(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
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
    r = chat("Reply with one word: READY", model=model, timeout=60)
    return {"provider": "mistral", "model": r.model, "ok": r.ok,
            "prompt_tokens": r.prompt_tokens, "eval_tokens": r.eval_tokens,
            "error": r.error[:200], "text": r.text[:80]}


def self_test() -> dict:
    """Offline contract and refusal tests.  No provider is contacted."""
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    # the banned name is READ from the policy list, never written here, so this
    # covers whatever is currently forbidden rather than one hard-coded name
    bad = chat("hi", model=FORBIDDEN_MODELS[0], api_key="x")
    check("forbidden_models_are_refused_on_every_provider",
          bad.ok is False and "forbidden" in bad.error,
          "a model ban holds on every provider")

    unknown = chat("hi", model="unlisted-model", api_key="unused")
    check("an_unknown_model_maximum_refuses_before_network_use",
          not unknown.ok and "unknown_model_output_limit" in unknown.error)
    check("returns_the_same_result_contract_as_the_other_providers",
          isinstance(unknown, ChatResult) and hasattr(unknown, "total_tokens"),
          "identical failure shape lets a caller handle refusal consistently")
    default_unknown = chat("hi", model=DEFAULT_MODEL, api_key="unused")
    check("a_context_window_is_not_misreported_as_an_output_maximum",
          not default_unknown.ok
          and "unknown_model_output_limit" in default_unknown.error,
          "configure an exact source-backed maximum before Mistral generation")

    passed = sum(1 for t in results if t["passed"])
    return {"record_type": "mistral_client_contract_test/v2",
            "scope": "offline_contract_only",
            "provider_integration_proven": False,
            "tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
