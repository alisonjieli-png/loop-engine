# Launch customer journey on the live service, October 16, 2026

Kind: dated verification record of the ordinary signed-in customer journey on
`https://baltor.ai`, run before launch for the October 13 priority in the
[delivery sequence](../roadmap/DELIVERY-SEQUENCE.md#current-ordered-checklist).
It keeps its bytes after this date; correct current guides instead.

## Result

| Gate | Result | Deciding observation |
| --- | --- | --- |
| Native OpenCode with Baltor | Passed in part | Connect, discover, retrieve, use, revise, crash and credential recovery all ran natively in a clean workspace. The model's first continuation after recovery was wrong and needed one correction turn. |
| Claude Code | Passed | The installed Claude Code 2.1.301 added the server, signed in with OAuth and connected; protocol search, download, digest, refresh and revocation passed. |
| Codex | Passed | The installed Codex 0.162.1 signed in with OAuth inside `codex mcp add`; protocol steps with its stored token, the key recipe and an emulated registration passed. |
| Cursor | Passed at protocol level | Both documented callback addresses and the key entry passed. No Cursor application was run. |
| VS Code | Passed at protocol level | Port 33418, a chosen port and the key entry passed. No VS Code MCP client was run. |
| ChatGPT app | Passed at protocol level | A client registered with ChatGPT's callback read the eight-tool OpenAI presentation without a header; search and download passed. ChatGPT itself was not used. |
| Pi | Passed | The installed Pi 0.73.1 ran the documented extension check (`Result: ready`); the extension's search and download requests passed with digest and header checks. |
| Account lifecycle | Passed | Sign-up, sign-out, sign-in, password recovery, key creation and revocation, checkout reachability. Saved work, data export and self-service deletion are not offered. |

The native OpenCode gate is recorded as passed in part because the recovery
continuation, observed once with one model, attributed earlier files to the
interrupted request, skipped the requested Baltor search and wrote one wrong
commit hash. A customer correction fixed both in the next turn. The service,
the credential refusal, the reconnection and the session history behaved as
documented. Only OpenCode 1.17.9 with `glm-5.3` on Linux was observed.

## Scope and controls

- One customer account, made at 14:31 UTC through Get started with a disposable
  inbox by `tools/check_live_account_journeys.mjs --fresh-only`. Its address
  prefix is `baltor-check-eab37f55`; analytics can exclude it by that prefix.
  The account took a founding place (`founding_free_monthly`, Pro), as every
  new account does while places remain.
- The journey state stayed in a private folder outside the repository, mode
  0700 with 0600 files. The suggested path directly under `~/.le-safety` was
  refused by the tool (`private_parent_permissions_required`), because that
  folder is group-writable.
- OpenCode ran from `~/.local/bin/opencode` with its own `HOME`,
  `XDG_DATA_HOME`, `XDG_CONFIG_HOME`, `XDG_STATE_HOME`, `XDG_CACHE_HOME` and
  `TMPDIR` under the journey folder. `opencode debug paths` confirmed every
  path. The owner's OpenCode data and configuration were never read.
  `OPENCODE_DISABLE_AUTOUPDATE` was set, and the customer configuration set
  `autoupdate` to false and `share` to disabled, so the installed binary could
  not change and no session was shared. That is machine safety, not a
  customer step.
- Model access was the customer's own OpenCode provider entry, pointed at a
  local recorder that forwarded each request to Ollama Cloud with the key from
  the environment and refused any call beyond a ceiling of 40. OpenCode never
  held the model key. 35 calls were made.
- Claude Code used its own `CLAUDE_CONFIG_DIR` and Codex its own `CODEX_HOME`,
  with credentials stored in that folder. Pi ran with its own `HOME`.
- No card details were entered. Checkout pages were opened and closed.
- Every OAuth delegation and all four Baltor keys were revoked before the
  record was written, and each was refused afterwards with status 401.
- Source revision of this checkout: `f2ae304e`. Catalogue release seen by every
  search: `29a2bc33c313...`.

## Native OpenCode journey

The project was a new Git repository with seven conventional commits and a
`v0.1.0` tag. The task: find a Baltor component that writes release notes,
install it, write the notes for 0.2.0, revise them once, then survive a crash
and a replaced key.

| Time (UTC) | Step | Result | Evidence |
| --- | --- | --- | --- |
| 14:55 | Create a Baltor key on `/account` | Passed | Label, three scopes, 1,440 minutes. Shown once, then cleared from the page. |
| 14:57 to 15:03 | Model check from the quickstart, no tools | Passed on the second start | The first `opencode run` stalled for 300 seconds before any model request. The second answered `5`. 2 calls, one of them OpenCode's title call. |
| 15:03 | Merge the published `baltor` entry and run `opencode mcp list` | Passed | `baltor connected`. Without the token in the environment: `baltor failed`, `SSE error: Non-200 status code (401)`. |
| 15:03 | Run the quickstart's skill bootstrap block | Passed | Six files printed `OK` in staging and after copying; `client.json` created. `cp` printed a portability warning about `-n`. |
| 15:05 | First search, the quickstart's own prompt | Passed | The model called `baltor_intelligence_search` with `review inputs` and listed three references with digests. 3 calls. |
| 15:05 | Discover for the task | Passed | `changelog-composer` (MIT, Community) chosen; the model noted that two other hits needed `reads_secret`. 2 calls. |
| 15:05 to 15:21 | Retrieve with the quickstart's download prompt | Passed on the third start | Two starts stalled before any model request (600 and 150 seconds). The third loaded the library skill, saved a selection, fetched with a new request identity, installed and ran `verify`: `verified: true`. 7 calls. |
| 15:21 | Check that it worked | Passed | `verify` again by hand: `verified: true`, eight files. `opencode debug skill` lists `changelog-composer`. The account usage record shows the item. |
| 15:21 to 15:23 | Use the installed skill in a new session | Passed | The native `skill` tool loaded `changelog-composer`; the model read the Git history and the skill's references and wrote `RELEASE_NOTES.md`. Every entry matches a commit; the chore commit was left out. 8 calls. |
| 15:23 | Revise after one change request | Passed | The fix moved to its own entry, a Highlights line was added and the date became the last commit's date; nothing else changed. 3 calls. |
| 15:24 | Crash mid-task | Done | A second change request started; OpenCode was killed with `SIGKILL` at 15:24:47 after its first tool call. No file had been written. 1 call. |
| 15:25 | Revoke the key on `/account` | Passed | `Key revoked.` The session check answered 401 `unauthorized`; `opencode mcp list` showed `baltor failed` with 401. |
| 15:25 | Create a new key and reconnect | Passed | `opencode mcp list` showed `baltor connected` with the new key. |
| 15:26 to 15:27 | Continue the interrupted session | Partly passed | The session history survived the crash. The model wrote a correct Keep a Changelog `CHANGELOG.md`, but claimed that the interrupted run had already searched, reused files from the 15:20 download and wrote `f516fd1` for commit `f516cd1`. 6 calls. |
| 15:28 | Customer correction | Passed | The model ran `baltor_intelligence_search` with the new key and fixed the hash. The search for Keep a Changelog guidance returned unrelated Verified items (finding F-5). 3 calls. |

OpenCode stalled during start-up in 3 of 12 `opencode run` starts, each before
any model request; the stalls stopped at different start-up log lines. Final
files: `RELEASE_NOTES.md` SHA-256 `fa6f8725665664d1...` and `CHANGELOG.md`
SHA-256 `27a433d5f8fecb2b...`, both checked by hand against `git log`.

The documented OAuth route was run separately in a second clean environment.
`opencode mcp list` first reported `needs authentication`. `opencode mcp auth
baltor` printed the sign-in address (S256, resource `https://baltor.ai/mcp`,
callback `127.0.0.1:19876/mcp/oauth/callback`). The consent page named OpenCode
and three scopes; the callback carried a code and `iss`. OpenCode reported
`Authentication successful!` and the list showed `baltor connected`. Its stored
token then passed the protocol steps and was revoked. A first attempt did not
reach consent. Its captured address ended the resource with a terminal
box-drawing character that this record's own capture script had joined from
the next output line; the cause is inferred from that address, because the
helper's error text was not kept.

## Other harness connections

No model call was made for these. Each row used the journey account.

| Time (UTC) | Harness and route | Steps passed | Notes |
| --- | --- | --- | --- |
| 15:33 | Claude Code 2.1.301, native OAuth, `tools/check_quickstart_oauth.py` | 15 of 15 | `claude mcp add`, `login` and `list` with the real binary; challenge, discovery, consent, token, 12 tools, search, 2,861-byte download with matching digest, refresh rotation with the old refresh token refused, revocation. 31 seconds. |
| 15:37 | Codex, OAuth with `http://127.0.0.1:PORT/callback` | 15 of 15 | Registration, consent naming Codex, single-use code, 15-minute access token, protocol steps, refresh, revocation. |
| 15:44 | Codex 0.162.1, native `codex mcp add` | Passed | Codex printed `Detected OAuth support. Starting OAuth flow` and finished the sign-in itself; `codex mcp list` showed OAuth. Its stored token passed 7 of 7 protocol steps and was revoked. |
| 15:37 | Cursor desktop, callback `http://localhost:8787/callback` | 15 of 15 | Address as `oauth_authorization.py` documents it. |
| 15:38 | Cursor on the web, callback on `www.cursor.com` | 15 of 15 | The callback was answered inside the browser; nothing reached cursor.com. |
| 15:38 | VS Code, four registered addresses, port 33418 | 15 of 15 | |
| 15:38 | VS Code, a port VS Code would choose | 15 of 15 | A loopback port other than the registered one was accepted, as RFC 8252 allows. |
| 15:39 | ChatGPT, callback `chatgpt.com/connector_platform_oauth_redirect` | 13 of 13 | `search_library` returned 5 results and `download_package_files` delivered one file whose digest matched. The answers' top-level fields name no account and no execution record. |
| 15:41 | Claude Code, Codex, OpenCode, Pi and Baltor Harness quickstarts with the customer key, `tools/check_quickstarts.py` steps | 5 of 5 quickstarts | Each page matched its published recipe and named only listed tools. Pi's extension path: session, capabilities, hybrid search, manifest, 533-byte download, digest and header match. |
| 15:41 | Pi 0.73.1, `pi -p --baltor-check` | Passed | `Token: accepted`, three scopes, `Result: ready`, no model configured. The served extension's SHA-256 equals the repository copy. |
| 15:46 | Cursor and VS Code key entries | 6 of 6 each | One key each, sent with the entry's headers; both keys revoked on `/account` and refused with 401. |

Every connection outside the OpenAI presentation listed twelve tools,
including three staff tools.
`feedback_review` and `staff_work_read` answered `staff_role_required` to the
customer key.

## Account lifecycle

| Time (UTC) | Step | Result | Evidence |
| --- | --- | --- | --- |
| 14:31 | Sign up through Get started | Passed | Link email received, password chosen, signed in, then a new sign-in; 27 seconds in all. |
| 14:32 | Account page | Passed | Plan Pro, a founding place free each month; 0 of 10 keys; scopes shown. |
| 14:55 to 16:37 | Create and revoke Baltor keys | Passed | Four keys created and revoked; each revoked key answered 401. The list keeps revoked keys with their state. |
| 15:48 to 15:51 | Plans and checkout | Passed | `/api/v1/billing/plans` offered only Pro. The account page showed an Open secure checkout link to `checkout.stripe.com`, which showed "Subscribe to Agent Feeds + Harness Files", $49.00 per month, billed monthly, matching the pricing page. Two checkout sessions were opened and left unpaid. Basic is free through December 31, 2026 with no checkout, and Max is not sold in the preview, as the pricing page says. |
| 15:52 | Sign out and in | Passed | Sign-out called `/api/v1/account/logout`; the old browser token then answered 401; the account page showed Not connected; signing in again worked. |
| 15:53 | Password recovery | Passed | The link arrived from `mail.baltor.ai` in 8 seconds ("Set a new Baltor password"), opened "Choose a new password." and signed in. The old password was refused and the new one accepted. |
| 15:56 | Saved work and feeds | Not offered | The workspace, feeds and account pages have no saved collection or feed. Feeds are public links. |
| 15:56 | Data export and deletion | Not self-service | No export or deletion control. The privacy notice says deletion is by request to the contact address; no request was sent. |
| 16:38 | Final state | Recorded | 0 active keys; 3 counted uses across 3 items; signed out. |

## Model calls

Every call was `glm-5.3` on Ollama Cloud, requested and reported under that
name, with the usage the provider reported. All 35 answered status 200; none
was refused by the ceiling. Calls 1, 3 and 15 are OpenCode's session title
calls.

| Call | Step | Prompt tokens | Completion tokens | Finish | Tool calls |
| --- | --- | ---: | ---: | --- | ---: |
| 1 | model check | 541 | 177 | stop | 0 |
| 2 | model check | 6,948 | 3 | stop | 0 |
| 3 | first search | 549 | 368 | stop | 0 |
| 4 | first search | 9,571 | 61 | tool calls | 1 |
| 5 | first search | 11,321 | 276 | stop | 0 |
| 6 | discover | 11,685 | 126 | tool calls | 1 |
| 7 | discover | 14,636 | 858 | stop | 0 |
| 8 | retrieve | 15,534 | 70 | tool calls | 1 |
| 9 | retrieve | 16,752 | 864 | tool calls | 1 |
| 10 | retrieve | 17,623 | 34 | tool calls | 1 |
| 11 | retrieve | 24,250 | 465 | tool calls | 1 |
| 12 | retrieve | 25,793 | 201 | tool calls | 1 |
| 13 | retrieve | 27,318 | 152 | tool calls | 1 |
| 14 | retrieve | 27,625 | 172 | stop | 0 |
| 15 | use | 568 | 1,472 | stop | 0 |
| 16 | use | 9,714 | 75 | tool calls | 1 |
| 17 | use | 11,740 | 309 | tool calls | 2 |
| 18 | use | 12,208 | 250 | tool calls | 2 |
| 19 | use | 12,605 | 261 | tool calls | 3 |
| 20 | use | 15,621 | 1,481 | tool calls | 3 |
| 21 | use | 20,031 | 3,101 | tool calls | 1 |
| 22 | use | 23,141 | 120 | stop | 0 |
| 23 | revise | 23,338 | 1,254 | tool calls | 2 |
| 24 | revise | 24,913 | 451 | tool calls | 3 |
| 25 | revise | 25,384 | 79 | stop | 0 |
| 26 | crash mid-task | 25,536 | 1,943 | tool calls | 1 |
| 27 | continue after recovery | 28,666 | 1,572 | tool calls | 3 |
| 28 | continue after recovery | 30,438 | 263 | tool calls | 2 |
| 29 | continue after recovery | 31,674 | 1,876 | tool calls | 3 |
| 30 | continue after recovery | 41,514 | 2,576 | tool calls | 2 |
| 31 | continue after recovery | 44,559 | 1,030 | tool calls | 1 |
| 32 | continue after recovery | 45,598 | 349 | stop | 0 |
| 33 | correction | 46,046 | 1,177 | tool calls | 2 |
| 34 | correction | 50,172 | 1,623 | tool calls | 1 |
| 35 | correction | 51,803 | 474 | stop | 0 |

Totals: 785,415 prompt tokens and 25,563 completion tokens as reported, within
the owner's existing Ollama Cloud subscription. Prompt counts include context
that OpenCode reported as read from the provider's cache.

## Findings

| Id | Severity | Finding | Evidence | Status |
| --- | --- | --- | --- | --- |
| F-1 | Medium | The setup guide's entries were not the published recipes: `app.baltor.ai`, no `Baltor-Step-Effects` header and no Pi `step_effects`, so a step would hold `reads_fs` only. | `docs/guides/service-getting-set-up.md` at `f2ae304e`; `/assets/client-recipes.json` | Fixed in `d61bae09`, with a test and a known-wrong control |
| F-2 | Low | The serving guide listed five tools; a connection lists twelve, three of them staff tools. | `tools/list` answers above | Fixed in `d61bae09` |
| F-3 | Low | The session check returns `token_expires_at` `null` for a Baltor key, while the guides promised the expiry; the guide also omitted the `founding_free_monthly` and `free_monthly` access sources. | `/api/v1/session` with the journey key; `http.py` session handler | Guides fixed in `d61bae09`. Reporting the key's expiry in the record stays open for the access owner. |
| F-4 | Low | The Get set up page and the Codex offering page said to run `codex mcp login` after `codex mcp add`; Codex 0.162.1 signs in during `add`. | Codex run at 15:44 | Fixed in `cb9c7481` |
| F-5 | Medium | Lexical search ranks any Verified match above Community matches. "Keep a Changelog" returned a dedupe, a forecast and a URL skill first, although hybrid search finds changelog templates. The agent then told the customer the library had no such guidance. | `fuse()` and `TIER_ORDER` in `catalogue_search.py`; queries at 15:29 | Open. A ranking change needs the fixed-query comparison that the policy comment names before promotion. |
| F-6 | Low | Customer connections list three staff tools that always refuse a customer, which costs context in every harness. | Twelve-tool lists above | Open; already a remaining step in `docs/guides/chatgpt-app.md` |
| F-7 | Low | The signed-in workspace still says "Connect to search permitted material." and the library badge says "Sign in to browse" until something is loaded. | `service.js` line 236 sets the text and the connect path at line 396 leaves it; `catalogue-browser.js` line 268 sets the badge and `connectionChanged()` at line 276 leaves it | Open. The owning browser suite, `tools/check_service_workspace.mjs`, needs a new check and a full run. |
| F-8 | Low | The workspace shows "External identity flow qualified: no." to customers, while OAuth sign-in worked natively in Claude Code, Codex and OpenCode today. | `/app` screenshot; `protocol.external_authorization_flow_qualified` | Open; changing that qualification is a decision for its owner |
| F-9 | Low | The OpenCode bootstrap's `cp -R -n` prints a GNU coreutils warning. | Bootstrap output at 15:03 | Open on purpose: the portable replacement does not exist on BSD `cp`, and the fresh target folder already prevents an overwrite. |
| F-10 | Info | OpenCode 1.17.9 stalled during start-up in 3 of 12 runs, before any model request. | Logs in the evidence folder | Upstream behavior; recorded only |
| F-11 | Info | The model's recovery continuation was wrong once (stale files, skipped search, one wrong hash). | Steps at 15:26 and 15:28 | Model behavior; recorded only |

## Provider-side items for the coordinating session

- Return the founding place of the account with prefix `baltor-check-eab37f55`.
- The live Stripe product "Agent Feeds + Harness Files" describes itself as
  "Reviewed guidance, skills and reusable code for the coding tools you already
  run". Check that wording against the owner's public-copy rules for the word
  "reviewed".
- Stripe checkout does not prefill the account's email address. Decide whether
  the checkout session should pass it.
- This run made at least ten dynamic client registrations against the bounded
  ceiling of 128: six by the protocol checks, one by Claude Code, at least one
  by OpenCode and at least two by Codex. Codex's `codex mcp add` started four
  sign-ins; this run's time limits stopped three of them before consent.

## Evidence

The JSON records, OpenCode event transcripts, the model call ledger and the
screenshots are kept privately with the October 15 Claude takeover workspace,
in the `journey-evidence-20261016` folder. They hold no password, key, token
or code; a scan for the journey's secrets found none. The account state and
keys stay in the private journey folder under `~/.le-safety`.
