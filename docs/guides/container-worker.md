# Run the downloadable worker

Kind: operating guide for the packaged worker and its explicit execution profiles.

The worker image includes the Loop Engine command, its Baltor text-response
harness, OpenCode 1.17.9, Python, Node.js, npm, Git and Bubblewrap. No model,
provider credential or customer project is baked into the image.

The website instructions are at `/worker`. The current publication workflow
builds Linux amd64. Docker Desktop can select `linux/amd64` on an ARM computer;
that is emulation, not a qualification of a native ARM build. The Dockerfile
can select the ARM OpenCode binary when an ARM image is deliberately built.

## Download and inspect

```bash
docker pull ghcr.io/alisonjieli-png/loop-engine:main
docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp:rw,nosuid,size=512m \
  ghcr.io/alisonjieli-png/loop-engine:main doctor --format json
```

The moving `main` tag follows a successfully tested source revision. For a
repeatable installation, use the `sha-COMMIT` tag or image digest recorded by
the publication workflow. The website deployment and the worker image are
separate releases.

Save [the Compose configuration](../../containers/worker/compose.yaml) as
`compose.yaml` beside a new `project` directory. Put a task file there. On
Linux, choose your own file ownership before mounting the directory:

```bash
export BALTOR_UID="$(id -u)"
export BALTOR_GID="$(id -g)"
docker compose run --rm worker
```

Only the selected project is mounted at `/work`. The configuration runs a
non-root user, a read-only image, no Linux capabilities, a bounded temporary
directory, one gigabyte of memory and a process limit. It does not mount the
host Docker socket. Model calls require network access from the parent
worker; the offline verification profile additionally disables that network.

## Choose a model and harness

Export the credential your chosen provider uses in your own terminal. Compose
passes only the listed provider variables to the parent worker. Never put a
key in a task, a command argument, a project file or an image.

This example selects an existing Ollama Cloud route and a thirty-call
allocation. Choose a model your own account can use:

```bash
docker compose run --rm --entrypoint baltor-worker worker \
  --task /work/task.md --provider ollama_cloud --model gemma4:31b \
  --harness baltor --max-model-calls 30 --max-passes 4 \
  --authorize-project-commands
```

`baltor`, `opencode` and `gateway` are explicit choices. The first two use
fresh native processes through the existing semantic response edge. The
direct gateway option uses the engine's configured provider route. There is
no automatic switch to a different model, provider or execution profile.

The launcher creates a new `project/baltor-runs` subdirectory for each run.
The existing public solve path retains task identity, cumulative authority,
verification and Run History. Its adaptive planner can propose dependency-bound
subproblems, repairs and later work while the run remains active and within
its allocation. A terminal run is not rewritten to add work afterwards.

`--authorize-project-commands` explicitly permits the existing local command
profile inside the worker. It is for trusted project work. This is not a
separate kernel sandbox for generated commands. Leave the flag out when that
authority is not intended; unavailable execution must remain unavailable.

## Two isolation profiles

The supplied version 2 harness configurations explicitly select
`trusted_process`. Each assignment gets its own process, Git root, home,
configuration, private prompt and selected digest-bound recipe modules.
The native process receives no provider credential. A private broker retains
model identity, output allocation, accounting and permission checks. Native
tools are disabled; the owning engine performs approved actions and evaluates
the result.

The outer Docker container is the physical boundary. The adapter therefore
reports no per-process operating-system isolation. It must not satisfy a
caller that requires the `os_sandbox` capability. A separately selected
version 1 configuration retains the existing Bubblewrap profile. Failure of
that profile never causes an implicit switch to trusted execution.

This distinction follows the [layered harness design](../architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md)
and [existing harness guide](../../embodiments/HARNESS-GUIDE.md).

## What the checks establish

`tools/check_worker_bundle.py` tests the installed image and two actual fresh
native turns per adapter using a private fixture broker. It checks exact
responses, separate process identities, step-specific material and rejection
of inherited parent context. No external provider is called. Passing this
check establishes packaging and process mechanics, not model quality,
arbitrary task success, or compatibility of every upstream plugin.

The hosted catalogue remains separate. Searching it requires the customer's
personal Baltor key and current entitlement. A content download gives no
additional execution permission. Model funding, library access and machine
authority remain separate.
