# Pro-Forma Financial, Infrastructure, Creative, and Personal-Agent Engine Comparisons (2026-10-16)

- Date: 2026-10-16
- Verification scope: deterministic pro-forma financial and infrastructure modeling (`tools/proforma_simulator.py`) and multi-engine creative motion and personal-agent safety benchmarks (`tools/creative_and_personal_agent_engines.py`) wrapped in the 6-layer component envelope (`loop_engine.core.engines.envelope`, `envelope_preflight`, `envelope_tracking`).
- Authority and alignment: [NORTH-STAR.md](../architecture/NORTH-STAR.md), [OWNER-DECISIONS.md](../architecture/OWNER-DECISIONS.md), [ADR-COMPONENT-ENVELOPE-LAYERS.md](../architecture/ADR-COMPONENT-ENVELOPE-LAYERS.md), and [OPENMUSE-COMPONENT-ENGINE-REUSE-2026-09-23.md](../research/OPENMUSE-COMPONENT-ENGINE-REUSE-2026-09-23.md).

## 1. Architecture Classification and Envelope Alignment

Every executable graph vertex in Loop Engine is a discrete cognitive or act step Loop node. Engines evaluated in this report operate strictly as swappable adapters behind typed, versioned component contracts and never introduce a new runtime vertex type.

```text
Loop (single runtime node type; Practitioner, Intelligence and Solution are roles, not subclasses)
├── Practitioner Loop
│   ├── deterministic mode
│   ├── hybrid mode
│   └── non-deterministic mode
├── Intelligence Loop
│   ├── deterministic mode
│   ├── hybrid mode
│   └── non-deterministic mode
└── Solution Loop
    ├── deterministic mode
    ├── hybrid mode
    └── non-deterministic mode
```

Every functional component benchmarked in this verification record passes through the six envelope layers in declared order:

1. `frustration_avoidance`: shapes every refusal as an `envelope_refusal/v1` record with a plain-sentence message, an explicit `next_action`, a `next_action_by` actor (`caller`, `account_owner`, or `operator`), and a retry rule (`retry_now_same_identity`, `retry_after_wait`, `retry_after_fix`, `reconcile_before_retry`, or `do_not_retry`).
2. `carrier`: validates typed `name/vN` records and content-addressed SHA-256 digests before engine dispatch.
3. `handshake`: computes `envelope_handshake_verdict/v1` from caller requirements and engine declarations; unknown or ungranted capabilities fail closed.
4. `account`: verifies account entitlements and effect grants against service records.
5. `tracking`: journals `envelope_journal_entry/v1` records (`intended`, `committed`, `reconciled`) keyed by `request_identity_digest`, refusing automatic retry whenever an effect is `pending` or `unknown`.
6. `preflight`: executes effect-free diagnostic checks (`EnvelopePreflightCheck`) and bounded pure self-repairs (`EnvelopeSelfRepair`) before dispatching the selected engine or entering a nested component via `enter_nested`.

## 2. Evidence Classification

- **Observed facts**:
  - `python3 tools/proforma_simulator.py --self-test` passes 6 deterministic verification checks across 30 pricing projection rows, 16 email stack rows, 9 catalogue hosting rows, and 2 envelope failover/reconciliation traces.
  - `python3 tools/creative_and_personal_agent_engines.py --self-test` passes 6 deterministic verification checks across 3 creative motion engines, nested layout QA gating, bounded preflight self-repair, and 6 personal-agent safety engines (primary and fallback for each of 3 components).
  - Unit test suites `tools/test_proforma_simulator.py` (9 tests) and `tools/test_creative_and_personal_agent_engines.py` (8 tests) pass under both `pytest` and `unittest`.
- **Assumed parameters**:
  - Stripe processing fees are modeled at standard US card rates (`2.9% + $0.30` per charge), with annual prepaid plans (`$290/year` Pro Annual) billed once upfront and amortized at `$24.17/month` for MRR reporting.
  - Customer-brought model inference (BYOK / Ollama Cloud / local endpoints) places zero variable model-inference spend on Baltor's own infrastructure account, per owner decision of September 23, 2026.
  - Component catalogue storage averages `14.5 KB` raw per distinct component file (`9.2 KB` after content-addressed SHA-256 deduplication across versions).
