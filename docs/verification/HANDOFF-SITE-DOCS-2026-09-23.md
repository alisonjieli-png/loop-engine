# Handoff: the website Documentation view, September 23, 2026

Kind: dated handoff record for one line of work. Written by Claude Code
(Claude Opus 5.5) in session `81df4e9e` when the owner asked every line to
wrap up. It is a snapshot, not new authority. The owner's rules for
committing, pushing, branching and releasing are in the
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md, and the task authority stays
[roadmap.yaml](../roadmap/roadmap.yaml).

## State

Work in progress. The commit that carries this file is on a detached head in
the worktree `/home/username/.le-integration/site-docs`, made from `main` at
`243a8811` (Fly release 20). Nothing was pushed, deployed or opened live. Do
not merge it to `main` as it is: the browser suite fails one named check by
design until step 3 below, three restored tools are not written yet, and the
customer pages have not had their independent review.

## What the task was

Restore the website's Documentation pages that never reached `main`, in the
redesigned site, as merge plan step 9 of the
[branch content triage](BRANCH-CONTENT-TRIAGE-2026-09-23.md) asks:

- the Documentation view of `wave6/documentation-content` (`240c1270`, with
  `7aee2a1e` and `c402a16b`): a versioned index, built pages, the build and
  check tools, their tests, the guide `docs/guides/website-documentation-view.md`
  and the serving;
- the three customer pages as corrected in the prepared port
  `restore-d18-docs` (`bf3afdc`, `ca62214`): what Baltor is, your account,
  and usage and what you pay for.

The coordinator added four directions during the work, and they stand:

1. The setup guide is Get set up at `/setup`, with `/connect` kept as an
   alias. It is first in the Docs index. Pages link `/setup` where they send
   someone to set up, and never call the guide Get started.
2. Get started is the sign-up, registration and payment page at
   `/get-started`. The account and usage pages send a new customer there.
3. There is one setup guide. `/docs/getting-set-up` opens `/setup`, and what
   the Markdown guide has that `/setup` lacks goes to the owner of `/setup`
   as a short list.
4. Design: at 1440 by 900 every documentation page shows its title, a
   one-line summary and, when it is longer than three screens, a contents
   list in the first screen; the Docs index fits in two screens as a compact
   grid of cards; bands are 64 pixels deep on a wide screen and 40 on a
   phone, and no band is dark; each page's height is measured at 1440 and
   390 and reported. Every documentation page must be reachable from the
   index and work on `docs.baltor.ai`.

## What is done

1. `bf3afdc` and `ca62214` applied without conflict: the refusal status
   guard in `tools/check_service_documentation.py`, the three pages in
   `DOCUMENTED_PAGES`, the two new tests, and the `docs/README.md` and
   `docs/guides/README.md` rows. On this tree, before any content edit, the
   check held 677 documented facts with no finding and
   `tools/test_service_documentation.py` passed 25 of 25.
2. The index `src/loop_engine/core/service_runtime/web_assets/documentation-index.json`
   (`website_documentation_index/v1`, served at
   `/assets/documentation-index.json`): four sections and seven entries.
   Get set up is first and points at `/setup`, with the alias
   `/docs/getting-set-up`. Six entries are built pages at `/docs/<id>`.
3. `tools/build_documentation_index.py`, adapted from `240c1270`. It
   validates the index (exact version, known fields only, unique ids and
   addresses, a built page at `/docs/<id>` with its body at
   `/assets/docs/<id>.html`, summaries of at most 100 characters), converts
   each Markdown page into bounded HTML under `web_assets/docs/`, gives every
   heading an anchor, refuses a link anchor that names no heading, serves a
   link to `https://app.baltor.ai/<page>` as a same-origin link only when
   `web_pages.py` serves that page, turns a link to another repository file
   into its address on GitHub, read from the Homepage entry of
   `pyproject.toml`, and records the Markdown title and its `Kind:` line in
   `documentation_pages.json` instead of serving them. `--check` writes
   nothing and fails when a body or the record is stale.
