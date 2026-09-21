# Owner actions for the first release

Kind: operating guide. Provider documentation checked: September 19, 2026.
These actions support the [continuation plan](../roadmap/CONTINUATION-AND-LAUNCH.md).
They do not mean that the hosted integrations are qualified or that a public
launch is ready.

The current Baltor pilot already has Fly, Supabase, Stripe and Resend accounts.
Do not repeat account creation. The main HTML's owner cards distinguish
prepared accounts, engineering-owned setup and missing consent.

| Current preparation | What remains |
|---|---|
| Fly pilot running in `iad` under the recorded allowance. The [current deployment](../architecture/MVP-CLIENT-SERVER.md#current-deployment) section names the running release. | Engineering completes customer integration and recovery qualification. |
| Supabase project, database, storage and key access prepared | Exact authentication-settings management permission, real customer integration and private storage checks. |
| Baltor sandbox runtime test credential verified | Engineering prepares and tests products, checkout, portal, webhooks and reconciliation. |
| Resend sender created and verification started | Engineering confirms verification, configures mail and tests controlled recipients. |
| Cloudflare write access and Namecheap authorization verified | The Free zone is active and nameservers are switched. Engineering verifies remaining mail and account integration; no manual domain setup remains. |

The owner still approves genuinely private access, controlled test recipients,
model-test authority, support and privacy choices, public prices and a later
paid-release decision. Engineering must request missing permission through
authorization or a protected reference and perform routine configuration.
Live payments and unapproved model calls remain disabled.

Start with the [step-by-step setup runbook](launch-setup-runbook.md) for the
recommended initial hosting shape, secret locations, local commands and
client configuration. This checklist retains the owner approvals and release gates.

## Reference checklist for a fresh installation

The following detailed checklist also serves new installations. For this
existing pilot, use the preparation table above and the main HTML's current
owner cards instead of repeating the account and resource creation steps.

### 1. Choose how to supply secrets

- [ ] Use your existing password manager, secret manager, or protected
  deployment settings. Enable multi-factor authentication on owner accounts
  and keep account-recovery material private.
- [ ] Keep development credentials separate from production credentials.
- [ ] Share the manager name and entry names, not secret values. For example,
  an entry called `loop-engine/development/stripe` identifies where a secret
  is held; it is not the secret itself or a required configuration name.
- [ ] State how the authorized service will receive each secret. Naming an
  entry does not give this development environment access to it.

Never paste secret keys, passwords, connection strings containing passwords,
session tokens, or webhook signing secrets into chat or repository files.
Engineering will document the exact deployment variable names once their
configuration contract is ready. Do not create broad administrator tokens
just to complete this checklist.

### 2. Prepare identity and private storage

- [ ] Create or select a Supabase organization you control. Create an isolated
  development project, such as `loop-engine-dev`, with no real customer data.
  Select the region where you want development data stored. Review any charge
  shown before confirming project creation.
- [ ] Save the generated database password in your secret manager. Return the
  project reference, project URL, and region, which do not contain that password.
- [ ] Identify the project's publishable key in its configuration. Keep any
  privileged server key separate. Supply a privileged key only when an
  approved server operation needs it; token verification alone does not need
  an administrative key. Supabase distinguishes browser-safe publishable keys
  from secret keys that bypass row-level security.
  [Key types and handling](https://supabase.com/docs/guides/getting-started/api-keys).
- [ ] Create one empty private storage bucket, such as
  `loop-engine-intelligence-dev`, or authorize engineering to create it in
  this development project. Return its name. Do not make it public to simplify
  downloads. Public buckets bypass download access checks.
  [Storage access models](https://supabase.com/docs/guides/storage/buckets/fundamentals).
- [ ] Choose the first sign-in method and identify two test users you control.
  Engineering will place them in separate test tenants. Email sign-in is a
  reasonable initial choice; say if you prefer an existing social provider.
  Do not share passwords or disable email verification to simplify tests.

Engineering owns database migrations, row-level security, storage access
policies, tenant membership, and token validation. Engineering will provide
the exact allowed redirect URLs after the development website has an address.
Do not add broad production redirect wildcards.
[Redirect configuration](https://supabase.com/docs/guides/auth/redirect-urls).

Website sign-in and Model Context Protocol client authorization are separate
integration tests. A Supabase project alone does not establish that remote
client discovery, consent, and authorization work.

### 3. Prepare Stripe without real charges

- [ ] Create or select a Stripe account you control. Use a dedicated sandbox
  where available, or explicitly confirm that the selected environment is
  test mode. Do not provide a live secret key. Sandbox transactions do not
  move funds, and Stripe supplies test payment methods for verification.
  [Stripe testing](https://docs.stripe.com/testing).
- [ ] Return the account and sandbox identifiers. Save the test secret key
  in your secret manager. Prefer a restricted test key once engineering gives
  you the required permissions. Keep it server-only.
  [Stripe key permissions](https://docs.stripe.com/keys).
- [ ] Choose one test subscription: amount, currency, billing interval, and
  the access it should grant. This can be provisional and is not public
  pricing. Create its test product and recurring price, then return their
  identifiers. Alternatively, authorize engineering to create those exact
  test objects in the named sandbox.
- [ ] Decide whether this test subscription has a trial and whether
  cancellation ends access immediately or at the end of the paid period.
  Keep usage overage charges disabled unless separately approved.
- [ ] If you already have a test customer for this exercise, return its
  identifier. Otherwise, include permission to create a disposable test
  customer. Do not provide real card details.

Wait for the exact endpoint before registering a webhook. Engineering will
provide the required events and test the signature, duplicates, delayed and
out-of-order delivery, and reconciliation. Save the endpoint signing secret
separately from the Stripe secret key. A local forwarding listener has its
own signing secret. A checkout success page never grants access by itself.
[Webhook configuration and delivery](https://docs.stripe.com/webhooks).

### 4. Set explicit limits and the test scope

- [ ] State the maximum one-time setup cost and maximum recurring monthly
  infrastructure cost, in a named currency. State which providers and paid
  resources are approved. Zero is a valid limit; a blank is not approval.
- [ ] State whether engineering may create and remove disposable test records,
  test users, and test artifacts in the named development project. Keep other
  projects and production data outside that permission.
- [ ] For live harness qualification, name one harness, its version, the
  machine where it may run, and the allowed working folder and effects.
- [ ] If model calls are permitted, name the exact provider and model,
  credential reference, total test budget, maximum physical calls, and time
  window. State any token ceiling separately. No alternate paid model or
  provider is authorized by default. Identity, payment, and deterministic
  retrieval tests can proceed without model calls.
- [ ] Confirm the telemetry choice. The suggested test setting keeps scoped
  identifiers, timings, costs, and outcome records, with raw inputs and outputs
  disabled. Training reuse requires separate permission. Choose a retention
  period for test records; embeddings are not anonymous telemetry.

Configure provider alerts as well. Do not assume an alert or plan allowance is
a hard spending limit. Supabase's spend cap excludes some charges, including
compute and several optional features.
[Cost controls](https://supabase.com/docs/guides/platform/cost-control).

## Prepare next, after the service address is known

| Owner action | What engineering will supply |
|---|---|
| Select a website hosting account. Vercel is a candidate, not a required purchase. | The tested build directory, environment settings, preview-access rules, and deployment procedure. Do not import and deploy the repository before these are ready; the GitHub integration can deploy automatically. |
| Choose an existing domain and intended development hostname, or approve a temporary host address. | Exact domain records and redirect URLs. Do not change existing production domain records yet. |
| Approve the Python service hosting account, region, resource limits, and storage. This may be separate from the website. | A measured deployment choice and cost estimate. Do not purchase several backend hosts. |
| Register the Stripe test webhook after its endpoint exists. | Exact endpoint, event selection, signature configuration, and replay test procedure. |
| Configure transactional email if the selected sign-in method sends messages to users outside the project team. | Sender requirements and exact authentication settings. Use an existing suitable service where possible. |

The website hosting account is optional for local verification, but remote
qualification needs an approved reachable service. Account preparation does
not authorize deployment or public exposure.
[Vercel GitHub deployments](https://vercel.com/docs/git/vercel-for-github).

Supabase's built-in email delivery is limited to pre-authorized project-team
addresses and is not intended for production use. Prepare custom email
delivery before inviting other testers through email sign-in. Do not grant
testers project-administrator access to work around that restriction.
[Authentication email delivery](https://supabase.com/docs/guides/auth/auth-smtp).

## Return this non-secret handoff

Fill only the fields that are ready. Use `not approved` or `undecided` for the
rest. This is a handoff form, not an executable configuration file.

```text
Secret manager and authorized delivery method:
Supabase project reference, URL, and region:
Private bucket name, or permission to create it:
Sign-in method and two controlled test-user identities:
Stripe account and sandbox/test-mode identity:
Stripe test secret-key reference:
Test product/price identifiers, or exact test-product creation permission:
Test customer identifier, or permission to create a disposable test customer:
Test amount, currency, interval, access, trial, and cancellation policy:
Disposable test-data creation/removal permission:
One-time infrastructure limit and recurring monthly limit:
Approved hosting account/region, or undecided:
Development hostname, or temporary address permitted:
Harness/version, permitted machine, working folder, and effects:
Model provider/model and credential reference, or no model calls:
Model test spending limit, physical-call limit, time window, and token policy:
Telemetry, retention, and separate training-use permission:
```

Send the webhook signing-secret reference only after that endpoint is
registered. Database and privileged storage-secret references can follow
when engineering identifies the exact server operation that needs them.

## Not required for this first test

Do not open paid accounts for every retrieval or learning candidate. AutoRAG,
MemRL, MemQ, GEPA, Qdrant, Vespa, and learned routing remain separate integration
and evaluation choices. No LangGraph subscription, dedicated search cluster,
separate content delivery service, or hosted browser subscription is a
prerequisite for testing identity, payments, and the first retrieval path.

Live payments, multiple embedding providers, public package publication,
accelerator applications, and Kaggle submissions can wait. A later benchmark
that needs competition data requires the owner's account authority and
acceptance of that competition's rules.

## Before public access

Confirm the support contact, account recovery path, service terms, privacy
description, retention choices, cancellation behavior, and rights to distribute
every starter package. Obtain appropriate review for business and legal
decisions. Engineering should implement the decisions and accurately describe
them; it should not invent legal assurances.

Identify a small first-user group and the concrete tasks they will try. Choose
what success means: connecting their client, retrieving useful qualified
material, applying a template, or completing a supported graph workflow.
Do not use the number of stored files as the product's success measure.

## Before charging

Run the selected provider's test-mode payment lifecycle with the exact
account and endpoint configuration. Verify successful activation, failed
payment, cancellation, reactivation, repeated events, and reconciliation.
Confirm that revocation reaches both the dashboard and protocol service.
Stripe documents the asynchronous subscription events and their intended
access consequences in its
[subscription event guide](https://docs.stripe.com/billing/subscriptions/webhooks).

Approve the final price and activation scope only after the running service
and product terms are concrete. Keep a recorded release decision that says
whether the result is a local candidate, a hosted pilot, or a paid launch.

## Work owned by engineering

Engineering owns the code, configuration templates, client instructions,
tests, evidence, deployment procedures, rollback preparation, status artifact,
and implementation of the approved account and product choices. Account
questions must not stop unrelated local work.

External outreach, accelerator applications, investor introductions, partner
submissions, and acquisition discussions require a separate instruction.
Researching these opportunities does not send a message or submit an application.
