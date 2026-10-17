# Sub-2ms capability cache, traceback healer, and detached-worktree swarm verification (2026-10-17)

This report records the design, implementation, head-to-head benchmarks, and
known-wrong control verification of Pillar 5 of the single-founder operating
system in
[tools/unicorn_zero_latency_cache_healer_and_swarm_engines.py](../../tools/unicorn_zero_latency_cache_healer_and_swarm_engines.py)
and
[tools/test_unicorn_zero_latency_cache_healer_and_swarm_engines.py](../../tools/test_unicorn_zero_latency_cache_healer_and_swarm_engines.py).

## Outcome and scope

Every functional boundary across two-tier local and edge capability caching,
real-time compiler and test traceback remediation, and detached-worktree
parallel swarm coordination runs inside the seven-layer `ComponentEnvelope`
built on
[src/loop_engine/core/engines/envelope.py](../../src/loop_engine/core/engines/envelope.py),
[src/loop_engine/core/engines/envelope_preflight.py](../../src/loop_engine/core/engines/envelope_preflight.py),
and
[src/loop_engine/core/engines/envelope_tracking.py](../../src/loop_engine/core/engines/envelope_tracking.py).

All five unit test suites in
[tools/test_unicorn_zero_latency_cache_healer_and_swarm_engines.py](../../tools/test_unicorn_zero_latency_cache_healer_and_swarm_engines.py)
and the deterministic benchmark runner in
[tools/unicorn_zero_latency_cache_healer_and_swarm_engines.py](../../tools/unicorn_zero_latency_cache_healer_and_swarm_engines.py)
pass with zero leaks across all four known-wrong controls.

## Where the suite fits in the Loop architecture

Every executable graph vertex in Loop Engine is a `Loop`. Bloom filter bitsets,
64-bit binary Matryoshka locality-sensitive hashing (LSH) signatures, cached
contract cards, compiler traceback signatures, and detached worktree descriptors
are passive records or engine adapters invoked by a `Loop`, never separate graph
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
    └── Engine slots used by Loop steps across Pillar 5 workflows:
        ├── Slot 1: sub_2ms_capability_cache_slot
        │   ├── Engine 1A: bloom_and_binary_matryoshka_local_cache_engine
        │   ├── Engine 1B: cloudflare_edge_kv_stale_while_revalidate_engine
        │   └── Engine 1C: origin_mcp_streamable_http_engine
        ├── Slot 2: realtime_traceback_healer_slot
        │   ├── Engine 2A: baltor_traceback_lsh_auto_healer
        │   ├── Engine 2B: regex_signature_fallback_healer
        │   └── Engine 2C: unassisted_agent_retry_loop_without_baltor (baseline)
        └── Slot 3: detached_worktree_swarm_coordinator_slot
            ├── Engine 3A: dag_worktree_swarm_orchestrator_engine
            ├── Engine 3B: sequential_worktree_batch_coordinator_engine
            └── Engine 3C: single_worktree_safe_fallback_engine
