# Configurable decision endpoints and harness tools

Kind: operating guide for client-side decision adapters.

Jev, Circuit and other compatible endpoints are optional decision providers
behind the existing model gateway. Users or providers operate those endpoints.
Loop Engine does not download, launch or manage their models or interfaces. Direct
Python calls avoid a native harness process. A host-launched Model Context
Protocol process exposes the same operation as a harness tool. Neither path
executes the chosen action or independently accepts a task outcome.

Local checks exercise real gateway and protocol code against explicit provider
fixtures over loopback HTTP. No live TypeSafe or Circuit model has been
qualified here. The shared wire mapping follows the
[provider reference](https://docs.typesafe.ai/api).

## Prepare the local key and configuration

Install from an approved checkout and inspect the command:

```bash
python -m pip install '.[serving]'
loop-engine decisions --help
```

Store the TypeSafe key privately. Supply it to the decision process as
`TYPESAFE_API_KEY`, not as a tool argument or website input. A temporary Bash
session can prompt without echoing the value or putting it in command history:

```bash
read -r -s -p 'TypeSafe key: ' TYPESAFE_API_KEY
export TYPESAFE_API_KEY
```

Close the shell or run `unset TYPESAFE_API_KEY` afterward. The operating-system
account can still inspect its process environment; this is not isolation from
an unrestricted local shell.

Save this non-secret host configuration as a local JSON file:

```json
{
  "record_type": "decision_host_configuration/v2",
  "engines": [{
    "name": "typesafe",
    "engine": "jev",
    "settings": {
      "record_type": "jev_configuration/v1",
      "model": "jev-1.13.0",
      "credential_ref": "env:TYPESAFE_API_KEY",
      "allow_network": false,
      "allow_model_calls": false
    }
  }],
  "route_names": ["typesafe"],
  "allow_failover": false,
  "maximum_model_calls": 5,
  "timeout_seconds": 20
}
```

The model is pinned deliberately. Recheck the supported exact version before
a live trial. Five is an example session allowance, not a product default.
Inspect without resolving a key or calling a provider:

```bash
loop-engine decisions inspect --config /absolute/path/decisions.json
```

Expected: `decision_tool_capabilities/v1`, zero calls used and disabled network
and model authority. Set both authority flags to true only after approving the
allowance and the context that may leave the machine.

## Use an existing Circuit or compatible endpoint

Replace the `engines` entry and its matching `route_names` with the endpoint
you already operate or have access to. This entry connects to an existing local
Circuit service; it does not start that service:

```json
{
  "name": "local-circuit",
  "engine": "circuit",
  "settings": {
    "record_type": "system_one_configuration/v1",
    "model": "lora:circuit-8b",
    "endpoint": "http://127.0.0.1:8901/v1/systemone",
    "credential_ref": "env:CIRCUIT_API_KEY",
    "locality": "local",
    "provenance": "open_weights",
    "allow_loopback_http": true,
    "allow_network": false,
    "allow_model_calls": false,
    "maximum_request_bytes": 262144,
    "maximum_response_bytes": 1048576
  }
}
```

The `model` must match the endpoint's actual response identity, not an assumed
display name. The reviewed Circuit server reports `lora:` followed by the
model-directory name; its request field does not choose loaded weights.
An unset upstream model can return `fake`, which the adapter refuses.

Use `engine: system_one` for another endpoint implementing the same Choice,
Score and Noul request and response contract. HTTPS is required for remote
endpoints. Numeric loopback HTTP needs its own explicit setting. Protocol
and endpoint placement are separate: declare `local`, `organization` or `cloud`
in `locality`. A loopback endpoint cannot claim cloud placement. Declare provenance as
`open_weights`, `vendor_foundation` or `custom_trained` from the provider's
documentation. This remains a host declaration, not independent attestation.
For `custom_trained`, also supply the SHA-256 `provenance_digest` of its training
record, as required by the existing model ontology.
Authentication uses a bearer credential resolved from the named environment variable. An
endpoint with a different authentication or wire protocol needs a separately
tested adapter. An OpenAI-compatible text endpoint alone is not a typed-decision
endpoint; existing text-model adapters remain separate.

For several configured engines, give each a unique name and select an ordered
list such as `route_names: [local-circuit, typesafe]`. Without
`allow_failover: true`, only the first selected route may run. Each endpoint
also requires its own model and network authority. Authentication failure
does not trigger automatic cross-provider fallback. Different origins cannot
share one configured credential reference.

No Loop Engine-specific server extension or model-launch command is required.
The optional `deployment_revision` is an operator-supplied SHA-256 identity,
not remote attestation. Request byte limits protect transport; they do not
establish a token capacity or prove complete context was used. Circuit's
reviewed implementation may truncate long input. Its operator should reject
oversize input or keep that limitation visible during qualification.
See the [source review](../research/CIRCUIT-DECISION-ENGINE-REVIEW-2026-09-19.md).

## Direct invocation

Save this example request as a separate local JSON file:

```json
{
  "record_type": "decision_batch_request/v1",
  "state": {
    "objective": "Choose a permitted continuation",
    "observation": "The candidate runs, but one required test failed."
  },
  "questions": [{
    "question_id": "continuation",
    "kind": "choice",
    "instructions": "Which declared next action fits this observation?",
    "choices": {
      "inspect_failure": "Inspect the failed test and its evidence",
      "request_information": "Required user information is missing",
      "none_apply": "The declared alternatives do not fit"
    }
  }]
}
```

```bash
loop-engine decisions evaluate --config /absolute/path/decisions.json --request /absolute/path/question.json
```

Missing authority or credentials refuse without a synthetic answer. A successful
authorized call returns `decision_batch_result/v1` and `task_accepted: false`.
Permissions and action contracts still apply before executing its selection.

Python callers use `DecisionBatchRequest` and
`ModelExecutionSession.invoke_decisions(request, owning_loop)`. This shares
the session's cumulative physical-call allowance. An occupied session refuses
concurrent or nested use instead of oversubscribing authority. A host integrating
an inner harness tool must allocate its session budget explicitly.

## Native harness tool

The standard-I/O server command is:

```bash
loop-engine decisions serve --config /absolute/path/decisions.json
```

It exposes `decision_capabilities` and `decision_evaluate`. Standard-I/O access
is controlled by the launching operating-system account. This is not a public
unauthenticated HTTP endpoint. Keep the process alive for the allocated session.
Restarting creates a new session and requires renewed host authority; this
command cannot enforce an outer-task ceiling across arbitrary relaunches.

### Codex

The installed command interface was checked with `codex-cli 0.155.1`.
Run these registration commands only after approving changes to your local
client configuration:

```bash
codex mcp add loop-decisions -- loop-engine decisions serve --config /absolute/path/decisions.json
codex mcp add baltor --url https://YOUR_SERVICE_HOST/mcp --bearer-token-env-var BALTOR_SERVICE_TOKEN
```

The second command connects the intelligence service, using a separate scoped
service token. Do not substitute the Jev key. Reconnect and inspect the tool
inventory. Registration alone does not prove native tool use.
[Official connection documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

The entry name `baltor` and the variable `BALTOR_SERVICE_TOKEN` match the
settings that the Connect page of the website offers. Both names exist only on
the customer's machine. The service does not read them. An earlier version of
this guide used the entry name `loop-intelligence` and the variable
`LOOP_ENGINE_ACCESS_TOKEN`. They were aligned with the website on September
20, 2026.

### OpenCode

The inspected local executable is version 1.17.9. Its documented configuration
uses entries directly under `mcp`. A local decision-tool entry is:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {"loop-decisions": {
    "type": "local",
    "command": ["loop-engine", "decisions", "serve", "--config", "/absolute/path/decisions.json"],
    "enabled": true
  }}
}
```

The process inherits the private environment of the launching account; do not
put the provider key in this file. Inspect `opencode mcp list` after deliberate
client configuration. Native tool selection and a live decision still require
separate qualification. [OpenCode connection documentation](https://opencode.ai/docs/mcp-servers/).

Version 2 nests servers under `mcp.servers`. Match the installed release rather
than combining the two shapes. For the version 2 header-authenticated
intelligence service:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {"servers": {"baltor": {
    "type": "remote",
    "url": "https://YOUR_SERVICE_HOST/mcp",
    "oauth": false,
    "protocol": "legacy",
    "headers": {"Authorization": "Bearer {env:BALTOR_SERVICE_TOKEN}"}
  }}}
}
```

Use the installed release's local-server configuration to launch the decision
command above. The `legacy` setting matches the service's currently supported
protocol, not every historical client. A fork of OpenCode is not required.
[OpenCode version 2 configuration](https://opencode.ai/v2/docs/mcp-servers).

## Judgment, recovery and qualification

`choice` returns a label and distribution. `score` returns an ordered rubric
position and distribution. `boolean_probability` maps to Jev's `noul` result,
without inventing a confidence field. Admission refuses missing questions,
unknown labels, nonfinite values, wrong model identity, inconsistent scores
and changed rubric identities.

Confidence is not a guarantee of correctness. Measure downstream outcomes,
decision errors, calibration and abstention on frozen tasks. Prompt variants
remain candidate Context Intelligence until independently reviewed.

Each adapter makes one HTTP attempt per invocation. It does not retry
automatically or silently change providers. Python callers can declare ordered
gateway alternatives with explicit failover authority. Unknown usage remains
unknown. Byte limits and response deadlines are not token ceilings; a supplied
strict token ceiling refuses until a suitable bound is qualified.

Qualify each supported configuration with a real key only after authorization:
inspect without calls, run one known request, call through the actual harness,
exhaust the allowance, test provider failure, and compare direct and harness
paths against suitable alternatives. The result qualifies that population and
configuration, not universal Jev superiority.
