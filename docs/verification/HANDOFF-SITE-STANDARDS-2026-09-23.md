# Handoff: website design standards and site map checks, September 23, 2026

This line wrote the website design standards, a typed site map contract and
the checks that stop pages, links and sections from disappearing without a
written reason. It was wrapped up early on the owner's direction of September
23, 2026, so some of it is unfinished. The work is one commit on a detached
worktree at `/home/username/.le-integration/site-standards`, made from
`243a8811` (main, live as Fly release 20). Nothing was pushed, deployed or
merged.

## What is done

- The standards: [website-design-standards.md](../guides/website-design-standards.md),
  covering colour tokens and dark bands, the type scale and line length, one
  spacing scale and the allowed section padding, containers and the shared
  left edge, the scroll budget and the first screen, buttons, cards, badges
  and forms, the header and footer anatomy, the page template,
  accessibility, responsive rules, copy rules and the regression rule. It
  includes every later direction of the day: the site map change (Get set up
  at `/setup`, Get started at `/get-started`, `/waitlist` its own page, the
  signed-in header), the scroll budget, the header measured at 1024 and 860,
  the sticky header and the primary action in every first screen.
- The typed, versioned contract, under `src/loop_engine/core/service_runtime/`:
  `web_site_map.py` (the reader and its refusals), `web_site_map.json`
  (record `service_web_site_map/v1`: 36 pages, the header for three states,
  four footer groups and the base row, seven hostnames, five dated removal
  rows) and `web_layout_standard.json` (record
  `service_web_layout_standard/v1`). The module is listed in
  `architecture_map.py` and `ARCHITECTURE-MAP.md`.
- `tools/test_website_site_map.py`: seven rules, 33 known-wrong sites built
  from a fixture site that passes every rule, a mutant control that removes
  each rule and requires its named check to fail once for each case, 15
  known-wrong records for the site map reader, five for the layout reader and
  a mutant control for two reader guards. It also writes a dated inventory.
- `tools/check_website_site_map.py`: the same seven rules applied to the
  website this checkout serves.
- The dated inventory of release 20:
  `artifacts/website-audit-2026-09-23/site-inventory-release-20.json` (16
  pages, 24 header entries, 10 footer links, 32 sections).
- The known-wrong run on `243a8811`:
  `artifacts/website-audit-2026-09-23/site-map-check-on-main-243a8811.txt`.
- `tools/check_website_layout.mjs`, the browser check, written and parsed by
  Node. It has not been run; see what is left.

## Allowed values the standards set

| Rule | Value |
|---|---|
| Section padding at 1440 | 0, 32, 40, 48, 64 pixels |
| Section padding at 390 | 0, 16, 24, 32, 40 pixels |
| Spacing scale | 4, 8, 12, 16, 20, 24, 32, 40, 48, 64 pixels |
| Content width | 1312 pixels (`--content-max`) |
| Reading column, lead line | 640 pixels, 760 pixels |
| Shared left edge | 64 pixels at 1440, 16 on a phone, within 2 pixels |
| Longest empty stretch at 1440 | 240 pixels |
| Page height at 1440 | 4,000 pixels for the homepage and How it works, 2,700 for any other page |
| Page height at 390 | twice the desktop budget in 844 pixel screens: 7,502 and 5,064 pixels |
| Contents list | a documentation page taller than 2,700 pixels opens with one |
| Header on a phone held sideways | 52 pixels at 844 by 390, or it steps aside while scrolling down |
| Text contrast, touch target | 4.5 to 1 for all text, 44 by 44 pixels |
| Line length | 80 characters |
| Dark bands, primary actions | at most one of each in a view |
| Typefaces | Geist and Geist Mono |

## What is left, in order

1. Run the browser check once against a local service and repair what the
   first run shows. It has never been executed, so expect some measurement
   code to need repair:
   `node tools/check_website_layout.mjs --local artifacts/website-audit-2026-09-23/layout-check-local-243a8811.json`.
2. With the owner's go-ahead for a read-only live run, run it against the
   deployed website and keep the report, which is expected to fail:
   `node tools/check_website_layout.mjs --url https://baltor.ai artifacts/website-audit-2026-09-23/layout-check-live-release-20.json`.
   The live failures of the scroll budget, the first screen and the sticky
   header belong in that report. The wrap-up direction forbade opening
   anything live, so this was not run.
