# Eighteen-persona adversarial, strange-user, and executive emulation record

Kind: verification record. Date: 2026-10-16. Scope: deterministic offline
loopback emulation across 18 adversarial, strange-user, and executive personas
evaluated through four swappable defense and normalization engines over the
seven-layer component envelope.

## Useful outcome and scope

This verification suite tests whether the component envelope blocks malicious
traffic, repairs or guides confused user requests without repeating effects, and
satisfies buyer, executive, and competitor boundary checks before launch. The
suite runs offline in [`tools/adversarial_persona_suite.py`](../../tools/adversarial_persona_suite.py)
and [`tools/test_adversarial_persona_suite.py`](../../tools/test_adversarial_persona_suite.py)
with zero network calls, zero provider writes, and zero model spend.

The 18 personas span three groups of six:

1. Malicious personas (`P-BAD-01` to `P-BAD-06`) test bulk catalogue scraping,
   indirect prompt injection, Server-Side Request Forgery (SSRF), cross-site
   scripting (XSS), SQL injection, staff-surface and cross-tenant Indirect
   Object Reference (IDOR) probing, billing webhook replay, transactional email
   budget exhaustion, oversized payloads, regular-expression denial of service,
   envelope nesting cycles, and unconfirmed-email pre-registration hijacking.
2. Strange or confused user personas (`P-STRANGE-01` to `P-STRANGE-06`) test
   copy-pasted smart quotes and duplicate `Bearer` prefixes, multi-tab rapid
   double-clicking under one request identity, 80-line polyglot and emoji stack
   traces pasted into search, mid-session rotated API keys, truncated JSON-RPC
   requests on a 320-pixel mobile viewport, and `127.0.0.1` loopback harness
   endpoints with non-canonical version strings and unsupported advisory flags.
3. Buyer, executive, and competitor personas (`P-EXEC-01` to `P-EXEC-06`) test
   enterprise Chief Technology Officer (CTO) provenance and fail-closed
   handshakes, Chief Financial Officer (CFO) token budget caps and billing
   record clarity, technical Venture Capital (VC) coverage ratchet and journal
   hash-chain auditing, solo creative studio contract-card discovery and clean
   reopen, Sustainable Development Goal (SDG) zero-cost baseline access, and
   competitor probing of public cards versus protected source bytes.

## Where the emulation suite fits in the system

Every executable graph vertex is a `Loop`. The envelope layers are internal
steps that one envelope `Loop` runs between its edge contract and its engine
slot, as defined in
[`docs/architecture/ADR-COMPONENT-ENVELOPE-LAYERS.md`](../architecture/ADR-COMPONENT-ENVELOPE-LAYERS.md)
and [`src/loop_engine/core/engines/envelope.py`](../../src/loop_engine/core/engines/envelope.py).

