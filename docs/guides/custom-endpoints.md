# Custom endpoints

Point the loop at any inference server you control or have access to — vLLM,
LM Studio, llama.cpp's server, text-generation-webui, LiteLLM, an internal
gateway, or a friend's GPU box.

Almost all of them speak the same wire format (`POST /v1/chat/completions`,
OpenAI-shaped), so this is **one parameterised adapter**, not an adapter per
server.

## In code

```python
from loop_engine import configure
from loop_engine.static_architecture.custom_endpoint import CustomEndpoint

access = configure(endpoints=[CustomEndpoint(
    name="friends_box",
    base_url="https://gpu.example.net/v1",
    model="qwen2.5-72b-instruct",
    api_key="...",          # omit if the server needs none
)])
```

Ollama's native shape works too:

```python
CustomEndpoint(name="my_ollama", base_url="http://192.168.1.5:11434",
               model="qwen2.5:7b", wire="ollama")
```

## Without touching code

```bash
export LOOP_ENGINE_ENDPOINTS="name=friends_box,url=https://gpu.example.net/v1,model=qwen2.5-72b-instruct,key=..."
```

Multiple endpoints separated by `|`:

```bash
export LOOP_ENGINE_ENDPOINTS="name=box_a,url=https://a.example/v1,model=m1|name=box_b,url=http://10.0.0.2:8000/v1,model=m2"
```

| Field | Required | Default | Meaning |
|---|---|---|---|
| `name` | yes | — | becomes the provider key; appears in receipts |
| `url` | yes | — | base URL, `http(s)://` |
| `model` | yes | — | the model to request |
| `key` | no | none | bearer token if the server wants one |
| `wire` | no | `openai` | `openai` or `ollama` |
| `locality` | no | `local` | `local` or `cloud` |
| `max_output` | no | 4096 | output ceiling |
| `evidence` | no | `false` | see below |

**A misspelled field is refused, not ignored.** `keyy=...` raises rather than
silently dropping your credential and leaving you to debug an auth failure.

## Two protections worth knowing about

**A custom endpoint cannot shadow a built-in provider.** Registering one named
`mistral` is refused. A receipt naming a provider has to mean that provider,
or the receipt is worthless.

**Your configuration decides who gets called.** `advice_function(access)`
routes to the providers that access verified. Configuring only your own server
means only your own server is contacted — this was a real defect once, where a
self-hosted configuration silently billed a different provider entirely.

## Self-hosted servers and evidence

```python
CustomEndpoint(..., counts_as_evidence=False)   # the default
```

A local endpoint is **usable by anyone** — that is not restricted. But
`counts_as_evidence` defaults to `False`, because a measurement campaign needs
token counts another machine can reproduce, and a box only you can reach does
not satisfy that.

These are separate facts, and conflating them either blocks you from using your
own hardware or quietly corrupts a benchmark. Set it `True` deliberately if you
own the box and know what the claim rests on.

## Credentials

`describe()` is the receipt shape, and it records `has_key: true` — never the
key itself. That is enforced by a test, and a conformance gate scans code and
evidence files for secret-shaped literals.

## Failure

An unreachable endpoint returns a reason, never an exception:

```python
{'provider': 'friends_box', 'ok': False,
 'error': 'URLError: [Errno 111] Connection refused', 'prompt_tokens': 0}
```

That is what lets failover move past it to the next provider instead of
crashing your run.
