# Staff tools

Kind: operating guide for the people who run Baltor.

The staff tools let a staff member manage the hosted service from Claude
Code, Codex, OpenCode or any other Model Context Protocol client: find and read
accounts, grant free monthly Baltor Pro or download credits, send a service
message, send sign-up links to people who signed up offline, read the
activity, search the catalogue and publish new library files without a
redeploy. The owner asked for them on September 24, 2026.

This guide describes the source in this repository. A deployment serves the
staff tools only after a release that includes them.

```text
Staff tools
├── a staff key, created on the Administration page by a superadmin
├── one protocol endpoint, /admin/mcp, that answers staff keys only
├── the same tools at /api/v1/admin/tools/<tool> for scripts and the page
└── every change planned first, then applied with the plan's digest
```

## Create a staff key

A staff key belongs to one entry of the `staff` list in the host file's
`accounts` block and carries that entry's role: superadmin, developer or
analytics. Only a superadmin can create one, and only in a signed-in browser
session, so a key that leaks cannot create another.

1. Sign in on the website and open Administration.
2. Under "Staff tools in Claude Code, Codex and other clients", choose the
   staff member, give the key a label such as "Claude Code on my laptop" and
   keep the lifetime at 24 hours unless you need longer. The longest is seven
   days.
3. Select Create staff key. The page shows the key once, in a password field.
4. Put it in the environment variable `BALTOR_STAFF_KEY` on the machine that
   runs your client. The service keeps only its digest and cannot show it
   again.

Revoke a key on the same page. Its next call is refused, and a change it
planned but had not applied commits nothing.

## Connect a client

The endpoint is `https://app.baltor.ai/admin/mcp` for the live service, or
`/admin/mcp` on the service you run. The transport is Streamable HTTP, and the
key travels in the `Authorization` header, read from `BALTOR_STAFF_KEY`. No
file below holds a key.

Claude Code, in a `.mcp.json` file in your project folder:

```json
{
  "mcpServers": {
    "baltor-staff": {
      "type": "http",
      "url": "https://app.baltor.ai/admin/mcp",
      "headers": {
        "Authorization": "Bearer ${BALTOR_STAFF_KEY}"
      }
    }
  }
}
```

Codex, merged into your `config.toml`:

```toml
[mcp_servers.baltor_staff]
url = "https://app.baltor.ai/admin/mcp"
bearer_token_env_var = "BALTOR_STAFF_KEY"
```

OpenCode, merged into the `mcp` section of your `opencode.json`:

```json
{
  "mcp": {
    "baltor-staff": {
      "type": "remote",
      "url": "https://app.baltor.ai/admin/mcp",
      "enabled": true,
      "oauth": false,
      "headers": {
        "Authorization": "Bearer {env:BALTOR_STAFF_KEY}"
      }
    }
  }
}
```

The Administration page shows the Claude Code and Codex entries with the
address of the service that served the page.

### An operator agent

An operator agent, such as OpenClaw or Nous Research's Hermes Agent running an
Ollama model, connects the same way: add a remote Model Context Protocol
server in the agent's own settings with the endpoint above, Streamable HTTP,
and an `Authorization` header whose value is `Bearer` followed by the key from
`BALTOR_STAFF_KEY`. The agent sees only the tools its key's role may call, and
the service checks the role again on every call.

Give an agent the smallest role it needs:

- add a staff entry for it in the host file's `accounts` block, named by an
  address you own for that purpose, with the role `analytics` for reports or
  `developer` for diagnostics;
- create its key on the Administration page for that entry;
- keep superadmin keys for people. Even a superadmin key changes nothing
  without a plan call followed by an apply call that names the plan's digest.

The model the agent runs is the operator's own. Baltor does not run it and
does not see its prompts.

## Plan, then apply

Every tool that changes something takes two calls. The first has `"step":
"plan"`. It changes nothing and answers what would change and a
`plan_digest`. The second repeats the same arguments with `"step": "apply"`,
that `plan_digest` and a new `request_id`:

```json
{"step": "plan", "tenant_id": "customers.1f0c...", "downloads": 20, "valid_days": 30,
 "reason": "Support gesture after the outage of September 24"}
```

```json
{"step": "apply", "tenant_id": "customers.1f0c...", "downloads": 20, "valid_days": 30,
 "reason": "Support gesture after the outage of September 24",
 "plan_digest": "<the plan_digest the plan returned>", "request_id": "credits-2026-09-24-1"}
```

If anything the plan depended on changed in between, such as the account's
record or the recipients of a message, the apply is refused with
`plan_changed` and nothing happens: plan again and read the new plan. A
repeated `request_id` returns the first result instead of acting twice. Every
call, a read, a plan, an apply or a refusal, leaves one audit record, and
`activity_search` reads them.

## Tools and the permission each needs

| Tool | What it does | Permission |
|---|---|---|
| `accounts_search` | Accounts by address text, plan, founding place, state and creation time, a page at a time | `accounts.search`; analytics gets counts only |
| `account_get` | One account: plan, entitlements, download credits, key metadata, usage totals, last activity | `accounts.read` |
| `account_action` | Grant or revoke free monthly Baltor Pro, switch an account off or on | the operation's own permission |
| `accounts_invite` | Send sign-up links to typed addresses | `accounts.send_sign_up_links` |
| `accounts_import` | Send sign-up links to rows exported from a form or a spreadsheet | `accounts.send_sign_up_links` |
| `credits_grant` | Grant download credits with an expiry and a reason | `credits.grant` |
| `credits_revoke` | End one grant of download credits | `credits.revoke` |
| `message_send` | Send a plain-text service message to one account or a filtered set | `messages.send` |
| `activity_search` | Staff calls, account actions, sign-ups, activations, downloads and refusals by code | `activity.read`; analytics gets counts only |
| `data_search` | The served catalogue with the usage of each item | `catalogue.read` |
| `catalogue_status` | The served release, the stored releases and the bundles waiting to be published | `catalogue.read` |
| `catalogue_publish` | Publish an uploaded release bundle | `catalogue.publish` |
| `catalogue_rollback` | Serve an earlier release again | `catalogue.rollback` |
| `item_withdraw` | Withdraw one item at once and for good | `catalogue.withdraw` |
| `service_health` | The measured health record, the newest refusal codes and the staff tools' own state | `service.diagnostics` |

A superadmin holds every permission. A developer holds `service.diagnostics`,
`activity.read` and `catalogue.read`. Analytics holds `accounts.counts`,
`usage.counts`, `activity.counts` and `catalogue.read`, and never reads an
address.

## Download credits

A download credit is one download of one item, the unit the service already
measures. `credits_grant` gives an account a number of downloads, an expiry
from one hour to 366 days away, and a reason. There is no purchase and no
overage billing: nobody pays for a credit, and an account that uses its last
credit is refused the next body read exactly as an account without a plan is.

An account whose plan grants downloads uses the plan and draws no credit. An
account without such a plan downloads while it holds a usable credit, and each
metered download draws one, from the grant that expires first. A retry with the
same request identity draws nothing again. `credits_revoke` ends one grant;
its unused downloads end with it.

## Service messages

`message_send` sends plain text inside the service message template, which
greets the reader and says that the message is about their account and is not
marketing. It needs a `purpose`:

- `account_notice`, about the person's own account;
- `service_notice`, about the service, such as planned maintenance;
- `security_notice`, about the security of the account or the service;
- `support_reply`, an answer to something the person asked.

A message without a purpose is refused with
`message_service_purpose_required`. Marketing, a newsletter, a promotion or an
offer is refused with `marketing_needs_recorded_consent`, because the service
records no marketing consent. The plan shows the exact subject and body each
recipient reads and a masked address for the first recipients.

Recipients are one account, named by `tenant_id`, or the accounts an
`audience` selects by plan, founding place, state and creation time. Only an
account with a confirmed address receives a message.

