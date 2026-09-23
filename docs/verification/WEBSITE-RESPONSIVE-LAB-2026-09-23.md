# Website responsive lab, live release 20

Kind: verification report, partial. Observed on September 23, 2026 against
`https://baltor.ai`, Fly release 20, revision `243a8811`. The lab ran a
bounded selection, not the whole device list: the owner asked for a wrap-up
before the full sweep. What was not run is listed under
[Not run yet](#not-run-yet).

## Method

The lab is [capture_website_devices.mjs](../../tools/capture_website_devices.mjs)
with the device list in [website_devices.json](../../tools/website_devices.json).
The [guide](../guides/website-responsive-lab.md) describes each measure and
the commands.

```text
Captures in this report
├── Attempt 1 (kept, degraded): 24 captures, 8 configurations x 3 pages,
│   four page loads at once. Some loads received 503 answers.
├── Attempt 2 (the result): 48 captures, 8 configurations x 6 pages,
│   two page loads at once, no degraded load and no error
│   ├── Configurations: phone 320x568, phone 390x844, phone 844x390,
│   │   tablet 768x1024, desktop 1440x900, WebKit 390x844,
│   │   text at 200 percent on 390x844, dark appearance on 1440x900
│   └── Pages: /, /how-it-works, /pricing, /connect, /waitlist, /docs
├── One WebKit check capture (/ at 390x844) for the console error source
└── One band measurement of the homepage at 1440x900 and 390x844
```

Engines: Chromium 151.0.7922.34 and WebKit 26.5, headless, through
Playwright core 1.62.1. Firefox 153.0 is installed and was not run.
Sizes are layout pixels.

| Record | Place |
|---|---|
| Metrics, attempt 2 | [responsive-metrics-live-release-20.json](../../artifacts/website-audit-2026-09-23/responsive-metrics-live-release-20.json) |
| Metrics, attempt 1 | [responsive-metrics-live-release-20-smoke-attempt-1.json](../../artifacts/website-audit-2026-09-23/responsive-metrics-live-release-20-smoke-attempt-1.json) |
| Screenshots, attempt 2 | `/home/username/.le-ci-tmp/site-audit/devices/ENGINE/DEVICE/PAGE/`, outside the repository |
| Contact sheets | `/home/username/.le-ci-tmp/site-audit/devices/contact-sheets/`, one per page |
| Screenshots, attempt 1 | `/home/username/.le-ci-tmp/site-audit/devices-smoke-attempt-1/` |

## Findings, ranked by severity

Each finding names the device, the page, the evidence and a fix in the
site's own tokens and class names at `243a8811`. A fix is a proposal for the
fix phase; no website source was changed.

### High

- Finding 1. **The live service drops style sheets and scripts under a small burst.**
  Attempt 1, four page loads at once from one workstation: 503 answers for
  `service.js`, `client-access.js`, `catalogue-browser.js`,
  `architecture-story.js` and `baltor-mark.svg`. One capture, phone
  320x568 on `/pricing`, rendered with no style sheet: the header was 251
  pixels tall and the page overflowed sideways. Every asset and the page
  are served with `cache-control: no-store`, so each visit fetches about
  18 files again, and `fly.toml` sets `hard_limit = 32` requests for the
  one machine. The cause is inferred from those two facts. Fix: serve
  `/assets/` with `Cache-Control: public, max-age=300` and a validator at
  the least, or a long lifetime with a content digest in the file name, and
  raise the request limit or add a second machine.
- Finding 2. **The homepage is 7,046 pixels tall at 1440x900, against a budget of
  4,000.** That is 7.8 screens. At 390x844 it is 11,836 pixels (14.0
  screens), at 320x568 13,020 pixels (22.9 screens) and at 844x390 8,059
  pixels (20.7 screens). Band heights at 1440: hero 1,249, harnesses 143,
  problems 1,023, how 1,065, library 776, trust 465, pricing 768, questions
  632, closing 430. At 390: hero 2,029, problems 1,949, how 2,042, library
  1,755. Each band has 112 pixels of padding above and below at 1440
  (`--band-pad: clamp(3rem,7.8vw,7rem)`), and the two largest empty runs
  are 228 and 226 pixels. Fix, in order of pixels saved: set `--band-pad` to
  `clamp(2.5rem,5vw,4.5rem)` (about 640 pixels at 1440); at 1100 pixels and
  wider put `.step-demo` in the right column of `.hero.product-hero` instead
  of `grid-column:1/-1` below the hero; fold the `trust` band into the
  `problems` band; on phones show `.problem-grid` and `.how-steps` as
  compact rows without card padding (`.problem{padding:1rem}`,
  `.how-step{padding:1rem}`) and `.kind-grid` in two columns down to 360
  pixels.
- Finding 3. **`/pricing` never shows its primary action in the first screen.** Every
  configuration misses it, from 320x568 to 1440x900, where the page is only
  2,066 pixels tall. The button in `.plan-card .actions` follows the whole
  `.plan-list`. Fix: move `.plan-card .actions` directly under
  `.plan-price`, or add the access action to the
  `.pricing-page > .page-heading` band.
- Finding 4. **Text at 200 percent on 390x844 breaks the headline inside words.** The
  first screen shows "Superch / arge / your / develop" and the h1 does not
  fit in the first screen; the homepage becomes 38,760 pixels (45.9
  screens). The cause is `[data-view=home],.architecture-page{overflow-wrap:anywhere}`
  at the top of `architecture.css`, which lets a heading break anywhere.
  At the same size the header puts the menu button alone on a second row.
  Separately, `:root{font-size:16px}` in `service.css` ignores the reader's
  own browser text size setting, so this state is reached only by zoom
  today. Fix: `h1,h2,h3{overflow-wrap:break-word;hyphens:auto}` so only a
  word longer than the line breaks; `:root{font-size:100%}`; below 380
  pixels, or when the header wraps, let `.header .header-primary` take the
  full row under the mark.
- Finding 5. **The primary action is below the first screen on the smallest phone and
  on landscape phones.** Homepage at 320x568: the headline takes four lines
  and "Request an invitation" starts under the fold. Homepage at 844x390:
  only the chip, headline and lead fit; action and price do not, and the
  65 pixel header takes 17 percent of the height. Fix: at
  `(max-width:360px)` set `--text-hero:2rem` and
  `.band-hero .hero-copy{gap:1rem}`; at
  `(max-height:500px) and (orientation:landscape)` set
  `.home-band.band-hero{padding-top:1.25rem}`, `--text-hero:2.25rem` and
  `.header{min-height:56px}`.

### Medium

- Finding 6. **The homepage price is never in the first screen on a phone and is
  small on a desktop.** At 390x844 `.hero-split` starts at 961 pixels. At
  1440x900 it is in the first screen as 14 pixel grey text in `.hero-aside`.
  Fix: move the price sentence into `.hero-facts` as its first item, "One
  plan, $29 a month", and raise `.band-hero .hero-split` to
  `var(--text-lead)` with `color:var(--ink)`.
- Finding 7. **`/connect` and `/waitlist` shift after load.** Attempt 1 at 390x844
  recorded a cumulative layout shift of 0.13, above the 0.1 limit, from
  `aside.start-access-gets` and `p.start-signin` at 1.5 seconds, when the
  page script shows the access panel that the service reports. Attempt 2
  recorded 0.033 to 0.036 at 1440x900 and none at 390x844, so the shift
  depends on when the service answers. Fix: serve `#start-invite` visible
  in the markup and hide it only when the service says the list is closed,
  or give `.start-access-main` a `min-height` that holds the tallest panel.
- Finding 8. **The Get started page misses the primary action at 1440x900 and runs to
  3.99 screens there.** The form button sits under `.start-intro` and the
  step 1 heading. At 320x568 the page is 10.98 screens and at 844x390 10.68.
  Fix: at 981 pixels and wider, lower `.start-intro` padding to
  `clamp(2rem,3vw,3rem)` and `.start-layout` top padding to 2rem; keep
  the phone rule that already brings the form into the first screen at
  390x844.
- Finding 9. **Controls under 44 by 44 pixels on touch screens.** Homepage at 390x844,
  14 controls that are not inline links: the header mark link, 94x32; nine
  footer links, 23 pixels tall; "Explore an example task" and "See what is
  included", 25 pixels tall; "Appearance: light", 40 pixels tall. On
  `/connect`, the recipe tabs are 40 pixels tall. Fix:
  `.site-footer .footer-links a{display:inline-flex;align-items:center;min-height:44px}`,
  `.header .brand{min-height:44px}`,
  `.text-link{display:inline-flex;align-items:center;min-height:44px}`,
  `.site-footer #theme{min-height:44px}` and
  `.recipe-tabs [role=tab]{min-height:44px}`.
- Finding 10. **Lines longer than 90 characters on wide screens.** At 1440x900:
  `#task-breakdown > p.secondary` on `/how-it-works` has about 166
  characters per line, the context paragraph 123, the runtime disclosure
  135; `/connect` 135; `/docs` 115; `/pricing` 101; homepage answers in
  `.faq-item p` 98 and `.benefit-limits` 104. Fix: `max-width:68ch` on
  `.task-explorer>.secondary`, `.context-lifecycle>p` (now `950px`),
  `.runtime-disclosure p`, `.faq-item p`, `.band-night .benefit-limits`
  (now `max-width:none`) and `.start-card>p`.
- Finding 11. **Pages other than the homepage exceed 3 screens.** `/how-it-works`
  6,144 pixels at 1440x900 (6.8 screens) and 12.8 screens at 390x844;
  `/connect` 3.99 and 6.45; `/docs` 2.97 and 4.72; `/pricing` 2.3 and 4.06.
  Fix for `/how-it-works`: close the four `.layer-card` examples into one
  `details`, show `.friction-grid` as three columns at 1050 pixels and
  wider, and apply the band padding change of finding 2 to its sections.

### Low

- Finding 12. **Text under 12 pixels.** `.step-demo-harness .status-tag` is 11 pixels
  ("Being built" in the homepage demonstration). Fix: `font-size:.75rem`.
- Finding 13. **Running text under 15 pixels on phones.** At 390x844:
  `.band-hero .hero-facts`, `.hero-split` and `.harness-note` are 14
  pixels. Fix: `font-size:.9375rem` for the three at 600 pixels and
  narrower.
- Finding 14. **The system dark preference is not followed.** The served markup sets
  `data-theme="light"`, so a visitor whose system asks for dark gets the
  light page until they press the appearance switch in the footer. This
  matches the recorded owner choice of a light default and is listed only
  for completeness. The dark appearance itself measured no contrast
  failure on the six pages at 1440x900.

### Checked and found sound

- No horizontal overflow in any of the 48 healthy captures, including text
  at 200 percent.
- No clipped text. The two sideways-scrolling boxes on the homepage are the
  step folder tree and the connection entry, both code, both intended.
- No overlapping text or controls that a visitor can see. The attempt 2
  record does list overlaps on `/`, `/how-it-works`, `/connect`,
  `/waitlist` and `/docs`; every one involves text inside a closed
  disclosure, such as `dl#assignment-contract` or a closed `.faq-item`,
  which keeps layout boxes in Chromium although it is not shown. The lab now
  skips the content of closed disclosures, and a check capture after that
  change (`/` and `/how-it-works` at 390x844 and 1440x900) found no overlap
  and the same tap target counts.
- No contrast failure in light or dark on any captured page.
- The header is not sticky, so it never covers content after the first
  screen. No anchor jump left its heading under a fixed or sticky box. The
  attempt 2 record also tried anchors whose links sit in hidden views; the
  lab now follows only links a visitor can see, and in the check capture
  every such jump landed in view.
- The phone menu opened on every phone and tablet, every link was visible
  inside the window, and Escape closed it.
- WebKit page heights at 390x844 are within 1.3 percent of Chromium.
- WebKit logs one refused inline style for each screenshot. The single
  WebKit check capture showed 3 such errors for 3 screenshots, so these are
  the lab's own and not the site's. The lab now records the errors seen
  before its first screenshot separately.

## Not run yet

In the order the next session should run them:

1. The whole device list: 20 devices and 13 special cases, on all 14 pages
   and the root of the seven other hostnames. The command is in the
   [guide](../guides/website-responsive-lab.md#commands).
2. Firefox at 390x844 and 1440x900, WebKit at 820x1180 and 1440x900, the
   throttled runs, reduced motion, and dark at 390x844.
3. The widths between 860 and 1100 pixels, where the header shows every link
   but the hero stays in one column; the device list covers them with
   915x412, 1024x768 and 1180x820.
4. The comparison with eight to ten developer tool websites, with
   `--benchmark`, at 1440x900 and 390x844, homepage and pricing page only.
5. A second opinion on the contact sheets from another reviewer.
6. The visual review of every screenshot, device by device; this report
   reviewed the homepage and pricing contact sheets only.

## Limits

- Headless engines with emulated viewports on one workstation, not physical
  devices. WebKit is not Safari itself.
- Text at 200 percent overrides the root text size in the served markup and
  turns off the page's content security policy for that case only.
- Contrast is computed against the nearest painted background colour.
- The layout shift result depends on when the service answers and varied
  between the two attempts.
- The 503 cause is inferred from the cache header and the request limit; the
  service logs were not read.
