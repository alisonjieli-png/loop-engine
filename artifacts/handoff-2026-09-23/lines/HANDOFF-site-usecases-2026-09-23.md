# Handoff: use case pages, status page and hostname surfaces, September 23, 2026

Kind: dated handoff record for the next session. Written by Claude Code
(Claude Opus 5.5) in the detached worktree
`/home/username/.le-integration/site-usecases`, started from `243a8811`
(main, live as Fly release 20). It is a snapshot, not new authority. The
owner's rules for committing, pushing and releasing are in the
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md.

The owner asked for the work to stop here: "Document all of your work, get
everything merged to main branch ... you are almost out of usage". This
commit is work in progress. It must stay a patch until the steps below are
finished. It is not safe to merge to main as it is (see "Known failures").

## The task

The owner, September 23, 2026: "with the new design you removed so many
header pages, footer pages, and other things. You need to recover those and
work that into the new and improved design." This line restores:

1. The four pages about what changes (`/overnight`, `/context`,
   `/model-choice`, `/tool-choice`) and the four audience pages
   (`/for/coding-agents`, `/for/engineering-teams`, `/for/comparing-tools`,
   `/for/protocol-and-client`) from the unmerged website line (tip
   `44a4b426`).
2. A new hub, `/use-cases`, listing those eight pages as short cards.
3. The overnight views of the branch `wave8/overnight-pages`, reconciled with
   `/overnight` into one page.
4. The status page of the branch `wave10/status-page` (`status.py`), with its
   route `/status`, reading the existing health record.
5. Hostname surfaces: the root of `docs.baltor.ai` shows the Docs view,
   `status.baltor.ai` the Status view, `examples.baltor.ai` the First example
   view, `demo.baltor.ai` the demonstration of one step, and `app.baltor.ai`
   the Workspace. `baltor.ai` and `www.baltor.ai` stay the homepage. Every
   other address serves the same page on every hostname, and every page names
   `https://baltor.ai/<address>` as its canonical address.

Directions received while the work ran, from the coordinating session, which
the next session must follow:

- Every benefit page, audience page and the hub carries one primary action,
  "Get started", linking `/get-started`, in every access state. Another agent
  builds the sign-up, registration and payment funnel at `/get-started`; it
  handles invitation-only itself. The old `/connect` guide becomes "Get set
  up" at `/setup`. A secondary text link "Get set up" (`/setup`) is fine where
  a page talks about connecting a harness. The primary action must therefore
  not carry `data-access-state`, because `service.js` rewrites every element
  with that attribute to the access-state label.
- The owner: "We need to get all of the pages that we built fully working and
  fully live, there is no point in building a page if we can't show it." Every
  page must be reachable from the footer, the `/use-cases` hub or another page.
- The owner: "improve the design so people don't have to scroll down so far
  to get all of the details." At 1440 by 900 the headline, the lead line and
  the one "Get started" action sit in the first screen. Each page is at most 3
  screens (2,700 pixels) tall at 1440 wide and at most 6 screens at 390 wide.
  Band padding is 64 pixels on a desktop and 40 on a phone. Details go side by
  side in grids, not stacked. No dark bands. Measure each page's height at
  both widths and report it.
- Do not edit the header or footer markup; the UI agent (worktree `r22-ui`)
  owns them, the homepage, Get started and the shared styles. Keep changes to
  `index.html` in contiguous regions. Report the header and footer links the
  pages need (listed at the end of this record).

## What is done in this commit

- `src/loop_engine/core/service_runtime/web_pages.py`:
  - Served addresses for the hub, the eight pages, `/status`, `/demo`,
    `/get-started` and `/setup` (all `index.html`), and two new assets,
    `/assets/public-pages.css` and `/assets/public-pages.js`. The two asset
    files do not exist yet (see "Known failures").
  - A typed, versioned hostname surface map: `WebSurface`, `WebSurfaceMap`
    (record `service_web_surface_map/v1`), read once from
    `web_surfaces.json` by `web_surface_map()`. The map refuses another
    record version, an unknown or missing field, a hostname with a scheme,
    port or wildcard, a hostname named twice, a root that is not an
    application page this service serves, and a canonical origin that is not
    `https://` and one hostname of the map whose root is the homepage.
    `root_address(host)` ignores the port and letter case and answers `/`
    for a hostname the map does not name.
  - `served_asset(path, method, display_name, host=None)` now writes a
    `<link rel="canonical">` into every served page, and at the root of a
    surface hostname a `<meta name="baltor-root-address">` naming the
    address whose view the root shows. `with_page_address` refuses a page
    without exactly one closing head tag.