4. Six built bodies under `web_assets/docs/` and the build record
   `src/loop_engine/core/service_runtime/documentation_pages.json`, built from
   the Markdown in this commit.
5. `web_pages.py`: one block of 20 rows: the six page addresses, the alias,
   `/setup`, `/get-started`, the index, the script, the stylesheet and the six
   bodies. Every row names a packaged file, so the existing boundary check
   `every_served_address_names_a_packaged_file` covers them.
6. `index.html`: the docs region is replaced in one hunk and nothing else in
   the file changed. It keeps `#docs-access`, the technical runtime reference
   word for word (`data-layer-notes` and the complete definition of a discrete
   cognitive or act step Loop node), and adds the card grid, the engine
   installation steps that Get set up promises, and the page view: a trail,
   the title, the summary, the list of pages, the page, its contents list and
   the previous and next links. The stylesheet and the script are linked
   inside the region so that the head is untouched.
7. `documentation.js`: reads the index only in its exact version, draws the
   cards, and at `/docs/<id>` fetches that page's body and rebuilds it element
   by element from an allowlist (headings with anchors, paragraphs, code,
   tables, lists, strong text and links whose address, target and rel are
   checked). A body that holds anything else is refused whole and the page
   says so. Links inside the view move through the site's history so a
   signed-in page keeps its sign-in. It sets the page title and opens the
   contents list on a wide screen.
8. `documentation.css`: the design above, from the tokens in `service.css`.
9. `service.js`: three lines. `/setup` and `/docs/getting-set-up` open the
   setup view, every other `/docs/` address opens the Documentation view,
   the view's title is Documentation, and the view is told when its address
   changes.
10. Content, in progress in two parallel edits that were stopped by the
    wrap-up (see the next section for what each reached).

### Where the customer copy stands

| Page | State in this commit |
|---|---|
| What Baltor is | Rewritten and shortened, 144 to 105 lines: the library is the harness family, 43 approved items with 34 offered by default because 9 declare effects, a section saying Baltor never runs a model, links to Get started and Get set up. Passes the facts check and Markdown lint. Not yet independently reviewed. |
| Your account | Rewritten, 211 to 204 lines: accounts by invitation with Get started at `/get-started`, the order of the four download checks, `access:manage` for operator work, the token policy as a table, "$29 a month", bring your own model. Passes the facts check and Markdown lint. The writer dropped "the link expires" because it could not verify it. Not yet independently reviewed. |
| Usage and what you pay for | Still the port from `ca62214`, and still wrong in the places listed under step 1 below. |
| Searching and retrieving, Serving and connections, Troubleshooting | Unchanged from `main`, so still stale and still carrying retired words, which the served bodies repeat. |
| Getting set up (Markdown, not served) | Unchanged from `main`. The website shows `/setup` instead. |

### Facts gathered for the remaining pages

A local instance of this worktree serving the real 43-item starter catalogue
was recorded on 2026-09-23 at 13:38 UTC, with the grants moved to a tenant
named `example-account` and a second tenant `account-without-grants`. The
recording, the script that made it and one public capabilities answer are in
`/home/username/.le-ci-tmp/site-docs-handoff/`, outside the repository. They
hold no credential (checked) and have had no independent review. What they
show:

- A search for "split address lines" returns
  `split_address_lines_into_components`, `source_layer` `harness_local`,
  3009 bytes; its manifest names the family `harness` and metering
  `required`; a wrong `expected_digest` answers 404 `item_unavailable`.
- A repeat download with the same `request_id` returns the same bytes and
  leaves usage at 1; an inline read with a new one takes it to 2; the usage
  record now carries `items`.
- Discover reports 34 items held and four never-metered entries; the list
  withholds 9 items that declare file access; an account without grants gets
  an empty list and a 404 manifest; a metadata-only token gets 403
  `insufficient_scope` on a download.
