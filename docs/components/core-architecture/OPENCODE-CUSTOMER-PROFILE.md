# Confined OpenCode customer profile

The `workspace_tools` profile lets a host give native OpenCode selected files,
read-only Baltor discovery and exact downloads, then collect selected output
files. Native tools run inside a fresh Linux sandbox. Model access and account
credentials stay in the host's separately authorized callbacks.

This is process machinery for the existing step executor. It creates no Loop
runtime, scheduler, account store or provider. The `opencode.raw_host` adapter
still refuses execution. `run_harness_process` still admits only
`text_response` recipes. A caller must choose
`run_workspace_harness_process` and supply `OpenCodeCustomerBoundary`
explicitly; no weaker fallback exists.

The existing `step_executor` and nested `process_confinement` engine slots
own this machinery. Their candidate status is unchanged. The recipe catalogue
selects this process profile; it is not a second engine registry or a claim
that the semantic step-adapter contract is implemented. Model, account and
artifact acceptance remain separate host boundaries.

The offline qualification starts OpenCode 1.17.9 with scripted fixture model
responses and local service fixtures. It checks native tool use, exact file
delivery, revision and recovery in a fresh process. It does not establish model
task-solving ability, a paid checkout, live account access, or availability of
a hosted execution product. A live proof needs its own authorized callbacks,
model identity, capacity evidence, complete attempt accounting and independent
artifact checks.

## Required inputs and ownership

`HarnessProcessRequest` names the exact installed binary and recipe catalogue,
model identity, source-backed context/output capacities, selected output
allocation, work directory and transport ceilings. The process identity binds
software and recipe digests. The customer boundary adds these inputs:

| Input | Host responsibility |
|---|---|
| `CustomerOperationBudget` | One shared model-request, service-request and monotonic-time ceiling across use, revision and recovery. The host also keeps durable physical-effect accounting. |
| `authority_effects` | Exactly `reads_fs`, `writes_fs`, `spawns_process`. This authorizes the bounded workspace, not arbitrary host access, general network access or secret reads. |
| `CustomerFile` snapshots | Explicit relative names and exact input bytes. At most 64 files, 200 UTF-8 bytes per path, depth 16, with a shared byte ceiling. No traversal, hidden configuration paths or `home` replacement. |
| `artifact_paths` | At most 64 exact relative paths selected before launch. Missing output is left for the independent grader to reject. |
| `mcp(method, params)` | The fixed ordinary-account broker. Returns only `{"result": ...}` or `{"error": ...}`. |
| Optional `http(method, path, payload)` | Returns exactly `status`, string-valued `headers`, and `body_base64`. It owns verified TLS and authentication. No sandbox authorization header is forwarded. |

The in-memory budget reserves before dispatch and never refunds an unknown
outcome. Reservations finish by stable sequence number under a lock. Reusing
one boundary concurrently refuses. Distinct boundaries can share one operation
budget, but the durable host broker remains the final physical-effect limit.
Both host callbacks must hold unknown external outcomes for reconciliation.
Neither the process runner nor the published-client wrapper retries them.

The native model boundary preserves structured assistant tool calls and tool
results. It refuses undeclared tools, other models, unmatched tool results,
multiple choices, external schema references and unknown top-level options.
It does not flatten tool history into text. The host model callback still owns
provider-specific validation, real capacity and allocation, deadline, usage
records and any unknown-outcome hold.

## Confinement and resource limits

The default profile has a 2 GiB aggregate memory limit, no swap, 64 tasks and
a 200% CPU quota in one owned transient user-systemd service. `RuntimeMaxSec`
and the operation deadline bound wall time. Before the host admits a broker
request it reads the actual cgroup limits and requires `KillMode=control-group`.
An unavailable user manager, mismatched limit or uncertain cleanup refuses.
No shared slice, timer or other service is changed.

The unit executes `/usr/bin/env -i PATH=/usr/bin:/bin` before Bubblewrap.
Bubblewrap's own `--clearenv` then supplies only the declared recipe
environment. Both steps matter: the negative control found a harmless unit
canary in namespace PID 1's initial environment when only `--clearenv` was
used. Clearing the environment before `execve` removed it from both native
`os.environ` and readable `/proc/*/environ` in the corrected native check.

Bubblewrap gives the process its own network and process namespaces. It mounts
only the declared software, the digest-bound recipe/relay, the private socket
and selected input files. `/work` is a 256 MiB tmpfs; `/tmp` is a 64 MiB tmpfs.
The host input directory is mounted read-only at `/seed`. Native writes have
no writable host-directory mount. Tmpfs memory also counts against the cgroup
limit. The recipe checks the actual filesystem type and capacity before it
copies selected seed files into `/work`.

The resource check exercises dirty memory pressure, task-count refusal, wall
timeout and cancellation of descendants. Its many-file control fills the
256 MiB workspace with 16,384 separate 16 KiB files and requires `ENOSPC`.
That control addresses aggregate scratch use, not just one large file.

