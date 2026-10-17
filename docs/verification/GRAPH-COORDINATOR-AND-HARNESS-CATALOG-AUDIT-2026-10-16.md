# Loop graph communication coordinator and 108-cell harness catalog verification, October 16, 2026

Kind: verification record. Date: 2026-10-16. Scope: deterministic audit and
multi-engine benchmark of `Loop` graphs, vertices, typed edges, four swappable
communication coordinator engines, the 108-cell (9 harnesses by 12 component
families) harness component catalog, 12 end-to-end use-case executions, and
eight known-wrong controls inside the seven-layer component envelope.

## Useful outcome and scope

This verification suite proves that every executable graph vertex remains a
canonical `Loop` (`LE-RUNTIME-001`), that inter-`Loop` communication edges
enforce versioned request, result, and refusal contracts with SHA-256 digests,
and that all 12 component families materialize and execute across all nine
supported coding harnesses (108 verified cells). The implementation and tests
live in
[`tools/graph_coordinator_and_harness_catalog_engines.py`](../../tools/graph_coordinator_and_harness_catalog_engines.py)
and
[`tools/test_graph_coordinator_and_harness_catalog_engines.py`](../../tools/test_graph_coordinator_and_harness_catalog_engines.py).

## Where the coordinator and catalog fit in the system

Every executable graph vertex is a `Loop`. Passive files, contract cards, and
renderer scene frames stay inside their owning `Loop` and never become separate
`Loop` runtimes. A discrete cognitive or act step Loop node retains a narrowly
scoped assignment, selected context and resources, separately initialized
harnesses, permitted harness changes, expectation checks, iteration until
declared completion conditions, continued production of alternative outputs, and
protection against repeated external effects, where publication of an output is
separate from completion.

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

Each communication coordinator and harness catalog adapter runs inside the
seven-layer component envelope defined in
[`src/loop_engine/core/engines/envelope.py`](../../src/loop_engine/core/engines/envelope.py):

```text
Envelope Loop (for one graph coordination or catalog request, outermost first)
├── 1 frustration_avoidance  shapes every refusal as envelope_refusal/v1 and bounds recovery via RecoveryAllowance(3)
├── 2 carrier                enforces canonical Loop vertex class, admitted roles and modes, and typed edge schemas
├── 3 handshake              computes envelope_handshake_verdict/v1 and refuses ungranted effect escalation across edges
├── 4 account                enforces run token budget ceilings before any subordinate Loop is scheduled
├── 5 tracking               records envelope_journal_entry/v1 intent and outcome chains for idempotent edge replay
├── 6 preflight              verifies DAG acyclicity, MCP transport keys, card-first discovery, and clean reopen digests
└── 7 nested_envelopes       enters subordinate Loop frames via enter_nested with shared allowance and deadline
```

## Four swappable communication coordinator engines and cascade benchmark

The suite benchmarks four swappable communication coordinator and `Solution`
graph scheduler engines plus the seven-layer cascade coordinator across four
reference `Loop` graph workloads (`W-DAG-01` Creative Studio Diamond DAG,
`W-WAVE-02` Parallel Practitioner Spawn under wave contention, `W-DEADLINE-03`
Intelligence Feed to System-1 Station under tight deadline slice, and
`W-MAILBOX-04` Overnight AFK Checkpoint Pipeline under mailbox backpressure):

1. `topological_wave_coordinator`: schedules deterministic Directed Acyclic
   Graph (DAG) topological waves with parallel fan-out and fan-in and verifies
   versioned edge schema digests.
2. `priority_deadline_coordinator`: partitions critical-path deadlines and
   per-vertex token ceilings across subordinate `Loop` vertices.
3. `actor_mailbox_handoff_coordinator`: manages bounded-queue edge handoffs with
   backpressure checks and idempotent journal replay through
   `envelope_tracking.py`.
4. `sequential_deterministic_fallback_coordinator`: executes vertices in
   deterministic linear topological order when parallel wave slots, deadline
   slices, or actor queues are saturated.
5. `cascade_coordinator_envelope`: wraps all four coordinator engines in the
   seven-layer envelope with automatic failover governed by one shared
   `RecoveryAllowance` (`MAXIMUM_AUTOMATIC_ATTEMPTS = 3`).

| Coordinator engine | Workloads completed | Completion rate | Mean latency (ms) | Total latency (ms) | Primary scheduling mechanism |
| --- | --- | --- | --- | --- | --- |
| `topological_wave_coordinator` | 1 / 4 | 25.0% | 0.088 | 0.352 | Kahn topological wave fan-out and fan-in with edge digest check |
| `priority_deadline_coordinator` | 2 / 4 | 50.0% | 0.084 | 0.336 | Critical-path slack and token ceiling partitioning |
| `actor_mailbox_handoff_coordinator` | 3 / 4 | 75.0% | 0.086 | 0.344 | Bounded mailbox queue with idempotent journal replay |
| `sequential_deterministic_fallback_coordinator` | 4 / 4 | 100.0% | 0.089 | 0.356 | Zero-concurrency linear topological execution |
| `cascade_coordinator_envelope` | 4 / 4 | 100.0% | 0.214 | 0.856 | Seven-layer envelope with shared `RecoveryAllowance(3)` failover |

