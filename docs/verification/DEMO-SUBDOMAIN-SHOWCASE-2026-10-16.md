# Demo subdomain and multi-domain side-by-side showcase engine suite verification (2026-10-16)

This report records the design, GitHub developer archetype registry,
seven-layer component envelope integration, head-to-head engine benchmarks, and
adversarial verification of the demo subdomain and multi-domain showcase suite
in
[tools/demo_subdomain_showcase_engines.py](../../tools/demo_subdomain_showcase_engines.py)
and
[tools/test_demo_subdomain_showcase_engines.py](../../tools/test_demo_subdomain_showcase_engines.py).

## Outcome and scope

Baltor serves interactive side-by-side comparisons, executable playground
bundles, brand-syndicated cards, and static Markdown twins across
`demos.baltor.ai`, `gallery.baltor.ai`, `agentbriefs.si`, `skillsforgood.org`,
and `agentstudios.si`. Every demo projection runs inside the seven-layer
component envelope defined in
[src/loop_engine/core/engines/envelope.py](../../src/loop_engine/core/engines/envelope.py),
[src/loop_engine/core/engines/envelope_preflight.py](../../src/loop_engine/core/engines/envelope_preflight.py),
and
[src/loop_engine/core/engines/envelope_tracking.py](../../src/loop_engine/core/engines/envelope_tracking.py).

All 15 unit tests in
[tools/test_demo_subdomain_showcase_engines.py](../../tools/test_demo_subdomain_showcase_engines.py)
and all six self-test assertions in
[tools/demo_subdomain_showcase_engines.py](../../tools/demo_subdomain_showcase_engines.py)
pass with zero leaks of credentials, session cookies, or unverified benchmark
claims.

## Where the suite fits in the Loop architecture

Every executable graph vertex in Loop Engine is a `Loop`. Contract cards,
trial receipts, rendered HTML comparison tables, static Markdown twins, and
showcase engine adapters are passive data or swappable engines invoked by a
`Loop`, never separate graph vertices.

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
    └── Engine slot used by Loop steps for demo subdomain and brand showcase projection:
        └── Slot: demo_subdomain_showcase (v1.0.0)
            ├── Engine 1: interactive_side_by_side_diff_showcase_engine
            ├── Engine 2: executable_playground_receipt_engine
            ├── Engine 3: brand_syndicated_demo_projection_engine
            └── Engine 4: static_markdown_twin_fallback_engine
