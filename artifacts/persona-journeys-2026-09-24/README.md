# Persona journeys evidence, September 24, 2026

Kind: evidence folder for
[the persona journeys record](../../docs/verification/PERSONA-JOURNEYS-2026-09-24.md).
Five scripted personas used the live Baltor site, Fly release 24, between 14:09
and 17:10 UTC. This README lists 43 PNG files: 37 screenshots that the persona
scripts saved and 6 frames taken from their recordings for the record. The
screenshots are byte-for-byte copies of the originals. The finding numbers
below are the ranks in the record. "Gap" means a test-tooling gap in the
record, not a product finding.

The images are committed in `docs/verification/assets/persona-journeys-2026-09-24/`,
in the same persona folders, and each file name below links there. The
repository ignores PNG files under `artifacts` (the `/artifacts/**/*.png` rule
in `.gitignore`) and keeps the screenshots of a record under
`docs/verification/assets/`, so the description lives here and the images sit
beside the record.

The originals, the persona reports, the scripts and the videos stay outside the
repository in `/home/username/.le-ci-tmp/persona-journeys-2026-09-24/`, one
folder per persona. That is a local folder on the workstation that ran the
personas; it is not published.

## Claude Code developer

A solo developer who uses Claude Code daily and wants tickets worked overnight
on a cheaper model. Viewport 1440 by 900.

| File | Page | What it shows | Findings | SHA-256, first 12 |
| --- | --- | --- | --- | --- |
| [02-overnight-use-case.png](../../docs/verification/assets/persona-journeys-2026-09-24/claude-code-developer/02-overnight-use-case.png) | `baltor.ai/overnight` | The overnight use case, read before sign-up | Context | `f70c4f0b851a` |
| [05-submit-signup-email.png](../../docs/verification/assets/persona-journeys-2026-09-24/claude-code-developer/05-submit-signup-email.png) | `baltor.ai/get-started` | The "Check your email" message after Create account | 16 | `dcdd1b885dc6` |
| [06-wait-for-confirmation-email.png](../../docs/verification/assets/persona-journeys-2026-09-24/claude-code-developer/06-wait-for-confirmation-email.png) | `baltor.ai/get-started` | The page while the inbox was polled; the email took 3.94 seconds | 16 | `961998d3c1d3` |
| [07-open-confirmation-link.png](../../docs/verification/assets/persona-journeys-2026-09-24/claude-code-developer/07-open-confirmation-link.png) | `baltor-pilot.fly.dev/auth/confirm` | "Choose your password", step 3 of 5, on the Fly hostname | 1 | `31dfebf936e5` |
| [09-plan-step.png](../../docs/verification/assets/persona-journeys-2026-09-24/claude-code-developer/09-plan-step.png) | `baltor-pilot.fly.dev/get-started` | Step 5, "Your account includes Baltor Pro", under the heading line that still says $29 a month; step 4 marked done | 1, 10 | `cae34a726e08` |
| [11-select-claude-code-tab.png](../../docs/verification/assets/persona-journeys-2026-09-24/claude-code-developer/11-select-claude-code-tab.png) | `baltor-pilot.fly.dev/setup`, Claude Code tab, signed in | The entry and the endpoint name `https://baltor-pilot.fly.dev/mcp`; Test service connection disabled beside "Sign in to check access"; step 1 still offers account creation | 1, 5, 18 | `28935038fc96` |
| [13-confirm-signed-in-on-account.png](../../docs/verification/assets/persona-journeys-2026-09-24/claude-code-developer/13-confirm-signed-in-on-account.png) | `baltor-pilot.fly.dev/account`, signed in | Raw Tenant, Namespace, Scopes and Access; "Load client tokens" not pressed; the billing panel asks to connect while connected | 15, 18, gap 4 | `adaa2b14f039` |

