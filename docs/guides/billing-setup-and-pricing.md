# Billing setup and pricing

Kind: operating guide for engineering. Stripe documentation checked on
September 21, 2026.

This guide records the launch price for the hosted Baltor service, the
reasons behind it, and the exact operator steps that make the Stripe test
environment ready. It is a technical document, so it uses the exact runtime
terms. The public website does not show them.

Read [the launch setup runbook](launch-setup-runbook.md) for the rest of the
hosted service,
[the owner steps for taking payments](stripe-activation-owner-steps.md) for
what only the owner can do, and
[the packaging record](packaging-tiers-and-hosted-service.md) for the wider
shape of what is free and what is sold.

Current behaviour and planned behaviour are kept apart in every section.

## The price at launch

One paid plan, named Baltor Pro, at 29.00 US dollars each month. Payment is
in US dollars. There is no annual price, no seat price, and no second tier at
launch.

The reasons:

1. The market anchor. The
   [competitive landscape record of 2026-09-18](../research/COMPETITIVE-LANDSCAPE-AND-MONETIZATION-2026-09-18.md)
   verified the published prices of adjacent companies on that date and
   recorded the anchor as entry tiers at 19 to 29 US dollars each month. The
   examples behind that range include Mem0 Starter at 19 dollars, Supermemory
   Pro at 19 dollars, MemOS Starter at 19 dollars, SenseLab Starter at 29
   dollars, and LangWatch Growth at 29 euros for each seat. Baltor sits at the
   top of that range because the service carries reviewed material and a
   verification path, not storage alone.
2. One plan is one decision. A single price removes the tier question from
   the first customer conversation and from the first release of the website,
   the dashboard and the checkout page. More tiers can be added later without
   changing the record shapes, because the entitlement policy already accepts
   a list of allowed Price identities.
3. A price that is easy to refuse is easy to try. Twenty nine US dollars is
   inside an individual developer's own budget, which is the group the
   private beta invites.

This is a launch decision, not a measured willingness to pay. No customer has
paid this price yet. Revisit it when the first invoices and the first
cancellations exist.

## What is free and what is measured

```text
Hosted service at launch
├── Free for every account
│   ├── search across the four intelligence layers, which returns typed references
│   ├── reading the metadata of an item, including its digest and its licence state
│   └── the account, the client keys and the usage report
├── Included in the paid plan
│   └── downloading the body of a reviewed item, measured and recorded
└── Not sold by Baltor
    ├── model calls, which the customer pays for with their own provider account
    └── the customer's own harness and their own machine time
```

The measured unit is one downloaded item. In the code it is the unit
`provisioned_item`, and `ProvisioningMeterRequest` refuses any quantity other
than one, so one body read records exactly one unit. Search and metadata reads
record nothing. A grant declares `metering` as required or not, and only a
required grant writes a usage record.

There is no overage billing at launch. When an account passes the allowance
that the plan describes, the service does not raise an invoice and does not
charge a second time. The usage records are still written, so the volume is
known before any later decision about an allowance. Planned behaviour: a
higher tier, or a purchased pack of downloads, once real usage shows the
distribution. Nothing in the current code charges for an extra download.

Invited beta users are free. They do not go through checkout. An operator
grants paid access directly with `set_operator_entitlement`, which records the
source as a host grant, an expiry and an approval reference. That record says
plainly that it is a host grant and not evidence of a Stripe payment, so a
free invited account is never confused with a paying one in the records.

## The live account is a separate account

Everything below prepares the Stripe test environment. Test mode takes no real
money, and nothing created in it moves to the live account.

What the repository records, on September 21, 2026: the owner activated a live
account and a key for it is saved in the workstation keyring. The reference
`stripe-live` in `tools/operator_credentials.json` names that account,
`acct_1UHZ972IF9bCskLc`, and the reference `stripe-test` names the sandbox
account, `acct_1UHZ9KCCxLfArYED`. This guide has not observed the live account
through Stripe, so treat its readiness as recorded, not as verified here.

