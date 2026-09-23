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
from .run_history_usage import optional_token

ENDPOINT = "https://ollama.com/api/chat"
#: Structured-output calls default to no reasoning; see chat().
THINK_DEFAULT = False
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
    # Small models. Registering these is what makes a weak executor usable at
    # all: output_capability_for fails closed on an unknown model, so a solve
    # pinned to gpt-oss:20b died with token_bound_unavailable before any work,
    # and "decompose with a large model, implement with a small one" was
    # unreachable for want of three numbers.
    "gpt-oss:20b": ModelOutputCapability(
        131072,
        "Ollama HTTP 400 response declared the exact model maximum",
        observed_at="2026-09-06"),
    "nemotron-3-nano:30b": ModelOutputCapability(
        131072,
        "Ollama HTTP 400 response declared the exact model maximum",
        observed_at="2026-09-06"),
    "gemma4:31b": ModelOutputCapability(
        262144,
        "Ollama HTTP 400 response declared the exact model maximum",
        observed_at="2026-09-06"),
    # The thirteen remaining models Ollama Cloud listed on 2026-09-13,
    # each maximum read from the service's own refusal of an over-limit
    # request on 2026-09-14 by learn_output_capability (one request per
    # model, no generation); the refusal names the exact number.
    "deepseek-v4.1-flash": ModelOutputCapability(
        393216,
        "Ollama HTTP 400 response declared the exact model maximum",
        observed_at="2026-09-14"),
    "glm-5.1": ModelOutputCapability(
        131072,
        "Ollama HTTP 400 response declared the exact model maximum",
        observed_at="2026-09-14"),
    "glm-5.2": ModelOutputCapability(
        131072,
        "Ollama HTTP 400 response declared the exact model maximum",
        observed_at="2026-09-14"),
    "glm-5.3": ModelOutputCapability(
        1048576,
        "Ollama HTTP 400 response declared the exact model maximum",
        observed_at="2026-09-14"),
    "gpt-oss:120b": ModelOutputCapability(
        131072,
        "Ollama HTTP 400 response declared the exact model maximum",
        observed_at="2026-09-14"),
    "kimi-k2.6": ModelOutputCapability(
        262144,
        "Ollama HTTP 400 response declared the exact model maximum",
        observed_at="2026-09-14"),
    "kimi-k2.7-code": ModelOutputCapability(
        262144,
        "Ollama HTTP 400 response declared the exact model maximum",
        observed_at="2026-09-14"),
    "minimax-m2.7": ModelOutputCapability(
        131072,
        "Ollama HTTP 400 response declared the exact model maximum",
        observed_at="2026-09-14"),
    "minimax-m3": ModelOutputCapability(
        131072,
        "Ollama HTTP 400 response declared the exact model maximum",
        observed_at="2026-09-14"),
    "mistral-large-3:675b": ModelOutputCapability(
        262144,
        "Ollama HTTP 400 response declared the exact model maximum",
        observed_at="2026-09-14"),
    "nemotron-3-super": ModelOutputCapability(
        65536,
        "Ollama HTTP 400 response declared the exact model maximum",
        observed_at="2026-09-14"),
    "nemotron-3-ultra": ModelOutputCapability(
        65536,
        "Ollama HTTP 400 response declared the exact model maximum",
        observed_at="2026-09-14"),
    "qwen3.5:397b": ModelOutputCapability(
        65536,
        "Ollama HTTP 400 response declared the exact model maximum",
        observed_at="2026-09-14"),
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


