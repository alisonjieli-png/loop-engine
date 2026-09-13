# Custom endpoints

Point the loop at any inference server you control or have access to: vLLM,
LM Studio, llama.cpp's server, text-generation-webui, LiteLLM, an internal
gateway, or a friend's GPU box.

Almost all of them speak the same wire format (`POST /v1/chat/completions`,
OpenAI-shaped), so this is **one parameterised adapter**, not an adapter per
server.

## In code

```python
from loop_engine import configure
from loop_engine.core.custom_endpoint import CustomEndpoint
from loop_engine.core.model_capabilities import (
    ModelOutputCapability,
)

access = configure(endpoints=[CustomEndpoint(
    name="friends_box",
    base_url="https://gpu.example.net/v1",
    model="qwen2.5-72b-instruct",
    api_key="...",          # omit if the server needs none
    output_capability=ModelOutputCapability(
        65536,
        "provider documentation dated 2026-08-25",
    ),
)])
```

Ollama's native shape works too:

```python
CustomEndpoint(
    name="my_ollama",
    base_url="http://192.168.1.5:11434",
    model="qwen2.5:7b",
    wire="ollama",
    output_capability=ModelOutputCapability(
        32768,
        "local server configuration checked 2026-08-25",
    ),
)
```

## Without touching code

```bash
export LOOP_ENGINE_ENDPOINTS="name=friends_box,url=https://gpu.example.net/v1,model=qwen2.5-72b-instruct,key=...,max_output=65536,max_output_source=provider documentation dated 2026-08-25"
```

Multiple endpoints separated by `|`:

```bash
export LOOP_ENGINE_ENDPOINTS="name=box_a,url=https://a.example/v1,model=m1,max_output=65536,max_output_source=box_a provider documentation|name=box_b,url=http://10.0.0.2:8000/v1,model=m2,max_output=32768,max_output_source=box_b server configuration"
```

| Field | Required | Default | Meaning |
|---|---|---|---|
| `name` | yes | none | becomes the provider key; appears in logs |
| `url` | yes | none | base URL, `http(s)://` |
| `model` | yes | none | the model to request |
| `key` | no | none | bearer token if the server wants one |
| `key_env` | no | none | the variable to read the key from, instead of `key`; an unset variable refuses before any request is sent |
| `wire` | no | `openai` | `openai` or `ollama` |
| `locality` | no | `local` | `local`, `organization`, or `cloud`; descriptive only, every endpoint is a URL |
| `max_output` | yes for generation | none | provider-declared maximum output tokens |
| `max_output_source` | yes with `max_output` | none | one-line source for that exact maximum |
| `evidence` | no | `false` | see below |
| `auth_scheme` | no | `bearer` | `bearer`, `header` (the key in the header named by `auth_header`), or `none` |
| `auth_header` | with `header` | none | the header that carries the key under the `header` scheme |
| `stream` | no | `auto` | `auto` (buffered first, streamed after a proxy timeout, the mode that delivered remembered for the process), `stream`, or `buffer` |
| `think` | no | `default` | `default` (`think: false` on the Ollama wire, nothing on the OpenAI wire), `off`, `on`, or `model` (send nothing; the model's own default) |
| `tls_verification` | no | `default` | `default`, `ca_file`, or `skip`; see the providers guide |
| `tls_ca_file` | with `ca_file` | none | the private authority to trust for this endpoint |

The `url` may name the bare root, the API prefix, or the chat path
(`https://ollama.com`, `https://ollama.com/api`, `https://ollama.com/api/chat`
compose the same `/api/chat` and `/api/tags`; `https://host/v1` and
`https://host/v1/chat/completions` compose the same `/v1/chat/completions` and
`/v1/models`). On the Ollama wire the stream is newline-delimited JSON, as
Ollama sends it; on the OpenAI wire it is server-sent events, and a stream cut
before its stop reason or `[DONE]` is reported as incomplete, never as an
answer.

**A misspelled field is refused, not ignored.** `keyy=...` raises rather than
silently dropping your credential and leaving you to debug an auth failure.

Loop Engine does not invent a smaller output limit. It requests the exact
maximum declared for the selected model and endpoint, then lets the model stop
naturally. If that maximum is unknown, generation is refused until you add a
source-backed `ModelOutputCapability`. `max_output` and `max_output_source`
must be set together.

## Two protections worth knowing about

**A custom endpoint cannot shadow a built-in provider.** Registering one named
`mistral` is refused. A log naming a provider has to mean that provider, or it
cannot be trusted.

**Your configuration decides who gets called.** `advice_function(access)`
routes to the providers that access verified. Configuring only your own server
means only your own server is contacted: this was a real defect once, where a
self-hosted configuration silently billed a different provider entirely.

## Self-hosted servers and evidence

```python
CustomEndpoint(..., counts_as_evidence=False)   # the default
```

A local endpoint is **usable by anyone**: that is not restricted. But
`counts_as_evidence` defaults to `False`, because a measurement campaign needs
token counts another machine can reproduce, and a box only you can reach does
not satisfy that.

These are separate facts, and conflating them either blocks you from using your
own hardware or quietly corrupts a benchmark. Set it `True` deliberately if you
own the box and know what the claim rests on.

## Credentials

`describe()` is the report shape, and it records `has_key: true`, never the
key itself. That is enforced by a test, and a conformance gate scans code and
evidence files for secret-shaped literals.

## Failure

An unreachable endpoint returns a reason, never an exception:

```python
{'provider': 'friends_box', 'ok': False,
 'error': 'URLError: <urlopen error [Errno 111] Connection refused>',
 'prompt_tokens': 0}
```

A refusal carries its status first (`HTTP 429 (retry after 120s): ...`), so
the gateway classifies by the status before any word in the body; the wait a
provider states in `Retry-After` is on the result as `retry_after_seconds`
(None when unstated). A connection that ends inside the body is
`incomplete_response`; a login page or proxy notice that is not JSON is
`invalid_response_body`; a refusal inside a 200 body is classified by its
words. The configured key and any bearer token are redacted from error text
before it reaches a record.

That is what lets failover move past it to the next provider instead of
crashing your run.