- `src/loop_engine/core/service_runtime/web_surfaces.json`: the map itself,
  with the seven hostnames above and the canonical origin
  `https://baltor.ai`. `baltor-pilot.fly.dev` is left out on purpose, so its
  root stays the homepage and its pages name `baltor.ai` as canonical.
- `src/loop_engine/core/service_runtime/status.py`: the public status record
  `service_status/v1`, built only from the one `service_health/v2` record
  that `observability.readiness_report` produces. It is not a second producer
  of the health record (the draft's `health()` method and its in-memory
  observations were not restored). Five customer parts: search and
  downloads (the health record's own `ready`), the library
  (`catalogue_registered`, `catalogue_view_current`), this website
  (`interface_page_readable`), signing in (`browser_identity_installed`,
  called "set up", never "working", because nothing contacts the provider)
  and payment (`billing_sessions_installed`, `billing_policy_current`). A
  closed vocabulary and `verify_publishable`, which withholds a record that
  carries any other text, keep release names, catalogue identities, refusal
  codes and provider messages off the public page. No history is kept, so no
  uptime is reported. Nothing calls it yet.

## Decisions taken, and why

- The eight pages and the hub are views of the one application page, not the
  standalone `campaign-*.html` files of the line. Reasons: they then share the
  UI agent's header and footer instead of carrying copies that drift (the
  line's own rule `shared_footer_addresses_missing` failed after every footer
  change), they get the redesign's styles, and a script-free standalone page
  could not follow a changing action. So `campaign-*.html` and `campaign.css`
  do not come back as files; their words come back as views.
- No attribution. `campaigns.js` (the page comparison that stored
  `baltor.page-comparison` in the visitor's browser), `campaigns.json` (the
  published names that sign-up used to attach a campaign name to an account)
  and the sign-up `campaign` field of `e7734bb` stay out until the owner
  revises the privacy notice, which says the site runs no analytics or
  tracking scripts. The primary action carries no campaign name.
- The line's `web_campaigns.py` becomes `web_use_cases.py` (not yet written):
  typed records of the nine pages and the rules each view must satisfy,
  adapted from the line's `campaign_page_problems`. The word campaign is
  dropped because no campaign name travels any more, and because the
  repository uses campaign for benchmark campaigns.
- Hostname surfaces serve the surface page at the root address rather than
  redirecting (the `wave9/subdomain-surfaces` draft redirected the root with
  302). The task says the root shows the view, the roadmap adversarial case
  of S-6.33 says "a subdomain that serves the homepage byte for byte must
  fail", and every page names its canonical address, which a redirect would
  not need. On a surface hostname the page script must send the homepage
  links (the brand and Library, `a[data-page="home"]`) to the canonical
  origin, because `/` on that hostname is the surface.
- The map is a packaged JSON record with a typed Python reader, not a host
  file setting, so it takes effect with a release and needs no change to
  `/data/host.json`; the node checks read the same file, so no script keeps
  its own list of hostnames. The canonical origin is in the map because the
  host file's `public_base_url` still names `baltor-pilot.fly.dev`.
- `demo.baltor.ai` shows a new address, `/demo`: a short page whose script
  moves the homepage's own `[data-step-demo]` element into the page and back,
  so the demonstration is not copied and the homepage checks of it stay
  valid. The styles of `.step-demo` are not scoped to the hero band, so the
  move keeps its look.
- The status page reads a new public route, `GET /api/v1/status`, which
  answers 200 with `service_status/v1` whether or not the service is ready.
  `/api/v1/health` answers 503 when not ready, which the page script's
  shared `request()` helper throws away. The route costs what the health
  question costs; both are public.
