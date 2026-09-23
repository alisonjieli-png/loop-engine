# Website design review, September 23, 2026

The owner asked on September 23, 2026 for a review that takes screenshots of
every page, asks design questions of them and catches white space, margin and
padding, consistency, missing pages, lost pages and regressions. A second
direction the same day asked for designs that stop people having to scroll so
far to reach the details. This record answers both from screenshots and
browser measurements. It changes no website source.

Status: the capture, the measurements and the findings below are complete for
the live website and release 17. Two independent second-opinion reviews were
started, one for the desktop and one for the phone and the website line. Both
reported; their agreements and disagreements are recorded at the end. The
[handoff](HANDOFF-WEBSITE-DESIGN-REVIEW-2026-09-23.md) lists what is left.

## Method

Four sources were captured on September 23, 2026 between 13:16 and 13:30 UTC.

| Folder name | Source | How it was served |
|---|---|---|
| `live` | `https://baltor.ai` and its seven other hostnames | The live service, Fly release 20, built from `f7c89465`. Its web assets are byte-identical to `243a8811` apart from the service name placeholder. |
| `r17` | Revision `3d2fe4e9`, release 17, the last website before the redesign | Locally, from a detached worktree |
| `g2` | Revision `44a4b426`, the unmerged website line | Locally, from a detached worktree |
| `r20local` | Revision `243a8811`, the same web assets as live | Locally, as a control for the local configuration |

The local services used one fixture configuration shaped like live. Its public
capabilities record matched live on every website field: browser sign-in on,
public registration off, client access on, access administration on, waiting
list on, checkout and customer portal on. The local control matched live on
page height, bands, links and type, so differences between release 17 and live
come from the source and not from the configuration.

Each address was loaded in Chromium from `playwright-core` 1.62.1 at 1440 by
900 (desktop) and 390 by 844 (phone, touch, mobile viewport), light colour
scheme, reduced motion, device scale 1. Every page got a full-page PNG, a
header crop and a footer crop. The homepage library section got an element
capture and a capture of the screen after following `/#library`. Five live
pages were also captured at 1920 by 1080 to check wide-screen alignment.
Nothing was submitted, no account was created and no state was changed on the
live service; the pages only read `/api/v1/capabilities` and
`/api/v1/account/identity`, as every visitor's browser does.

Measurements inside the page: header and footer links, every top-level band
with its position, height, background colour and luminance, padding, content
maximum width and left edge; vertical runs taller than 160 pixels with no text,
image or control; horizontal overflow and tap targets on the phone; the fonts
the browser actually rendered (from the DevTools protocol call
`CSS.getPlatformFontsForNode`); heading and paragraph sizes and line capacity
in characters; primary buttons; word counts; dark bands; and the style of every
button, card and badge. A second pass measured scroll depth: page height in
screens, where the first heading, first primary action, first price and footer
start, and how much of the height carries no content.

Evidence files:

- Screenshots: `/home/username/.le-ci-tmp/site-audit/shots/<folder>/<width>/<page>.png`,
  with `.header.png` and `.footer.png` crops, outside the repository.
  [screenshots.json](../../artifacts/website-audit-2026-09-23/screenshots.json)
  lists all 457 files with their SHA-256 digest, source, width and capture time.
- Measurements: [metrics.json](../../artifacts/website-audit-2026-09-23/metrics.json).
- Tools, outside the repository in `/home/username/.le-ci-tmp/site-audit/`:
  `capture.mjs`, `scrolldepth.mjs`, `wide.mjs`, `serve_like_live.py`,
  `tile.py`, `analyze.py` and `build_artifacts.py`. Viewing tiles cut from the
  screenshots are in `view/` beside them; they are aids, not evidence.

Limits: signed-in views were not captured. Dark mode was not captured. Release
17 and the website line do not bundle a web font, so on this machine they
rendered in Noto Sans; a visitor's machine may show another system font.

## Findings ranked by severity

Every fix below uses the redesign's own tokens from
`src/loop_engine/core/service_runtime/web_assets/service.css`: `--band-pad`,
`--band-gutter`, `--content-max`, `--text-hero`, `--text-h2`,
`--text-h2-small`, `--text-lead`, `--radius-button`, `--radius-card`,
`--radius-panel`, `--radius-field` and the `--night` colours.

### High

