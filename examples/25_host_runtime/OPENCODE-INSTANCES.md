# Optional OpenCode instances

This source-checkout experiment can run an OpenCode instance for a governed
Loop responsibility. It preserves native execution and the three existing
Loop modes. It does not enable the quarantined raw-host adapter or install
anything into your personal OpenCode configuration.

Read the [architecture and alternatives](../../docs/research/HARNESSES-AS-OPTIONAL-LOOP-EXECUTORS-2026-09-06.md)
for the complete classification tree, tested scope, and comparison rules.

## Configuration boundary

`CoreBundle` pins mandatory resources and upper policy limits. A separate
`InstanceGrant` authorizes optional resources for one activation and step.
`InstanceSelection` binds a proposal to both digests. The compiler checks the
grant before loading selected bodies. New task context can have a different
grant without changing the core bundle.

The native path is lazy:

```python
from opencode_instance import InstanceSelection, run_optional

result = run_optional(
    InstanceSelection(),
    native=existing_native_operation,
    prepare_opencode=prepare_selected_instance,
    invoke_opencode=invoke_selected_instance,
)
```

With `backend="native"`, neither harness callback is called. For OpenCode,
the caller supplies a compiled instance and explicit bridge authority.
These modules live beside the example, not at the installed package root.
They are not a new `solve_task` command-line option.

`opencode_resource_selection.select_resources` optionally asks the existing
ModelGateway to select from bounded descriptor cards. It does not read full
resource bodies, invent digests, use a keyword router, or promote a skill.
The host still checks the exact selection and grant.

## Prepare the tested environment

The demonstrated environment is Linux x86-64 with Docker, OpenCode 1.17.9,
and portable ripgrep 14.1.1. Other platforms and versions need qualification.
The package and the configured provider must already work.

Use a new build context containing only the approved `opencode` and `rg`
binaries. The tested binary digests are:

| Binary | SHA-256 |
|---|---|
| OpenCode 1.17.9 Linux binary | `ff18379ebe33df346d2b3b36080ccef9c0eb0b0cdf68dd471567e0304651db70` |
| ripgrep 14.1.1 Linux musl binary | `f401154e2393f9002ac77e419f9ee5521c18f4f8cd3e32293972f493ba06fce7` |

The portable ripgrep archive comes from its
[official release](https://github.com/BurntSushi/ripgrep/releases/tag/14.1.1).
The archive digest is
`4cf9f2741e6c465ffdb7c26f38056a59e2a2544b51f7cc128ef28337eeae4d8e`.
Inspect archive members before extraction. Do not copy provider credentials,
personal caches, `.env` files, or previous sessions into the build context.

Build from the repository root:

```bash
docker build --network none --pull=false \
  -f examples/25_host_runtime/opencode_instance.Dockerfile \
  -t loop-engine-opencode-probe:1.17.9 /absolute/build-context

docker image inspect loop-engine-opencode-probe:1.17.9 \
  --format '{{json .RepoDigests}}'
```

Use the resulting immutable `name@sha256:...` reference for `--image`.
The exact base Node image must be available locally because the build does
not pull it. A tag or an installed executable alone is not qualification.
The test image is not published by this example.

## Run the probe

The default prints a plan. It makes no model call and starts no container:

```bash
python examples/25_host_runtime/run_opencode_instance.py
```

An explicit run uses a new work directory and a pinned image:

```bash
python examples/25_host_runtime/run_opencode_instance.py \
  --backend opencode \
  --work-dir /absolute/new/opencode-probe \
  --image 'loop-engine-opencode-probe@sha256:REPLACE_WITH_VERIFIED_DIGEST' \
  --model-route cloud.hard \
  --model-id deepseek-v4-pro:0813 \
  --authorize-model-calls \
  --allow-context-to-model \
  --authorize-instance-effects \
  --allow-tool-message-emulation \
  --select-resources-with-model
```

The last flag adds a real model-led resource selection before instantiation.
Without it, the authored probe explicitly chooses its two step resources.
The route and model must match current configured authority. No model-call or
total-token ceiling is invented by the example. Gateway output capacity and
provider timeouts remain in force.

The container has no network and receives no host credentials. A local model
endpoint exchanges framed messages with the host through stdin/stdout.
The current bridge explicitly emulates tool messages through structured text;
it does not claim provider-native tool calling. Read and skill are the only
qualified tool names. The prepared workspace is read-only.

## Read the evidence

The command prints a content-addressed result reference. The work directory
contains private artifacts and canonical Run History. It records model
requests and replies before admission, tool outcomes, source identity, and
container cleanup. It does not publish those private packets.

The numeric probe passes only when the Loop reaches its accepted local state,
the answer is correct, both requested skills and the read completed, their
tool results reached later model requests, and the workspace stayed unchanged.
This is an integration probe, not a general reasoning score or full-system
benchmark. A harness candidate still needs the host's task-specific verifier.

```bash
python -m unittest discover \
  -s examples/25_host_runtime -p 'test_opencode*.py'
```

Current limits include in-flight provider cancellation, arbitrary plugin
combinations, writable tools, MCP effects, pooling, and durable shared
sessions. Do not remove the containment policy to make a failing test pass.
For operational status changes, use the [managed-record tool](../24_managed_records/README.md)
and regenerate any exported JSON view.