### Workload failover chains under `cascade_coordinator_envelope`

| Workload ID | Workload title | Vertices and edges | Fallback chain exercised | Waves scheduled | Tokens allocated | Outcome code |
| --- | --- | --- | --- | --- | --- | --- |
| `W-DAG-01` | Creative Studio Diamond DAG | 5 vertices, 5 edges | `topological_wave_coordinator` | 4 | 14,700 / 20,000 | `scheduled_by_topological_wave_coordinator` |
| `W-WAVE-02` | Parallel Practitioner Spawn with Wave Contention | 4 vertices, 4 edges | `topological_wave` -> `priority_deadline` | 3 | 17,000 / 25,000 | `scheduled_by_priority_deadline_coordinator` |
| `W-DEADLINE-03` | Intelligence Feed to System-1 Station under Tight Deadline | 3 vertices, 2 edges | `topological_wave` -> `priority_deadline` -> `actor_mailbox` | 3 | 5,500 / 15,000 | `scheduled_by_actor_mailbox_handoff_coordinator` |
| `W-MAILBOX-04` | Overnight AFK Checkpoint Pipeline under Mailbox Backpressure | 3 vertices, 2 edges | `topological_wave` -> `priority_deadline` -> `actor_mailbox` -> `sequential_fallback` | 3 | 7,000 / 15,000 | `scheduled_by_sequential_deterministic_fallback_coordinator` |

## Nine-harness adapter specification and MCP transport verification

The catalog adapter suite verifies exact configuration paths, rule files, skill
directories, and Model Context Protocol (MCP) transport keys across all nine
supported harnesses:

| Harness ID | Display name | Workspace rule file | Skill directory | MCP configuration path | Verified MCP transport key | Cells verified |
| --- | --- | --- | --- | --- | --- | --- |
| `claude_code` | Claude Code | `CLAUDE.md` | `.claude/skills` | `.claude/settings.json` | `http` | 12 / 12 |
| `codex` | Codex | `AGENTS.md` | `.codex/skills` | `.codex/config.toml` | `http_transport` | 12 / 12 |
| `cursor` | Cursor | `.cursorrules` | `.cursor/skills` | `.cursor/mcp.json` | `url` | 12 / 12 |
| `windsurf` | Windsurf | `.windsurfrules` | `.windsurf/skills` | `.codeium/windsurf/mcp_config.json` | `serverUrl` | 12 / 12 |
| `cline` | Cline | `.clinerules` | `.cline/skills` | `.cline/mcp_settings.json` | `streamableHttp` | 12 / 12 |
| `roo_code` | Roo Code | `.roorules` | `.roo/skills` | `.roo/mcp.json` | `streamable-http` | 12 / 12 |
| `opencode` | OpenCode | `AGENTS.md` | `.opencode/skills` | `opencode.json` | `remote` | 12 / 12 |
| `pi` | Pi | `AGENTS.md` | `.pi/skills` | `.pi/settings.json` | `mcp_endpoint` | 12 / 12 |
| `goose_chatgpt_app` | Goose / ChatGPT App | `AGENTS.md` | `.goose/skills` | `.config/goose/config.yaml` | `sse_or_streamable_http` | 12 / 12 |

## Twelve component families and end-to-end use-case verification (108 cells)

Each of the 12 component families is verified across all nine harnesses (9 by 12
equals 108 verified cells) and executed through an end-to-end use case that
checks contract-card discovery prior to source materialization, seven-layer
envelope handshake compatibility, and `Loop` graph coordinator completion.

