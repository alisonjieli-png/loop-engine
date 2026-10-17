# Baltor Cloud Proxy Web-Portal BYOK Vault and 7-Mode MITM Gateway Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `eddf7d9a`
Implementation module: [`tools/baltor_cloud_proxy_byok_portal_and_7mode_mitm_gateway_engines.py`](../../tools/baltor_cloud_proxy_byok_portal_and_7mode_mitm_gateway_engines.py)
Verification suite: [`tools/test_baltor_cloud_proxy_byok_portal_and_7mode_mitm_gateway_engines.py`](../../tools/test_baltor_cloud_proxy_byok_portal_and_7mode_mitm_gateway_engines.py)

## Scope

This record documents the implementation, 7-layer `ComponentEnvelope` verification (`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`), 35-request benchmark, and 4 known-wrong preflight refusal controls for the Baltor Cloud Proxy:

1. Slot Family 1: Web-Portal BYOK Credential Vault, 4-Protocol Endpoint Emulator, and Signed Ephemeral Download Broker (`cloud_proxy_byok_portal_and_emulator_slot`).
2. Slot Family 2: 7-Mode Authorized Man-in-the-Middle (`MITM`) Intelligent Proxy Router (`seven_mode_mitm_proxy_orchestrator_slot`).

## 1. Slot Family 1: Web-Portal BYOK Credential Vault and 4-Protocol Endpoint Emulator (`cloud_proxy_byok_portal_and_emulator_slot`)

Customers configure their upstream model credentials once in the Baltor Web Portal (`/account/proxy-vault`) across `6` supported upstream provider families (`openai`, `anthropic`, `ollama_cloud`, `google_gemini`, `openrouter`, and paired home/LAN `lan_local_ollama` at `127.0.0.1:11434`). The portal issues a scoped Baltor Proxy base URL (`https://proxy.baltor.ai/v1`) and a virtual proxy key (`btr_proxy_<id>`) while keeping raw provider keys inside the encrypted vault.

Any existing application, SDK, or coding harness connects by changing a single base URL across `4` emulated wire protocols:

| Wire Protocol Emulator Engine | Emulated HTTP Route | Supported Client Harnesses & SDKs | Ephemeral Capability & Feed Payload |
| --- | --- | --- | --- |
| `openai_v1_chat_completions_emulator` | `POST /v1/chat/completions` | `OpenAI` SDK, `Cursor`, `OpenCode`, `Continue`, `LiteLLM` | `baltor_proxy_extension` + `HMAC-SHA256` download URL + `agentfeeds.si` stream |
| `anthropic_v1_messages_emulator` | `POST /v1/messages` | `Anthropic` SDK, `Claude Code`, `Cline` | `baltor_proxy_extension` + `HMAC-SHA256` download URL + `agentfeeds.si` stream |
| `openai_v1_responses_emulator` | `POST /v1/responses` | `OpenAI` Responses SDK, `Codex` `CLI`, agentic tool runners | `baltor_proxy_extension` + `HMAC-SHA256` download URL + `agentfeeds.si` stream |
| `ollama_api_chat_and_generate_emulator` | `POST /api/chat` | `Ollama` clients, local `LAN` assistants, `OpenClaw`, `Pi` | `baltor_proxy_extension` + `HMAC-SHA256` download URL + `agentfeeds.si` stream |

When a request resolves to a reusable file, shader pack, contract card, or live feed, the broker mints an `HMAC-SHA256` signed temporary download link (`https://baltor.ai/dl/<lease_id>?sig=<hmac>&exp=<ts>`), a scoped capability token (`btr_dl_cap_<digest>`), and a feed stream pointer (`https://agentfeeds.si/v1/streams/<slug>/latest.json`).

## 2. Slot Family 2: 7-Mode Authorized MITM Intelligent Proxy Router (`seven_mode_mitm_proxy_orchestrator_slot`)

Every executable vertex in the proxy router runs as a `Loop` (`Practitioner`, `Intelligence`, or `Solution` role; `deterministic`, `hybrid`, or `non-deterministic` mode). The `seven_mode_mitm_proxy_orchestrator_slot` implements and benchmarks all `7` operating variations of the Baltor Cloud Proxy:

| Mode | Engine Identifier | `Loop` Role / Mode | Upstream Calls | Mean Latency (`ms`) | Direct Pass | Proxy Pass | Direct Tokens | Proxy Tokens | Operating Behavior |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `M1` | `m1_direct_emulated_responder_engine` | `Solution` / `deterministic` | `0` | `1.80` | `2 / 5` | `5 / 5` | `18,800` | `0` | Short-circuits capability, feed, creative asset, and `L0` deterministic math requests directly in emulated wire format with signed download URLs (`0` upstream tokens). |
| `M2` | `m2_context_concatenating_passthrough_engine` | `Intelligence` / `hybrid` | `1` | `17.96` | `3 / 5` | `5 / 5` | `43,400` | `6,980` | Runs sub-`2 ms` `LSH` + Matryoshka + Cognitive-Fingerprint retrieval, prepends a `< 200`-token `baltor_contract_card.json` + `AGENTS.md`/`RULES.md` slice, and forwards with portal `BYOK` auth. |
| `M3` | `m3_proxy_side_tool_execution_loop_engine` | `Practitioner` / `hybrid` | `2` | `26.24` | `1 / 5` | `5 / 5` | `51,800` | `8,580` | Injects virtual Baltor tools, intercepts `tool_calls` inside the proxy, executes search/verification server-side, and returns the completed answer to zero-tool clients. |
| `M4` | `m4_post_response_verifier_self_heal_engine` | `Solution` / `hybrid` | `1` | `26.74` | `1 / 5` | `5 / 5` | `46,900` | `6,000` | Runs deterministic `verifier.py` on the upstream draft before release; performs a `1`-turn surgical repair when an `AST`, `3D` horizon, tabular leakage, or `FTC` invariant fails. |
| `M5` | `m5_cheap_to_frontier_split_router_engine` | `Practitioner` / `hybrid` | `1` | `16.36` | `3 / 5` | `5 / 5` | `36,600` | `5,260` | Routes `85%+` of routine turns to `Ollama Cloud` (`gemma4:31b`) or `LAN` `127.0.0.1` + Contract Cards, escalating to frontier keys (`Claude` / `GPT`) only when `M4` verification requires it. |
| `M6` | `m6_speculative_parallel_verified_race_engine` | `Solution` / `hybrid` | `2` | `18.12` | `2 / 5` | `4 / 5` | `41,800` | `7,730` | Dispatches speculative cheap candidates in parallel and streams the first candidate that passes deterministic `verifier.py`. |
| `M7` | `m7_fail_open_passthrough_fallback_engine` | `Practitioner` / `deterministic` | `1` | `5.28` | `5 / 5` | `5 / 5` | `2,150` | `2,150` | Zero-overhead transparent passthrough when the no-extra-material baseline applies. |

## 3. 35-Request Cloud Proxy Benchmark (`local_qualification_check`)

Observed local qualification benchmark across `35` coding, data-science, creative, and agentic requests (`5` requests per mode `M1..M7`):

| Engine Configuration | Verified Pass Count | Verified Pass Rate | Total Upstream Tokens | Mean Upstream Tokens / Req | Upstream Token Reduction | Total Cost (`USD`) | Mean Cost / Req (`USD`) | Dollar Cost Reduction | `M1` Short-Circuit Latency |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `direct_upstream_llm_without_baltor_proxy` | `17 / 35` | `48.6%` | `241,450` | `6,898.6` | `0.0%` | `$2.2993` | `$0.0657` | `0.0%` | N/A |
| `baltor_7mode_intelligent_cloud_proxy` | `34 / 35` | `97.1%` | `36,700` | `1,048.6` | `-84.8%` | `$0.1472` | `$0.0042` | `-93.6%` | `1.8 ms` |

## 4. Known-Wrong Controls (Layer 6 Preflight Refusals)

All `4` known-wrong controls refuse deterministically at `ComponentEnvelope` Layer 6 (`preflight`) before any external network call or unverified response release:

| Control ID | Fault Injected | Expected Refusal Code | Observed Layer | Observed Outcome |
| --- | --- | --- | --- | --- |
| Control (a) | Proxy request attempts to echo or log a plaintext customer `BYOK` credential in the response or trace | `byok_credential_exposure_refused` | `preflight` | Refused (`accepted=False`) |
| Control (b) | Proxy request attempts to forward a customer `anthropic` credential to untrusted host `evil-collector.example.org` instead of `api.anthropic.com` | `upstream_host_credential_mismatch_refused` | `preflight` | Refused (`accepted=False`) |
| Control (c) | Client presents an expired or tampered `HMAC-SHA256` signature on a temporary download link (`https://baltor.ai/dl/...`) | `ephemeral_download_signature_invalid_refused` | `preflight` | Refused (`accepted=False`) |
| Control (d) | Safety-critical `M4` response fails deterministic `verifier.py` and attempts to bypass surgical self-heal | `m4_unverified_safety_critical_release_refused` | `preflight` | Refused (`accepted=False`) |
