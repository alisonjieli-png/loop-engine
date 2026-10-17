# Multi-surface startup federation and shared backend verification, October 16, 2026

Kind: verification record of the multi-surface startup federation and shared
backend dispatch engine suite, dated October 16, 2026. It keeps its bytes; later
work belongs in a new record.

The owner requested on October 16, 2026: "continue to aggressively push and
deploy everything needed for this to be a fully functioning startup with
multiple surface areas/websites all providing value and with some shared
backends, flexible easy to manage, modular, multi-layer wrapping with
handshakes and other things".

This record documents the verification and head-to-head benchmark of
[`tools/multi_surface_federation_engines.py`](../../tools/multi_surface_federation_engines.py)
and its test suite
[`tools/test_multi_surface_federation_engines.py`](../../tools/test_multi_surface_federation_engines.py).

## Outcome

All 22 startup surface areas across four surface families resolve through a
single 7-layer component envelope (`frustration_avoidance`, `carrier`,
`handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`) backed by
four swappable dispatch engines (`edge_manifest_federation_engine`,
`hybrid_stale_while_revalidate_engine`, `origin_scoped_gateway_engine`, and
`static_bundle_failover_engine`).

- **Topology alignment.** All 22 surfaces are registered with explicit
  capability and plane boundaries. The three canonical section subdomains
  (`deterministicskills.baltor.ai`, `tools.baltor.ai`, and
  `cornercases.baltor.ai`) match `src/loop_engine/core/service_runtime/web_site_map.json`
  (`service_web_site_map/v4`) on both `canonical_section` and `section_root`.
- **Cross-surface security isolation.** All eight adversarial cross-surface
  probes (session cookie attachment on a public brand host, staff tool
  invocation on a brand host, account state mutation on a Public Good host,
  external identity provider script in CSP on an AFK host, canonical section
  root mismatch, stale served release digest mismatch, missing staff grant on
  `systems.baltor.ai`, and missing `Strict-Transport-Security` or
  `Cache-Control: no-store` on `systems.baltor.ai`) were refused before any
  engine dispatch (`engine_dispatched: false`).
- **Zero-downtime cascade failover.** Under simulated multi-tier degradation
  (edge snapshot eviction, stale-while-revalidate cold cache with an open
  origin circuit breaker, and origin SQLite write lock saturation), all 22
  surfaces completed through the bounded 4-engine fallback chain using one
  shared `RecoveryAllowance` across nested envelope frames.

## Startup surface topology registry

The registry models 22 startup surface areas grouped into four families:

| Family | Surface hostname | Display name | Admitted shared backend planes | Public projection only | Canonical section and root |
| --- | --- | --- | --- | --- | --- |
| `commercial_core` | `baltor.ai` | Baltor | `catalogue_projection_plane/v1`, `feed_digest_plane/v1`, `identity_and_entitlement_plane/v1`, `telemetry_rollup_plane/v1`, `briefs_evidence_plane/v1`, `afk_approval_gate_plane/v1` | `false` | `false` (`/`) |
| `commercial_core` | `baltor.dev` | Baltor Developer Hub | `catalogue_projection_plane/v1`, `feed_digest_plane/v1`, `identity_and_entitlement_plane/v1`, `telemetry_rollup_plane/v1`, `briefs_evidence_plane/v1` | `false` | `false` (`/`) |
| `commercial_core` | `systems.baltor.ai` | Baltor Systems Staff View | `systems_view/v1`, `telemetry_rollup_plane/v1`, `catalogue_projection_plane/v1` | `false` (requires `staff_grant`) | `false` (`/`) |
| `standalone_product_brand` | `agentfeeds.si` | AgentFeeds | `feed_digest_plane/v1`, `catalogue_projection_plane/v1` | `true` | `false` (`/`) |
| `standalone_product_brand` | `agentfoundry.si` | AgentFoundry | `catalogue_projection_plane/v1`, `telemetry_rollup_plane/v1` | `true` | `false` (`/`) |
| `standalone_product_brand` | `agentstudios.si` | AgentStudios | `catalogue_projection_plane/v1`, `telemetry_rollup_plane/v1` | `true` | `false` (`/`) |
| `standalone_product_brand` | `agentafk.si` | AgentAFK | `afk_approval_gate_plane/v1`, `catalogue_projection_plane/v1` | `true` | `false` (`/`) |
| `standalone_product_brand` | `agentbriefs.si` | AgentBriefs | `briefs_evidence_plane/v1`, `catalogue_projection_plane/v1` | `true` | `false` (`/`) |
| `library_showcase_subdomain` | `deterministicskills.baltor.ai` | Deterministic Skills Showcase | `catalogue_projection_plane/v1`, `briefs_evidence_plane/v1` | `true` | `true` (`/deterministic-skills`) |
| `library_showcase_subdomain` | `tools.baltor.ai` | Harness Tools Showcase | `catalogue_projection_plane/v1`, `briefs_evidence_plane/v1` | `true` | `true` (`/tools`) |
| `library_showcase_subdomain` | `cornercases.baltor.ai` | Corner Cases Showcase | `catalogue_projection_plane/v1`, `briefs_evidence_plane/v1` | `true` | `true` (`/corner-cases`) |
| `library_showcase_subdomain` | `docs.baltor.ai` | Baltor Documentation Surface | `catalogue_projection_plane/v1`, `feed_digest_plane/v1` | `true` | `false` (`/docs`) |
| `library_showcase_subdomain` | `gallery.baltor.ai` | Baltor Creative Gallery Surface | `catalogue_projection_plane/v1`, `telemetry_rollup_plane/v1` | `true` | `false` (`/gallery`) |
| `public_good_and_open_protocol` | `skillsforgood.org` | Skills for Good | `catalogue_projection_plane/v1`, `briefs_evidence_plane/v1` | `true` | `false` (`/`) |
| `public_good_and_open_protocol` | `theloopengine.org` | The Loop Engine Foundation | `catalogue_projection_plane/v1`, `telemetry_rollup_plane/v1` | `true` | `false` (`/`) |
| `public_good_and_open_protocol` | `loopengine.io` | Loop Engine Ecosystem | `catalogue_projection_plane/v1`, `feed_digest_plane/v1` | `true` | `false` (`/`) |
| `public_good_and_open_protocol` | `loopengine.dev` | Loop Engine Developer Portal | `catalogue_projection_plane/v1`, `telemetry_rollup_plane/v1` | `true` | `false` (`/`) |
| `public_good_and_open_protocol` | `agenticengineering.org` | Agentic Engineering Standards | `briefs_evidence_plane/v1`, `catalogue_projection_plane/v1` | `true` | `false` (`/`) |
| `public_good_and_open_protocol` | `openknowledgeformat.org` | Open Knowledge Format | `catalogue_projection_plane/v1` | `true` | `false` (`/`) |
| `public_good_and_open_protocol` | `openintelligenceprotocol.org` | Open Intelligence Protocol | `catalogue_projection_plane/v1`, `feed_digest_plane/v1` | `true` | `false` (`/`) |
| `public_good_and_open_protocol` | `openpractitionerprotocol.org` | Open Practitioner Protocol | `catalogue_projection_plane/v1` | `true` | `false` (`/`) |
| `public_good_and_open_protocol` | `opensolutionprotocol.org` | Open Solution Protocol | `catalogue_projection_plane/v1`, `briefs_evidence_plane/v1` | `true` | `false` (`/`) |

## Seven-layer cross-surface envelope handshakes

Every cross-surface request traverses the seven envelope layers defined in
`src/loop_engine/core/engines/envelope.py`:

1. **`frustration_avoidance`**: wraps every refusal in an `envelope_refusal/v1`
   record with a plain-English sentence, next action, actor (`caller` or
   `operator`), retry rule, and effect commitment (`none`), and coordinates
   bounded automatic failover through `EnvelopeRecoveryPolicy` and
   `RecoveryAllowance`.
2. **`carrier`**: validates the `cross_surface_federation_request/v1` record,
   verifies that `surface_hostname` is admitted in `SURFACE_TOPOLOGY_REGISTRY`,
   and checks that `plane_schema` names a registered versioned shared backend
   plane.
3. **`handshake`**: computes an `envelope_handshake_verdict/v1` via
   `negotiate_handshake` and enforces cross-surface isolation on all public
   projection surfaces (`public_projection_only: true`), refusing session
   cookies, staff tool calls, account mutations, external identity provider
   CSP directives, and unadmitted planes before any inner layer runs.
4. **`account`**: verifies `staff_grant` on `systems.baltor.ai` and requires an
   explicit origin-bound `principal_id` on `identity_and_entitlement_plane/v1`.
5. **`tracking`**: records `envelope_journal_entry/v1` intent and outcome
   chains by request identity digest, answers idempotent replays from the first
   confirmed result (`answer_from_first_result`) without re-dispatching the
   engine, and evaluates release resync state (`in_sync` or `resync_now`) via
   `resync_decision`.