`tools/setup_stripe_sandbox.py` works in the test account only. It refuses any
key that is not a test key before a request leaves the machine, and it stops
if Stripe answers with an object that is not in test mode. Preparing the live
account needs a command that accepts a live key, with its own confirmation and
its own evidence; that is separate work and no part of it is in this command.

Both references declare the same environment name, `STRIPE_API_KEY`, so a
deployment holds the test key or the live key and never both. Observed today:
`tools/stage_service_secrets.py` refuses `stripe-live` before it gets that
far, with `only_runtime_credentials_may_be_staged:stripe-live`, because its
purpose `runtime-live-api` is not one of the runtime purposes that command
accepts. Staging the live key therefore needs a deliberate change to that
command, made with the live journey it belongs to.

## Prepare the Stripe test environment

`tools/setup_stripe_sandbox.py` finds or creates four objects in the Stripe
test environment and reports their identities:

```text
Stripe test environment
├── Product: Baltor Pro, with the fixed identity baltor_pro
├── Price: 2900 US cents each month, lookup key baltor_pro_monthly_usd
├── Billing portal configuration: cancel at the period end, update the payment
│   method, and show the billing history
└── Webhook endpoint: one HTTPS address, subscribed to exactly the five event
    types the service processes
```

The five event types are `customer.subscription.created`,
`customer.subscription.updated`, `customer.subscription.deleted`,
`invoice.paid` and `invoice.payment_failed`. They are the exact contents of
`EVENT_TYPES` in
`src/loop_engine/core/service_runtime/billing_records.py`, and a check in
`tools/test_setup_stripe_sandbox.py` compares the two lists.

How the command behaves:

- The API key arrives only in the environment variable that the selected
  reference names in `tools/operator_credentials.json`. A key that is not a
  Stripe test key is refused before any request leaves the machine.
- Every read happens before the first write. A dry run performs the reads and
  writes nothing.
- Nothing is written without `--confirm-test-mode-writes`.
- Each write carries its own idempotency key and is sent once. When the answer
  to a write is lost, the outcome is reported as unknown and the command stops.
  Inspect the Stripe test dashboard before running it again.
- One address keeps one endpoint. The reads happen first, and an endpoint that
  the reads find is never written again, so the command cannot create a second
  endpoint for an address that already has one. A second endpoint would
  deliver every event twice.
- Stripe returns the signing secret of a webhook endpoint only when the
  endpoint is created. The command puts that value straight into the system
  keyring and never prints it. When the endpoint already exists and the keyring
  does not hold its secret, the command stops. It does not report a ready
  service that names a signing secret nobody holds, because every delivery
  would then fail its signature check.
- The report holds identifiers only and is written to a path that must not
  already exist.

Exit codes:

| Code | Meaning | What exists at Stripe |
|---|---|---|
| 0 | ready, or a completed dry run | what the report names |
| 1 | stopped before Stripe performed any write | nothing new |
| 2 | refused before any request left the machine | nothing new |
| 3 | a write was sent and its outcome is unknown | look in the dashboard |
| 4 | stopped after Stripe performed at least one write | what the report names |

Read `committed_provider_writes` in the report for the number of writes that
Stripe answered with a success, and `provider_writes` for the number that were
sent. Code 4 always means the account changed. Code 3 means one write may or
may not have taken effect; the command never repeats it.

A run whose report could not be written is not ready either, whatever else
happened. The line the command prints then carries
`"report_written": false`, and the exit code follows the account: 4 when
Stripe performed a write, 1 when it did not.

### When a created endpoint loses its signing secret

Stripe shows the signing secret of a webhook endpoint once, in the answer to
the request that creates it. If the command cannot keep that value, the secret
is gone for good. Two paths lead there, and both end with exit code 4,
`committed_provider_writes` at 4, `webhook_endpoint.state` at `created` and
`signing_secret.in_keyring` false:

- the answer holds no value of the accepted shape, reported as
  `created_endpoint_answer_held_no_usable_signing_secret`;
- the workstation keyring refuses the value, reported as
  `signing_secret_could_not_be_stored_in_the_keyring`.

Running the command again does not repair this. The next run finds the
endpoint, finds no secret, and stops with
`webhook_endpoint_exists_but_its_signing_secret_is_not_in_the_keyring`.