The mail provider's free plan sends 100 messages a day for the whole service.
Staff messages and staff sign-up links draw on their own daily allowance of
50, so public sign-up and password recovery keep the rest. A plan or an apply
that would pass the allowance is refused with `staff_mail_daily_cap_reached`
before anything is sent. The allowance resets at midnight UTC.

## People who signed up offline

`accounts_invite` takes typed addresses; `accounts_import` takes the CSV text
of a form or spreadsheet export with its header row, or JSON rows. Either way
each address gets Baltor's own sign-up link, the same one the Administration
page's form sends: a message that names you, a link to the confirmation page,
and a password the person chooses there. With `"free_monthly": true` the
account includes free monthly Baltor Pro when it opens.

Each row is decided on its own, and the plan lists every row's outcome:

- `send`: the address gets a link;
- `invalid_address`, `empty_row`: nothing to send;
- `duplicate`: the same address appeared earlier in the import;
- `address_has_an_account`: the account is already open;
- `sign_up_pending`: a link is waiting to be used; send it again with
  `"resend_pending": true`;
- `second_way_in`: the row has a value in a column that would carry authority
  into an account, such as a password, a confirmation, a provider identity, a
  role, scopes, a plan or credits. Nothing is sent, and the value is never
  kept. Remove the column, or leave it empty, and import again.

The import finds the address column by its name, such as "Email" or "Email
Address", or by `email_column`. Other columns, such as a timestamp or a name,
are listed as ignored.

## New files in the live library without a redeploy

A catalogue release adds, changes and withdraws library files while the
service runs. It needs the host file's `catalogue` section with its body
folder, and for `catalogue_publish` the incoming folder in the `staff_tools`
block.

1. Build the bundle away from the service with
   `tools/build_catalogue_release_bundle.py` and keep the `bundle_digest` it
   prints. The
   [launch runbook](launch-setup-runbook.md#publish-and-roll-back-a-catalogue-release)
   has the command.
2. Upload and unpack the bundle into the incoming folder, `/data/incoming` on
   the hosted service, as the runbook describes.
3. Call `catalogue_status`. The bundle is listed under `incoming_bundles`.
4. Call `catalogue_publish` with `"step": "plan"`, the bundle's folder name and
   `expected_bundle_digest`. A bundle whose digest differs is refused with
   `bundle_digest_mismatch`. The plan says how many items it adds, changes and
   withdraws against the active release.
5. Apply the plan. The service serves the new release at its next catalogue
   refresh, which the `catalogue` section's `refresh_seconds` sets, with no
   restart.

`catalogue_rollback` serves an earlier release again, and every withdrawal
stays honoured. `item_withdraw` removes an item version at once and for good.
This is the same release step the `publish-catalogue`, `rollback-catalogue`
and `withdraw-catalogue-item` commands run, with the same guards.

What comes next: the import pipeline that turns outside and generated
material into reviewed items hands its bundles to this same release step, and
a library of many thousands of items also needs the search index built by the
publisher and object storage for bodies that the
[catalogue release design record](../architecture/CATALOGUE-RELEASES-AND-HOT-SWAP-2026-09-22.md)
names. Neither is built yet.

## Host configuration

Nothing new is required: a host with the `accounts` block and a browser
identity serves the staff tools, and no new secret is stored, because a staff
key lives in the service store as a digest. The optional `staff_tools` block
sets two things:

```json
"staff_tools": {"record_type": "service_staff_tools/v1", "mail_daily_cap": 50,
                "catalogue_incoming_root": "/data/incoming"}
```

`mail_daily_cap` is a whole number from 0 to 100. Without
`catalogue_incoming_root`, `catalogue_publish` is refused with
`catalogue_incoming_folder_not_configured`. A release that predates the staff
tools refuses a host file with this block, so remove it before you roll back
to such a release.

## Limits

- Account search and message recipients read the identity provider's whole
  user list for each call, which suits a young service.
- Activity search reads every record of each kind it is asked for. Refusals
  come from the failure journal, which keeps the newest refused requests.
- A message that fails after its reservation still counts against the
  allowance.
- The sign-up link form on the Administration page does not draw on the staff
  daily message allowance yet.
