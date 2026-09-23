# Handoff: website user acceptance testing line, September 23, 2026

This line was asked to run real-world user acceptance testing of the Baltor
website, live as Fly release 20. The owner stopped the work early on
September 23, 2026 to hand it over. This file records what was done, what is
left, what was found so far and how to continue. Nothing here changes the
website source.

## Where the work is

- Worktree: `/home/username/.le-integration/site-uat`, detached at
  `243a8811`. The website files in `src/loop_engine/core/service_runtime/web_assets/`
  at that revision are identical to `f7c89465`, the revision that Fly release
  20 was built from (`git diff f7c89465 243a8811 -- src/loop_engine/core/service_runtime/web_assets/`
  prints nothing). A local build from this worktree therefore serves the same
  pages as the live site.
- Two ignored links make the worktree runnable and are not committed:
  `.venv` points at `/home/username/.le-wave2/mcp-revision/.venv-mcp2`
  (Python 3.10, protocol library 2.2.0, which the service needs), and
  `showcase/node_modules` points at
  `/home/username/loop-engine/showcase/node_modules` (playwright-core 1.62.1).
- Test tools live outside the repository in
  `/home/username/.le-ci-tmp/site-audit/uat/`: axe-core 4.13.0, pixelmatch
  7.2.0, pngjs 7.0.0 and Lighthouse 13.5.0, installed from the public npm
  registry.
- Raw results of this line are in `artifacts/website-audit-2026-09-23/uat/`.

## What is done

1. The worktree, the Python environment link and the browser library link.
2. The three browser engines were checked. Chromium 151.0.7922.34, WebKit
   26.5 and Firefox 153.0 all start headless through playwright-core 1.62.1
   (3 of 3). WebKit is the engine for the phone persona.
3. One read-only HTTP probe of the live site, saved with its script:
   `artifacts/website-audit-2026-09-23/uat/live-http-probe-2026-09-23.txt`
   and `live-http-probe.sh`. It asked for 24 named addresses, the eight
   hostnames, the plain HTTP address, three HEAD requests, the home page
   headers, the caching and compression of seven files, and the head tags
   of `/pricing` as served before any script runs.
4. Reading of the page source and the served address table
   (`web_pages.py`, `index.html`, `service.js`) to ground the findings below.
5. The Ollama Cloud model list was read to choose extra persona reviewers.
   Models that accept images: `kimi-k3`, `kimi-k2.6`, `gemma4:31b` and
   `qwen3.5:397b`. `glm-5.3` accepts text only. No model was asked anything,
   so no model usage was spent.

No persona run, accessibility scan, Lighthouse run, link crawl, error state
test, form test or screenshot baseline was made yet. No tool under `tools/`
was written yet.

## Findings so far

These come from the saved probe and from reading the source. Each has the
page, the evidence and a concrete fix. The severity is this line's judgment.