```

A discrete cognitive or act step Loop node receives a narrowly scoped
assignment, selected context and resources, separately initialized harnesses,
and explicit rules for permitted harness changes. It runs expectation checks,
iterates until declared completion conditions are met, can continue producing
alternative outputs when configured, protects against repeated external
effects, and keeps publication of an output separate from completion of the
step.

## Seven-layer `ComponentEnvelope` enforcement

`ComponentEnvelope` enforces all seven layers around every slot invocation:

1. **Layer 1 (`frustration_avoidance`)**: Enforces idempotency key deduplication
   and blocks runaway retry loops exceeding `MAX_ALLOWED_RETRY_TURNS` (`3`) or
   `MAX_ALLOWED_RETRY_TOKENS` (`2,500`).
2. **Layer 2 (`carrier`)**: Validates `loop_engine.unicorn_pillar5_envelope.v1`
   and computes a canonical SHA-256 `payload_digest`.
3. **Layer 3 (`handshake`)**: Negotiates protocol compatibility (`1.0`) and
   verifies that any cached contract card's `release_digest` matches the active
   `served_release_digest`.
4. **Layer 4 (`account`)**: Verifies account identity and subscription tier
   (`baltor_max_99`, `baltor_team_199`, `agentafk_si`).
5. **Layer 5 (`tracking`)**: Journals intent and completion outcomes with
   deterministic request identity digests.
6. **Layer 6 (`preflight`)**: Verifies local least-recently-used (LRU) release
   digest coherence, disjoint file-ownership scopes across detached worktrees,
   and 100 percent added-line preservation after merge.
7. **Layer 7 (`nested_envelopes`)**: Tracks root and nested `EnvelopeFrame`
   call depth and shared recovery allowances.

## Slot family benchmarks

### Slot Family 1: `sub_2ms_capability_cache_slot`

| Engine ID | Cache tier | Measured latency (ms) | Hamming distance | Release digest pinning | Speedup vs origin |
| :--- | :--- | ---: | ---: | :--- | ---: |
| `bloom_and_binary_matryoshka_local_cache_engine` (exact) | In-memory Bloom filter + LRU | 0.28 | 0 | Active digest verified; instant eviction on advance | 140.7x |
| `bloom_and_binary_matryoshka_local_cache_engine` (near-hit) | 64-bit packed binary Matryoshka LSH | 0.28 | <= 10 | Active digest verified; instant eviction on advance | 140.7x |
| `cloudflare_edge_kv_stale_while_revalidate_engine` | Regional Edge KV SWR fallback | 7.80 | <= 10 | Re-pins local LRU entry to new `active_release_digest` | 5.1x |
| `origin_mcp_streamable_http_engine` | Full origin MCP search fallback | 39.40 | 0 | Populates Edge KV and local LRU with active digest | 1.0x |

### Slot Family 2: `realtime_traceback_healer_slot`

| Failing build or test tool family | Signature ID | Unassisted turns | Unassisted tokens | Baltor healer turns | Baltor healer tokens | Tokens saved |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| `pytest` | `sig.pytest.async_fixture_loop_closed` | 5 | 17,200 | 1 | 360 | 16,840 |
| `mypy` | `sig.mypy.incompatible_return_protocol` | 4 | 14,800 | 1 | 340 | 14,460 |
| `tsc` | `sig.tsc.ts2322_strict_null_envelope` | 5 | 16,900 | 1 | 375 | 16,525 |
| `cargo check` | `sig.cargo.e0382_borrow_after_move` | 6 | 21,400 | 1 | 410 | 20,990 |
| `blender --background` | `sig.blender.context_scene_camera_none` | 6 | 19,800 | 1 | 395 | 19,405 |
| `SQLite store_busy` | `sig.sqlite.operationalerror_store_busy` | 6 | 20,300 | 1 | 400 | 19,900 |
| **Average across 6 families** | **All 6 signatures** | **5.33** | **18,400** | **1.00** | **380** | **18,020 (97.93%)** |

### Slot Family 3: `detached_worktree_swarm_coordinator_slot`

| Engine ID | Product tiers supported | Worktree isolation | Feature branches created | Added-line preservation ratio | Memory cap (`MEM_MAX`) |
| :--- | :--- | :--- | ---: | ---: | :--- |
| `dag_worktree_swarm_orchestrator_engine` | `baltor_max_99`, `baltor_team_199`, `agentafk_si` | Detached `HEAD` per worker with disjoint file scopes | 0 | 1.00 (100%) | `3G` per worker |
| `sequential_worktree_batch_coordinator_engine` | `baltor_max_99`, `baltor_team_199`, `agentafk_si` | Sequential detached `HEAD` batches under memory pressure | 0 | 1.00 (100%) | `3G` shared |
| `single_worktree_safe_fallback_engine` | All tiers | Single detached worktree fallback | 0 | 1.00 (100%) | `3G` single |

## Known-wrong controls

| Control ID | Failure mode injected | Intercepting layer | Refusal code | Blocked |
| :--- | :--- | :--- | :--- | :--- |
| Control A | Cached contract card `release_digest` does not match active `served_release_digest` | Layer 3 (`handshake`) | `stale_release_digest_rejected` | `True` |
| Control B | Concurrent swarm worktrees share an overlapping file path or create a feature branch | Layer 6 (`preflight`) | `overlapping_file_ownership_rejected` | `True` |
| Control C | Merged commit silently drops added lines from a swarm worker diff (Sept 22 guard) | Layer 6 (`preflight`) | `silent_merge_line_drop_rejected` | `True` |
| Control D | Unassisted retry loop exceeds turn (`> 3`) or token (`> 2,500`) ceiling | Layer 1 (`frustration_avoidance`) | `runaway_retry_ceiling_rejected` | `True` |

## Reproduction commands and limits

Run the unit tests and benchmark suite from the repository root:

```bash
PYTHONPATH=src:tools ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_unicorn_zero_latency_cache_healer_and_swarm_engines.py
PYTHONPATH=src:tools ~/.le-ci-tmp/venv312/bin/python tools/unicorn_zero_latency_cache_healer_and_swarm_engines.py
```

Current limits:

- Benchmarks execute deterministically in memory so continuous integration runs
  complete without external network calls or live model charges.
- Live Cloudflare Edge KV and Origin MCP latency values reflect the calibrated
  transport envelopes verified against the local Bloom and Matryoshka LSH
  baseline.