- **Finding 1: The homepage is 60 percent longer than release 17 and the price is five
   screens down.** At 1440 the live homepage is 7,046 pixels (7.83 screens)
   against 4,389 (4.88 screens) in release 17; on the phone it is 11,836
   pixels (14.0 screens) against 7,873 (9.3). The price is first mentioned at
   y=635 in 14-pixel grey text in the hero aside, but the first visible price
   (`$29`, 56 pixels) starts at y=4,992 on the desktop and y=9,245 on the
   phone. More than half of the desktop height (55 percent) carries no text,
   image or control, and band padding alone is 1,812 pixels (26 percent).
   Evidence: `shots/live/1440/home.png`, `shots/r17/1440/home.png`,
   `metrics.json` pages `live/1440/home` scrollDepth. Fix: see the scroll
   depth section; the three largest changes shorten the desktop page by about
   2,100 pixels without removing content.
- **Finding 2: Inner pages do not share the homepage grid, and nothing shares it at wide
   screens.** At 1440 the header logo and the homepage bands start at x=64,
   but How it works and Pricing start at x=78, the reading pages (Docs,
   Examples, Security, Privacy, Sign up) at x=300, Sign in at x=220, and the
   workspace pages at x=79 and x=343. The cause is two containers: the
   redesign's `--content-max` of 1,312 pixels with `--band-gutter`, and the
   older `main{max-width:1400px;padding:3rem 4vw 4rem}` that every view except
   home and Get started still uses. At 1920 the header logo stays at x=64 and
   the header button ends at x=1,856 while the homepage content and footer sit
   at x=304 to 1,616, and Docs starts at x=540. Evidence:
   `shots/live/1440/how-it-works.png`, `shots/live/1920/home.png`,
   `metrics.json` `wideScreenLive1920` and `summaries.live/1440.headingLeftEdges`.
   Release 17 had the same split (header box 57.6, content 77.6), so this is not
   new, but the redesign fixed it only on the homepage. Fix: give `.header`,
   `main` and `.site-footer` the homepage band rule,
   `padding-inline:max(var(--band-gutter),calc((100% - var(--content-max)) / 2))`
   with `max-width:none`, and keep narrower reading columns inside that grid,
   aligned to its left edge.
- **Finding 3: The setup instructions are reachable only through "Request an
   invitation".** Release 17 linked Get started (`/connect`) from the header
   and the footer. Live removed both links; `/connect` and `/waitlist` now show
   the same page. Outside the workspace sidebar (Connect) and one account link
   (Open the connection settings), every route to it is labelled Request an
   invitation. An invited customer who needs the connection settings has no
   link in the header or footer that says so, and Workspace and Account are
   hidden until sign-in. The homepage closing band also lost release 17's second
   action, Get started in three steps. Evidence: header and footer link lists
   in `metrics.json` (`live` and `r17`, page `home`),
   `shots/r17/1440/home.header.png`, `shots/live/1440/home.header.png`. Fix: add
   Connect or Get started to the header (beside Docs) and to the Developers
   column of the footer, and add a quiet second action to the closing band.
- **Finding 4: Four hostnames promise a page they do not show.** `docs.baltor.ai`,
   `status.baltor.ai`, `examples.baltor.ai` and `demo.baltor.ai` each show the
   marketing homepage (identical height, bands and links at both widths).
   The release record says the per-hostname surfaces are not in this release,
   but a visitor who types `docs.baltor.ai` expects documentation. Evidence:
   `shots/live/1440/host-docs.png` and the other `host-*` captures. Fix: until
   those surfaces exist, send `docs` to `/docs`, `examples` to `/examples` and
   `status` to a short service status view built from `/api/v1/health`.

### Medium

- **Finding 5: Every homepage band boundary leaves 230 to 260 pixels of empty space at
   1440.** Each band carries 112 pixels of padding at top and bottom
   (`--band-pad` at its 7rem ceiling), and the last child of most bands adds
   a further 26 to 40 pixels, so the visible space below the content is 138 to
   152 pixels. The measured empty runs are 173 (hero), 260, 255, 247, 229, 261,
   248 and 180 pixels. The Get started page leaves 213 pixels at its end.
   Evidence: `emptyVerticalRunsOver160px` in `metrics.json`. Fix:
   `--band-pad:clamp(2.5rem,5vw,4.5rem)` (72 pixels at 1440, 40 on the phone)
   and `.home-band > :last-child{margin-bottom:0}` together with the same rule
   on each band's inner section.
