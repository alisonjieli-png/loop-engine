# Session handoff, September 23, 2026

This is the newest dated handoff. It records what is live, what the owner
asked for on September 23, 2026, what engineering decided and why, the state of
every line of work when the session stopped, and the ordered work that remains.
The next session (GPT 6 Astra) picks up from here. The roadmap remains the
task authority, and the
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md remains the one statement of what engineering may do.

## What is live

- The Fly app `baltor-pilot` runs release 20, built from `main` at `f7c89465`.
  The [current deployment](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
  section records its image digest, the rollback image and the live checks of
  releases 16 to 20.
- Eight hostnames answer: baltor.ai, www, app, docs, status, examples, demo and
  baltor-pilot.fly.dev. Every one of them shows the same homepage at its root
  today. A page of its own for each hostname is planned work below.
- Catalogue releases run without a redeploy. The host's catalogue source is the
  store; the active release is `c824a1d2` (the earlier one is `ad440982`).
  Only `pilot-owner` follows the release; the other five tenants hold empty
  snapshots, so tenant isolation passes 19 of 19.
- Payments are live but shown as "Invitation only". A customer paying through
  the live checkout is the product working; engineering makes no charge.
- Mail: the send-only key `resend-send` sends from `accounts@mail.baltor.ai`;
  a test send to `delivered@resend.dev` was accepted on September 23.

## What the owner asked for on September 23

Quoted in the owner's words, in order.

1. Terms and registration: "I have approved the terms, you can open it".
2. Models: "we'd be better off just using Ollama Cloud, we don't actually need
   the model running locally", and "Baltor is not a tool to run models, people
   are expected to bring their own API key, or auth ... Ollama + local model at
   127.0.0.1, Ollama cloud, another system in their house on a local IP ... We
   can still prove out overnight solving using cheap/local models using Ollama
   Cloud and something like Gemma 4".
3. Logo: the owner's own sheet of 100 variations, "These are much much much
   better logos". Variation 52 (the husky head on a navy tile) is traced as
   the header mark and page icon; variation 23 is the standalone mark.
4. Interface: fewer black spaces, less text, no "US dollar" wording, a separate
   section between the hero and the demonstration, and "Get started" back in
   the top bar.
5. Recovery: "with the new design you removed so many header pages, footer
   pages, and other things. You need to recover those and work that into the
   new and improved design and go through and inventory everything that you
   cut, why you cut it". Create design standards, take screenshots, review
   whitespace, padding, consistency, missing and lost pages and regressions.
6. Paths: "We need to get all of the pages that we built fully working and
   fully live, there is no point in building a page if we can't show it.
   However, not every page needs to be in the header." And: "I think we need
   to have 'Get Setup' which is a guide on how to get setup and 'get started'
   is the sign up and registration/pay funnel."
7. Length: "improve the design so people don't have to scroll down so far to
   get all of the details."
8. Testing: "do more real world analysis, screenshot, scrolling, and
   improvements on various screen sizes", and "Are there any other best
   practices real world UA/UAT, actual browsing that can help".
9. Working style, verbatim: "You need to stop asking me for stupid 'decisions
   for you', your just is to use best practices, or implemeent necessary tools
   to collect data then make a decision. We don't need real paid device for
   testing."

## Decisions engineering made, and why

The full target site map with its reasons is
[TARGET-SITE-MAP.md](../../artifacts/handoff-2026-09-23/website-audit/TARGET-SITE-MAP.md).

| Decision | Choice | Reason |
|---|---|---|
| Header, signed out | How it works, Use cases, Library, Pricing, Docs, then Sign in and one primary action, "Get started" | The owner's split of the two paths; not every page belongs in the header |
| Header, signed in | Workspace, Get set up, Library, Docs, then Account and Sign out, plus Administration for the operator | The guide matters most once an account exists |
| Get started | The sign-up, registration and payment funnel at `/get-started`: create an account with an email only, confirm it, choose a password, subscribe at $29 a month, get set up. While accounts are invitation-only, step 1 is the invitation request. The header label never switches | The owner's definition; a stable label |
| Get set up | The setup guide at `/setup`; `/connect` stays an alias so earlier links work. Visible spelling "Get set up", the verb form of the owner's "Get Setup" | The owner's definition; plain English |
| Waiting list | Its own focused page at `/waitlist` again, as in release 17 | It was a lost page |
| Footer | Four groups (Product, Use cases, Documentation, Company) plus a base row; every built page reachable | Every built page must be shown |
| Hostnames | docs shows Docs, status shows Status, examples shows First example, demo shows the one-step demonstration, app shows the Workspace; every page names its baltor.ai address as canonical | Pages built for them never shipped |
| Scroll budget | The first screen holds the h1, the lead line and the primary action (the price too on the homepage and pricing); band padding at most 64 px on desktop and 40 px on phones; homepage and How it works at most 4,000 px at 1440 wide; other pages at most 3 screens; phones at most twice the desktop screens; no dark bands | Live release 20 measured 7.8 screens for the homepage at 1440 wide and 14 to 23 on phones, with the price 5.6 screens down |
| Header behaviour | Sticky and compact at every size; slimmer on phones held sideways; anchors land below it | Live, it scrolls away at every size |
| Testing | Emulated devices on three browser engines (Chromium, WebKit for Safari, Firefox), persona tests by agents, accessibility, speed, links and metadata, error states and visual regression; no paid device cloud | The owner: no paid devices; best practice covers the rest |
| Real-visitor measurement | A first-party, cookie-free collector that keeps metadata only, with the privacy notice change prepared alongside it | Data before decisions, within the privacy notice |

## Measured on the live site (release 20)

Raw data: [page depth](../../artifacts/handoff-2026-09-23/website-audit/page-depth-live-release-20.json)
and [device sweep](../../artifacts/handoff-2026-09-23/website-audit/device-sweep-live-release-20.json),
both from Playwright against <https://baltor.ai>.

- The homepage is 7,046 px at 1440 x 900 (7.8 screens); the price first
  appears at y = 5,001; the hero band alone is 1,249 px; seven bands carry
  112 px of padding top and bottom, 1,812 px in all.
- How it works is 6,144 px (6.8 screens). Get started (`/connect`) is 4
  screens. On a 320 x 568 phone the homepage is 22.9 screens.
- No horizontal overflow at any of 18 sizes from 320 x 568 to 2560 x 1440.
- The header is not sticky at any size. Its "Request an invitation" button
  shows on every first screen, beside the menu button on phones.
- Pricing still says "29 United States dollars each month".
- Text as small as 11 px on the homepage; 9 to 18 paragraphs per page run past
  about 90 characters a line on laptops; 14 to 22 tap targets under 44 px on
  touch screens.

## Work lines when the session stopped

Each line ran in its own detached worktree under `/home/username/.le-integration/`.
The table in [the line register](../../artifacts/handoff-2026-09-23/LINES.md)
gives each line's commit, its own handoff file, whether it reached `main`, and
where its patch is kept when it did not.

## Artifacts

- Website audit canvas: <https://claude.ai/artifact/U8VDRBQYdvShmaVVUYM8k4>.
  Boards: the cut inventory, the restored header, the restored footer, the Get
  started funnel, less scrolling and the screen-size sweep with real
  screenshots. The generator is
  [build_audit_canvas.py](../../artifacts/handoff-2026-09-23/scripts/build_audit_canvas.py).
- Website design canvas: <https://claude.ai/artifact/Rtmq5qQByY2656efjRBoN3>,
  with the round-five logo board from the owner's sheet.
- Handbook: <https://claude.ai/artifact/NmqrRcuhDj97nvFGztZqQT>, with seven
  set pages and the tracker <https://claude.ai/artifact/KSN2vSw1niawnEmMK1xHJJ>.
  They describe the state of release 20.

## Ordered work that remains

1. Merge the website lines in this order, each checked for line survival after
   the merge (every line a branch added is still present) and then the full CI
   set: release 21 (terms at `/terms` and the traced logo), then the header,
   footer, homepage and Get set up line, then the Get started funnel and secure
   sign-up, then the use-case, documentation and model and machine pages, then
   the standards and the two new checks (`tools/test_website_site_map.py` and
   `tools/check_website_layout.mjs`) with the checks switched on in CI.
2. Release through `.github/workflows/fly-pilot.yml` from a committed `main`
   whose CI passed, then run
   [qa-release.sh](../../artifacts/handoff-2026-09-23/scripts/qa-release.sh)
   from the released worktree, the responsive lab and the acceptance checks
   against the live site. Record the release and update the current
   deployment section.
3. Open registration, which the owner approved. Ship the email-only sign-up
   (the service creates the account with a random password, the person
   verifies the email and then chooses a password), set the account email host
   block and the two secrets (`BALTOR_IDENTITY_SERVICE_KEY` from
   `supabase-secret`, `BALTOR_MAIL_API_KEY` from `resend-send`, staged through
   standard input and never printed), switch `registration_enabled` and
   `email_signup_enabled` on, and close the identity provider's own public
   sign-up. The management token for that setting was never stored; the
   prepared Supabase connection in the harness needs its sign-in first. Until
   the provider's public sign-up is closed, keep registration closed, because
   the provider's sign-up link keeps the first password (account
   pre-hijacking, recorded in the identity probe of September 23).
