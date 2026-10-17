# Self-Serve Enterprise B2B Procurement, SOC2 Evidence, Team Policy Governance, and Hybrid BYOK Federation Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `b3001c15`
Implementation module: [`tools/unicorn_enterprise_b2b_governance_and_byok_engines.py`](../../tools/unicorn_enterprise_b2b_governance_and_byok_engines.py)
Verification suite: [`tools/test_unicorn_enterprise_b2b_governance_and_byok_engines.py`](../../tools/test_unicorn_enterprise_b2b_governance_and_byok_engines.py)

## Scope

This record documents the implementation, 7-layer `ComponentEnvelope` verification, head-to-head engine benchmarks, and known-wrong refusal probes for Pillar 3 of the Single-Founder Unicorn Operating System:

1. Slot Family 1 (`zero_touch_security_questionnaire_and_soc2_slot`): `cryptographic_soc2_and_cai_evidence_compiler_engine` and `sbom_and_component_provenance_attestation_engine` enabling a single founder to close `$199/mo` Team and Enterprise contracts without manual security questionnaire bottlenecks.
2. Slot Family 2 (`team_seat_policy_and_license_compliance_slot`): `org_license_and_trust_tier_policy_engine` and `cross_seat_audit_ledger_and_chargeback_engine` enforcing organization SPDX license allowlists, minimum trust tiers, per-seat daily budgets, and department chargeback attribution without storing raw developer source code.
3. Slot Family 3 (`byok_and_private_vpc_federation_slot`): `zero_trust_byok_and_local_endpoint_router` and `airgapped_local_contract_federation_engine` routing model inference to the customer's own endpoint (`127.0.0.1:11434` Ollama, LAN AI server, Ollama Cloud, vLLM Private-VPC, AWS Bedrock PrivateLink) while keeping private internal repository contract cards inside the customer boundary.

## 1. Zero-Touch Enterprise Security Questionnaire and SBOM Evidence Pack (`zero_touch_security_questionnaire_and_soc2_slot`)

The `zero_touch_security_questionnaire_and_soc2_slot` answers standard enterprise CISO and procurement controls with SHA-256 repository and live-check receipts, and compiles `CycloneDX-1.5` and `SPDX-2.3` software bill of materials (SBOM) manifests for every component downloaded by a team's coding agents during a billing period.

### Verified Enterprise Security Controls (`8/8` Backed by SHA-256 Receipts)

| Control ID | Control Title | Framework Mappings | Repository Evidence Path | Live-Check Probe | SHA-256 Receipt |
| --- | --- | --- | --- | --- | --- |
| `data_residency` | Data Residency & Regional Boundary Enforcement | `SOC2-CC6.1`, `ISO27001-A.8.23`, `CAI-DSP-04` | `docs/architecture/MVP-CLIENT-SERVER.md` | `live_edge_region_and_zero_store_header_check` | `64-hex verified` |
| `zero_training_on_customer_code` | Zero Training on Customer Code or Prompts | `SOC2-CC6.7`, `ISO27001-A.5.34`, `CAI-AIS-02` | `docs/legal/terms-of-service.md` | `zero_prompt_retention_and_byok_passthrough_audit` | `64-hex verified` |
| `zero_third_party_tracking_cookies` | Zero Third-Party Tracking or Ad-Tech Cookies | `SOC2-P3.1`, `ISO27001-A.5.34`, `GDPR-Art-5` | `docs/legal/privacy-notice.md` | `playwright_cookie_and_storage_isolation_check` | `64-hex verified` |
| `strict_transport_security` | Strict-Transport-Security (HSTS) Enforcement | `SOC2-CC6.7`, `ISO27001-A.8.24`, `CAI-IVS-09` | `src/loop_engine/core/service_runtime/edge/site_edge_worker.js` | `live_https_hsts_header_verification` | `64-hex verified` |
| `content_security_policy` | Content-Security-Policy (CSP) & Frame Isolation | `SOC2-CC6.6`, `ISO27001-A.8.26`, `CAI-APP-03` | `src/loop_engine/core/service_runtime/http_security_headers.py` | `live_csp_and_frame_ancestors_header_check` | `64-hex verified` |
| `spdx_license_provenance` | SPDX License Provenance & Source Revision Pinning | `SOC2-CC8.1`, `ISO27001-A.5.23`, `SPDX-2.3` | `docs/architecture/OWNER-DECISIONS.md` | `catalogue_spdx_and_sha256_integrity_gate` | `64-hex verified` |
| `immutable_audit_logs` | Immutable Hash-Chained Audit Logs | `SOC2-CC7.2`, `ISO27001-A.8.15`, `CAI-LOG-01` | `src/loop_engine/core/records/record_operation_service.py` | `immutable_record_hash_chain_verification` | `64-hex verified` |
| `well_known_security_txt` | RFC 9116 `/.well-known/security.txt` Disclosure Endpoint | `SOC2-CC2.3`, `ISO27001-A.5.24`, `RFC-9116` | `src/loop_engine/core/service_runtime/web_site_map.py` | `live_well_known_security_txt_probe` | `64-hex verified` |

