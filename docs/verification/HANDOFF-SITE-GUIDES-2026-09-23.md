# Handoff: the model, machine fit and refusal wording pages, September 23, 2026

Kind: dated handoff record for one work line, the site guides line. Written
by Claude Code (Claude Opus 5.5), a sub-agent of session `81df4e9e`, when the
owner asked every line to wrap up. It is a snapshot, not new authority. The
owner's rules for committing, pushing and releasing are in the
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md, and the task authority stays
[roadmap.yaml](../roadmap/roadmap.yaml).

## State in one paragraph

The work stopped at the analysis and design stage, before any change to
source, pages or checks. This commit holds three things only: this record,
its line in the [records index](../RECORDS-INDEX.md), and the three pieces of
uncommitted source work the task started from, saved as patch files under
[`artifacts/site-guides-sources-2026-09-23/`](../../artifacts/site-guides-sources-2026-09-23/).
Nothing new is served. No file under `src/` or `tools/` changed.

## The task as it was given

The coordinator gave four items, from the owner's words of September 23,
2026: "We need to get all of the pages that we built fully working and fully
live, there is no point in building a page if we can't show it. However, not
every page needs to be in the header."

1. Finish the three model guidance pages of `wave9/model-guidance` against
   current main and the owner's model direction of September 23: Baltor never
   runs models; customers bring their own model access, which is a local
   Ollama at 127.0.0.1, Ollama Cloud, another machine on their own network
   serving a local model, or a provider key. Serve them at `/models`, as one
   page or a short hub with pages under `/models/`, and write the reason down.
   Claim nothing about a model's quality or speed that saved evidence does not
   support. Leave a clearly marked place, with no number, for the overnight
   proof of Gemma 4 on Ollama Cloud that another session is measuring.
2. Bring `loop-engine machine-fit` of `wave10/machine-fit` onto current main,
   split under the length cap, reviewed, with its self-tests, and serve a page
   at `/machine-fit`. The page explains the command and offers a small picker
   (memory, graphics card, operating system) that gives the same advice as the
   command, from one shared and tested table rather than a second copy of the
   rules.
3. Land the refusal wording of `wave6/polish` (14 refusal codes and the next
   actions of `loop-engine report` refusals) without its `forbidden` entry,
   which repeats the 403 wording.
4. Decide whether `showcase/index.html` belongs on the website and write the
   reason down.

Site rules from the same task: the redesign's look and tokens, short plain
text, one call to action ("Get started" at `/get-started`, or a secondary
"Get set up" at `/setup`), no edit to the header or footer markup, new views
kept in one region of `index.html`, addresses added to `web_pages.py`, an
independent review of all customer copy recorded under `docs/verification/`,
route and view checks with removed-guard mutants, the full continuous
integration set on an export, and screenshots at 1440 and 390 pixels.

A later coordinator message added the owner's layout rule, "improve the
design so people don't have to scroll down so far to get all of the details":
at 1440 by 900 the heading, the lead line and the page's action sit in the
first screen; a page is at most 2,700 pixels tall at 1440 and at most six
screens at 390; details stand side by side in grids; band padding is 64
pixels on a desktop and 40 on a phone, with no dark band; the machine fit
picker and its answer are both visible without scrolling at 1440.

## Where the sources are

Each source is uncommitted work in a worktree of the shared checkout. The
branch commits themselves are already ancestors of main, so the branch names
carry nothing that main lacks. The patch files in this commit hold the
tracked changes and the untracked files of each worktree, read on September
23 at about 09:40 Eastern.

| Item | Branch | Worktree | Base revision | Patch file | Files | Applies to its base | Applies to `243a8811` |
|---|---|---|---|---|---|---|---|
| Model guidance | `wave9/model-guidance` | `.claude/worktrees/wf_cb91ffac-592-1` | `62d86761` | `model-guidance-wave9-uncommitted.patch` | 7 | yes | no (`index.html`, and `web_routes.py`, which main replaced with `web_pages.py`) |
| Machine fit | `wave10/machine-fit` | `.claude/worktrees/wf_eb5e10dc-951-1` | `fd5eeea1` | `machine-fit-wave10-uncommitted.patch` | 14 | yes | no (`__main__.py`, `_self_test.py` and others) |
| Refusal wording | `wave6/polish` | `.claude/worktrees/wf_bce6c2d4-baf-3` | `6e0ae3e2` | `refusal-wording-wave6-polish-uncommitted.patch` | 3 | yes | no (`_self_test.py`, `refusals.py`) |

