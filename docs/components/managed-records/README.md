# Managed records

Kind: component explanation for `src/loop_engine/record_cli.py` and
`src/loop_engine/core/record_operations.py`.

A note, a report or a decision that people will read again later needs a
different treatment from a temporary file. It needs a schema, a version that
tells you whether somebody else changed the record while you were reading it,
and an unchanged copy of every earlier version. This component owns that
treatment. It reads and revises a host-scoped collection of records through one
typed request, and it never edits a file in place.

The registered operational boundary is `record tool dispatch`, whose envelope is
`record_cli.record_command`. A second registered boundary, `managed record
operation`, has the envelope
`core.record_operations.RecordOperationService.execute` and owns the decision
inside the command. The request, the policy and the store are passive typed
objects. They are not graph vertices. One Practitioner Loop with the
`practitioner.code_execution@1.0.0` profile owns each dispatch.

## Runtime classification

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

The dispatch Loop runs in deterministic mode. It calls no model, and the result
it prints reports `model_calls` as zero.

## What this component owns

```text
Managed records
├── Host configuration, supplied on the command line and never in the request
│   ├── The policy file, a record_operation_policy/v1 document
│   ├── The storage backend, either an SQLite database or read-only shards
│   ├── The revision artifact root
│   └── The one exact effect digest the host approved for this write
├── The typed request, read once from standard input
│   ├── record_operation_request/v1
│   └── Five operations: create, get, query, update and retire
├── The decision, taken by RecordOperationService
│   ├── Scope, schema, operation and query-field checks before any effect
│   ├── One immutable managed_record_revision/v1 artifact for each write
│   └── One atomic expected-version update of the managed_record_head/v1
│       current reference
└── The typed answer
    ├── record_operation_plan/v1 when a write still needs approval
    ├── record_operation_result/v1 for a decided operation
    └── record_operation_failure/v1 for a refusal
```

The component does not own the storage engine. `CatalogStore` and
`IntelligenceQuery` remain the typed query boundary, and the revision bodies
live in the existing artifact store. It creates no second history store, no
second event vocabulary and no second source of truth.

## Typed inputs and outputs

The host owns everything that grants authority. Backend paths, the namespace
policy and the write approval arrive as command-line arguments from the
launcher. None of them is a field the request can set, so model output cannot
widen its own scope.

`record_operation_policy/v1` declares the scope, which is a namespace, a source
collection, an artifact kind and an intelligence layer; the document schema; the
operations the host allows; the fields a query may filter on; and a maximum
number of query results. Its digest is written into every revision.

`record_operation_request/v1` names one `operation`, one `record_id`, and, for a
write, the `expected_record_version` the caller believes is current. A `get` may
ask for an exact `record_version` and may set `materialize` to ask for the body
rather than the card. A `query` carries filters and no record identity.

`record_operation_result/v1` returns the scoped cards, the commit disposition
and the effect digest. It always reports `grants_authority` and
`promotes_intelligence` as false: storing a record never makes it approved
intelligence, and reading one never grants an effect.

The status field carries seven values.

| Status | What it means |
|---|---|
| `found` | The read matched. |
| `not_found` | Nothing in scope carries that identity or version. |
| `unmanaged` | A record exists under that identity, but this tool did not write it, so its history cannot be trusted. |
| `retired` | The record exists and its current revision is retired. |
| `stored` | The write committed and was read back. |
| `conflict` | The expected version was not the current version. Nothing was committed. |
| `commit_unknown` | The write may or may not have landed. `committed` is null, not false. |

`commit_unknown` is the value that matters most. When the backend does not
confirm a write, when the confirmation does not have the expected shape, or when
the read-back does not find the revision, the tool reports that it does not
know, names the reason in `diagnostic_code`, and returns the artifact reference
in `potential_orphan_artifact_ref` so an operator can find the written body. It
never reports an unknown commit as a success.

## Refusals

A refusal prints `record_operation_failure/v1` with an exact `error_code` and
exits 2. These are checked before any effect.

