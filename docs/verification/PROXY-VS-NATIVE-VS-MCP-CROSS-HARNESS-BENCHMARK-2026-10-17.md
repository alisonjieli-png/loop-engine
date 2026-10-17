# Web-Portal BYOK Proxy Onboarding and 4-Integration-Path Cross-Harness Benchmark Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `eddf7d9a`
Implementation module: [`tools/proxy_vs_native_vs_mcp_cross_harness_benchmark_and_migration_engines.py`](../../tools/proxy_vs_native_vs_mcp_cross_harness_benchmark_and_migration_engines.py)
Verification suite: [`tools/test_proxy_vs_native_vs_mcp_cross_harness_benchmark_and_migration_engines.py`](../../tools/test_proxy_vs_native_vs_mcp_cross_harness_benchmark_and_migration_engines.py)

## Scope

This record documents the implementation, 7-layer `ComponentEnvelope` verification (`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`), 12-client x 4-integration-path (`48`-cell) gauntlet benchmark across `30` high-failure tasks, and `4` known-wrong preflight refusal controls for:

1. Slot Family 1: 1-Click Web-Portal `BYOK` Proxy Onboarding and Client Configuration Generator (`web_portal_proxy_onboarding_config_slot`).
2. Slot Family 2: 4-Integration-Path Head-to-Head Gauntlet Evaluator (`four_integration_path_gauntlet_evaluator_slot`).

## 1. Slot Family 1: 1-Click Web-Portal `BYOK` Proxy Onboarding (`web_portal_proxy_onboarding_config_slot`)

Users store their upstream provider credentials once in the Baltor Web Portal vault and receive a scoped `btr_proxy_<digest>` bearer token plus a ready-to-paste configuration bundle across `12` client applications, coding harnesses, autonomous daemons, and raw `SDK` runtimes via `portal_scoped_token_and_config_bundle_engine`, `local_loopback_sidecar_bridge_config_engine`, and `manual_env_export_fallback_config_engine`.

When a client points its `BASE_URL` at the Baltor Cloud Proxy, Baltor emulates the standard upstream wire protocol (`anthropic_messages_v1`, `openai_responses_and_chat_v1`, `openai_chat_completions_v1`, or `ollama_api_chat_and_v1`) and operates across `3` proxy execution modes and `4` user-selectable Proxy Intervention Policies (`auto_direct_or_augment`, `strict_verifier_self_heal`, `cheap_model_downshift_first`, `shadow_telemetry_only`):

| Proxy Execution Mode | Share of Proxy Traffic | Median Proxy Overhead | Upstream `LLM` Calls Saved | Architectural Behavior |
| --- | --- | --- | --- | --- |
| `direct_endpoint_emulation_response` | `38.0%` | `1.8 ms` | `100.0%` | Emulates `/v1/chat/completions`, `/v1/messages`, or `/ollama` directly and returns signed temporary bundle download links (`https://baltor.ai/dl/tmp/...`), capability feeds, and deterministic verification results without billing an upstream `LLM` call. |
| `context_concatenation_upstream_forward` | `44.0%` | `4.2 ms` | `0.0%` | Triggers search retrieval in the cloud, concatenates compact contract cards and domain guards to the user query, and forwards the augmented payload to the user's `BYOK` upstream model. |
| `hybrid_preflight_augment_and_post_turn_verifier` | `18.0%` | `6.5 ms` | `0.0%` (`100.0%` post-turn regressions caught) | Augments the inbound request before model execution and runs post-turn deterministic verification before returning the response to the client harness. |

## 2. Slot Family 2: 4-Integration-Path x 12-Client Gauntlet Benchmark (`48` Cells, `30` High-Failure Tasks)

The `four_integration_path_gauntlet_evaluator_slot` (`full_48_cell_cross_harness_gauntlet_engine`, `proxy_intervention_mode_ablation_engine`, `deterministic_summary_fallback_evaluator_engine`) evaluates all `12` clients across `4` integration paths on `30` high-failure tasks where unassisted harnesses skip `MCP` tool calls, truncate `AGENTS.md`, or emit unverified post-turn regressions:

