# Lines of work at the September 23 wrap-up

Each line ran in a detached worktree under `/home/username/.le-integration/`,
started from `main` at `243a8811` unless noted. "On main" means merged and
pushed; "patch" means the line's committed work is kept under
`artifacts/handoff-2026-09-23/patches/` because it was unfinished or its checks
did not all pass, with the line's own handoff file beside it.

| Line | Worktree | Scope | State |
|---|---|---|---|
| Release 21 | `r21` | Terms of service at `/terms`, the consent sentence and footer link, the owner's traced logo (variation 52 tile, variation 23 summit) as mark and icons, AGENTS.md records of the approvals and the model direction | reported at wrap-up; see below |
| Interface | `r22-ui` | Header and footer restored (Get started as the funnel action, Get set up as the guide), homepage sections restored, Get set up at `/setup`, waiting list page, lighter bands, less text, "$29 a month", sticky header, scroll budgets | reported at wrap-up; see below |
| Secure sign-up and funnel | `signup` | Email-only sign-up request version 2 with a service-made random password, verify-then-choose-password at `/auth/confirm`, recovery, and the Get started funnel at `/get-started` | reported at wrap-up; see below |
| Catalogue round two | `round-two` | 71 approved items (library from 43 to about 114), re-anchored, bundle for `publish-catalogue` | reported at wrap-up; see below |
| Library importer and panel | `library` | The importer (LS1, `60929071`) and review panel (LS2, `2424c34a`) onto main; panel review of 3,251 staged candidates | reported at wrap-up; see below |
| Overnight proof | `overnight` | Gemma 4 on Ollama Cloud, frozen design, ceiling 600 requests, report | reported at wrap-up; see below |
| Cut inventory | `site-inventory` | Every header link, footer link, page, section and hostname surface that was cut or never shipped, with reasons and decisions | reported at wrap-up; see below |
| Design review | `site-review` | Screenshots of release 17 and live release 20 at 1440 and 390, measured padding and empty space, eleven design questions per page | reported at wrap-up; see below |
| Standards and checks | `site-standards` | `docs/guides/website-design-standards.md`, a typed site map contract, `tools/test_website_site_map.py`, `tools/check_website_layout.mjs` | reported at wrap-up; see below |
| Documentation pages | `site-docs` | Seven documentation pages at `/docs/<page>` from branch `wave6/documentation-content` and the three customer pages, each reviewed independently | reported at wrap-up; see below |
| Use-case pages | `site-usecases` | Four benefit pages, four audience pages, the `/use-cases` hub, `/status`, hostname surfaces | reported at wrap-up; see below |
| Model and machine pages | `site-guides` | `/models` (bring your own model access), `/machine-fit`, refusal wording, the showcase decision | reported at wrap-up; see below |
| Responsive lab | `site-devices` | Device list and capture tool across Chromium, WebKit and Firefox; scroll runs; benchmark | reported at wrap-up; see below |
| Acceptance testing | `site-uat` | Persona tests by browsing, accessibility, speed, links and metadata, error states, forms, visual regression tool | reported at wrap-up; see below |

The per-line results follow, as each line reported.

## Results at the wrap-up

| Line | Commit | Where it is | Its own handoff | What remains |
|---|---|---|---|---|
| Release 21 | `38db84a4` | On main (merged in `7799c872`) | `docs/verification/HANDOFF-RELEASE-21-2026-09-23.md` | Deploy. The approved terms say "beta" twice; the retired-word scan skips the terms block only while it matches the approved file word for word. New accounts bind the starter snapshot once at start: set `catalogue.new_accounts_follow_release: true` with empty `starter_identities` before a catalogue release follows registration |
| Interface | `84132d84` | On main (merged in `62417ee3`) | `docs/verification/HANDOFF-r22-ui-2026-09-23.md` | Apply `docs/verification/HANDOFF-r22-ui-2026-09-23-homepage-polish.patch` (light bands, shorter text, "$29 a month", the demonstration in its own band, two restored sections) and update its checks; then the scroll budgets, the guide's missing steps and the device fixes |
| Library importer and panel | `d8dc09d9` | On main (merged in `b64aa56a`) | `docs/verification/HANDOFF-LIBRARY-LS1-LS2-2026-09-23.md` | The panel needs a reader for the importer's staging rows, criteria for outside material, review record version 3 and a seeded pilot before judging the 3,251 candidates |
| Cut inventory | `5972118a` | On main (merged in `3eb67480`) | `docs/verification/HANDOFF-site-inventory-2026-09-23.md` | 141 rows: 2 restore as it was, 58 restore reworked, 81 superseded. Its note that terms wait for the owner is out of date: the owner approved them on September 23 |
| Acceptance testing | `6ffc7304` | On main (merged in `4f57bc49`) | `docs/verification/HANDOFF-SITE-UAT-2026-09-23.md` | Persona runs, accessibility, Lighthouse, link crawl, error states, forms and the screenshot baseline were not run; the tools are installed in `/home/username/.le-ci-tmp/site-audit/uat/`. Live probe findings: `/get-started` answered 404 on a direct visit (served by the interface merge); every address serves the homepage's title and description to crawlers; no canonical link, no social card tags; eight hostnames serve the same page; no `robots.txt` or sitemap; `HEAD` answers 404; every file is sent with `no-store` |
| Model and machine pages | `6793217b` | On main (merged in `b03493ba`) | `docs/verification/HANDOFF-SITE-GUIDES-2026-09-23.md` | Build `/models` (one page) and `/machine-fit` as views, with the picker reading a table generated from the command's own advice code; source patches of the three unmerged branches are under `artifacts/site-guides-sources-2026-09-23/`. The showcase stays off the website |
| Secure sign-up and funnel | `81256882` | Patch `patches/signup-81256882.patch` | `lines/HANDOFF-signup-2026-09-23.md` | Run the browser suite and full CI; merge (expect conflicts on the sign-up form line, the page title line and the workspace check); then the live steps in its handoff to open registration |
| Documentation pages | `bc6d44f2` | Patch `patches/site-docs-bc6d44f2.patch` | `lines/HANDOFF-SITE-DOCS-2026-09-23.md` | Scan the new files for retired words, refresh three stale reference pages, fix 11 errors on the usage page, the index check tool and tests, the independent review |
| Use-case pages | `6d1deb09` | Patch `patches/site-usecases-6d1deb09.patch` | `lines/HANDOFF-site-usecases-2026-09-23.md` | The views are not written; `public-pages.css` and `.js` are named but missing; `http.py` must pass the Host header for the hostname map; `status.py` needs a route and its architecture entry |
| Catalogue round two | `949e29a9` | Patch `patches/round-two-949e29a9.patch` | `lines/HANDOFF-catalogue-round-two-2026-09-23.md` | Full CI on the final commit; settle the two review criteria of triage hazard 5; publish bundle `/home/username/baltor-bundles/round-two-4be111f` (digest `7f822354…`) with `publish-catalogue`; the homepage then says 114, so deploy that page with or after the release |

