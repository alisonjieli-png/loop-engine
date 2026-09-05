# Managed records through a tool

This example uses the existing catalog and immutable artifact store. It does
not create another runtime or intelligence layer. The host controls the small
static policy file; an agent supplies a typed request, not SQL or storage paths.

```text
Canonical Loop
├── Host policy: schema, scope, storage binding, limits
├── Request: create, get, query, update, or retire
├── Exact effect approval for mutation
├── Immutable revision artifact
└── Atomic SQLite head update with expected revision
```

Run from the repository root. Submit this request on standard input to
`loop-engine records` with the arguments below:

```json
{
  "record_type": "record_operation_request/v1",
  "operation": "create",
  "record_id": "note.example",
  "document": {"title": "First note", "body": "A reported observation, not verified truth."}
}
```

```bash
loop-engine records \
  --policy examples/24_managed_records/policy.json \
  --database .loop-engine-dev/records/notes.sqlite \
  --artifact-root .loop-engine-dev/records/artifacts
```

Without write approval this returns a plan and its exact `effect_digest`. It
does not create the database or artifact directories. After the host approves
that exact effect, resubmit the unchanged request with
`--approve-effect-digest <approved-digest>`. Do not build an agent wrapper that
automatically approves whatever digest it receives.

For a read, use the same host arguments and this stdin request without an
approval flag:

```json
{"record_type":"record_operation_request/v1","operation":"get","record_id":"note.example","materialize":true}
```

An update supplies `expected_record_version` from the previous result and a
new `document`. A conflicting writer receives a conflict. A storage failure
remains a separate failure or unknown commit status. `retire` creates a
tombstone revision; it does not erase old artifacts. An exact historical read
supplies `record_version` and a bounded `maximum_history_depth`.

Use an explicit query limit, or the host policy's bound applies:

```json
{"record_type":"record_operation_request/v1","operation":"query","filters":{"title":"First note"},"limit":10}
```

Results are small cards by default. Materialize a selected revision only when
its body is needed. No result grants execution or promotion authority.

The `package-jsonl` backend reads canonical catalog-row shards through the
same request contract. It does not write them. Arbitrary JSON documents or
legacy intelligence schemas need an explicit mapping before they are catalog
records; no column meanings are guessed from filenames.

This is a local managed-record example, not a migration of all report writers,
a PostgreSQL integration, or a hard filesystem sandbox. CLI operation Loops
are observable in the returned summary, but their execution Run History is
not automatically persisted to a third location. The immutable note-revision
chain is persisted.

`session-policy.json` demonstrates a different structured document schema with
test records, unproven claims, and next actions. It uses the same implementation
and command; only host policy changes. Its data remains reported candidate
information, not independently verified truth or execution authority.
