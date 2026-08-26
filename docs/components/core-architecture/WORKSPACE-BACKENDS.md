# Workspace backends

A workspace backend gives a Loop typed file, command, and snapshot operations.
The Loop keeps the goal, mode, budget, approval state, and event history. The
backend supplies the execution boundary.

`WorkspaceOperationService` is the approval-aware entry point over an existing
backend. It does not implement another backend.

```text
WorkspaceOperationService
├── Read, list, stat, snapshot
│   └── Existing backend policy and confinement
├── File write
│   ├── Exact LOCAL_WRITE EffectSpec
│   ├── One native approval consumption
│   └── At most one backend.file call
└── Command
    ├── Exact COMMAND_EXECUTION EffectSpec
    ├── One native approval consumption
    └── At most one backend.command call
```

The current module is
`loop_engine.core.workspace_backends`.

## Common contract

Every backend follows `WorkspaceBackend` and accepts the same main objects.

| Object | Purpose |
|---|---|
| `WorkspaceSpec` | Names the workspace and defines its base directory, command policy, file limit, and network policy. |
| `FileRequest` | Requests one relative read, write, list, or stat operation. |
| `FileResult` | Returns the content, digest, entries, or typed failure. |
| `CommandRequest` | Carries argv, a relative working directory, selected environment keys, limits, and explicit authority. |
| `CommandResult` | Returns the exit status, bounded output, or typed failure. |
| `WorkspaceSnapshotRef` | Identifies a snapshot by relative paths and content digests. |

The request objects keep a growing set of related values out of function
signatures. A loop can log each request and result without interpreting a
backend-specific return value.

## Approved writes and commands

The operation service maps a file write to the workspace ID, backend kind,
base-directory digest, relative path, content digest, replacement flag, directory creation
flag, and expected digest. It maps a command to the workspace identity and a
digest of the complete `CommandRequest`. File bodies, command input, and
environment values do not enter the approval parameters.

```python
from loop_engine.loop.approval_state_store import (
    LocalJsonApprovalStateStore,
)
from loop_engine.loop.effect_approval import (
    ApprovalDecision,
    EffectApprovalService,
)
from loop_engine.core.workspace_operations import (
    WorkspaceOperationService,
)

approvals = EffectApprovalService(
    runtime,
    store=LocalJsonApprovalStateStore("/approved/approval-state"),
)
operations = WorkspaceOperationService(workspace, approvals=approvals)

write_request = FileRequest(
    operation=FileOperation.WRITE,
    path="outputs/report.txt",
    content=b"reviewed output",
    create_parents=True,
)
plan = operations.plan_file_write(
    write_request,
    loop_id=requesting_loop.loop_id,
    reason="Write the reviewed report.",
)
checkpoint = approvals.create(plan.approval)
approvals.resume(
    checkpoint.pending,
    checkpoint.resume_token,
    ApprovalDecision.approve(plan.approval.request_id, "project-owner"),
)
result = operations.file(
    plan.request,
    approval_id=plan.approval.request_id,
)
```

The approval is consumed before the backend call. A changed path, content,
overwrite condition, command, working directory, timeout, environment key, or
request ID is refused. A backend failure is returned once and does not restore
the approval. A second call with the same approval cannot cross the backend.

Reads, directory listings, file status, and snapshots do not consume effect
approval because they are non-mutating operations. The selected backend still
applies its base-directory, path, size, and operating policy.

## Restricted local workspace

`RestrictedLocalWorkspace` requires an existing base directory. Its file
methods reject:

- absolute paths;
- any path with `..`;
- a symlink that resolves outside the base directory;
- a write larger than the configured file limit;
- replacement without `replace_existing=True`;
- replacement that fails an optional digest precondition.

```python
from loop_engine.core.workspace_backends import (
    FileOperation,
    FileRequest,
    RestrictedLocalWorkspace,
    WorkspaceSpec,
)

workspace = RestrictedLocalWorkspace(WorkspaceSpec(
    "invoice-review",
    "./work/invoice-review",
))

result = workspace.file(FileRequest(
    operation=FileOperation.READ,
    path="inputs/invoices.csv",
))
```

The local command method has two independent checks. `WorkspaceSpec` must set
`execution_enabled=True`, and the individual `CommandRequest` must set
`execution_authorized=True`. The exact executable string must also appear in
`allowed_commands`.

This command method is not an operating-system sandbox. It limits selection,
working directory, and environment construction. An authorized host process
still has the permissions of the host user. Use a container or remote sandbox
for untrusted code.

## Docker declaration

`DockerWorkspace` is inert when it is created. Its availability check uses a
local binary lookup. It does not contact the Docker daemon or pull an image.

Docker execution requires all of these conditions:

1. The Docker command exists.
2. The workspace base directory exists.
3. `WorkspaceSpec.execution_enabled` is true.
4. `CommandRequest.execution_authorized` is true.
5. The command is in the workspace allowlist.

The adapter disables container network access unless the workspace policy
allows it. It also refuses image tags by default. The caller must name an
immutable SHA-256 image digest that is already present. The command uses no
image pull, a read-only container filesystem, dropped capabilities, a process limit,
memory and CPU limits, and a bounded temporary directory.

The Docker backend uses the same confined file and snapshot implementation on
the exact host directory mounted into the container. File preparation and
result collection do not start a container. Commands start a container as the
current numeric host user, so prepared files retain the expected access rules.

A live local check used one immutable Python image, no network, no image pull,
a read-only container filesystem, and one mounted input file. All four checks
passed.
See the [saved Docker workspace evidence](../../evidence/docker-workspace-2026-08-25.json).

The mounted workspace remains writable. The backend still requires policy and
request authority for commands. `WorkspaceOperationService` adds exact native
Effect Approval before the existing backend receives a write or command.

## E2B and Modal declarations

`E2BWorkspaceDeclaration` and `ModalWorkspaceDeclaration` are typed optional
configuration objects. They do not require either SDK. A
`DeclaredRemoteWorkspace` reports `adapter_not_registered` until an executing
adapter is supplied.

This separation prevents a configuration object from silently creating a
remote resource or spending money. A future adapter must preserve the common
request, result, snapshot, approval, and event contracts.

## Current limit

The local path checks protect calls made through this backend. They do not
control custom tools that open files directly. A Practitioner must expose
workspace access through typed capability loops and keep direct host access
outside an untrusted Spawned Loop.