def live_model_listing(api_key: str | None = None,
                       timeout: float = 30.0) -> dict:
    """The served catalog as a record that says whether it was obtained.

    ``live_models`` folds a missing key, a refused key, an outage, and an
    empty catalog into one empty list. A readiness probe has to tell them
    apart: a refused key stops a route, an outage waits, and an empty
    catalog with a working key is a provider still coming up. Forbidden
    models are listed separately so the record shows what was withheld.
    """
    key = api_key or load_api_key()
    record = {"record_type": "ollama_model_listing/v1",
              "listing_url": CATALOG_ENDPOINT, "ok": False, "models": [],
              "forbidden": [], "http_status": None, "error": "",
              "error_type": "", "retry_after_seconds": None,
              "credential_present": bool(key)}
    if not key:
        record.update(error="OLLAMA_API_KEY not found",
                      error_type="MissingCredential")
        return record
    req = urllib.request.Request(
        CATALOG_ENDPOINT, headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(4 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read()[:300].decode("utf-8", "replace")
        except OSError:
            pass
        record.update(http_status=exc.code, error=f"HTTP {exc.code}: {detail}",
                      error_type="HTTPError",
                      retry_after_seconds=_retry_after_seconds(
                          getattr(exc, "headers", None)))
        return record
    except (urllib.error.URLError, OSError) as exc:
        record.update(error=f"{type(exc).__name__}: {str(exc)[:250]}",
                      error_type=type(exc).__name__)
        return record
    if len(raw) > 4 * 1024 * 1024:
        record.update(error="invalid_response_body: listing exceeds the "
                            "probe contract", error_type="OversizedListing")
        return record
    try:
        data = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        record.update(error="invalid_response_body: listing is not JSON",
                      error_type="ValueError")
        return record
    if not isinstance(data, dict):
        record.update(error="invalid_response_body: listing is not an object",
                      error_type="ValueError")
        return record
    if data.get("error"):
        record.update(error=f"provider_error_body: {str(data['error'])[:300]}",
                      error_type="ErrorBody")
        return record
    names = [str(m.get("name") or m.get("model") or "")
             for m in data.get("models", ()) if isinstance(m, dict)]
    names = [n for n in names if n]
    forbidden = [n for n in names
                 if any(n.startswith(f) for f in FORBIDDEN_MODELS)]
    record.update(ok=True, http_status=200,
                  models=[n for n in names if n not in forbidden],
                  forbidden=forbidden)
    return record


def live_models(api_key: str | None = None) -> list[str]:
    """The currently-served Ollama Cloud models, minus any forbidden by policy.

    Compatibility projection of ``live_model_listing``: every failure
    reads as an empty list; ask the listing record for the reason.
    """
    return list(live_model_listing(api_key)["models"])


def _redacted(detail: str, secret: str) -> str:
    """Provider error text with the key and any bearer token removed."""
    import re
    text = str(detail)
    if secret:
        text = text.replace(secret, "<redacted>")
    return re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{8,}", "Bearer <redacted>", text)


def _retry_after_seconds(headers) -> "float | None":
    """The wait a refusal asked for (``Retry-After`` as seconds or an HTTP
    date), or None when the provider stated none."""
    if headers is None:
        return None
    try:
        raw = headers.get("Retry-After")
    except AttributeError:
        return None
    text = str(raw).strip() if raw is not None else ""
    if not text:
        return None
    try:
        return max(0.0, float(text))
    except ValueError:
        pass
    try:
        import email.utils
        import time as _time
        when = email.utils.parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        from datetime import timezone
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, when.timestamp() - _time.time())


#: The OpenAI-compatible chat path beside the native one, where the
#: service validates the requested ceiling against the model's maximum
#: before generating. Composed from the one declared endpoint above, so
#: this module binds a single service origin.
NATIVE_CHAT_PATH = "/api/chat"
COMPATIBLE_CHAT_PATH = "/v1/chat/completions"
COMPATIBLE_CHAT_ENDPOINT = ENDPOINT[:-len(NATIVE_CHAT_PATH)] + COMPATIBLE_CHAT_PATH
#: A request far above any served ceiling, so the validation names the
#: real one. Never sent as a generation budget: the stream is closed on
#: its first byte if the service accepts instead of refusing.
CEILING_PROBE_REQUEST_TOKENS = 100_000_000
#: No served model's output ceiling is below this; a smaller integer in a
#: refusal (a status, a count, a version) is not the ceiling.
SMALLEST_PLAUSIBLE_CEILING = 256
LEARNED_CAPABILITY_RECORD_TYPE = "learned_output_capability/v1"


def _declared_maximum(message: str, requested: int) -> "int | None":
    """The one integer a refusal names as the maximum, never the number we
    sent, a reference id, or a digit in the model's name.

    Ollama Cloud's wording on 2026-09-14: ``max_tokens (100000000) exceeds
    model's maximum output tokens (393216) for model deepseek-v4.1-flash
    (ref: 9e1e0e6a-...)``. The number after "maximum" is taken when the
    wording names one; otherwise the refusal must contain exactly one
    plausible integer once references and the request are removed.
    """
    import re
    text = re.sub(r"\(ref:[^)]*\)|\b(?=[0-9a-f-]*[a-f])[0-9a-f]{6,}(?:-[0-9a-f]{2,})*\b", " ",
                  message, flags=re.I)
    named = {int(n.replace(",", "")) for n in re.findall(
        r"maximum[^0-9]{0,60}?(\d[\d,]*)", text, flags=re.I)}
    named = {n for n in named if n != requested and n >= SMALLEST_PLAUSIBLE_CEILING}
    if len(named) == 1:
        return next(iter(named))
    numbers = {int(n.replace(",", "")) for n in re.findall(r"(?<![\w.:-])\d[\d,]*(?![\w.:-])", text)}
    numbers.discard(requested)
    candidates = sorted(n for n in numbers if n >= SMALLEST_PLAUSIBLE_CEILING)
    return candidates[0] if len(candidates) == 1 else None


def learn_output_capability(model: str, api_key: str | None = None,
                            timeout: float = 30.0, *, observed_at: str = "") -> dict:
    """Ask the service to name one model's output ceiling.

    The request asks for far more output than any served model allows, on
    the OpenAI-compatible path where the service validates the ceiling
    before generating. A refusal that names the exact maximum (the source
    the capability table already cites for every entry) yields a
    ``ModelOutputCapability`` under ``capability``; anything else yields
    none: an accepted request is closed on its first byte and recorded as
    ``accepted_without_ceiling``, because acceptance is not proof (a server
    may clamp silently), and a refusal by allowance or credential is
    recorded by its status. Nothing here guesses a number.
    """
    from datetime import date
    key = load_api_key() if api_key is None else api_key
    observed = observed_at or date.today().isoformat()
    record = {"record_type": LEARNED_CAPABILITY_RECORD_TYPE, "model": model,
              "endpoint": COMPATIBLE_CHAT_ENDPOINT,
              "requested_output_tokens": CEILING_PROBE_REQUEST_TOKENS,
              "observed_at": observed, "ok": False, "maximum_output_tokens": None,
              "source": "", "capability": None, "http_status": None,
              "declaration_text": "", "error": "", "error_type": "",
              "accepted_without_ceiling": False, "physical_requests": 0,
              "retry_after_seconds": None}
    if not key:
        record.update(error="OLLAMA_API_KEY not found", error_type="MissingCredential")
        return record
    payload = {"model": model, "messages": [{"role": "user", "content": "Reply with one word: x"}],
               "max_tokens": CEILING_PROBE_REQUEST_TOKENS, "temperature": 0.0, "stream": True}
    req = urllib.request.Request(
        COMPATIBLE_CHAT_ENDPOINT, data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    record["physical_requests"] = 1
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            # Accepted: read one chunk so the record says what came, and
            # leave; closing the response ends the stream.
            first = resp.read(200)
        record.update(http_status=200, accepted_without_ceiling=True,
                      declaration_text=first.decode("utf-8", "replace")[:200],
                      error="the service accepted the request instead of naming a "
                            "ceiling; acceptance is not a declared maximum")
        return record
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = _redacted(exc.read()[:400].decode("utf-8", "replace"), key)
        except OSError:
            pass
        record.update(http_status=exc.code, declaration_text=detail,
                      retry_after_seconds=_retry_after_seconds(getattr(exc, "headers", None)))
        if exc.code != 400:
            record.update(error=f"HTTP {exc.code}: {detail}", error_type="HTTPError")
            return record
        message = detail
        try:
            body = json.loads(detail)
            error = body.get("error") if isinstance(body, dict) else None
            if isinstance(error, dict):
                message = str(error.get("message") or detail)
            elif isinstance(error, str):
                message = error
        except ValueError:
            pass
        maximum = _declared_maximum(message, CEILING_PROBE_REQUEST_TOKENS)
        if maximum is None:
            record.update(error="HTTP 400 did not name exactly one maximum: " + message[:200],
                          error_type="UndeclaredMaximum")
            return record
        source = ("Ollama HTTP 400 response declared the exact model maximum: "
                  + message[:160])
        record.update(ok=True, maximum_output_tokens=maximum, source=source,
                      capability=ModelOutputCapability(maximum, source, observed_at=observed))
        return record
    except (urllib.error.URLError, OSError) as exc:
        record.update(error=f"{type(exc).__name__}: {str(exc)[:200]}", error_type=type(exc).__name__)
        return record


def learn_output_capabilities(models, api_key: str | None = None,
                              timeout: float = 30.0) -> dict:
    """One learned-capability record per model, stopping at the first
    refusal by allowance or credential, since every later request would be
    refused the same way."""
    records = {}
    stopped_by = ""
    for model in models:
        record = learn_output_capability(model, api_key, timeout)
        records[model] = record
        if record["http_status"] in (401, 402, 403, 429) or record["error_type"] == "MissingCredential":
            stopped_by = record["error"]
            break
    return {"record_type": "learned_output_capabilities/v1", "records": records,
            "learned": sorted(m for m, r in records.items() if r["ok"]),
            "stopped_by": stopped_by,
            "physical_requests": sum(r["physical_requests"] for r in records.values())}


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
    prompt_tokens: int | None = None
    eval_tokens: int | None = None
    ok: bool = True
    error: str = ""
    num_predict_used: int = 0      # the output ceiling this call actually ran at
    attempts: int = 1             # physical calls represented by this result
    response_received: bool = False
    done: "bool | None" = None
    done_reason: str = ""
    reasoning_present: bool = False
    output_limit_reached: bool = False
    #: The wait a refusal asked for (``Retry-After``), in seconds; None when
    #: the provider stated none, which is not the same as zero.
    retry_after_seconds: "float | None" = None
    #: Whether a streamed request delivered this result (``auto`` mode
    #: records which mode actually answered).
    delivered_by_stream: bool = False
    #: HTTP requests this one logical attempt opened: two when ``auto``
    #: streaming retried a proxy timeout, zero when the adapter refused
    #: before sending. ``attempts`` stays the contract's one.
    physical_requests: int = 1
    usage_reported: bool = False

    @property
    def total_tokens(self) -> int | None:
        if self.prompt_tokens is None or self.eval_tokens is None:
            return None
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
                "output_limit_reached": self.output_limit_reached,
                "retry_after_seconds": self.retry_after_seconds,
                "delivered_by_stream": self.delivered_by_stream,
                "physical_requests": self.physical_requests,
                "usage_reported": self.usage_reported}


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
    return bool(type(output_tokens) is int and maximum_output_tokens > 0
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
            "", "", ok=False, physical_requests=0,
            error="physical model retries require an explicit outer call budget")
    return chat(
        prompt, model=model, system=system,
        num_predict=max_output_tokens, temperature=temperature,
        timeout=timeout, api_key=api_key,
        output_capability=output_capability)


def chat(prompt: str, *, model: str = DEFAULT_MODEL, system: str = "",
         num_predict: "int | None" = None, temperature: float = 0.7,
         timeout: float = 90.0, api_key: str | None = None,
         think: "bool | None" = THINK_DEFAULT,
         output_capability: "ModelOutputCapability | None" = None) -> ChatResult:
    """Send one chat request to Ollama Cloud and return the text + provider token
    counts.  Never raises — a failure returns ``ok=False`` with the error, so a
    resolver can fall back rather than crash the loop."""
    try:
        capability = output_capability or output_capability_for(model)
        maximum = require_declared_maximum(num_predict, capability)
    except (UnknownModelOutputLimit, ModelOutputLimitMismatch) as exc:
        return ChatResult("", "", ok=False, error=str(exc), physical_requests=0)
    # An explicit api_key="" means "no key" (used to test fallback); only None
    # falls back to the environment / .env.
    key = load_api_key() if api_key is None else api_key
    if not key:
        return ChatResult("", "", ok=False,
                          error="OLLAMA_API_KEY not found",
                          physical_requests=0)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model, "messages": messages, "stream": False,
        "options": {"num_predict": maximum, "temperature": temperature},
    }
    #: A reasoning model spends num_predict on its thinking before it emits a
    #: single content byte, so an unbounded think budget truncates the answer
    #: the caller actually asked for.  Measured on deepseek-v4-flash at
    #: num_predict=4096: thinking consumed 9,853 characters and the JSON body
    #: came back truncated (done_reason="length"); with think=False the same
    #: request returned 8,018 characters of valid JSON and stopped naturally.
    #: Every caller here wants a structured payload, not the reasoning, so the
    #: default is off and a caller may re-enable it explicitly.
    if think is not None:
        payload["think"] = think
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        ENDPOINT, data=body, method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read()[:300].decode("utf-8", "replace")
        except OSError:
            pass
        detail = _redacted(detail, key)
        retry_after = _retry_after_seconds(getattr(exc, "headers", None))
        stated = (f" (retry after {retry_after:g}s)"
                  if retry_after is not None else "")
        return ChatResult("", "", ok=False,
                          error=f"HTTP {exc.code}{stated}: {detail}",
                          retry_after_seconds=retry_after)
    except Exception as exc:
        return ChatResult("", "", ok=False, error=repr(exc))
    try:
        data = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return ChatResult("", "", ok=False, response_received=True,
                          error="invalid_response_body: Ollama answered with "
                                "a body that is not JSON")
    if not isinstance(data, dict):
        return ChatResult("", "", ok=False, response_received=True,
                          error="invalid_response_body: Ollama answered with "
                                "JSON that is not an object")
    reported_model = data.get("model") if type(data.get("model")) is str else ""
    prompt_tokens = optional_token(data.get("prompt_eval_count"))
    eval_tokens = optional_token(data.get("eval_count"))
    if data.get("error") and not (data.get("message") or {}).get("content"):
        # A refusal inside a 200 body is classified by its words, never
        # read as an empty answer.
        return ChatResult("", reported_model, prompt_tokens=prompt_tokens, eval_tokens=eval_tokens, ok=False,
                          response_received=True,
                          usage_reported=prompt_tokens is not None and eval_tokens is not None,
                          error=f"provider_error_body: {str(data['error'])[:300]}")
    message = data.get("message", {}) or {}
    text = message.get("content", "")
    reasoning_present = bool(str(message.get("thinking", "") or "").strip())
    done = data.get("done") if isinstance(data.get("done"), bool) else None
    done_reason = str(data.get("done_reason", "") or "")
    output_limit_reached = response_reached_output_limit(
        done_reason, eval_tokens, maximum)
    error = ""
    if reported_model != model:
        error = "model_identity_mismatch: the provider did not report the exact requested model"
    elif output_limit_reached:
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
        text=text, model=reported_model,
        prompt_tokens=prompt_tokens, eval_tokens=eval_tokens,
        ok=bool(text) and not error,
        error=error, num_predict_used=maximum, response_received=True,
        done=done, done_reason=done_reason,
        reasoning_present=reasoning_present,
        output_limit_reached=output_limit_reached,
        usage_reported=prompt_tokens is not None and eval_tokens is not None)


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

    # Learning a ceiling: only a 400 that names exactly one maximum yields a
    # capability; acceptance, allowance refusals, and vague refusals do not.
    import email.message
    import io

    def _refusal(code, body):
        return urllib.error.HTTPError(COMPATIBLE_CHAT_ENDPOINT, code, f"status {code}",
                                      email.message.Message(), io.BytesIO(body))

    class _Accepted:
        def __init__(self):
            self.closed = False

        def read(self, limit=None):
            return b'data: {"choices": [{"delta": {"content": "x"}}]}\n'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.closed = True
            return False

    scripted = {}
    sent = []

    def _fake_urlopen(request, timeout=None):
        sent.append(json.loads(request.data))
        item = scripted[sent[-1]["model"]]()  # fresh each time: a body reads once
        if isinstance(item, BaseException):
            raise item
        return item
    saved = urllib.request.urlopen
    urllib.request.urlopen = _fake_urlopen
    try:
        accepted = _Accepted()
        scripted.update({
            "named": lambda: _refusal(400, b'{"error":{"message":"max_tokens 100000000 exceeds the maximum of 65536 for this model"}}'),
            "live": lambda: _refusal(400, b'{"error":{"message":"max_tokens (100000000) exceeds model\'s maximum output '
                                          b'tokens (65536) for model qwen3.5:397b (ref: 9e1e0e6a-3cd6-4cc1-804f-a124c7436645)",'
                                          b'"type":"invalid_request_error","param":null,"code":null}}'),
            "plain": lambda: _refusal(400, b'{"error":"num_predict must be at most 131,072"}'),
            "vague": lambda: _refusal(400, b'{"error":"invalid request"}'),
            "spent": lambda: _refusal(429, b'{"error":"you have reached your weekly usage limit"}'),
            "open": lambda: accepted,
        })
        named = learn_output_capability("named", api_key="fixture-key", observed_at="2026-09-13")
        live = learn_output_capability("live", api_key="fixture-key")
        plain = learn_output_capability("plain", api_key="fixture-key")
        vague = learn_output_capability("vague", api_key="fixture-key")
        spent = learn_output_capability("spent", api_key="fixture-key")
        opened = learn_output_capability("open", api_key="fixture-key")
        batch = learn_output_capabilities(["named", "spent", "plain"], api_key="fixture-key")
    finally:
        urllib.request.urlopen = saved
    check("the_live_wording_with_a_reference_id_and_digits_in_the_model_name_yields_the_maximum",
          live["ok"] and live["maximum_output_tokens"] == 65536, live["error"])
    check("a_refusal_that_names_the_maximum_yields_a_source_backed_capability",
          named["ok"] and named["maximum_output_tokens"] == 65536
          and isinstance(named["capability"], ModelOutputCapability)
          and named["capability"].maximum_output_tokens == 65536
          and named["capability"].observed_at == "2026-09-13"
          and "declared the exact model maximum" in named["source"]
          and plain["ok"] and plain["maximum_output_tokens"] == 131072
          and sent[0]["max_tokens"] == CEILING_PROBE_REQUEST_TOKENS and sent[0]["stream"] is True,
          named["error"] or plain["error"])
    check("a_vague_refusal_an_allowance_refusal_and_an_acceptance_yield_no_number",
          not vague["ok"] and vague["error_type"] == "UndeclaredMaximum"
          and not spent["ok"] and spent["http_status"] == 429 and spent["maximum_output_tokens"] is None
          and not opened["ok"] and opened["accepted_without_ceiling"] and accepted.closed
          and opened["maximum_output_tokens"] is None and opened["physical_requests"] == 1,
          f"{vague['error'][:60]} / {spent['error'][:60]} / {opened['error'][:60]}")
    check("a_batch_stops_at_the_first_allowance_refusal_and_counts_its_requests",
          batch["learned"] == ["named"] and "plain" not in batch["records"]
          and batch["stopped_by"].startswith("HTTP 429") and batch["physical_requests"] == 2)
    check("a_missing_key_learns_nothing_and_sends_nothing",
          learn_output_capability("any", api_key="")["physical_requests"] == 0)

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