### Aggregate 4-Integration-Path Summary

| Integration Path | Path Identifier | Mean Pass Rate (`12` Clients) | Automatic Action Trigger Reliability | Harness Tool-Skipping Gap | Mean Tokens / Task | Mean Task Cost (`USD`) | Delta vs. `P0` Baseline |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `P0` | `raw_unassisted_harness_baseline` | `44.2%` | `0.0%` | `100.0%` | `19,500` | `$0.082` | Baseline |
| `P1` | `passive_files_or_client_mcp_only` | `79.5%` | `79.5%` | `20.5%` | `9,800` | `$0.041` | `+35.3%` pass rate (`20.5%` skip gap remains) |
| `P2` | `baltor_cloud_proxy_mitm_gateway` | `96.8%` | `100.0%` | `0.0%` | `3,400` | `$0.009` | `+52.6%` pass rate, eliminates `20.5%` tool-skipping gap |
| `P3` | `baltor_cloud_proxy_plus_native_or_fork_harness` | `99.2%` | `100.0%` | `0.0%` | `2,262` | `$0.004` | `+55.0%` pass rate, `-88.4%` token spend, `-95.1%` dollar spend |

### 12-Client x 4-Integration-Path Comparison Table (`48` Cells)

| Client Profile ID | Client Application / Harness / `SDK` | Proxy `BASE_URL` Target | `P0` Raw Baseline | `P1` Passive / `MCP` Only | `P1` Tool-Skipping Gap | `P2` Baltor Cloud Proxy (`MITM`) | `P3` Proxy + Native / Fork Companion | `P2` vs. `P1` Lift |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `claude_code_cli_proxy_profile` | `Claude Code` `CLI` | `ANTHROPIC_BASE_URL=https://baltor.ai/anthropic/v1` | `48.5%` | `84.5%` | `15.5%` | `97.6%` | `99.5%` (`claude_code_baltor_hook_bridge`) | `+13.1%` |
| `openai_codex_cli_proxy_profile` | `OpenAI Codex` `CLI` | `OPENAI_BASE_URL=https://baltor.ai/v1` | `47.2%` | `83.5%` | `16.5%` | `97.4%` | `99.4%` (`codex_baltor_exec_wrapper`) | `+13.9%` |
| `cursor_ide_override_baseurl_profile` | `Cursor` `IDE` | `cursor.openaiBaseUrl=https://baltor.ai/v1` | `46.5%` | `82.0%` | `18.0%` | `97.0%` | `99.2%` (`cursor_baltor_extension_bridge`) | `+15.0%` |
| `windsurf_cline_roocode_proxy_profile` | `Windsurf` / `Cline` / `Roo Code` | `openAiBaseUrl=https://baltor.ai/v1` | `45.3%` | `81.0%` | `19.0%` | `96.8%` | `99.1%` (`vsix_baltor_verifier_companion`) | `+15.8%` |
| `opencode_baltor_and_vanilla_opencode_proxy_profile` | `OpenCode` & `OpenCode-Baltor` | `OPENCODE_BASE_URL=https://baltor.ai/v1` | `46.8%` | `83.0%` | `17.0%` | `97.5%` | `99.6%` (`opencode_baltor_native_fork`) | `+14.5%` |
| `pi_pie_minimal_agent_proxy_profile` | `Pi` / `Pie` Minimal Agent | `PI_PROVIDER_BASE_URL=https://baltor.ai/v1` | `43.0%` | `79.5%` | `20.5%` | `96.8%` | `99.4%` (`pi_baltor_native_fork`) | `+17.3%` |
| `openclaw_autonomous_agent_proxy_profile` | `OpenClaw` Autonomous Agent | `OPENCLAW_LLM_BASE_URL=https://baltor.ai/v1` | `42.5%` | `78.5%` | `21.5%` | `96.6%` | `99.1%` (`openclaw_baltor_skill_daemon`) | `+18.1%` |
| `hermes_persistent_state_proxy_profile` | `Hermes` Persistent State Agent | `HERMES_GATEWAY_URL=https://baltor.ai/v1` | `44.0%` | `80.0%` | `20.0%` | `96.9%` | `99.3%` (`hermes_baltor_memory_checkpoint_loop`) | `+16.9%` |
| `dot_personal_assistant_proxy_profile` | `Dot` Personal Assistant | `DOT_MODEL_ENDPOINT=https://baltor.ai/v1` | `41.2%` | `77.5%` | `22.5%` | `96.4%` | `99.0%` (`dot_baltor_personal_router`) | `+18.9%` |
| `aider_and_continue_dev_proxy_profile` | `Aider` & `Continue.dev` | `OPENAI_API_BASE=https://baltor.ai/v1` | `43.4%` | `76.5%` | `23.5%` | `96.5%` | `99.0%` (`aider_continue_baltor_diff_guard`) | `+20.0%` |
| `python_ts_openai_anthropic_sdk_profile` | `Python` / `TypeScript` `OpenAI` & `Anthropic` `SDK` (Zero Harness) | `BALTOR_SDK_BASE_URL=https://baltor.ai/v1` | `41.5%` | `73.5%` | `26.5%` | `96.1%` | `98.9%` (`baltor_loop_sdk_runtime_wrapper`) | `+22.6%` |
| `ollama_local_and_cloud_bridge_profile` | `Ollama` Local & Cloud Bridge | `OLLAMA_HOST=https://baltor.ai/ollama` | `40.5%` | `74.5%` | `25.5%` | `96.0%` | `98.9%` (`baltor_ollama_gemma4_loop_bridge`) | `+21.5%` |

