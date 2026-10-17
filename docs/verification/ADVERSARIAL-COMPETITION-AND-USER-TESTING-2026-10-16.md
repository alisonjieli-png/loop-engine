# Twenty-four-scenario adversarial competition, supply-chain, user, and domain verification record

Kind: verification record. Date: 2026-10-16. Scope: deterministic offline
loopback emulation across 24 adversarial competition, GitHub supply-chain,
multi-surface user, and public-good or creative safety scenarios evaluated
through four swappable defense and verification engines over the seven-layer
component envelope.

## Useful outcome and scope

This verification suite tests whether the `adversarial_competition_guard` engine
slot, wrapped in the seven-layer `ComponentEnvelope`, blocks benchmark data
leakage and supply-chain poisoning while repairing confused user requests and
creative media defects without repeating effects. The suite runs offline in
[`tools/adversarial_competition_and_user_suite.py`](../../tools/adversarial_competition_and_user_suite.py)
and
[`tools/test_adversarial_competition_and_user_suite.py`](../../tools/test_adversarial_competition_and_user_suite.py)
with zero network calls, zero provider writes, and zero model spend.

The 24 scenarios span four attack and emulation surfaces of six scenarios each:

1. Kaggle artificial intelligence and machine learning benchmark integrity
   attacks (`A-KAGGLE-01` to `A-KAGGLE-06`) test train-on-test and group-split
   imputation or target-encoding leakage before `GroupKFold`, future-timestamp
   lookahead in rolling windows, holdout directory path traversal and symlink
   escapes, memorized test-identifier lookup cheats, `NaN` or `Inf` and
   uncalibrated probability submission poisoning, and three-gigabyte memory-bomb
   polynomial feature cross explosions.
2. GitHub profile and component supply-chain poisoning attacks (`A-GITHUB-01` to
   `A-GITHUB-06`) test top-level `os.system` and `subprocess` execution inside
   `setup.py` during static Abstract Syntax Tree (AST) card extraction, Zip-Slip
   and Tar-Slip archive traversal, typosquatted and homoglyph package identity
   spoofing (`reqeusts` and `cachet00ls`), indirect prompt injection inside
   Python docstrings, catastrophic backtracking regular expressions (`^(a+)+$`)
   in tool schemas, and GNU General Public License (GPL) to MIT licence
   laundering.
3. Multi-surface adversarial and strange user emulation scenarios (`A-USER-01`
   to `A-USER-06`) test 16-thread concurrent store writes and checkouts through
   `_FairQueueLock` in first-in, first-out (FIFO) arrival order without
   starvation, OAuth 2.1 Proof Key for Code Exchange (PKCE) `plain` downgrade
   and authorization code replay, cross-brand session cookie and staff-route
   escalation from `demos.baltor.ai` and `agentfeeds.si`, zero-width spaces and
   smart quotes with duplicate `Bearer` prefixes in Model Context Protocol (MCP)
   headers, 120-line Python tracebacks concatenated with minified JavaScript
   bundles pasted into `/api/v1/search`, and daily verification email budget
   exhaustion with constant-byte HTTP 202 anti-enumeration responses.
4. Public-good and creative media safety and quality scenarios (`A-DOMAIN-01`
   to `A-DOMAIN-06`) test National Institute for Occupational Safety and Health
   (NIOSH) Wet-Bulb Globe Temperature (WBGT) heat-stress underestimation at high
   humidity (`36C` and `85%` relative humidity), crisis shelter routing with hard
   wheelchair-ramp and bed-capacity constraints, 1080x1920 vertical video
   captions colliding with bottom `420px` and right `160px` keep-out zones,
   low-contrast (`1.65:1`) overlay text repaired to Web Content Accessibility
   Guidelines (WCAG) AAA (`>= 7.0:1`), procedural Karplus-Strong synthesizer
   direct-current (DC) offset and peak clipping above `0.0 dBFS`, and a
   self-approving model producer (`producer_id == reviewer_id`) attempting
   promotion to `baltor_reviewed`.

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

Within the `ComponentEnvelope` wrapper around the `adversarial_competition_guard`
slot, each scenario request passes the inbound layers in fixed order and leaves
through frustration avoidance:

```text
ComponentEnvelope Loop (for one scenario request, outermost first)
├── 1 frustration_avoidance  shapes every refusal as envelope_refusal/v1 with plain-English next actions
├── 2 carrier                checks workspace confinement, archive paths, NaN/Inf bounds, memory caps, and ReDoS
├── 3 handshake              verifies typosquatting edit distance, SPDX licence match, and capability declarations
├── 4 account                enforces OAuth 2.1 S256 PKCE, cross-brand cookie isolation, and independent review
├── 5 tracking               serializes 16-thread bursts via _FairQueueLock FIFO and enforces constant-202 email caps
├── 6 preflight              audits AST dataflow leakage and NIOSH/shelter safety, and runs pure media/query repairs
└── 7 nested_envelopes       enforces shared RecoveryAllowance(3), monotonic deadline, and maximum depth 4 (enter_nested)
```

## Multi-engine defense and verification comparison

The suite compares four swappable defense and verification engines behind the
`adversarial_competition_guard` slot and the `CompetitionDefenseResult`
contract:

1. `strict_zero_trust_blocker`: enforces deterministic carrier, handshake,
   account, tracking, and domain physics or accessibility guards (`14 / 18`
   attacks blocked), without deep Python AST dataflow inspection and with zero
   automatic self-repairs (`0 / 6` repairable scenarios recovered).
2. `ast_and_dataflow_leakage_auditor`: adds static Python AST and symbol-table
   dataflow auditing for fit-before-`GroupKFold` leakage, negative `.shift(-k)`
   and centered rolling lookahead, memorized test-identifier lookup tables, and
   top-level `setup.py` command execution (`18 / 18` attacks blocked), with
   automatic self-repairs disabled (`0 / 6` repairable scenarios recovered).
3. `tolerant_self_repair_normalizer`: combines the deterministic boundary guards
   with `_FairQueueLock` 16-thread FIFO burst serialization, MCP header
   zero-width and smart-quote stripping, 3-gram Locality-Sensitive Hashing (LSH)
   sub-token query distillation for 120-line tracebacks and minified JavaScript
   bundles, 1080x1920 vertical video keep-out clamping, WCAG AAA relative
   luminance contrast repair, and Karplus-Strong DC-offset removal with peak
   limiting (`6 / 6` repairable scenarios recovered and `0` false positives).
4. `cascade_7layer_competition_guard`: orchestrates the seven-layer
   `ComponentEnvelope` by running `ast_and_dataflow_leakage_auditor` first
   (blocking all `18 / 18` malicious or leaky scenarios immediately without
   consuming recovery attempts) and cascading recoverable preflight or
   concurrency refusals to `tolerant_self_repair_normalizer` within one shared
   `RecoveryAllowance` (`MAXIMUM_AUTOMATIC_ATTEMPTS = 3`), achieving `24 / 24`
   scenario pass (`100.0%` attacks blocked, `100.0%` strange-user and creative
   defects self-repaired, and `0.0%` false positives).

| Engine | Total passed | Malicious or leaky blocked | Strange or creative repaired | False positives on repairable | Mean latency (ms) | Total latency (ms) |
| --- | --- | --- | --- | --- | --- | --- |
| `strict_zero_trust_blocker` | 14 / 24 | 14 / 18 (77.8%) | 0 / 6 (0.0%) | 6 / 6 (100.0%) | 0.059 | 1.416 |
| `ast_and_dataflow_leakage_auditor` | 18 / 24 | 18 / 18 (100.0%) | 0 / 6 (0.0%) | 6 / 6 (100.0%) | 0.068 | 1.632 |
| `tolerant_self_repair_normalizer` | 20 / 24 | 14 / 18 (77.8%) | 6 / 6 (100.0%) | 0 / 6 (0.0%) | 0.172 | 4.128 |
| `cascade_7layer_competition_guard` | 24 / 24 | 18 / 18 (100.0%) | 6 / 6 (100.0%) | 0 / 6 (0.0%) | 0.175 | 4.200 |

## Complete 24-scenario emulation results

The table below records the observed outcome for each of the 24 scenarios across
the four engines, including the attack surface, primary envelope layer, fallback
chain exercised by `cascade_7layer_competition_guard`, and resulting
verification or `envelope_refusal/v1` code.