```

A discrete cognitive or act step Loop node receives a narrowly scoped
assignment, selected context and resources, separately initialized harnesses,
and explicit rules for permitted harness changes. It runs expectation checks,
iterates until declared completion conditions are met, can continue producing
alternative outputs when configured, protects against repeated external
effects, and keeps publication of an output separate from completion of the
step. When a Solution Loop or Practitioner Loop projects verified side-by-side
comparisons onto `demos.baltor.ai`, `gallery.baltor.ai`, `agentbriefs.si`,
`skillsforgood.org`, or `agentstudios.si`, it invokes the
`demo_subdomain_showcase` slot through its seven-layer envelope.

## GitHub developer archetype registry and evidence separation

The registry in
[tools/demo_subdomain_showcase_engines.py](../../tools/demo_subdomain_showcase_engines.py)
(`github_developer_archetypes/v1`) defines 16 developer project archetypes
across four categories (four archetypes per category). In accordance with
constitutional evidence rules, observed model pilot runs and deterministic
contract-verifier simulations are explicitly separated in code and in every
rendered card:

- **Observed pilot trials (`observed_pilot_and_deterministic_contract_verifier`, 3 archetypes)**:
  Anchored to saved Ollama Cloud `gemma4:31b` trials in
  [artifacts/comparison-pilot-2026-10-16/results/summary.json](../../artifacts/comparison-pilot-2026-10-16/results/summary.json)
  and
  `docs/benchmarks/OPEN-SOURCE-COMPARISON-PILOT-2026-10-15.md`
  across `claude_code`, `codex_cli`, `gemini_cli`, and `open_harness_mcp`.
- **Deterministic contract-verifier simulations (`deterministic_contract_verifier_simulation`, 13 archetypes)**:
  Anchored to deterministic Python AST and invariant verifiers executing
  against baseline snippets versus contract-card implementations. These 13
  entries are labeled as deterministic verifier simulations rather than live
  LLM pilot runs.

Across all 16 archetypes, baseline implementations without Baltor contract
cards pass `110 / 164` deterministic verifier checks (`0.6707`), whereas
contract-guided implementations pass `164 / 164` checks (`1.0000`).

### Category A: Kaggle AI and machine learning projects (`kaggle_ai_ml`)

| Index | Archetype ID | Upstream reference and popularity evidence | Evidence basis | Without Baltor checks | With Baltor checks | Contract card invariant verified |
| ---: | :--- | :--- | :--- | ---: | ---: | :--- |
| 1 | `spaceship_titanic_groupkfold` | Kaggle Spaceship Titanic (`17336d55...`, 8,050 votes on `gusthema/spaceship-titanic-with-tfdf`) | `observed_pilot_and_deterministic_contract_verifier` | 3 / 5 | 5 / 5 | Derive `travel_group` from `PassengerId` prefix and split via `GroupKFold(groups=travel_group)` to prevent 0.0144 CV leakage |
| 2 | `ames_house_prices_oof_rmsle` | Kaggle House Prices (`ames-housing-v1-2026-10-16`, 4,800+ competition notebooks) | `deterministic_contract_verifier_simulation` | 2 / 5 | 5 / 5 | Compute `Neighborhood` target encoding strictly inside out-of-fold training indices and optimize `log1p(SalePrice)` |
| 3 | `store_sales_lag_leakage_free` | Kaggle Store Sales Time-Series Forecasting (`favorita-store-sales-v1-2026-10-16`, 3,900+ teams) | `deterministic_contract_verifier_simulation` | 2 / 5 | 5 / 5 | Shift rolling sales windows by the 16-day forecast horizon grouped by `(store_nbr, family)` |
| 4 | `credit_card_fraud_calibrated_prauc` | ULB Credit Card Fraud (`ulb-creditcard-v1-2026-10-16`, 11,200+ dataset upvotes) | `deterministic_contract_verifier_simulation` | 1 / 5 | 5 / 5 | Preserve the 0.172% validation positive rate without pre-split SMOTE and evaluate PR-AUC and calibrated Brier loss |

### Category B: Common GitHub profile and backend projects (`github_common_projects`)

| Index | Archetype ID | Upstream reference and popularity evidence | Evidence basis | Without Baltor checks | With Baltor checks | Contract card invariant verified |
| ---: | :--- | :--- | :--- | ---: | ---: | :--- |
| 5 | `cachetools_tlru_cache` | `tkem/cachetools` (`be0b2eba...`, 2,787 GitHub stars) | `observed_pilot_and_deterministic_contract_verifier` | 31 / 34 | 34 / 34 | Maintain a min-heap for out-of-order per-item `ttu` expirations and discard items with `ttu <= now` on insertion |
| 6 | `python_dotenv_rfc_parser` | `theskumar/python-dotenv` (`a565c2cc...`, 8,900 GitHub stars) | `observed_pilot_and_deterministic_contract_verifier` | 54 / 56 | 56 / 56 | Escape backslashes before double quotes on `set_key` round trips and strip `#` comments only after unquoted whitespace |
| 7 | `sqlite_wal_rate_limiter_webhook` | `oven-sh/bun` SQLite WAL pattern (`sqlite-wal-webhook-pattern-2026-10-16`, 18,500+ repositories) | `deterministic_contract_verifier_simulation` | 2 / 6 | 6 / 6 | Enable `PRAGMA journal_mode=WAL`, `BEGIN IMMEDIATE`, and `INSERT OR IGNORE` over `UNIQUE(event_id, payload_sha256)` |
| 8 | `mcp_streamable_http_server` | `modelcontextprotocol/python-sdk` (`mcp-python-sdk-2026-10-16`, 24,000+ SDK stars) | `deterministic_contract_verifier_simulation` | 2 / 5 | 5 / 5 | Keep discovery schema under 400 tokens (`search_cards`, `load_contract_card`) and enforce `is_relative_to(workspace_root)` |