Not copied: `01-homepage.png` is byte-identical to the engineering lead's
`01-01-homepage.png`. `03-get-started-click.png` and
`04-prepare-disposable-inbox.png` are byte-identical to the engineering lead's
`12-get-started-view-only.png`. `08-set-password.png` is byte-identical to
`09-plan-step.png`. `10-go-to-setup.png` is the Codex tab of the same signed-in
page as `11-select-claude-code-tab.png`. `12-go-to-account.png` and
`14-copy-connection-entry.png` are byte-identical to
`13-confirm-signed-in-on-account.png`.

## Data scientist

Cleans messy tables and has heard that small models can do it with the right
instructions. Viewport 1280 by 800.

| File | Page | What it shows | Findings | SHA-256, first 12 |
| --- | --- | --- | --- | --- |
| [02-use-cases.png](../../docs/verification/assets/persona-journeys-2026-09-24/data-scientist/02-use-cases.png) | `baltor.ai/use-cases` | The use cases page, with no data cleanup example | 17 | `26011ebfb56e` |
| [03-efficiency.png](../../docs/verification/assets/persona-journeys-2026-09-24/data-scientist/03-efficiency.png) | `baltor.ai/efficiency` | Efficient operation, with no data cleanup example | 17 | `feef6f5c804a` |
| [04-pricing.png](../../docs/verification/assets/persona-journeys-2026-09-24/data-scientist/04-pricing.png) | `baltor.ai/pricing` | $29 a month and no mention of the founding offer | 10, 17 | `75bafac81d75` |
| [05-docs.png](../../docs/verification/assets/persona-journeys-2026-09-24/data-scientist/05-docs.png) | `baltor.ai/docs` | The documentation index, with no data cleanup example | 17 | `55724d0070a6` |
| [09-wait-for-confirmation-email.png](../../docs/verification/assets/persona-journeys-2026-09-24/data-scientist/09-wait-for-confirmation-email.png) | `baltor.ai/get-started` | The page while the inbox was polled; the email took 9.01 seconds | 16 | `2c55a6d59116` |
| [10-open-confirmation-link.png](../../docs/verification/assets/persona-journeys-2026-09-24/data-scientist/10-open-confirmation-link.png) | `baltor-pilot.fly.dev/auth/confirm` | "Choose your password" on the Fly hostname | 1 | `22eb3d63d441` |
| [11-confirm-password-attempt-1.png](../../docs/verification/assets/persona-journeys-2026-09-24/data-scientist/11-confirm-password-attempt-1.png) | `baltor-pilot.fly.dev/auth/confirm` | 0.49 seconds after the click: "Setting your password…". The script read this as a hang | 4, gap 1 | `ea8c9fc7abcb` |
| [verify-03-result.png](../../docs/verification/assets/persona-journeys-2026-09-24/data-scientist/verify-03-result.png) | `baltor.ai/login` | The follow-up sign-in with a deliberately wrong password: the generic failure message | Gap 1 | `4a38ffd4ef03` |

Not copied: `01-homepage.png`, `06-get-started.png`, `07-enter-email.png`,
`08-submit-signup.png`, `verify-01-signin-form.png` and
`verify-02-filled.png`, which repeat screens shown above. The folders
`attempt-1-2026-09-24T14-29Z` and `attempt-2-2026-09-24T13-04Z` hold the two
earlier runs whose false blocker is gap 2. The second folder's name carries
Eastern time with a Z; its email arrived at 17:03:49 UTC.

## Engineering lead

Compares Baltor with other skill registries before buying seats for a team.
Did not sign up. Viewport 1440 by 900.