- **Finding 6: The type scale has grown, and most reading lines are too long.** At 1440
   the live site uses four `h1` sizes (64, 53.28, 51.84 and 34 pixels), ten
   `h2` sizes (43.92 down to 15), ten `h3` sizes and twelve paragraph sizes
   (43.2 down to 11). Release 17 used two `h1` sizes and six `h2` sizes. Of
   154 paragraphs that wrap at 1440, 86 exceed about 75 characters a line: the
   840-pixel reading column holds 114 characters at 16 pixels, the Get started
   page 136 characters at 14 pixels, and the closing disclaimer 202 characters
   at 14 pixels across 1,312 pixels. On the phone no paragraph exceeds 75.
   Evidence: `summaries.live/1440.typeSizes`, `type.longLines` per page. Fix:
   a closed scale of `--text-hero` (homepage `h1`), one inner-page `h1` token,
   `--text-h2`, `--text-h2-small`, 1.25rem for `h3`, `--text-lead`, 1rem body
   and .875rem small text; cap reading text at `max-width:68ch`.
- **Finding 7: Buttons, cards, badges, accordions, arrows and prices are styled several
   ways.** Primary buttons come in seven sizes (44, 46, 48, 52 and 56 pixels
   tall, radius 10 or 12). Secondary buttons use blue text on a transparent
   ground (`.quiet`) except See one step work, which uses dark text on white.
   Rounded cards use radii of 10, 12, 14, 16 and 18 pixels and paddings from 20
   to 36 pixels (16 distinct card styles). Two badge classes (`.badge` and
   `.status-tag`) differ only by padding (11.2 against 10.4 pixels), and the
   Being built tag is 11 pixels in the step demonstration and 12 pixels in the
   dark band. The homepage FAQ is a
   card accordion with plus and minus icons; the Pricing FAQ uses native
   triangles. Request an invitation carries a right arrow in the hero and the
   closing band, a north-east arrow (which reads as an external link) on
   Pricing, and no arrow in the header. The price reads `$29 per month` on the
   homepage and `29 United States dollars each month` on Pricing. Evidence:
   `buttonStyles`, `cardStyles` and `badgeStyles` per page in `metrics.json`;
   `shots/live/1440/pricing.png`. Fix: one primary and one secondary button at
   48 pixels with `--radius-button` (a 44-pixel small size only in the header);
   every card at `--radius-card` with 24 or 32 pixels of padding and
   `--radius-panel` only for page-level panels; one badge class; one accordion
   component; the right arrow for internal links; one price format with the
   long form in small text.
- **Finding 8: Some pages have no single primary action, or hide it below the first
   screen.** Sign in shows three primary buttons: the header invitation, Sign
   in and Connect, with Connect wider than Sign in. The plan's Request an
   invitation on Pricing starts at y=1,090 at 1440 and y=1,305 on the phone,
   below the first screen, although the price sits at y=460. The invitation
   form's submit button on `/waitlist` ends at y=931 at 1440, just under the
   first screen; release 17's dedicated waiting-list page had it at y=529.
   The Get started page shows four primary-styled buttons, including a
   disabled Test service connection. Evidence: `primaryButtons` and
   `scrollDepth.primaryAction` in `metrics.json`; `shots/live/1440/login.png`.
   Fix: make email Sign in the primary action and the service key a quiet
   secondary panel; put the plan's button beside the price; on `/waitlist`,
   scroll to or focus the form.
- **Finding 9: Dark bands carry a lot of empty dark space.** The closing band is 430
   pixels at 1440, of which 223 pixels are padding (52 percent), and its
   disclaimer runs 202 characters a line. The How band is 1,065 pixels at
   1440 and 2,042 pixels on the phone, two and a half phone screens of
   unbroken dark. Release 17 had no dark bands. Evidence: `darkBands` in
   `metrics.json`, `shots/live/390/home.png`. Fix: halve the closing band's
   padding (`calc(var(--band-pad) / 2)`), move the disclaimer to the footer's
   bottom row at `max-width:68ch`, and on the phone show the five steps as a
   compact numbered list inside the dark band instead of five full cards.
