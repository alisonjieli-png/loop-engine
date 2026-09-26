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
| Pi | The direct interface, as the served extension asks it | connected (`/api/v1/session`), listed (`/api/v1/capabilities` names the download route and the search request version), searched (`/api/v1/retrieval` in the extension's own search mode, `hybrid`), manifest matches (`/api/v1/provisioning` asked by identity alone, answered as a `provisioning_manifest/v3` record with the promised digest), downloaded (`/api/v1/download`), digest matches |
| Baltor Harness | The direct interface with `curl`, as the page shows | connected, listed (the token holds `provisioning:metadata` and `provisioning:read`), searched (the body of the page's own search command, unchanged), downloaded (the body of the page's own download command with the chosen identity, its digest and a new `request_id` filled in), digest matches |

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
