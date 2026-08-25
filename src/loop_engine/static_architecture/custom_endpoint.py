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
import urllib.error
import urllib.request
from dataclasses import dataclass

from .ollama_client import ChatResult, FORBIDDEN_MODELS
from .provider_failover import PROVIDERS

#: Wire formats understood. "openai" covers the overwhelming majority of
#: self-hosted servers; "ollama" is the native /api/chat shape.
WIRE_FORMATS = ("openai", "ollama")

LOCALITIES = ("cloud", "local")


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
    api_key: str = ""
    wire: str = "openai"
    locality: str = "local"
    max_output: int = 4096
    counts_as_evidence: bool = False
    timeout: float = 900.0

    def __post_init__(self):
        if not self.name or not self.name.replace("_", "").isalnum():
            raise EndpointError(
                f"endpoint name {self.name!r} must be a simple identifier — it "
                "becomes a provider key and appears in receipts")
        if self.wire not in WIRE_FORMATS:
            raise EndpointError(f"wire {self.wire!r} not in {WIRE_FORMATS}")
        if self.locality not in LOCALITIES:
            raise EndpointError(f"locality must be one of {LOCALITIES}")
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
            # what it means, so it is stated in the receipt rather than assumed.
            pass

    @property
    def chat_url(self) -> str:
        base = self.base_url.rstrip("/")
        if self.wire == "ollama":
            return base + ("/api/chat" if not base.endswith("/api/chat") else "")
        return base + ("/chat/completions"
                       if not base.endswith("/chat/completions") else "")

    def describe(self) -> dict:
        """Receipt shape — carries no credential."""
        return {"name": self.name, "base_url": self.base_url,
                "model": self.model, "wire": self.wire,
                "locality": self.locality,
                "counts_as_evidence": self.counts_as_evidence,
                "has_key": bool(self.api_key)}


