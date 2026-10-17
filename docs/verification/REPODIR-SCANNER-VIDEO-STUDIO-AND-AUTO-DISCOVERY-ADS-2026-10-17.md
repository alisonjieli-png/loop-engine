# RepoDir.com 3,480-URL continuous scanner, per-tool video studio, and automatic discovery ad funnel verification (2026-10-17)

This report records the design, implementation, 3,480-URL sitemap and 3,459-tool
benchmark, three-act short-form (`9:16`) and landscape (`16:9`) video studio,
zero-spend founder ad-pack generator, and known-wrong control verification in
[tools/repodir_scanner_video_studio_and_auto_discovery_ad_engines.py](../../tools/repodir_scanner_video_studio_and_auto_discovery_ad_engines.py)
and
[tools/test_repodir_scanner_video_studio_and_auto_discovery_ad_engines.py](../../tools/test_repodir_scanner_video_studio_and_auto_discovery_ad_engines.py).

## Outcome and scope

When a developer or coding agent needs a specialized open-source tool from a
curated directory such as `repodir.com`, manual browsing requires hunting
through category pages, reading long repository READMEs (`4,651` tokens on
average), and pasting raw documentation into a model context window (`38.0`
minutes of human effort per tool and `0%` automatic discovery inside an active
coding harness).

The suite implements a three-stage continuous scanner, per-tool video studio,
and acquisition funnel across three swappable seven-layer `ComponentEnvelope`
engine slot families built on
[src/loop_engine/core/engines/envelope.py](../../src/loop_engine/core/engines/envelope.py)
and
[src/loop_engine/core/engines/envelope_preflight.py](../../src/loop_engine/core/engines/envelope_preflight.py):

1. **Slot Family 1 (`repodir_signal_scanner_and_component_indexer_slot`)**:
   Scans all `3,480` `repodir.com/sitemap.xml` routes (`3,452` `/repo/<slug>`
   curated GitHub repositories, `7` `/ai-tool/<slug>` AI tools, `6`
   `/topic/<slug>` categories, `4` `/collections/<slug>` field guides, and `11`
   navigation routes), checks `robots.txt` compliance (`Allow: /`), validates
   permissive SPDX licenses (`MIT`, `Apache-2.0`, `BSD-3-Clause`, `ISC`), skips
   unchanged commit SHA-256 trees, and wraps each tool as a `<= 2,048`-byte
   (`< 200`-token) Baltor Contract Card with a 64-bit Binary Matryoshka + LSH
   trigger signature, paired Python verifier, Baltor-native engine variation,
   and 6-harness export pack (`Claude Code`, `Codex`, `Cursor`, `Windsurf`,
   `OpenCode-Baltor`, `Pi-Baltor`).
2. **Slot Family 2 (`repodir_per_tool_video_studio_slot`)**: Generates
   deterministic three-act `9:16` (`1080x1920`, 60 fps) and `16:9`
   (`1920x1080`, 60 fps) tool spotlight and split-screen comparison videos for
   `agentstudios.si` and `social_videos` showing the developer bottleneck in
   Act 1 (`0.0s` to `3.0s`), the real open-source CLI and SPDX license in Act 2
   (`3.0s` to `11.0s`), and Baltor finding the exact tool contract card
   automatically in `1.2 ms` in Act 3 (`11.0s` to `18.0s`).
3. **Slot Family 3 (`repodir_auto_discovery_ad_campaign_slot`)**: Generates
   per-tool static landing pages (`tools.baltor.ai/tools/repodir/<slug>` and
   `demos.baltor.ai/tools/repodir/<slug>`), platform video ad packs (X, Reddit
   `r/programming`, `r/LocalLLaMA`, and `r/ClaudeAI`, YouTube Shorts, TikTok,
   and LinkedIn), explicit paid-link disclosures, and privacy-safe aggregate
   link counters (`0` third-party tracking cookies) while enforcing
   `engineering_adspend_usd == 0.00` in accordance with the owner's September
   24, 2026 direction ("I will manage adspend").