```text
Operational runtime type
└── Loop
    ├── Operational relationship: Starting, Spawned by, Queried by, Retrieved by, Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode: deterministic, hybrid, or non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

Within one functional component's envelope `Loop`, each persona request passes
the inbound layers in fixed order and leaves through frustration avoidance:

```text
Envelope Loop (for one persona request, outermost first)
├── 1 frustration_avoidance  shapes every refusal as envelope_refusal/v1 with plain-English next actions
├── 2 carrier                checks record schema, payload byte bounds, privilege fields, and SSRF or XSS vectors
├── 3 handshake              computes envelope_handshake_verdict/v1 from declarations; unknown fails closed
├── 4 account                enforces tenant isolation, staff route gates, pagination rate limits, and email-first sign-up
├── 5 tracking               verifies envelope_journal_entry/v1 chains, answers confirmed replays once, and checks webhook windows
├── 6 preflight              runs effect-free diagnosis checks and bounded pure self-repairs (run_preflight)
└── 7 nested_envelopes       enforces shared RecoveryAllowance(3), monotonic deadline, and maximum depth 4 (enter_nested)
```

## Multi-engine defense and normalization comparison

The suite compares four swappable defense and normalization engines behind the
same typed evaluation contract (`DefenseEngineResult`):

1. `exact_strict_guard`: enforces deterministic carrier, handshake, account, and
   tracking security guards with preflight diagnosis checks enabled and zero
   automatic self-repairs.
2. `normalized_tolerant_guard`: adds deterministic preflight self-repairs for
   whitespace and quote stripping, duplicate `Bearer` collapsing, idempotent
   double-click replay lookup, rotated session credential refresh, minor
   read-only JSON-RPC truncation repair, and loopback URL and version
   normalization, without fuzzy traceback distillation.
3. `lsh_fuzzy_traceback_normalizer`: combines stack-frame noise stripping,
   Unicode NFKC normalization, token extraction, and 3-gram Locality-Sensitive
   Hashing (LSH) shingle Jaccard similarity for noisy multi-line traceback and
   polyglot search queries, without stateful session or JSON-RPC repairs.
4. `cascade_envelope_guard`: orchestrates the seven-layer component envelope
   with an automatic fallback chain (`exact_strict_guard` to
   `normalized_tolerant_guard` to `lsh_fuzzy_traceback_normalizer`) governed by
   one shared `RecoveryAllowance` (`MAXIMUM_AUTOMATIC_ATTEMPTS = 3`) and one
   inherited `EnvelopeFrame` deadline. Security blocks on malicious requests
   terminate immediately at the first engine and never trigger fallback.

| Engine | Total passed | Malicious blocked (`P-BAD`) | Strange recovered (`P-STRANGE`) | Executive verified (`P-EXEC`) | False positives on non-malicious | Mean latency (ms) | Total latency (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `exact_strict_guard` | 12 / 18 | 6 / 6 (100.0%) | 0 / 6 (0.0%) | 6 / 6 (100.0%) | 6 / 12 (50.0%) | 0.183 | 3.294 |
| `normalized_tolerant_guard` | 17 / 18 | 6 / 6 (100.0%) | 5 / 6 (83.3%) | 6 / 6 (100.0%) | 1 / 12 (8.3%) | 0.251 | 4.518 |
| `lsh_fuzzy_traceback_normalizer` | 14 / 18 | 6 / 6 (100.0%) | 2 / 6 (33.3%) | 6 / 6 (100.0%) | 4 / 12 (33.3%) | 0.210 | 3.780 |
| `cascade_envelope_guard` | 18 / 18 | 6 / 6 (100.0%) | 6 / 6 (100.0%) | 6 / 6 (100.0%) | 0 / 12 (0.0%) | 0.485 | 8.730 |

## Complete 18-persona emulation results

The table below records the observed outcome for each of the 18 personas under
the four engines, including the primary envelope layer, the fallback chain
exercised by `cascade_envelope_guard`, and the resulting verification or
`envelope_refusal/v1` code.

| Persona ID | Category | Persona title | Primary layer | `exact_strict_guard` | `normalized_tolerant_guard` | `lsh_fuzzy_traceback_normalizer` | `cascade_envelope_guard` (fallback chain) | Observed code |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `P-BAD-01` | Malicious | Bulk Catalogue Scraper and Enumeration Abuser | `account` | Blocked | Blocked | Blocked | Blocked (`exact_strict_guard`) | `bulk_enumeration_refused` |
| `P-BAD-02` | Malicious | Indirect Prompt Injector and SSRF/XSS/SQLi Prober | `carrier` | Blocked | Blocked | Blocked | Blocked (`exact_strict_guard`) | `hostile_payload_or_ssrf_refused` |
| `P-BAD-03` | Malicious | Staff-Surface and Cross-Tenant IDOR Prober | `account` | Blocked | Blocked | Blocked | Blocked (`exact_strict_guard`) | `cross_tenant_or_staff_surface_refused` |
| `P-BAD-04` | Malicious | Billing Webhook Replay and Email Budget Exhaustion Attacker | `tracking` | Blocked | Blocked | Blocked | Blocked (`exact_strict_guard`) | `webhook_replay_or_email_quota_refused` |
| `P-BAD-05` | Malicious | Oversized Payload, ReDoS, and Concurrency Exhaustion Abuser | `nested_envelopes` | Blocked | Blocked | Blocked | Blocked (`exact_strict_guard`) | `resource_or_envelope_depth_refused` |
| `P-BAD-06` | Malicious | Unconfirmed-Email Pre-Registration Hijacker | `account` | Blocked | Blocked | Blocked | Blocked (`exact_strict_guard`) | `unconfirmed_pre_registration_refused` |
| `P-STRANGE-01` | Strange | Copy-Paste Whitespace, Duplicate-Bearer, and Smart-Quote Mangler | `preflight` | Refused (FP) | Repaired | Repaired | Repaired (`exact` -> `normalized`) | `repaired_auth_and_whitespace` |
| `P-STRANGE-02` | Strange | Multi-Tab Rapid Double-Clicker and Session Race Runner | `tracking` | Refused (FP) | Repaired | Refused (FP) | Repaired (`exact` -> `normalized`) | `answered_from_first_confirmed_result` |
| `P-STRANGE-03` | Strange | Polyglot, Emoji, and 80-Line Traceback Query Searcher | `preflight` | Refused (FP) | Refused (FP) | Repaired | Repaired (`exact` -> `normalized` -> `lsh`) | `repaired_traceback_lsh_query` |
| `P-STRANGE-04` | Strange | Expired or Replaced Key Mid-Session Runner | `preflight` | Refused (FP) | Repaired | Refused (FP) | Repaired (`exact` -> `normalized`) | `repaired_rotated_session_credential` |
| `P-STRANGE-05` | Strange | Truncated JSON-RPC and Narrow 320px Viewport User | `carrier` | Refused (FP) | Repaired | Refused (FP) | Repaired (`exact` -> `normalized`) | `repaired_jsonrpc_and_narrow_viewport` |
| `P-STRANGE-06` | Strange | Wrong-Harness and Localhost 127.0.0.1 Configurer | `handshake` | Refused (FP) | Repaired | Refused (FP) | Repaired (`exact` -> `normalized`) | `compatible_with_degradation_after_preflight` |
| `P-EXEC-01` | Executive | Skeptical Enterprise CTO (Provenance, Licence, and Fail-Closed Handshake) | `handshake` | Verified | Verified | Verified | Verified (`exact_strict_guard`) | `cto_provenance_and_handshake_verified` |
| `P-EXEC-02` | Executive | FinOps and CFO (Cost Predictability, Budget Caps, and Billing Record Clarity) | `account` | Verified | Verified | Verified | Verified (`exact_strict_guard`) | `cfo_budget_cap_and_billing_record_verified` |
| `P-EXEC-03` | Executive | Technical VC and Auditor (Live vs Recorded Fact Consistency) | `tracking` | Verified | Verified | Verified | Verified (`exact_strict_guard`) | `vc_coverage_and_journal_integrity_verified` |
| `P-EXEC-04` | Executive | Solo Creative Studio Builder (Card-First Discovery, Revision, and Clean Reopen) | `preflight` | Verified | Verified | Verified | Verified (`exact_strict_guard`) | `creative_workflow_revision_and_reopen_verified` |
| `P-EXEC-05` | Executive | Public Good SDG Grant Applicant (Zero-Cost Baseline and Accessible Guidance) | `frustration_avoidance` | Verified | Verified | Verified | Verified (`exact_strict_guard`) | `sdg_public_good_baseline_verified` |
| `P-EXEC-06` | Executive | Competitor Surface Prober (Public Card vs Protected Source and Ranking Boundary) | `carrier` | Verified | Verified | Verified | Verified (`exact_strict_guard`) | `public_card_served_and_protected_internals_withheld` |

## Known-wrong controls

Each guard in the suite pairs with a `removed_*` known-wrong control that
disables that single guard and verifies that the corresponding attack or
boundary probe leaks through (`malicious_leaked_when_removed = True`). All eight
controls pass.

| Control name | Target persona | Guarded code | Unguarded code when removed | Leak detected |
| --- | --- | --- | --- | --- |
| `removed_rate_and_enumeration_guard` | `P-BAD-01` | `bulk_enumeration_refused` | `known_wrong_malicious_request_leaked` | Passed (`True`) |
| `removed_payload_injection_ssrf_guard` | `P-BAD-02` | `hostile_payload_or_ssrf_refused` | `known_wrong_malicious_request_leaked` | Passed (`True`) |
| `removed_tenant_and_staff_idor_guard` | `P-BAD-03` | `cross_tenant_or_staff_surface_refused` | `known_wrong_malicious_request_leaked` | Passed (`True`) |
| `removed_webhook_replay_and_email_quota_guard` | `P-BAD-04` | `webhook_replay_or_email_quota_refused` | `known_wrong_malicious_request_leaked` | Passed (`True`) |
| `removed_payload_size_and_depth_guard` | `P-BAD-05` | `resource_or_envelope_depth_refused` | `known_wrong_malicious_request_leaked` | Passed (`True`) |
| `removed_unconfirmed_email_hijack_guard` | `P-BAD-06` | `unconfirmed_pre_registration_refused` | `known_wrong_malicious_request_leaked` | Passed (`True`) |
| `removed_handshake_declaration_guard` | `P-EXEC-01` | `cto_provenance_and_handshake_verified` | `known_wrong_undeclared_handshake_accepted` | Passed (`True`) |
| `removed_public_surface_source_boundary_guard` | `P-EXEC-06` | `public_card_served_and_protected_internals_withheld` | `known_wrong_competitor_source_and_ranking_leaked` | Passed (`True`) |

## Reproduce the verification locally

Run the benchmark and unit test suite under the memory cap:

```bash
export TMPDIR=$HOME/.le-ci-tmp/tmp-layers
mkdir -p "$TMPDIR" && touch "$TMPDIR/.keep-in-place"
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python tools/adversarial_persona_suite.py
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_adversarial_persona_suite.py
```

## Limits and deeper references

This suite is a deterministic, in-process loopback emulation over the real
record and layer primitives in `src/loop_engine/core/engines/envelope.py`,
`src/loop_engine/core/engines/envelope_tracking.py`,
`src/loop_engine/core/engines/envelope_preflight.py`, and
`src/loop_engine/core/engines/envelope_coverage.py`. It does not replace live
post-deployment browser verification against the production Fly.io and
Cloudflare endpoints recorded in
[`docs/architecture/MVP-CLIENT-SERVER.md`](../architecture/MVP-CLIENT-SERVER.md).

For the normative envelope rules and coverage ratchet, see:

- [`docs/architecture/ADR-COMPONENT-ENVELOPE-LAYERS.md`](../architecture/ADR-COMPONENT-ENVELOPE-LAYERS.md)
- [`docs/architecture/FUNCTIONAL-COMPONENT-STANDARD.md`](../architecture/FUNCTIONAL-COMPONENT-STANDARD.md)
- [`src/loop_engine/data/component_envelope_coverage.yaml`](../../src/loop_engine/data/component_envelope_coverage.yaml)
- [`src/loop_engine/data/component_envelope_coverage_baseline.yaml`](../../src/loop_engine/data/component_envelope_coverage_baseline.yaml)