### Category C: Public good and civic tech projects (`public_good_projects`)

| Index | Archetype ID | Upstream reference and popularity evidence | Evidence basis | Without Baltor checks | With Baltor checks | Contract card invariant verified |
| ---: | :--- | :--- | :--- | ---: | ---: | :--- |
| 9 | `osha_niosh_wbgt_calculator` | `CDCgov/niosh-heat-safety` (`niosh-wbgt-2016-rev-2026-10-16`) | `deterministic_contract_verifier_simulation` | 1 / 5 | 5 / 5 | Compute indoor `0.7*T_nwb + 0.3*T_g` and outdoor solar `0.7*T_nwb + 0.2*T_g + 0.1*T_db` with clothing adjustments and RAL/REL limits |
| 10 | `offline_crisis_shelter_wcag_aaa_router` | `sahana/eden` (`sahana-disaster-triage-2026-10-16`, 1,950+ stars) | `deterministic_contract_verifier_simulation` | 2 / 6 | 6 / 6 | Filter by ADA wheelchair and generator medical power before Haversine ranking; enforce WCAG-AAA 7:1 contrast and zero external CDNs |
| 11 | `open_air_quality_pm25_advisory` | `openaq/openaq-api-v2` (`epa-2024-pm25-breakpoint-table-2026-10-16`, 1,100+ stars) | `deterministic_contract_verifier_simulation` | 2 / 5 | 5 / 5 | Truncate PM2.5 to `0.1 ug/m3` and interpolate against the revised 2024 EPA breakpoints (`0.0-9.0` Good, `9.1-35.4` Moderate) |
| 12 | `municipal_benefits_rule_verifier` | `PolicyEngine/policyengine-us` (`policyengine-snap-liheap-rules-2026-10-16`, 1,400+ stars) | `deterministic_contract_verifier_simulation` | 2 / 5 | 5 / 5 | Compute income and deductions in integer cents, apply the elderly/disabled gross-income exemption, and emit `7_CFR_273.9(a)` citations |

### Category D: Creative design, motion, and playable media (`design_media_projects`)

| Index | Archetype ID | Upstream reference and popularity evidence | Evidence basis | Without Baltor checks | With Baltor checks | Contract card invariant verified |
| ---: | :--- | :--- | :--- | ---: | ---: | :--- |
| 13 | `reelkit_vertical_motion_explainer` | `remotion-dev/remotion` (`reelkit-1080x1920-layout-contract-2026-10-16`, 21,800+ stars) | `deterministic_contract_verifier_simulation` | 2 / 7 | 7 / 7 | Reserve bottom 20% (`y >= 1536`) and right 12% (`x >= 950`) on a 1080x1920 canvas, enforce beat durations `>= 0.25s`, and `>= 4.5:1` contrast |
| 14 | `fourier_epicycle_dft_animator` | `3b1b/manim` (`fourier-epicycle-dft-contract-2026-10-16`, 62,000+ stars) | `deterministic_contract_verifier_simulation` | 1 / 5 | 5 / 5 | Resample closed SVG contours to uniform arc-length steps, normalize complex DFT by `1/N`, and sort epicycles by descending amplitude |
| 15 | `html5_rigid_body_karplus_strong_arena` | `liabru/matter-js` (`symplectic-euler-karplus-strong-2026-10-16`, 17,400+ stars) | `deterministic_contract_verifier_simulation` | 2 / 5 | 5 / 5 | Step rigid bodies with fixed `1/120s` symplectic Euler and Baumgarte positional correction so energy drift stays within `0.5%` |
| 16 | `headless_blender_glb_contract_verifier` | `KhronosGroup/glTF-Validator` (`gltf-2.0-pbr-scene-contract-2026-10-16`, 4,100+ stars) | `deterministic_contract_verifier_simulation` | 1 / 6 | 6 / 6 | Apply object transforms to mesh vertices, ground minimum `z` to `0.0`, verify positive determinant, and clamp PBR metallic/roughness to `[0.0, 1.0]` |