3. When the restored pages merge, confirm or correct the parts of the site
   map that were proposals because those pages did not exist yet: the view ids
   of the new pages (the address without its first slash, further slashes as
   hyphens, for example `for-coding-agents` and `docs-getting-set-up`), the
   footer labels of the four benefit pages and the four audience pages, and
   the titles of the new pages (taken from the unmerged `g2-website` line at
   `44a4b426` where it had them). Operator order is Account, Administration,
   Sign out, as the header of the UI line had it.
4. Then add both new checks to continuous integration (below) and record the
   first passing run.
5. Resolve with the owner that 12 percent of a 390 pixel screen is 46.8
   pixels, while the direction named 52 pixels; the record uses 52.

## Checks run and their results

| Check | Result |
|---|---|
| `PYTHONPATH=src:tools python -m unittest tools/test_website_site_map.py` | passed, 15 of 15 tests, including the mutant controls |
| `PYTHONPATH=src:tools python -m unittest tools/check_website_site_map.py` on `243a8811` | failed as expected: 5 of 7 rules refuse the served website |
| `node --check tools/check_website_layout.mjs` | parses; the check itself was not run |
| Conformance, `python -m loop_engine --conformance` | all zero-tolerance gates pass; the rewritten manifest is committed |
| `architecture_map.self_test()` | passes with the new module mapped |
| Hardcoding audit with the CI allowlist and baseline, `--fail-on-new high` | passes, 0 new high findings after four were repaired in source |
| `markdownlint-cli2` 0.23.2 on the new and changed Markdown | 0 issues in 5 files |
| The two retired language searches of the CI documents job, on the new Markdown | no match |
| `tools/test_context_routes.py`, `test_build_records_index.py`, `test_service_documentation.py` | passed |
| `tools/test_homepage_demonstration.py` | passed with a virtual environment that has the pinned `mcp` 2.2.0; the shared `.venv` lacks `mcp.server.caching`, which fails it before and after this change |

The run on `243a8811` refuses: 21 pages that are not served or have no view
(19 addresses the served address table does not serve, and `/waitlist`, which
has no view of its own), 8 header differences (Use cases and Get started are
missing when signed out, the invitation action is extra, and the signed-in
header differs), 6 footer differences (two missing groups, the Developers
group, missing links, no mark in the base row), 45 reachability problems (the
missing pages, `/connect` linked although the site map calls it an old
address, `/login` missing from the footer) and 4 price problems (three
"29 United States dollars" and one "$29 per month"). Internal addresses and
the release 20 inventory pass.

Not run, on the wrap-up direction: the whole tools test suite, the self-test,
vale, the offline link check (every relative link in the new documents was
resolved by hand), and the browser check.

## Findings for other lines

- `/auth/confirm` is served, but the page script has no route for it, so the
  confirmation address shows the homepage. The site map expects the sign-in
  view there.
- `tools/check_hosted_website.mjs` and `tools/check_service_workspace.mjs`
  expect "29 United States dollars"; the standards write "$29 a month". They
  change together with the copy.

## Continuous integration

Neither new check makes continuous integration fail on its own.
`tools/test_website_site_map.py` passes and is found by the existing tools
test step. `tools/check_website_site_map.py` fails on main until the restored
pages merge, so its name keeps it out of that step. Once the restored pages
merge and it passes, add this line to the step "Development command and report
regression checks" in `.github/workflows/ci.yml`, after the discover line:

```bash
PYTHONPATH=src:tools python -m unittest tools/check_website_site_map.py
```

The browser check is not run by continuous integration, like the other
website browser checks. Once it passes on a local service, it can run in the
same job after `pip install -e '.[serving]'` and `npm ci --prefix showcase`:

```bash
node tools/check_website_layout.mjs --local "$RUNNER_TEMP/website-layout.json"
```

## Live and external effects

- Read-only requests to the deployed website: the homepage, the public
  capabilities record and `/use-cases` (which answered 404), to learn the
  live state. No form was submitted, no credential was sent.
- Read-only reads of other worktrees and the shared checkout, to align the
  site map with work in flight. Nothing in them was changed.
- No push, no deployment, no merge, no provider change and no model call.