| Scenario ID | Surface | Scenario title | Primary layer | `strict_zero_trust_blocker` | `ast_and_dataflow_leakage_auditor` | `tolerant_self_repair_normalizer` | `cascade_7layer_competition_guard` | Observed code |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `A-KAGGLE-01` | Kaggle ML | Train-on-Test and Group-Split Data Leakage | `preflight` | Missed (Leak) | Blocked | Missed (Leak) | Blocked (`ast_dataflow`) | `train_on_test_group_leakage_refused` |
| `A-KAGGLE-02` | Kaggle ML | Future-Timestamp Lookahead Leakage in Time-Series Rolling Windows | `preflight` | Missed (Leak) | Blocked | Missed (Leak) | Blocked (`ast_dataflow`) | `future_timestamp_lookahead_refused` |
| `A-KAGGLE-03` | Kaggle ML | Holdout Directory Mount and Symlink Escape | `carrier` | Blocked | Blocked | Blocked | Blocked (`ast_dataflow`) | `holdout_symlink_or_path_traversal_refused` |
| `A-KAGGLE-04` | Kaggle ML | Hardcoded Test-ID and Memorized Submission Cheat Detector | `preflight` | Missed (Leak) | Blocked | Missed (Leak) | Blocked (`ast_dataflow`) | `memorized_submission_lookup_refused` |
| `A-KAGGLE-05` | Kaggle ML | NaN, Inf, and Uncalibrated Probability Submission Poisoning | `carrier` | Blocked | Blocked | Blocked | Blocked (`ast_dataflow`) | `submission_nan_inf_or_probability_bounds_refused` |
| `A-KAGGLE-06` | Kaggle ML | Memory-Bomb Feature Cross Explosion (`MEM_MAX=3G` Guard) | `nested_envelopes` | Blocked | Blocked | Blocked | Blocked (`ast_dataflow`) | `memory_bomb_feature_cross_refused` |
| `A-GITHUB-01` | GitHub Supply Chain | Malicious `setup.py` and `pyproject.toml` Top-Level `os.system` Execution | `preflight` | Missed (Leak) | Blocked | Missed (Leak) | Blocked (`ast_dataflow`) | `malicious_setup_code_execution_refused` |
| `A-GITHUB-02` | GitHub Supply Chain | Zip-Slip and Tar-Slip `../` and Symlink Escape During Unpacking | `carrier` | Blocked | Blocked | Blocked | Blocked (`ast_dataflow`) | `archive_zip_or_tar_slip_refused` |
| `A-GITHUB-03` | GitHub Supply Chain | Typosquatted GitHub/PyPI Package Identity Spoofing (`reqeusts`, `cachet00ls`) | `handshake` | Blocked | Blocked | Blocked | Blocked (`ast_dataflow`) | `typosquatted_package_identity_refused` |
| `A-GITHUB-04` | GitHub Supply Chain | Indirect Prompt Injection Hidden in JSDoc and Python Docstrings | `carrier` | Blocked | Blocked | Blocked | Blocked (`ast_dataflow`) | `docstring_indirect_prompt_injection_refused` |
| `A-GITHUB-05` | GitHub Supply Chain | Catastrophic Backtracking ReDoS Regex in Tool Schema (`^(a+)+$`) | `carrier` | Blocked | Blocked | Blocked | Blocked (`ast_dataflow`) | `catastrophic_redos_schema_pattern_refused` |
| `A-GITHUB-06` | GitHub Supply Chain | License Laundering and Copyleft Contamination (`GPL-3.0-only` as `MIT`) | `handshake` | Blocked | Blocked | Blocked | Blocked (`ast_dataflow`) | `license_laundering_copyleft_mismatch_refused` |
| `A-USER-01` | Multi-Surface User | 16-Thread Concurrent Store Write and Checkout Burst (`_FairQueueLock` FIFO) | `tracking` | Refused (FP) | Refused (FP) | Repaired | Repaired (`ast` -> `tolerant`) | `fair_queue_fifo_16_thread_burst_verified` |
| `A-USER-02` | Multi-Surface User | OAuth 2.1 PKCE `code_verifier` Downgrade and Authorization Code Replay | `account` | Blocked | Blocked | Blocked | Blocked (`ast_dataflow`) | `pkce_downgrade_or_auth_code_replay_refused` |
| `A-USER-03` | Multi-Surface User | Cross-Brand Session Cookie and Staff-Tool Escalation Probe | `account` | Blocked | Blocked | Blocked | Blocked (`ast_dataflow`) | `cross_brand_cookie_or_staff_escalation_refused` |
| `A-USER-04` | Multi-Surface User | Strange User Pasting Zero-Width Spaces, Smart Quotes, and Duplicate `Bearer` | `frustration_avoidance` | Refused (FP) | Refused (FP) | Repaired | Repaired (`ast` -> `tolerant`) | `repaired_zero_width_smart_quotes_and_bearer` |
| `A-USER-05` | Multi-Surface User | Strange User Pasting 120-Line Python Traceback and Minified JS Bundle | `preflight` | Refused (FP) | Refused (FP) | Repaired | Repaired (`ast` -> `tolerant`) | `repaired_120_line_traceback_and_minified_js_query` |
| `A-USER-06` | Multi-Surface User | Account Email Daily Budget Exhaustion and Enumeration Timing Prober | `tracking` | Blocked | Blocked | Blocked | Blocked (`ast_dataflow`) | `email_budget_exhausted_constant_202_enforced` |
| `A-DOMAIN-01` | Public Good & Creative | Unsafe Worker Heat-Stress WBGT Underestimation (`36C`, `85% RH`) | `preflight` | Blocked | Blocked | Blocked | Blocked (`ast_dataflow`) | `unsafe_wbgt_heat_stress_underestimation_refused` |
| `A-DOMAIN-02` | Public Good & Creative | Crisis Shelter Router Returning Full and Inaccessible Shelter to Wheelchair User | `preflight` | Blocked | Blocked | Blocked | Blocked (`ast_dataflow`) | `inaccessible_or_full_crisis_shelter_refused` |
| `A-DOMAIN-03` | Public Good & Creative | 1080x1920 Vertical Video Caption Colliding with Bottom `420px` and Right `160px` | `preflight` | Refused (FP) | Refused (FP) | Repaired | Repaired (`ast` -> `tolerant`) | `repaired_vertical_video_keep_out_zone_collision` |
| `A-DOMAIN-04` | Public Good & Creative | Low-Contrast `#c0392b` on `#8a2820` (`1.65:1`) Repaired to WCAG AAA `>= 7.0:1` | `preflight` | Refused (FP) | Refused (FP) | Repaired | Repaired (`ast` -> `tolerant`) | `repaired_wcag_aaa_overlay_contrast` |
| `A-DOMAIN-05` | Public Good & Creative | Audio Clipping (`> 0.0 dBFS`) and DC Offset in Procedural Karplus-Strong Synth | `preflight` | Refused (FP) | Refused (FP) | Repaired | Repaired (`ast` -> `tolerant`) | `repaired_audio_dc_offset_and_peak_limiter` |
| `A-DOMAIN-06` | Public Good & Creative | Self-Approving Model Producer (`producer_id == reviewer_id`) Promotion Attempt | `account` | Blocked | Blocked | Blocked | Blocked (`ast_dataflow`) | `self_approving_producer_promotion_refused` |

