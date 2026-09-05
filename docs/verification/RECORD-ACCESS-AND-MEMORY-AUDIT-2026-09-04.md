# Record access implementation and memory audit

This session implemented a bounded local record tool and hardened the existing
catalog read/write contracts. It did not complete the full Record Fabric,
Memory ABI, or migration mandate.

## A. Repository state

Work began on clean `main` at
`d121379773e46a1255fd3e86436d907dc2a0b4d0` on 2026-09-04 at 21:32 local time.
Existing Codex/OpenCode processes were inventoried without printing arguments
or credentials. The separate showcase worktree was untouched. New changes in
this session were split by explicit file ownership; independent reviewers did
not modify implementation files.

All 470 packaged runtime files stayed unchanged during final verification and
matched the wheel, source distribution, and installed-wheel readback.
Outside-package documentation and examples were finalized separately.
No commit, push, remote database connection, or live provider test was made
in this session. One local OpenCode version probe occurred during research;
no OpenCode task/session was launched.

## B. Inventory and findings

The [research audit](../research/STORAGE-PACKAGES-HARNESSES-AND-MEMORY-2026-09-04.md)
records the 678 selected-format files, 62.6 MB, AST read/write sites, known
owners, package choices, and explicit inventory omissions. This is not a
complete dynamic caller-to-Loop graph of every possible file effect.

The largest files are not necessarily mutable runtime state. Some large
historical exports remain appropriate immutable artifacts. Risks depend on
who writes, expected revisions, transaction scope, corruption handling,
retention, and authority.

## C. Implemented corrections

| Boundary | Correction | Proof |
|---|---|---|
| Query contract | Reject unknown operators; detach predicates at stream-call time | Mutate nested values or clear filters before first iteration; original query remains bound |
| SQL adapters | Apply namespace/scalar predicates and residual attributes before pagination | Shared adapter conformance and foreign-namespace tests |
| File reads | Bound paths as SQL parameters; refuse globs/symlinks; stop JSONL reads at requested limit | Quote/path attacks and bounded stream cases |
| Capability handshake | Report only actual operations/formats; refuse unknown compatibility | Capability/refusal tests; composite no longer advertises missing write methods |
| SQLite | Transactional absence/version checks and batch import; logical read-only opening; visible corrupt JSON | Competing writers produce one winner; trigger failure rolls back import |
| SQLite WAL | Check qualified version and current journal mode inside every write transaction | External post-open journal switch is refused on affected runtime |
| Managed records | Schema/scope/approval, immutable revisions, conditional head, historical get and retire | 30 focused tool checks plus public CLI use |
| Write status | Distinguish typed conflict from `commit_unknown`; verify exact or later-chain readback | Storage abort and false confirmation cannot report committed success |
| Architecture | Register service/CLI boundaries; resolve root/nested module symbols; generate storage view | Boundary tests and 20 diagram checks |
| C4 output | Use C4-PlantUML instead of invalid Structurizr-flavoured text | Generated source checks; visual rendering was not performed |

The [ADR](../architecture/ADR-SCOPED-RECORD-OPERATIONS.md) keeps catalog,
artifact, Run History, and Git authority separate. No new Loop runtime,
intelligence layer, domain workflow, or promotion authority was added.

## D. Actual managed-record proof

The public `python3 -m loop_engine records` command was used with JSON stdin
and an exact approved effect digest. The first unapproved create returned a
plan and created no database/artifact root. Approved operations then:

1. Created `note.storage-audit`, revision 1.
2. Updated it with expected revision 1.
3. Materialized historical revision 1.
4. Queried current revision 2 by an indexed document field.
5. Later saved the final summary as revision 3.

A separate demonstration note was created and retired through the public CLI.
Its original document remained readable as revision 1. Retirement removed no
user data or historical artifact.

A second host schema created `session.storage-review-20260904` with structured
tests, unproven claims, and next actions using the same code. Its first revision
artifact is
`e33305c72be07e6d35b05780551c996d3078d5ca8f3c479a041f09110db791d3`.
The data lives under the ignored local directory
`.loop-engine-dev/record-tools/storage-review-20260904/`.
No LLM directly rewrote the database or revision artifact.