Worktree paths are under `/home/username/loop-engine/`. The SHA-256 digests of
the patch files:

| Patch file | SHA-256 |
|---|---|
| `machine-fit-wave10-uncommitted.patch` | `2fccffa1fcdfba3f3ebe0c85eb48baed3afae9697d83eb8a3dc30116a996f779` |
| `model-guidance-wave9-uncommitted.patch` | `279293c6bb3fca002509af491f6697cbf61c8ddc0068c7c9f59b1140e2ed7a50` |
| `refusal-wording-wave6-polish-uncommitted.patch` | `8c1246a24b01a15f5944b0aa4d879f11ea3203a900549d1dcc7185f7033fd16b` |

A fourth, related source is not saved here: `wave9/subdomain-surfaces`
(worktree `.claude/worktrees/wf_cb91ffac-592-2`) builds a page at
`/suggested-models` from `tools/build_surface_pages.py`. It covers the same
ground as the model guidance: a building step and a deciding step need
different models, plus the one measured local call.

## What was found

### Model guidance

- The three pages are standalone HTML files with the header of the design
  before September 23, so serving them as they are would show a second,
  older header. The redesign's pages are views of `index.html` that share one
  header and footer.
- The two deep pages are far longer than the owner's height rule allows, and
  about half of each is settings of the local engine (fields of
  `loop-engine.settings.yaml`, route names such as `cloud.default`, the typed
  decision contract and the cost record fields). That is technical
  documentation, not a customer page, and it prints the command name, which
  the plain-word rule refuses (see the site constraints below).
- The only measured figures on the pages come from
  [the local model call record](../evidence/local-model-call-2026-09-21.md):
  `qwen2.5-coder:7b` at Q4_K_M on an NVIDIA GeForce RTX 3060 with 12288 MiB
  held 6659 MiB at a context of 32768; the first call took 87.28 seconds and
  the next two 0.71 and 0.78 seconds, because the first loaded 4.7 GB of
  weights. That record carries no rate and no quality judgement.
- The local model server on this workstation was read once, read-only, at
  `http://127.0.0.1:11434/api/tags` on September 23. It holds
  `qwen2.5-coder:7b` (4683087561 bytes, Q4_K_M), `nomic-embed-text`, and four
  models whose names end in `cloud` and whose `remote_host` is
  `https://ollama.com` (`glm-5.3-flash:cloud`, `deepseek-v4-flash:0731-cloud`,
  `kimi-k2.7-code:cloud`, `glm-5.2:cloud`). So Ollama Cloud models can be
  reached through the local Ollama server, which forwards the call. The
  repository's own Ollama Cloud adapter calls `https://ollama.com/api/chat`
  with the `OLLAMA_API_KEY` variable (`src/loop_engine/core/ollama_client.py`).
- The four checks of the wave9 module that fail on its own tip were not
  re-run here; the module is written against `web_routes.py`, which main no
  longer has.

### Machine fit

- `machine_reading.py` is 834 lines, over the cap of 800 in
  `src/loop_engine/forbidden_paths.json`. A split that follows its own
  sections keeps every part well under the cap: the reading records and the
  platform reads, the video device reads (the driver library, the vendor
  command and the kernel files), and the loopback read of a local model
  server with the cache element setting.
- `machine_fit_advice.py` (632 lines) and `machine_fit_cli.py` (365 lines)
  are under the cap. The patch also moves `local_fit.py` from
  `examples/30_overnight_local_run/` into `src/loop_engine/core/`, and that
  example folder has not changed on main since the patch's base, so the move
  still fits.
- The patch's own `web_routes.py` and its `http.py` hunk must be dropped:
  main moved the served address table to `web_pages.py` on September 21.
- The patch's regenerated conformance record showed `all_gates_pass` false:
  two unclassified files (`core/machine_reading.py`, `core/local_fit.py`) and
  one network gate finding. The new modules need their architecture map
  entries, and `machine_reading.py` needs its declared loopback network and
  command (`nvidia-smi`) adapters in `forbidden_paths.json`, as the patch
  drafted.
- Two design gaps block the page. First, the advice needs candidate models,
  and without a local server or a hand-named model it refuses with "no model
  was offered", so a web page has nothing to advise from. Second, a machine
  with memory shared between the processor and the graphics unit (Apple
  silicon) reads as having no video memory, so the command offers only a
  split placement for building and no answer for deciding, which is the wrong
  advice for that machine.