To recover:

1. Read `webhook_endpoint.id` and `webhook_endpoint.url` in the report.
2. Delete that endpoint in the Stripe test dashboard, under Workbench and
   Webhooks. Deleting it at Stripe is the owner's decision, not the command's;
   the command never deletes anything.
3. For a keyring failure, unlock the workstation keyring first, or remove a
   conflicting saved item under the same service, account and purpose.
4. Run the command again. The product, the price and the portal configuration
   already exist, so the second run creates the endpoint only.

### Three values are fixed inside the command on purpose

The hardcoding audit reports three high findings in
`tools/setup_stripe_sandbox.py`, and all three are deliberate:

| Value | Finding | Why it is fixed |
|---|---|---|
| `https://api.stripe.com` | `hardcoding.09a7ae1c2fe8b01d5ee23900` | The command carries the account's secret key. A configurable origin would let a setting send that key somewhere else. The command imports nothing from `loop_engine`, so a change inside the service cannot move the destination either. A check asserts the exact value. |
| `STRIPE_WEBHOOK_SECRET` | `hardcoding.dcf08939757e7aaba6414bb0` | The name of the environment variable the running service reads, not a value. The service, the staging command and this command have to agree on one name. |
| `https://app.baltor.ai/api/v1/billing/webhook` | `hardcoding.de0597ea9aaeaead742ae431` | Only the default of `--webhook-url`. Pass another HTTPS address for another deployment. |

None of the three is a secret value. The command never writes a credential to
a file, an argument, an output line or a report.

All three have a reviewed entry in `devtools/hardcoding-allowlist.yaml`,
created on September 21, 2026, and all three are suppressed by it. The delta
gate

```bash
PYTHONPATH=devtools/src .venv/bin/python -m loop_engine_devtools.cli \
  --hardcoding-audit --allowlist devtools/hardcoding-allowlist.yaml \
  --baseline devtools/hardcoding-ci-baseline.json --fail-on-new high
```

ends with exit code 0. Observed on September 21, 2026:

```text
severity: {'high': 632, 'medium': 16579}
blocking_new_finding_ids: []
```

The webhook entry did not suppress its finding when it was written, and the
reason was one field. It declared `classification: DEPLOYMENT_CONFIGURATION`,
while the audit classifies the same finding as `STRATEGY_OR_PROVIDER_BINDING`.
The loader `_load_allowlist` in
`devtools/src/loop_engine_devtools/assurance/hardcoding.py` requires the entry
to mirror the classification the audit assigned; when it does not, the loader
skips the entry and records an allowlist problem, and the command in
`devtools/src/loop_engine_devtools/cli.py` returns 1 for a blocking finding
and for an invalid allowlist alike. The entry now carries the audit's own
classification, which is what the loader compares.

A known-wrong run confirms that the field is what clears the gate, and not
some other change. With one scratch copy of the allowlist whose only
difference is `DEPLOYMENT_CONFIGURATION` in that entry, the same command
reports `blocking_new_finding_ids: ["hardcoding.de0597ea9aaeaead742ae431"]`
and exits 1. The repository file was not changed for that run.

Finding identifiers are stable while the literal and its owner stay the same;
take them from a fresh audit run if either changes. Do not choose the
classification a reviewer would prefer. Read the one the audit assigned and
repeat it, or the entry will be skipped without suppressing anything.

## Order of operations

1. Save the Stripe test key once, if it is not already saved:
   `/usr/bin/python3 tools/operator_credentials.py store --ref stripe-test`.
   The value is typed into a hidden prompt and never appears in an argument.
2. Read what exists, and write nothing:

   ```bash
   /usr/bin/python3 tools/operator_credentials.py run --ref stripe-test \
     --timeout 180 -- \
     /usr/bin/python3 tools/setup_stripe_sandbox.py \
     --api-version 2025-03-31.basil \
     --report artifacts/stripe-test-setup-dry-run-1.json \
     --dry-run
   ```

