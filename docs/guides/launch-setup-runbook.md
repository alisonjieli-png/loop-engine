# Launch setup runbook

Kind: owner and operator instructions. Provider documentation checked on
September 19, 2026. This guide separates account preparation from qualified
deployment. No account, paid resource, domain change or live charge is created
by reading it.

## Current private pilot

The [current deployment](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
section of the client and server map is the current short statement of what
runs and where. Follow that section when this runbook differs from it. This
section adds the detail that the owner and the operator need.

The diagnostic service runs at <https://baltor-pilot.fly.dev/app>. One Fly
Machine in `iad` has one shared processor, 2 GB of memory and a 1 GB encrypted
persistent volume. The owner delegated the selection of reasonable limits:
50 United States dollars per month for infrastructure and 10 dollars for
one-time setup, with no model spending or live customer charges. This is an
operator allowance, not a provider-enforced billing cap.

Sixteen real HTTPS and Model Context Protocol checks passed, including
authentication, reference search, exact-body delivery, tenant separation and
duplicate-request accounting. The material is a private host-attested
diagnostic example, not an independently qualified customer catalogue.
The [live check report](../../artifacts/architecture-audit-2026-09-19/hosted-service-attempt-3.json)
does not qualify signup, payments, Supabase or native harness use.

The selected runtime payment account is `Baltor sandbox`,
`acct_1UHZ9KCCxLfArYED`. Stripe command-line authorization succeeded and a
read-only account request confirmed the binding. Its test credential is
privately stored. The earlier operator connection `acct_1UHZ972IF9bCskLc`
and the unrelated temporary sandbox are not this runtime target. Do not
mix their customers, prices, events or keys. Billing is not enabled live.

The Supabase organization is connected and the isolated `baltor-pilot` project
`qfzxmjznlwiopgvfgtsw` is healthy in `us-east-1`. Its quoted setup cost is
zero dollars per month on the selected free profile. Runtime database,
identity and private-storage integration remain incomplete. `app.baltor.ai`
has a valid Fly certificate. Namecheap has accepted Cloudflare's assigned
nameservers; the registry confirms them and Cloudflare reports the zone
active. Root and www also have valid certificates. With release 7, each of
these three hostnames passed 45 hosted website checks. With release 8, each
of the four hostnames passes 46. Some recursive resolvers retain older
answers. The owner confirms no existing email or forwarding.

Updated on September 20, 2026: releases one to seven were deployed directly
from the exact locally tested service image, which was built from a working
tree that was not committed. Release 8 was built by the guarded GitHub
workflow from a committed revision and deployed by image digest. The
deployment switch of that workflow was set to off again after the release.
The release record
`artifacts/architecture-audit-2026-09-19/pilot-release-8.json` holds the
revision, the image digest and the check counts. An earlier version of this
paragraph said that GitHub deployment remained disabled until the reviewed
release files were published together.

## Prepared access and remaining permission gaps

Resend management authorization works. The sender `auth.baltor.ai` exists and
verification has started. Cloudflare write authorization works; the Free zone
and its website, certificate and sender records have been created. Namecheap
read-back confirms `dana.ns.cloudflare.com` and `nile.ns.cloudflare.com`.
The registry delegation and Cloudflare activation are confirmed. Supabase database, storage and key
access work, while authentication-settings management returned forbidden.
Seek that exact additional grant through
authorization or a protected credential reference; do not bypass a refusal.

The owner confirmed Site URL `https://baltor-pilot.fly.dev` and redirect
`https://baltor-pilot.fly.dev/auth/callback` in Supabase. Treat this as an
owner observation until read-back is permitted. Do not ask for the same
manual settings change again.

Non-secret workstation references, resolved through the existing system
keyring rather than copied into files:

| Service | Exact lookup reference | Purpose |
|---|---|---|
| Fly | `application=loop-engine`, `service=fly.io`, `account=baltor`, `purpose=organization-deploy` | Existing pilot operations. |
| Stripe | `application=loop-engine`, `service=stripe`, `account=acct_1UHZ9KCCxLfArYED`, `purpose=runtime-test-api` | Approved sandbox operations only. |
| Supabase | `application=loop-engine`, `service=supabase`, `account=qfzxmjznlwiopgvfgtsw`, purposes `publishable-api` and `secret-api` | Browser application identification and separately approved server operations. Never interchange the keys. |
| Resend | `application=loop-engine`, `service=resend`, `account=baltor`, `purpose=transactional-email` | Sending credential; domain management required separate authorization. |
| Operator authorization | Credential labels beginning `resend-baltor\|`, `cloudflare-baltor-write\|`, or `supabase-baltor-project\|`, ending with `Codex MCP Credentials` | Existing Model Context Protocol connections. Resolve privately and check expiry; never dump the stored token response. |
| Namecheap | Claude Code project-local connection `baltor-namecheap` | Native authorization store and refresh, without raw-secret export. Registrar nameserver changes are authorized. |

Resend management uses `https://mcp.resend.com/mcp`. Its separate grant covers
management; a successful connection does not mean a domain was created or
mail delivered. No fresh authorization is needed unless a subsequent
operation demonstrates missing or expired access.

## Email and domain setup owned by engineering

Use Resend for authentication email. Start with its Free plan: 3,000 emails
per month and no more than 100 per day. The paid Pro plan is currently 20
dollars per month for 50,000 emails. Do not upgrade for the private pilot.
The choice is based on its documented Supabase connection, pilot allowance
and operator tooling, not a measured claim of superior inbox delivery.
[Resend pricing](https://resend.com/pricing)

1. Reuse the existing Resend account and completed management authorization.
   Inspect domain state before creating anything or retrying an uncertain call.
2. Reuse `auth.baltor.ai`, which engineering has created. The intended sender is
   `accounts@auth.baltor.ai`, named Baltor. Use the exact domain-verification
   records Resend supplies. Do not invent their values or replace existing
   mail records at the domain root.
3. Reuse the Free Cloudflare zone and verify the nameserver change already
   accepted by Namecheap. Keep Namecheap as registrar. The owner confirms no
   existing mail or forwarding, so its unused forwarding records were not
   migrated. Keep the saved old delegation for a reviewed rollback.
   The initial Namecheap record batch partially succeeded and refused the
   Resend mail-exchange record; the complete sender record set is now in
   Cloudflare. Do not repeat the partial batch with a force flag.
4. Keep the initial Fly website record DNS-only while its certificate and
   Model Context Protocol connection are qualified. Cloudflare proxying can
   be considered separately. Do not select Flexible encryption mode.
5. After authorization, engineering verifies the sending domain and connects
   Supabase authentication mail to `smtp.resend.com`, port `465`, username
   `resend`, with a private Resend sending credential. Disable tracking for
   authentication messages. Test confirmation, expiry, password recovery,
   duplicate submissions and delivery failures before opening registration.

The Fly-provided CNAME named `app`, targeting
`yj0ooj6.baltor-pilot.fly.dev`, is active in the old and new DNS configurations.
Cloudflare also holds root and www website records and exact certificate
verification records. The Fly host configuration accepts those exact hosts
and origins. The canonical protocol resource remains the Fly origin until
the account and client migration is separately qualified.

Resend is the application's transactional sender. It is not a replacement
for your human support mailbox. Keep any existing mailbox or forwarding
service until its replacement is explicitly selected and tested.

References: [Supabase connection](https://resend.com/docs/send-with-supabase-smtp),
[Cloudflare setup](https://developers.cloudflare.com/dns/zone-setups/full-setup/setup/),
[Fly domain setup](https://fly.io/docs/networking/custom-domain/).

## Email-free administrator and test access

The administrator sign-in address is <https://baltor-pilot.fly.dev/login>.
The dashboard is <https://baltor-pilot.fly.dev/admin>. This is token-based
sign-in, not a username and password form. The account is `baltor-admin`.

The owner credential is in the development workstation's system keyring.
Copy it to the local clipboard without printing it or adding it to a document:

```bash
/usr/bin/python3 /home/username/loop-engine/tools/service_admin_operator.py copy-key --app baltor-pilot --administrator baltor-admin
```

Paste it into the Service access token field. The administrator can create,
label, inspect and revoke test tokens. The initial limit is 20 active tokens,
with a default lifetime of 24 hours and a maximum of seven days. These are
host configuration fields, not fixed limits embedded in the dashboard.

The selected tenant determines material and usage access. `pilot-owner` has
the diagnostic example; `pilot-boundary` has no grant to that example.
Tokens for the same tenant share its grants and usage records. Creating a
token does not create an isolated customer workspace or grant payment access.
The existing diagnostic body entitlement has its own expiry and is not
extended by issuing a longer-lived token.

Only the creation response contains the raw token. Save it immediately.
The service stores its digest and an operation record. An exact repeated
creation request returns the same key identity without revealing its secret
or issuing another key. If delivery of the secret failed, inspect and revoke
that key before creating a replacement.

Test tokens cannot create administrators, change billing, run commands,
access cloud administration or call models. The administrator credential is
separate from customer harness credentials and expires October 20, 2026 at
02:51:28 UTC. Bootstrap-key rotation remains an operator action. Administrator
revocation does not automatically revoke every previously issued test token;
revoke those tokens explicitly or disable their target tenant.

The browser keeps the connection in memory only. Reloading signs it out.
The dashboard is not a secret vault and does not recover a cleared token.

Domain changes, multiple endpoints, region selection and request reconciliation
are covered by the [endpoint migration design](../architecture/SERVICE-IDENTITY-ENDPOINTS-AND-MIGRATION.md).
That document is embedded in the same main HTML; its proposed failover behavior
is not a current deployment claim.

## Recommended starting setup

Use one Python service for the website, subscriber workspace and Model Context
Protocol endpoint. The packaged pages use the same origin as the service.
Use Fly.io for general compute, reflecting the owner's existing experience.
Use Supabase as the proposed managed PostgreSQL, authentication and private
storage service. Vercel and a dedicated search cluster are not required for
this initial shape. The main HTML contains the complete comparison, costs and
six immediate setup instructions under Hosting and setup.

The current durable service uses SQLite. That deployment profile needs one
service instance, a persistent disk and tested backups. Do not put its database
on an ephemeral function filesystem or start independent replicas. Supabase
Postgres and private-bucket integration remain separate implementation and
qualification work. Creating a Supabase project does not migrate this store.

The pilot answers on `baltor.ai`, `www.baltor.ai`, `app.baltor.ai` and
`baltor-pilot.fly.dev`, each with a valid certificate, and the `/mcp` path
serves clients. Canonical protocol and account redirects still use the Fly
origin. The domain had no earlier mail records. The sender records for
`auth.baltor.ai` are installed. A DMARC record that only monitors,
`v=DMARC1; p=none;`, was added on September 20, 2026, and a public lookup
returns it. The bare domain still has no sender policy. Tighten the DMARC
policy only after sending is verified. The record of that change is
`artifacts/architecture-audit-2026-09-19/domain-mail-policy-1.json`.

## What you do and what engineering does

For this pilot, the selected accounts, region and limits are already recorded.
The owner supplies missing consent, controls private access and decides public
pricing and policy. Engineering performs routine configuration through the
permitted management interfaces, supplies tests and rehearses rollback.
The installation steps below are a reference for a fresh setup, not a request
to repeat completed preparation in the existing accounts.

| Prepare | Start with | Leave disabled |
|---|---|---|
| Hosting | One container-hosting account and one region | Automatic production deployment of the current development tree |
| Identity and large files | One isolated Supabase project and private bucket | Public buckets and broad redirect wildcards |
| Payments | Stripe sandbox, one recurring test Price and one test customer | Live charges and overages |
| Decision model | Optional Jev, Circuit or compatible existing endpoint and separate authentication reference | Calls without an exact approved allowance |
| Building work | One selected native harness and its provider account | Unneeded providers and paid services |

You do not need LangGraph, a hosted browser, several embedding providers or a
dedicated search cluster to qualify the first service journey.

## 1. Set up hosting

1. Sign in to your Fly.io account, select the organization that should own
   Loop Engine, and enable multi-factor authentication. Record its slug.
2. If connecting GitHub, grant access only to `alisonjieli-png/loop-engine`.
   Keep automatic production deployment off until a release is approved.
3. Choose a region and a monthly ceiling. Review the current service and disk
   charges before creating paid resources. Alerts are not necessarily hard caps.
4. Wait for engineering's single-Machine container deployment configuration.
   The current SQLite profile requires a persistent volume; the intended
   Supabase profile uses the external database once its adapter is qualified.
   Engineering must provide the exact tested image, command, host configuration,
   health path and disk ownership. The worker image's default `doctor` command
   is not a web server.
5. Store approved runtime secrets in Fly secret settings or the selected secret
   manager. Do not commit them or bake them into a container image.
6. Use the temporary hostname for tests. After those pass, add the custom
   hostname in the host dashboard and copy only its returned DNS records into
   the registrar. Do not invent an IP address or replace mail records.
7. Wait for the certificate and test the exact public hostname before giving
   the endpoint to customers.

References: [Fly applications](https://fly.io/docs/apps/),
[persistent volumes](https://fly.io/docs/volumes/overview/),
[application secrets](https://fly.io/docs/apps/secrets/).

### Prepared Fly access on the development workstation

The owner selected the Fly organization `baltor` (display name `Baltor`).
The installed `fly` and `flyctl` commands use version `0.4.104`.
An authenticated `fly orgs list --json` returned that organization successfully.
This verifies organization access, not deployment or spending approval.

The owner-provided token is stored in the operating system's persistent
Login keyring for the `username` account. Its item label is
`Baltor / Fly.io organization deployment`. These exact lookup attributes are
non-secret:

```json
{
  "application": "loop-engine",
  "service": "fly.io",
  "account": "baltor",
  "purpose": "organization-deploy"
}
```

Use the system Secret Service to resolve this item on the development
workstation. The system Python environment provides `secretstorage`.
Supply the value only as `FLY_API_TOKEN` in the authorized Fly command's
process environment. Do not print it or put it in command arguments, project
files, shell startup files or the main HTML. This is an operator credential
reference, not a new Loop Engine credential-resolver protocol.

Storage and read-back were verified. The browser login attempt was cancelled;
token-based access does not depend on completing it. A new workstation or a
locked keyring requires access to this credential store. Do not treat a missing
entry as permission to create another credential or resource.

### GitHub connection and manual deployment

The repository's `pilot` environment exists and accepts only the `main`
branch. Its `FLY_API_TOKEN` environment secret was transferred directly from
the system keyring. The secret value is not in this guide or in Git.
`FLY_ORG` is `baltor`, and `FLY_DEPLOY_ENABLED` is `false`.
These settings were read back from GitHub after creation.

The [manual workflow](../../.github/workflows/fly-pilot.yml) has two
operations. `verify_access` lists permitted Fly resources without creating
anything. `deploy` requires explicit settings, a matching application
confirmation and successful source checks for the exact current `main`
revision.

Updated on September 20, 2026: the workflow is committed and published, and
it built and deployed release 8. Its first `deploy` run stopped at a guard
before anything was built, because the guard compared the application name
with a padded line of a listing and could never match. Production did not
change. The guard now reads the structured listing, and the next `deploy` run
succeeded. The release record
`artifacts/architecture-audit-2026-09-19/pilot-release-8.json` keeps all three
runs. `FLY_DEPLOY_ENABLED` was set to `false` again after the release. An
earlier version of this paragraph said that the workflow still had to be
committed and published.

The [service image](../../Dockerfile.service) installs the serving dependencies
and starts the website and Model Context Protocol service as user `65534`.
The worker image keeps its existing diagnostic command. The workflow tests
the service image without external networking, then publishes and deploys
that exact image by digest. It does not rebuild after the checks.

After the deploy the workflow applies the catalogue grants of the release on
the one Machine. Stored grants name the items of the release that wrote them,
so a release that changes the catalogue offers nothing until the grants of
its packaged manifest are applied again: Fly release 12 offered no item until
`loop-engine service apply-grants --config /data/host.json` was run by hand.
The workflow now runs that command itself on the single started Machine,
through `flyctl machine exec`, which calls the Machines API the way the command
run by hand did. It does not open a remote shell, because from a new runner
each shell session adds a WireGuard peer to the organization that nothing
removes. The exec call starts the command as root, so the command runs as user
`65534` by way of `setpriv`. The command registers no tenant and replaces the
grants of each tenant the packaged manifest names, except an account that
follows the active catalogue release: for that account it reports the count of
items the account receives and writes nothing. The step reads the JSON
answer of the exec call, which leaves out the exit code when it is zero. It
fails unless the exit code is zero and the command printed exactly one grant
record, for the manifest at `/opt/baltor/catalogue/manifest.json`, with at
least one item for every named tenant and no tenant registered. It then repeats
the readiness check. A search that is in flight while the grants are replaced
is refused once with `disclosure_grant_changed` and succeeds when it is sent
again. The container check runs the same command against the image before it
is published: it clears the grants, shows that nothing is offered, runs the
command as root, and requires exactly one record, the packaged grants back and
every file on the volume still owned by the service user. If the step fails,
the release is already deployed; apply the grants by hand as after release 12,
then run `tools/check_hosted_catalogue.py`.

The next step applies the host billing policies on the same Machine. Each
release computes its billing policy digests from the host file, and checkout
and the customer portal stay unavailable while the stored digests differ. Fly
release 13 served for a day with both unavailable, because the one command that
stored them, `loop-engine service configure`, cannot run twice. The step runs
`loop-engine service apply-billing-policy --config /data/host.json` through
the same exec call and `setpriv` rule. The command names each stored record
version it read as the expected one, registers nothing, calls no provider and
changes nothing on an unchanged host. The step fails unless the exit code is
zero and the command printed one record that says every installed policy is
current, with no paid access ended, no tenant registered and no provider call.
It then requires `billing.checkout` and `billing.portal` in the live
capabilities record to equal what the host file offers, as the record states
it in `checkout_expected` and `portal_expected`, and repeats the readiness
check. The step prints the command's record in the workflow log: record
versions and digests, or a refusal code, and no secret. The workflow never
passes `--reset-paid-access`, so a changed entitlement policy that would end
paid access stops the release at this step with
`billing_policy_change_ends_paid_access`, for an operator to decide. The
container check runs the same command against the image before it is
published: it stores the terms an older release computed, requires the health
record to name that state, runs the command as root and requires the health
record to pass, a second run to change nothing and every file on the volume to
stay owned by the service user. If the step fails after a deploy, run the
command by hand on the Machine, read the record it prints, and read
`billing_policy_current` in the health record.

| Pilot environment setting | Required value or current state |
|---|---|
| `FLY_ORG` | `baltor`, configured |
| `FLY_DEPLOY_ENABLED` | `false`, set again after release 8. Follow the release stage of the [working cycle](../context/TAKEOVER-CHECKPOINT-2026-09-20.md#working-cycle) before switching it on. |
| `FLY_API_TOKEN` | Protected environment secret, configured |
| `FLY_APP` | Existing application `baltor-pilot`; independently verify the workflow variable before enabling deployment |
| `FLY_PRIMARY_REGION` | Selected region `iad`; independently verify the workflow variable |
| `FLY_APPROVED_MONTHLY_USD` | Recorded pilot allowance 50; not a provider billing cap |
| `FLY_DEPLOYMENT_APPROVAL_REF` | Reference to the exact deployment approval |
| `FLY_SERVICE_CONFIGURED` | Set to `true` only after host preparation and restore testing |

The [Fly profile](../../fly.toml) uses one shared processor, 2 GB of memory,
one persistent volume and a health check on `/api/v1/health`. Its explicit
single-Machine deployment disables spare Machines and uses immediate
replacement, so upgrades can interrupt service. It does not provide high
availability. Application and region are required runtime settings, not
assumed values in the file. The spending value is an approval record, not
a billing cap enforced by Fly.

Before enabling deployment, engineering must prepare exactly one
`loop_engine_service` volume in the approved region and the required public
networking. `/data/host.json`, the reviewed manifest and approved bodies must
already exist. The service process needs write access to the database
directory as user `65534`; it must not receive an empty replacement database
on every restart. The host configuration must allow its exact public
hostname and `localhost:8080`, which the health check uses. It must also state
where each caller's address comes from, in `http.request_limits`, because the
image binds every address behind the Fly proxy and refuses to start without
that statement; the [service runtime guide](../../src/loop_engine/core/service_runtime/README.md#which-address-is-counted)
shows the mapping for the Fly proxy. Preparation must also verify backup
restoration. The workflow does not create accounts, tenants, credentials or
these data files. Its only changes to service state are the grant application
and the billing policy application after the deploy, described above.

`FLY_SERVICE_CONFIGURED` records completed preparation; setting the variable
alone does not prove that preparation happened. A healthy process does not
qualify identity, payments, intelligence usefulness or the paid release.
Supabase integration remains separate work. No Fly application, Machine,
volume or public deployment was created during the GitHub connection setup.

### Publish and roll back a catalogue release

This procedure needs a deployed release that includes catalogue releases;
release 16 and every earlier release do not. It was first run against the live
Machine on September 23, 2026, after Fly release 17. Step 7 of the first
release then named `--all-tenants` and moved every account to grants that
follow the release, including `pilot-boundary`, the diagnostic account that
proves isolation. Step 7 now names the account to move, and
[the design record](../architecture/CATALOGUE-RELEASES-AND-HOT-SWAP-2026-09-22.md#the-first-live-run-and-the-isolation-repair)
records what happened and how it was repaired. The design is in
[the catalogue release design record](../architecture/CATALOGUE-RELEASES-AND-HOT-SWAP-2026-09-22.md).
Library bodies are private: a bundle is built outside this public repository,
travels only over `fly ssh sftp` from this workstation, and is removed from the
volume after it is published. In the commands below, `MACHINE` is the one
started Machine that `flyctl machine list --app baltor-pilot --json` names,
and `AS_SERVICE` is `setpriv --reuid=65534 --regid=65534 --clear-groups`, the
prefix the release workflow uses so that a command runs as the service user
that owns `/data`.

**Rollback rule.** An image rollback target must understand the current
catalogue state version. `loop-engine service catalogue-status` prints
`catalogue_state_version` and the versions the running image supports. Release
16 and every older release predate catalogue state: they refuse a host file
that has the `catalogue` section and fail the health check, which leaves the
service down until a compatible image is deployed again. They are not rollback
targets once the section exists. Do not remove the section to start an older
image while any catalogue state exists, because that image would serve items
the store has withdrawn and its `apply-grants` would turn accounts that follow
the release back into fixed lists.

Once, before the first release:

1. Create the body folder and the incoming folder as the service user:
   `flyctl machine exec MACHINE "AS_SERVICE mkdir -p /data/catalogue-bodies /data/incoming" --app baltor-pilot`.
2. Fetch `/data/host.json` with `python3 tools/fly_operator.py --account ACCOUNT -- ssh sftp get /data/host.json host.json --app baltor-pilot`,
   add the `catalogue` section with `"source": "image"` and
   `"body_store_root": "/data/catalogue-bodies"`, put it back with
   `ssh sftp put`, and restart the Machine. From this moment release 16 and
   every older release refuse the host file. Check that `/api/v1/health` answers ready.

For each release:

1. Build the bundle on this workstation, outside the repository:
   `PYTHONPATH=src python tools/build_catalogue_release_bundle.py --catalogue examples/29_intelligence_service/starter-catalogue --output ~/baltor-bundles/NAME --notes "WHAT CHANGED" --write`.
   Keep the printed `bundle_digest`.
2. Pack and measure it: `tar -C ~/baltor-bundles -cf NAME.tar NAME` and
   `sha256sum NAME.tar`.
3. Upload it privately:
   `python3 tools/fly_operator.py --account ACCOUNT -- ssh sftp put ~/baltor-bundles/NAME.tar /data/incoming/NAME.tar --app baltor-pilot`.
   Run this from this workstation, whose WireGuard peer already exists; a new
   runner would add a peer that nothing removes.
4. Check the archive digest on the Machine, then unpack it as the service user:
   `flyctl machine exec MACHINE "sha256sum /data/incoming/NAME.tar" --app baltor-pilot --json`
   must print the digest from step 2, then
   `flyctl machine exec MACHINE "AS_SERVICE tar -C /data/incoming -xf /data/incoming/NAME.tar" --app baltor-pilot`.
5. Publish:
   `flyctl machine exec MACHINE "AS_SERVICE loop-engine service publish-catalogue --config /data/host.json --bundle /data/incoming/NAME --expected-bundle-digest DIGEST" --app baltor-pilot --json`.
   The answer is one `service_catalogue_operation/v1` record whose `state` is
   `published` or `unchanged`. A wrong digest is refused with
   `bundle_digest_mismatch` and nothing is written.
6. The first time only, change the host file's `source` to `"store"` and
   restart the Machine. After that, every release reaches the running service
   within `refresh_seconds` without a restart.
7. The first time only, move each account that the packaged manifest grants
   to grants that follow the release, with one command for each account. The
   pilot manifest grants `pilot-owner` alone:
   `flyctl machine exec MACHINE "AS_SERVICE loop-engine service follow-catalogue-release --config /data/host.json --tenant pilot-owner" --app baltor-pilot --json`.
   An account that follows the release receives every item published later.
   Never name `pilot-boundary`, the diagnostic account that proves an account
   without grants reads nothing, the billing check accounts or `baltor-admin`.
   Never use `--all-tenants` on a host with diagnostic or isolation accounts.
   Up to Fly release 17 it moved every registered account. A release that
   carries the repair moves only the accounts already granted every item the
   service offers and lists every other account under `left_out` with the
   reason, but the rule stays: name each account.
8. Verify: `/api/v1/health` names the new `release_id` under
   `catalogue_release` and the `catalogue_view_current` check passes;
   `loop-engine service catalogue-status` names it as active; run
   `tools/check_hosted_catalogue.py`; and run the isolation check described
   below, which must pass all 19 of its checks.
9. Remove the incoming copy:
   `flyctl machine exec MACHINE "AS_SERVICE rm -r /data/incoming/NAME /data/incoming/NAME.tar" --app baltor-pilot`.
   The body store keeps its own copy, and two copies of a large library take a
   large share of the one gigabyte volume.

To roll back a release, read the active and earlier release identities with
`catalogue-status`, then run
`loop-engine service rollback-catalogue --config /data/host.json --to-release EARLIER --expected-release ACTIVE`.
The target is verified completely before the pointer moves, and every
withdrawal stays honoured. To withdraw one item at once, run
`loop-engine service withdraw-catalogue-item --config /data/host.json --identity IDENTITY --note "REASON"`;
a body read is refused immediately and the next view leaves the item out.

**Return an account to a fixed list.** An account that follows the release
receives every item published later, minus the items it denies. To end that
for one account, run
`flyctl machine exec MACHINE "AS_SERVICE loop-engine service stop-following-catalogue-release --config /data/host.json --tenant ACCOUNT" --app baltor-pilot --json`
once for each account. The account keeps exactly the items it receives from
the served release now, as a fixed list like the one `apply-grants` writes, and
an item published later does not reach it. An account that follows with every
current item denied keeps an empty list. The answer is one
`service_catalogue_grant_engine/v1` record whose `engine` is `snapshot` and
whose `grants` is the number of items the account kept. The command refuses an
account that does not follow the release with `account_not_following_release`.
It refuses with `catalogue_state_changed` when a release, a rollback or a
withdrawal was committed while it read the served release; run it again.

Then check isolation from this workstation:
`python3 tools/check_hosted_service.py --origin https://baltor-pilot.fly.dev --account pilot-owner --isolated-account pilot-boundary --identity IDENTITY --digest DIGEST --query "QUERY" --authorize-metered-read --output REPORT`.
`IDENTITY` names one item the owner receives and `DIGEST` the digest the
service serves for it now, which the owner's listing and the `items.jsonl` of
the published bundle both carry. Once the source is the store, the manifest in
this repository can name other digests: it follows the latest anchor, not the
published release. `REPORT` is a new file under
`artifacts/architecture-audit-2026-09-19/`. The check makes one metered read
for the owner. All 19 checks must pass, among them
`isolated_tenant_has_no_owner_grants` and `another_tenant_cannot_read_the_body`.

**Open repair from September 23, 2026.** After the first live run the five
accounts other than `pilot-owner` (`pilot-boundary`, `billing-check`,
`billing-check-2`, `billing-check-3` and `baltor-admin`) follow the release
with every current item denied, so an item published later would reach them.
Publish nothing new until a release that carries
`stop-following-catalogue-release` is deployed. Then return each of the five to
a fixed list with the command above; each answer must report `"grants": 0`.
Leave `pilot-owner` following, run the isolation check, and only then publish
the next release.

### Let new accounts follow the catalogue release

Found on September 24, 2026: the live host file sets
`"new_accounts_follow_release": false` in its `catalogue` section and names the
43 starter items under `browser_identity.starter_identities`. Every account
that Baltor's sign-up creates is therefore given a fixed list of those 43 items
and never receives an item published later. This procedure changes that.
`catalogue_follow_checks.py` replays it step by step against a real service
store, and `tools/test_catalogue_release_runbook.py` holds this section to the
replayed commands.

Before you start, check that the running release reports
`follow_all_tenants_preview` in the answer of `catalogue-status`. A release
without that field predates this procedure. `MACHINE` and `AS_SERVICE` are as
in the section above.

1. Fetch the host file and keep a copy on the volume:
   `python3 tools/fly_operator.py --account ACCOUNT -- ssh sftp get /data/host.json host.json --app baltor-pilot`,
   then `flyctl machine exec MACHINE "AS_SERVICE cp /data/host.json /data/host.json.before-follow-DATE" --app baltor-pilot`.
2. In one edit, set `"new_accounts_follow_release": true` in the `catalogue`
   section and `"starter_identities": []` in the `browser_identity` section.
   The service refuses a host file that sets both, with
   `invalid_starter_identities`, so the two changes go together. Put the file
   back with `ssh sftp put`, restart the Machine and check that
   `/api/v1/health` answers ready. From this moment a new account follows the
   release.
3. Read what the move would do, without writing anything:
   `flyctl machine exec MACHINE "AS_SERVICE loop-engine service catalogue-status --config /data/host.json" --app baltor-pilot --json`.
   Under `follow_all_tenants_preview`, `would_follow` must name customer
   accounts only, and `left_out` must name `pilot-boundary`, `billing-check`,
   `billing-check-2`, `billing-check-3` and `baltor-admin` with the reason
   `not_granted_every_item`, and `pilot-owner` with `already_following`. If
   `would_follow` names any of those six accounts, stop: that account holds
   every item, which the isolation check forbids, and it must first return to
   an empty list.
4. Move the customer accounts:
   `flyctl machine exec MACHINE "AS_SERVICE loop-engine service follow-catalogue-release --config /data/host.json --all-tenants" --app baltor-pilot --json`.
   Its `tenants` must equal `would_follow` from step 3. An account created
   between steps 3 and 4 follows already and appears under `left_out` as
   `already_following`. A customer whose fixed list lacks an item, for example
   one created before a catalogue release changed an item, appears under
   `left_out` as `not_granted_every_item`; move it by name with
   `follow-catalogue-release --tenant` only after checking that it is a
   customer account.
5. Run the isolation check of the section above, which must pass all 19 of
   its checks, among them `isolated_tenant_has_no_owner_grants`, then
   `tools/check_hosted_catalogue.py`.

The replay checks these known-wrong cases. A host file that follows the release
and still names starter identities is refused at start. With the live settings,
a customer account never receives a later item. Without step 4, the customers
that signed up before step 2 never receive a later item. Under the rule of Fly
release 17, which moved every account, the preview names `pilot-boundary` and
the next release reaches it; the current rule leaves it out. And the grant
engine refuses the whole move, writing nothing, when an account it is told to
keep fixed would move.

## 2. Create the Supabase account, then connect it

Account creation comes before the authorization link. The owner has completed
account creation for this pilot; do not create another account.

1. If you are setting up a new installation and do not have an account, open
   [Supabase sign-up](https://supabase.com/dashboard/sign-up). Continue with
   GitHub or sign up with an email address and complete its verification.
2. Create or select the organization that will own this project. For this
   pilot, use `Baltor` and the Free plan. Do not upgrade or add payment details
   merely to finish account preparation.
3. Approve the fresh Model Context Protocol authorization link. An earlier
   link can expire during signup. Engineering will create the isolated pilot
   project in `us-east-1`, record its reference and URL, and store private
   credentials separately. You do not need to create the project or bucket
   manually. Project-scoped database and storage permissions are a subsequent
   connection step, not permission to modify unrelated projects.
4. Identify the publishable application key. Keep the privileged secret key
   server-only. A publishable key identifies the application; a user access
   token identifies the signed-in person. They are not interchangeable.
5. Engineering creates the empty private intelligence bucket and its access
   policies. Do not make it public to simplify downloads.
6. Choose email sign-in or one existing identity provider, and two test users
   you control. Do not disable verification or make testers project administrators.
7. For protocol authorization, enable Supabase's OAuth 2.1 server in the test
   project when the consent page is ready. Start with pre-registered clients
   and explicit consent. Engineering supplies exact callback addresses.
8. Before inviting users outside your project team, configure production-suitable
   authentication email delivery. Do not rely on the limited built-in sender.

The resource server checks the exact issuer and intended audience before
resolving a durable subject-to-tenant binding. A token for another resource
must not become acceptable by removing audience validation. Website sign-in,
protocol consent and tenant access are separate tests.

References: [key handling](https://supabase.com/docs/guides/getting-started/api-keys),
[private buckets](https://supabase.com/docs/guides/storage/buckets/fundamentals),
[protocol authorization](https://supabase.com/docs/guides/auth/oauth-server/mcp-authentication),
[email delivery](https://supabase.com/docs/guides/auth/auth-smtp).

## 3. Set up Stripe test subscriptions

1. Select a dedicated sandbox or confirm that the selected account is in test
   mode. Do not supply a live key or real payment-card data.
2. Save the test secret key in your secret manager. Return the account and
   sandbox identifiers, not the secret value.
3. Create one test product and recurring Price. Choose amount, currency,
   interval, access, trial policy and cancellation behavior. This is test
   configuration, not an approved public price.
4. Create a disposable test customer for the first tenant. Return its identifier.
   The current adapter requires an exact server-owned customer mapping.
5. Configure the customer portal's allowed operations and return address.
   Engineering binds the exact portal configuration rather than accepting
   a customer-supplied redirect.
6. Wait until the service has an address, then register its
   `/api/v1/billing/webhook` endpoint with the event profile engineering supplies.
   Store that endpoint's signing secret separately from the test API key.
7. Run test checkout, activation, failed payment, cancellation, duplicate events
   and delayed-event reconciliation. A checkout success page must not grant access.
8. Keep live mode disabled until the release checks and product terms are approved.

References: [Stripe testing](https://docs.stripe.com/testing),
[key permissions](https://docs.stripe.com/keys),
[subscription events](https://docs.stripe.com/billing/subscriptions/webhooks).

## 4. Put each key in the right place

These are suggested environment bindings. A secret-manager entry name can
differ; the approved process must have a documented way to resolve it.

| Name or value | Place | Use |
|---|---|---|
| `BALTOR_SERVICE_TOKEN` | Customer's local client secret environment | Scoped access to the intelligence service. This is the variable that the Connect page of the website offers. An earlier version of this table named it `LOOP_ENGINE_ACCESS_TOKEN`. |
| `TYPESAFE_API_KEY` | Local decision-service process or approved credential host | Optional Jev calls |
| `OLLAMA_API_KEY`, `OPENROUTER_API_KEY`, `MISTRAL_API_KEY` | The selected local provider adapter | Only the provider the user chooses |
| `STRIPE_TEST_SECRET_KEY` | Hosted service's secret environment | Approved Stripe test operations |
| `STRIPE_WEBHOOK_SECRET` | Hosted service's secret environment | Signature verification for one endpoint |
| Supabase URL and publishable key | Approved client configuration when the adapter is installed | Application identification |
| Supabase secret key | Privileged server adapter only, if needed | Never a browser or protocol-client credential |
| Database password or connection string | Server secret manager only | Only a configured database adapter, not SQLite |

The current environment resolver uses references such as
`env:STRIPE_TEST_SECRET_KEY`. Do not place the corresponding value in JSON,
Markdown, source control, tool arguments, screenshots or chat.

An environment variable is not hidden from every process running as the same
operating-system user. Stronger isolation requires a separately controlled
credential holder and an authenticated scoped connection. A missing key in a
model prompt alone does not establish credential isolation from a local shell.

## 5. Start the current local service

Use the exact configuration and reviewed artifact manifest supplied for the
test. The host file uses `service_http_host_configuration/v1`, absolute paths,
explicit write authority and exact tenant grants. It is not a browser input.

The [runnable service example](../../examples/29_intelligence_service/README.md)
generates these files in a new directory and provides a complete local
walkthrough without any cloud account. Use it first.

```bash
python -m pip install '.[serving]'
loop-engine service configure --config /absolute/path/host.json
loop-engine service issue-key --config /absolute/path/host.json --tenant your-tenant
loop-engine service serve --config /absolute/path/host.json --host 127.0.0.1 --port 8000
```

Key issuance displays the secret once. Save it privately and do not record the
output. Visit `http://127.0.0.1:8000/app` for the workspace and `/docs` for setup
guidance. A restart serves existing records; it does not restore revoked grants.

To issue a billing-management key, the tenant must already hold
`billing:manage`. Use repeated `--scope` options to select the key's exact
scopes. Billing management is not included in the default key.

Remote serving requires an approved TLS proxy and exact public origin. The
loopback command above is not a public deployment recipe. Health confirms the
process is responding; it does not qualify identity, storage or payments.

## 6. Connect local harnesses and optional Jev

Model Context Protocol is the tool protocol. Authentication determines who
may call it. The hosted service needs both. The source serves protocol versions
`2025-11-25`, through the `initialize` handshake, and `2026-07-28`, named on
every request. A client that asks for an unserved version in `initialize` is
answered with `2025-11-25` and decides whether to continue. A host file whose
`http` block names `service_http_configuration/v1` or `protocol_version` must
be changed before a release with this source starts; the
[service runtime guide](../../src/loop_engine/core/service_runtime/README.md#the-host-record)
shows the change.

Use the [Jev and client setup guide](jev-and-harness-decision-tools.md) for
the decision configuration, direct command and harness tool process. Keep
service access and model access separate. Customers can use their chosen
native harness's own sign-in or user-owned provider key. An intelligence
subscription does not include model usage.

First inspect the available tools without calling a model. Then search a
permitted item, fetch its exact bytes and verify the digest. Separately test
native loading and actual use. A successful protocol connection does not
prove that the harness used the retrieved material.

## 7. Return a non-secret handoff

```text
Hosting account and selected region:
Temporary hostname or approved app.baltor.ai:
Maximum one-time setup cost and monthly recurring cost:
Supabase project reference, URL, region and private bucket:
Selected sign-in method and two controlled test-user identities:
Secret manager and authorized secret-delivery mechanism:
Stripe account, sandbox, product, Price and test customer identifiers:
Stripe API-key and webhook-secret references:
Optional Jev secret reference, model and call allowance:
Selected native harness, version, machine and allowed working directory:
Permission for disposable test users, records and artifacts:
Telemetry retention and separate permission for training reuse:
```

Use `not approved` or `not ready` for missing items. Do not paste credentials.
State any model spending and token ceiling separately from infrastructure
spending. Zero is a valid spending limit. Account preparation does not itself
authorize production access, a domain change or a purchase.

Before public launch, approve the support contact, account recovery, service
terms, privacy description, cancellation policy and distribution rights for
starter material. The [owner checklist](launch-owner-checklist.md) retains the
full approval and release requirements.
