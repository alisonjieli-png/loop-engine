"""Custom endpoints — point the loop at any OpenAI-compatible server.

Architectural role: static architecture (a parameterised provider adapter).

Almost every self-hosted inference server speaks the same wire format: vLLM,
LM Studio, llama.cpp's server, text-generation-webui, LiteLLM, Ollama's compat
layer, and most managed gateways all expose ``POST /v1/chat/completions`` with
an OpenAI-shaped body. So "support custom endpoints" does not mean writing an
adapter per server — it means ONE adapter parameterised by base URL, key, and
model, plus an honest statement of what that endpoint is.

    endpoint = CustomEndpoint(name="friends_box",
                              base_url="https://gpu.example.net/v1",
                              api_key="...", model="qwen2.5-72b-instruct",
                              locality="local")
    register_endpoint(endpoint)          # now a provider like any other

The distinction this module is careful about, because it is easy to get wrong:

    A CUSTOM ENDPOINT IS USABLE BY ANYONE; WHETHER ITS TOKENS COUNT AS
    LOOP ENGINE EVIDENCE IS A SEPARATE QUESTION.

    The cloud-only rule exists because a measurement campaign needs
    provider-reported counts that another machine can reproduce. That is a
    rule about EVIDENCE, not a restriction on what a library user may run. So
    a custom endpoint is free to serve any loop; it is `counts_as_evidence`
    that decides whether its usage may back a savings or benchmark claim, and
    that defaults to False for a self-hosted box until its owner says
    otherwise.

Owns:
    - CustomEndpoint: the declared configuration plus its evidence posture;
    - make_adapter(): the endpoint as a module-shaped adapter the resolver
      already knows how to call;
    - register_endpoint() / unregister_endpoint(): joining the provider table;
    - endpoints_from_env(): LOOP_ENGINE_ENDPOINTS parsing, so deployment needs no
      code.

Does not own:
    - the built-in adapters, failover order, discovery, or loop semantics.

Key invariants:
    - a forbidden model is refused here too;
    - never raises — a failure returns ok=False with the reason;
    - a self-hosted endpoint does not silently become admissible evidence;
    - registering an endpoint never displaces a built-in provider by accident
      (a name collision is refused).

Verification: self_test() — adapter contract parity, evidence posture, name
collision refusal, environment parsing, and the adversarial forbidden-model and
credential-leak paths.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from .ollama_client import (
    ChatResult, FORBIDDEN_MODELS, response_reached_output_limit,
)
from .model_capabilities import (
    ModelOutputCapability, ModelOutputLimitMismatch,
    UnknownModelOutputLimit, require_declared_maximum,
)
from .provider_failover import PROVIDERS

#: Wire formats understood. "openai" covers the overwhelming majority of
#: self-hosted servers; "ollama" is the native /api/chat shape.
#: Streaming modes for a custom endpoint.
#:   "auto"    - self-orienting: try the endpoint's normal (non-streamed)
#:               request first; when a generation dies at a reverse-proxy
#:               read wall (gateway timeout), retry the same request with
#:               SSE streaming, which keeps the proxy's read timer fed.
#:               The learned mode is remembered per run in route health.
#:   "stream"  - always send stream: true (proxied gateways that must not
#:               hold a silent connection open for minutes).
#:   "buffer"  - always send stream: false (direct, unproxied servers).
STREAM_MODES = ("auto", "stream", "buffer")

WIRE_FORMATS = ("openai", "ollama")


def _normalize_stream(value: object) -> str:
    """Accept flexible spellings from settings and env declarations."""
    if value is None:
        return "auto"
    if isinstance(value, bool):
        return "stream" if value else "buffer"
    text = str(value).strip().casefold()
    aliases = {
        "auto": "auto", "self": "auto", "detect": "auto",
        "stream": "stream", "true": "stream", "yes": "stream",
        "sse": "stream", "1": "stream",
        "buffer": "buffer", "false": "buffer", "no": "buffer",
        "0": "buffer", "none": "buffer", "off": "buffer",
    }
    if text not in aliases:
        raise EndpointError(
            f"stream must be one of {STREAM_MODES} (booleans and common "
            f"spellings accepted); got {value!r}")
    return aliases[text]

LOCALITIES = ("cloud", "organization", "local")


class EndpointError(ValueError):
    """A custom endpoint declared something inconsistent."""


@dataclass(frozen=True)
class CustomEndpoint:
    """One user-supplied inference server.

    ``counts_as_evidence`` is deliberately explicit rather than inferred. A
    self-hosted server can absolutely report honest token counts — but whether
    a campaign may cite them is a judgement about reproducibility on another
    machine, and that belongs to whoever runs the campaign."""
    name: str
    base_url: str
    model: str
    api_key: str = field(default="", repr=False, compare=False)
    wire: str = "openai"
    locality: str = "local"
    output_capability: "ModelOutputCapability | None" = None
    counts_as_evidence: bool = False
    timeout: float = 900.0
    headers: tuple[tuple[str, str], ...] = ()
    auth_scheme: str = "bearer"
    auth_header: str = ""
    stream: str = "auto"
    tls_verification: str = "default"

    def __post_init__(self):
        if not self.name or not self.name.replace("_", "").isalnum():
            raise EndpointError(
                f"endpoint name {self.name!r} must be a simple identifier — it "
                "becomes a provider key and appears in records")
        if self.wire not in WIRE_FORMATS:
            raise EndpointError(f"wire {self.wire!r} not in {WIRE_FORMATS}")
        if self.locality not in LOCALITIES:
            raise EndpointError(f"locality must be one of {LOCALITIES}")
        if self.tls_verification not in ("default", "skip"):
            raise EndpointError(
                "tls_verification must be default or skip; skip is the "
                "explicit operator choice for an origin behind a private "
                "certificate authority (such as a Cloudflare Origin CA on "
                "a DNS-only hostname) and is recorded in every run")
        if self.auth_scheme not in ("bearer", "header", "none"):
            raise EndpointError(
                "auth_scheme must be bearer, header, or none")
        object.__setattr__(self, "stream", _normalize_stream(self.stream))
        if self.stream not in STREAM_MODES:
            raise EndpointError(
                f"stream must be one of {STREAM_MODES}")
        if self.auth_scheme == "header":
            if (not self.auth_header.strip()
                    or not re.fullmatch(
                        r"[!#$%&'*+.^_`|~0-9A-Za-z-]+",
                        self.auth_header)
                    or self.auth_header.casefold() in {
                        "authorization", "proxy-authorization", "cookie",
                        "set-cookie"}):
                raise EndpointError(
                    "header authentication needs a valid HTTP header name")
        elif self.auth_header:
            raise EndpointError(
                "auth_header is only valid for header authentication")
        if self.auth_scheme == "none" and self.api_key:
            raise EndpointError(
                "auth_scheme none cannot carry an API key")
        if (self.output_capability is not None
                and not isinstance(self.output_capability,
                                   ModelOutputCapability)):
            raise EndpointError(
                "output_capability must be a ModelOutputCapability")
        if not self.base_url.startswith(("http://", "https://")):
            raise EndpointError(
                f"base_url {self.base_url!r} must be an http(s) URL")
        base = self.model.split("/")[-1].split(":")[0]
        if any(f in self.model or f in base for f in FORBIDDEN_MODELS):
            raise EndpointError(
                f"model {self.model!r} is forbidden by policy — a custom "
                "endpoint is not a way around a model ban")
        if self.locality == "local" and self.counts_as_evidence:
            # Allowed, but it must be a DECLARED choice by someone who knows
            # what it means, so it is stated in the record rather than assumed.
            pass
        forbidden = {"authorization", "proxy-authorization", "cookie",
                     "set-cookie", "x-api-key", "api-key"}
        headers = tuple(self.headers)
        if any(not isinstance(item, tuple) or len(item) != 2
               or not all(isinstance(value, str) for value in item)
               for item in headers):
            raise EndpointError(
                "custom endpoint headers must contain text name/value pairs")
        if (len(headers) != len({item[0].casefold() for item in headers})
                or any(not item[0].strip() or not item[1].strip()
                       or item[0].casefold() in forbidden
                       or item[0].casefold() == self.auth_header.casefold()
                       or "\n" in item[0] or "\r" in item[0]
                       or "\n" in item[1] or "\r" in item[1]
                       for item in headers)):
            raise EndpointError(
                "custom endpoint headers must be unique non-secret headers")
        object.__setattr__(self, "headers", tuple(sorted(headers)))

    @property
    def chat_url(self) -> str:
        base = self.base_url.rstrip("/")
        if self.wire == "ollama":
            return base + ("/api/chat" if not base.endswith("/api/chat") else "")
        return base + ("/chat/completions"
                       if not base.endswith("/chat/completions") else "")

    def describe(self) -> dict:
        """Record shape — carries no credential."""
        return {"name": self.name, "base_url": self.base_url,
                "model": self.model, "wire": self.wire,
                "locality": self.locality,
                "output_capability": (self.output_capability.summary()
                                      if self.output_capability else None),
                "counts_as_evidence": self.counts_as_evidence,
                "has_key": bool(self.api_key),
                "header_names": [item[0] for item in self.headers],
                "auth_scheme": self.auth_scheme,
                "auth_header": self.auth_header,
                "stream": self.stream,
                "tls_verification": self.tls_verification}


def _request_headers(ep: CustomEndpoint) -> dict[str, str]:
    """Resolve one secret-bearing request header without serializing it."""
    headers = {"Content-Type": "application/json", **dict(ep.headers)}
    if not ep.api_key or ep.auth_scheme == "none":
        return headers
    if ep.auth_scheme == "bearer":
        headers["Authorization"] = f"Bearer {ep.api_key}"
    else:
        headers[ep.auth_header] = ep.api_key
    return headers


def _endpoint_opener(ep: CustomEndpoint):
    """Return an opener honoring the endpoint's TLS verification policy.

    ``tls_verification: skip`` is the explicit operator choice for an
    origin serving a private certificate authority (for example a
    Cloudflare Origin CA on a DNS-only hostname). The choice is declared
    on the endpoint, appears in its describe() record, and never applies
    to any other provider.
    """
    if ep.tls_verification != "skip":
        return urllib.request.build_opener()
    import ssl
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    handler = urllib.request.HTTPSHandler(context=context)
    return urllib.request.build_opener(handler)


def _sse_lines(response):
    """Yield decoded SSE data lines from an open streaming response.

    Tolerant of gateway variance: lines may be bytes or text, ``data:``
    may be followed by any spacing, and some gateways emit ``data:[DONE]``
    with no space. Non-data lines (comments, event:, id:, keep-alives) are
    skipped, so an unseen gateway's framing cannot break parsing.
    """
    for raw_line in response:
        if isinstance(raw_line, bytes):
            line = raw_line.decode("utf-8", errors="replace")
        else:
            line = str(raw_line)
        stripped = line.strip()
        if not stripped or stripped.startswith(":"):
            continue
        if stripped.casefold().startswith("data:"):
            yield stripped[len("data:"):].strip()


def _sse_chunk_text(chunk: dict) -> tuple[list, list, str]:
    """Extract (content_parts, reasoning_parts, finish_reason) from one SSE
    chunk, tolerant of the shape variance across OpenAI-compatible servers.

    Observed variants: ``choices[0].delta.content`` (OpenAI/vLLM/TRT),
    ``choices[0].message.content`` (some Open WebUI and LiteLLM builds),
    ``delta.reasoning_content`` or ``delta.reasoning`` (thinking models),
    and finish_reason on any chunk. Unknown shapes contribute nothing
    rather than failing the stream.
    """
    content: list = []
    reasoning: list = []
    finish = ""
    choices = chunk.get("choices") or []
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        delta = choice.get("delta")
        if not isinstance(delta, dict):
            delta = choice.get("message") if isinstance(
                choice.get("message"), dict) else {}
        text = delta.get("content")
        if isinstance(text, str) and text:
            content.append(text)
        for reasoning_key in ("reasoning_content", "reasoning", "thinking"):
            value = delta.get(reasoning_key)
            if isinstance(value, str) and value:
                reasoning.append(value)
        reason = choice.get("finish_reason")
        if isinstance(reason, str) and reason:
            finish = reason
    text_fallback = chunk.get("content") or chunk.get("response")
    if not content and isinstance(text_fallback, str) and text_fallback:
        content.append(text_fallback)
    return content, reasoning, finish


def _chat_streamed(ep: CustomEndpoint, payload: dict, headers: dict,
                   timeout: float) -> dict:
    """One streamed SSE request; returns the same body shape as non-stream.

    Streaming keeps a reverse proxy's read timer fed with token chunks, so
    long generations no longer hit a silent-connection read timeout (such
    as Cloudflare's 125-second 524 wall). The streamed deltas are joined
    into the final text; usage and finish_reason come from the terminal
    chunk when the server sends them.
    """
    payload = dict(payload)
    payload["stream"] = True
    # Ask OpenAI-compatible servers to include usage in the final streamed
    # chunk. Gateways that do not know the option ignore it; gateways that
    # do return exact provider-reported token counts alongside the text.
    if ep.wire != "ollama":
        payload["stream_options"] = {"include_usage": True}
    req = urllib.request.Request(
        ep.chat_url, data=json.dumps(payload).encode(), headers=headers)
    text_parts: list[str] = []
    reasoning_parts: list[str] = []
    finish_reason = ""
    reported_model = ep.model
    usage: dict = {}
    with _endpoint_opener(ep).open(
            req, timeout=timeout) as response:
        for data in _sse_lines(response):
            if data == "[DONE]" or data.casefold() == "[done]":
                break
            try:
                chunk = json.loads(data)
            except ValueError:
                continue
            if not isinstance(chunk, dict):
                continue
            reported_model = str(chunk.get("model") or reported_model)
            content, reasoning, finish = _sse_chunk_text(chunk)
            text_parts.extend(content)
            reasoning_parts.extend(reasoning)
            if finish:
                finish_reason = finish
            if isinstance(chunk.get("usage"), dict):
                usage = chunk["usage"]
    if not usage:
        usage = {}
    return {
        "model": reported_model,
        "choices": [{"index": 0, "message": {
            "role": "assistant", "content": "".join(text_parts)},
            "finish_reason": finish_reason}],
        "usage": usage,
        "_streamed": True,
        "_reasoning": "".join(reasoning_parts),
    }


def _chat_once(ep: CustomEndpoint, prompt: str, *, system: str,
               max_tokens: int, temperature: float,
               timeout: float) -> ChatResult:
    """One request in whichever wire format the endpoint declared.

    Streaming is self-orienting in ``auto`` mode: the first attempt uses the
    endpoint's normal non-streamed request, and when a reverse-proxy read
    wall (gateway timeout) cuts a long generation, the same request is
    retried once with SSE streaming, which keeps the proxy's read timer
    fed. The streamed result is marked so the run record shows which mode
    actually delivered the response.
    """
    messages = ([{"role": "system", "content": system}] if system else []) \
        + [{"role": "user", "content": prompt}]
    if ep.wire == "ollama":
        payload = {"model": ep.model, "messages": messages, "stream": False,
                   "options": {"num_predict": int(max_tokens),
                               "temperature": temperature}}
    else:
        payload = {"model": ep.model, "messages": messages,
                   "max_tokens": int(max_tokens), "temperature": temperature}

    headers = _request_headers(ep)
    use_streaming = ep.stream == "stream"
    while True:
        try:
            if use_streaming:
                body = _chat_streamed(ep, payload, headers, timeout)
            else:
                req = urllib.request.Request(
                    ep.chat_url,
                    data=json.dumps(payload).encode(), headers=headers)
                with _endpoint_opener(ep).open(
                        req, timeout=timeout) as r:
                    body = json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read()[:300].decode("utf-8", "replace")
            except OSError:
                pass
            if e.code in (504, 524):
                if ep.stream == "auto" and not use_streaming:
                    # Self-orient: the proxy cut a silent non-streamed
                    # connection. Retry the same request with SSE streaming
                    # so the proxy's read timer stays fed.
                    use_streaming = True
                    continue
                return ChatResult(
                    text="", model=ep.model, ok=False,
                    error="gateway_timeout: origin did not finish before the "
                          f"proxy read timeout (HTTP {e.code}); a shorter "
                          "owner-set output ceiling may complete within the "
                          f"proxy window: {detail}")
            return ChatResult(text="", model=ep.model, ok=False,
                              error=f"HTTP {e.code}: {detail}")
        except (urllib.error.URLError, OSError, ValueError) as e:
            if ep.stream == "auto" and not use_streaming \
                    and isinstance(e, (urllib.error.URLError, OSError)) \
                    and "timed out" in str(e).lower():
                use_streaming = True
                continue
            return ChatResult(text="", model=ep.model, ok=False,
                              error=f"{type(e).__name__}: {str(e)[:250]}")
        break

    if ep.wire == "ollama" and not body.get("_streamed"):
        message = body.get("message") or {}
        text = message.get("content", "")
        p_tok = int(body.get("prompt_eval_count", 0) or 0)
        e_tok = int(body.get("eval_count", 0) or 0)
        done = body.get("done") if isinstance(body.get("done"), bool) else None
        done_reason = str(body.get("done_reason", "") or "")
        reasoning_present = bool(
            str(message.get("thinking", "") or "").strip())
    else:
        choices = body.get("choices") or []
        text = (choices[0].get("message", {}).get("content", "")
                if choices else "")
        usage = body.get("usage") or {}
        p_tok = int(usage.get("prompt_tokens", 0) or 0)
        e_tok = int(usage.get("completion_tokens", 0) or 0)
        done = True
        done_reason = str(choices[0].get("finish_reason", "") or "") \
            if choices else ""
        reasoning_present = bool(str(body.get("_reasoning") or "").strip())
    output_limit_reached = response_reached_output_limit(
        done_reason, e_tok, int(max_tokens))
    error = ""
    if output_limit_reached:
        error = (
            "output_limit_reached: endpoint stopped at its declared output "
            "ceiling")
    elif done is False:
        error = "incomplete_response: endpoint response did not finish"
    elif not text and reasoning_present:
        error = (
            "output_validation_failed: endpoint returned reasoning but no "
            "final response content")
    elif not text:
        error = "empty_response: endpoint returned no final response content"
    return ChatResult(text=str(text), model=str(body.get("model", ep.model)),
                      prompt_tokens=p_tok, eval_tokens=e_tok,
                      ok=bool(text) and not output_limit_reached
                      and done is not False,
                      num_predict_used=int(max_tokens), error=error,
                      response_received=True, done=done,
                      done_reason=done_reason,
                      reasoning_present=reasoning_present,
                      output_limit_reached=output_limit_reached)


def make_adapter(ep: CustomEndpoint):
    """The endpoint as a module-shaped adapter.

    The resolver calls ``chat_maxout`` / ``chat`` / ``verify`` and reads
    ``DEFAULT_MODEL``; anything exposing those IS a provider here. Returning a
    small object rather than requiring a module file is what makes a
    user-supplied server a first-class provider without a code change."""

    class _Adapter:
        DEFAULT_MODEL = ep.model
        endpoint = ep

        @staticmethod
        def output_capability_for(model=""):
            selected = model or ep.model
            if selected != ep.model or ep.output_capability is None:
                raise UnknownModelOutputLimit(
                    "unknown_model_output_limit: custom endpoint needs an "
                    "explicit ModelOutputCapability for its exact model")
            return ep.output_capability

        @staticmethod
        def chat(prompt, *, model="", system="", max_tokens=0,
                 temperature=0.7, timeout=None, api_key=None,
                 output_capability=None):
            try:
                capability = (output_capability
                              or _Adapter.output_capability_for(model))
                maximum = require_declared_maximum(
                    max_tokens or None, capability)
            except (UnknownModelOutputLimit,
                    ModelOutputLimitMismatch) as exc:
                return ChatResult("", model or ep.model, ok=False,
                                  error=str(exc))
            return _chat_once(
                ep, prompt, system=system, max_tokens=maximum,
                temperature=temperature, timeout=timeout or ep.timeout)

        @staticmethod
        def chat_maxout(prompt, *, model="", system="", temperature=0.7,
                        timeout=None, api_key=None, backoff=0.9,
                        floor_frac=0.3, max_attempts=1,
                        max_output_tokens=None, output_capability=None):
            """Make one call at the explicitly declared model maximum."""
            del backoff, floor_frac
            if max_attempts != 1:
                return ChatResult(
                    "", model or ep.model, ok=False,
                    error="physical model retries require an explicit outer "
                          "call budget")
            return _Adapter.chat(
                prompt, model=model, system=system,
                max_tokens=max_output_tokens or 0,
                temperature=temperature, timeout=timeout, api_key=api_key,
                output_capability=output_capability)

        @staticmethod
        def live_models():
            """Whatever the endpoint lists, or just its configured model."""
            url = ep.base_url.rstrip("/") + (
                "/api/tags" if ep.wire == "ollama" else "/models")
            headers = _request_headers(ep)
            try:
                with _endpoint_opener(ep).open(
                        urllib.request.Request(url, headers=headers),
                        timeout=30) as r:
                    body = json.loads(r.read())
            except (urllib.error.URLError, OSError, ValueError):
                return [ep.model]
            rows = body.get("data") or body.get("models") or []
            names = sorted(str(m.get("id") or m.get("name", "")) for m in rows)
            return [n for n in names if n] or [ep.model]

        @staticmethod
        def verify(model=""):
            r = _Adapter.chat(
                "Reply with one word: READY", model=model, system="",
                temperature=0.0, timeout=60)
            return {"provider": ep.name, "model": r.model, "ok": r.ok,
                    "prompt_tokens": r.prompt_tokens,
                    "eval_tokens": r.eval_tokens, "error": r.error[:200],
                    "locality": ep.locality,
                    "counts_as_evidence": ep.counts_as_evidence}

    return _Adapter


def register_endpoint(ep: CustomEndpoint, *, order_hint: str = "append"):
    """Make this endpoint a provider the resolver can reach.

    A name that collides with a built-in provider is REFUSED rather than
    silently shadowing it — quietly replacing a sanctioned provider is exactly
    the kind of substitution a record would then misattribute."""
    builtins = {"ollama_cloud", "mistral", "openrouter"}
    if ep.name in builtins:
        raise EndpointError(
            f"{ep.name!r} is a built-in provider; choose another name rather "
            "than shadowing it — a record naming that provider must mean it")
    adapter = make_adapter(ep)
    PROVIDERS[ep.name] = adapter
    return adapter


def unregister_endpoint(name: str) -> bool:
    """Remove a custom endpoint. Built-ins cannot be removed this way."""
    if name in {"ollama_cloud", "mistral", "openrouter"}:
        raise EndpointError(f"{name!r} is a built-in provider, not a custom "
                            "endpoint")
    return PROVIDERS.pop(name, None) is not None


def endpoints_from_env(value: "str | None" = None) -> list:
    """Parse ``LOOP_ENGINE_ENDPOINTS`` so a deployment needs no code change.

    Format is one endpoint per entry, semicolon-separated fields:

        name=friends_box,url=https://gpu.example.net/v1,model=qwen2.5,key=sk-…

    Multiple endpoints are separated by ``|``. Unknown fields are refused
    rather than ignored, because a typo'd field silently dropping a key is the
    failure this format exists to avoid."""
    raw = value if value is not None else os.environ.get("LOOP_ENGINE_ENDPOINTS", "")
    out = []
    for chunk in [c.strip() for c in raw.split("|") if c.strip()]:
        fields = {}
        for part in chunk.split(","):
            if "=" not in part:
                raise EndpointError(f"endpoint field {part!r} is not key=value")
            k, v = part.split("=", 1)
            fields[k.strip()] = v.strip()
        unknown = set(fields) - {"name", "url", "model", "key", "wire",
                                 "locality", "max_output",
                                 "max_output_source", "evidence",
                                 "auth_scheme", "auth_header", "stream",
                                 "tls_verification"}
        if unknown:
            raise EndpointError(
                f"unknown endpoint field(s) {sorted(unknown)} — refused rather "
                "than ignored, so a typo cannot silently drop a setting")
        maximum = fields.get("max_output", "").strip()
        maximum_source = fields.get("max_output_source", "").strip()
        if bool(maximum) != bool(maximum_source):
            raise EndpointError(
                "max_output and max_output_source must be declared together")
        capability = (ModelOutputCapability(
            maximum if maximum.casefold() == "unknown" else int(maximum),
            maximum_source) if maximum else None)
        out.append(CustomEndpoint(
            name=fields.get("name", "custom"), base_url=fields.get("url", ""),
            model=fields.get("model", ""), api_key=fields.get("key", ""),
            wire=fields.get("wire", "openai"),
            locality=fields.get("locality", "local"),
            auth_scheme=fields.get("auth_scheme", "bearer"),
            auth_header=fields.get("auth_header", ""),
            stream=fields.get("stream", "auto"),
            tls_verification=fields.get("tls_verification", "default"),
            output_capability=capability,
            counts_as_evidence=fields.get("evidence", "").lower()
            in ("1", "true", "yes")))
    return out


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    ep = CustomEndpoint(name="friends_box",
                        base_url="https://gpu.example.net/v1",
                        model="qwen2.5-72b-instruct", api_key="secret-key-xyz",
                        locality="local",
                        output_capability=ModelOutputCapability(
                            32768, "endpoint owner declaration"))

    # 1. URL composition per wire format — the one thing that differs between
    # a self-hosted OpenAI-compatible server and Ollama's native shape.
    oll = CustomEndpoint(name="box2", base_url="http://192.168.1.5:11434",
                         model="qwen2.5", wire="ollama")
    check("the_chat_url_is_composed_for_the_declared_wire_format",
          ep.chat_url == "https://gpu.example.net/v1/chat/completions"
          and oll.chat_url == "http://192.168.1.5:11434/api/chat"
          and CustomEndpoint(name="b3", base_url="https://x.net/v1/chat/completions",
                             model="m").chat_url
          == "https://x.net/v1/chat/completions",
          "an already-complete URL is not doubled")

    # 2. THE EVIDENCE DISTINCTION: a self-hosted box is usable by default and
    # NOT admissible evidence by default. Those are separate facts, and
    # conflating them either blocks a user or corrupts a campaign.
    check("a_self_hosted_endpoint_is_usable_but_not_evidence_by_default",
          ep.locality == "local" and ep.counts_as_evidence is False
          and CustomEndpoint(name="b4", base_url="https://api.x.com/v1",
                             model="m", locality="cloud",
                             counts_as_evidence=True).counts_as_evidence,
          "usable by anyone; citable only when its owner says so")

    # 3. ADAPTER CONTRACT PARITY — a custom endpoint is a provider because it
    # exposes what the resolver calls, not because of any special-casing.
    ad = make_adapter(ep)
    from . import ollama_client
    needed = ("chat", "chat_maxout", "verify", "live_models",
              "output_capability_for", "DEFAULT_MODEL")
    check("a_custom_endpoint_exposes_the_same_contract_as_a_builtin",
          all(hasattr(ad, n) for n in needed)
          and all(hasattr(ollama_client, n) for n in needed)
          and ad.DEFAULT_MODEL == "qwen2.5-72b-instruct",
          "same surface the resolver already calls; no special-casing")

    # 4. REGISTRATION joins the provider table, and a built-in name is REFUSED
    # rather than shadowed — a record naming 'mistral' must mean mistral.
    saved = dict(PROVIDERS)
    try:
        register_endpoint(ep)
        joined = "friends_box" in PROVIDERS
        collided = False
        try:
            register_endpoint(CustomEndpoint(name="mistral",
                                             base_url="https://evil.example/v1",
                                             model="m"))
        except EndpointError:
            collided = True
        removed = unregister_endpoint("friends_box")
        builtin_safe = False
        try:
            unregister_endpoint("mistral")
        except EndpointError:
            builtin_safe = True
        check("registering_joins_the_table_but_cannot_shadow_a_builtin",
              joined and collided and removed and builtin_safe
              and "mistral" in PROVIDERS,
              "a custom endpoint cannot impersonate a sanctioned provider")
    finally:
        PROVIDERS.clear()
        PROVIDERS.update(saved)

    # 5. ADVERSARIAL — a forbidden model cannot ride in on a custom endpoint,
    # and a malformed declaration is refused at construction.
    banned = bad_url = bad_name = False
    try:
        CustomEndpoint(name="x", base_url="https://a.com/v1",
                       model=f"local/{FORBIDDEN_MODELS[0]}")
    except EndpointError:
        banned = True
    try:
        CustomEndpoint(name="x", base_url="gpu.example.net", model="m")
    except EndpointError:
        bad_url = True
    try:
        CustomEndpoint(name="my box!", base_url="https://a.com/v1", model="m")
    except EndpointError:
        bad_name = True
    check("forbidden_models_and_malformed_declarations_are_refused",
          banned and bad_url and bad_name,
          "a custom endpoint is not a way around a model ban")

    # 6. NO CREDENTIAL LEAK: describe() is the record shape and must not
    # carry the key, only whether one is set.
    d = ep.describe()
    check("the_record_shape_records_that_a_key_exists_never_the_key",
          d["has_key"] is True and "secret-key-xyz" not in json.dumps(d)
          and "secret-key-xyz" not in repr(ep)
          and d["counts_as_evidence"] is False,
          "records carry posture, never credentials")

    header_ep = CustomEndpoint(
        name="header_auth", base_url="https://api.example/v1", model="m",
        api_key="header-secret", locality="cloud", auth_scheme="header",
        auth_header="x-api-key")
    resolved_headers = _request_headers(header_ep)
    check("header_auth_uses_runtime_secret_without_serializing_it",
          resolved_headers["x-api-key"] == "header-secret"
          and "header-secret" not in json.dumps(header_ep.describe())
          and "Authorization" not in resolved_headers)

    # 7. ENVIRONMENT CONFIG: deployment without code, and a typo'd field is
    # refused rather than silently dropped.
    parsed = endpoints_from_env(
        "name=box_a,url=https://a.example/v1,model=m1,max_output=8192,"
        "max_output_source=provider docs|"
        "name=box_b,url=http://10.0.0.2:8000/v1,model=m2,wire=openai,"
        "max_output=4096,max_output_source=server config")
    typo = False
    try:
        endpoints_from_env("name=x,url=https://a.com/v1,model=m,keyy=oops")
    except EndpointError:
        typo = True
    check("endpoints_can_be_declared_in_the_environment_and_typos_are_refused",
          len(parsed) == 2 and parsed[0].name == "box_a"
          and parsed[1].base_url == "http://10.0.0.2:8000/v1" and typo,
          "a misspelled field cannot silently drop a setting")

    unknown_capability = make_adapter(CustomEndpoint(
        name="unknown_cap", base_url="http://127.0.0.1:9",
        model="m")).verify()
    check("an_unknown_custom_model_maximum_refuses_before_network_use",
          not unknown_capability["ok"]
          and "unknown_model_output_limit" in unknown_capability["error"])

    # Streaming self-orientation: flexible mode spelling, tolerant SSE
    # parsing across gateway shapes, and auto's proxy-wall retry.
    check("stream_modes_normalize_flexible_spellings",
          _normalize_stream(True) == "stream"
          and _normalize_stream("SSE") == "stream"
          and _normalize_stream("off") == "buffer"
          and _normalize_stream(None) == "auto"
          and CustomEndpoint(
              name="t1", base_url="https://x/v1/chat/completions",
              model="m").stream == "auto")

    refused_stream = False
    try:
        CustomEndpoint(name="t2", base_url="https://x/v1/chat/completions",
                       model="m", stream="sideways")
    except EndpointError:
        refused_stream = True
    check("an_unrecognized_stream_mode_is_refused", refused_stream)

    delta_chunk = {"choices": [{"delta": {"content": "hello "}, }]}
    message_chunk = {"choices": [{"message": {"content": "world"}}]}
    reasoning_chunk = {"choices": [{"delta": {
        "content": "", "reasoning_content": "thinking"}}]}
    finish_chunk = {"choices": [{"delta": {}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 2}}
    parts_a, reason_a, finish_a = _sse_chunk_text(delta_chunk)
    parts_b, _reason_b, _finish_b = _sse_chunk_text(message_chunk)
    parts_c, reason_c, _finish_c = _sse_chunk_text(reasoning_chunk)
    _parts_d, _reason_d, finish_d = _sse_chunk_text(finish_chunk)
    check("sse_parser_accepts_delta_message_and_reasoning_shapes",
          parts_a == ["hello "] and parts_b == ["world"]
          and reason_a == [] and reason_c == ["thinking"]
          and finish_a == "" and finish_d == "stop")

    class _SSEBody:
        def __iter__(self):
            yield b'data: {"choices": [{"delta": {"content": "one"}}]}'
            yield b'data:{"choices": [{"delta": {"content": "two"}}]}'
            yield b': keep-alive comment'
            yield b'event: ping'
            yield b'data: [DONE]'

    class _SSEResponse:
        def __init__(self, body):
            self._body = body
        def __iter__(self):
            return iter(self._body)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    lines = list(_sse_lines(_SSEBody()))
    check("sse_lines_skip_comments_and_accept_spacing_variants",
          lines == ['{"choices": [{"delta": {"content": "one"}}]}',
                    '{"choices": [{"delta": {"content": "two"}}]}',
                    '[DONE]'])

    passed = sum(1 for t in results if t["passed"])
    return {"record_type": "custom_endpoint_contract_test/v2",
            "scope": "offline_contract_only",
            "provider_integration_proven": False,
            "tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