4. Publish catalogue review round two (71 approved items) as a catalogue
   release with `publish-catalogue`, then verify isolation and the demo digests.
5. Merge the library importer and review panel lines, then have the panel
   review the 3,251 staged candidates toward the 10,000 and 100,000 package
   milestones (roadmap S-6.40).
6. Finish and publish the overnight proof with Gemma 4 on Ollama Cloud, within
   the recorded ceiling of 600 requests, and put its measured result on the
   `/models` page in the place left for it.
7. Merge the consolidation line (triage plan steps 2 to 9) and serve an answer
   for `HEAD /`, which returns 404 today.
8. Fix what the responsive lab found on the live site
   ([its report](../verification/WEBSITE-RESPONSIVE-LAB-2026-09-23.md)). First,
   four page loads at once got 503 answers for style sheets and scripts, and
   one page showed without styling. Every file is sent with `no-store` against
   a limit of 32 requests at a time, so cache `/assets/` with a validator and
   raise the limit or add a machine. Then:
   - the pricing button under the price;
   - headings that break inside words at 200% text;
   - `:root{font-size:100%}`, so the reader's text size counts;
   - the layout shift on `/connect` and `/waitlist`;
   - 44 px tap targets;
   - `max-width: 68ch` on running text.

## How to continue

- Full CI on an export of a revision:
  [ci-run-wt.sh](../../artifacts/handoff-2026-09-23/scripts/ci-run-wt.sh).
- Page depth and the device sweep:
  [depth.mjs](../../artifacts/handoff-2026-09-23/scripts/depth.mjs) and
  [sweep.mjs](../../artifacts/handoff-2026-09-23/scripts/sweep.mjs), run with
  Playwright from `showcase/node_modules`.
- The inventory parser:
  [site_inventory.py](../../artifacts/handoff-2026-09-23/scripts/site_inventory.py)
  lists the header links, footer links and views of any revision of
  `web_assets/index.html`.
- These scripts keep the absolute paths of this machine. They are evidence of
  how the work was done; move a script under `tools/` with its tests before a
  release depends on it.
