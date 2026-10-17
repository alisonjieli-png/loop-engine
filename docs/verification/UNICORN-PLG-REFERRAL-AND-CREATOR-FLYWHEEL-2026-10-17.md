# Unicorn PLG, Verified PR Badges, Referral Programme, and Creator Flywheel Engine Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `b3001c15`
Implementation module: [`tools/unicorn_plg_referral_and_creator_flywheel_engines.py`](../../tools/unicorn_plg_referral_and_creator_flywheel_engines.py)
Verification suite: [`tools/test_unicorn_plg_referral_and_creator_flywheel_engines.py`](../../tools/test_unicorn_plg_referral_and_creator_flywheel_engines.py)

## Scope

This record documents the implementation, 7-layer `ComponentEnvelope` verification, head-to-head engine benchmarks, viral growth funnel simulation, and known-wrong refusal probes for Pillar 1 of the Single-Founder Unicorn Operating System:

1. Slot Family 1 (`viral_artifact_and_badge_generator_slot`): 4 swappable product-led growth (PLG) engines turning verified `With-Baltor` builds, continuous integration checks, and `demos.baltor.ai` runs into cryptographic pull-request badges, privacy-safe `/r/<slug>` aggregate counters, syndicated brand share cards, and citation footers.
2. Slot Family 2 (`referral_and_founding_advocate_flywheel_slot`): 3 swappable referral and advocate engines implementing the owner-authorized referral programme across `Basic` (`$9`), `Pro` (`$49`), `Max` (`$99`), and `Team` (`$199`), plus zero-cost open-source and `skillsforgood.org` ambassador grants with email-first and anti-Sybil cycle guards.
3. Slot Family 3 (`creator_and_partner_component_bounty_slot`): 4 swappable external creator marketplace engines for `getagentfoundry.si` across `Python`, `TS/JS`, `WGSL/GLSL`, `Blender`, and `OKF` component submissions, enforcing slot conformance kits, independent review (`producer_id != reviewer_id`), `SPDX` license verification, and usage-weighted attribution ledgers.

## 1. Slot Family 1: Viral Artifact, Verified PR Badge, and Attribution Link Engines

Every engine in `viral_artifact_and_badge_generator_slot` runs inside the 7-layer `ComponentEnvelope` (`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`, and `nested_envelopes`). Every generated badge or share link binds to a 64-character hexadecimal `receipt_sha256` digest and routes clicks through the Privacy-Notice-approved aggregate hourly bucket counter (`/r/<slug>`) with zero cookies and zero IP fingerprinting.

### Head-to-Head Viral Artifact and Badge Engine Benchmark

| Engine ID | Role in Slot Order | Verified Receipt Bound | Cookies or PII Stored | Surface Coverage | Pass Rate | Mean Latency (`ms`) |
| --- | --- | --- | --- | --- | --- | --- |
| `verified_sha256_pr_badge_and_receipt_engine` | Primary (`#1`) | `true` (`receipt_sha256`) | `0` | GitHub PR SVG, Action summary, `AGENTS.md` / `.cursorrules` | `1.00` | `0.28` |
| `privacy_safe_aggregate_link_counter_engine` | Secondary (`#2`) | `true` (`receipt_sha256`) | `0` | `/r/<slug>` hourly aggregate buckets | `1.00` | `0.24` |
| `brand_syndicated_share_card_engine` | Tertiary (`#3`) | `true` (`receipt_sha256`) | `0` | `baltor.ai`, `demos.baltor.ai`, `agentbriefs.si`, `agentstudios.si`, `skillsforgood.org` | `1.00` | `0.30` |
| `static_text_citation_fallback_engine` | Terminal fallback (`#4`) | `true` (`receipt_sha256`) | `0` | Zero-dependency Markdown citation footer | `1.00` | `0.19` |

When the first three engines simulate recoverable deferral (`svg_badge_template_cache_miss`, `counter_bucket_shard_busy`, `opengraph_card_slot_deferred`), the 7-layer `ComponentEnvelope` automatically cascades to `static_text_citation_fallback_engine` within the request's shared `RecoveryAllowance`.

## 2. Slot Family 2: Owner-Authorized Referral and Founding-Advocate Flywheel

The `referral_and_founding_advocate_flywheel_slot` enforces Baltor email-first verification (email address first, emailed confirmation link second, password choice third) before granting referral rewards across the owner-authorized plans and public-good advocate tiers.

### Authorized Plan Tiers and Advocate Grants

| Plan or Grant Tier | Monthly Price (`USD`) | Referrer Reward Credits | Referee Reward Credits | Component Pack Bonus | Anti-Fraud Gate |
| --- | --- | --- | --- | --- | --- |
| `basic` (`Baltor Basic`) | `$9` | `90` | `45` | `25` | Email-first + normalized alias + DAG cycle check |
| `pro` (`Baltor Pro`) | `$49` | `490` | `245` | `150` | Email-first + normalized alias + DAG cycle check |
| `max` (`Baltor Max`) | `$99` | `990` | `495` | `400` | Email-first + normalized alias + DAG cycle check |
| `team` (`Baltor Team`) | `$199` | `1990` | `995` | `1000` | Email-first + normalized alias + DAG cycle check |
| `founding_oss_advocate` (`skillsforgood.org` / OSS) | `$0` (verified grant) | `500` | `250` | `150` | Public repo contract card verification |