- **Finding 10: The new footer adds about 330 pixels to every desktop page and 610 to
    every phone page.** It is 422 pixels tall at 1440 and 813 at 390, against
    94 and 201 in release 17, with four link columns whose last column holds
    status text ("Terms of service: not yet published") styled like links.
    Evidence: `footer.height` per page in `metrics.json`,
    `shots/live/1440/home.footer.png`, `shots/r17/1440/home.footer.png`. Fix:
    padding of 40 and 32 pixels, the three link columns in one row beside the
    brand on the desktop and in two columns on the phone, and status text in
    the bottom row as plain text (about 170 pixels saved on the desktop and 300
    on the phone).
- **Finding 11: Phone details: cut-off code, small text and small tap targets.** No page
    overflows horizontally at 390. But the homepage code block (512 pixels of
    content in a 353-pixel box) and the file tree in the step demo (440 in
    289) are cut at the right edge with no sign that they scroll, so the token
    variable name is hidden. The homepage renders 49 text runs under 13
    pixels, 40 of them at 12 pixels. Footer links are 23 pixels tall, text
    links 21 to 25, summary rows 32 to 33, and the workspace tabs and harness
    tabs 40. The open menu keeps the three-line icon instead of a close icon.
    Evidence: `phone` sections in `metrics.json`,
    `shots/live/390/home-menu-open.png`. Fix: wrap code on narrow screens
    (`white-space:pre-wrap;overflow-wrap:anywhere`) or add an edge fade; use
    .8125rem as the smallest text; give footer links, text links, summaries and
    tabs `min-height:44px`.
- **Finding 12: The Sign in form is cramped.** The No account yet link touches the Sign
    in with email heading, and the Sign in button touches the password field.
    The service key card is stretched to the form's height and leaves about
    200 pixels empty. Release 17 had the same spacing, so this is not a
    regression. Evidence: `shots/live/1440/login.png`,
    `shots/r17/1440/login.png`. Fix: a 24-pixel gap between the link and the
    heading and a 16-pixel gap above the button; `align-self:start` on the
    card.

### Low

- **Finding 13: The Administration page shows a grey strip under the footer at 1440.**
    The page content ends at 812 pixels in a 900-pixel window and the body's
    `--bg` shows below the white footer. Evidence: `shots/live/1440/admin.png`.
    Fix: `body{min-height:100vh;display:flex;flex-direction:column}` with
    `main{flex:1}`.
- **Finding 14: Following `/#library` puts the eyebrow flush against the top of the
    screen.** The section lands at scroll position 3,664 with its top at 0.
    Evidence: `shots/live/1440/home-library-viewport.png`. Fix:
    `scroll-margin-top:2rem` on anchored sections.
- **Finding 15: Small homepage inconsistencies.** The Hooks card's badge sits 20 pixels
    lower than its neighbours because its description wraps; the six benefit
    cards already pin badges to the bottom. The Trust, FAQ and closing bands
    have no eyebrow while the other five bands do. The hero chip and the
    aside both open with "Harness and agent optimized operation". Evidence:
    `shots/live/1440/home.png`. Fix: `margin-top:auto` on the library card
    badge; one rule for eyebrows; say the phrase once.
- **Finding 16: Workspace and Account show a dashboard of disabled controls to signed-out
    visitors.** `/app` renders a sidebar, a disabled Search, a Connect to
    search badge and an empty state; `/account` renders four panels with
    disabled buttons. Evidence: `shots/live/1440/app.png`. Fix: a compact
    signed-out state with one Sign in action and one line on what the page
    holds.
- **Finding 17: Missing root files.** `/favicon.ico`, `/robots.txt` and `/sitemap.xml`
    answer 404 on live. The page declares its icons, so browsers show one, but
    some clients request `/favicon.ico`. `/get-started` is a client route with
    no server entry, so a direct visit answers 404; no page links to it.
    Evidence: `metrics.json` `httpStatus`.

### The unmerged website line at 44a4b426