- An expired key gets 401 with `WWW-Authenticate: Bearer`; `GET /mcp` gets
  405 `protocol_method_not_allowed`; after 30 refused attempts the next gets
  429 `failed_attempt_limit_reached`.
- `initialize` for 2025-06-18 is answered with 2025-11-25; `tools/list` for
  2025-06-18 gets -32022 with both served versions; no version header gets
  -32020; an `Accept` without the event stream gets 406.
- The public capabilities record of the deployed service, read once without
  a credential: both protocol versions with library 2.2.0; the failed-attempt
  limit on at 30 in 60 seconds; request 65536 bytes, response 262144, 50
  search results, 8 operations at once and 4 for each account, nesting depth
  64, inline bodies 16384 bytes, downloads 1048576 bytes; checkout and the
  portal report true.

### What the Markdown setup guide has that /setup lacks

For the owner of `/setup`'s markup. Items 4 and 5 were not compared with the
notes in `client-recipes.json`.

1. Make one client token for each client or machine, with a label you will
   recognise.
2. A token is shown once and stored only as a digest; it carries at most the
   account's scopes and cannot create another token; it expires, and an
   expired or revoked token is refused on its next request.
3. Keep the token out of configuration files, repositories, tickets and chat;
   the variable name comes from `credential_variable` in
   `/assets/client-recipes.json`.
4. OpenCode: the service takes a token you supply, so do not start a login
   flow; the OpenCode 2.x layout is not published.
5. Claude Code: Pending approval means starting a session once in that folder
   and approving the server.
6. A command-line check with `curl` on `/api/v1/session`, and how to read
   `tenant_id`, `entitlement` and `scopes`; the check on `/setup` runs only in
   the browser after sign-in.
7. What a connection does not give you: no model, no model allowance and no
   spending; no permission to run code on your machine; downloads are
   `host_attested`, not independently checked.
8. Links onward to troubleshooting and to the full refusal table.

## What is left, in order

1. Finish the customer copy. The three new pages and the three served
   reference pages must be true against current `main` and the current
   deployment section of
   [MVP-CLIENT-SERVER.md](../architecture/MVP-CLIENT-SERVER.md), short and
   plain, with no retired word anywhere (the browser suite reads every served
   file). Known stale statements in the reference pages: the protocol facts
   still framed as local only, the failed-attempt limit said to be missing
   from the deployed image, `/api/v1/health` called liveness only, recorded
   answers that name `example.review_inputs` (no longer served) and the
   tenant names `pilot-owner` and `pilot-boundary`, and the source layer
   described as one of the four persistent layers. A refusal record now also
   carries `error.message`, `error.next_action` and `request_reference`, so
   every recorded refusal on these pages shows the old shape. The tables miss
   `tenant_concurrency_limit_reached` (429), `external_provider_capacity_reached`
   (503) and `nesting_limit_exceeded` (400), and the address table misses the
   account, waiting list, billing session, administration and webhook
   addresses. `intelligence_search` carries no read-only mark, so "the only
   tool not marked read only" is wrong. Codes raised through the catalogue's
   `_refuse(...)` helper (`item_withdrawn`, `package_file_not_found`,
   `package_files_unavailable`, `search_filter_not_allowed`) are not raise
   sites to `tools/check_service_documentation.py`, so a status row for one of
   them is refused: keep them in prose or extend the checker. The usage page
   still needs: a lower-case placeholder instead of `ITEM_IDENTITY`; "$29 a
   month"; the `items` field of `durable_tenant_usage/v1`; no release 16
   wording; `metered_unit` is null, not absent, when nothing was recorded; an
   accepted read is committed and durable, so `unknown` is not a success
   state; `/api/v1/download` returns bytes and `X-Content-SHA256` and no
   acknowledgment; a `request_id` belongs to one item (reusing it for another
   item answers 503 `meter_commit_unknown` on every retry on current main);
   the Get started link and the bring-your-own-model sentence; and drop the
   sentence about an undefined `metering_policy`, which is host setup. Then
   rebuild: `python tools/build_documentation_index.py --repository .`.