3. Read the report. It names every object that a confirmed run would create.
4. Create what is missing:

   ```bash
   /usr/bin/python3 tools/operator_credentials.py run --ref stripe-test \
     --timeout 180 -- \
     /usr/bin/python3 tools/setup_stripe_sandbox.py \
     --api-version 2025-03-31.basil \
     --report artifacts/stripe-test-setup-1.json \
     --confirm-test-mode-writes
   ```

   Check the exit code before going on. Only 0 means ready. On 4, read
   [the recovery steps above](#when-a-created-endpoint-loses-its-signing-secret)
   before running the command again, because objects now exist at Stripe. On
   3, look in the Stripe test dashboard first.

5. Copy the record at `signing_secret.manifest_entry` in the report into the
   `api_keys` map of `tools/operator_credentials.json`, under the name at
   `signing_secret.keyring_reference`, which is `stripe-test-webhook-secret`.
   Copy that record whole. It holds no secret value, and it carries the seven
   fields staging needs: `service`, `account`, `purpose`, `environment`,
   `required_prefixes`, `value_pattern` and `endpoint_url`. The other fields
   under `signing_secret` describe where the value was saved; they are not a
   manifest entry, and staging fails on the missing environment name if they
   are copied instead. The purpose is `webhook-signing`, which is the purpose
   `tools/stage_service_secrets.py` accepts for a runtime credential.
6. Stage both runtime credentials into the deployment:

   ```bash
   /usr/bin/python3 tools/stage_service_secrets.py --app baltor-pilot \
     --account baltor --ref stripe-test --ref stripe-test-webhook-secret \
     --confirm-stage
   ```

7. Copy the `host_billing_block` from the report into the host configuration
   file, under the key `billing`.
8. Restart the service and run `loop-engine service configure`, which installs
   the entitlement policy and the session policy.
9. Test the customer journey with a Stripe test card, then confirm that the
   webhook delivery and the subscription state agree.

Steps 1 to 6 are operator work on the workstation. Steps 7 to 9 change the
deployed service and need the owner's authority for that release.

## The billing block of the host configuration

The report writes this block for the operator to paste into the host
configuration file. Every secret is an environment reference; no value is ever
written into the file. The identities below are examples from a check, not
identities from the live account.

```json
{
  "billing": {
    "webhook": {
      "account_id": "acct_1UHZ9KCCxLfArYED",
      "api_version": "2025-03-31.basil",
      "livemode": false,
      "signing_secret_refs": ["env:STRIPE_WEBHOOK_SECRET"]
    },
    "policy": {
      "allowed_price_ids": ["price_1SandboxMonthly"]
    },
    "provider": {
      "account_id": "acct_1UHZ9KCCxLfArYED",
      "api_version": "2025-03-31.basil",
      "livemode": false,
      "api_key_ref": "env:STRIPE_API_KEY",
      "allow_network": true
    },
    "sessions": {
      "account_id": "acct_1UHZ9KCCxLfArYED",
      "api_version": "2025-03-31.basil",
      "livemode": false,
      "api_key_ref": "env:STRIPE_API_KEY",
      "plans": [
        {
          "plan_ref": "pro-monthly",
          "label": "Baltor Pro",
          "price_id": "price_1SandboxMonthly"
        }
      ],
      "checkout_success_url": "https://app.baltor.ai/app",
      "checkout_cancel_url": "https://app.baltor.ai/app",
      "portal_return_url": "https://app.baltor.ai/app",
      "portal_configuration_id": "bpc_1SandboxPortal",
      "allow_network": true,
      "allow_session_creation": true
    }
  }
}
```

What each part does:

- `webhook` builds `StripeWebhookConfig`. It names the account, the event API
  version and the references that hold the signing secrets. More than one
  reference is allowed, which is how a signing secret is rotated without a gap.
- `policy` builds `StripeEntitlementPolicy`. Only a subscription on a listed
  Price grants paid access. There is no default paid plan and no amount is
  inferred.
- `provider` builds `StripeProviderConfig` and installs the read-only
  subscription reader. Without it, the service cannot resolve the current
  subscription state after an event.
- `sessions` builds `StripeSessionConfiguration` and turns on checkout and the
  customer portal. Each plan has its own reference, which is what a browser
  sends; a browser never sends a Price identity.

`checkout_success_url` and `checkout_cancel_url` are deliberately the same
address. The return from Stripe grants nothing. Paid access comes from the
subscription event and the entitlement policy, so a browser that lands on the
success address after abandoning checkout gets no more than one that lands on
the cancel address. Telling the two apart would only change what the page
says, and the deployed application serves one address for the signed-in view.
Give them different addresses when the application has a page worth showing
for each, and keep both inside the deployment's own origin.

Two environment names are used by the running service:

| Name | Holds | Used by |
|---|---|---|
| `STRIPE_API_KEY` | the Stripe test secret key | the subscription reader and the session creator |
| `STRIPE_WEBHOOK_SECRET` | the signing secret of the webhook endpoint | the signature check on every delivery |

`STRIPE_API_KEY` is the name the `stripe-test` entry in
`tools/operator_credentials.json` declares, and it is therefore the name that
`tools/stage_service_secrets.py` sets in the deployment. The report and the
generated block both use it, so the configuration and the staged secret cannot
drift apart.

One warning about the other guide. Section 4 of
[the launch setup runbook](launch-setup-runbook.md) still names
`STRIPE_TEST_SECRET_KEY` for the same secret, in its table of suggested
bindings and in the sentence about `env:STRIPE_TEST_SECRET_KEY`. That name is
a suggestion from before the credential manifest existed. Nothing sets it. An
`api_key_ref` of `env:STRIPE_TEST_SECRET_KEY` in the host configuration makes
the service refuse with `configured_secret_unavailable`. Use
`STRIPE_API_KEY`, which comes from the manifest. The runbook needs the same
correction; it is owned by another piece of work.

## Switching billing on and off

The billing block is optional. The service loads a billing boundary only when
the `billing` key is present, so removing the key switches the whole feature
off at the next start.

```text
Switching billing on
├── billing present, webhook and policy present        signature check and entitlement
├── provider present                                   current subscription state resolved
└── sessions present, allow_network and
    allow_session_creation both true                   checkout and portal offered
```

Finer control without removing the key:

- Set `sessions.allow_session_creation` to `false` to stop offering checkout
  and the portal while still processing events. The options answer then names
  `session_network_not_authorized` as the reason.
- Set `sessions.allow_network` to `false` for the same effect at the network
  boundary.
- Remove `provider` to stop reading the account. The event processor then has
  no resolver, and unknown subscription state stays unavailable rather than
  being guessed.
- Remove `sessions` and keep `webhook` and `policy` to accept events for
  subscriptions created elsewhere, for example by an operator in the Stripe
  dashboard.
- Set the runtime's `writes_authorized` to `false` to stop every write,
  including a session creation.

Switching billing off does not cancel a subscription at Stripe and does not
remove an entitlement that has already been recorded. Cancel the subscription
in Stripe, or let the customer cancel it in the portal, and the recorded
entitlement follows the next event.

## What this guide does not prove

- No live payment has been taken. The commands above touch the Stripe test
  environment only.
- The checks for `tools/setup_stripe_sandbox.py` use an injected transport.
  They prove the local contract, the refusals and the ordering. They do not
  prove that Stripe accepts these parameters on the live API.
- The parameters and the answers come from the public Stripe documentation
  read on 2026-09-21: the create reference for `/v1/webhook_endpoints`, which
  states that `url` and `enabled_events` are required, that `api_version` and
  `metadata` are optional, and that the answer carries the `secret` field;
  and the webhooks guide, which says a signing secret begins with `whsec_`.
  Neither page publishes the character set or the length of that secret, so
  the shape the command accepts is a local rule that is wider than every
  published example, not a provider rule.
- The delta gate for hardcoded values is red until the classification of one
  central allowlist entry is corrected, as recorded above. That is stated here
  rather than worked around.
- A live portal configuration also needs a business profile with a privacy
  policy address and a terms of service address. The test configuration does
  not.
- One Stripe account holds one signing secret for the service, because the
  keyring finds an item by service, account and purpose. Moving the webhook to
  another address means removing the old endpoint and the old keyring item
  first.