The command reported zero model calls and `run_history_persisted: false`.
The note-revision chain is durable. Persisted execution Run History and
generated session Markdown remain separate, unimplemented targets. This was
new managed data, not a silent migration of old session files.

## E. Read-scale diagnostic

One private synthetic population contained 100,000 canonical rows. A single
SQLite batch import and matching JSONL snapshot were queried in order:
SQLite, direct package JSONL, DuckDB file adapter. All returned the same 46
selected IDs and zero mismatched-namespace rows.

| Measurement | Seconds |
|---|---:|
| Generate rows | 0.230067 |
| Write JSONL | 0.709834 |
| SQLite single batch import | 1.062203 |
| SQLite selected / absent namespace | 0.093243 / 0.000131 |
| Package JSONL selected / absent namespace | 0.636795 / 0.709290 |
| DuckDB file selected / absent namespace | 0.673351 / 0.108010 |

JSONL: 31,960,222 bytes, SHA-256
`85788028d4227a5c0ce4fa36529ff8c9689aefac3e2ac486e9afac6e71e237b3`.
SQLite: 26,382,336 bytes. This was one process, one pass, fixed order, no warmup;
DuckDB's first measurement included lazy startup. Memory and concurrent scale
were not measured. Temporary generated data was removed. The complete inline
timing harness was not saved, so do not claim a fully archived performance
benchmark or a production ranking. No million-record qualification follows.

## F. Final verification

| Check | Result |
|---|---|
| Full source suite | 2,589/2,589 |
| Clean base-wheel suite | 2,544/2,544 applicable checks |
| Source and wheel conformance | 27/27 each |
| Catalog module checks | 107/107, including shared cross-adapter tests |
| Managed record checks | 30/30 |
| Architecture diagram checks | 20/20 |
| Build and archive/install integrity | Passed for all 470 runtime bodies |

Both full suites made zero provider calls. The base wheel explicitly did not
test optional DuckDB, MCP, model2vec, NumPy, OpenTelemetry SDK, pandas, or
sklearn integrations. The source environment did test the installed DuckDB
adapter. Exact commands, environments, and outputs are in the
[verification export](../evidence/record-access-20260904/final-verification.json).

Intermediate failures are preserved: source 2,586/2,588 due to terminology and
root-module resolution checks; a base-wheel optional-DuckDB import failure;
and generated conformance-manifest drift. The fixes did not disable gates or
claim absent adapters were tested. Documentation received Markdown/link checks;
no browser, Studio, or external diagram renderer was exercised.

## G. Open memory and harness incidents

At the close of this storage slice, three in-memory counterexamples were open:
post-verification inline aliases can change, forged working-memory snapshots
restore without digest/capacity revalidation, and run-note aliases can change
without another write event. These are not solved by a database migration.

The subsequent [harness and memory hardening report](HARNESS-AND-MEMORY-HARDENING-2026-09-04.md)
records their bounded repairs and fresh verification. The counts above remain
evidence for the earlier storage checkout, not the later changed source.

The earlier OpenCode adapter was one opaque realization inside a canonical Loop. Its
native configuration, tool, skill, plugin, and MCP discovery are not yet bound
to Loop Engine's admission/effect policy. The old direct wrapper remains an
audit finding. Do not enable broad harness execution based on source presence
or the old smoke record.

## H. Files and authority

The catalog protocol/query/handshake/composite and five adapters own storage
semantics. `record_operations`, its passive records/checks, and `record_cli`
own the new scoped tool. CLI dispatch, module map, boundary register, generated
architecture YAML mirror, and C4/Mermaid projections connect that tool to the
existing runtime. `AGENTS.md`, the guide, ADR, examples, and start-here page
explain the intended use. No unrelated user files were rewritten.

## I. Remaining limits and next action

Still unproven: full inventory/owner graph, migration of existing managed
writers, generated session views, general query plans/joins/snapshots,
Parquet/PostgreSQL substitution, durable cross-store write coordination,
retention and purge, million-record concurrency/crash testing, automatic
product model-tool discovery, and the complete Memory ABI.

Original next action: repair the demonstrated mutable-memory and snapshot-integrity boundaries,
then connect managed-record references to bounded context hydration. The next
storage migration should preserve one old operational source exactly, import
supported facts with unknowns retained, and generate a digest-bound view.
Do not replace constitutional files or canonical Run History wholesale.