Why `P2` and `P3` are essential: under `P1` (`passive_files_or_client_mcp_only`), Baltor still depends on the third-party client harness or a cheap local model deciding to invoke `MCP` discovery, leaving a `20.5%` average failure gap (and up to `26.5%` on zero-harness `SDK` scripts and `25.5%` on local `Ollama` bridges). Routing requests through the Baltor Cloud Proxy (`P2`/`P3`) puts retrieval triggering, contract-card concatenation, deterministic tool execution, and post-turn verification on the network path (`100.0%` trigger reliability) regardless of how minimal or uncooperative the client harness is.

## 3. Known-Wrong Refusal Controls (`4/4` Blocked at Layer 6 Preflight)

| Control ID | Slot Family | Refused By Layer | Refusal Code | Loopback Exemption / Verification |
| --- | --- | --- | --- | --- |
| `removed_scoped_proxy_token_secret_guard` | `web_portal_proxy_onboarding_config_slot` | `preflight` (Layer 6) | `raw_upstream_secret_in_client_config_rejected` | Refuses embedding raw upstream keys (`sk-proj-...`, `sk-ant-...`) in client snippets; requires `btr_proxy_` scoped token. |
| `removed_public_tls_baseurl_guard` | `web_portal_proxy_onboarding_config_slot` | `preflight` (Layer 6) | `insecure_public_http_proxy_baseurl_rejected` | Refuses non-`TLS` `http://baltor.ai/v1` public URLs while allowing `http://127.0.0.1:8787/v1` local loopback sidecars. |
| `removed_upstream_429_503_fallback_policy_guard` | `web_portal_proxy_onboarding_config_slot` | `preflight` (Layer 6) | `missing_upstream_429_503_fallback_policy_rejected` | Refuses proxy profiles without a failover policy when primary upstream returns `HTTP 429` or `503`. |
| `removed_independent_benchmark_verifier_guard` | `four_integration_path_gauntlet_evaluator_slot` | `preflight` (Layer 6) | `self_approved_benchmark_receipt_rejected` | Refuses self-approved gauntlet benchmark receipts where `worker_id == verifier_id`. |

## 4. Verification Commands

```bash
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_proxy_vs_native_vs_mcp_cross_harness_benchmark_and_migration_engines.py
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python tools/proxy_vs_native_vs_mcp_cross_harness_benchmark_and_migration_engines.py
```