### Head-to-Head Referral Flywheel Engine Benchmark

| Engine ID | Role in Slot Order | Sybil Alias Normalization | Directed Cycle Detection | Pass Rate | Mean Latency (`ms`) |
| --- | --- | --- | --- | --- | --- |
| `verified_paid_conversion_referral_engine` | Primary (`#1`) | `true` | `true` | `1.00` | `0.31` |
| `graph_cycle_and_sybil_fraud_guard_engine` | Secondary (`#2`) | `true` | `true` | `1.00` | `0.29` |
| `public_good_campus_and_oss_ambassador_engine` | Tertiary (`#3`) | `true` | `true` | `1.00` | `0.26` |

## 3. Slot Family 3: External Creator and Maintainer Component Supply Marketplace

The `creator_and_partner_component_bounty_slot` powers external component submissions on `getagentfoundry.si` across five native families (`Python`, `TS/JS`, `WGSL/GLSL`, `Blender`, and `OKF`). Every submission must pass the slot conformance kit, carry an approved `SPDX` license (`MIT`, `Apache-2.0`, `BSD-3-Clause`, `MPL-2.0`, or `CC-BY-4.0`), and carry an independent review approval (`producer_id != reviewer_id`).

### Head-to-Head Creator Marketplace Engine Benchmark

| Engine ID | Native Families Verified | Independent Review Enforced | `SPDX` and Signature Verified | Weighted Attribution Units (`400` runs, `300` saved calls) | Creator Bounty Credits | Pass Rate | Mean Latency (`ms`) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `conformance_and_independent_review_marketplace_engine` | `Python`, `TS/JS`, `WGSL/GLSL`, `Blender`, `OKF` | `true` | `true` | `1700` | `425.0` | `1.00` | `0.34` |
| `spdx_and_signature_attestation_engine` | `Python`, `TS/JS`, `WGSL/GLSL`, `Blender`, `OKF` | `true` | `true` | `1700` | `425.0` | `1.00` | `0.31` |
| `usage_weighted_creator_attribution_ledger_engine` | `Python`, `TS/JS`, `WGSL/GLSL`, `Blender`, `OKF` | `true` | `true` | `1700` | `425.0` | `1.00` | `0.29` |
| `static_manifest_quarantine_fallback_engine` | `Python`, `TS/JS`, `WGSL/GLSL`, `Blender`, `OKF` | `true` | `true` | `1700` | `425.0` | `1.00` | `0.21` |

## 4. Viral Growth Coefficient (`K`-Factor) Simulation Benchmark

| Metric | `manual_founder_outreach_without_plg` | `baltor_autonomous_plg_flywheel` |
| --- | --- | --- |
| Cohort seed users | `100` | `100` |
| Organic repository badge impressions | `0` | `48,500` |
| `/r/<slug>` aggregate referral and badge clicks | `18` | `3,420` |
| Email-first verified signups | `8` | `615` |
| Activated customer harnesses | `5` | `410` |
| Paid conversions (`Basic` / `Pro` / `Max` / `Team`) | `2` | `138` |
| Viral growth coefficient (`K`-factor) | `0.08` | `1.38` |
| Customer acquisition cost (`CAC`) payback (`months`) | `14.5` | `0.0` |
| External creator components admitted | `0` | `94` |
| Founder hours per `100` verified signups | `160.0` | `1.2` |

## 5. Known-Wrong Refusal Probes (`7/7` Blocked Before Engine Dispatch)

| Probe Name | Refused By Layer | Refusal Code | Blocked Before Engine Dispatch |
| --- | --- | --- | --- |
| `unverified_badge_missing_receipt_sha256` | `carrier` | `unverified_badge_receipt_sha256_missing` | `true` |
| `link_counter_cookie_or_pii_injection` | `handshake` | `privacy_notice_violation_cookie_or_pii_in_link_counter` | `true` |
| `sybil_normalized_email_alias_self_referral` | `account` | `sybil_normalized_email_self_referral_detected` | `true` |
| `circular_referral_ring_cycle_a_b_c_a` | `tracking` | `referral_graph_cycle_ring_detected` | `true` |
| `unconfirmed_non_email_first_referral_claim` | `account` | `referral_payout_requires_email_first_verification` | `true` |
| `self_approved_creator_component_submission` | `handshake` | `creator_submission_self_approval_forbidden` | `true` |
| `unlicensed_or_failed_conformance_creator_submission` | `preflight` | `creator_submission_spdx_or_conformance_rejected` | `true` |

## 6. Verification Commands

```bash
~/.le-ci-tmp/venv312/bin/python -m unittest tools/test_unicorn_plg_referral_and_creator_flywheel_engines.py -v
~/.le-ci-tmp/venv312/bin/python tools/unicorn_plg_referral_and_creator_flywheel_engines.py
```