- Public pages print no `loop-engine` command. The browser check's runtime
  word rule matches "loop" in `loop-engine`, and the command name is an open
  owner decision in `terminology.yaml`. `/overnight` therefore says what the
  overnight command does in plain words.

## What is left, in order

1. `http.py`: pass `request.headers.get("host")` to `served_asset` in
   `_web_route`; import `STATUS_RECORD_PATH` and `status_report` from
   `.status`; add `STATUS_RECORD_PATH: ("GET",)` to `API_ROUTES`; add
   `elif path == STATUS_RECORD_PATH and method == "GET": output =
   status_report(await self._readiness())` right after the health branch.
   The check `the_route_table_names_every_address_the_router_answers` picks
   the constant up because its name appears in `_web_route`.
2. `architecture_map.py`: add `status`, `web_use_cases` and
   `web_page_checks` to `MODULE_MAP["core.service_runtime"]` on a line of
   their own; regenerate with `python -m loop_engine --map >
   src/loop_engine/ARCHITECTURE-MAP.md` and the conformance manifest.
3. `index.html`: after the `architecture.css` link, add
   `<link rel="stylesheet" href="/assets/public-pages.css">` and
   `<script defer src="/assets/public-pages.js"></script>`. Add one
   contiguous block of views between the privacy view and the docs view.
   Each view line must start with exactly four spaces and
   `<section data-view="..."`, or the nomenclature gate does not see the
   region. Views: `use-cases`, `overnight`, `context`, `model-choice`,
   `tool-choice`, `for-coding-agents`, `for-engineering-teams`,
   `for-comparing-tools`, `for-protocol-and-client`, `status`, `demo`. Put
   the page title in `data-title` on each view. Layout: the intro band
   (`page-intro`) holds a trail link back to `/use-cases`, one `h1`, the
   `lede`, the one primary action `<a class="button primary"
   href="/get-started" data-page="get-started">Get started</a>` and the price
   line "Search is free. Baltor Pro is $29 a month."; then a real limit
   sentence (`data-limit`) on the four benefit pages; then cards in grids
   (four columns on a desktop, one on a phone); then a small source caption
   with file names in `code` elements.
4. `service.js`: one block after `routeNames`. Add each new address only when
   `routeNames` does not already hold it, so another agent's mapping of
   `/get-started` or `/setup` wins after a merge. Read
   `meta[name="baltor-root-address"]`; when it names another address, map
   `/` to that address's view and rewrite every `a[data-page="home"]` to the
   canonical origin with its `data-page` removed (before the click handlers
   are bound on the line that binds `[data-page]`). Change the one line of
   `route()` that sets the title to fall back to the shown view's
   `data-title`.
5. `public-pages.js`: a `MutationObserver` on `body[data-page]`. On `status`,
   fetch `/api/v1/status`, read only `service_status/v1`, and render the
   summary, the time and one card for each part with its label and, for a
   limited or broken part, what stops and what still works; say plainly when
   the record could not be read. On `demo`, move `[data-step-demo]` into
   `[data-demo-slot]`; on any other view, put it back where it was. On every
   view, update the canonical link to the canonical origin and the shown
   address.
6. `public-pages.css`: styles scoped to the new views, built only from the
   tokens in `service.css` and `architecture.css`: light bands, 64 pixels of
   band padding on a desktop and 40 on a phone, card grids, no dark band.
7. `web_use_cases.py` and `web_page_checks.py` (run from
   `http_checks.self_test`, like the other check modules): each view has one
   `h1`, exactly one primary action to `/get-started` labelled Get started
   and without `data-access-state`, the price line, no runtime word (the
   `publicVocabulary` rule and `terminology.yaml`), no retired word, only
   served internal addresses, no absolute address, no dated protocol version
   the service does not speak, the client qualification sentence where a
   page names a client whose recipe says "native end-to-end qualification is
   pending" (all three do today), and a real limit on each benefit page. The
   hub lists the eight pages in record order. Surface checks: the map
   refusals above; the docs hostname root serves bytes that differ from the
   main root and name `/docs` (the S-6.33 adversarial case); every other
   address serves identical bytes on every hostname; an unnamed hostname
   gets the homepage; `WEB_ASSETS` holds no address twice (a merge of the
   funnel work may add `/get-started` again). Status checks: a ready record
   reads working; a failed required check reads not working; a failed
   catalogue refresh reads limited; a deadline report reads not measured; a
   planted foreign string is withheld; the route answers 200 over a real
   socket with `service_status/v1`. Each new guard needs a removed-guard
   control that must be detected.