## Exact downloads and selected outputs

The recipe mounts a private byte snapshot of the existing published
`baltor-library` client. Its SHA-256 is part of the process identity. The
wrapper changes only the client's transport through its injectable opener;
the client's source, schema checks, selected-reference binding, digest checks
and fetch-record format remain unchanged. The wrapper disables automatic retries.
Compare the recorded client digest with the exact served release before a
live proof.

The host permits only GET `/api/v1/capabilities` and POST
`/api/v1/retrieval`, `/api/v1/provisioning`, `/api/v1/download` through this
wrapper. Its MCP allowance is initialization, initialized notification,
tool discovery and the `intelligence_search`/`provisioning_read` tools.
The host must also bind exact references, declared effects, digests and logical
request identities; a native shell can speak the private socket directly.

Inside the sandbox, a task can use:

```text
python3 /relay/opencode_customer_recipe.py search QUERY --limit 3 --output selection
python3 /relay/opencode_customer_recipe.py fetch --identity IDENTITY --digest SHA256 \
  --request-id LOGICAL_REQUEST_ID --selection selection/selection.json --output stage
```

Those arguments must come from the actual selected reference and the host's
declared task. `fetch` stages exact bytes and writes the original fetch record.
It does not execute the download or install a native skill. The task can then
use a staged component within its declared workspace effects. Model-written
copies of component source are never counted as verified downloads.

After native execution, the recipe's `collect_workspace_artifacts(config)`
hook sends one `customer_artifact_snapshot/v1` through the existing Unix
channel. The parent authorizes the path list. Descriptor-relative opens reject
symlinks, hardlinks, sockets and FIFOs; identity checks reject parent-path
replacement and files changed during capture. The host validates decoded
bytes, names, SHA-256, file count and aggregate size again. A duplicate or
mixed export refuses. Captured bytes remain untrusted task output and are
released only after confirmed process-tree cleanup.

The default raw output allowance is 1 MiB. Its conservative base64-and-metadata
request allowance is 1,431,896 bytes, within the existing 2 MiB request ceiling.
The default response ceiling remains 4 MiB; neither value is the service's
maximum component-file size. A larger selected component needs explicit
compatible transport allowances before launch. The profile never increases
them silently.

OpenCode sends a cancellation notification after some completed MCP requests.
The local relay accepts only the shaped notification for a known completed
request, records bounded housekeeping counts, and makes no host call. Unknown,
active and initialization request identities are not recorded as completed
cancellations. This housekeeping does not claim to cancel an external effect.
Whole-operation cancellation still uses the host's cancellation flag, unknown
outcome handling and confirmed teardown.

## Verification and recovery

The independent grader checks captured file bytes and task results. A native
`ready` answer alone does not pass. For revision, select the accepted bytes as
fresh `CustomerFile` snapshots and keep the same operation budget. Recovery
starts another clean sandbox from those explicit snapshots; it does not read
the prior harness's ambient home or session state.

If setup fails before dispatch, fix the declared prerequisite and retry within
the operation deadline. If cleanup is uncertain, the same boundary refuses a
new launch and releases no artifacts. Reconcile a failed account or provider
request before authorizing any retry. Do not grant more effects in response to
a tool error.

Focused checks require the repository's Python environment:

```bash
PYTHONPATH=src python3 tools/test_opencode_customer.py
PYTHONPATH=src python3 tools/check_opencode_customer_offline.py \
  --binary /absolute/path/to/qualified/opencode \
  --output /absolute/path/to/a/new/offline-report-directory
PYTHONPATH=src python3 tools/check_opencode_customer_resources.py \
  --output /absolute/path/to/a/new/resource-report-directory
```

The native and resource checks create their own transient units and refuse
existing report directories. They use no provider/account credential and call
no real model or service. Preserve failed reports beside later passing ones.
The native checker uses the release catalogue's `opencode_customer` recipe
and exact module digest. The old text-only and raw-host guards remain. This
registration makes the process profile selectable by explicit callers; it
does not register a semantic `ExternalHarnessAdapter/v2` implementation or
qualify hosted customer execution.

## Reused implementations and source review

The implementation reuses `harness_process`, its Unix relay and recipe
catalogue; `harness_customer_resources` adapts the repository's existing
systemd/Bubblewrap component-qualification pattern. Docker workspaces remain
a separate backend. No image pull or second scheduler is needed here.

OpenCode's [configuration](https://opencode.ai/docs/config/) and
[permission](https://opencode.ai/docs/permissions/) documents describe native
configuration controls. These controls support the recipe, but the OS and
host broker enforce its authority. The
[Bubblewrap source](https://github.com/containers/bubblewrap) supplies the
namespace/mount mechanism; the installed command's `--size`/`--tmpfs`
behavior is checked locally. The
[MCP cancellation specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/cancellation)
allows a receiver to ignore cancellation for completed or uncancellable
requests. That is the basis for the local-only housekeeping handler.