2. Write `tools/check_documentation_index.py` and
   `tools/test_documentation_index.py` for this layout, starting from
   `git show 240c1270:tools/check_documentation_index.py` and
   `git show 240c1270:tools/test_documentation_index.py`. The branch versions
   check the old layout and must not be copied as they are. Rules to hold,
   each with a known-wrong case and a removed-guard mutant: the index is
   valid; every page the guides index lists for a paying customer is named by
   the index (read the table, not the file names:
   `service-failure-diagnosis.md` is an operator guide); every index address,
   alias and body is a row of `WEB_ASSETS`, and every `/docs/` row and
   `/assets/docs/` row is named by the index; the alias routes to the view of
   its page; the built files are fresh; no built body or index text carries a
   word that terminology.yaml refuses on `website_documentation_view` (read
   with `resolved_terms` from `loop_engine.nomenclature_conformance`); and
   `check_service_documentation.check()` passes over the index's pages. Add a
   test that `DOCUMENTED_PAGES` equals the index's Markdown pages.
3. Browser suite, `tools/check_service_workspace.mjs`: add the nine new
   `/assets/` rows to `servedFiles`. Until then
   `every_served_asset_route_is_scanned_for_retired_words` fails by name,
   which is the check doing its job. Then add named checks, each with a
   removed-guard control served in memory: the index lists every entry in
   order with Get set up first and fits in two screens at 1440 by 900; every
   page opens directly and through a card, shows one header and one footer,
   its title from the index and its summary on one line, and at 1440 by 900
   its contents list in the first screen when it is taller than three
   screens; `/docs/getting-set-up` opens the setup view; a changed index
   version and a body with an element outside the allowlist are refused;
   back returns to the index; no page scrolls sideways at 390; the retired
   word scan and the contrast check include the pages. Screenshot every page
   at 1440 and 390, look at each, and record each page's height.
4. `src/loop_engine/core/service_runtime/http_checks.py`: the loopback check
   from `240c1270`, adapted: the index is served in its exact version, every
   body it names answers 200 as `text/html`, and an address no entry names
   answers `route_unavailable`. `http_checks.py` must stay under 800 lines.
5. `tools/check_hosted_website.mjs`: add `/docs` pages to the layout and
   retired word passes and the new assets to the byte comparison, so the
   release check covers every hostname, `docs.baltor.ai` included.
6. The guide `docs/guides/website-documentation-view.md`, starting from
   `git show 240c1270:docs/guides/website-documentation-view.md`, rewritten
   for this layout. It must record the rendering decision and its reason:
   the page is drawn inside `index.html` from the versioned index, so there
   is one header and one footer and every page address still returns
   `index.html`, as
   [the languages and components standard](../standards/LANGUAGES-AND-COMPONENTS.md)
   says; the served files stay under `web_assets/`, because the page table
   serves only from there and its checks read only that folder; and a body
   is rebuilt from an allowlist rather than inserted as markup, which keeps
   the page policy's `script-src 'self'` and `style-src 'self'` intact and
   keeps the site free of `innerHTML`. Update
   `src/loop_engine/core/service_runtime/web_assets/README.md` and the
   standard's script count at the same time.
7. The independent review of the customer copy: a reviewer that wrote none
   of it (a fresh Claude subagent, or Kimi or GLM through Ollama Cloud with
   model, usage and outcome recorded) checks each page against the source.
   Record the review, its findings and the fixes under `docs/verification/`.