### Refusal wording

Main added the waiting list and catalogue entries at the place the patch
edits, so the `refusals.py` hunk no longer applies; the `run_history_cli.py`
part does. Each code was traced to where the service raises it and to the
status that `_status` in `http.py` gives it:

| Code | Raised in | Status | Recommendation |
|---|---|---|---|
| `account_unavailable` | `browser_identity.py`, when no account is bound to a verified sign-in | 401 | keep |
| `verified_customer_identity_required` | `browser_identity.py`, anonymous or unauthenticated sign-in | 401 | keep |
| `identity_subject_mismatch` | `browser_identity.py`, provider record differs from the token | 401 | keep |
| `browser_session_revoked` | `browser_identity.py`, a signed-out session reused | 401 | keep |
| `email_signup_requires_account_admission` | `BrowserIdentityConfiguration.__post_init__`, host configuration only | not reachable by a customer | drop: the module's own rule keeps the status wording for host configuration faults |
| `invalid_access_request` | `access.py`, eight shape checks on a token request | 400 | keep, after checking that the label, operation and lifetime fields are the ones the account page sends |
| `access_lifetime_exceeded` | `access.py` | 400 | keep, after checking that the account page shows the maximum lifetime beside its form |
| `invalid_expiry` | `runtime.py`, key issue, session revocation and operator entitlement | 400 | reword: the time is not always in minutes |
| `subject_not_found` | `runtime.py`, `revoke_subject` for another tenant | 400 | keep |
| `unissued_principal` | `runtime.py`, `_revalidate` | 400 | keep |
| `invalid_usage_request` | `runtime.py`, `record_usage` | 400 | keep |
| `invalid_selected_digest` | `provisioning.py` | 400 | keep |
| `not_found` | `runtime.py`, `_payload` for any record kind that is missing | 400 | reword: "search again" fits items only, and items use `item_unavailable` |
| `forbidden` | `http.py` status list | 403 | drop, as the triage said: it repeats the 403 wording |

One more finding: the existing `entitlement_required` wording, which a
customer can meet, says "ask for a beta invitation", and the owner retired
that word on customer pages. Changing it to "ask for an invitation" belongs
with this item.

### The showcase

`showcase/index.html` is the player of a 26-slide canvas presentation titled
"Loop Engine architecture showcase", with the subtitle "Loops are all you
need." Its data file names Practitioner, Intelligence and Solution Loops on
most slides, and its README calls it a dated architecture snapshot of August
25, 2026 that is not a current test report.

Decision: it does not belong on the website. The reasons:

1. Almost every slide shows the runtime words that the owner keeps off the
   public pages, and the browser suite's plain-word scan would refuse it on
   any customer page.
2. It describes the architecture of August 25, including the in-process
   execution path that the harness-first direction of September 21 parked, so
   it would present a product the website no longer offers.
3. It is a presentation for engineers and reviewers, not a page a customer
   acts on, and it would need its player, its canvas and its module script
   admitted under the site's content policy.

Where it should live: where it already is, in the repository under
`showcase/`, linked from the [documentation index](../README.md) as the
architecture presentation. If it is ever published, publish its exported PDF
or video as a dated asset of a GitHub release, labelled as the snapshot of
August 25, 2026.

### Site constraints found on main at `243a8811`

- `/get-started` and `/setup` are not in `WEB_ASSETS`. The self-test check
  `every_internal_address_on_the_page_is_served` in
  `src/loop_engine/core/service_runtime/http_checks.py` fails on any link in
  `index.html` to an address the table does not serve, so a new view that
  links to either fails the self-test until those addresses are served. The
  uncommitted work in `/home/username/.le-integration/r22-ui` adds both, with
  the comment line "The guide, Get set up, and the sign-up funnel, Get
  started".
- The router in `service.js` keeps its address table (`routeNames`) and its
  title table (inside `route`) on two single lines, and the r22 work edits
  both. A new view that edits those lines will conflict with it.
- The plain-word rule `internalTerms` and the stricter `publicVocabulary` in
  `tools/check_service_workspace.mjs` match the command name `loop-engine`,
  because the word boundary falls at the hyphen. Only the `/docs` view is
  exempt. A page that prints `loop-engine machine-fit` fails
  `no_customer_page_uses_the_runtime_vocabulary` as the scan stands.