- **Finding 18: The website line cannot sit beside the live pages as it is.** It
    predates the redesign: no Geist font files (it renders a system font), the
    release 17 header and footer, and the arrow brand mark. It has three header
    variants of its own: the `/for/` pages drop Workspace, Account and
    Appearance and use a text Sign in. Its `/privacy` address answers 404 and
    its footer has no Privacy notice link, although live links it from every
    page. Its `/for/` pages ask visitors to "Create your Baltor account" while
    account creation is closed. The benefit pages show a visitor-facing test
    notice ("You are seeing version A of 2 of this page") and internal file
    names such as `instance_hibernation.py`. The footer grows to twelve links
    and wraps to two rows. Evidence: `shots/g2/1440/overnight.png`,
    `shots/g2/1440/for-coding-agents.png`, `shots/g2/1440/privacy.png`. Fix:
    rebuild these pages on the redesign's bands and tokens, keep the privacy
    route from main, use Request an invitation, and move test notices and file
    names to the documentation.

## What release 17 had that live lacks

- **Header:** Get started (`/connect`), Workspace and Account were always
  visible, with the Appearance toggle. Live shows Workspace and Account only
  when signed in, moved Appearance to the footer and removed Get started.
- **Footer:** Get started and Request access. Live has Request an invitation
  and adds Library (`/#library`).
- **Homepage sections:** Four things you can do today (search, selected
  downloads, connection settings, usage); Six things your agents get for each
  step, including Solutions you can run without us, A failed check is
  examined, not obeyed, and Work that can stop and start again; the callout
  Spend more time on the problem, with See the approach; Plan, build and
  review with the information each step needs, with Explore an example task
  as a button (now a text link in the dark band); and the closing band's
  second action, Get started in three steps.
- **Waiting list page:** release 17's `/waitlist` was a separate one-screen
  page, "Tell us what you want to build.", 973 pixels tall at 1440. Live shows
  the Get started page there, 3,594 pixels tall, with the form as step 1.
- **Get started page:** release 17 had eleven sections, including Get the part
  that runs on your machine and Revoke the token when you no longer need it.
  Live condenses them into three steps and points to the documentation for
  installation.
- **Not lost:** every internal link on every captured page answers 200 on
  live, release 17 and the website line. No page that release 17 served is
  missing from live.

Improvements over release 17 worth keeping: the phone header is 65 pixels
with a menu instead of 254 pixels of wrapped links; the header and footer are
identical on all 22 live captures; the Geist fonts are self-hosted and load on
every page; and no live page overflows horizontally on the phone.

## Answers to the design questions by page

Positions are pixels from the top of the page at 1440, then 390. "Empty" is
the share of the height with no text, image or control. Screens are page
height divided by the window height (900 and 844).

| Page | Height in screens | Empty | Whitespace | Primary action | Notes |
|---|---|---|---|---|---|
| Home | 7.83 and 14.02 | 55 and 50 percent | Eight runs of 173 to 261 pixels at band edges; the hero's upper right quarter is empty dotted ground next to the headline | Request an invitation, repeated four times, clear | Findings 1, 5, 9, 15 |
| How it works | 6.83 and 12.78 | 50 and 48 percent | One flat grey column with no band rhythm | None in the page body | Old layout with the new header; content at x=78; 1,176 words |
| Pricing | 2.30 and 4.06 | 49 and 47 percent | Right half empty beside the FAQ | Below the first screen (y=1,090 and 1,305) | Price at y=460 and 441; long price format |
| Get started and waiting list | 3.99 and 6.45 | 48 and 44 percent | 213 pixels at the end | Four primary buttons | Step titles appear three times each; 136-character lines |
| Docs, Examples, Security | 2.17 to 2.97; 3.28 to 4.72 | 47 to 50 percent | Tidy | One, or none on Security | 840-pixel column at x=300 holds 114 characters a line |
| Privacy | 3.09 and 5.82 | 45 and 46 percent | Tidy | None, correctly | Phone table becomes readable label and value rows |
| Sign in | 1.45 and 2.50 | 42 and 47 percent | Card stretched, 200 pixels empty | Three primary buttons | Finding 12 |
| Sign up | 1.51 and 2.36 | 52 and 48 percent | Tidy | Request an invitation | Secondary button uses the blue `.quiet` style |
| Workspace and Account | 2.11 and 4.11; 1.51 and 2.76 | 46 to 55 percent | Disabled panels | Disabled Search | Finding 16 |
| Administration | 1.00 and 1.49 | 60 and 52 percent | Grey strip under the footer at 1440 | None | Finding 13 |

## Scroll depth and how to shorten each page

