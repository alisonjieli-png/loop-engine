# Trace, sync, and continuous self-improvement engine suite verification (2026-10-16)

This report records the design, implementation, head-to-head benchmarks, and
adversarial verification of the swappable four-slot, twelve-engine trace,
sync, and continuous self-improvement suite in
[tools/trace_and_self_improvement_engines.py](../../tools/trace_and_self_improvement_engines.py)
and
[tools/test_trace_and_self_improvement_engines.py](../../tools/test_trace_and_self_improvement_engines.py).

## Outcome and scope

Every functional boundary across frontend behavior tracing, local harness trace
storage, cloud trace synchronization, and continuous self-improvement now runs
inside the seven-layer component envelope defined in
[src/loop_engine/core/engines/envelope.py](../../src/loop_engine/core/engines/envelope.py),
[src/loop_engine/core/engines/envelope_preflight.py](../../src/loop_engine/core/engines/envelope_preflight.py),
and
[src/loop_engine/core/engines/envelope_tracking.py](../../src/loop_engine/core/engines/envelope_tracking.py).
Each of the four slot families exposes a fixed, typed, versioned request and
result contract with three swappable engines and an ordered runtime fallback
cascade.

All 14 unit tests in
[tools/test_trace_and_self_improvement_engines.py](../../tools/test_trace_and_self_improvement_engines.py)
and all four self-test assertions in
[tools/trace_and_self_improvement_engines.py](../../tools/trace_and_self_improvement_engines.py)
pass with zero leaks of credentials, bearer tokens, email addresses, filesystem
paths, or raw source code payloads.

## Where the suite fits in the Loop architecture

Every executable graph vertex in Loop Engine is a `Loop`. Passive trace
records, SQLite write-ahead logs, JSONL spool files, sync envelopes, and engine
slots are passive data or adapters used by a `Loop`, never separate graph
vertices.

```text
Loop
├── Relationship: Starting, Spawned by, Queried by, Retrieved by, Connected from
├── Role: Practitioner, Intelligence, or Solution
├── Mode: deterministic, hybrid, or non-deterministic
├── Category: organization and search taxonomy across library components
└── Settings: contract, loop condition, exit condition, budget, and permissions
    ├── Discrete cognitive or act step Loop node behavioral guarantees:
    │   ├── Narrowly scoped assignment with selected context and resources
    │   ├── Separately initialized harnesses and permitted harness changes
    │   ├── Expectation checks and iteration until declared completion conditions
    │   ├── Continued production of alternative outputs when configured
    │   ├── Protection against repeated external effects before retry
    │   └── Separation of output publication from Loop completion
    └── Engine slots used by Loop steps across trace and self-improvement flows:
        ├── Slot A: frontend_behavior_trace (upgrades runtime_memory coverage)
        │   ├── Engine A1: in_tab_session_ring_buffer
        │   ├── Engine A2: aggregate_funnel_step_counter
        │   └── Engine A3: voluntary_redacted_diagnostic_bundle
        ├── Slot B: harness_local_trace_store (upgrades run_history_export coverage)
        │   ├── Engine B1: local_sqlite_wal_trace_store
        │   ├── Engine B2: local_jsonl_ring_spool
        │   └── Engine B3: in_memory_ephemeral_trace_buffer
        ├── Slot C: cloud_trace_sync (upgrades usage_export coverage)
        │   ├── Engine C1: cloud_batch_digest_exporter
        │   ├── Engine C2: edge_worker_beacon_exporter
        │   └── Engine C3: offline_spool_with_circuit_breaker
        └── Slot D: continuous_self_improvement (upgrades failure_journal coverage)
            ├── Engine D1: heuristic_gap_cluster_improver
            ├── Engine D2: lsh_alias_and_query_relaxation_synthesizer
            └── Engine D3: harmony_pareto_verified_promoter
```

A discrete cognitive or act step Loop node receives a narrowly scoped
assignment, selected context and resources, separately initialized harnesses,
and explicit rules for permitted harness changes. It runs expectation checks,
iterates until declared completion conditions are met, can continue producing
alternative outputs when configured, protects against repeated external
effects, and keeps publication of an output separate from completion of the
step. When a Practitioner Loop or Solution Loop records runtime traces, exports
usage digests, or executes a self-improvement Practitioner task over
accumulated failure clusters, it invokes these four engine slots through their
typed envelopes.