- The page policy is `script-src 'self'` and `style-src 'self'`, so a picker
  needs its own script file and no inline style. Every new `/assets/` address
  must also be added to `servedFiles` in `tools/check_service_workspace.mjs`,
  or `every_served_asset_route_is_scanned_for_retired_words` fails.
- The shared checkout's virtual environment has `mcp` 1.29.1, which lacks
  `mcp.server.caching`, so a local service started with it fails in
  `_sdk_server`. The coordinator's CI exports use
  `/home/username/.le-wave2/mcp-revision/.venv-mcp2` (`mcp` 2.2.0).

Heights of today's pages, measured on a local service built from `243a8811`,
full page, light theme, in pixels:

| Page | 1440 by 900 | 390 by 844 |
|---|---|---|
| `/security` | 2057 | 3086 |
| `/pricing` | 2090 | 3450 |
| `/connect` | 3263 | 5077 |
| `/docs` | 2649 | 3934 |
| `/examples` | 1953 | 2724 |

## Decisions made, with the reason for each

| Decision | Reason |
|---|---|
| `/models` is one page, not a hub with pages under `/models/` | The owner's height rule and side-by-side grids fit one page; the four ways to bring a model apply to both kinds of step, so one grid shows them once; the engine settings in the deep pages belong in technical documentation; one page needs half the checks. |
| The pages are views of `index.html` | They then share the one header and footer and the redesign's tokens, and no second copy of the header can drift. |
| New views go after the security view, at line 304 of `index.html` | The r22 work edits lines 296, 303 and 322 but none between 304 and 321, so an insertion there does not touch its hunks. |
| Each new view declares its addresses and title in its own markup (`data-routes`, `data-title`) | One small block in `service.js`, placed between the `/auth/callback` block and `const serviceName`, reads them into `routeNames`, and a mutation observer on the body's `data-page` writes the title after `route` runs. Neither of the two lines the r22 work edits is touched, and the next page added this way needs no router edit. |
| Styles go in a new `guides.css`, not at the end of `architecture.css` | The r22 work appends to the end of `architecture.css`. |
| The picker reads a table generated from the command's own advice | A reference list of openly published models (Qwen family first, whose full-attention layout the cache formula describes exactly) with their shapes and sources, plus the declared policies of the advice module, produce one JSON table for every picker choice. A test regenerates it and compares; the page script only looks rows up and holds no arithmetic. The command prints the same reference advice for a described machine. |
| Shared memory machines use two thirds of system memory as the graphics budget, declared | The overnight guide already declares the same share for its 16 GiB unified memory laptop tier. It is a declared policy, printed beside the word declared, not a reading. |
| Refusal wording drops `forbidden` and `email_signup_requires_account_admission`, and rewords `not_found` and `invalid_expiry` | See the table above. |
| The showcase stays in the repository | See the showcase section above. |

## What is left, in order

1. Refusal wording. Add the eleven kept entries of the table above to
   `CODE_GUIDANCE` in `refusals.py` after the catalogue entries, with the two
   rewordings; change "beta invitation" in `entitlement_required`; add a
   check that no code entry repeats its status wording, with a mutant that
   restores `forbidden`; add `run_history_cli` and its next actions from the
   patch, and register `run_history_cli` in `_FOLDED_SUBMODULE_TESTS`.
2. Machine fit command. Apply the patch's `local_fit.py` move and its
   example and guide edits; split `machine_reading.py` into three modules
   under the cap; add the new modules to the architecture map, the self-test
   list and the declared adapter lists in `forbidden_paths.json`; add the
   `machine-fit` entry to `cli_help.py` and `__main__.py`; drop
   `web_routes.py` and the `http.py` hunk; review every guard against its
   known-wrong input; regenerate the conformance record.
