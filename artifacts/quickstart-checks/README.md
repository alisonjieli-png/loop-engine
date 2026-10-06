# Quickstart live checks

Kind: dated check records. Each `quickstart-check-YYYY-MM-DD.json` file is one run of
[`tools/check_quickstarts.py`](../../tools/check_quickstarts.py) against one hostname of the
live service: `https://baltor.ai`, the published base of the deployment recorded in
[the client and server map](../../docs/architecture/MVP-CLIENT-SERVER.md#current-deployment),
and since October 5, 2026 also `https://app.baltor.ai` and `https://baltor-pilot.fly.dev`.
Each `quickstart-oauth-check-YYYY-MM-DD.json` file is one run of
[`tools/check_quickstart_oauth.py`](../../tools/check_quickstart_oauth.py), the Claude Code
OAuth connection described [below](#the-claude-code-oauth-check). A second run on the same day
is saved beside the first as `-2`, `-3` and so on; a failed attempt stays beside its successor
and is never overwritten. A record named `known-wrong` is a deliberate control.

## What one record holds

The check reads the five quickstart pages under `docs/guides/` (Claude Code, Codex,
OpenCode, Pi and the Baltor Harness). Three page steps come first on every quickstart:

- page names the published base: every service address in the page's snippets is on
  `https://baltor.ai`;
- page documents the first search: the page names `review inputs` in a code span;
- page matches the published recipe: the page shows its harness's configuration and
  verification command exactly as the Get set up page shows them. The recipes are read
  from `/assets/client-recipes.json` on the live service. A JSON configuration must
  parse to the same value, and the Codex table must be the same TOML text.

The published base is the one the service publishes for itself: its authorization
server's `resource` without `/mcp`. Every hostname names `https://baltor.ai`, so a run
against `app.baltor.ai` or `baltor-pilot.fly.dev` holds the pages to the same base;
`published_base_source` says where the base came from.

Then the check runs each page's documented steps in the shape that harness sends them:

| Quickstart | Wire path | Service steps recorded |
|---|---|---|
| Claude Code, Codex, OpenCode | Model Context Protocol over streamable HTTP at `/mcp` | connected (`initialize` and `notifications/initialized`), listed (`tools/list` holds `intelligence_search` and `provisioning_read`), searched (`intelligence_search`), downloaded (`provisioning_read` with a new `request_id` and the `expected_digest`), digest matches |
| Pi | The direct interface, as the served extension asks it | connected (`/api/v1/session`), listed (`/api/v1/capabilities` names the download route and the search request version), searched (`/api/v1/retrieval` in the extension's own search mode, `hybrid`), manifest matches (`/api/v1/provisioning` asked by identity alone, answered as a `provisioning_manifest/v3` record with the promised digest), downloaded (`/api/v1/download`), digest matches |
| Baltor Harness | The direct interface with `curl`, as the page shows | connected, listed (the token holds `provisioning:metadata` and `provisioning:read`), searched (the body of the page's own search command, unchanged), downloaded (the body of the page's own download command with the chosen identity, its digest and a new `request_id` filled in), digest matches |

On the protocol path a fourth page step, page names listed tools, follows the
tool list: every tool the page names in a code span must be one the service lists, and
a count the page states, such as "Baltor's six tools", must be the number it lists.

A unit test holds the Pi search mode and manifest record type to the extension
source that the website serves. A Baltor Harness page whose download command does
not bind `expected_digest` and `request_id` fails its downloaded step before
anything is sent.

Both paths answer a `service_http_result/v1` record whose `result` holds the
session, search, manifest or body record, and an answer in any other shape fails
its step by name. A quickstart passes only when every step passes: a connection
without a retrieval is not a pass, a search that says it loaded a body is not a
pass, and a body whose digest differs from the one the search promised is not a
pass. The record names the query, the identity each path chose, the digest prefix
of what it received, each `request_id`, the number of HTTP calls, the catalogue
release the search answered from, the served item count, the protocol versions
and the review date of the recipes. It keeps no body text and no credential;
refusal text is scrubbed before it is recorded.

Each successful download is one measured unit on the diagnostic account, so a
full run adds five usage records to that account and none to any customer.

Since October 5, 2026 every record names its `failure_code`: none when it passed,
`credential_expired` when every quickstart's connection was refused with 401 and the
expiry recorded beside the key in the keyring has passed, `credential_refused` for the
same refusal with a later or unrecorded expiry, `service_unavailable` when no connection
completed because the service could not be reached or answered a server error (5xx), as
during a deploy, and `quickstart_failed` otherwise. A credential failure marks every quickstart
`blocked_by` that code and lists it as blocked, not failed, in the one-line summary, and
the exit status is 3. `credential` holds the key's reference, account, `key_id`, expiry
and seconds left, read from the keyring item's attributes, never the key;
`credential_warning` is `credential_expires_soon` when fewer than three days are left
while the run still passes.

A request that does not complete fails the step it belongs to and names the
method, the address and the reason: the service could not be reached, the answer
was cut off or timed out, or the service answered with a redirect, which the
check never follows. The run goes on to the next quickstart, so a run during an
outage still writes its record. `capabilities_error` and `recipes_error` hold the
reason when the capabilities or the published recipes could not be read, and stay
empty otherwise. A download that was sent but not delivered keeps its
`request_id` in `request_ids_not_confirmed` instead of being counted: a refusal is
not measured, but an answer cut off after the service recorded the unit may be.
The first two records predate these three fields.

## Records

| Record | Checked at (UTC) | Result | What it showed |
|---|---|---|---|
| `quickstart-check-2026-09-26.json` | September 26, 2026, 13:02 | 2 of 5 passed | Pi and the Baltor Harness passed. The three protocol quickstarts failed at searched because the checker read the hits off the `service_http_result/v1` wrapper instead of its `result`. The service answered correctly; the fault was in the checker, which was repaired with a named known-wrong test. This record predates the recipe page step. |
| `quickstart-check-2026-09-26-2.json` | September 26, 2026, 17:07 | 5 of 5 passed | All five pages matched the recipes reviewed on September 24, 2026. Every path found five hits for `review inputs` in catalogue release `856bff51…` of 6,398 served items, chose `orient_on_a_task_and_write_its_contracts` and received its 2,861 bytes with the promised digest. 24 HTTP calls, five usage records, no model call. |
| `quickstart-check-2026-09-26-3.json` | September 26, 2026, 21:30 | 5 of 5 passed | The first run of the checker that records a request that did not complete as a failed step. The same result as the run before it: the same catalogue release, item and digest, 24 HTTP calls, five usage records, no request left not confirmed, no model call. The Pi path still searched in `lexical` mode here. |
| `quickstart-check-2026-09-26-4.json` | September 26, 2026, 21:44 | 5 of 5 passed | The first run in which the Pi path sends the extension's `hybrid` search and asks for the manifest by identity alone, and the Baltor Harness path sends the page's own curl request bodies. The live library had moved to catalogue release `add92543…` of 7,806 served items since the run before. The protocol and Pi paths found five hits and received the same 2,861-byte item; the page's own search, three results in `lexical` mode, found three hits and chose `file_path_aggregation_agent_coordination`, 3,865 bytes, with the promised digest. 24 HTTP calls, five usage records, no request left not confirmed, no model call. |
| `quickstart-check-2026-09-26-5.json` | September 26, 2026, 21:47 | 5 of 5 passed | The cron entry's own command, run by hand without its hour gate from an environment as bare as cron's: only `HOME`, `LOGNAME`, `USER`, `PATH=/usr/bin:/bin`, `SHELL`, `DBUS_SESSION_BUS_ADDRESS` and `TMPDIR`. The key resolved from the keyring in that environment, and the result matched the run before it. No run started by cron itself has happened yet; the first is due at 05:40 UTC on September 27, 2026. |
| `quickstart-check-2026-10-05.json` | October 5, 2026, 05:40 | 0 of 5 passed | The nightly cron's own record, the sixth failure in a row since September 30. Every page step passed; every quickstart stopped at connected with 401 `unauthorized`. The `pilot-owner` key, issued on September 22 for seven days, had expired on September 29 at 18:02:01 UTC ([evidence](diagnostic-key-renewal-2026-10-05.json)). |
| `quickstart-check-2026-10-05-2.json` | October 5, 2026, 23:34 | 0 of 5 passed | The same failure, run by hand before the renewal. |
| `quickstart-check-2026-10-05-3.json` | October 5, 2026, 23:35 | 5 of 5 passed | After `tools/reissue_service_keys.py` issued a new seven-day key for `pilot-owner` and `pilot-boundary`. Nothing else failed: no recipe drift, no protocol change. Catalogue release `133a102e…` of 39,710 served items; every path read `orient_on_a_task_and_write_its_contracts`, 2,861 bytes, with the promised digest. The service listed 12 tools while the Claude Code and Codex pages promised six, which this checker did not yet look at. |
| `quickstart-check-2026-10-05-4.json` | October 5, 2026, 23:52 | 5 of 5 passed | The checker of this change, on `https://baltor.ai`, with the pages that no longer state a tool count: `failure_code` none, the key's expiry read from the keyring (October 12, 23:52 UTC). |
| `quickstart-check-2026-10-05-5.json` | October 5, 2026, 23:53 | 5 of 5 passed | The same on `https://app.baltor.ai`, held to the published base `https://baltor.ai`. |
| `quickstart-check-2026-10-05-6.json` | October 5, 2026, 23:53 | 5 of 5 passed | The same on `https://baltor-pilot.fly.dev`. |
| `quickstart-check-2026-10-05-known-wrong-unfixed-pages.json` | October 5, 2026, 23:53 | 3 of 5 passed | Control: this checker with the pages as they were on `main`. Claude Code and Codex failed page names listed tools with "the page says six tools and the service lists 12". |
| `quickstart-check-2026-10-05-known-wrong-refused-key.json` | October 5, 2026, 23:54 | 0 of 5 passed | Control: an invalid key with the expired key's recorded expiry. The live service refused all five connections with 401 and the record named `credential_expired`, listing the five as blocked and none as failed. |
| `quickstart-check-2026-10-06.json`, `-2`, `-3` | October 6, 2026, 00:16 to 00:17 | 5 of 5 passed on each | The new cron command run by hand without its hour gate in cron's bare environment, against `baltor.ai`, `app.baltor.ai` and `baltor-pilot.fly.dev` in turn. |
| `quickstart-oauth-check-2026-10-06.json` | October 6, 2026, 00:06 | 15 of 15 steps passed | The first Claude Code OAuth check, with Claude Code 2.1.290. It made the checking account through Get started (`customer.cac8d810…`, access `founding_free_monthly`), and Claude Code registered client `55b89515…` with the loopback redirect `http://localhost:57853/callback`. The consent page named "Claude Code (baltor)" and three scopes; Claude Code's own listener took the redirect. |
| `quickstart-oauth-check-2026-10-06-2.json` | October 6, 2026, 00:07 | 15 of 15 steps passed | The same with the account and client registration reused, after the first run's revocation: Claude Code reported Needs authentication again before signing in. |
| `quickstart-oauth-check-2026-10-06-3.json` | October 6, 2026, 00:15 | 15 of 15 steps passed | The nightly unit's command, run inside the unit's sandbox (read-only home except the state and record folders, private `/tmp`). |

## How it runs

The diagnostic key resolves from the workstation's system keyring through
[`tools/operator_credentials.py`](../../tools/operator_credentials.py) under the
reference `baltor-pilot-owner`, and is sent only in the request header. The
diagnostic keys expire on purpose, after seven days at most. From September 30 to
October 5, 2026 nothing renewed them, so the check failed six nights in a row at
connected while the five quickstarts were fine.

[`tools/reissue_service_keys.py`](../../tools/reissue_service_keys.py) renews them
unattended. The systemd user timer `baltor-diagnostic-keys.timer` runs
`~/.le-ci-tmp/quickstarts/renew-diagnostic-keys.sh` every day at 05:10 UTC, before the
05:40 UTC check:

```bash
tools/reissue_service_keys.py --origin https://baltor-pilot.fly.dev \
  --account pilot-owner --account pilot-boundary --lifetime-seconds 604800 \
  --renew-within 345600 --revoke-replaced --confirm-reissue
```

It checks each saved key first and replaces only one the service refuses or one that
expires within four days, so a seven-day key is renewed about every three days and
always has three or more days left. The new key is stored only in the keyring, with
its `key_id`, `expires_at` and `issued_at` as attributes beside it; the service must
accept it before the key it replaces is revoked, so one key per account stays active.
Without `--confirm-reissue` the same command only reports what it would do. The script
uses `~/.le-main` once that checkout carries the renewal mode and this change's
worktree until then; its log is `~/.le-ci-tmp/quickstarts/renewal.log`, and the unit
runs with a read-only home except that log folder. The renewal signs with the
`baltor-admin` key, which it cannot renew: that key expires on October 20, 2026 and is
replaced through the operator bootstrap, after which the renewal exits 3 with
`administrator_credential_refused`.

```bash
systemctl --user list-timers 'baltor-*'                      # next runs
systemctl --user start baltor-diagnostic-keys.service       # renew now, if due
systemctl --user disable --now baltor-diagnostic-keys.timer  # stop renewing
```

Run it by hand from the repository root:

```bash
PYTHONPATH=src:tools python tools/check_quickstarts.py --origin https://baltor.ai
```

A cron entry on the development machine runs it once a day at 05:40 UTC against
`https://baltor.ai`, `https://app.baltor.ai` and `https://baltor-pilot.fly.dev` in turn,
and appends each one-line summary to `~/.le-ci-tmp/quickstart-cron.log`. That
machine's cron keeps America/New_York time and has no `CRON_TZ`, so the entry
fires at 00:40 and 01:40 local time and only the run that lands in the 05 UTC
hour proceeds. It runs from the shared checkout once that checkout carries the
hostname check, and from the worktree that wrote it until then. Its records go to
`~/.le-ci-tmp/quickstarts/records`; they are copied here when they show something new.

The unit tests in [`tools/test_check_quickstarts.py`](../../tools/test_check_quickstarts.py)
run the same code against a fixture service on this machine and require each
known-wrong answer or page to fail its named step. One of them compares the
committed pages with the committed recipes on every push, without the network;
another holds the committed pages' tool names to the twelve tools the service's own
protocol self-check expects. The roadmap step for this work is S-6.202.

## The Claude Code OAuth check

The token check signs with an operator-issued key. A customer who adds
`https://baltor.ai/mcp` to Claude Code without a header connects through OAuth instead,
and [`tools/check_quickstart_oauth.py`](../../tools/check_quickstart_oauth.py) runs that
path with the installed Claude Code itself. It makes no model call. Its checking
account was made once through Baltor's own public sign-up, by
`tools/check_live_account_journeys.mjs --fresh-only` with a disposable inbox, never
through staff tools, and is reused; its state and Claude Code's own credential store
stay in `~/.le-safety/quickstart-oauth`, mode 0700, outside the repository.

Its fifteen steps: the account is ready; a request without a credential is answered 401
with a challenge naming the protected-resource metadata; that metadata and the
authorization server's match what a client needs (S256, public-client registration,
refresh, revocation); `claude mcp list` says the server needs authentication;
`claude mcp login baltor --no-browser`, in a pseudo-terminal, prints an authorization
address with the code flow, S256, the exact resource, a loopback redirect and only
offered scopes; [`tools/oauth_consent_browser.mjs`](../../tools/oauth_consent_browser.mjs)
signs in on the consent page and allows the connection, and the browser takes the
redirect, with a code, the same state and the issuer, to Claude Code's own loopback
listener (the redirect is pasted at Claude Code's prompt only if the listener did not
take it); Claude Code stores an access and a refresh token; `claude mcp list` says
Connected; the token quickstart's connected, listed, searched, downloaded and digest
steps pass with the token Claude Code holds; the refresh token rotates the pair and the
old one is refused; and revocation ends the delegation. Revocation runs after any
failed step once tokens exist, so no run leaves a live grant. Claude Code keeps its
client registration between runs; `claude mcp logout` would drop it, so the check never
calls it.

The checking account holds a founding place, as every new account does while places
remain, so the first search's item downloads with its Baltor Pro access. An account
without a plan can read only Public Good files, and the check would then fail at
searched with no readable hit until it learns that free path.

The systemd user timer `baltor-quickstart-oauth.timer` runs
`~/.le-ci-tmp/quickstarts/check-quickstart-oauth.sh` every day at 05:55 UTC, with a
read-only home except the state folder and `~/.le-ci-tmp/quickstarts`; records go to
`~/.le-ci-tmp/quickstarts/oauth-records` and the summary to
`~/.le-ci-tmp/quickstarts/oauth.log`. It uses `~/.le-main` once that checkout carries the
check and a `showcase/node_modules` link, like this change's worktree has.

```bash
PYTHONPATH=src:tools python tools/check_quickstart_oauth.py --origin https://baltor.ai \
  --state-dir ~/.le-safety/quickstart-oauth                  # by hand; add --create-account only for a new account
systemctl --user disable --now baltor-quickstart-oauth.timer # stop the nightly run
```

OAuth works at `https://baltor.ai/mcp` only. Every hostname's challenge names that
resource, so Claude Code refuses `https://app.baltor.ai/mcp` with "Protected resource
https://baltor.ai/mcp does not match expected https://app.baltor.ai", observed on October 5,
2026. The Get set up page's OAuth section names the right address, but its Endpoint field
shows the address of the host it is opened on.

The unit tests in [`tools/test_check_quickstart_oauth.py`](../../tools/test_check_quickstart_oauth.py)
run the orchestration against a fake service and a fake Claude Code, and the terminal
driver against a small program in a real pseudo-terminal that prints what Claude Code
printed; each known-wrong case fails its named step.