## Seven-layer component envelope and baseline gap closure

The baseline coverage file
[src/loop_engine/data/component_envelope_coverage_baseline.yaml](../../src/loop_engine/data/component_envelope_coverage_baseline.yaml)
recorded missing or partial envelope layers across `runtime_memory`,
`run_history_export`, `usage_export`, and `failure_journal`. The
`SevenLayerSlotEnvelope` wrapper in
[tools/trace_and_self_improvement_engines.py](../../tools/trace_and_self_improvement_engines.py)
enforces all seven layers around every engine invocation:

1. **Layer 1 (`frustration_avoidance`)**: Enforces bounded payload size, budget
   ceilings (`max_duration_ms`, `max_bytes`, `max_events`), and structured
   actionable remediation messages on every refusal.
2. **Layer 2 (`carrier`)**: Wraps requests and responses in a versioned
   `EnvelopeCarrier` (`loop_engine.component_envelope.v1`) with deterministic
   SHA-256 request and payload digests.
3. **Layer 3 (`handshake`)**: Validates slot schema compatibility (`1.0.0`) and
   scrubs or refuses secret patterns (`baltor_`, `sk-`, `ghp_`, `glpat-`,
   `xoxb-`, `AIza`, `AKIA`, `Bearer`), personal email addresses, and local home
   paths before engine code executes.
4. **Layer 4 (`account`)**: Enforces `AccountContext` scope isolation, refuses
   anonymous cloud mutations when account authentication is required, and keys
   rate and byte budgets by account identifier.
5. **Layer 5 (`tracking`)**: Emits monotonic duration (`duration_us`),
   `TrackingStatus`, engine identifier, and trace correlation records via
   `TrackingContext`.
6. **Layer 6 (`preflight`)**: Runs `run_preflight_checks` plus secret,
   opt-in consent, and independent reviewer checks before any filesystem,
   SQLite, or network effect can occur.
7. **Layer 7 (`nested_envelopes`)**: Propagates `parent_invocation_id`,
   increments `nesting_depth`, detects cycles across `visited_slots`, and
   enforces `max_nesting_depth` across multi-slot pipelines.

### Baseline to target coverage matrix

| Baseline component | Mapped slot family | `frustration_avoidance` | `carrier` | `handshake` | `account` | `tracking` | `preflight` | `nested_envelopes` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `runtime_memory` | `frontend_behavior_trace` | `none` to `full` | `none` to `full` | `none` to `full` | `not_applicable` to `full` | `none` to `full` | `none` to `full` | `not_applicable` to `full` |
| `run_history_export` | `harness_local_trace_store` | `none` to `full` | `none` to `full` | `none` to `full` | `not_applicable` to `full` | `none` to `full` | `none` to `full` | `not_applicable` to `full` |
| `usage_export` | `cloud_trace_sync` | `none` to `full` | `none` to `full` | `none` to `full` | `none` to `full` | `none` to `full` | `none` to `full` | `not_applicable` to `full` |
| `failure_journal` | `continuous_self_improvement` | `partial` to `full` | `none` to `full` | `none` to `full` | `not_applicable` to `full` | `partial` to `full` | `none` to `full` | `not_applicable` to `full` |

## Slot family contracts, swappable engines, and benchmarks

All latency benchmarks below were measured over 10 iterations per engine on the
verification host using `run_all_benchmarks()` in
[tools/trace_and_self_improvement_engines.py](../../tools/trace_and_self_improvement_engines.py).

### Slot Family A: `frontend_behavior_trace`

This slot captures privacy-respecting frontend interaction telemetry (`page_view`,
`funnel_step`, `ui_action`, `ui_error`, `diagnostic_report`, `feedback_submit`)
under the constraints of [docs/legal/PRIVACY-NOTICE.md](../legal/PRIVACY-NOTICE.md):
zero tracking cookies (`cookies_set == 0`), zero third-party ad beacons, and
automatic preflight scrubbing of credentials and personal identifiers.