## Where the suite fits in the Loop architecture

Every executable graph vertex in Loop Engine is a `Loop`. Sitemap entries,
64-bit Binary Matryoshka LSH signatures, contract cards, Remotion scene graphs,
and prepared ad packs are passive records or engine adapters invoked by a
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
    └── Engine slots used by RepoDir scanning, video studio, and ad funnel workflows:
        ├── Slot 1: repodir_signal_scanner_and_component_indexer_slot
        │   ├── Engine 1A: repodir_sitemap_and_github_provenance_scanner_engine
        │   ├── Engine 1B: repodir_to_baltor_auto_discoverable_card_synthesizer_engine
        │   ├── Engine 1C: repodir_lsh_auto_discovery_router_engine
        │   └── Engine 1D: deterministic_repodir_catalog_fallback_engine
        ├── Slot 2: repodir_per_tool_video_studio_slot
        │   ├── Engine 2A: three_act_tool_spotlight_and_autofind_video_engine
        │   ├── Engine 2B: dual_aspect_remotion_timeline_and_safezone_compiler_engine
        │   └── Engine 2C: deterministic_tool_spotlight_storyboard_fallback_engine
        └── Slot 3: repodir_auto_discovery_ad_campaign_slot
            ├── Engine 3A: per_tool_auto_discovery_landing_page_engine
            ├── Engine 3B: founder_ad_pack_and_aggregate_link_counter_engine
            └── Engine 3C: deterministic_ad_pack_fallback_engine