| Page and width | Height | First heading | First primary action | Price (first mention, first large) | Footer starts | Band padding |
|---|---|---|---|---|---|---|
| Home, 1440 | 7,046 | 220 | 566 | 635, 4,992 | 6,623 | 1,812 (26 percent) |
| Home, 390 | 11,836 | 165 | 451 | 962, 9,245 | 11,024 | 816 (7 percent) |
| How it works, 1440 | 6,144 | 167 | none | none | 5,722 | 576 |
| How it works, 390 | 10,786 | 124 | none | none | 9,973 | 432 |
| Pricing, 1440 | 2,066 | 167 | 1,090 | 460, 460 | 1,644 | 216 |
| Pricing, 390 | 3,425 | 124 | 1,305 | 441, 441 | 2,612 | 120 |
| Get started, 1440 | 3,594 | 178 | 879 | none | 3,172 | 264 |
| Get started, 390 | 5,442 | 117 | 728 | none | 4,629 | 120 |
| Sign in, 390 | 2,110 | 144 | 615 | none | 1,297 | 104 |
| Workspace, 390 | 3,468 | 275 | 1,214 | none | 2,655 | 176 |

The coordinator's figures agree: the homepage is 7,046 pixels at 1440, the
hero band 1,249 pixels, and bands carry 112 pixels at top and bottom. The
coordinator put the first price at y=5,001; this review measures the top of
the large `$29` text line at y=4,992 and finds an earlier small mention at
y=635 in the hero aside.

The three changes that would shorten each page most without removing content:

- **Home, desktop.** Merge Pricing, Questions and Trust into one band with the
  pricing text and the FAQ on the left and the plan card and the three trust
  points on the right; today the pricing text leaves about 360 pixels empty
  beside the plan card (about 900 pixels saved). Put the step demonstration in
  the hero's right column and turn the aside paragraph into one caption under
  the buttons, so the hero fits the first screen (about 550 pixels). Lower
  `--band-pad` to 72 pixels and drop trailing margins (about 700 pixels).
  Together these bring the page to about 4,900 pixels, near release 17, and a
  line under the hero buttons such as "29 US dollars a month; search is free"
  puts the price in the first screen.
- **Home, phone.** Show the six benefit cards, the five steps and the six
  library kinds as compact two-column tiles or numbered lists instead of
  full-width cards (about 2,000 pixels across the three bands). Move the step
  demonstration out of the hero or show only the chosen result with the other
  two behind a disclosure (about 600 pixels). Merge Trust into Questions as
  three collapsed entries and set the footer's link columns in a tighter grid
  (about 700 pixels).
- **How it works.** Put the four task-explorer tabs in a two by two grid on
  the phone and trim the panel to the selected step; merge the effort grid and
  the four layer cards, which repeat the homepage benefits, into one
  three-column grid; and move the architecture figure and its caption behind a
  disclosure.
- **Pricing.** Put the plan's button beside the price; show the plan rows as a
  checklist like the homepage plan card (about 500 pixels on the phone); set
  the Common questions beside the plan at 1440.
- **Get started.** Show steps 2 and 3 as compact summaries that open when
  chosen; say each step's title once instead of three times; put Check the
  service connection behind a disclosure.
- **Docs, Examples, Security.** Narrow the text to 68 characters and use two
  columns for the short definition pairs; move the technical runtime reference
  to the end in a disclosure; reduce the intro padding from 64 and 40 pixels to
  the band tokens.
- **Sign in.** Make email sign-in the one card and put the service key behind a
  disclosure (about 450 pixels on the phone); align the card to its content.
- **Workspace and Account, signed out.** Replace the disabled dashboard with a
  short signed-out state, which removes most of the 3,468 and 2,326 pixels on
  the phone.

## Distinct values measured on live

Band vertical padding at 1440, top and bottom in pixels: 112 and 112, 87.84
and 96 (hero), 30 and 30, 64 and 40, 72 and 40, 56 and 96, 16 and 48, 40 and
56, 56 and 72, 56 and 16, 32 and 32, 25.6 and 25.6, 24 and 24, 12 and 12, 8
and 8.