| Engine ID | Primary mechanism | p50 latency (us) | p95 latency (us) | Cookies set | Redactions per call (synthetic PII load) |
| :--- | :--- | ---: | ---: | ---: | ---: |
| `in_tab_session_ring_buffer` | Bounded in-tab ring buffer with rotating ephemeral session salt and friction score computation | 336.604 | 631.612 | 0 | 0 |
| `aggregate_funnel_step_counter` | Zero-identifier aggregate funnel transition counter and drop-off detector | 322.439 | 449.583 | 0 | 0 |
| `voluntary_redacted_diagnostic_bundle` | Explicit user-initiated (`user_opted_in=True`) diagnostic bundle packager with recursive PII and secret redaction | 544.255 | 746.675 | 0 | 6 |

Fallback cascade verification: when `in_tab_session_ring_buffer` encounters a
simulated storage quota failure, `SevenLayerSlotEnvelope` automatically falls
back to `aggregate_funnel_step_counter` and preserves aggregate funnel counts.

### Slot Family B: `harness_local_trace_store`

This slot persists structured step execution traces, failure journals, and
recovery outcomes (`run_id`, `step_id`, `slot_id`, `engine_id`, `outcome`,
`error_code`, `latency_ms`, `tokens_used`, `payload_digest`) inside the local
harness without blocking execution when a disk is full or read-only.

| Engine ID | Storage backend | p50 latency (us) | p95 latency (us) | Durability and bounds |
| :--- | :--- | ---: | ---: | :--- |
| `local_sqlite_wal_trace_store` | Local SQLite database with `PRAGMA journal_mode=WAL` and indexed queries by `run_id`, `slot_id`, and `error_code` | 32817.223 | 842418.180 | Crash-safe transactional persistence on writable local filesystems |
| `local_jsonl_ring_spool` | Size-capped append-only JSONL ring spool with automatic segment rotation and retention pruning | 1483.736 | 1643.905 | Bounded disk usage (`max_segment_bytes` and `max_segments`) without SQLite locks |
| `in_memory_ephemeral_trace_buffer` | Zero-disk bounded `collections.deque` ring buffer | 424.604 | 664.269 | Runs in read-only sandboxes or restricted containers with zero filesystem writes |

Fallback cascade verification: when both `local_sqlite_wal_trace_store` and
`local_jsonl_ring_spool` are pointed at an unreachable read-only path,
`SevenLayerSlotEnvelope` falls back to `in_memory_ephemeral_trace_buffer` and
completes the trace write in memory.

### Slot Family C: `cloud_trace_sync`

This slot synchronizes scrubbed local trace digests and usage summaries to the
Baltor cloud ingestion endpoint with content-addressed idempotency keys
(`batch_digest`), per-account rate and byte budget enforcement, and offline
circuit breaking.

| Engine ID | Sync mode | p50 latency (us) | p95 latency (us) | Compression ratio (repeated failure burst) |
| :--- | :--- | ---: | ---: | ---: |
| `cloud_batch_digest_exporter` | Deduplicates identical `(slot_id, engine_id, outcome, error_code, payload_digest)` tuples into aggregated rollups before export | 2639.344 | 3951.306 | 11.0x |
| `edge_worker_beacon_exporter` | Enforces a strict 64 KiB beacon frame ceiling and emits lightweight telemetry summaries for browser and edge profiles | 2249.669 | 2561.863 | 1.0x |
| `offline_spool_with_circuit_breaker` | Tracks endpoint failure streaks, opens a circuit breaker after threshold failures, spools batches locally, and replays idempotently on recovery | 3209.340 | 5034.743 | 1.0x |

Fallback cascade verification: when the cloud endpoint is unreachable,
`cloud_batch_digest_exporter` and `edge_worker_beacon_exporter` return network
refusals and `SevenLayerSlotEnvelope` selects
`offline_spool_with_circuit_breaker`, preserving the batch in the local spool
for idempotent replay when connectivity returns.

### Slot Family D: `continuous_self_improvement`

This slot executes the closed-loop self-improvement pipeline over accumulated
trace digests and user feedback records:

1. **Stage 1 (Observation and aggregation)**: Groups failure clusters, latency
   outliers, and negative feedback signals.
2. **Stage 2 (Root-cause diagnosis and candidate generation)**: Synthesizes
   engine priority adjustments, query relaxation rules, or LSH token aliases.
3. **Stage 3 (Independent multi-metric Pareto verification)**: Enforces the
   constitutional rule that a producer never approves its own work
   (`producer_id != reviewer_id`) and checks that held-out quality (`top1`,
   `mrr`), latency (`p95_ms`), error rate, and safety (`secret_leak_count == 0`,
   `known_wrong_pass_count == 0`) do not regress.