8. Both `terminology.yaml` copies: claim the new views under
   `public_website_pages`, whose enforcement is `checked`.
9. Restore `tools/check_benefit_page_sources.py` and
   `tools/test_benefit_page_sources.py` from `44a4b426`, with the new view
   names and the new citations.
10. Browser checks, in a module imported by `tools/check_service_workspace.mjs`
    so the large file changes in one place: each page opens at its address,
    the first screen at 1440 by 900 holds the `h1`, the lead and Get started,
    the height budgets hold at 1440 and 390, nothing scrolls sideways at 390
    or 320, the vocabulary scans cover the new routes and
    `/assets/public-pages.*` (the list `servedFiles` must name them), the hub
    links work, the status view renders the fixture's record and refuses
    another version, the demo moves and returns, and a second browser
    launched with `--host-resolver-rules` opens the surface hostnames against
    the fixture (the fixture needs `hostname:port` values in its allowed
    hosts). `tools/check_hosted_website.mjs` must read `web_surfaces.json`:
    on `app.baltor.ai` the root is now the Workspace, so its homepage checks
    run only where the map gives the root as `/`.
11. Documents: `docs/guides/public-website-content-and-domain.md`, a guide
    for the use case pages (the line's `campaign-landing-pages.md` no longer
    fits), the route table of `docs/components/service-runtime/README.md`
    (`/api/v1/status`), `web_assets/README.md`, and after release the
    hostnames row of `docs/architecture/MVP-CLIENT-SERVER.md`.
12. Screenshots of every page at 1440 and 390; fix spacing; record heights.
13. An independent review of the customer copy (a reviewer that did not write
    it: a separate Claude subagent, or Kimi or GLM through Ollama Cloud with
    model, usage and outcome recorded), saved in `docs/verification/`.
14. The full continuous integration set on an export, then commit.

## Draft content for the pages, with the facts checked so far

Checked against source at `243a8811` and the live capabilities record:

- A search reference carries identity, kind, purpose, digest, source, size,
  licence and declared effects, and `body_included` false
  (`provisioning_list/v2`). The capabilities record says `returns_bodies`
  false, `requires_reauthorization` true, retrieval `lexical` and `hybrid`
  with `deterministic_character_hash`, and no semantic embedding model.
- The model gateway refuses a request whose estimated input plus requested
  output exceeds the route's declared context window before the provider is
  contacted (`context_window_preflight_refused`, `model_gateway.py`). Routes
  declare a locality (`cloud`, `organization`, `local`) and purposes
  (`model_routes.py`). Unknown usage stays unknown.
- `instance_instructions.py` writes one instruction file from typed fields,
  refuses a section naming an effect the step does not hold, never replaces
  a file without its marker, and records a digest.
- The overnight command (`loop-engine overnight check`, `start`, `resume`,
  `report`, in `overnight_cli.py`) is live and its checks run. `check`
  asks the server whether it answers, holds the model, reports a context
  length, and whether weights, cache and reserve fit the declared video
  memory; it starts nothing. A night runs within declared hours, model calls
  and folders; a failure becomes a typed next action; it ends only for a
  checked result, spent authority, a question for the person, a cancellation
  or a recorded outage; every effect is written before it happens, so a
  resume repeats only what was declared repeatable. Parked modules
  (`run_checkpoint.py`, `night_budget.py`, `step_state.py`,
  `overnight_outcome.py`, `solve_terminal.py`) are imported by it; cite only
  the live ones (`overnight_cli.py`, `overnight_authority.py`,
  `overnight_journal.py`, `overnight_night.py`). `loop-engine solve` is
  parked (`solve_cli.py`), so the `wave8/overnight-pages` command guides,
  which use it, cannot be restored as they are.
