# Claude Code Fable 5.1 handoff

Kind: human-authored development handoff. Recheck its snapshot before acting.
It is not an execution contract, a generated session packet or new authority.

The primary owner document is the
[single development HTML](../../artifacts/architecture-audit-2026-09-19/loop-engine-system-map.html).
It embeds this handoff, the checkpoint, setup instructions, architecture,
feature comparisons and worklist. Do not make another competing dashboard.

## Start from the actual state

The private pilot is live at <https://baltor.ai/>, <https://app.baltor.ai/> and
<https://baltor-pilot.fly.dev/>. Public email
registration, paid subscriptions and complete native task execution are not
qualified. The account integration code and plain-language website are
deployed in Fly release 7. Public account registration remains disabled.

The repository is `/home/username/loop-engine`, branch `main`, base revision
`48cc954322691e492aad69a465ba470a112730e7`. There is substantial modified and
untracked work. This handoff does not commit, push or publish any of it.
Preserve changes whose ownership is unresolved. Never reset the tree to make
the handoff easier to apply. Keep work in this repository, not `/root`.

Read `AGENTS.md`, `ASTRA.md`, the
[checkpoint](DEVELOPMENT-CHECKPOINT-2026-09-20.md), the
[continuation plan](../roadmap/CONTINUATION-AND-LAUNCH.md), and the relevant
component guide before changing behavior. The machine-readable work authority
is `docs/roadmap/roadmap.yaml`. Its sixteen delivery packages expand existing
steps into 128 actions and eighty verification cases. Each package names
existing code owners, acceptance dependencies and a rollback procedure.
Each case distinguishes its required evidence level and a negative control.
These are planned obligations, not recorded passes or a second task-state store.

The [credential handoff](../guides/developer-credential-handoff.md) is ready.
Claude Code's six project-local Baltor connections include authorized
Namecheap access and the new Cloudflare write grant. Thirteen
named API and authorization references remain in the system keyring; no raw
secrets are embedded here. Namecheap retains its credential in Claude Code's
native authorization store. The private configuration supports
`--strict-mcp-config` to avoid unrelated or older account connections.

## First working session

1. Inspect revision, dirty paths, active processes and concurrent writers.
   Confirm the deployed image and service capabilities through read-only
   checks. Do not redeploy merely because the health endpoint responds.
2. Retain the reviewed exact registrations for `browser_identity.py` and
   `browser_identity_checks.py`. Conformance now passes. Preserve their
   fixed destinations, permission checks, secret handling and local-only
   test boundaries; do not replace them with a broad exception.
3. Review the deployed account code before enabling it. Check user information
   against the signed subject; refuse editable tenant metadata and generic
   browser tokens at the protocol endpoint. Test outage classification,
   token expiry, logout, repeated activation and account disablement.
4. Retain the verified registrar delegation and complete Resend sender checks.
   Cloudflare records and Namecheap nameservers have been changed. Do not
   repeat those writes blindly. Request only the missing Supabase
   authentication-settings permission through an approved connection.
   The owner does not want routine dashboard configuration delegated back.
5. Complete one real account and test-payment journey. Keep the existing
   pilot available while qualifying the replacement. Record real provider
   evidence separately from injected fixtures.

Useful local commands, after confirming their source and dependencies:

```bash
git status --short --branch
git rev-parse HEAD
git worktree list --porcelain
PYTHONPATH=src .venv/bin/python -m loop_engine service smoke
PYTHONPATH=src .venv/bin/python -m loop_engine --conformance
PYTHONPATH=src:tools .venv/bin/python -m unittest tools.test_build_continuation_status tools.test_architecture_audit
```

The current package report passes 5,938 checks with 15 optional checks
untested. Earlier conformance failures remain in their original reports.
Recheck source identities before applying any saved result to further edits.

## Existing owners and unfinished integration