| File | Page | What it shows | Findings | SHA-256, first 12 |
| --- | --- | --- | --- | --- |
| [01-01-homepage.png](../../docs/verification/assets/persona-journeys-2026-09-24/team-lead-evaluator/01-01-homepage.png) | `baltor.ai/` | "finds them, vets them", "43 vetted packages", the two sections about teams and the footer | 3, 8, 14 | `325327111429` |
| [02-02-how-it-works.png](../../docs/verification/assets/persona-journeys-2026-09-24/team-lead-evaluator/02-02-how-it-works.png) | `baltor.ai/how-it-works` | The "Available today" notice that says public account creation is not open | 2 | `b0a07de9e933` |
| [03-03-security-access-and-data.png](../../docs/verification/assets/persona-journeys-2026-09-24/team-lead-evaluator/03-03-security-access-and-data.png) | `baltor.ai/security` | "Public account creation is not open", "Do not send private customer content yet" and the operational limits | 2, 9, 14 | `14d8721e839d` |
| [04-04-privacy-notice.png](../../docs/verification/assets/persona-journeys-2026-09-24/team-lead-evaluator/04-04-privacy-notice.png) | `baltor.ai/privacy` | The privacy notice, including backups and deletion | 9, what worked | `1f0e9ad36b68` |
| [05-05-terms-of-service.png](../../docs/verification/assets/persona-journeys-2026-09-24/team-lead-evaluator/05-05-terms-of-service.png) | `baltor.ai/terms` | The terms of service | What worked | `8a9129a3f423` |
| [06-06-pricing.png](../../docs/verification/assets/persona-journeys-2026-09-24/team-lead-evaluator/06-06-pricing.png) | `baltor.ai/pricing` | "for one person", "New vetted additions" and the outbound arrow on Get started | 3, 8, 13 | `39f88b045cb1` |
| [07-07-docs.png](../../docs/verification/assets/persona-journeys-2026-09-24/team-lead-evaluator/07-07-docs.png) | `baltor.ai/docs` | The documentation index | Context | `b069512f1eb7` |
| [08-homepage-faq-data-kept.png](../../docs/verification/assets/persona-journeys-2026-09-24/team-lead-evaluator/08-homepage-faq-data-kept.png) | `baltor.ai/` | The homepage answer to "What does Baltor keep about my work?" | What worked | `e6c64e0d56f6` |
| [09-docs-what-baltor-is.png](../../docs/verification/assets/persona-journeys-2026-09-24/team-lead-evaluator/09-docs-what-baltor-is.png) | `baltor.ai/docs/what-baltor-is` | The reference table with `host_attested` | 8 | `e66c62d52d2e` |
| [10-pricing-faq.png](../../docs/verification/assets/persona-journeys-2026-09-24/team-lead-evaluator/10-pricing-faq.png) | `baltor.ai/pricing` | The answers to "Is there a free plan?" and "Can a team share one account?" | 3, 10 | `2470cfd0aa71` |
| [12-get-started-view-only.png](../../docs/verification/assets/persona-journeys-2026-09-24/team-lead-evaluator/12-get-started-view-only.png) | `baltor.ai/get-started` | The five-step self-service sign-up, viewed without typing | 2, 10 | `bdd5d4dd796e` |

Not copied: `11-how-it-works-faq.png`, a How it works answer that no finding
uses.

## Pi and OpenCode developer

Runs Pi and OpenCode with local and cloud models and dislikes vendor lock-in.
Viewport 1440 by 900.

| File | Page | What it shows | Findings | SHA-256, first 12 |
| --- | --- | --- | --- | --- |
| [06-open-opencode-tab.png](../../docs/verification/assets/persona-journeys-2026-09-24/pi-opencode-user/06-open-opencode-tab.png) | `baltor.ai/setup`, OpenCode tab | Documented configuration, with native end-to-end qualification pending | 19 | `645b54c6883d` |
| [09-open-confirmation-link.png](../../docs/verification/assets/persona-journeys-2026-09-24/pi-opencode-user/09-open-confirmation-link.png) | `baltor-pilot.fly.dev/auth/confirm` | "Choose your password" on the Fly hostname | 1 | `3ec2c7d5a20b` |
| [11-return-to-setup-signed-in.png](../../docs/verification/assets/persona-journeys-2026-09-24/pi-opencode-user/11-return-to-setup-signed-in.png) | `baltor.ai/setup`, after sign-up | A signed-out header, Sign in and Get started. Byte-identical to `05-return-to-setup.png`, taken before sign-up | 1 | `7bf7b30ea8ef` |
| [12-open-pi-tab-signed-in.png](../../docs/verification/assets/persona-journeys-2026-09-24/pi-opencode-user/12-open-pi-tab-signed-in.png) | `baltor.ai/setup`, Pi tab, after sign-up | The extension path as plain text and "Sign in to check access". Byte-identical to `03-open-pi-tab.png`, taken before sign-up | 1, 5, 6 | `c176545e60db` |