| Use case ID | Component family (`family_id`) | Default `Loop` role and mode | Primary harness checked | Card bytes | Full source bytes | Discovery byte savings | Harnesses verified | End-to-end status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `UC-01` | `skills` (`SKILL.md`) | `Practitioner` (`hybrid`) | Claude Code | 320 B | 4,800 B | 93.33% | 9 / 9 | Verified (`1.0`) |
| `UC-02` | `workspace_rules` (`AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.windsurfrules`, `.roorules`) | `Practitioner` (`deterministic`) | Codex | 290 B | 5,200 B | 94.42% | 9 / 9 | Verified (`1.0`) |
| `UC-03` | `lifecycle_hooks` (`pre-turn`, `post-edit`, `pre-commit`) | `Solution` (`deterministic`) | Cursor | 310 B | 3,600 B | 91.39% | 9 / 9 | Verified (`1.0`) |
| `UC-04` | `slash_commands` (`/goal`, `/plan`, `/boost`, `/learn`) | `Practitioner` (`hybrid`) | Windsurf | 260 B | 2,900 B | 91.03% | 9 / 9 | Verified (`1.0`) |
| `UC-05` | `mcp_server_configs` (transport-verified MCP definitions) | `Solution` (`deterministic`) | Cline | 340 B | 2,400 B | 85.83% | 9 / 9 | Verified (`1.0`) |
| `UC-06` | `system1_decision_stations` (O(1) deterministic triage tables) | `Intelligence` (`deterministic`) | Roo Code | 280 B | 3,100 B | 90.97% | 9 / 9 | Verified (`1.0`) |
| `UC-07` | `engine_api_cards` (Python, JS, Three.js, Babylon.js, Godot, Blender) | `Intelligence` (`deterministic`) | OpenCode | 380 B | 14,200 B | 97.32% | 9 / 9 | Verified (`1.0`) |
| `UC-08` | `corner_case_test_packs` (boundary and known-wrong suites) | `Solution` (`deterministic`) | Pi | 350 B | 8,400 B | 95.83% | 9 / 9 | Verified (`1.0`) |
| `UC-09` | `creative_studio_recipes` (`reelkit`, shaders, 3D mesh, audio DSP) | `Solution` (`hybrid`) | Goose / ChatGPT App | 410 B | 16,800 B | 97.56% | 9 / 9 | Verified (`1.0`) |
| `UC-10` | `overnight_afk_task_manifests` (budget-capped and journalled) | `Practitioner` (`hybrid`) | Claude Code | 370 B | 6,900 B | 94.64% | 9 / 9 | Verified (`1.0`) |
| `UC-11` | `curated_agent_feeds` (digest-verified intelligence streams) | `Intelligence` (`deterministic`) | Codex | 300 B | 5,400 B | 94.44% | 9 / 9 | Verified (`1.0`) |
| `UC-12` | `executive_comparison_briefs` (provenance and trade-off matrices) | `Intelligence` (`deterministic`) | Cursor | 330 B | 7,600 B | 95.66% | 9 / 9 | Verified (`1.0`) |

## Known-wrong controls

Every structural, security, and catalog boundary guard is paired with a
`removed_*` known-wrong control that disables that single guard and confirms
that the invalid case is then noticed as a leak (`known_wrong_detected = True`).

| Control name | Target workload or cell | Guarded refusal code | Unguarded code when removed | Leak detected |
| --- | --- | --- | --- | --- |
| `removed_cycle_detection_guard` | `KW-CYCLE-01` | `graph_cycle_detected` | `known_wrong_graph_violation_leaked` | Passed (`True`) |
| `removed_untyped_edge_guard` | `KW-UNTYPED-02` | `untyped_edge_contract_refused` | `known_wrong_graph_violation_leaked` | Passed (`True`) |
| `removed_concrete_loop_subclass_guard` | `KW-SUBCLASS-03` | `concrete_loop_subclass_refused` | `known_wrong_graph_violation_leaked` | Passed (`True`) |
| `removed_passive_frame_vertex_guard` | `KW-PASSIVE-04` | `passive_frame_or_file_as_loop_refused` | `known_wrong_graph_violation_leaked` | Passed (`True`) |
| `removed_edge_effect_escalation_guard` | `KW-EFFECT-05` | `edge_effect_escalation_refused` | `known_wrong_graph_violation_leaked` | Passed (`True`) |
| `removed_mcp_transport_key_guard` | `windsurf__mcp_server_configs` | `mcp_transport_key_mismatch` | `known_wrong_catalog_violation_leaked` | Passed (`True`) |
| `removed_card_first_lazy_source_guard` | `claude_code__engine_api_cards` | `eager_source_load_on_discovery_refused` | `known_wrong_catalog_violation_leaked` | Passed (`True`) |
| `removed_creative_reopen_digest_guard` | `opencode__creative_studio_recipes` | `creative_reopen_or_digest_failed` | `known_wrong_catalog_violation_leaked` | Passed (`True`) |

## Reproduce the verification locally

Run the coordinator benchmark, 108-cell catalog verifier, and unit test suite
under the memory cap:

```bash
export TMPDIR=$HOME/.le-ci-tmp/tmp-layers
mkdir -p "$TMPDIR" && touch "$TMPDIR/.keep-in-place"
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python tools/graph_coordinator_and_harness_catalog_engines.py
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_graph_coordinator_and_harness_catalog_engines.py
```

## Limits and deeper references

This verification suite executes deterministically in memory over the seven
envelope layers in `src/loop_engine/core/engines/envelope.py`,
`src/loop_engine/core/engines/envelope_tracking.py`, and
`src/loop_engine/core/engines/envelope_preflight.py`. It verifies structural
contracts, adapter transport keys, card-first discovery byte bounds, and
coordinator failover semantics offline; it does not claim live execution inside
external commercial IDE binaries on a user workstation.

For deeper architecture and contract references, see:

- [`docs/architecture/ADR-COMPONENT-ENVELOPE-LAYERS.md`](../architecture/ADR-COMPONENT-ENVELOPE-LAYERS.md)
- [`docs/architecture/FUNCTIONAL-COMPONENT-STANDARD.md`](../architecture/FUNCTIONAL-COMPONENT-STANDARD.md)
- [`docs/architecture/NORTH-STAR.md`](../architecture/NORTH-STAR.md)
- [`docs/guides/repository-engineering-rules.md`](../guides/repository-engineering-rules.md)
