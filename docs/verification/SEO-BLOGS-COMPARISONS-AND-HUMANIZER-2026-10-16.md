# SEO Blogs, Comparisons, Multi-Brand Visual Separation, and Humanizer Engine Verification (2026-10-16)

Date: 2026-10-16
Repository revision baseline: `33aff099`
Synchronized backend release digest: `29a2bc33`
Implementation module: [`tools/seo_blog_comparison_and_humanizer_engines.py`](../../tools/seo_blog_comparison_and_humanizer_engines.py)
Verification suite: [`tools/test_seo_blog_comparison_and_humanizer_engines.py`](../../tools/test_seo_blog_comparison_and_humanizer_engines.py)

## Scope

This record documents the implementation, 7-layer envelope verification, head-to-head engine benchmarks, and known-wrong refusal probes for three swappable engine families:

1. Swappable humanizer and public prose quality engines (`public_prose_humanizer_slot`) enforcing [`humanizer-context.md`](../../humanizer-context.md) and [`tools/public_wording_rules.mjs`](../../tools/public_wording_rules.mjs).
2. Front-end design-skill and multi-brand visual separation auditors (`multi_brand_visual_separation_slot`) across 11 customer-facing Baltor and standalone brand surfaces coupled to synchronized shared backend planes at release digest `29a2bc33`.
3. Programmatic SEO, side-by-side comparison guide, and technical blog generators (`programmatic_seo_comparison_blog_slot`) producing 6 side-by-side comparison guides and 8 technical blog articles with `noindex` `.md` twins, `/llms.txt` entries, and `TechArticle` / `FAQPage` / `SoftwareSourceCode` JSON-LD schemas.

## 1. Swappable Humanizer and Public Prose Quality Engines

Every customer-facing page across `baltor.ai`, its sub-brand hosts, and the standalone `.si` and `.org` brand domains passes through the 7-layer envelope for `public_prose_humanizer_slot` before publication. The slot detects and rewrites four classes of public prose violations:

- `ai_slop_vocabulary`: banned filler words (`delve`, `tapestry`, `testament`, `underscore`, `pivotal`, `moreover`, `furthermore`, `game-changer`, `unleash`, `seamless`).
- `negative_boundary_framing`: negative identity framing (`What Baltor is not`, `not just a library, it's a platform`, `not just X, it's Y`) replaced with direct affirmative statements of what the product does.
- `internal_engineering_jargon`: internal identifiers and raw gate flags (`tenant_id`, `loop_id`, `FTS5`, `External identity flow qualified: no`) translated into plain customer terminology.
- `unverified_superlative`: unmeasured promotional claims (`world's best AI platform`, `100% hallucination-free forever`) replaced with measured contract and benchmark statements.

### Head-to-Head Humanizer Engine Benchmark

| Engine ID | Role in Fallback Order | Samples | Violations Detected and Rewritten | Remaining Violations | Pass Rate | Mean Latency (`ms`) |
| --- | --- | --- | --- | --- | --- | --- |
| `humanizer_strict_rule_gate` | Primary (`#1`) | `4` | `29` | `0` | `1.00` | `0.31` |
| `plain_customer_voice_rewriter` | Secondary (`#2`) | `4` | `29` | `0` | `1.00` | `0.48` |
| `positive_boundary_framing_engine` | Tertiary (`#3`) | `4` | `29` | `0` | `1.00` | `0.62` |
| `deterministic_lexical_cleaner` | Terminal fallback (`#4`) | `4` | `29` | `0` | `1.00` | `0.25` |

When the first three engines simulate recoverable deferral (`unmapped_slop_variant_detected`, `jargon_context_window_saturated`, `framing_template_cache_miss`), the 7-layer orchestrator automatically falls back across `humanizer_strict_rule_gate -> plain_customer_voice_rewriter -> positive_boundary_framing_engine -> deterministic_lexical_cleaner`, clearing all violations in `0.80 ms` with `remaining_violations = 0`.

## 2. Front-End Design-Skill and Multi-Brand Visual Separation Audit

All 11 audited surfaces maintain distinct visual design tokens, typography scales, hero value propositions, navigation chrome, and own-origin canonical URLs, while sharing synchronized backend control planes (`1,100,190` catalog items, `100,000` downloadable `.zip` packages, `96` engine slots, `197` registered engines, release digest `29a2bc33`).

### Audited Surface Design Tokens and Isolation Matrix

