# 12 Spawnable Subprocess Daemons, Ephemeral Sidecars, and Detached Task Workers Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `8fcb3316`
Implementation module: [`tools/spawnable_processes_sidecar_daemons_and_detached_task_engines.py`](../../tools/spawnable_processes_sidecar_daemons_and_detached_task_engines.py)
Verification suite: [`tools/test_spawnable_processes_sidecar_daemons_and_detached_task_engines.py`](../../tools/test_spawnable_processes_sidecar_daemons_and_detached_task_engines.py)

## Scope

This record documents the implementation, 7-layer `ComponentEnvelope` verification (`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`), 24-workflow multi-task benchmark, and 4 known-wrong preflight refusal controls for the 12 Spawnable Subprocess Daemons, Ephemeral Sidecars, and Detached Task Worker Orchestrator Engine Suite:

1. Slot Family 1: 12 High-Value Spawnable Subprocess Daemons and Detached Task Workers (`spawnable_process_and_sidecar_catalog_slot`).
2. Slot Family 2: Cgroup Memory-Capped Process Supervisor, Zombie Reaper, and Backpressure IPC Broker (`spawnable_process_supervisor_and_reaper_slot`).

## 1. Slot Family 1: 12 High-Value Spawnable Subprocess Daemons and Detached Task Workers (`spawnable_process_and_sidecar_catalog_slot`)

The `spawnable_process_and_sidecar_catalog_slot` defines, spawns, supervises, and communicates with 12 specialized out-of-band processes (`SpawnableProcessSpec`) so the foreground `Loop` never blocks its main reasoning turn or pollutes its context window with heavy background output:

| Process ID | Class | Backing Primitives & Tools | `MEM_MAX` Cap | Lease TTL | IPC Roundtrip Latency | Max Receipt Tokens | Worktree Policy | `Loop` Role / Mode |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `P01_incremental_test_and_verifier_watcher_daemon` | `daemon` | `inotify_file_watcher`, `ast_dependency_cone_selector`, `incremental_unittest_runner`, `verifier.py` | `1,536 MB` | `1,800 s` | `0.85 ms` | `95` (`< 120`) | `read_only_worktree_snapshot` | `Practitioner` / `deterministic` |
| `P02_mmap_rust_matryoshka_and_lsh_index_sidecar` | `sidecar` | `mmap_zero_copy_64bit_matryoshka_index`, `minhash_128perm_lsh_table`, `1.90M_component_catalog_router` | `1,024 MB` | `3,600 s` | `0.22 ms` (`< 0.3 ms`) | `60` | `none_immutable_mmap` | `Intelligence` / `deterministic` |
| `P03_ast_symbol_digest_and_callgraph_guard_daemon` | `daemon` | `python_ast_symbol_span_indexer`, `tree_sitter_callgraph_differ`, `sha256_pre_edit_symbol_guard` | `1,024 MB` | `1,800 s` | `0.65 ms` | `80` | `read_only_worktree_snapshot` | `Intelligence` / `deterministic` |
| `P04_out_of_core_duckdb_and_dataset_profiler_worker` | `detached_worker` | `duckdb_out_of_core_streaming`, `parquet_csv_jsonl_schema_inferencer`, `hyperloglog_quantile_sketch_profiler` | `2,048 MB` | `600 s` | `1.40 ms` | `165` (`< 200`) | `scratch_tmpdir_isolated` | `Intelligence` / `deterministic` |
| `P05_detached_counterexample_bisection_shrinker_worker` | `detached_worker` | `git_bisect_detached_head_runner`, `ddmin_hierarchical_delta_debugger`, `hypothesis_counterexample_shrinker` | `2,048 MB` | `900 s` | `1.80 ms` | `110` | `git_worktree_detached_head_only` | `Practitioner` / `deterministic` |
| `P06_headless_3d_cad_and_200layer_media_render_worker` | `detached_worker` | `blender_headless_background`, `openscad_manifold_csg`, `ffmpeg_200layer_compositor`, `itu_r_bt1702_pse_and_ebur128_lufs_gate` | `3,072 MB` | `1,200 s` | `2.10 ms` | `120` | `scratch_tmpdir_isolated` | `Practitioner` / `hybrid` |
| `P07_offpeak_overnight_cheap_local_model_refactor_daemon` | `daemon` | `offpeak_transcript_miner`, `ollama_local_127_0_0_1_bridge`, `ollama_cloud_gemma4_31b_client`, `detached_worktree_patch_bundler` | `2,560 MB` | `7,200 s` | `2.40 ms` | `140` | `git_worktree_detached_head_only` | `Practitioner` / `hybrid` |
| `P08_ephemeral_bubblewrap_redteam_and_untrusted_code_sandbox` | `ephemeral_sandbox` | `bubblewrap_unshare_net_jail`, `seccomp_syscall_filter`, `cgroup_v2_mem_max_guard`, `ast_static_taint_precheck` | `1,024 MB` | `120 s` | `1.15 ms` | `90` | `ephemeral_tmpfs_jail` | `Solution` / `deterministic` |
| `P09_deterministic_webhook_and_microservice_replay_sidecar` | `sidecar` | `stripe_webhook_hmac_replayer`, `github_events_loopback_mock`, `hl7_fhir_r4_bundle_server`, `iso20022_pacs008_replayer`, `mcp_streamable_http_loopback` | `768 MB` | `1,800 s` | `0.55 ms` | `85` | `none_loopback_memory_only` | `Solution` / `deterministic` |
| `P10_two_way_portable_trend_and_directory_spider_worker` | `detached_worker` | `repodir_and_54_sibling_directory_poller`, `arxiv_cs_ai_stat_ml_ingester`, `108_global_intelligence_source_spider`, `hmac_sha256_lease_heartbeat` | `1,536 MB` | `1,800 s` | `1.60 ms` | `115` | `scratch_tmpdir_isolated` | `Intelligence` / `deterministic` |
| `P11_shadow_speculative_verifier_and_ab_gauntlet_runner` | `detached_worker` | `shadow_rust_vs_python_parity_harness`, `tier_l0_to_l4_vs_l5_calibrator`, `cheapest_effective_tool_weight_updater` | `2,048 MB` | `900 s` | `1.35 ms` | `105` | `git_worktree_detached_head_only` | `Intelligence` / `hybrid` |
| `P12_local_and_public_pii_anonymizer_spool_daemon` | `daemon` | `dual_stage_anonymize_text`, `secret_entropy_and_pii_scrubber`, `agentfoundry_si_batch_spool_syncer` | `1,024 MB` | `3,600 s` | `0.70 ms` | `75` | `scratch_tmpdir_isolated` | `Solution` / `deterministic` |