- **Inferred conclusions**:
  - Introducing the `multi_tier_expansion` packaging (`Baltor Max $99/mo`, `Baltor Team $199/mo`, `AgentBriefs Enterprise $799/mo`, and `Playground Sponsorships`) reaches the owner's `$100,000` MRR target between Month 3 (`$94,899.33` gross MRR on the aggressive curve) and Month 6 (`$73,122.17` on the base curve; `$226,303.00` on the aggressive curve), whereas the baseline `current_launch` packaging reaches `$75,938.67` on the base curve at Month 12.
  - Offloading static catalogue blobs to Cloudflare R2 with a Worker-first content-addressed edge cache (`worker_first_r2_d1_cache`) keeps total monthly hosting cost within the `$50/month` pilot infrastructure allowance all the way to `10,000,000` distinct component files (`$35.76/month`), whereas scaling attached NVMe volumes directly on Fly.io origin machines (`fly_volume_origin`) exceeds `$50/month` at `5,000,000` files (`$66.84/month`).

## 3. Pricing and Tier Mix Variations Across Growth Curves

The simulator compares two pricing structures mandated in [OWNER-DECISIONS.md](../architecture/OWNER-DECISIONS.md):

- **Model A (`current_launch`)**: Free supported baseline (`$0`), Basic Feeds (`$9/mo`, free during the 60-day launch window through November 23, 2026), Baltor Pro Monthly (`$29/mo`), Baltor Pro Annual (`$290/yr` upfront, `$24.17/mo` amortized MRR), and AgentBriefs Standard (`$299/mo`).
- **Model B (`multi_tier_expansion`)**: Adds Baltor Max (`$99/mo`), Baltor Team (`$199/mo`, 5 seats), AgentBriefs Enterprise (`$799/mo`), and Playground Sponsorship slots (`$1,000/mo` per sponsor slot).

### 3.1 Model A (`current_launch`) Pro-Forma Trajectory

| Growth Curve | Horizon | Free Accounts | Paid Accounts | Gross MRR (USD) | Annual Cash Inflow (USD) | Stripe Fees (USD) | Infra + Email (USD) | Net MRR (USD) | Operating Margin |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Conservative | Days 1 to 7 | 65 | 5 | $220.17 | $290.00 | $7.88 | $38.50 | $173.78 | 78.93% |
| Conservative | Month 1 | 195 | 24 | $1,076.67 | $1,160.00 | $37.52 | $39.16 | $999.98 | 92.88% |
| Conservative | Month 3 | 130 | 159 | $4,093.00 | $3,480.00 | $163.10 | $41.62 | $3,888.28 | 95.00% |
| Conservative | Month 6 | 270 | 384 | $9,795.17 | $7,250.00 | $392.36 | $79.39 | $9,323.42 | 95.18% |
| Conservative | Month 12 | 610 | 939 | $23,721.00 | $17,400.00 | $953.11 | $110.72 | $22,657.17 | 95.52% |
| Base | Days 1 to 7 | 135 | 17 | $758.50 | $870.00 | $26.50 | $38.50 | $693.50 | 91.43% |
| Base | Month 1 | 500 | 65 | $2,936.67 | $2,900.00 | $101.96 | $76.27 | $2,758.43 | 93.93% |
| Base | Month 3 | 330 | 485 | $12,495.83 | $10,150.00 | $498.28 | $85.03 | $11,912.52 | 95.33% |
| Base | Month 6 | 760 | 1,253 | $32,086.17 | $24,650.00 | $1,283.00 | $126.96 | $30,676.21 | 95.61% |
| Base | Month 12 | 1,810 | 2,993 | $75,938.67 | $55,100.00 | $3,047.92 | $224.61 | $72,666.14 | 95.69% |
| Aggressive | Days 1 to 7 | 310 | 45 | $2,006.33 | $2,320.00 | $69.58 | $43.92 | $1,892.83 | 94.34% |
| Aggressive | Month 1 | 1,210 | 190 | $8,565.00 | $8,700.00 | $296.99 | $105.50 | $8,162.51 | 95.30% |
| Aggressive | Month 3 | 810 | 1,558 | $40,810.33 | $31,900.00 | $1,620.60 | $139.38 | $39,050.35 | 95.69% |
| Aggressive | Month 6 | 1,910 | 3,810 | $96,730.00 | $69,600.00 | $3,882.17 | $256.70 | $92,591.13 | 95.72% |
| Aggressive | Month 12 | 4,510 | 8,386 | $206,497.33 | $145,000.00 | $8,366.82 | $532.50 | $197,598.01 | 95.69% |