Not copied: `01-homepage.png` is byte-identical to the engineering lead's
`01-01-homepage.png`. `02-click-get-set-up.png` is the signed-out Get set up
page on its Codex tab. `03-open-pi-tab.png` and `05-return-to-setup.png` are
byte-identical to `12-open-pi-tab-signed-in.png` and
`11-return-to-setup-signed-in.png`. `04-open-pi-extension-file.png` is a 2.2 MB
capture of the served extension source, which the record's follow-up check
confirmed answers 200. `07-click-get-started.png` is byte-identical to the
engineering lead's `12-get-started-view-only.png`. `08-submit-signup-email.png`
repeats the "Check your email" message. `10-set-password.png` is
byte-identical to the Claude Code developer's `09-plan-step.png`.

## Phone visitor

Saw Baltor mentioned on social media and opens it on a phone. Chromium with a
390 by 844 viewport, touch and a phone user agent. The screenshots are full
page, so some are very tall.

| File | Page | What it shows | Findings | SHA-256, first 12 |
| --- | --- | --- | --- | --- |
| [01-01-homepage-landing.png](../../docs/verification/assets/persona-journeys-2026-09-24/mobile-visitor/01-01-homepage-landing.png) | `baltor.ai/` | The homepage on the phone viewport; the menu control sits in the header | 7 | `6b2184bf62a0` |
| [03-03-open-menu.png](../../docs/verification/assets/persona-journeys-2026-09-24/mobile-visitor/03-03-open-menu.png) | `baltor.ai/` | The menu open | 7 | `1189d065786b` |
| [04-04-use-cases.png](../../docs/verification/assets/persona-journeys-2026-09-24/mobile-visitor/04-04-use-cases.png) | `baltor.ai/use-cases` | Use cases on the phone viewport | What worked | `257b697483df` |
| [05-05-reopen-menu-for-pricing.png](../../docs/verification/assets/persona-journeys-2026-09-24/mobile-visitor/05-05-reopen-menu-for-pricing.png) | `baltor.ai/use-cases` | The menu reopened to reach Pricing | 7 | `7e1eb8f40f81` |
| [06-06-pricing.png](../../docs/verification/assets/persona-journeys-2026-09-24/mobile-visitor/06-06-pricing.png) | `baltor.ai/pricing` | $29 a month and no mention of the founding offer | 10 | `f76cc10be344` |
| [07-07-get-started.png](../../docs/verification/assets/persona-journeys-2026-09-24/mobile-visitor/07-07-get-started.png) | `baltor.ai/get-started` | Step 1 of the sign-up on the phone viewport | What worked | `f08476f1e7ec` |
| [09-09-submit-create-account.png](../../docs/verification/assets/persona-journeys-2026-09-24/mobile-visitor/09-09-submit-create-account.png) | `baltor.ai/get-started` | Create account pressed on an empty field, because no test inbox could be created | Gaps 3 and 5 | `439b8c2e6d4f` |

Not copied: `02-02-scroll-to-skim.png`, the homepage again after scrolling;
`08-08-enter-email-address.png`, byte-identical to `07-07-get-started.png`;
and `10-10-stopped-before-opening-email-link.png`, the same screen as
`09-09-submit-create-account.png`.

## Frames from the recordings

Extracted for the record with ffmpeg at full resolution, at the time shown in
each name, measured from the start of the recording.