## Seven-layer component envelope and four swappable engines

The `DemoSubdomainShowcaseOrchestrator` wraps the `demo_subdomain_showcase`
slot (`v1.0.0`) in all seven layers of `ComponentEnvelope`:

1. **Layer 1 (`frustration_avoidance`)**: Enforces a shared `RecoveryAllowance`
   budget across all four candidate engines so cascade failover never amplifies
   retries, and attaches plain-English `next_steps` to every refusal.
2. **Layer 2 (`carrier`)**: Validates schema `demo_subdomain_showcase_request/v1`,
   archetype existence, target hostname admission (`demos.baltor.ai`,
   `gallery.baltor.ai`, `agentbriefs.si`, `skillsforgood.org`,
   `agentstudios.si`), and harness compatibility.
3. **Layer 3 (`handshake`)**: Enforces zero cross-brand session cookies on
   `.si`, `.org`, and public demo subdomains (`cookies_set: 0`), blocks
   external identity provider redirects on non-`baltor.ai` domains, and verifies
   category-to-host syndication rules.
4. **Layer 4 (`account`)**: Enforces `read_only_public_projection` authority,
   refuses state-mutation requests on demo endpoints, and refuses live
   unbudgeted model inference calls (`live_model_call_requested: True`) so demo
   traffic always serves pre-verified artifacts at `$0` model cost.
5. **Layer 5 (`tracking`)**: Computes deterministic SHA-256 `correlation_id`
   digests, caches idempotent replays (`replayed: True`), and records
   `release_resync` events when `release_revision` advances.
6. **Layer 6 (`preflight`)**: Verifies 64-hex SHA-256 trial receipts, quarantines
   raw credentials (`baltor_`, `sk-`, `ghp_`, `AKIA`, `AIza`, `xoxb-`, `Bearer`,
   `PRIVATE KEY`) without echoing secret values in `EnvelopeRefusal`, and checks
   copy against `humanizer-context.md` rules (with pure self-repair when
   `allow_self_repair: True`).
7. **Layer 7 (`nested_envelopes`)**: Emits child `ComponentEnvelope` records
   linking `parent_invocation_id` for the contract-verifier receipt check and
   brand-syndication badge check.

### Head-to-head benchmark across all 16 archetypes

All four engines were benchmarked across all 16 archetypes in
`run_head_to_head_benchmark()` in
[tools/demo_subdomain_showcase_engines.py](../../tools/demo_subdomain_showcase_engines.py):

| Priority | Engine ID | Output format | Archetypes tested | Success rate | Mean latency (ms) | P95 latency (ms) | Primary role |
| ---: | :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| 1 | `interactive_side_by_side_diff_showcase_engine` | `html+markdown+json` | 16 | 100.0% | 0.64 | 0.64 | Interactive Without-Baltor vs. With-Baltor unified diff, verifier scorecard, and SHA-256 provenance badge |
| 2 | `executable_playground_receipt_engine` | `playground_bundle_json+html` | 16 | 100.0% | 0.88 | 0.88 | Deterministic offline Python AST verifier and sandboxed HTML5/SVG preview bundle (`network_egress_allowed: False`) |
| 3 | `brand_syndicated_demo_projection_engine` | `syndicated_html+json` | 16 | 100.0% | 0.45 | 0.45 | Domain-tailored showcase cards for `skillsforgood.org`, `agentstudios.si`, `agentbriefs.si`, and `gallery.baltor.ai` |
| 4 | `static_markdown_twin_fallback_engine` | `markdown_twin+html` | 16 | 100.0% | 0.25 | 0.25 | Zero-JavaScript static Markdown twin (`/demos/<id>.md`) and semantic HTML `<article>` fallback |

### Cascade failover verification

When simultaneous engine faults are injected across the fleet (`Engine 1`
degraded on `spaceship_titanic_groupkfold`, `Engine 1 + Engine 2` degraded on
`osha_niosh_wbgt_calculator`, and `Engine 1 + Engine 2 + Engine 3` degraded on
`reelkit_vertical_motion_explainer`), `DemoSubdomainShowcaseOrchestrator`
cascades across the declared fallback order within a single shared
`RecoveryAllowance` and completes `16 / 16` archetypes with zero downtime:

- `13` archetypes served by `interactive_side_by_side_diff_showcase_engine`
- `1` archetype (`spaceship_titanic_groupkfold`) failed over to
  `executable_playground_receipt_engine`
- `1` archetype (`osha_niosh_wbgt_calculator`) failed over to
  `brand_syndicated_demo_projection_engine`
- `1` archetype (`reelkit_vertical_motion_explainer`) failed over to
  `static_markdown_twin_fallback_engine`

## Known-wrong security and governance controls

All seven adversarial probes in `run_head_to_head_benchmark()` are refused
inside the envelope before any showcase engine executes (`engine_dispatched:
False`):

| Probe | Target hostname | Refused by layer | Refusal code | Verified behavior |
| :--- | :--- | :--- | :--- | :--- |
| `unverified_benchmark_missing_sha256_receipt` | `demos.baltor.ai` | `preflight` | `unverified_benchmark_claim_missing_sha256_receipt` | Refuses benchmark cards with missing or malformed SHA-256 trial receipts |
| `raw_credential_in_demo_payload` | `demos.baltor.ai` | `preflight` | `demo_payload_raw_credential_forbidden` | Quarantines `sk-proj-...` and `baltor_...` tokens and omits the raw secret from `EnvelopeRefusal` |
| `cross_brand_session_cookie_on_skillsforgood` | `skillsforgood.org` | `handshake` | `cross_brand_session_cookie_forbidden` | Refuses `baltor_session` cookies on `.org` public-good projections |
| `cross_brand_session_cookie_on_agentstudios` | `agentstudios.si` | `handshake` | `cross_brand_session_cookie_forbidden` | Refuses session cookies on `.si` creative studio projections |
| `cross_brand_category_mismatch_on_skillsforgood` | `skillsforgood.org` | `handshake` | `cross_brand_category_projection_mismatch` | Refuses projecting commercial Kaggle/backend archetypes onto `skillsforgood.org` |
| `banned_negative_framing_without_repair` | `demos.baltor.ai` | `preflight` | `humanizer_negative_framing_or_slop_forbidden` | Refuses copy containing banned negative framing (`not a chat wrapper`, `delve into`, em/en dashes) when `allow_self_repair: False` |
| `live_unbudgeted_model_call_on_demo_surface` | `demos.baltor.ai` | `account` | `demo_showcase_live_model_call_forbidden` | Refuses live LLM inference calls on public demo routes |

## Reproduction commands and limits

Run the self-test, unit test suite, and single-file hardcoding audit from the
repository root:

```bash
PYTHONPATH=src /home/username/loop-engine/.venv/bin/python tools/demo_subdomain_showcase_engines.py
PYTHONPATH=src /home/username/loop-engine/.venv/bin/python -m unittest -v tools/test_demo_subdomain_showcase_engines.py
```

Current limits:

- Three of the 16 archetypes are backed by observed Ollama Cloud `gemma4:31b`
  pilot trials in `artifacts/comparison-pilot-2026-10-16/results/summary.json`,
  while the remaining 13 archetypes are backed by deterministic contract-card
  verifier simulations and are labeled accordingly on every rendered surface.
- Public demo routes serve pre-verified, content-addressed artifacts with zero
  live model spend; running custom prompts against a user's own model endpoint
  requires the user's own harness or API key.

## References

- [Demo subdomain showcase engines implementation](../../tools/demo_subdomain_showcase_engines.py)
- [Demo subdomain showcase unit tests](../../tools/test_demo_subdomain_showcase_engines.py)
- Open-source comparison pilot report (`docs/benchmarks/OPEN-SOURCE-COMPARISON-PILOT-2026-10-15.md`)
- [Envelope runtime implementation](../../src/loop_engine/core/engines/envelope.py)
- [Functional component standard](../architecture/FUNCTIONAL-COMPONENT-STANDARD.md)