| Rank | Severity | Finding | Evidence | Fix |
|---|---|---|---|---|
| 1 | High | A direct visit to `https://baltor.ai/get-started` shows "Address not found" with status 404. The page script lists `/get-started` as a Get started address and the website files README says `/connect`, `/get-started` and `/waitlist` open the same page, so anyone who types or shares that address reaches a dead end. | Probe line `/get-started 404`. `routeNames` in `service.js` has `/get-started`; `WEB_ASSETS` in `web_pages.py` does not. The comment above `routeNames` admits it. | Add `"/get-started": ("index.html", HTML_MEDIA_TYPE)` to `WEB_ASSETS` and a hosted check that asks for it and expects 200. |
| 2 | High | Every address serves the head of the home page. A shared link to the pricing, privacy or setup page shows "Baltor, Material your coding tools can search" and the home page description in Slack, LinkedIn, X, chat apps and search results. There is no Open Graph tag, no social card tag, no share image and no canonical link. The page title changes only after the page script runs, which link preview services do not run. | Probe section "head tags" for `/pricing`: title, description and icons only. | Let `served_asset` write a head block for each address, the way it already writes `{{SERVICE_NAME}}`: title, description, `<link rel="canonical" href="https://baltor.ai/PATH">`, `og:title`, `og:description`, `og:url`, `og:type`, `og:image` (a 1200 by 630 PNG served from `/assets/`), `twitter:card` set to `summary_large_image`. Add a check that each public address has its own title and description. |
| 3 | Medium | Eight hostnames serve the full site with status 200 and no redirect: `baltor.ai`, `www`, `app`, `docs`, `status`, `examples`, `demo` and `baltor-pilot.fly.dev`. Search engines see eight copies of every page, and `docs` and `status` promise a page they do not have. | Probe section "the other hostnames". | Redirect `www` to `https://baltor.ai` with 301 now. Add the canonical link from finding 2 so the other copies point at the main address. Serve a real page, or a redirect to the matching main page, for `docs` and `status` when their surfaces exist. The identity provider redirect list only matters for moving the host configuration's canonical origin, not for a canonical link tag. |
| 4 | Medium | There is no `robots.txt` and no `sitemap.xml`; both answer 404. | Probe lines `/robots.txt 404` and `/sitemap.xml 404`. | Serve `robots.txt` that allows the public pages, disallows `/app`, `/account`, `/admin` and `/auth/`, and names the sitemap. Serve `sitemap.xml` with the public addresses `/`, `/how-it-works`, `/pricing`, `/connect`, `/docs`, `/examples`, `/security` and `/privacy`. |
| 5 | Medium | A HEAD request to any page answers 404 with a JSON body. Uptime monitors, link checkers and some link preview services send HEAD first and will report the site as down or a link as broken. The HTTP standard (RFC 9110, section 9.1) expects every general-purpose server to answer HEAD wherever it answers GET. | Probe section "HEAD requests to pages": `/`, `/pricing` and `/docs` all 404. `served_asset` returns nothing unless the method is GET. | Answer HEAD for every address in `WEB_ASSETS` with the GET headers and no body. Add a check for one page and one file. |
| 6 | Medium | Every response is sent with `cache-control: no-store`, including the two typefaces (69,652 and 71,368 bytes), both stylesheets, the page scripts and the identity client script (223,189 bytes, 66,440 compressed). Every page load and every return visit downloads about 280 kilobytes again. | Probe section "caching and compression". | Serve `/assets/` files with a version in the address and `cache-control: public, max-age=31536000, immutable`, or at least `max-age=3600` with an entity tag. Keep `no-store` for the HTML and the interface. Measure the change with the Lighthouse run below. |
| 7 | Low | No `Strict-Transport-Security` header. Plain HTTP redirects to HTTPS with 301, but a visitor's first plain request can still be intercepted. | Probe section "response headers of the home page". | Add `Strict-Transport-Security: max-age=31536000; includeSubDomains`. All eight hostnames already serve HTTPS. |
| 8 | Low | No `/favicon.ico`, no web app manifest and no `theme-color` tag. Browsers use the declared icons, but some tools and older browsers ask for `/favicon.ico`, and a phone's "add to home screen" has no name or colour to use. | Probe lines `/favicon.ico 404`, `/manifest.webmanifest 404`. | Serve `favicon.ico` made from `favicon-32.png`, a small `manifest.webmanifest` with the name, the two icons and the colours, and `<meta name="theme-color">`. |
| 9 | Low | No `/.well-known/security.txt`, so a person who finds a security problem has no standard place to learn where to report it. | Probe line `/.well-known/security.txt 404`. | Serve a `security.txt` with the contact named in `SECURITY.md` and an expiry date one year ahead. |
| 10 | To measure | Every public page loads the identity client script (223,189 bytes) with `defer`, although only the sign-in, account and email return pages use it. | `index.html` head. | Measure with Lighthouse first. If it costs main thread time, load it only when a sign-in view opens. |
| 11 | To verify | The phone menu is a checkbox named "Show the menu", opened by a label that is hidden from assistive technology. A screen reader will announce a checkbox, not a menu button with an expanded state. The design choice keeps the menu working without the page script. | `index.html` header. | Check the accessibility tree and a screen reader reading in step 2 below before deciding. If confirmed, keep the checkbox for the no-script case and let the page script swap in a button with `aria-expanded`. |