## Known-wrong controls

Each of the 18 security, benchmark-integrity, supply-chain, and domain-safety
guards pairs with a `removed_*` known-wrong control that disables that single
guard and verifies that the corresponding attack or unsafe output slips through
(`malicious_leaked_when_removed = True`). All 18 controls pass.

| Control name | Target scenario | Surface | Guarded code | Unguarded code when removed | Leak detected |
| --- | --- | --- | --- | --- | --- |
| `removed_kaggle_group_split_leakage_guard` | `A-KAGGLE-01` | `kaggle_benchmark_integrity` | `train_on_test_group_leakage_refused` | `known_wrong_attack_or_leakage_slipped_through` | Passed (`True`) |
| `removed_kaggle_lookahead_window_guard` | `A-KAGGLE-02` | `kaggle_benchmark_integrity` | `future_timestamp_lookahead_refused` | `known_wrong_attack_or_leakage_slipped_through` | Passed (`True`) |
| `removed_kaggle_holdout_path_traversal_guard` | `A-KAGGLE-03` | `kaggle_benchmark_integrity` | `holdout_symlink_or_path_traversal_refused` | `known_wrong_attack_or_leakage_slipped_through` | Passed (`True`) |
| `removed_kaggle_memorized_submission_guard` | `A-KAGGLE-04` | `kaggle_benchmark_integrity` | `memorized_submission_lookup_refused` | `known_wrong_attack_or_leakage_slipped_through` | Passed (`True`) |
| `removed_kaggle_nan_inf_probability_guard` | `A-KAGGLE-05` | `kaggle_benchmark_integrity` | `submission_nan_inf_or_probability_bounds_refused` | `known_wrong_attack_or_leakage_slipped_through` | Passed (`True`) |
| `removed_kaggle_memory_bomb_guard` | `A-KAGGLE-06` | `kaggle_benchmark_integrity` | `memory_bomb_feature_cross_refused` | `known_wrong_attack_or_leakage_slipped_through` | Passed (`True`) |
| `removed_github_setup_ast_exec_guard` | `A-GITHUB-01` | `github_supply_chain` | `malicious_setup_code_execution_refused` | `known_wrong_attack_or_leakage_slipped_through` | Passed (`True`) |
| `removed_github_archive_slip_guard` | `A-GITHUB-02` | `github_supply_chain` | `archive_zip_or_tar_slip_refused` | `known_wrong_attack_or_leakage_slipped_through` | Passed (`True`) |
| `removed_github_typosquat_identity_guard` | `A-GITHUB-03` | `github_supply_chain` | `typosquatted_package_identity_refused` | `known_wrong_attack_or_leakage_slipped_through` | Passed (`True`) |
| `removed_github_docstring_injection_guard` | `A-GITHUB-04` | `github_supply_chain` | `docstring_indirect_prompt_injection_refused` | `known_wrong_attack_or_leakage_slipped_through` | Passed (`True`) |
| `removed_github_redos_schema_guard` | `A-GITHUB-05` | `github_supply_chain` | `catastrophic_redos_schema_pattern_refused` | `known_wrong_attack_or_leakage_slipped_through` | Passed (`True`) |
| `removed_github_license_laundering_guard` | `A-GITHUB-06` | `github_supply_chain` | `license_laundering_copyleft_mismatch_refused` | `known_wrong_attack_or_leakage_slipped_through` | Passed (`True`) |
| `removed_user_pkce_and_code_replay_guard` | `A-USER-02` | `multi_surface_user` | `pkce_downgrade_or_auth_code_replay_refused` | `known_wrong_attack_or_leakage_slipped_through` | Passed (`True`) |
| `removed_user_cross_brand_cookie_staff_guard` | `A-USER-03` | `multi_surface_user` | `cross_brand_cookie_or_staff_escalation_refused` | `known_wrong_attack_or_leakage_slipped_through` | Passed (`True`) |
| `removed_user_email_budget_and_timing_guard` | `A-USER-06` | `multi_surface_user` | `email_budget_exhausted_constant_202_enforced` | `known_wrong_attack_or_leakage_slipped_through` | Passed (`True`) |
| `removed_domain_wbgt_heat_stress_guard` | `A-DOMAIN-01` | `public_good_and_creative` | `unsafe_wbgt_heat_stress_underestimation_refused` | `known_wrong_attack_or_leakage_slipped_through` | Passed (`True`) |
| `removed_domain_shelter_accessibility_guard` | `A-DOMAIN-02` | `public_good_and_creative` | `inaccessible_or_full_crisis_shelter_refused` | `known_wrong_attack_or_leakage_slipped_through` | Passed (`True`) |
| `removed_domain_self_approval_governance_guard` | `A-DOMAIN-06` | `public_good_and_creative` | `self_approving_producer_promotion_refused` | `known_wrong_attack_or_leakage_slipped_through` | Passed (`True`) |