### 3.2 Model B (`multi_tier_expansion`) Pro-Forma Trajectory

| Growth Curve | Horizon | Free Accounts | Paid Accounts | Gross MRR (USD) | Annual Cash Inflow (USD) | Stripe Fees (USD) | Infra + Email (USD) | Net MRR (USD) | Operating Margin |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Conservative | Days 1 to 7 | 65 | 6 | $319.17 | $290.00 | $11.06 | $38.50 | $269.61 | 84.47% |
| Conservative | Month 1 | 195 | 29 | $1,971.67 | $1,160.00 | $64.98 | $39.34 | $1,867.35 | 94.71% |
| Conservative | Month 3 | 130 | 177 | $8,826.00 | $3,480.00 | $305.75 | $42.24 | $8,478.01 | 96.06% |
| Conservative | Month 6 | 270 | 431 | $21,400.17 | $7,250.00 | $743.00 | $81.03 | $20,576.13 | 96.15% |
| Conservative | Month 12 | 610 | 1,060 | $52,954.00 | $17,400.00 | $1,837.17 | $114.95 | $51,001.88 | 96.31% |
| Base | Days 1 to 7 | 135 | 21 | $1,554.50 | $870.00 | $50.78 | $38.50 | $1,465.22 | 94.26% |
| Base | Month 1 | 500 | 82 | $7,570.67 | $2,900.00 | $241.45 | $76.87 | $7,252.35 | 95.80% |
| Base | Month 3 | 330 | 546 | $27,286.83 | $10,150.00 | $945.52 | $87.16 | $26,254.16 | 96.22% |
| Base | Month 6 | 760 | 1,422 | $73,122.17 | $24,650.00 | $2,523.74 | $132.87 | $70,465.55 | 96.37% |
| Base | Month 12 | 1,810 | 3,412 | $174,979.67 | $55,100.00 | $6,045.81 | $239.27 | $168,694.59 | 96.41% |
| Aggressive | Days 1 to 7 | 310 | 57 | $5,745.33 | $2,320.00 | $181.61 | $44.34 | $5,519.38 | 96.07% |
| Aggressive | Month 1 | 1,210 | 240 | $21,217.00 | $8,700.00 | $678.89 | $107.25 | $20,430.86 | 96.29% |
| Aggressive | Month 3 | 810 | 1,775 | $94,899.33 | $31,900.00 | $3,254.28 | $146.98 | $91,498.07 | 96.42% |
| Aggressive | Month 6 | 1,910 | 4,349 | $226,303.00 | $69,600.00 | $7,801.49 | $275.57 | $218,225.94 | 96.43% |
| Aggressive | Month 12 | 4,510 | 9,563 | $487,445.33 | $145,000.00 | $16,867.41 | $580.05 | $469,997.86 | 96.42% |

## 4. Transactional and Support Email Stack Comparisons

The simulator evaluates four swappable engine stacks for the `transactional_and_support_email` component across 100, 1,000, 10,000, and 100,000 monthly emails:

| Stack ID | Stack Architecture | 100 / mo (USD) | 1,000 / mo (USD) | 10,000 / mo (USD) | 100,000 / mo (USD) | Scoped API Auth | OAuth / JMAP | Inbound Worker | Failover Chain |
| :--- | :--- | ---: | ---: | ---: | ---: | :--- | :--- | :--- | :--- |
| `resend_free_cf_routing` | Resend Free (`$0`, 100/day, 3k/mo cap) + Cloudflare Email Routing | $0.00 | $0.00 | Refused (cap) | Refused (cap) | Yes | No | No | `resend_free_api -> aws_ses_api` |
| `resend_pro_cf_workers_fastmail` | Resend Pro (`$20/mo`, 50k incl.) + Cloudflare Email Workers + Fastmail JMAP (`$5/mo`) | $25.00 | $25.00 | $25.00 | $70.00 | Yes | Yes | Yes | `resend_pro_api -> aws_ses_api -> fastmail_jmap_submission` |
| `aws_ses_cf_workers` | AWS SES (`$0.10/1k`) + Cloudflare Email Workers | $0.01 | $0.10 | $1.00 | $10.00 | Yes | No | Yes | `aws_ses_api -> resend_pro_api` |
| `postmark_fastmail` | Postmark (`$15/mo` for 10k, `$1.80/1k` overage) + Fastmail JMAP (`$5/mo`) | $20.00 | $20.00 | $20.00 | $182.00 | Yes | Yes | No | `postmark_api -> fastmail_jmap_submission -> aws_ses_api` |

### 4.1 Envelope Failover and `EFFECT_STATE_UNKNOWN` Reconciliation

- **Pre-effect quota failover (`pre_effect_quota_failover`)**: When `resend_free_api` refuses a send before any network effect with `quota_exceeded` (`effect_commitment="none"`, `retry="retry_now_same_identity"`, `automatic_retry=True`), `may_recover` spends 1 shared attempt from `RecoveryAllowance` and fails over automatically to `aws_ses_api`, which confirms delivery (`effect_state="confirmed"`).
- **Interrupted transport reconciliation (`unknown_outcome_reconciliation_guard`)**: When a send times out after socket submission, `journal_outcome` records `effect_state="unknown"`. A subsequent retry is refused at the tracking layer (`decision="reconcile_first"`, `retry="reconcile_before_retry"`) so the message is never sent twice. After querying the provider status API and recording `journal_reconciliation(..., observed_effect_state="confirmed")`, the next retry is answered directly from the journal (`decision="answer_from_first_result"`, `engine_dispatched=False`).

## 5. Catalogue Hosting and Serving Comparisons (1.90M to 10.00M Files)

The simulator models three hosting architectures across `1,900,000` (current live scale), `5,000,000`, and `10,000,000` distinct component files:

| Architecture ID | Distinct Files | Raw Size (GB) | Dedup Size (GB) | Fly Compute + Vol (USD) | Cloudflare R2 + Workers (USD) | Total Monthly (USD) | Within $50 Cap | p50 / p95 Read (ms) | Deploy Resync (s) | Origin Disk Pressure |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- | ---: | ---: | :--- |
| `fly_volume_origin` | 1,900,000 | 27.55 | 17.48 | $29.05 | $0.00 | $29.05 | Yes | 48.0 / 163.0 | 95.0 | moderate |
| `fly_volume_origin` | 5,000,000 | 72.50 | 46.00 | $66.84 | $0.00 | $66.84 | No | 57.8 / 208.7 | 250.0 | high |
| `fly_volume_origin` | 10,000,000 | 145.00 | 92.00 | $133.53 | $0.00 | $133.53 | No | 73.6 / 282.4 | 500.0 | high |
| `fly_origin_r2_edge_export` | 1,900,000 | 27.55 | 17.48 | $17.65 | $6.91 | $24.56 | Yes | 18.0 / 58.0 | 36.0 | low |
| `fly_origin_r2_edge_export` | 5,000,000 | 72.50 | 46.00 | $18.85 | $10.28 | $29.13 | Yes | 18.0 / 64.5 | 49.1 | low |
| `fly_origin_r2_edge_export` | 10,000,000 | 145.00 | 92.00 | $36.40 | $15.70 | $52.10 | No | 18.0 / 75.1 | 70.1 | low |
| `worker_first_r2_d1_cache` | 1,900,000 | 27.55 | 17.48 | $16.90 | $7.51 | $24.41 | Yes | 11.0 / 34.0 | 14.5 | minimal |
| `worker_first_r2_d1_cache` | 5,000,000 | 72.50 | 46.00 | $16.90 | $11.86 | $28.76 | Yes | 11.0 / 34.0 | 18.6 | minimal |
| `worker_first_r2_d1_cache` | 10,000,000 | 145.00 | 92.00 | $16.90 | $18.86 | $35.76 | Yes | 11.0 / 34.0 | 25.2 | minimal |

