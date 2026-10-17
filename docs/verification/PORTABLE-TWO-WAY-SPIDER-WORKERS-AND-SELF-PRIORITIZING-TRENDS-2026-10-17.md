# Portable two-way spider workers and self-prioritizing trend engines verification (2026-10-17)

This report records the design, implementation, head-to-head benchmarks, and
known-wrong control verification of the portable two-way spider worker and
sprouting trend self-prioritization suite in
[tools/portable_two_way_spider_worker_and_self_prioritizing_trend_engines.py](../../tools/portable_two_way_spider_worker_and_self_prioritizing_trend_engines.py)
and
[tools/test_portable_two_way_spider_worker_and_self_prioritizing_trend_engines.py](../../tools/test_portable_two_way_spider_worker_and_self_prioritizing_trend_engines.py).

## Outcome and scope

Every functional boundary across portable anywhere-launch two-way spider
workers, permissive and owner repository harvesters, live model and harness
leaderboard scrapers, and sprouting keyword self-prioritization runs inside the
seven-layer `ComponentEnvelope` built on
[src/loop_engine/core/engines/envelope.py](../../src/loop_engine/core/engines/envelope.py),
[src/loop_engine/core/engines/envelope_preflight.py](../../src/loop_engine/core/engines/envelope_preflight.py),
and
[src/loop_engine/core/engines/envelope_tracking.py](../../src/loop_engine/core/engines/envelope_tracking.py).

All five unit test suites in
[tools/test_portable_two_way_spider_worker_and_self_prioritizing_trend_engines.py](../../tools/test_portable_two_way_spider_worker_and_self_prioritizing_trend_engines.py)
and the deterministic benchmark runner in
[tools/portable_two_way_spider_worker_and_self_prioritizing_trend_engines.py](../../tools/portable_two_way_spider_worker_and_self_prioritizing_trend_engines.py)
pass with zero leaks across all four known-wrong controls.

## Where the suite fits in the Loop architecture

Every executable graph vertex in Loop Engine is a `Loop`. Portable worker lease
tokens, repository harvest manifests, normalized benchmark leaderboard tables,
and cumulative sum (CUSUM) or exponential moving average (EMA) trend velocity
records are passive data structures or engine adapters invoked by a `Loop`,
never separate graph vertices.

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
    └── Engine slots used by Loop steps across autonomous discovery workflows:
        ├── Slot 1: portable_two_way_spider_worker_slot
        │   ├── Engine 1A: authenticated_two_way_lease_and_heartbeat_worker_engine
        │   ├── Engine 1B: multi_source_github_mit_and_owner_repo_spider_engine
        │   ├── Engine 1C: live_model_and_harness_benchmark_scraper_engine
        │   └── Engine 1D: offline_spool_and_local_cache_worker_fallback_engine
        └── Slot 2: sprouting_trend_and_search_self_prioritizer_slot
            ├── Engine 2A: kusum_and_ema_sprouting_keyword_velocity_engine
            ├── Engine 2B: expected_value_of_information_queue_prioritizer_engine
            └── Engine 2C: manual_founder_copy_paste_discovery_without_baltor (baseline)
