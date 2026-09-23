# A focused assignment packet before any skill

Status: candidate renderer and two offline examples. Nothing is admitted,
installed in a customer's harness, or served by Baltor. These are ephemeral
run assignments. They add **zero persistent library items**.

Each fresh harness needs its actual assignment before it can select useful
library material. A skill alone cannot supply the current objective, input,
state, next actions and output contract. This example renders those fields
from an explicit brief through the repository's existing instruction composer.

## Open the two examples

| Example | Native entrypoint | Additional context | Structured state |
|---|---|---|---|
| Reconcile inventory availability | [AGENTS.md](packets/inventory-reconciliation/AGENTS.md) | [node_context.md](packets/inventory-reconciliation/node_context.md) | [run-state.json](packets/inventory-reconciliation/run-state.json) |
| Order incident observations without inventing causality | [CLAUDE.md](packets/incident-timeline/CLAUDE.md), importing [AGENTS.md](packets/incident-timeline/AGENTS.md) | [node_context.md](packets/incident-timeline/node_context.md) | [run-state.json](packets/incident-timeline/run-state.json) |

The inventory packet has eight payload files and one digest manifest. The
incident packet has nine payload files and one manifest. Together these are
19 example files: seven Markdown files and twelve JSON files, including the
two manifests. Neither packet includes a `SKILL.md` file or executable hook.
The renderer and its tests are outside the packets.

The native entrypoint contains the objective, relevant context, ordered first
actions, current state, bounded input, output JSON Schema and acceptance
checks. The auxiliary files preserve explicit machine-readable contracts and
state. Their filenames do not make them auto-load. A trusted host retains
the expected binding outside the packet and checks it before launch.

## Reuse and ownership

- `NodeAssignment` supplies the existing `node_assignment/v3` fields. Its
  repository-native serialized filename is `task.json`, not `assignment.json`.
- `AssignmentBriefing`, `sections_for_assignment`, `compose` and `write`
  supply the native instruction entrypoint and Claude import alias.
- `TrustedStateSnapshot` supplies the state identity, version and digest.
- `resolved_schema_json` and the existing JSON Schema dependency validate
  self-contained schemas without fetching remote references.
- The repository's strict JSON reader and secret patterns are reused.

The small passive `PacketBrief` wrapper is confined to this artifact. It
does not add a runtime, state store, service endpoint or public contract.
Its candidate record names must not become accepted production formats just
because these files exist.

An approved reusable renderer can eventually compose each run's packet from
host-validated task and authority fields. A routine generated `task.json`
does not need a new panel of three models on every execution. Reusable
procedure, tool and plugin bodies still need their own exact-byte admission.
Separately, each actual task result needs its owning acceptance process.

## Run the bounded offline checks

From the repository root, with the repository Python environment:

```bash
PYTHONPATH=src python -m unittest discover \
  -s artifacts/focused-step-packet-2026-09-23 -p test_render_packet.py -v
```

The command-line renderer accepts `render` or `verify`, a `--brief` file,
its externally supplied `--brief-sha256`, and a `--destination`. Use the exact
fixture hashes in [fixture-bindings.json](fixture-bindings.json), which also
records the expected run, step, state version, context version and payload
digest. Rendering requires a new directory under an existing plain parent;
it refuses to overwrite a previous packet.

Example verification, with the recorded digest substituted for `EXACT_DIGEST`:

```bash
PYTHONPATH=src python artifacts/focused-step-packet-2026-09-23/render_packet.py \
  verify \
  --brief artifacts/focused-step-packet-2026-09-23/fixtures/inventory-reconciliation.json \
  --brief-sha256 EXACT_DIGEST \
  --destination artifacts/focused-step-packet-2026-09-23/packets/inventory-reconciliation
```

The renderer has a 128 KiB brief and total payload ceiling, 32 KiB per payload
file, bounded text/list fields and a fixed file inventory. It permits no
model, process or other execution authority in these examples. It refuses
unknown fields and versions, stale expected bindings, unexpected files,
path traversal, existing destinations and symlink paths. It scans the entire
brief and payload for the repository's known secret patterns. Those patterns
cannot identify every possible secret.

## Saved evidence

- [Before implementation](tests-before-renderer.txt): 16 tests failed against
  the test-first stub.
- [First implementation](tests-after-renderer-initial.txt): 16 tests passed.
- [Before version repair](tests-before-version-repair.txt): a seventeenth
  known-wrong test exposed `true` being treated as integer version `1`.
- [After repair](tests-after-version-repair.txt): all 17 tests passed.
- [Before schema-refusal repair](tests-before-schema-refusal-repair.txt): an
  eighteenth test showed an invalid JSON Schema escaping as the library's
  exception rather than the renderer's typed refusal.
- [Final unit tests](tests-final.txt): all 18 tests passed after that repair.
- [Final removed-guard checks](removed-guard-checks-20260923T132739.json): a passing
  baseline and seven guard removals, each detected on the final source.
  The [initial record](removed-guard-checks.json) is retained. The repeatable
  `check_removed_guards.py` writes a new dated report on every run.
- [Codex pickup on current formatted bytes](CODEX-PICKUP-20260923T132425.json): Codex 0.155.1's
  `debug prompt-input` included the exact objective, first action, state
  identity and output contract for both shared `AGENTS.md` files. Removing
  `AGENTS.md` while keeping auxiliary files removed every marker. No model
  was called. The Claude import itself remains untested in this experiment.
- [Final Markdown check](markdown-final.json): nine files, zero issues,
  with the exact native-import exception described below.

The first native probe,
[CODEX-PICKUP-20260923T131730.json](CODEX-PICKUP-20260923T131730.json), tested
the earlier formatting. Those exact packet bytes are kept in
`failed-attempts/pre-format-packets`, with their expected binding in
[fixture-bindings-before-format-repair.json](fixture-bindings-before-format-repair.json).
The direct Markdown library found 23 style issues in that version, recorded
in [markdown-before-format-repair.json](markdown-before-format-repair.json).
The renderer was repaired to separate lists and JSON fences. The native
`CLAUDE.md` import intentionally has no heading; Markdown rule MD041 is
excluded for that exact import file only, preserving the existing writer's
native bytes. The normal rules apply to the remaining Markdown files.

The probe used an empty home/configuration and a temporary root without
ancestor instruction files. A closed proxy was configured; this is not an
operating-system network sandbox. The probe establishes prompt construction,
not model use, semantic correctness or accepted task completion.

A separate reviewer replayed four adversarial boundary checks against the final
renderer: a FIFO replacing context, an unexpected directory, an unexpected
FIFO and forged typed assignment fields. All were refused in the
[independent report](independent-boundary-checks.json). This did not grant
admission or establish task completion.

## Integration limits

The [verification and integration note](../../docs/verification/FOCUSED-STEP-CONTEXT-PACKET-2026-09-23.md)
maps this work to the existing boundaries. The current writer is used only
inside a newly created private directory. Concurrent hostile filesystem
mutation, hard-link/mount provenance, process sandboxing and a distributed
freshness authority are not qualified here. A digest establishes identity,
not the truth of a claimed state. Failed writes preserve partial output for
inspection; they are not committed execution state.

The packet copies a supplied state snapshot and never advances it. The host
must produce a new expected state/context binding for a changed assignment.
Prompt text does not enforce permissions or guard against all prompt
injection. This renderer refuses authority-bearing examples because its
typed host authorization integration is still proposed.
