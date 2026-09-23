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