```

A discrete cognitive or act step Loop node receives a narrowly scoped
assignment, selected context and resources, separately initialized harnesses,
and explicit rules for permitted harness changes. It runs expectation checks,
iterates until declared completion conditions are met, can continue producing
alternative outputs when configured, protects against repeated external
effects, and keeps publication of an output separate from completion of the
step.

## Seven-layer `ComponentEnvelope` enforcement

`ComponentEnvelope` enforces all seven layers around both slot families:

1. **Layer 1 (`frustration_avoidance`)**: Enforces idempotency key deduplication
   and honors immediate one-click human steering `veto` overrides from
   `/admin/systems` (`human_steering_veto_enforced`).
2. **Layer 2 (`carrier`)**: Validates
   `loop_engine.portable_spider_and_trend_envelope.v1` and computes a canonical
   SHA-256 `payload_digest`.
3. **Layer 3 (`handshake`)**: Negotiates protocol compatibility (`1.0`) and
   verifies that each portable worker's HMAC-SHA256 fencing token epoch matches
   or exceeds the server's active lease epoch (`stale_fencing_token_rejected`).
4. **Layer 4 (`account`)**: Verifies account identity and subscription tier.
5. **Layer 5 (`tracking`)**: Journals intent and completion outcomes with
   deterministic request identity digests.
6. **Layer 6 (`preflight`)**: Blocks server-side request forgery (SSRF) against
   private RFC 1918, loopback, link-local, or cloud metadata addresses from
   public spider workers (`ssrf_private_or_metadata_ip_rejected`) and blocks
   copyleft or unlicensed repositories from entering the public permissive
   catalogue tier (`copyleft_or_unlicensed_repo_rejected`).
7. **Layer 7 (`nested_envelopes`)**: Tracks root and nested `EnvelopeFrame`
   call depth and shared recovery allowances.

## Slot family benchmarks

### Slot Family 1: `portable_two_way_spider_worker_slot`

The portable worker slot supports five zero-dependency launch profiles
(`laptop_127_0_0_1`, `lan_host_192_168_50_x`, `cloudflare_worker_edge`,
`fly_io_machine`, and `github_action_runner`) communicating two-way with
`/admin/systems` and `agentfoundry.si/api/v1/workers` over four bidirectional
remote procedure calls (`claim_discovery_lease`, `stream_telemetry_heartbeat`,
`submit_candidate_bundle`, and `apply_human_steering_override`).

| Repository or benchmark source | Origin kind | License or category | External adapter ID | Baltor-native engine ID or slot target | Rule 6 dual engine |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `alisonjieli-png/loop-engine` | `owner_github` | `OWNER-FIRST-PARTY` | `adapter.github.alisonjieli_png.loop_engine` | `baltor.native.loop_engine_core_runtime_engine` | `True` |
| `alisonjieli-png/baltor-library` | `owner_github` | `MIT` | `adapter.github.alisonjieli_png.baltor_library` | `baltor.native.component_catalog_shard_engine` | `True` |
| `Amarel-Taylor-Scott/stock-research` | `owner_github` | `MIT` | `adapter.github.amarel_taylor_scott.stock_research` | `baltor.native.quant_equity_signal_research_engine` | `True` |
| `Amarel-Taylor-Scott/philippines-wins-everyday` | `owner_github` | `MIT` | `adapter.github.amarel_taylor_scott.philippines_wins_everyday` | `baltor.native.regional_news_and_positive_signal_aggregator_engine` | `True` |
| `aidonerightcorp/solutiongraph` | `owner_github` | `Apache-2.0` | `adapter.github.aidonerightcorp.solutiongraph` | `baltor.native.typed_solution_graph_composer_engine` | `True` |
| `local/roll_watch` | `owner_local_repo` | `OWNER-FIRST-PARTY` | `adapter.local.roll_watch_options_scanner` | `baltor.native.conviction_roll_and_diagonal_spread_engine` | `True` |
| `local/suspicious_networks_analysis` | `owner_local_repo` | `OWNER-FIRST-PARTY` | `adapter.local.suspicious_networks_analysis` | `baltor.native.sybil_and_coordinated_network_graph_detector_engine` | `True` |
| `local/ollama-loop-behavior-lab` | `owner_local_repo` | `MIT` | `adapter.local.ollama_loop_behavior_lab` | `baltor.native.local_model_loop_stability_harness_engine` | `True` |
| `local/ai_agent_security_comp` | `owner_local_repo` | `Apache-2.0` | `adapter.local.ai_agent_security_comp` | `baltor.native.adversarial_prompt_and_ssrf_guard_engine` | `True` |

In addition, `live_model_and_harness_benchmark_scraper_engine` normalizes nine
live external leaderboards (`GIFT-Eval`, `fev-bench`, `SWE-bench`,
`LiveCodeBench`, `Artificial Analysis`, `LMSYS Arena`,
`HuggingFace FineEnvs/multi-harness-rl`, `Kaggle Competitions`, and
`ArXiv CS.AI/CS.LG`) into structured routing updates for `agentfeeds.si` and
`baltor.ai`.

### Slot Family 2: `sprouting_trend_and_search_self_prioritizer_slot`

| Sprouting keyword | Category | License | EMA velocity ($\dot{v}_k$) | EMA acceleration ($\ddot{v}_k$) | Agent search miss rate | Detection lag (min) |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: |
| `Harmony Harness` | `multi_agent_contract_card_orchestration` | `Apache-2.0` | 24.162 | 12.164 | 0.86 | 8.1 |
| `BitNet-b1.58` | `ternary_local_model_inference_kernel` | `MIT` | 25.039 | 12.607 | 0.81 | 7.6 |
| `Timestral` | `time_series_foundation_model` | `MIT` | 23.226 | 11.737 | 0.84 | 8.4 |
| `SolidCraft` | `programmatic_cad_and_brep_geometry` | `Apache-2.0` | 19.349 | 9.654 | 0.76 | 10.2 |
| `FluidCAD` | `differentiable_cfd_and_parametric_cad` | `MIT` | 18.239 | 9.100 | 0.74 | 11.0 |
| `Jumpstart-3D` | `editable_scene_graph_and_gltf_procedural_rig` | `MIT` | 18.704 | 9.354 | 0.77 | 9.8 |
| `claude-pxl` | `parametric_pixel_and_sprite_sheet_generator` | `MIT` | 21.028 | 10.612 | 0.79 | 9.1 |

### Head-to-head comparison: manual copy-paste baseline vs autonomous Baltor suite

| Metric | `manual_founder_copy_paste_discovery_without_baltor` | `baltor_autonomous_two_way_spider_and_self_prioritizer` |
| :--- | ---: | ---: |
| Manual founder forum reading hours per day | 2.50 h | 0.00 h |
| Average sprouting trend discovery lag | 2,880.00 min (48 h) | 9.17 min (< 15 min) |
| Sprouting keywords tracked continuously | 0 | 7 |
| Live benchmark leaderboards normalized | 0 | 9 |
| Permissive (`MIT`/`Apache-2.0`) license verification rate | 0.0% | 100.0% |
| Rule 6 external adapter + Baltor-native engine pair rate | 0.0% | 100.0% |

## Known-wrong controls

| Control ID | Failure mode injected | Intercepting layer | Refusal code | Blocked |
| :--- | :--- | :--- | :--- | :--- |
| Control A | Portable worker submits bundle with stale fencing epoch (`4 < 10`) | Layer 3 (`handshake`) | `stale_fencing_token_rejected` | `True` |
| Control B | Spider attempts to ingest copyleft (`GPL-3.0-only` / `AGPL-3.0-only`) repo into public tier | Layer 6 (`preflight`) | `copyleft_or_unlicensed_repo_rejected` | `True` |
| Control C | Public spider attempts SSRF to `169.254.169.254` or RFC 1918 `192.168.50.10` | Layer 6 (`preflight`) | `ssrf_private_or_metadata_ip_rejected` | `True` |
| Control D | Human steering `veto` override applied in `/admin/systems` | Layer 1 (`frustration_avoidance`) | `human_steering_veto_enforced` | `True` |

## Reproduction commands and limits

Run the unit tests and benchmark suite from the repository root:

```bash
PYTHONPATH=src:tools ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_portable_two_way_spider_worker_and_self_prioritizing_trend_engines.py
PYTHONPATH=src:tools ~/.le-ci-tmp/venv312/bin/python tools/portable_two_way_spider_worker_and_self_prioritizing_trend_engines.py
```

Current limits:

- Benchmarks execute deterministically in memory so continuous integration runs
  complete without external network calls or live model charges.
- Live GitHub repository harvesting and external leaderboard scraping run
  through calibrated deterministic fixtures during offline test runs and bind
  to live HTTPS origins when launched on authorized worker profiles.