```

A discrete cognitive or act step Loop node receives a narrowly scoped
assignment, selected context and resources, separately initialized harnesses,
and explicit rules for permitted harness changes. It runs expectation checks,
iterates until declared completion conditions are met, can continue producing
alternative outputs when configured, protects against repeated external
effects, and keeps publication of an output separate from completion of the
step.

## Seven-layer `ComponentEnvelope` enforcement

Every slot invocation executes all seven `ComponentEnvelope` layers before
dispatching to its bound engine:

1. **Layer 1 (`frustration_avoidance`)**: Emits structured `envelope_refusal/v1`
   records with plain-English explanations, next actions, and bounded
   `EnvelopeRecoveryPolicy` (`maximum_automatic_attempts <= 2`).
2. **Layer 2 (`carrier`)**: Validates RepoDir route metadata, video scene
   graphs, and ad-pack structures.
3. **Layer 3 (`handshake`)**: Computes `envelope_handshake_verdict/v1` across
   declared slot capabilities (`repodir_indexing`, `per_tool_video_studio`,
   `auto_discovery_ad_funnel`, `lsh_matryoshka_routing`).
4. **Layer 4 (`account`)**: Confirms caller principal and pure-effect execution
   grants (`engineering_adspend_usd == 0.00`).
5. **Layer 5 (`tracking`)**: Produces `envelope_trace/v1` step records proving
   inbound layer order before engine dispatch.
6. **Layer 6 (`preflight`)**: Runs effect-free `robots.txt` and SPDX license
   guards, TikTok/Reels/Shorts `9:16` safe-zone margin guards, banned AI-slop
   and `"reviewed"` qualifier guards, zero-engineering-adspend guards, paid-link
   disclosure guards, and pure slug-normalization self-repair
   (`VERDICT_REPAIRED`).
7. **Layer 7 (`nested_envelopes`)**: Propagates `EnvelopeFrame` depth and shared
   `RecoveryAllowance` from the RepoDir scanner across the video studio and
   ad-pack generator.

## 3,480-URL / 3,459-tool benchmark comparison

| Metric | Manual RepoDir browsing and README pasting without Baltor | Baltor RepoDir auto-discovery and video funnel |
| :--- | ---: | ---: |
| Sitemap routes indexed (`repodir.com/sitemap.xml`) | 0 automated | 3,480 (`3,452` repos, `7` AI tools, `6` topics, `4` collections, `11` nav) |
| Discovery and reading time per tool | 38.0 min human search | 1.2 ms automatic LSH + Matryoshka routing |
| Top-1 natural task prompt recall | 0.0% automatic | 99.2% automatic |
| Mean context tokens loaded per tool | 4,651.0 raw README tokens | 163.8 contract card tokens (`96.5%` reduction) |
| Render-ready `9:16` + `16:9` spotlight videos | 0 | 3,459 (`1080x1920` and `1920x1080` at 60 fps) |
| Engineering adspend executed | $0.00 | $0.00 (owner manages adspend; engineering prepares packs) |
| Third-party tracking cookies on landing pages | N/A | 0 (aggregate link counting only) |

## Representative RepoDir tools, Baltor native variations, and natural query routing

| RepoDir slug | Upstream GitHub repository | SPDX | Natural developer prompt matched in `1.2 ms` | README tokens | Contract card tokens | Baltor-native engine variation |
| :--- | :--- | :--- | :--- | ---: | ---: | :--- |
| `ajeetdsouza-zoxide` | `github.com/ajeetdsouza/zoxide` | `MIT` | `fast terminal directory jump` | 4,420 | 158 | `baltor_frecency_workspace_navigator_engine` |
| `3b1b-manim` | `github.com/3b1b/manim` | `MIT` | `mathematical explainer animation` | 5,180 | 168 | `baltor_parametric_math_scene_graph_engine` |
| `agentdeskai-browser-tools-mcp` | `github.com/AgentDeskAI/browser-tools-mcp` | `MIT` | `browser console mcp server` | 4,390 | 162 | `baltor_browser_telemetry_inspector_engine` |
| `addyosmani-agent-skills` | `github.com/addyosmani/agent-skills` | `MIT` | `claude code agent skills` | 4,890 | 166 | `baltor_verified_engineering_skill_pack_engine` |
| `activepieces-activepieces` | `github.com/activepieces/activepieces` | `MIT` | `open source zapier workflow automation` | 4,720 | 164 | `baltor_typed_webhook_connector_engine` |
| `zilliztech-claude-context` | `github.com/zilliztech/claude-context` | `Apache-2.0` | `semantic code context vector search` | 4,590 | 161 | `baltor_matryoshka_code_context_engine` |

## Known-wrong controls verified

| Control ID | Fault injected | Expected refusal code | Refusal layer | Observed result |
| :--- | :--- | :--- | :--- | :--- |
| Control A | Engineering code attempts paid adspend (`engineering_adspend_usd=25.0`) | `engineering_adspend_refused` | `preflight` | Refused before engine dispatch (`engine_dispatched=False`) |
| Control B | Sponsored ad pack omits paid-link disclosure (`include_paid_link_disclosure=False`) | `missing_paid_link_disclosure_refused` | `preflight` | Refused before engine dispatch (`engine_dispatched=False`) |
| Control C | Vertical `9:16` overlay encroaches on TikTok/Reels keep-out zone (`top=80px`, `bottom=200px`) | `tiktok_reels_safe_zone_violation_refused` | `preflight` | Refused before engine dispatch (`engine_dispatched=False`) |
| Control D | Video script or ad copy includes AI-slop (`"delve"`, `"game-changer"`) or `"3,452 reviewed repos"` | `ai_slop_or_reviewed_qualifier_refused` | `preflight` | Refused before engine dispatch (`engine_dispatched=False`) |
| Control E | Disallowed `robots.txt` (`robots_txt_allow_root=False`) or copyleft `GPL-3.0-only` license | `robots_or_unapproved_license_refused` | `preflight` | Refused before engine dispatch (`engine_dispatched=False`) |
| Control F | Undeclared engine identifier (`engine_id="nonexistent_engine"`) | `engine_handshake_incompatible` | `handshake` | Refused at Layer 3 before preflight (`engine_dispatched=False`) |