- The residency finding has an evidence record,
  `docs/evidence/local-model-call-2026-09-21.md`: one machine (RTX 3060,
  12288 MiB), `qwen2.5-coder:7b` at Q4_K_M, first call 87.28 seconds while
  loading the weights, next two 0.71 and 0.78 seconds.
- Protocol: Model Context Protocol over streamable HTTP; `2025-11-25`
  through the `initialize` handshake and `2026-07-28` named in every
  request; stateless; a bearer header; one endpoint `/mcp`.
- `client-recipes.json` names Codex, OpenCode 1.x and Claude Code, credential
  variable `BALTOR_SERVICE_TOKEN`; all three say native end-to-end
  qualification is pending.
- Personal client keys: the live record reports `client_access_available`
  true. Accounts are provisioned by the operator; public registration is
  closed. One account holds one person's keys; team billing, team
  administration and adding a team's own material are not built.
- The line's pages carried claims that no longer hold and must not come back:
  "Version 2025-11-25, refused when a client offers another one" (two
  versions are served now), and the engineering teams card saying a team's
  own "methods, checklists ... sit together" in the library.

Page drafts (titles, headlines and cards), short:

- `/use-cases`, "Use cases": two card groups, "What changes" (Overnight work,
  Being built; Less in each request, Available now; Model choice, Being
  built; Tool choice, Being built) and "Who it is for" (the four audience
  pages), and a link to `/demo`.
- `/overnight`, "Overnight work": "Leave a long task running overnight."
  Limit: it runs in the part you install, on your machine and your model;
  Baltor's service keeps and serves material and does not run your work.
  Cards: check before you start; write down what the night may do; keep
  going after a failure; resume without repeating. Panels: keep one model
  loaded (the evidence record above, and the Ollama keep time and context
  length); what we are aiming for.
- `/context`, "Less in each request": "Send each step only what it needs."
  Cards: references, not bodies; a file only after a choice; refused, not
  cut short; plain about search.
- `/model-choice`, "Model choice": "Match each step to the model it needs."
  Limit: comparing existing code, a small and a large model for each step is
  written and not connected to a live run yet. Cards: every route declares
  itself; a policy on the gateway; refused before it is sent; unknown stays
  unknown. Baltor never runs models; you keep your provider account.
- `/tool-choice`, "Tool choice": limit: settings for Claude Code, Codex and
  OpenCode are published; carrying a whole task through each tool, and
  passing a failed step to another tool, are being built. Cards: the
  instructions are written before the tool starts; only the step's
  permissions; your own files are left alone; three tools connect today.
  Secondary link "Get set up" (`/setup`).
- The four audience pages keep their audience sentences from the line and
  their card ideas, corrected as above, each with the price line.
- `/status`, "Service status": summary, time, one card for each part, a
  "Check again" button, and three notes: what the page covers (this service
  only, not your model provider or your machine), no history, and what to
  check first when a client stops working.
- `/demo`, "One step, shown": headline "What your coding agent sees at one
  step.", the moved demonstration, one Get started action.

## Checks run, and their results

- The surface map and the address tags, in the private environment below: the
  map loads (7 hostnames, canonical `https://baltor.ai`); the root address is
  right for `baltor.ai`, `DOCS.baltor.ai:443`, `docs.baltor.ai`,
  `status.baltor.ai`, `app.baltor.ai`, `baltor-pilot.fly.dev`,
  `127.0.0.1:8765` and `[::1]:80`; `served_asset("/", "GET", "Baltor",
  "docs.baltor.ai")` writes the canonical `https://baltor.ai/docs` and the
  root address `/docs` just before the head closes. This was a manual run,
  not a committed check.
- Baseline page heights at `243a8811` on a local fixture service (1440 by
  900, then 390 by 844), for the height budgets: homepage 7050 and 11880
  pixels, `/examples` 1953 and 2724, `/security` 2057 and 3086, `/pricing`
  2090 and 3450, `/how-it-works` 6134 and 10764, `/privacy` 2760 and 4817.
