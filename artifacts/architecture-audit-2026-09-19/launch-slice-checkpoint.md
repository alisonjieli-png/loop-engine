# Local website and decision-engine checkpoint

Date: September 19, 2026. Working-tree implementation, not a hosted release.
No live model calls, payment operations, cloud resources or domain changes
were authorized or performed. Changes remain uncommitted.

## Implemented paths

| Boundary | Current behavior | Important limit |
|---|---|---|
| Python service website | Packaged same-origin workspace, setup and explanation pages; scoped connection, search, digest-verified download, usage and billing-session routes | No automated signup or real provider qualification |
| Typed decisions | Immutable request and result contracts, strict admission, optional Jev adapter, existing gateway and model session, direct and local protocol-tool entry points | No automatic Practitioner selection, live Jev result, or measured decision quality |
| Solution execution | The existing model invocation port can request typed decisions under its owning Loop | Model confidence never grants authority or accepts the task |
| Retrieval | Explicit host-supplied backend bindings, existing handshakes, effect checks, exact embedding spaces and configurable ranking policy | External named engines are not installed by this extension |
| Assignment preparation | Reasoning and building purposes retain different initial choices; explicit workspace and command settings can refine either within owning authority | Preparation and offered metadata do not establish native resource loading |
| Metadata disclosure | Grant revision captured before ranking and checked again with current principal at completion | Cannot recall bytes already sent; hosted behavior remains unqualified |
| Owner setup | Launch runbook, separate key locations, version-specific client examples and a runnable local service example | Hosted storage, self-service onboarding and live accounts remain work |

Decision implementation now lives under `core/decisions`, with imports checked
against the existing dependency direction. Website assets belong to
`core/service_runtime/web_assets`. These are internal mechanics, not new Loop
runtime classes or public capability groups. The larger flat `core` still has
organization debt; passing conformance is not proof that every abstraction is
ideal or every configuration is complete.

## Verification

- `verification-launch-attempt-3.json`: 5,852 of 5,852 executed offline checks
  passed; 15 optional checks were not tested. The frozen export did not change
  during the run and its package identity matches the current working source.
- Source identity:
  `fae8fad7f713b7611b41c345ff5f6e6e5bc35a14dacf880f044d509150b225b6`.
- `launch-slice-verification-3.json`: 204 checks passed; five removed-guard
  controls were detected. These include decision admission, model authority,
  cumulative calls, retrieval authority and metadata completion authorization.
- `service-workspace-browser-3.json`: 28 browser checks passed against real
  local HTTP and durable service records. Stripe was an injected provider
  fixture; no browser request reached an external provider. Desktop and narrow
  viewport screenshots were inspected.
- Conformance passed all declared gates. The local service example passed
  four checks, including exact body digest and revocation across restart.
- The architecture, continuation and decision import-boundary tool tests
  passed 29 checks. Documentation structure passed over 388 Markdown files.

These checks are not a full-system benchmark, a security certification, a real
phone performance test, or evidence that a native harness benefited from the
downloaded intelligence.

## Failed attempts retained

The first full capture passed 5,846 of 5,848 checks. It exposed an outdated
packaged architecture projection and missing runtime folders in the export.
The projection and export were corrected rather than weakening those checks.

The second capture passed 5,847 of 5,850. Two expectations omitted explicitly
authorized process spawning from the assignment record. One read-only host
guard had become too permissive. The guard was restored, its refusal fixture
made explicitly mutating, and public tests added for reasoning experiments and
read-only building work. All eleven public provisioning checks now pass.

The first focused mutation run detected four of five controls. The missed
control patched an unused imported function reference, not the reference the
checks called. The control was corrected; the failed report remains available.
A continuation freshness check also correctly failed after the plan changed
and before its generated view was refreshed. It passed after regeneration.

## Circuit review

The [pinned-source review](../../docs/research/CIRCUIT-DECISION-ENGINE-REVIEW-2026-09-19.md)
recommends a separately configured trial, not an installed provider or a new
default. Upstream authentication, fake-scorer defaults, context truncation,
model identity, accounting and calibration require explicit qualification.
No weights were downloaded or run.

## Remaining release work

Cloud object delivery and shared database deployment, automated identity and
customer bootstrap, actual client authorization, native harness materialization
and observed use, periodic billing reconciliation, deployment recovery, real
test-mode payments and approved provider trials remain open. The service is
not ready for a paid public-launch claim. Use the
[owner runbook](../../docs/guides/launch-setup-runbook.md) for manual setup and
the generated worklist for engineering work.