## Reproduce the verification locally

Run the benchmark and unit test suite under the memory cap:

```bash
export TMPDIR=$HOME/.le-ci-tmp/tmp-adv-comp
mkdir -p "$TMPDIR" && touch "$TMPDIR/.keep-in-place"
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python tools/adversarial_competition_and_user_suite.py
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_adversarial_competition_and_user_suite.py
```

## Limits and deeper references

This suite is a deterministic, in-process verification over the real record,
lock, and layer primitives in
[`src/loop_engine/core/engines/envelope.py`](../../src/loop_engine/core/engines/envelope.py),
[`src/loop_engine/core/engines/envelope_tracking.py`](../../src/loop_engine/core/engines/envelope_tracking.py),
[`src/loop_engine/core/engines/envelope_preflight.py`](../../src/loop_engine/core/engines/envelope_preflight.py),
and
[`src/loop_engine/core/service_runtime/storage.py`](../../src/loop_engine/core/service_runtime/storage.py).
It complements the 18-persona emulation record in
[`docs/verification/ADVERSARIAL-PERSONA-EMULATION-2026-10-16.md`](ADVERSARIAL-PERSONA-EMULATION-2026-10-16.md)
and does not replace live post-deployment verification against the production
Fly.io and Cloudflare endpoints recorded in
[`docs/architecture/MVP-CLIENT-SERVER.md`](../architecture/MVP-CLIENT-SERVER.md).