def _chat_once(ep: CustomEndpoint, prompt: str, *, system: str,
               max_tokens: int, temperature: float,
               timeout: float) -> ChatResult:
    """One request in whichever wire format the endpoint declared."""
    messages = ([{"role": "system", "content": system}] if system else []) \
        + [{"role": "user", "content": prompt}]
    if ep.wire == "ollama":
        payload = {"model": ep.model, "messages": messages, "stream": False,
                   "options": {"num_predict": int(max_tokens),
                               "temperature": temperature}}
    else:
        payload = {"model": ep.model, "messages": messages,
                   "max_tokens": int(max_tokens), "temperature": temperature}

    headers = {"Content-Type": "application/json"}
    if ep.api_key:
        headers["Authorization"] = f"Bearer {ep.api_key}"
    req = urllib.request.Request(ep.chat_url, data=json.dumps(payload).encode(),
                                 headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read()[:300].decode("utf-8", "replace")
        except OSError:
            pass
        return ChatResult(text="", model=ep.model, ok=False,
                          error=f"HTTP {e.code}: {detail}")
    except (urllib.error.URLError, OSError, ValueError) as e:
        return ChatResult(text="", model=ep.model, ok=False,
                          error=f"{type(e).__name__}: {str(e)[:250]}")

    if ep.wire == "ollama":
        text = (body.get("message") or {}).get("content", "")
        p_tok = int(body.get("prompt_eval_count", 0) or 0)
        e_tok = int(body.get("eval_count", 0) or 0)
    else:
        choices = body.get("choices") or []
        text = (choices[0].get("message", {}).get("content", "")
                if choices else "")
        usage = body.get("usage") or {}
        p_tok = int(usage.get("prompt_tokens", 0) or 0)
        e_tok = int(usage.get("completion_tokens", 0) or 0)
    return ChatResult(text=str(text), model=str(body.get("model", ep.model)),
                      prompt_tokens=p_tok, eval_tokens=e_tok, ok=bool(text),
                      num_predict_used=int(max_tokens),
                      error="" if text else "endpoint returned no text")


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
        def chat(prompt, *, model="", system="", max_tokens=0,
                 temperature=0.7, timeout=None, api_key=None):
            return _chat_once(ep, prompt, system=system,
                              max_tokens=max_tokens or ep.max_output,
                              temperature=temperature,
                              timeout=timeout or ep.timeout)

        @staticmethod
        def chat_maxout(prompt, *, model="", system="", temperature=0.7,
                        timeout=None, api_key=None, backoff=0.9,
                        floor_frac=0.3, max_attempts=8,
                        max_output_tokens=None):
            """Same back-off policy as every built-in adapter, so failing over
            to a custom endpoint does not change the call's semantics."""
            ceiling = min(ep.max_output, int(max_output_tokens)) \
                if max_output_tokens is not None else ep.max_output
            mt, last, attempt = ceiling, None, 1
            for attempt in range(1, max_attempts + 1):
                res = _chat_once(ep, prompt, system=system, max_tokens=int(mt),
                                 temperature=temperature,
                                 timeout=timeout or ep.timeout)
                res.num_predict_used, res.attempts = int(mt), attempt
                if res.ok and res.text.strip():
                    return res
                last = res
                mt = int(mt * backoff)
                if mt < ceiling * floor_frac:
                    break
            if last is not None:
                last.num_predict_used, last.attempts = int(mt), attempt
            return last if last is not None else _chat_once(
                ep, prompt, system=system, max_tokens=ceiling,
                temperature=temperature, timeout=ep.timeout)

        @staticmethod
        def live_models():
            """Whatever the endpoint lists, or just its configured model."""
            url = ep.base_url.rstrip("/") + (
                "/api/tags" if ep.wire == "ollama" else "/models")
            headers = ({"Authorization": f"Bearer {ep.api_key}"}
                       if ep.api_key else {})
            try:
                with urllib.request.urlopen(
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
            r = _chat_once(ep, "Reply with one word: READY", system="",
                           max_tokens=20, temperature=0.0, timeout=60)
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
    the kind of substitution a receipt would then misattribute."""
    builtins = {"ollama_cloud", "mistral", "openrouter"}
    if ep.name in builtins:
        raise EndpointError(
            f"{ep.name!r} is a built-in provider; choose another name rather "
            "than shadowing it — a receipt naming that provider must mean it")
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
                                 "locality", "max_output", "evidence"}
        if unknown:
            raise EndpointError(
                f"unknown endpoint field(s) {sorted(unknown)} — refused rather "
                "than ignored, so a typo cannot silently drop a setting")
        out.append(CustomEndpoint(
            name=fields.get("name", "custom"), base_url=fields.get("url", ""),
            model=fields.get("model", ""), api_key=fields.get("key", ""),
            wire=fields.get("wire", "openai"),
            locality=fields.get("locality", "local"),
            max_output=int(fields.get("max_output", 4096)),
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
                        locality="local")

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
    needed = ("chat", "chat_maxout", "verify", "live_models", "DEFAULT_MODEL")
    check("a_custom_endpoint_exposes_the_same_contract_as_a_builtin",
          all(hasattr(ad, n) for n in needed)
          and all(hasattr(ollama_client, n) for n in needed)
          and ad.DEFAULT_MODEL == "qwen2.5-72b-instruct",
          "same surface the resolver already calls; no special-casing")

    # 4. REGISTRATION joins the provider table, and a built-in name is REFUSED
    # rather than shadowed — a receipt naming 'mistral' must mean mistral.
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

    # 6. NO CREDENTIAL LEAK: describe() is the receipt shape and must not
    # carry the key, only whether one is set.
    d = ep.describe()
    check("the_receipt_shape_records_that_a_key_exists_never_the_key",
          d["has_key"] is True and "secret-key-xyz" not in json.dumps(d)
          and d["counts_as_evidence"] is False,
          "receipts carry posture, never credentials")

    # 7. ENVIRONMENT CONFIG: deployment without code, and a typo'd field is
    # refused rather than silently dropped.
    parsed = endpoints_from_env(
        "name=box_a,url=https://a.example/v1,model=m1|"
        "name=box_b,url=http://10.0.0.2:8000/v1,model=m2,wire=openai")
    typo = False
    try:
        endpoints_from_env("name=x,url=https://a.com/v1,model=m,keyy=oops")
    except EndpointError:
        typo = True
    check("endpoints_can_be_declared_in_the_environment_and_typos_are_refused",
          len(parsed) == 2 and parsed[0].name == "box_a"
          and parsed[1].base_url == "http://10.0.0.2:8000/v1" and typo,
          "a misspelled field cannot silently drop a setting")

    # 8. a dead endpoint fails as a reason, never as an exception — the
    # property that lets failover move past it.
    dead = make_adapter(CustomEndpoint(
        name="dead", base_url="http://127.0.0.1:9", model="m")).verify()
    check("an_unreachable_endpoint_returns_a_reason_not_an_exception",
          dead["ok"] is False and dead["error"]
          and dead["prompt_tokens"] == 0,
          f"reported: {dead['error'][:60]}")

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