6. **`preflight`**: runs `EnvelopePreflightCheck` rules for canonical section
   root binding (`section_root_binding_mismatch`), served release digest parity
   (`served_release_digest_mismatch`, with bounded pure self-repair
   `resync_edge_release_digest_repair` when resync is authorized), staff
   surface `Strict-Transport-Security` and `Cache-Control: no-store` headers
   (`staff_surface_security_headers_missing`), and release projection signature
   verification (`unsigned_shared_projection_refused`).
7. **`nested_envelopes`**: enters each candidate engine slot through
   `enter_nested`, sharing the parent's `RecoveryAllowance` and depth bound
   (`maximum_depth: 4`) so cascade failover never multiplies retry budgets.

## Head-to-head engine benchmark

Each of the four swappable dispatch engines was evaluated across all 22 startup
surfaces:

| Engine ID | Role and mechanism | Requests | Succeeded | Success rate | Mean latency (ms) | P95 latency (ms) | Mean origin lock wait (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `edge_manifest_federation_engine` | Immutable R2/Edge signed manifest lookup (`O(1)`) | 22 | 22 | 1.0 | 0.42 | 0.42 | 0.0 |
| `hybrid_stale_while_revalidate_engine` | Immediate edge cache projection with async origin revalidation queue and circuit breaker | 22 | 22 | 1.0 | 1.15 | 1.15 | 0.0 |
| `origin_scoped_gateway_engine` | Direct origin SQLite plane router with per-surface rate budgets (4 concurrent writers) | 22 | 22 | 1.0 | 14.40 | 14.40 | 11.0 |
| `static_bundle_failover_engine` | Deterministic packaged fallback bundle when edge KV and origin are degraded | 22 | 22 | 1.0 | 0.29 | 0.29 | 0.0 |

### Cascade failover under simulated multi-tier degradation

When `edge_manifest_federation_engine` evicted `agentfeeds.si`,
`agentfoundry.si`, and `skillsforgood.org`, while
`hybrid_stale_while_revalidate_engine` had a cold cache and an open circuit
breaker (`origin_failures: 4 >= threshold: 3`) for `agentfoundry.si` and
`skillsforgood.org`, and `origin_scoped_gateway_engine` experienced write lock
saturation (`10 >= threshold: 8`), the cascade router completed 22 of 22
surfaces:

- 19 surfaces were served directly by `edge_manifest_federation_engine` in
  `0.42 ms`.
- 1 surface (`agentfeeds.si`) failed over to
  `hybrid_stale_while_revalidate_engine` in `1.33 ms` (`0.18 ms + 1.15 ms`).
- 2 surfaces (`agentfoundry.si` and `skillsforgood.org`) cascaded across all
  four engines to `static_bundle_failover_engine` in `32.82 ms`, consuming all
  3 shared automatic recovery attempts and reaching nested frame depth 4.

## Adversarial cross-surface security probes (known-wrong controls)

| Probe | Surface hostname | Expected refusal code | Actual refusal code | Refused by layer | Engine dispatched | Blocked before engine |
| --- | --- | --- | --- | --- | --- | --- |
| `cookie_leakage_on_public_brand` | `agentfeeds.si` | `cross_surface_session_cookie_forbidden` | `cross_surface_session_cookie_forbidden` | `handshake` | `false` | `true` |
| `staff_tool_on_public_brand` | `agentstudios.si` | `cross_surface_staff_tool_forbidden` | `cross_surface_staff_tool_forbidden` | `handshake` | `false` | `true` |
| `account_mutation_on_public_good` | `skillsforgood.org` | `cross_surface_account_mutation_forbidden` | `cross_surface_account_mutation_forbidden` | `handshake` | `false` | `true` |
| `external_idp_csp_on_afk_surface` | `agentafk.si` | `cross_surface_external_idp_csp_forbidden` | `cross_surface_external_idp_csp_forbidden` | `handshake` | `false` | `true` |
| `section_root_mismatch_on_showcase` | `deterministicskills.baltor.ai` | `section_root_binding_mismatch` | `section_root_binding_mismatch` | `preflight` | `false` | `true` |
| `stale_release_digest_on_canonical_section` | `tools.baltor.ai` | `served_release_digest_mismatch` | `served_release_digest_mismatch` | `preflight` | `false` | `true` |
| `missing_staff_grant_on_systems_surface` | `systems.baltor.ai` | `staff_grant_required` | `staff_grant_required` | `account` | `false` | `true` |
| `missing_zero_cache_or_hsts_on_systems_surface` | `systems.baltor.ai` | `staff_surface_security_headers_missing` | `staff_surface_security_headers_missing` | `preflight` | `false` | `true` |

## Limits

This verification suite runs deterministically in memory against the repository
site map, brand profile declarations, and 7-layer envelope contracts. It does
not perform live DNS, Cloudflare Worker, or Fly.io origin network calls.