## 6. Creative Video and Motion Engine Comparisons (`creative_motion_scene`)

Informed by the local `reelkit` layout contract and `layout_audit.py` QA rules, `tools/creative_and_personal_agent_engines.py` benchmarks three swappable engines behind `creative_motion_scene/v1` and a nested `creative_layout_qa_gate/v1` component entered via `enter_nested(frame, "creative_layout_qa_gate")` at envelope depth `1`:

| Engine ID | Artifact Format | Frame Count (6.0s @ 30fps) | Planned Boxes | Nested QA Depth | QA Passed | Artifact Digest Prefix | Primary Use Case and Dependencies |
| :--- | :--- | ---: | ---: | ---: | :--- | :--- | :--- |
| `reelkit_frame_planner` | `reelkit_frame_manifest/v1` | 180 | 3 | 1 | Yes (`0` fail, `0` warn) | `26010b30b0ed6195` | Deterministic Python slot layout (`top=290`, `upper=470`, `middle=820`, `lower=1180`, `low=1390`), `stable_seed` frame hashing, zero external dependencies |
| `remotion_three_scene_generator` | `remotion_three_scene_graph/v1` | 180 | 3 | 1 | Yes (`0` fail, `0` warn) | `0dea1fc30c7e957a` | Declarative Remotion / Three.js camera keyframe spline and 3D overlay track descriptor for GPU/WebGL rendering |
| `svg_canvas_storyboard_fallback` | `svg_storyboard_xml/v1` | 180 | 3 | 1 | Yes (`0` fail, `0` warn) | `f30675842d6b0bd5` | Zero-dependency deterministic SVG storyboard fallback when FFmpeg or headless WebGL is unavailable |

### 6.1 Preflight Self-Repair and Nested QA Gate Verification

- **Bounded pure preflight self-repair (`caption_contrast_and_size_repair`)**: When given the Miso v02 stamp defect (`stamp_miso_v02` at `30px` below the `38px` `stamp` floor, and `#c0392b` foreground on `#8a2820` background with `1.65:1` relative luminance contrast), `EnvelopePreflightCheck` diagnoses the violation and `EnvelopeSelfRepair` (`effects=("pure",)`, `maximum_applications=2`) lifts the font size to `38px` and repairs the foreground fill to `#fff8ec` (`8.27:1` contrast), yielding preflight verdict `repaired` (`STEP_REPAIRED`).
- **Nested layout QA gate refusal (`creative_layout_qa_gate_rejected`)**: When preflight repair is disabled or a layout intrudes into the TikTok/Reels/Shorts bottom 20% UI zone (`y1 > 1536`), right 12% action rail (`x1 > 950.4`), 22px canvas edge margin, subject keep-out box (`>= 200 px^2`), text-to-text overlap (`>= 120 px^2`), or sub-quarter-second caption flicker (`duration_s < 0.25s`), the nested QA gate refuses the scene with `retry="retry_after_fix"`.

## 7. Personal Agent and Local Safety Engine Comparisons (`personal_agent_safety`)

`PersonalAgentSafetyDispatcher` wraps three personal-agent safety sub-components in the 6-layer envelope, pairing a primary structured engine with a deterministic fallback engine for each slot:

| Component ID | Engine ID | Role in Slot | Fallback Used | Key Verification Outcome | Envelope Safety Guarantee |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `transcript_secret_scanner` | `structured_token_and_entropy_scanner` | Primary | No | Redacts 2 markers (`sha256:1ddfd0f000165f3c`) | Replaces PEM blocks, Bearer headers, `sk-` grants, and high-entropy assignments with SHA-256 digests; never echoes raw values in `EnvelopeRefusal` |
| `transcript_secret_scanner` | `regex_boundary_fallback_scanner` | Fallback | Yes | Redacts 2 markers (`sha256:1ddfd0f000165f3c`) | Deterministic regex boundary fallback when structured AST/entropy evaluation is faulted |
| `pre_compaction_checkpoint` | `structured_ast_and_ledger_checkpoint_engine` | Primary | No | Digest `403fe70cbc05cd67` (1 uncommitted file) | Emits `context_checkpoint/v1` JSON; refuses compaction (`compaction_unanchored_pending_effect`, `reconcile_before_retry`) if any unsettled journal entry is unanchored |
| `pre_compaction_checkpoint` | `line_anchor_checkpoint_fallback` | Fallback | Yes | Digest `0a3eb33a7c95dc3a` (1 uncommitted file) | Deterministic line-anchor serializer preserving uncommitted file digests and unsettled effect identities |
| `durable_task_approval_gate` | `cas_lease_and_digest_approval_engine` | Primary | No | Approved (CAS lease epoch `7` verified) | Verifies worker CAS lease epoch, human-approved payload SHA-256 digest, account owner match, expiry window, and `RECONCILE_BEFORE_RETRY` on `EFFECT_STATE_UNKNOWN` |
| `durable_task_approval_gate` | `strict_local_policy_fallback_engine` | Fallback | Yes | Approved for read-only; refuses mutating effects | Admits only read-only effects when the primary CAS lease coordinator is unreachable (`fallback_policy_refuses_mutating_effect`) |

## 8. Engineering Decisions and Recommendations

1. **Adopt `worker_first_r2_d1_cache` before catalogue scale passes 3.5M files**: Direct origin volume serving (`fly_volume_origin`) is economical at `1.90M` files (`$29.05/month`) but breaches the `$50/month` infrastructure allowance at `5.00M` files (`$66.84/month`). Moving immutable component blobs to Cloudflare R2 behind a Worker content-addressed cache keeps monthly cost at `$28.76` for `5.00M` files and `$35.76` for `10.00M` files while cutting p95 read latency from `282.4 ms` to `34.0 ms`.
2. **Use `resend_free_cf_routing` for Day 1 launch, then switch primary to `resend_pro_cf_workers_fastmail` with `aws_ses_api` failover**: This keeps fixed email cost at `$0/month` during the initial week and `$25/month` through Month 6 while providing JMAP/OAuth mailbox access, programmable inbound Workers, and automatic pre-effect failover to AWS SES (`$0.10/1k`) if a daily or monthly quota is reached.
3. **Require nested `creative_layout_qa_gate` before any video render spend**: Running `reelkit_frame_planner` with bounded preflight self-repair and the nested layout QA gate catches contrast, font floor, keep-out overlap, platform UI zone, and flicker defects in pure Python (`< 5 ms`) before dispatching FFmpeg or GPU rendering.

## 9. Verification Commands Run

```bash
PYTHONPATH=src:tools python3 -m pytest -q tools/test_proforma_simulator.py tools/test_creative_and_personal_agent_engines.py
PYTHONPATH=src:tools /home/username/loop-engine/.venv/bin/python -m unittest -v tools/test_proforma_simulator.py tools/test_creative_and_personal_agent_engines.py
PYTHONPATH=src:tools python3 tools/proforma_simulator.py --self-test
PYTHONPATH=src:tools python3 tools/creative_and_personal_agent_engines.py --self-test
```