8. Run the continuous integration set on an export of the final commit with
   `/tmp/claude-1000/-home-username-loop-engine/81df4e9e-adbc-4fcf-9636-2fadc680611e/scratchpad/ci-run-wt.sh`
   and `PY_OVERRIDE=/home/username/.le-wave2/mcp-revision/.venv-mcp2/bin/python`
   (the default virtual environment lacks `mcp.server.caching`), read every
   log, and run the mutants.
9. Records: this folder's review record, `python tools/build_records_index.py`,
   and the roadmap state for merge plan step 9.

## Checks run in this line, and their results

| Check | Result |
|---|---|
| `tools/check_service_documentation.py` after applying `bf3afdc` and `ca62214`, before content edits | 677 documented facts, no finding |
| `tools/test_service_documentation.py`, same tree | 25 of 25 passed, 111 seconds |
| `tools/build_documentation_index.py` on the Markdown in this commit, then `--check` | six bodies and the record written; `--check` exit 0 |
| `node --check` on `documentation.js` and `service.js` | both parse |
| `py_compile` on the builder and `web_pages.py` | both compile |
| Every `WEB_ASSETS` row names a packaged file; `/docs/your-account` and its body are served as `text/html` | yes, none missing |
| `tools/check_service_documentation.py` on the Markdown in this commit | 666 documented facts, no finding |
| `markdownlint-cli2` 0.23.2 on the six Markdown files this commit changes | 0 issues |
| Retired words in the six served bodies | six lines in three bodies: `troubleshooting.html` (2), `searching-and-retrieving.html` (3), `serving-and-connections.html` (1) |
| The test fixture texts on the three new pages | all three still present |

Not run in this line: the browser suite, the service self-test, the tools
suite as a whole, conformance, the hardcoding audit, Markdown lint of the
whole tree, and any check against a live hostname.

## Known failures and risks

- The browser suite fails `every_served_asset_route_is_scanned_for_retired_words`
  until step 3, and `no_served_file_carries_a_retired_word` fails while a
  served page carries a retired word.
- The hardcoding audit has not seen `tools/build_documentation_index.py`,
  which names `https://app.baltor.ai` and two address schemes. The branch
  needed two allowlist entries for the same kind of constants.
- Merge overlaps to resolve by hand: `/setup` and `/get-started` are added
  here to `WEB_ASSETS` and to the route table in `service.js` so that the
  index and the pages work in this tree; the owners of Get set up and Get
  started add the same rows, so keep one of each. The `route` line of
  `service.js` is one long line and any other change to it will conflict.
  The consolidation line `44a4b42` carries another refusal status guard
  (`685fdd3`); keep one, as merge plan step 3 of the triage says, and it
  also edits the serving and troubleshooting pages that this line corrects.

## Commands to continue

```bash
cd /home/username/.le-integration/site-docs
export TMPDIR=/home/username/.le-ci-tmp
PYTHONPATH=src .venv/bin/python tools/check_service_documentation.py --repository .
.venv/bin/python tools/build_documentation_index.py --repository .
.venv/bin/python tools/build_documentation_index.py --repository . --check
PYTHONPATH=src:tools .venv/bin/python -m unittest tools.test_service_documentation
PYTHON=.venv/bin/python node tools/check_service_workspace.mjs /home/username/.le-ci-tmp/browser-site-docs-1.json
```

In this worktree `.venv` links to
`/home/username/.le-wave2/mcp-revision/.venv-mcp2` and `showcase/node_modules`
to the main checkout's. `tools/architecture_report/node_modules` is an
untracked link; do not commit it.

## Live and external effects

None by the author of this record: no push, no deployment, no request to a
live hostname, no model call. One parallel writer made one unauthenticated read of
`https://app.baltor.ai/api/v1/capabilities` (status 200) at about 13:36 UTC
on September 23, 2026, and used no credential. It ran two local instances on
loopback ports; both stopped. The first failed on its host file before any
key was issued and left `/home/username/.le-ci-tmp/forkb-local-3myn92vx` (a
host file, a copy of the catalogue manifest and possibly an empty database,
no credential), which can be deleted.