4. **Stage 4 (Canary promotion and automatic rollback)**: Emits a canary routing
   promotion or triggers an immediate rollback if post-promotion error rates
   exceed `rollback_error_ceiling`.

| Engine ID | Pipeline stage | p50 latency (us) | p95 latency (us) | Verification behavior |
| :--- | :--- | ---: | ---: | :--- |
| `heuristic_gap_cluster_improver` | Stage 1 and Stage 2 diagnosis and candidate synthesis | 694.133 | 5562.436 | Ranks failure clusters by frequency and impact and proposes fallback order updates |
| `lsh_alias_and_query_relaxation_synthesizer` | Stage 1 and Stage 2 lexical alias and query relaxation synthesis | 536.517 | 5081.102 | Extracts missed query tokens via 3-gram minhashing and synthesizes deterministic alias maps |
| `harmony_pareto_verified_promoter` | Stage 3 and Stage 4 independent Pareto verification and canary promotion | 410.490 | 980.044 | Refuses self-approval, verifies Pareto dominance, and executes canary rollback on error spikes |

## Adversarial and known-wrong verification

The test suite in
[tools/test_trace_and_self_improvement_engines.py](../../tools/test_trace_and_self_improvement_engines.py)
verifies eight explicit refusal conditions:

1. **Raw credential leakage (`preflight_secret_leak_refused`)**: Injecting a
   `baltor_` API key or `sk-` secret into a trace record with
   `allow_auto_scrub=False` is refused at Layer 6 before any SQLite or JSONL
   write occurs.
2. **Pure self-repair scrubbing (`allow_auto_scrub=True`)**: Injecting `baltor_`,
   `sk-`, `ghp_`, `Bearer`, email addresses, and `/home/username/...` paths
   into a frontend trace scrubs all sensitive substrings in a cloned request
   without mutating the caller's input dictionary.
3. **Unconsented diagnostic bundle (`consent_required_for_diagnostic_bundle`)**:
   Calling `voluntary_redacted_diagnostic_bundle` with `user_opted_in=False` is
   refused at preflight.
4. **Anonymous cloud sync (`account_authentication_required`)**: Calling
   `cloud_trace_sync` with an anonymous `AccountContext` when authentication is
   required is refused at Layer 4.
5. **Account byte budget exhaustion (`account_byte_budget_exceeded`)**: Sync
   batches exceeding `max_bytes_per_window` are refused with a budget
   remediation message.
6. **Edge beacon oversize (`edge_beacon_payload_too_large`)**: Payloads
   exceeding `max_beacon_bytes` on `edge_worker_beacon_exporter` are refused and
   cascaded to the next engine.
7. **Producer self-approval (`self_approval_forbidden`)**: Submitting a
   candidate patch where `producer_id == reviewer_id` is refused before
   `harmony_pareto_verified_promoter` can promote the candidate.
8. **Pareto regression and nested cycle refusal (`pareto_regression_refused`,
   `nested_envelope_cycle_detected`)**: Candidates that degrade `top1`, `mrr`,
   `p95_ms`, or `error_rate`, or nested invocations that revisit an active slot
   in `visited_slots`, are deterministically refused.

## Reproduction commands and limits

Run the unit test suite and benchmark self-test from the repository root:

```bash
PYTHONPATH=src:tools python3 -m unittest -v tools/test_trace_and_self_improvement_engines.py
PYTHONPATH=src:tools python3 tools/trace_and_self_improvement_engines.py
```

Current limits:

- The benchmark harness measures local SQLite, filesystem, and in-process
  transport adapters so that verification remains deterministic and offline in
  continuous integration.
- Production network transport for `cloud_trace_sync` requires an authenticated
  account session and explicit host configuration.

## References

- [Envelope runtime implementation](../../src/loop_engine/core/engines/envelope.py)
- [Envelope preflight checks](../../src/loop_engine/core/engines/envelope_preflight.py)
- [Envelope tracking primitives](../../src/loop_engine/core/engines/envelope_tracking.py)
- [Component envelope coverage baseline](../../src/loop_engine/data/component_envelope_coverage_baseline.yaml)
- [Privacy notice](../legal/PRIVACY-NOTICE.md)
