"""Ollama Cloud client — the sanctioned hosted model surface for the loop.

Per the repository model policy (cloud-only), every generation call goes to a
hosted endpoint.  This is a minimal, dependency-free client for Ollama Cloud's
native ``/api/chat`` (``OLLAMA_API_KEY`` from ``.env``), returning the model's
text and the PROVIDER-REPORTED token counts — the only counts admissible as
evidence.  It is deliberately small: one chat call, real usage, no retries baked
in beyond a single attempt, so a caller (a resolver) decides policy.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .model_capabilities import (
    ModelOutputCapability, ModelOutputLimitMismatch,
    UnknownModelOutputLimit, require_declared_maximum,
    resolve_output_capability,
)

ENDPOINT = "https://ollama.com/api/chat"
# Sanctioned, live default (kimi-k3 is forbidden per the model policy).
# deepseek-v4-flash is fast/cheap for the loop; deepseek-v4-pro for hard calls.
DEFAULT_MODEL = "deepseek-v4-flash:0731"
CATALOG_ENDPOINT = "https://ollama.com/api/tags"
FORBIDDEN_MODELS = ("kimi-k3",)
OUTPUT_LIMIT_STOP_REASONS = frozenset((
    "length", "max_tokens", "max_output_tokens", "output_limit",
    "token_limit",
))

# Each model's MAXIMUM output-token limit (from the served registry).  We never
# cap output below this — a call asks for the model's full ceiling and the model
# stops naturally when its answer is complete (num_predict is a max, not a
# target, so this does NOT force giant replies — it only removes truncation).
# Only if a max-output call fails do we back off (see chat_maxout).
# On 2026-08-25 Ollama's
# OpenAI-compatible endpoint rejected 128000 for this exact identifier and
# reported 65536 as the maximum.  Native acceptance of a larger number was not
# treated as proof because a server may silently clamp it.
MODEL_OUTPUT_CAPABILITIES = {
    "deepseek-v4-flash:0731": ModelOutputCapability(
        65536,
        "Ollama HTTP 400 response declared the exact model maximum",
        observed_at="2026-08-25"),
    "deepseek-v4-pro:0813": ModelOutputCapability(
        65536,
        "Ollama HTTP 400 response declared the exact model maximum",
        observed_at="2026-08-31"),
    "glm-5.3-flash": ModelOutputCapability(
        1048576,
        "Ollama HTTP 400 response declared the exact model maximum",
        observed_at="2026-08-31"),
}
# Compatibility projection for read-only catalog consumers.  It has no default.
MODEL_MAX_OUTPUT = {
    name: capability.maximum_output_tokens
    for name, capability in MODEL_OUTPUT_CAPABILITIES.items()
}


def output_capability_for(model: str) -> ModelOutputCapability:
    """Return the source-backed output maximum or fail closed."""
    return resolve_output_capability(
        "ollama_cloud", model, ENDPOINT, MODEL_OUTPUT_CAPABILITIES)


def max_output_for(model: str) -> int:
    """Compatibility accessor with no invented fallback."""
    return output_capability_for(model).maximum_output_tokens


def live_models(api_key: str | None = None) -> list[str]:
    """The currently-served Ollama Cloud models, minus any forbidden by policy."""
    key = api_key or load_api_key()
    if not key:
        return []
    req = urllib.request.Request(
        CATALOG_ENDPOINT, headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return []
    names = [m.get("name") or m.get("model") for m in data.get("models", ())]
    return [n for n in names if n and not any(
        n.startswith(f) for f in FORBIDDEN_MODELS)]


def load_api_key(env_path: str | Path | None = None) -> str | None:
    """Read OLLAMA_API_KEY from the environment or the repo .env."""
    key = os.environ.get("OLLAMA_API_KEY")
    if key:
        return key.strip()
    # Walk up from this file to find a .env at the repo root.
    here = Path(__file__).resolve()
    candidates = [Path(env_path)] if env_path else [
        p / ".env" for p in here.parents[:8]]
    for cand in candidates:
        try:
            if cand.exists():
                for line in cand.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("OLLAMA_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            continue
    return None


@dataclass
class ChatResult:
    text: str
    model: str
    prompt_tokens: int = 0
    eval_tokens: int = 0
    ok: bool = True
    error: str = ""
    num_predict_used: int = 0      # the output ceiling this call actually ran at
    attempts: int = 1             # physical calls represented by this result
    response_received: bool = False
    done: "bool | None" = None
    done_reason: str = ""
    reasoning_present: bool = False
    output_limit_reached: bool = False

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.eval_tokens

    def to_dict(self) -> dict:
        return {"text": self.text, "model": self.model,
                "prompt_tokens": self.prompt_tokens,
                "eval_tokens": self.eval_tokens,
                "total_tokens": self.total_tokens, "ok": self.ok,
                "error": self.error,
                "response_received": self.response_received,
                "done": self.done, "done_reason": self.done_reason,
                "reasoning_present": self.reasoning_present,
                "output_limit_reached": self.output_limit_reached}


def response_reached_output_limit(
        done_reason: str, output_tokens: int, maximum_output_tokens: int
        ) -> bool:
    """Classify a provider stop without guessing when it declared ``stop``.

    Some compatible endpoints omit a stop reason. In that case, an output
    count equal to the exact requested maximum is the only available evidence
    that generation reached the ceiling. An explicit ordinary ``stop`` wins
    over that inference.
    """
    normalized = str(done_reason or "").strip().lower()
    if normalized:
        return normalized in OUTPUT_LIMIT_STOP_REASONS
    return bool(maximum_output_tokens > 0
                and output_tokens >= maximum_output_tokens)


def chat_maxout(prompt: str, *, model: str = DEFAULT_MODEL, system: str = "",
                temperature: float = 0.7, timeout: float = 900.0,
                api_key: str | None = None, backoff: float = 0.9,
                floor_frac: float = 0.3, max_attempts: int = 1,
                max_output_tokens: "int | None" = None,
                output_capability: "ModelOutputCapability | None" = None
                ) -> ChatResult:
    """Make one call at the source-backed model maximum.

    ``backoff`` and ``floor_frac`` remain accepted for call compatibility but
    never reduce the model ceiling.  Retry policy belongs above this physical
    call boundary and must retain its own authorization and call budget.
    """
    del backoff, floor_frac
    if max_attempts != 1:
        return ChatResult(
            "", model, ok=False,
            error="physical model retries require an explicit outer call budget")
    return chat(
        prompt, model=model, system=system,
        num_predict=max_output_tokens, temperature=temperature,
        timeout=timeout, api_key=api_key,
        output_capability=output_capability)


def chat(prompt: str, *, model: str = DEFAULT_MODEL, system: str = "",
         num_predict: "int | None" = None, temperature: float = 0.7,
         timeout: float = 90.0, api_key: str | None = None,
         output_capability: "ModelOutputCapability | None" = None) -> ChatResult:
    """Send one chat request to Ollama Cloud and return the text + provider token
    counts.  Never raises — a failure returns ``ok=False`` with the error, so a
    resolver can fall back rather than crash the loop."""
    try:
        capability = output_capability or output_capability_for(model)
        maximum = require_declared_maximum(num_predict, capability)
    except (UnknownModelOutputLimit, ModelOutputLimitMismatch) as exc:
        return ChatResult("", model, ok=False, error=str(exc))
    # An explicit api_key="" means "no key" (used to test fallback); only None
    # falls back to the environment / .env.
    key = load_api_key() if api_key is None else api_key
    if not key:
        return ChatResult("", model, ok=False,
                          error="OLLAMA_API_KEY not found")
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    body = json.dumps({
        "model": model, "messages": messages, "stream": False,
        "options": {"num_predict": maximum, "temperature": temperature}
    }).encode()
    req = urllib.request.Request(
        ENDPOINT, data=body, method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return ChatResult("", model, ok=False,
                          error=f"HTTP {exc.code}: {exc.read().decode()[:200]}")
    except Exception as exc:
        return ChatResult("", model, ok=False, error=repr(exc))
    message = data.get("message", {}) or {}
    text = message.get("content", "")
    reasoning_present = bool(str(message.get("thinking", "") or "").strip())
    done = data.get("done") if isinstance(data.get("done"), bool) else None
    done_reason = str(data.get("done_reason", "") or "")
    prompt_tokens = int(data.get("prompt_eval_count", 0) or 0)
    eval_tokens = int(data.get("eval_count", 0) or 0)
    output_limit_reached = response_reached_output_limit(
        done_reason, eval_tokens, maximum)
    error = ""
    if output_limit_reached:
        error = (
            "output_limit_reached: Ollama response reached the exact "
            f"{maximum}-token output ceiling; done_reason={done_reason!r}")
    elif done is False:
        error = "incomplete_response: non-streaming Ollama response was not done"
    elif not text and reasoning_present:
        error = (
            "output_validation_failed: Ollama returned reasoning but no "
            "final response content")
    elif not text:
        error = "empty_response: Ollama returned no final response content"
    return ChatResult(
        text=text, model=data.get("model", model),
        prompt_tokens=prompt_tokens, eval_tokens=eval_tokens,
        ok=bool(text) and not output_limit_reached and done is not False,
        error=error, num_predict_used=maximum, response_received=True,
        done=done, done_reason=done_reason,
        reasoning_present=reasoning_present,
        output_limit_reached=output_limit_reached)


def verify(model: str = DEFAULT_MODEL) -> dict:
    """A harmless real call that verifies the credential by USING it.  A
    reasoning model needs headroom past its thinking, so ask for enough tokens."""
    res = chat("Reply with exactly the word: online", model=model,
               temperature=0.0)
    return {"record_type": "ollama_verify/v1", "ok": res.ok,
            "model": res.model, "text": res.text.strip()[:60],
            "prompt_tokens": res.prompt_tokens, "eval_tokens": res.eval_tokens,
            "error": res.error}


def self_test() -> dict:
    """Offline contract and refusal tests.  No provider is contacted."""
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # No key -> ok=False, no crash.
    res = chat("hi", api_key="")
    check("a_missing_key_returns_ok_false_not_a_crash",
          not res.ok and "not found" in res.error.lower(),
          "with no api key the client returns ok=False with an error, never "
          "raising into the loop")

    unknown = chat("hi", model="unlisted-model", api_key="unused")
    check("an_unknown_model_maximum_refuses_before_network_use",
          not unknown.ok and "unknown_model_output_limit" in unknown.error)

    reduced = chat("hi", model=DEFAULT_MODEL, api_key="unused", num_predict=1)
    check("a_caller_cannot_replace_the_declared_maximum_with_a_small_cap",
          not reduced.ok and "not the declared model maximum" in reduced.error)

    check("the_exact_live_observation_overrides_the_stale_family_value",
          max_output_for(DEFAULT_MODEL) == 65536,
          "exact deepseek-v4-flash:0731 maximum is 65536")

    check("alternate_cloud_models_have_exact_observed_output_contracts",
          max_output_for("deepseek-v4-pro:0813") == 65536
          and max_output_for("glm-5.3-flash") == 1048576,
          "alternate routes remain unavailable until Ollama declares maxima")

    check("chat_result_reports_total_tokens",
          ChatResult("x", "m", prompt_tokens=3, eval_tokens=5).total_tokens == 8,
          "the result exposes provider-reported prompt + eval token totals")

    truncated = ChatResult(
        "partial", DEFAULT_MODEL, prompt_tokens=10, eval_tokens=65536,
        ok=False, error="output_limit_reached", num_predict_used=65536,
        response_received=True, done=True, done_reason="length",
        output_limit_reached=True)
    check("provider_completion_metadata_distinguishes_truncation",
          truncated.response_received and truncated.done
          and truncated.done_reason == "length"
          and truncated.output_limit_reached
          and response_reached_output_limit("length", 12, 65536)
          and not response_reached_output_limit("stop", 65536, 65536),
          "an explicit stop is complete; length is a typed output limit")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "ollama_client_contract_test/v2",
            "scope": "offline_contract_only",
            "provider_integration_proven": False, "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=1))