3. The shared table. Add a reference model list with a source and a reading
   date for every figure (weights file bytes from the Ollama registry
   manifest of the exact tag; layers, key and value heads, head dimension
   and context from the model's published configuration), the picker's
   choices, the shared memory policy, and a generator that writes
   `web_assets/machine-fit-table.json`; test that the packaged table equals a
   fresh run, with a mutant that edits one row.
4. The views. `/models` and `/machine-fit` in `index.html` after the
   security view; `guides.css`; `machine-fit.js` for the picker; addresses in
   `web_pages.py` (`/models`, `/machine-fit`,
   `/assets/guides.css`, `/assets/machine-fit.js`,
   `/assets/machine-fit-table.json`); the router block in `service.js`. The
   `/models` page carries a marked place for the Gemma 4 overnight result
   with no number in it, and a check that the place holds no digit until an
   evidence record exists.
5. Resolve the two open site constraints with the coordinator: serve
   `/get-started` and `/setup` (either with the r22 merge or with the same
   table line in this change), and choose how the machine fit page shows the
   command name under the plain-word rule (for example a narrow exemption for
   `code[data-command]` elements, held by a check that such an element holds
   nothing but the command).
6. Checks. Route and view checks for both pages in
   `tools/check_service_workspace.mjs` and `tools/check_hosted_website.mjs`,
   each with a removed-guard mutant; add the new addresses to
   `accessJourneyPaths`, `servedRoutes` and `servedFiles`; add both pages to
   the responsive loops.
7. The independent review of all customer copy by a reviewer that did not
   write it, recorded under `docs/verification/`.
8. Screenshots at 1440 and 390, the height of each page at both widths, and
   the layout fixes they show.
9. The full continuous integration set on an export of the commit, then the
   commit.

## Checks run, and their results

No repository check ran on a change of this line, because this line changed
no source. These ran:

| Check | Result |
|---|---|
| Each saved patch against its own base, with `git apply --cached --check` on a temporary index | 3 of 3 apply |
| Each saved patch against `243a8811` | 0 of 3 apply, as listed above |
| A local service from `243a8811` with the shared checkout's environment | failed: `ModuleNotFoundError: No module named 'mcp.server.caching'` |
| The same with the `mcp` 2.2.0 environment | started; five pages screenshotted at two widths, no horizontal overflow on any |
| `markdownlint-cli2` 0.23.2 on this record and the records index | 0 issues in 2 files |
| `tools/build_records_index.py --check` after regenerating the index | current |
| `tools/test_build_records_index.py` and `tools/test_context_routes.py` | 27 tests, OK |
| The retired word search of the CI set, on this record | no match |
| The hardcoding audit as CI runs it, with this commit's files staged | exit 0, no new high finding (2672 files scanned) |

The coordinator's own continuous integration run on `243a8811` (logs in the
session scratchpad, folder `ci-243a8811d9aeb210fedc6d37578e9c7154887448`)
is the baseline for this line: 11 of 12 stages exited 0. The browser suite
passed 495 of 495 with 76 of 76 mutants detected. The self-test passed 3224
of 3225; the one failure was
`a_request_in_flight_finishes_on_the_view_it_started_with`, which was not
investigated here.

## Known failures

None introduced by this commit. The base revision's one self-test failure is
named above.

## Commands to continue

```bash
# The worktree of this line, at this commit, with the environment the CI exports use
git -C /home/username/loop-engine worktree add --detach /home/username/.le-integration/site-guides-next <this commit>
ln -sfn /home/username/.le-wave2/mcp-revision/.venv-mcp2 /home/username/.le-integration/site-guides-next/.venv

# Check a saved source patch against its own base without touching any worktree
GIT_INDEX_FILE=/tmp/base.index git read-tree 6e0ae3e2
GIT_INDEX_FILE=/tmp/base.index git apply --cached --check artifacts/site-guides-sources-2026-09-23/refusal-wording-wave6-polish-uncommitted.patch

# A local service for screenshots, and the full continuous integration set on an export
PYTHONPATH=src .venv/bin/python <scratchpad>/site-guides/serve.py
PY_OVERRIDE=/home/username/.le-wave2/mcp-revision/.venv-mcp2/bin/python bash <scratchpad>/ci-run-wt.sh <revision>
```

`<scratchpad>` is
`/tmp/claude-1000/-home-username-loop-engine/81df4e9e-adbc-4fcf-9636-2fadc680611e/scratchpad`;
`site-guides/serve.py` and `site-guides/shoot.mjs` there start a local
service and take full-page screenshots at both widths with their heights.

## Live and external effects

None. Nothing was pushed, deployed or published, no model or provider was
called, and no account, key or record changed. Two reads left the process:
`git ls-remote origin main`, which showed `243a8811` at the head of main, and
one read of the local model server's list at `127.0.0.1:11434`. Local effects:
the detached worktree `/home/username/.le-integration/site-guides`, a `.venv`
link inside it that git ignores, and a local service on a loopback port that
was stopped.
