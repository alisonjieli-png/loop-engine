# Runtime settings and model tiers

Loop Engine can load one typed settings object for loops, search, model
providers, model tiers, operating permissions, and saved run history. A YAML
file is optional. Environment variables and typed request objects can override
specific values.

## Create and inspect settings

Create the user settings file:

```bash
loop-engine settings init
```

The default path is `~/.config/loop-engine/settings.yaml`. You can select a
different path:

```bash
loop-engine settings init --settings-file ./loop-engine.yaml
```

Show the resolved settings without calling a provider:

```bash
loop-engine settings show
loop-engine settings check
```

`settings check` validates provider IDs and route names. It reports which
routes are usable in each model tier. It makes zero network calls.

## Precedence

Settings resolve in this order:

1. Built-in defaults.
2. One YAML file.
3. Supported environment overrides.
4. A typed request object for one loop or model task.

The loader checks these YAML locations in order:

1. A path passed with `--settings-file`.
2. The path in `LOOP_ENGINE_SETTINGS`.
3. `.loop-engine.yaml` in the current directory.
4. `~/.config/loop-engine/settings.yaml`.

Unknown keys cause an error. A spelling mistake does not silently become an
unused setting.

## Settings sections

| Section | Responsibility |
|---|---|
| `loop` | Default step profile, run modes, delegation modes, depth, loop condition, and exit condition. |
| `search` | Retrieval mode, lexical backend, vector backend, and result limit. |
| `models.providers` | Built-in or custom provider declarations and credential environment variable names. |
| `models.tiers` | Ordered model routes and resource limits for each thinking power. |
| `models.escalation` | Typed failures that may move a request to a larger tier. |
| `operating` | Network, model, construction, default effort, optimization, and resource policy. |
| `history` | Run History directory and default save behavior. |

The complete example is
[`loop-engine.settings.example.yaml`](../../loop-engine.settings.example.yaml).

## Loop effort and model thinking power

Loop effort and model thinking power are different settings.

| Setting | Values | What it changes |
|---|---|---|
| Loop effort | `light`, `standard`, `deep`, `max` | Iterations, intelligence retrieval, and work budget. |
| Model thinking power | `small`, `medium`, `high`, `max`, `specialized` | Which configured model routes a model-using step may try. |

A deterministic-only loop does not carry model thinking power. A hybrid or
non-deterministic loop must carry a valid model thinking power.

`specialized` is a separate route family. It is not larger than `max`, and it
is not part of automatic escalation. Use it for a task-specific model that has
a declared capability.

## Bounded escalation

Automatic escalation is off by default. When enabled, it follows the declared
order and maximum number of tier changes. The default escalation trigger is a
failed output validation after the routes in the current tier are exhausted.
You can configure other typed triggers explicitly.

Authentication errors, rate limits, provider outages, and timeouts use
provider failover within the same tier. They do not increase thinking power by
default. A stronger model cannot repair a rejected credential or provider
outage. Provider failover and model tier escalation are recorded as separate
decisions.

Each tier also declares:

- ordered route names;
- maximum provider attempts;
- timeout per attempt.

The provider or endpoint capability record supplies the exact maximum output
size. The tier does not reduce it. A request can add a total usage ceiling for
the complete run. The gateway stops before another tier after that ceiling is
exhausted, but each physical generation still requests the model's declared
maximum output and lets the model stop naturally.

## Use typed settings in Python

```python
from loop_engine import (
    Loop,
    LoopConfigOverride,
    ModelPolicyRequest,
    ModelTask,
    load_runtime_settings,
)

loaded = load_runtime_settings()
settings = loaded.settings

loop_config = settings.loop_config(LoopConfigOverride(
    allowable_modes=("hybrid",),
    preferred_modes=("hybrid",),
    llm_thinking_power="high",
))
loop = Loop("review a release decision", loop_config)

task = ModelTask(
    prompt="Return one JSON object with decision and reason.",
    policy=ModelPolicyRequest(
        thinking_power="high",
        allow_escalation=False,
        max_total_tokens=4000,
    ),
    output_contract='{"decision":"continue|rollback","reason":"..."}',
)
gateway = settings.build_gateway()
request = settings.model_request(task)
```

`ModelTask`, `ModelPolicyRequest`, and `LoopConfigOverride` keep optional values
inside typed objects. Callers do not need to pass the same long list of
parameters through several functions.

## Credential safety

YAML contains names such as `MISTRAL_API_KEY`. It does not contain the key
value. Custom endpoints also use `credential_env`.

Resolved settings summaries show `env:MISTRAL_API_KEY`. They never serialize
the value read from that environment variable.

## Current limit

The default route tiers are operator hints, not a measured quality ranking.
Benchmark results may later justify a different order. Change the YAML without
changing the loop runtime.