| Code | What it means |
|---|---|
| `operation_not_authorized_by_policy` | The host policy does not allow this operation. |
| `record_id_outside_scope` | The identity is outside the namespace the policy declares. |
| `document_schema_failed` | The document does not satisfy the policy's schema. |
| `query_field_not_indexed` | The query filters on a field the policy did not declare. |
| `expected_record_version_required` | An update or a retire arrived without the version it expects to replace. |
| `record_write_approval_required` | A write reached the service with no approved effect. |
| `approved_effect_digest_mismatch` | The approved digest is not the digest of the effect this request would perform. |
| `unexpected_write_approval` | A read arrived carrying a write approval. |
| `external_schema_reference_refused` | The policy schema points outside itself. |
| `backend_path_symlink_refused` | A configured path passes through a symbolic link. |
| `atomic_authoritative_store_required` | The negotiated store cannot promise an atomic precondition, so a write is refused rather than attempted. |
| `revision_predecessor_invalid` | A revision's recorded predecessor does not match the chain. |

Two of these deserve a sentence. `approved_effect_digest_mismatch` is what binds
an approval to one exact effect: a changed request produces a different digest
and needs a new decision. `atomic_authoritative_store_required` is why the
read-only shard backend refuses every write instead of doing a best effort one.

## How to check it

```bash
PYTHONPATH=src python -c \
  'from loop_engine.core.record_operations_checks import self_test; print(self_test()["all_passed"])'
PYTHONPATH=src python -c \
  'from loop_engine.record_cli import self_test; print(self_test()["all_passed"])'
```

The first runs the service checks against local temporary fixtures, including
the conflict, the refused operation and the unknown-commit paths. The second
runs the command-surface checks. Both write only into a temporary directory and
call no provider.

To see the plan for a write without performing it, send the request with no
`--approve-effect-digest`. The command prints `record_operation_plan/v1` with
the effect and its digest, reports `effects_executed` as false, and exits 0.

```bash
loop-engine records --policy /absolute/path/to/policy.json \
  --backend sqlite --database /absolute/path/to/records.db \
  --artifact-root /absolute/path/to/revisions < request.json
```

## Current behaviour and what is not established

Current behaviour: the SQLite backend supports reads and writes. The
`package-jsonl` backend is read-only and refuses a write with
`package_backend_is_read_only`. One request is processed for each command run,
and the request is bounded at one mebibyte. The dispatch reports
`run_history_persisted` as false, because the only history this component keeps
is the chain of immutable revisions.

Planned and not built: a qualified server-side store adapter, and any automatic
migration of existing JSON files, Markdown documents or logs into managed
records. The component is an incremental boundary over the catalogue store, not
a replacement for the repository's files. Do not read a design sentence in
[Queryable records and storage](../../guides/queryable-records-and-storage.md)
as a description of shipped behaviour; that guide marks the same separation.

No local fixture establishes durability across machines, concurrent writers from
separate processes, or the behaviour of a backend other than the two configured
here.

## What it deliberately does not do

- It does not edit a Markdown file, a database row or a current-reference
  document directly. Every change goes through the typed request.
- It does not accept a backend path, a namespace or an approval from the
  request body, so a model cannot widen its own scope by writing a field.
- It does not delete a revision. Retiring a record writes a new revision that
  records the retirement and leaves every earlier body unchanged.
- It does not report an unconfirmed write as committed, and it does not report
  it as failed either.
- It does not promote a stored record to active intelligence. Admission is a
  separate, independent process.
- It does not call a model, and it does not persist Run History.

## Related reading

- [Queryable records and storage](../../guides/queryable-records-and-storage.md)
  for the storage boundary this component sits on, and for what is still
  planned there.
- [Effect approvals](../core-architecture/EFFECT-APPROVALS.md) for the durable
  approval decision the write path uses.
- [Search and storage](../core-architecture/SEARCH-AND-STORAGE.md) for the
  retrieval backends and where bodies live.
- `examples/24_managed_records/` for a working request and policy pair.