- Nothing else was run: no self-test, no tools suite, no browser suite, no
  conformance, no hardcoding audit and no Markdown lint.

## Known failures in this commit

- `every_served_address_names_a_packaged_file` in
  `http_boundary_checks.py` fails, because `WEB_ASSETS` names
  `public-pages.css` and `public-pages.js`, which do not exist yet. The
  browser check `every_served_asset_route_is_scanned_for_retired_words`
  fails for the same two routes.
- Conformance is expected to fail on `status.py` until it is added to
  `MODULE_MAP`.
- Every served page now carries a canonical link; no check was run to show
  that nothing compares served page bytes with the source file.
- The surfaces are not active: `http.py` does not pass the Host header yet.
- The eleven page addresses serve the homepage view until the views and the
  `service.js` routes exist.

## Commands to continue

```text
cd /home/username/.le-integration/site-usecases
# The shared main virtualenv has mcp 1.29.1, which lacks mcp.server.caching
# that http.py imports at this revision, so the service cannot start with it.
# This worktree's .venv links a private environment with mcp 2.2.0:
#   /home/username/.le-ci-tmp/venv-site-usecases
PYTHONPATH=src .venv/bin/python -m loop_engine.core.service_runtime.http_entrypoint smoke
PYTHONPATH=src:tools .venv/bin/python -m unittest discover -s tools -p 'test_*.py'
PYTHON=.venv/bin/python node tools/check_service_workspace.mjs /home/username/.le-ci-tmp/browser-site-usecases-N.json
PY_OVERRIDE=/home/username/.le-ci-tmp/venv-site-usecases/bin/python \
  bash /tmp/claude-1000/-home-username-loop-engine/81df4e9e-adbc-4fcf-9636-2fadc680611e/scratchpad/ci-run-wt.sh <sha>
```

The source of the line's pages and checks: `git show
44a4b426:<path>` for `src/loop_engine/core/service_runtime/web_campaigns.py`,
the four `web_assets/campaign-*.html`, the benefit views in
`web_assets/index.html` (`campaign-overnight` and the next three),
`tools/check_benefit_page_sources.py` and `tools/test_benefit_page_sources.py`.
The overnight views are uncommitted in
`/home/username/loop-engine/.claude/worktrees/wf_90f15b07-bb7-1`, the status
draft in `wf_eb5e10dc-951-2`, and the surface draft in `wf_cb91ffac-592-2`;
read them, do not edit them.

## Live and external effects

- Read-only requests without credentials to the live service: `GET
  /api/v1/health` and `GET /api/v1/capabilities` on `baltor.ai`, and `GET /`
  on `www`, `docs`, `status`, `examples`, `demo` and `app` under `baltor.ai`
  (each answered 200). Nothing was written.
- A new detached worktree, `/home/username/.le-integration/site-usecases`,
  with untracked links (not committed): `.venv`, `showcase/node_modules` and
  `tools/architecture_report/node_modules`.
- A private virtualenv, `/home/username/.le-ci-tmp/venv-site-usecases`
  (Python 3.10, the main environment's packages with `mcp==2.2.0`).
- A local fixture service on `127.0.0.1:8765`, stopped before this commit,
  and screenshots in the session scratchpad.
- No model call, no push, no deployment, no change to a provider, a domain
  record or the host file.

## Links the pages need in the header and footer

For the UI agent and the integrating session:

- Header: Use cases (`/use-cases`).
- Footer, Use cases group: Use cases (`/use-cases`), Overnight work
  (`/overnight`), Less in each request (`/context`), Model choice
  (`/model-choice`), Tool choice (`/tool-choice`), For coding agents
  (`/for/coding-agents`), For engineering teams (`/for/engineering-teams`),
  Comparing tools (`/for/comparing-tools`), Protocol and client
  (`/for/protocol-and-client`).
- Footer, Documentation group: Status (`/status`).
- `/demo` is reached from the hub; a footer link is optional.
