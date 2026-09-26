# Quickstart live checks

Kind: dated check records. Each `quickstart-check-YYYY-MM-DD.json` file is one run of
[`tools/check_quickstarts.py`](../../tools/check_quickstarts.py) against the live
service at `https://baltor.ai`, the published base of the deployment recorded in
[the client and server map](../../docs/architecture/MVP-CLIENT-SERVER.md#current-deployment).
A second run on the same day is saved beside the first as `-2`, `-3` and so on; a
failed attempt stays beside its successor and is never overwritten.

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

Then the check runs each page's documented steps in the shape that harness sends them:

| Quickstart | Wire path | Service steps recorded |
|---|---|---|
| Claude Code, Codex, OpenCode | Model Context Protocol over streamable HTTP at `/mcp` | connected (`initialize` and `notifications/initialized`), listed (`tools/list` holds `intelligence_search` and `provisioning_read`), searched (`intelligence_search`), downloaded (`provisioning_read` with a new `request_id` and the `expected_digest`), digest matches |
| Pi | The direct interface, as the served extension asks it | connected (`/api/v1/session`), listed (`/api/v1/capabilities` names the download route and the search request version), searched (`/api/v1/retrieval`), manifest matches (`/api/v1/provisioning`), downloaded (`/api/v1/download`), digest matches |
| Baltor Harness | The direct interface with `curl`, as the page shows | connected, listed (the token holds `provisioning:metadata` and `provisioning:read`), searched, downloaded, digest matches |

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

## Records

| Record | Checked at (UTC) | Result | What it showed |
|---|---|---|---|
| `quickstart-check-2026-09-26.json` | September 26, 2026, 13:02 | 2 of 5 passed | Pi and the Baltor Harness passed. The three protocol quickstarts failed at searched because the checker read the hits off the `service_http_result/v1` wrapper instead of its `result`. The service answered correctly; the fault was in the checker, which was repaired with a named known-wrong test. This record predates the recipe page step. |
| `quickstart-check-2026-09-26-2.json` | September 26, 2026, 17:07 | 5 of 5 passed | All five pages matched the recipes reviewed on September 24, 2026. Every path found five hits for `review inputs` in catalogue release `856bff51…` of 6,398 served items, chose `orient_on_a_task_and_write_its_contracts` and received its 2,861 bytes with the promised digest. 24 HTTP calls, five usage records, no model call. |

## How it runs

The diagnostic key resolves from the workstation's system keyring through
[`tools/operator_credentials.py`](../../tools/operator_credentials.py) under the
reference `baltor-pilot-owner`, and is sent only in the request header. The
diagnostic keys expire on purpose;
[`tools/reissue_service_keys.py`](../../tools/reissue_service_keys.py) reissues
one without printing it, and a run after the expiry records `connected` as
failed with status 401.

Run it by hand from the repository root:

```bash
PYTHONPATH=src:tools python tools/check_quickstarts.py --origin https://baltor.ai
```

A cron entry on the development machine runs it once a day at 05:40 UTC and
appends its one-line summary to `~/.le-ci-tmp/quickstart-cron.log`. That
machine's cron keeps America/New_York time and has no `CRON_TZ`, so the entry
fires at 00:40 and 01:40 local time and only the run that lands in the 05 UTC
hour proceeds. It runs from the shared checkout when the check is committed
there, and from the worktree that wrote it until then.

The unit tests in [`tools/test_check_quickstarts.py`](../../tools/test_check_quickstarts.py)
run the same code against a fixture service on this machine and require each
known-wrong answer or page to fail its named step. One of them compares the
committed pages with the committed recipes on every push, without the network.
The roadmap step for this work is S-6.202.