All vertical padding values at 1440: 8, 12, 16, 19.2, 24, 25.6, 27.2, 30, 32,
36, 40, 48, 56, 64, 72, 87.84, 96 and 112 pixels (18 values). At 390: 8, 10,
12, 16, 19.2, 20, 20.8, 22.4, 24, 25.6, 28, 30, 32, 40, 44, 48 and 56 pixels
(17 values). Release 17 used 13 values at 1440.

Horizontal gutters at 1440: 64 pixels for the header, homepage bands, Get
started and footer; 57.6 pixels (`4vw`) inside the 1,400-pixel `main`, which
puts content at x=77.6; centred columns elsewhere.

Maximum widths: 1,312 pixels (`--content-max`: footer and homepage bands),
1,400 (`main` on inner pages), 1,000 (Sign in), 950 (figure caption), 840
(reading pages), 760 (homepage section titles), 720, 640, 540, 416, 410, 365
and 320 pixels.

## Second opinion

Two independent reviewers were given the same screenshots and the same
questions, with no access to these findings: one for the desktop captures and
one for the phone captures and the website line.

The desktop review agreed on: the homepage length against release 17 (about
7,050 against 4,390 pixels), band padding as the largest cause, the empty
upper right of the hero, the two containers (x=64 against x=78, and 240 pixels
at 1920), several primary button heights and arrow styles, the two price
formats, the dark bands (21 percent of the homepage), the Pricing button below
the first screen, the Sign in spacing, the grey strip on Administration and
the Hooks badge.

It added points this review then checked and adopted: the footer growth
(finding 10); a third question-list style (blue triangles on Docs); secondary
columns off the grid (the hero aside at x=876, the library count card at
x=976 where the card grid uses x=952, the questions card at x=528 where the
grid uses x=508); a gap from header to first content that varies from 49 to
about 100 pixels by page; the blue Not connected badge, which release 17
showed in grey; dark cards that say Live where light cards say Available now;
and engineering text on the signed-out Workspace (`deterministic_character_hash`,
"External identity flow qualified: no").

Where the two reviews disagree:

| Subject | Desktop reviewer | This review | Reading |
|---|---|---|---|
| Type scale | Mostly consistent by eye | Fragmented: four `h1`, ten `h2`, ten `h3` and twelve paragraph sizes | The visible hierarchy holds; the values are not on a closed scale. Both are true. |
| Primary button heights | Six, estimated from pixels: 44, 46, 48, 50, 52, 54 | Seven computed styles: 44, 46, 48, 52 (two paddings), 56, and 48 at radius 10 | Computed styles are exact; the conclusion is the same. |
| Longest line | "Choose a step" on How it works, about 165 characters | Closing disclaimer, 202 characters of capacity | Different measures (visible characters against capacity); both exceed 75. |
| Savings from merging Pricing and Questions | About 450 pixels | About 900 pixels, merging Trust as well | Different scope. |

The phone review agreed on: the clipped code blocks with no scroll cue, the
homepage at 14 phone screens, the dark How band at 2.4 screens, the Sign in
spacing and its oversized service-key button, the footer of about 812 pixels on
every phone page, the Pricing button 1.5 screens down with the price spelled
out, and every mismatch of the website line (header, footer without the
privacy link, type, buttons, the test notice and file names). Its estimate for
shortening the phone homepage, about 3,000 pixels, is close to this review's
3,300.

It added points this review then checked and adopted: on the phone the Get
started page's step 2 card is about 2,480 pixels and its three-step progress
list moves to the bottom of the page; the harness tabs wrap Claude Code onto a
second row; the open menu keeps the three-line icon, has no dimmed backdrop and
cuts through a line of text; the menu says Docs where the footer says
Documentation; and the website line's homepage states "Payment is open" and
that the library holds one example item, which live no longer says.

Where the phone review disagrees:

| Subject | Phone reviewer | This review | Reading |
|---|---|---|---|
| Most severe problem | The signed-out Workspace, whose most prominent button (Search) is disabled at about 2.2 to 1 contrast and looks broken | Low severity (finding 16), because signed-out visitors reach it only through a direct address | Both call for a signed-out state; the ranking depends on how often visitors land there, which no record here measures. |
| The dark How band | Make it light and keep only the code block dark | Keep it dark and show the steps as a compact list | Either shortens it; a light band also removes most of the dark space in finding 9. |
| Phone band padding | About 52 pixels, from the image | 48 pixels computed, plus margins | Measurement method. |
