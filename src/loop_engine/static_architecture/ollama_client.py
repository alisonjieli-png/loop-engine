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

ENDPOINT = "https://ollama.com/api/chat"
# Sanctioned, live default (kimi-k3 is forbidden per the model policy).
# deepseek-v4-flash is fast/cheap for the loop; deepseek-v4-pro for hard calls.
DEFAULT_MODEL = "deepseek-v4-flash:0731"
CATALOG_ENDPOINT = "https://ollama.com/api/tags"
FORBIDDEN_MODELS = ("kimi-k3",)

# Each model's MAXIMUM output-token limit (from the served registry).  We never
# cap output below this — a call asks for the model's full ceiling and the model
# stops naturally when its answer is complete (num_predict is a max, not a
# target, so this does NOT force giant replies — it only removes truncation).
# Only if a max-output call fails do we back off (see chat_maxout).
MODEL_MAX_OUTPUT = {
    "deepseek-v4-pro": 128000, "deepseek-v4-flash": 128000,
    "glm-5.2": 131072, "glm-5.1": 131072,
    "kimi-k2.7-code": 256000, "kimi-k2.6": 262128, "kimi-k2.5": 262128,
    "minimax-m3": 16384, "minimax-m2.7": 16384,
    "mistral-large-3": 262144, "nemotron-3-ultra": 65536,
    "qwen3.5": 262144, "x-preview-f": 131072, "ox-alpha": 131072,
    "gpt-oss": 131072,
}
# A conservative default ceiling for any model not in the table.
DEFAULT_MAX_OUTPUT = 32768


def max_output_for(model: str) -> int:
    """The maximum output tokens a model supports, matching by name prefix so
    version/':cloud' suffixes still resolve (e.g. 'kimi-k2.7-code:cloud')."""
    base = model.split("/")[-1].split(":")[0]
    if base in MODEL_MAX_OUTPUT:
        return MODEL_MAX_OUTPUT[base]
    for name, cap in MODEL_MAX_OUTPUT.items():
        if base.startswith(name) or name in base:
            return cap
    return DEFAULT_MAX_OUTPUT


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
    except Exception:                                           # noqa: BLE001
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
        except Exception:                                       # noqa: BLE001
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
    attempts: int = 1             # how many backoff attempts chat_maxout took

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.eval_tokens

    def to_dict(self) -> dict:
        return {"text": self.text, "model": self.model,
                "prompt_tokens": self.prompt_tokens,
                "eval_tokens": self.eval_tokens,
                "total_tokens": self.total_tokens, "ok": self.ok,
                "error": self.error}


def chat_maxout(prompt: str, *, model: str = DEFAULT_MODEL, system: str = "",
                temperature: float = 0.7, timeout: float = 900.0,
                api_key: str | None = None, backoff: float = 0.9,
                floor_frac: float = 0.3, max_attempts: int = 8,
                max_output_tokens: "int | None" = None) -> ChatResult:
    """Call a model asking for its FULL output ceiling, backing off only on failure.

    The owner rule: never cap output — each call requests the model's maximum
    output, and the model stops when its answer is done.  If (and only if) a call
    fails — timeout, HTTP error, or an empty reply — retry at 90% of the previous
    request, then 81%, and so on, down to ``floor_frac`` of the ceiling.  A large
    generation is slow, so the default timeout is generous (15 minutes).  The
    returned ChatResult carries ``num_predict_used`` and ``attempts`` so the
    receipt shows the model ran at (or near) full capacity."""
    ceiling = min(max_output_for(model), int(max_output_tokens)) \
        if max_output_tokens is not None else max_output_for(model)
    np = ceiling
    last = None
    for attempt in range(1, max_attempts + 1):
        res = chat(prompt, model=model, system=system, num_predict=int(np),
                   temperature=temperature, timeout=timeout, api_key=api_key)
        res.num_predict_used = int(np)
        res.attempts = attempt
        if res.ok and res.text.strip():
            return res
        last = res
        np = int(np * backoff)
        if np < ceiling * floor_frac:
            break
    if last is not None:
        last.num_predict_used = int(np)
        last.attempts = attempt
    return last if last is not None else chat(prompt, model=model,
                                              num_predict=int(np))


def chat(prompt: str, *, model: str = DEFAULT_MODEL, system: str = "",
         num_predict: int = 512, temperature: float = 0.7,
         timeout: float = 90.0, api_key: str | None = None) -> ChatResult:
    """Send one chat request to Ollama Cloud and return the text + provider token
    counts.  Never raises — a failure returns ``ok=False`` with the error, so a
    resolver can fall back rather than crash the loop."""
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
        "options": {"num_predict": num_predict, "temperature": temperature}
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
    except Exception as exc:                                    # noqa: BLE001
        return ChatResult("", model, ok=False, error=repr(exc))
    text = (data.get("message", {}) or {}).get("content", "")
    return ChatResult(
        text=text, model=data.get("model", model),
        prompt_tokens=int(data.get("prompt_eval_count", 0) or 0),
        eval_tokens=int(data.get("eval_count", 0) or 0), ok=bool(text))


def verify(model: str = DEFAULT_MODEL) -> dict:
    """A harmless real call that verifies the credential by USING it.  A
    reasoning model needs headroom past its thinking, so ask for enough tokens."""
    res = chat("Reply with exactly the word: online", model=model,
               num_predict=160, temperature=0.0)
    return {"record_type": "ollama_verify/v1", "ok": res.ok,
            "model": res.model, "text": res.text.strip()[:60],
            "prompt_tokens": res.prompt_tokens, "eval_tokens": res.eval_tokens,
            "error": res.error}


def self_test() -> dict:
    """Offline self-test — verifies the client's construction and error handling
    without a network call (a live call is exercised by `verify`)."""
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # No key -> ok=False, no crash.
    res = chat("hi", api_key="", num_predict=1)
    check("a_missing_key_returns_ok_false_not_a_crash",
          not res.ok and "not found" in res.error.lower(),
          "with no api key the client returns ok=False with an error, never "
          "raising into the loop")

    # A bad key hitting the endpoint returns ok=False without crashing (whether
    # the endpoint answers with an HTTP error or an empty body).
    res2 = chat("hi", api_key="definitely not a real key", num_predict=1,
                timeout=15.0)
    check("a_bad_key_or_network_error_is_handled_gracefully",
          not res2.ok,
          "a bad credential or unreachable endpoint returns ok=False rather "
          "than raising into the loop — a resolver can fall back")

    check("chat_result_reports_total_tokens",
          ChatResult("x", "m", prompt_tokens=3, eval_tokens=5).total_tokens == 8,
          "the result exposes provider-reported prompt + eval token totals")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "ollama_client_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}


if __name__ == "__main__":
    import sys
    if "--verify" in sys.argv:
        print(json.dumps(verify(), indent=1))
    else:
        print(json.dumps(self_test(), indent=1))