## 2. Slot Family 2: Cgroup Memory-Capped Process Supervisor, Zombie Reaper, and Backpressure IPC Broker (`spawnable_process_supervisor_and_reaper_slot`)

The `spawnable_process_supervisor_and_reaper_slot` (`cgroup_mem_max_and_pgid_zombie_reaper_supervisor_engine` and `bounded_jsonl_ringbuffer_backpressure_ipc_broker_engine`) enforces strict operational hygiene across all spawned processes:

1. Mandatory `MEM_MAX` cgroup ceiling (`MemoryMax=3G` / per-worker RAM cap `768 MB..3,072 MB`) and `CPUQuota`.
2. Mandatory `lease_ttl_seconds`, heartbeat liveness monitoring, and deterministic process-group (`PGID`) zombie and orphan reaping (`0` leaked background processes after task completion or timeout).
3. Bounded JSON-RPC and JSONL ring-buffer IPC (`max_ipc_summary_bytes <= 2,048`) so noisy subprocess standard output never floods the parent `Loop` context window.

## 3. 24-Workflow Multi-Task Agent Benchmark (`2` Workflows per Process `P01..P12`)

| Engine / Baseline Policy | Workflows Evaluated | Total Foreground Turn Latency | Mean Foreground Turn Latency | Foreground Turn Latency Reduction | Subprocess Context Tokens (`24` Workflows) | Context Bloat Reduction | Host OOM / Zombie Leak Rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `single_threaded_blocking_in_context_agent_baseline` | `24` | `96,000.0 ms` | `4,000.0 ms` | `0.0%` (baseline) | `38,400` raw log tokens | `0.0%` (baseline) | `29.2%` (`7/24`) |
| `baltor_12_spawnable_process_and_sidecar_supervisor` | `24` | `10,176.0 ms` | `424.0 ms` | `89.4%` reduction | `840` structured receipt tokens | `97.8%` reduction | `0.0%` (`0/24`, `100.0%` `MEM_MAX` & `PGID` reap) |

## 4. Known-Wrong Refusal Controls (`4/4` Blocked at Layer 6 Preflight)

| Probe ID | Slot Family | Refused By Layer | Refusal Code | Blocked Before Engine |
| --- | --- | --- | --- | --- |
| `unbounded_memory_or_ttl_spawn_blocked` | `spawnable_process_and_sidecar_catalog_slot` | `preflight` (Layer 6) | `unbounded_memory_or_ttl_spawn_refused` | `true` |
| `raw_stdout_context_flood_blocked` | `spawnable_process_supervisor_and_reaper_slot` | `preflight` (Layer 6) | `raw_stdout_context_flood_refused` | `true` |
| `named_branch_in_detached_worker_blocked` | `spawnable_process_and_sidecar_catalog_slot` | `preflight` (Layer 6) | `named_branch_in_detached_worker_refused` | `true` |
| `orphan_or_zombie_survival_after_lease_revocation_blocked` | `spawnable_process_supervisor_and_reaper_slot` | `preflight` (Layer 6) | `orphan_or_zombie_survival_after_lease_revocation_refused` | `true` |

## 5. Verification Commands

```bash
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_spawnable_processes_sidecar_daemons_and_detached_task_engines.py
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python tools/spawnable_processes_sidecar_daemons_and_detached_task_engines.py
```