What already works, from the same probe: plain HTTP redirects to HTTPS; text
files are compressed (zstd); an unknown address in a browser gets a helpful
HTML page with status 404; the security headers `content-security-policy`,
`referrer-policy`, `x-frame-options`, `permissions-policy` and
`x-content-type-options` are present on every response.

## What is left, in order

1. **Persona browsing.** Build `tools/website_persona_browser.mjs`: a small
   local HTTP server that holds one Playwright browser for one persona, and a
   `do` command that sends it one action and prints the result. Actions:
   `look` (a screenshot of the window at CSS scale, the visible text, and the
   visible controls with short references such as `e7`), `click`, `type`
   (fills a field, never submits), `press` (keyboard; reports the focused
   element, its name and whether a focus mark is visible), `scroll` (records
   the real distance moved), `find`, `back`, `goto`, `tree` (the accessibility
   snapshot), `note` (the persona's own words) and `stop`. Every action goes
   to a line of a JSON log with its time. On the live site the server aborts
   every request whose method is not GET, HEAD or OPTIONS, so a persona cannot
   submit a form even by mistake. Presets: `iphone` (WebKit, 390 by 844,
   touch), `laptop` (Chromium, 1366 by 768), `desktop` (Chromium, 1440 by
   900). A `--local-account` mode starts the account service fixture that
   `tools/check_service_workspace.mjs` builds (browser identity, client
   access, waiting list) and answers the identity provider's token request in
   the browser, as that suite does at its line 1697.
2. **Run the six personas**, one Claude subagent each, starting at the home
   page with no site knowledge. Before the first click each states where they
   would click first for each question (the first-click test). Questions and
   where the answers are, for scoring only:
   - Solo developer, `iphone`: what Baltor does, whether it works with Claude
     Code (home page harness strip), the cost (29 United States dollars each
     month, search free, invited accounts free), how to start (the one action
     "Request an invitation" to `/waitlist`).
   - Engineering lead, `laptop`: what data leaves the machine (`/security`
     and `/privacy`), whether model keys stay theirs (home page and How it
     works say yes), how usage is counted (one downloaded item), how to stop
     paying (check whether any page says it; likely a gap).
   - Overnight local model developer: Ollama on their machine or Ollama
     Cloud, and what they need. The home page marks overnight work "Being
     built" and may never name Ollama; record the gap as found.
   - Agent system builder: the protocol endpoint `https://baltor.ai/mcp` and
     how to connect a client (`/connect` recipes, `/docs`).
   - Keyboard-only visitor, `desktop`: reach pricing and the invitation form
     with the keyboard alone.
   - Returning customer, `--local-account`: sign in with
     `account-test@example.invalid` and any password, find the setup guide,
     create a client key, see usage.
   Then the five-second test: two fresh subagents and `kimi-k3` each see only
   the first screen (phone and desktop) and answer what this is and what to do
   next. `glm-5.3`, which reads text only, reviews the page text as the
   engineering lead. Record model, token usage and outcome of every call and
   stop at a declared ceiling of eight calls.
3. **Accessibility.** axe-core on every public view (`/`, `/how-it-works`,
   `/pricing`, `/connect`, `/docs`, `/examples`, `/security`, `/privacy`,
   `/login`, `/signup` and the unknown-address page) at 390 and 1440 pixels
   in the light and dark colour schemes; keyboard order and visible focus;
   the skip link; reflow at 320 pixels and at 200 percent text; forced colours;
   reduced motion; the accessibility tree of the header, the phone menu, the
   forms and the accordions.
4. **Speed.** Lighthouse for phone and desktop on `/`, `/how-it-works`,
   `/pricing`, `/connect` and `/docs` with Chrome at `/opt/google/chrome/chrome`:
   Largest Contentful Paint, Cumulative Layout Shift, Total Blocking Time,
   page weight and font loading. One more run with applied throttling of a
   slow network and a six times slower processor.
5. **Links and sharing.** Build `tools/check_website_links.mjs`: render every
   public page, follow every internal link, check each in-page anchor exists in
   the shown view, check external links once each, the unknown-address page,
   the root of each hostname, `robots.txt`, the sitemap, the canonical address,
   the title and description per page, Open Graph and social card tags, the
   icon and the manifest. Findings 1 to 5, 8 and 9 above are its first
   known-wrong cases.
6. **Error states.** With Playwright request routing, make `/api/v1/capabilities`
   and `/api/v1/health` fail, time out and answer slowly, and record what the
   home page, Get started and pricing show. Then go offline after load.
7. **Forms, local build only.** Validation messages, `type="email"` and
   `autocomplete` values, labels, password manager hints and double submit on
   the invitation form, sign-in and the client key form.
8. **Visual regression.** Build `tools/compare_website_screenshots.mjs` with a
   `baseline` and a `compare` mode that uses pixelmatch and writes a diff image
   and a JSON report. Record live release 20 (or the release live on the day)
   as the first baseline under
   `/home/username/.le-ci-tmp/site-audit/baselines/release-20/`. The tool
   should load pixelmatch and pngjs from a folder named by an option, so no
   home path is written into it.
9. **Write** `docs/guides/website-acceptance-testing.md` (the checklist for
   before and after each release) and `docs/verification/WEBSITE-UAT-2026-09-23.md`
   (persona table, ranked findings), save raw results under
   `artifacts/website-audit-2026-09-23/uat/`, lint, run the hardcoding audit,
   and regenerate `docs/RECORDS-INDEX.md`.

## Decisions instead of owner questions

The owner, September 23, 2026: stop asking for decisions that best practice or
collected data can settle, and no paid real device is needed. These are the
choices and their reasons.

| Practice | Decision | Reason |
|---|---|---|
| Speed and use measured on real visitors | Build a first-party collector on the service itself: one small record per page view, sent to the same origin, with the page address without its query, Largest Contentful Paint, Cumulative Layout Shift and Interaction to Next Paint from the browser's performance interface, the window width rounded to a range and the service version. No cookie, no browser storage, no identifier, no account, no network address. Records are added into daily totals and removed after 30 days. Ship it switched off until the privacy notice revision below is published. | A same-origin collector needs no change to the content security policy and sends no visitor address to another company. The current notice says the site "runs no analytics" and "keeps no log of requests that succeed", so the notice must change before the collector records anything. Publishing a revised privacy notice is a legal commitment, which the authority section of AGENTS.md keeps with the owner, so the text below is prepared for one yes or no. |
| Real devices | No paid device cloud. Use Chromium, WebKit and Firefox with device settings on every release, and a person's own phone for a short manual pass when one is at hand. | The owner said no paid device is needed. WebKit is Safari's engine, so the remaining risk is limited to phone-specific scrolling and on-screen keyboard behaviour. |
| Tests with real people | Put the same six task scenarios into the material an invited user receives, as an optional feedback task, and record answers in the persona table format. No incentive payments. | Model personas find wayfinding and wording problems but not real motivation. Invited users are the real audience, and this costs nothing. |
| Search engines | Allow indexing of the public pages, publish the sitemap, and verify the domain in the free search engine consoles through a DNS text record in the existing Cloudflare zone. | It costs nothing and is needed for people to find the site. |
| Uptime from outside | A scheduled GitHub Actions workflow that sends GET requests to the eight hostnames every 15 minutes and opens an issue on failure. | Free, and it measures from outside Fly. It uses GET because HEAD is broken today (finding 5). |

Prepared privacy notice change, for `docs/legal/PRIVACY-NOTICE.md` and the
privacy view in `index.html` together (a browser check compares the two, so
both must change in one commit):

- Replace "It runs no analytics, advertising or tracking scripts. Every script
  on the site is served from the site itself." with "It runs no advertising or
  tracking scripts and no analytics product from another company. Every script
  on the site is served from the site itself. To keep the site fast, each page
  view may send one speed record to the service itself: the page address
  without any query, how long the page took to show and to respond, how much
  the layout moved, the width of the window rounded to a range, and the service
  version. A speed record holds no cookie, no identifier, no account, no
  network address and nothing you typed. Speed records are added into daily
  totals and removed after 30 days."
- Replace "It keeps no log of requests that succeed." with "It keeps no log of
  requests that succeed, other than the speed records described above, which
  name no person."

## Checks run and their results

| Check | Result |
|---|---|
| Three browser engines start through playwright-core 1.62.1 | 3 of 3 |
| Read-only live probe, 24 named addresses | 16 answered 200; `/get-started`, `robots.txt`, `sitemap.xml`, `favicon.ico`, both manifest names, `security.txt` and the unknown address answered 404 |
| HEAD requests to pages | 0 of 3 answered 200 |
| Hostnames answering their home page | 8 of 8 with 200, none redirected |
| Static files with a cache lifetime | 0 of 7 |
| Markdown lint of this file with `markdownlint-cli2` 0.23.2 | 0 issues in 1 file |
| No em dash or en dash in this line's files | 0 found |
| Records index regenerated and checked with `tools/build_records_index.py --check` | current; 233 records, one added |
| Hardcoding audit gate as continuous integration runs it (`--fail-on-new high`) | exit 0; 632 high and 20,040 material findings, the same as the run before this line's files; 1 minute 39 seconds |

There are no known failing checks in this line's files.

## Live and external effects

- Read-only GET and HEAD requests to the live site, without credentials: about
  25 on September 23, 2026 between 13:37 and 13:39 UTC while exploring, and
  about 50 between 13:41 and 13:42 UTC for the saved probe, one at a time.
- One read of the Ollama Cloud model list and five model information reads.
  No generation call.
- Packages installed from the public npm registry into
  `/home/username/.le-ci-tmp/site-audit/uat/`.
- Nothing was submitted, signed in, created, changed, deployed or pushed. No
  form was filled on the live site.

## Commands to continue

```bash
cd /home/username/.le-integration/site-uat
# Links that the worktree needs (ignored by Git)
ln -sfn /home/username/.le-wave2/mcp-revision/.venv-mcp2 .venv
ln -sfn /home/username/loop-engine/showcase/node_modules showcase/node_modules
# Repeat the read-only probe into a new file
bash artifacts/website-audit-2026-09-23/uat/live-http-probe.sh > /home/username/.le-ci-tmp/site-audit/uat/probe-again.txt
# Lighthouse, phone settings, one page
node /home/username/.le-ci-tmp/site-audit/uat/node_modules/lighthouse/cli/index.js https://baltor.ai/ \
  --chrome-path=/opt/google/chrome/chrome --chrome-flags="--headless=new" \
  --output=json --output-path=/home/username/.le-ci-tmp/site-audit/uat/lighthouse-home-phone.json
# Checks before committing documentation
npx --yes markdownlint-cli2@0.23.2 docs/verification/HANDOFF-SITE-UAT-2026-09-23.md
python tools/build_records_index.py && python tools/build_records_index.py --check
PYTHONPATH=devtools/src python -m loop_engine_devtools.cli --hardcoding-audit \
  --allowlist devtools/hardcoding-allowlist.yaml --baseline devtools/hardcoding-ci-baseline.json --fail-on-new high
```