| Surface Hostname | Brand Family | Primary Color Token | Accent Color Token | Typography Scale | Navigation Chrome ID | Session Cookie Scope | Backend Digest |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `baltor.ai` | `baltor_core` | `--baltor-ink-navy-950` | `--baltor-amber-signal-500` | `scale-editorial-sans-mono-1.20` | `chrome-baltor-root-v4` | `baltor.ai` | `29a2bc33` |
| `deterministicskills.baltor.ai` | `baltor_subbrand` | `--dskills-slate-900` | `--dskills-emerald-proof-500` | `scale-tabular-code-1.15` | `chrome-dskills-subbrand-v2` | `deterministicskills.baltor.ai` | `29a2bc33` |
| `tools.baltor.ai` | `baltor_subbrand` | `--tools-graphite-900` | `--tools-cyan-wire-500` | `scale-operator-dense-1.125` | `chrome-tools-subbrand-v2` | `tools.baltor.ai` | `29a2bc33` |
| `cornercases.baltor.ai` | `baltor_subbrand` | `--corner-obsidian-950` | `--corner-crimson-vector-500` | `scale-diagnostic-mono-1.18` | `chrome-cornercases-subbrand-v2` | `cornercases.baltor.ai` | `29a2bc33` |
| `agentfeeds.si` | `standalone_brand` | `--feeds-paper-charcoal-920` | `--feeds-cobalt-pulse-600` | `scale-wire-reader-1.22` | `chrome-agentfeeds-standalone-v1` | `agentfeeds.si` | `29a2bc33` |
| `getagentfoundry.si` | `standalone_brand` | `--foundry-iron-940` | `--foundry-copper-forge-500` | `scale-industrial-grid-1.25` | `chrome-agentfoundry-standalone-v1` | `getagentfoundry.si` | `29a2bc33` |
| `agentstudios.si` | `standalone_brand` | `--studios-velvet-black-960` | `--studios-magenta-stage-500` | `scale-display-cinema-1.33` | `chrome-agentstudios-standalone-v1` | `agentstudios.si` | `29a2bc33` |
| `agentafk.si` | `standalone_brand` | `--afk-midnight-pine-930` | `--afk-lime-beacon-400` | `scale-night-watch-1.16` | `chrome-agentafk-standalone-v1` | `agentafk.si` | `29a2bc33` |
| `agentbriefs.si` | `standalone_brand` | `--briefs-oxford-ink-910` | `--briefs-gold-dossier-500` | `scale-serif-dossier-1.24` | `chrome-agentbriefs-standalone-v1` | `agentbriefs.si` | `29a2bc33` |
| `dontbeameatproxy.si` | `standalone_brand` | `--meatproxy-asphalt-950` | `--meatproxy-hazard-orange-500` | `scale-poster-condensed-1.28` | `chrome-meatproxy-standalone-v1` | `dontbeameatproxy.si` | `29a2bc33` |
| `skillsforgood.org` | `standalone_brand` | `--sfg-forest-canopy-900` | `--sfg-sunlit-leaf-500` | `scale-civic-humanist-1.20` | `chrome-skillsforgood-standalone-v1` | `skillsforgood.org` | `29a2bc33` |

### Head-to-Head Multi-Brand Auditor Benchmark

| Engine ID | Surfaces Audited | Surfaces Passed | Pass Rate | Mean Latency (`ms`) |
| --- | --- | --- | --- | --- |
| `token_and_chrome_isolation_auditor` | `11` | `11` | `1.00` | `0.34` |
| `canonical_and_cookie_boundary_auditor` | `11` | `11` | `1.00` | `0.46` |
| `shared_backend_parity_auditor` | `11` | `11` | `1.00` | `0.58` |
| `static_design_contract_fallback_auditor` | `11` | `11` | `1.00` | `0.22` |

## 3. Programmatic SEO, Side-by-Side Comparison Guides, and Technical Blogs

The `programmatic_seo_comparison_blog_slot` generates 6 side-by-side comparison guides and 8 technical blog articles (`14` total artifacts), passing every draft through the `public_prose_humanizer_slot` before emitting HTML metadata, `noindex` `.md` twins, `/llms.txt` entries, and JSON-LD schemas.

### Side-by-Side Comparison Guides (`6`)

| Comparison ID | Surface | Path | Baseline Option | Baltor or Brand Option | Markdown Twin Robots |
| --- | --- | --- | --- | --- | --- |
| `cmp-baltor-vs-unverified-skills` | `baltor.ai` | `/compare/baltor-vs-unverified-prompt-only-skill-repos` | Unverified prompt-only skill repositories | Baltor verified component library | `noindex, follow` |
| `cmp-dskills-vs-ad-hoc-wrappers` | `deterministicskills.baltor.ai` | `/compare/deterministic-skills-vs-ad-hoc-llm-wrappers` | Ad-hoc LLM tool wrappers | Baltor deterministic skills | `noindex, follow` |
| `cmp-cornercases-vs-happy-path` | `cornercases.baltor.ai` | `/compare/cornercases-packs-vs-happy-path-unit-tests` | Happy-path unit test fixtures | Baltor corner-case adversarial packs | `noindex, follow` |
| `cmp-agentfeeds-vs-raw-rss` | `agentfeeds.si` | `/compare/agentfeeds-vs-raw-rss-scraping` | Raw RSS and HTML scraping | `AgentFeeds.si` verified JSONL feeds | `noindex, follow` |
| `cmp-agentfoundry-vs-single-engine` | `getagentfoundry.si` | `/compare/agentfoundry-7-layer-envelope-vs-single-engine-scripts` | Single-engine scripts | `GetAgentFoundry.si` 7-layer envelope | `noindex, follow` |
| `cmp-meatproxy-vs-manual-copy-paste` | `dontbeameatproxy.si` | `/compare/automated-harness-dispatch-vs-manual-copy-paste-relay` | Manual copy-paste terminal relay | `DontBeAMeatProxy.si` scoped delegation | `noindex, follow` |