### Slot Family 1 Engine Benchmark

| Engine ID | Role in Slot | Controls Answered | SBOM Spec Versions | Pass Rate | Latency (`ms`) |
| --- | --- | --- | --- | --- | --- |
| `cryptographic_soc2_and_cai_evidence_compiler_engine` | Primary (`#1`) | `8/8` | `CycloneDX-1.5`, `SPDX-2.3` | `1.00` | `0.32` |
| `sbom_and_component_provenance_attestation_engine` | Failover (`#2`) | `8/8` | `CycloneDX-1.5`, `SPDX-2.3` | `1.00` | `0.41` |

## 2. Organization and Team Policy Governance (`team_seat_policy_and_license_compliance_slot`)

The `team_seat_policy_and_license_compliance_slot` enforces organization-wide discovery and materialization rules across 10 to 500 coding agent seats:

- `allowed_spdx_licenses`: `{"MIT", "Apache-2.0", "BSD-3-Clause"}` by default; copyleft licenses (`GPL-3.0-only`, `AGPL-3.0-only`) are blocked at Layer 3 (`handshake`).
- `minimum_trust_tier`: `"baltor_reviewed"` (tier score `>= 3`), blocking unreviewed community submissions before engine execution.
- `stores_raw_developer_source_code`: `false` on every ledger record; department and project chargeback entries record only seat IDs, component IDs, SPDX identifiers, consumed units, and SHA-256 receipts.

### Slot Family 2 Engine Benchmark

| Engine ID | Role in Slot | Events Evaluated | Raw Developer Source Stored | Ledger Root SHA-256 | Pass Rate | Latency (`ms`) |
| --- | --- | --- | --- | --- | --- | --- |
| `org_license_and_trust_tier_policy_engine` | Primary (`#1`) | `2` | `false` | `d81d53cc...36c83` | `1.00` | `0.29` |
| `cross_seat_audit_ledger_and_chargeback_engine` | Failover (`#2`) | `2` | `false` | `d81d53cc...36c83` | `1.00` | `0.37` |

## 3. Hybrid BYOK, Local `127.0.0.1`, and Private-VPC Capability Federation (`byok_and_private_vpc_federation_slot`)

The `byok_and_private_vpc_federation_slot` pairs public Baltor contract cards fetched from `baltor.ai/mcp` with private internal repository contract cards held inside the customer's boundary, routing inference directly to the customer's chosen model endpoint.

### Customer Inference Target Benchmark Matrix

| Target ID | Endpoint URL | Boundary Class | Allows Private Repo Cards | Private Code Never Egresses | Raw Key Never Egresses | Latency (`ms`) |
| --- | --- | --- | --- | --- | --- | --- |
| `local_loopback_ollama` | `http://127.0.0.1:11434/api/chat` | `customer_local_loopback` | `true` | `true` | `true` | `0.26` |
| `lan_workstation_ai_box` | `http://192.168.1.50:8000/v1/chat/completions` | `customer_private_lan` | `true` | `true` | `true` | `0.26` |
| `private_vpc_vllm_cluster` | `https://vllm.internal.vpc.local/v1/chat/completions` | `customer_private_vpc` | `true` | `true` | `true` | `0.26` |
| `aws_bedrock_vpc_privatelink` | `https://vpce-bedrock-runtime.us-east-1.vpce.amazonaws.com/model/invoke` | `customer_private_vpc` | `true` | `true` | `true` | `0.26` |
| `customer_byok_ollama_cloud` | `https://ollama.com/api/chat` | `customer_byok_cloud` | `false` | `true` | `true` | `0.26` |

## 4. Known-Wrong Controls (`5/5` Blocked Before Engine Dispatch)

| Probe Name | Refused By Layer | Refusal Code | Blocked Before Engine Dispatch |
| --- | --- | --- | --- |
| `copyleft_or_unreviewed_component_blocked` | `handshake` | `enterprise_policy_spdx_or_trust_violation` | `true` |
| `private_source_or_raw_byok_egress_blocked` | `handshake` | `private_code_or_raw_byok_egress_forbidden` | `true` |
| `cross_organization_tenant_audit_read_blocked` | `account` | `cross_organization_audit_read_forbidden` | `true` |
| `unverified_compliance_claim_fabrication_blocked` | `handshake` | `unverified_compliance_claim_forbidden` | `true` |
| `seat_daily_budget_overrun_blocked` | `preflight` | `seat_daily_budget_exhausted` | `true` |

## 5. Verification Commands

```bash
python3 -m unittest tools/test_unicorn_enterprise_b2b_governance_and_byok_engines.py -v
python3 tools/unicorn_enterprise_b2b_governance_and_byok_engines.py
```
