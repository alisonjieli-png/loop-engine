# Providers and keys

The library runs deterministic loops with no provider at all. This guide is
about the other two modes, which need one.

## One call from keys to capability

```python
from loop_engine import configure

access = configure(openrouter_key="...")     # or ollama_key= / mistral_key=
                                             # or nothing: reads the environment
print(access.explain())
```

```text
Working providers: mistral
Models reachable: 56
  ollama_cloud: HTTP 429 ...  -> rate or usage limit; this key works but is currently capped
  openrouter: HTTP 401 ...    -> the key was rejected; check it is current
Modes available: deterministic, hybrid, non_deterministic
```

Note that the two failures get *different* advice. A capped key and a rejected
key need opposite actions from you, and a setup message that blurs them wastes
your time.

## Verified by use

A provider appears as working only because it answered a real call. A key in an
environment variable is not a working provider: it might be expired, capped,
or scoped wrong, and every one of those looks identical until something tries
to use it.

This is why `configure()` costs a few tokens: it is buying you certainty at
setup instead of a mystery mid-run.

## Which modes you can run

| Mode | Needs a provider | What it does |
|---|---|---|
| `deterministic` | no | never calls a model, ever |
| `hybrid` | yes | escalates the step that needs judgement |
| `non_deterministic` | yes | leads with the model |

```python
access.can_run("deterministic")       # always True
access.can_run("hybrid")              # True only if something answered
access.modes_available()
```

With nothing reachable, `advice_function()` returns **`None`** rather than a
callable that fails later:

```python
advise = advice_function(access)
if advise is None:
    ...            # choose a deterministic loop deliberately
```

That is the whole design: a setup problem should surface at setup.

## Supported providers

| Provider | Environment variable | Notes |
|---|---|---|
| OpenRouter | `OPENROUTER_API_KEY` | one key, hundreds of models |
| Ollama Cloud | `OLLAMA_API_KEY` | hosted Ollama |
| Mistral | `MISTRAL_API_KEY` | |
| Your own server | `LOOP_ENGINE_ENDPOINTS` | see [custom endpoints](custom-endpoints.md) |

## Discovery costs zero model calls

Models are sorted into three roles from each vendor's **published catalog** :
price per output token, context length, declared reasoning and tool support:

| Role | Meaning |
|---|---|
| `decide_label` | cheap and fast: classification, routing, scoring |
| `generate` | the workhorse |
| `reason` | declared reasoning models, or the expensive tier |

```python
roster = access.roster
roster.best("decide_label")           # cheapest model that can route a decision
roster.for_role("reason")             # everything reasoning-capable, cheapest first
```

**These are declared facts, not measured ones.** Every entry carries
`basis="declared", measured=False`, because a vendor's price list tells you what
something costs, not how well it will do your job. Treat a role as a routing
hint. If you want a quality ranking, measure one.

An unpriced model is *not* tiered by its name. Name heuristics are not
evidence, so it lands in the general role: the assumption that fails most
safely.

## Failover

```python
from loop_engine import call_with_failover

r = call_with_failover("Which estimator family for tabular data?")
r.ok            # did anyone answer?
r.provider      # who did
r.attempts      # everyone tried, refusals included
r.usage_record()
```

Providers are tried in order; the first success wins and the rest are never
contacted. Every attempt is recorded, because *"the third provider answered"*
is a materially different run log from *"a model answered"*, and six months
later that difference is the thing you need.

**If every provider refuses, that is a failure and stays one.** The library
never quietly returns a non-model answer and reports it as a model result. This
was worth building deliberately: a model arm that silently never reached a
model produces numbers that look like evidence and are not.

## Cost attribution

Token counts are provider-reported: never estimated: and always travel with
the provider that produced them:

```python
text, usage = advise("...")
usage["provider"]         # 'mistral'
usage["prompt_tokens"]    # 66
usage["eval_tokens"]      # 337
usage["providers_tried"]  # ['ollama_cloud', 'mistral']
```

A count with nothing attached cannot be checked against a bill later, which
makes it decoration rather than accounting.

## Your configuration decides who gets called

`advice_function(access)` routes to the providers *that access verified*, not
to a global default order.

This was a real defect, found by testing against a live stand-in server:
configuring only a self-hosted box produced a callable that contacted: and
billed: a completely different provider, while the configured server was never
reached. If you configure a provider, that is who gets called.

## Forbidden models

A model ban is a policy fact, not a provider fact: it holds on every provider,
including a custom endpoint. Adding a second provider is not a route around it.