| File | Source recording | What it shows | Findings | SHA-256, first 12 |
| --- | --- | --- | --- | --- |
| [data-scientist-19.30s-setting-your-password.png](../../docs/verification/assets/persona-journeys-2026-09-24/video-frames/data-scientist-19.30s-setting-your-password.png) | `data-scientist/journey.webm` | "Setting your password…" with the button disabled | 4, gap 1 | `d6e322d96227` |
| [data-scientist-19.95s-false-link-panel.png](../../docs/verification/assets/persona-journeys-2026-09-24/video-frames/data-scientist-19.95s-false-link-panel.png) | `data-scientist/journey.webm` | The false "This link cannot be used" panel, with "Setting your password…" below it | 4 | `d8349b35ff70` |
| [data-scientist-20.35s-step-5-signed-in.png](../../docs/verification/assets/persona-journeys-2026-09-24/video-frames/data-scientist-20.35s-step-5-signed-in.png) | `data-scientist/journey.webm` | Step 5, signed in, "Your account includes Baltor Pro" | 4, 10, gap 1 | `ee3bed61511d` |
| [claude-code-developer-14.42s-false-link-panel.png](../../docs/verification/assets/persona-journeys-2026-09-24/video-frames/claude-code-developer-14.42s-false-link-panel.png) | `claude-code-developer/claude-code-developer-session.webm` | The same false panel | 4 | `145fe56d5ec0` |
| [pi-opencode-user-13.50s-settings-still-loading.png](../../docs/verification/assets/persona-journeys-2026-09-24/video-frames/pi-opencode-user-13.50s-settings-still-loading.png) | `pi-opencode-user/session-recording.webm` | "This page is still loading its sign-in settings", with the button enabled | 12 | `e7477b7330cd` |
| [pi-opencode-user-15.30s-false-link-panel.png](../../docs/verification/assets/persona-journeys-2026-09-24/video-frames/pi-opencode-user-15.30s-false-link-panel.png) | `pi-opencode-user/session-recording.webm` | The same false panel | 4 | `4da860cae83c` |

## Videos, not committed

Each path is under `/home/username/.le-ci-tmp/persona-journeys-2026-09-24/`.

| Path | Length | Size | Notes |
| --- | --- | --- | --- |
| `claude-code-developer/claude-code-developer-session.webm` | 60.7 seconds | 4.9 MB, 1440 by 900 | The whole run |
| `data-scientist/journey.webm` | 41.6 seconds | 2.4 MB, 1280 by 800 | The reported run, 17:05 UTC |
| `data-scientist/attempt-1-2026-09-24T14-29Z/journey.webm` | 31.9 seconds | 2.5 MB, 1280 by 800 | First run, 14:28 UTC, gap 2 |
| `data-scientist/attempt-2-2026-09-24T13-04Z/journey.webm` | 21.2 seconds | 1.7 MB, 1280 by 800 | Second run, 17:03 UTC, gap 2 |
| `mobile-visitor/page@8e4881aa5bdbecb5e5437f14ccfa0dfe.webm` | 5 minutes 23 seconds | 7.1 MB, 390 by 844 | The reported run, most of it waiting on mail.tm retries |
| `mobile-visitor/page@f5ec71761f952455f98a9011bc870348.webm` | 14.3 seconds | 0.9 MB, 390 by 844 | An earlier short run, not cited |
| `pi-opencode-user/session-recording.webm` | 20.0 seconds | 1.9 MB, 1440 by 900 | The whole run |
| `team-lead-evaluator/session-recording.webm` | 11.2 seconds | 1.4 MB, 1440 by 900 | The main run; the follow-up disclosures have no video |

## Other evidence outside the repository

Also under `/home/username/.le-ci-tmp/persona-journeys-2026-09-24/`:

- Persona reports: `claude-code-developer/results-final.json`,
  `data-scientist/final-report.json`, `mobile-visitor/report.json`,
  `pi-opencode-user/result.json`, and `team-lead-evaluator/result.json` with
  `result-followup.json`. The earlier report files and run logs sit beside
  them.
- Persona scripts: the `.mjs` file in each persona folder.
- Follow-up for the record, in `follow-up-2026-09-24/`:
  `probe-signed-out-pages.mjs` and `probe-signed-out-pages-result.json`, the
  read-only load of 12 public pages on both hostnames; `video-frames/`, the
  six frames above; and `frames-candidates/`, the frames that were compared to
  choose them.