| Work | Owning paths | Immediate review or build |
|---|---|---|
| Browser identity | `core/service_runtime/browser_identity.py`, `http_auth.py`, `http.py`, `http_entrypoint.py` | Real provider qualification, recovery, transient failures, bounded registration and session handling. Exact network registration is complete. |
| Customer state | `core/service_runtime/runtime.py`, `records.py`, `access.py` | Atomic subject-to-tenant activation, revocation, no reinstatement on repeated sign-in, self-service client credentials without administrator authority. |
| Billing | `core/service_runtime/billing.py`, `stripe_provider.py`, `stripe_sessions.py` | Server-owned customer creation, approved sandbox binding, test checkout, webhook registration and reconciliation. |
| Records and files | `catalog/protocol.py`, `catalog/stores/`, `core/service_runtime/provisioning.py` | Qualified PostgreSQL and private-storage adapters, exact references, migration and restore. Current deployment still uses SQLite. |
| Search and context | `core/retrieval.py`, `retrieval_backends.py`, `intelligence_layers.py` | One versioned semantic profile, authorized filtering, measured relevance, feature compatibility and index rebuilds. |
| Selected files and execution | `core/node_provisioning.py`, `instance_instructions.py`, `harness_process.py`, `harness_semantic.py` | Actual download and native loading, dependency placement, isolated workspaces and independent task checks. |
| Long-running work | `core/local_resources.py`, `instance_hibernation.py`, `credential_leases.py`, `loop/delegation_runtime.py` | Resource reservations, shared credential use, cancellation, restart and unknown-effect reconciliation. |
| Public pages | `core/service_runtime/web_assets/` | Keep plain-language explanations and accurate pilot limits; finish real account and client journeys. |
| Main development document | `tools/architecture_report/`, `architecture_report_data.py`, `architecture_audit.py` | Generate from the roadmap and source. Do not hand-edit the generated HTML. |

All source paths in the table are relative to `src/loop_engine/` unless they
start with `tools/`. The table locates responsibility; it does not assert that
every listed behavior is implemented.

## Provider access: prepared versus unfinished

| Service | Observed preparation | Remaining work |
|---|---|---|
| Fly | Release 7 on the existing `baltor-pilot` Machine in `iad`; resources unchanged. Root, www and app hostnames each pass 45 hosted website checks with valid certificates. | Complete recovery and the full customer journey. No horizontal replicas while SQLite is authoritative. |
| Supabase | Project `qfzxmjznlwiopgvfgtsw`; database, storage and key access prepared. Public authentication settings respond with email confirmation enabled. | Private bucket, shared-store adapter, real customer identity and sender setup. Management authentication-settings access returned forbidden. |
| Stripe | Newly approved `Baltor sandbox`, account `acct_1UHZ9KCCxLfArYED`; runtime test credential successfully reads that account. | Test product, Price, customer lifecycle, portal, webhook and real reconciliation. Do not use the older operator account or temporary sandbox. |
| Resend | `auth.baltor.ai` exists, tracking is disabled, exact sender records are in Cloudflare and verification has started. | Confirm verified status, configure `accounts@auth.baltor.ai` in Supabase, then test confirmation and recovery. No email has been sent by this setup. |
| Cloudflare | New write authorization works. Zone `574082e7cc7798981b82b317a8dceb38` is active on the Free plan with 14 website, certificate and sender records. | Website records remain DNS-only. Do not enable a proxy or change transport security without testing. |
| Namecheap | Registrar and registry checks confirm `dana.ns.cloudflare.com` and `nile.ns.cloudflare.com`. The owner confirms no existing email or forwarding. | Some recursive resolvers still cache old answers. No manual nameserver task remains for the owner; preserve the prior configuration for a reviewed rollback. |

The owner reports setting the Supabase Site URL to
`https://baltor-pilot.fly.dev` and the redirect to
`https://baltor-pilot.fly.dev/auth/callback`. These are owner-confirmed, not
independently read back. Do not ask for the same manual change again.

The [setup runbook](../guides/launch-setup-runbook.md) records non-secret
credential references. Values belong in the system keyring or deployment
secret manager, never here. An operator authorization is not automatically
a durable application credential. A denied operation needs the right grant,
not a different route around the refusal.

## Constraints that stay in force

The recorded pilot allowance is 50 United States dollars monthly for
infrastructure and up to 10 dollars for setup. Model-call authority remains
zero. Live customer charging remains disabled. Local models still require
explicit model-call, time, resource and data authority for qualification.
Do not infer approval to run them because there is no per-token invoice.

Customers or their providers operate model endpoints. Loop Engine connects
to supported endpoints and credential references; it need not install or
manage model servers. Local execution does not mean local inference. A task
using a remote model must disclose which information can leave the machine.

