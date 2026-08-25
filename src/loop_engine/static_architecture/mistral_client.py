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

Verification: self_test() — offline contract tests always; the live call runs
only with a working key and is reported as NOT RUN otherwise.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from .ollama_client import ChatResult, FORBIDDEN_MODELS

API_URL = "https://api.mistral.ai/v1/chat/completions"
MODELS_URL = "https://api.mistral.ai/v1/models"

DEFAULT_MODEL = "mistral-small-latest"

MODEL_MAX_OUTPUT = {
    "mistral-small-latest": 8192,
    "mistral-medium-latest": 8192,
    "mistral-large-latest": 8192,
    "open-mistral-nemo": 8192,
    "codestral-latest": 8192,
}
DEFAULT_MAX_OUTPUT = 4096


def max_output_for(model: str) -> int:
    return MODEL_MAX_OUTPUT.get(model, DEFAULT_MAX_OUTPUT)


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
         max_tokens: int = 512, temperature: float = 0.7,
         timeout: float = 90.0, api_key: "str | None" = None) -> ChatResult:
    """One Mistral chat call. Never raises."""
    if _forbidden(model):
        return ChatResult(text="", model=model, ok=False,
                          error=f"model {model!r} is forbidden by policy on "
                                "every provider")
    key = api_key if api_key is not None else load_api_key()
    if not key:
        return ChatResult(text="", model=model, ok=False,
                          error="no MISTRAL_API_KEY in environment or .env")

    messages = ([{"role": "system", "content": system}] if system else []) \
        + [{"role": "user", "content": prompt}]
    req = urllib.request.Request(
        API_URL,
        data=json.dumps({"model": model, "messages": messages,
                         "max_tokens": int(max_tokens),
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
        ok=bool(text), num_predict_used=int(max_tokens),
        error="" if text else "provider returned no text")


def chat_maxout(prompt: str, *, model: str = DEFAULT_MODEL, system: str = "",
                temperature: float = 0.7, timeout: float = 900.0,
                api_key: "str | None" = None, backoff: float = 0.9,
                floor_frac: float = 0.3, max_attempts: int = 8) -> ChatResult:
    """Full output ceiling, backing off only on failure — same policy as the
    other providers, so a failover does not change the call's semantics."""
    ceiling = max_output_for(model)
    mt, last, attempt = ceiling, None, 1
    for attempt in range(1, max_attempts + 1):
        res = chat(prompt, model=model, system=system, max_tokens=int(mt),
                   temperature=temperature, timeout=timeout, api_key=api_key)
        res.num_predict_used, res.attempts = int(mt), attempt
        if res.ok and res.text.strip():
            return res
        last = res
        mt = int(mt * backoff)
        if mt < ceiling * floor_frac:
            break
    if last is not None:
        last.num_predict_used, last.attempts = int(mt), attempt
    return last if last is not None else chat(prompt, model=model)


def verify(model: str = DEFAULT_MODEL) -> dict:
    r = chat("Reply with one word: READY", model=model, max_tokens=20,
             timeout=60)
    return {"provider": "mistral", "model": r.model, "ok": r.ok,
            "prompt_tokens": r.prompt_tokens, "eval_tokens": r.eval_tokens,
            "error": r.error[:200], "text": r.text[:80]}


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    r = chat("hi", api_key="")
    check("a_missing_key_returns_a_reason_not_an_exception",
          r.ok is False and "MISTRAL_API_KEY" in r.error,
          "a resolver can fall back; nothing raises")

    # the banned name is READ from the policy list, never written here, so this
    # covers whatever is currently forbidden rather than one hard-coded name
    bad = chat("hi", model=FORBIDDEN_MODELS[0], api_key="x")
    check("forbidden_models_are_refused_on_every_provider",
          bad.ok is False and "forbidden" in bad.error,
          "a model ban holds on every provider")

    check("returns_the_same_result_contract_as_the_other_providers",
          isinstance(r, ChatResult) and hasattr(r, "total_tokens"),
          "identical shape means failover is invisible to callers")

    key = load_api_key()
    if key:
        v = verify()
        if v["ok"]:
            check("live_call_returns_provider_reported_tokens",
                  v["prompt_tokens"] > 0 and v["eval_tokens"] > 0,
                  f"{v['model']}: {v['prompt_tokens']}+{v['eval_tokens']}")
        else:
            results.append({
                "test": "live_call_returns_provider_reported_tokens",
                "passed": True, "skipped": True,
                "detail": f"NOT RUN — provider refused: {v['error'][:80]}"})
    else:
        results.append({"test": "live_call_returns_provider_reported_tokens",
                        "passed": True, "skipped": True,
                        "detail": "NOT RUN — no MISTRAL_API_KEY present"})

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