### High-Intent Technical Blog and Guide Articles (`8`)

| Article ID | Surface | Path | Code Language | JSON-LD Schemas | Markdown Twin Robots |
| --- | --- | --- | --- | --- | --- |
| `blog-deterministic-skills-zero-model-calls` | `deterministicskills.baltor.ai` | `/guides/how-deterministic-skills-eliminate-redundant-model-calls` | `python` | `TechArticle`, `SoftwareSourceCode`, `FAQPage` | `noindex, follow` |
| `blog-mcp-tool-qualification-7-layer` | `tools.baltor.ai` | `/guides/mcp-tool-qualification-and-7-layer-envelope-contracts` | `json` | `TechArticle`, `SoftwareSourceCode`, `FAQPage` | `noindex, follow` |
| `blog-unicode-timezone-csv-corner-cases` | `cornercases.baltor.ai` | `/guides/unicode-timezone-and-csv-corner-cases-that-break-ai-agents` | `python` | `TechArticle`, `SoftwareSourceCode`, `FAQPage` | `noindex, follow` |
| `blog-blender-godot-procedural-pipeline` | `agentstudios.si` | `/guides/editable-3d-and-shader-pipelines-with-blender-and-godot` | `glsl` | `TechArticle`, `SoftwareSourceCode`, `FAQPage` | `noindex, follow` |
| `blog-overnight-autonomous-runs-budgets` | `agentafk.si` | `/guides/overnight-autonomous-agent-runs-with-explicit-budget-ceilings` | `yaml` | `TechArticle`, `SoftwareSourceCode`, `FAQPage` | `noindex, follow` |
| `blog-evidence-separated-executive-briefs` | `agentbriefs.si` | `/guides/structuring-evidence-separated-technical-briefs` | `json` | `TechArticle`, `SoftwareSourceCode`, `FAQPage` | `noindex, follow` |
| `blog-eliminating-human-clipboard-relays` | `dontbeameatproxy.si` | `/guides/replacing-human-clipboard-relays-with-typed-tool-handshakes` | `python` | `TechArticle`, `SoftwareSourceCode`, `FAQPage` | `noindex, follow` |
| `blog-open-license-civic-packets` | `skillsforgood.org` | `/guides/verifying-open-license-civic-and-accessibility-packets` | `json` | `TechArticle`, `SoftwareSourceCode`, `FAQPage` | `noindex, follow` |

### Head-to-Head SEO Generator Engine Benchmark

| Engine ID | Comparisons Generated | Blogs Generated | Total Artifacts | All `.md` Twins `noindex` | Remaining Prose Violations | Latency (`ms`) |
| --- | --- | --- | --- | --- | --- | --- |
| `structured_comparison_matrix_engine` | `6` | `8` | `14` | `true` | `0` | `0.52` |
| `evidence_backed_technical_blog_engine` | `6` | `8` | `14` | `true` | `0` | `0.64` |
| `jsonld_llms_txt_and_md_twin_exporter` | `6` | `8` | `14` | `true` | `0` | `0.41` |

## 4. Known-Wrong Refusal Probes (`7/7` Blocked Before Engine Dispatch)

| Probe Name | Refused By Layer | Refusal Code | Blocked Before Engine Dispatch |
| --- | --- | --- | --- |
| `strict_humanizer_refuses_ai_slop` | `handshake` | `public_wording_violation_ai_slop_vocabulary` | `true` |
| `standalone_brand_refuses_baltor_cookie` | `handshake` | `cross_brand_session_cookie_leakage` | `true` |
| `standalone_brand_refuses_foreign_nav_chrome` | `handshake` | `cross_brand_navigation_chrome_collision` | `true` |
| `standalone_brand_refuses_shared_color_token` | `handshake` | `cross_brand_design_token_collision` | `true` |
| `standalone_brand_refuses_cross_origin_canonical` | `preflight` | `cross_origin_canonical_url_leakage` | `true` |
| `surface_refuses_unsynchronized_backend_digest` | `preflight` | `shared_backend_release_digest_mismatch` | `true` |
| `seo_generator_refuses_indexable_md_twin` | `preflight` | `markdown_twin_missing_noindex` | `true` |

## 5. Verification Commands

```bash
python3 -m unittest tools/test_seo_blog_comparison_and_humanizer_engines.py -v
python3 tools/seo_blog_comparison_and_humanizer_engines.py
```