The canonical architecture is unchanged: one `Loop` runtime, three roles,
separate mode and relationship fields, four persistent intelligence layers,
and temporary Runtime Memory. Use the full classification and behavioral
explanation in the [continuation plan](../roadmap/CONTINUATION-AND-LAUNCH.md).
Do not add another runtime, scheduler, credential store or catalogue authority.

Read the complete configuration dimensions, flexible composition and layered
harness documents before changing selection or recovery. Preserve explicit
initial choices, ordered authorized fallbacks and unavailable states. More
context, a stronger model or an extra review step can be the correct choice.
The objective is accepted work under the user's constraints, not the fewest
tokens regardless of quality.

One governed step does not imply a fresh container. Separate logical task
identity, harness process, sandbox, dependency image and inference service.
Compare supported process and isolation choices before selecting a default.
Never share writable private state across customers to reduce overhead.

## Public language and launch claims

The public brand is Baltor. On the homepage and How it works, use task, step,
tools, model, information, checks and reusable results. Avoid Loop, Loop node,
Loop Engine, runtime classification and role profiles there. Technical
documentation and GitHub retain exact architecture names and identifiers.
Do not rename packages or contracts to satisfy a copy change.

The deployed How it works page leads with "Big problems. Clear steps." It
keeps the interactive import example and moves the complete runtime
explanation into technical documentation.
The existing `/docs` route remains the technical entry point; no documentation
subdomain is claimed to exist.

Three launch-message drafts are in the main HTML and
[benefit guide](../guides/launch-benefits-and-evidence.md): overnight work with
local models, fewer tokens spent on repetition, and useful expertise for
each step. None is a new measured performance claim. Preserve the evidence
requirements before publishing stronger language such as "significant"
savings, "always" right context or guaranteed completion by morning.

## Verification and handoff discipline

The deployed package report passes 5,938 executed checks with 15 optional
checks untested: `verification-deployment-account-code-1.json`.
Its source digest is
`65010363f3092095404e9c7f1b14677c95c11fbb288f2d3e09a1e690e2918d2e`.
The running platform image digest is
`sha256:7b45d327faba2e65829230e8ee4f91109207183b4575cdab08c545aae6af55e8`.
Reports apply to those bytes, not later unrelated changes.

The subsequent plain-language website report passes 120 local browser
checks: `plain-language-handoff-browser-2.json` in the architecture artifact
folder. Attempt one caught the technical reference on the wrong page and is
retained. Local HTTP and durable-runtime checks pass 104 and 31 respectively;
they do not exercise real provider signup or billing. The current deployment
passes conformance, 284 focused launch checks, 120 local browser checks,
45 hosted website checks, 16 hosted service checks and 12 administrator
checks. The app hostname passes 45 browser checks after the nameserver change.
`handoff-focused-checks-1.json` records those component results with an
unchanged package identity and preserves the failing conformance output.

Run focused checks during changes. Freeze the source before the full suite,
clean install, examples, browser, container and live qualification. Use a new
report filename; do not overwrite an earlier failed attempt. Prove each new
guard rejects a known-wrong case. A fixture is not a real provider result.

After updating the authoritative roadmap and documentation:

```bash
PYTHONPATH=src:tools .venv/bin/python tools/build_continuation_status.py
PYTHONPATH=src:tools .venv/bin/python tools/build_continuation_status.py --check
PYTHONPATH=src:tools .venv/bin/python tools/build_records_index.py
PYTHONPATH=src:tools .venv/bin/python tools/architecture_audit.py
```

Use `tools/check_architecture_report.mjs` with a new report path for the main
document. Use `tools/check_service_workspace.mjs` for local website checks.
The browser runners write diagnostic reports and screenshots; they are not
deployment commands. Follow the current continuous-integration workflow for
full release verification. Do not publish the dirty tree through the disabled
GitHub workflow.

## Suggested first instruction to the next developer

> Continue from this handoff and the current checkpoint. Verify the checkout
> and live state first. Preserve the repaired identity boundaries and complete
> the earliest safe work in the
> sixteen delivery packages. Reuse existing provider access and ask only for
> missing permission or a decision engineering cannot make. Keep all evidence,
> failures and plans in the single generated development HTML. Do not make
> model calls, enable live payments, commit, push or deploy from this note
> alone. Report a completed customer-visible path and its remaining limits
> after each reviewed batch.
