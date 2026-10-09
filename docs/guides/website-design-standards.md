# Website design standards

Kind: operating guide. It states how the Baltor website looks and what it
holds, as it is on September 23, 2026 and as it should be. The owner asked for
it that day, after a redesign dropped header links, footer links and pages
that no check noticed: "create design standards ... you should be able to
catch things like white space issues, margin/padding issues, consistency,
missing pages, lost pages, regressions".

Every rule here that can be measured is also written as data and checked:

```text
Website design standards
├── This guide: the rules in plain words, and why
├── Records, read by one typed reader (web_site_map.py)
│   ├── web_site_map.json: pages, header, footer, hostnames, dated removals
│   └── web_layout_standard.json: widths, padding, budgets, contrast, typefaces
└── Checks
    ├── tools/test_website_site_map.py: the rules, known-wrong sites, mutant controls
    ├── tools/check_website_site_map.py: the served pages against the site map
    └── tools/check_website_layout.mjs: the pages in a browser at five window sizes
```

The records are
[web_site_map.json](../../src/loop_engine/core/service_runtime/web_site_map.json)
and
[web_layout_standard.json](../../src/loop_engine/core/service_runtime/web_layout_standard.json).
A number in this guide that disagrees with a record is a mistake in this
guide: the record is what the checks read. Change a rule by changing the
record, this guide and the pages in one change.

The [product style guide](product-style-guide.md) keeps the product voice and
the rule on marketing language and factual claims. The
[writing context](../../humanizer-context.md) keeps the punctuation, and
[terminology.yaml](../../terminology.yaml) keeps the words each surface may
use.

## Colour tokens and dark bands

Every colour, typeface, radius and shadow is a custom property in the token
block at the top of `service.css`. `architecture.css` holds the components and
reads the same tokens. A rule never writes a colour of its own.

The homepage, account pages, directories and deck use the same selected
appearance. The light palette uses warm neutrals and the ember accent; the
dark palette uses the matching dark tokens. The homepage hero and header do
not force a dark appearance over a light selection. Code samples keep their
own code surface. `site-chrome.js` owns the appearance control and saves only
`baltor.appearance` in this origin's browser storage. Full-page navigation and
reload retain it; other tabs on the same origin follow changes. Unsupported
or unavailable storage leaves the light default and a working control. No
account preference or tracking request is created.

`tools/check_site_appearance.mjs` checks both appearances at desktop and phone
widths across the homepage, pricing, feeds, directories, Public Good and deck.
It also checks system appearance, reload, tab synchronization, storage refusal
and a known-wrong forced-dark hero. Colour contrast remains owned by
`tools/test_design_tokens.py` and the website layout browser checks.

The live people check selects the site's supported `baltor.appearance`
preference in its isolated browser context. It verifies the applied document
theme, control label, rendered ground and sampled body/headline contrast before
labeling an image light or dark. Browser `colorScheme` alone does not override
the site's light default. `tools/browser_appearance_checks.mjs` also refuses
an ignored selection, a contradictory ground and low contrast.

| Use | Tokens |
|---|---|
| Grounds | `--bg`, `--ground`, `--paper`, `--band`, `--panel-head`, `--soft` |
| Text | `--ink`, `--muted`, `--subtle` |
| Lines and fields | `--border`, `--rule`, `--line-strong`, `--field-edge` |
| Action | `--accent`, `--accent-hover`, `--button`, `--button-hover`, `--button-ink` |
| States | `--ok`, `--ok-soft`, `--info`, `--info-soft`, `--planned`, `--planned-soft`, `--error` |
| Dark ground | `--night`, `--night-card`, `--night-rule`, `--night-ink`, `--night-muted`, `--night-accent` |
| States on a dark ground | `--night-live`, `--night-live-soft`, `--night-building`, `--night-building-soft`, `--night-planned`, `--night-planned-soft` |
| Code | `--code-bg`, `--code-ink`, `--code-rule` |
| Decoration and depth | `--dot`, `--shadow`, `--card-shadow`, `--panel-shadow` |

The owner asked for fewer black spaces. A page has at most one dark band: a
block as wide as the window, at least 120 pixels tall, on `--night`. It holds
the closing action of the page and nothing else. A code panel, a terminal
sample and the folder of one step may use `--code-bg` or `--night` inside a
light band. Since September 24, 2026 the homepage has one dark band, the
closing action; the hero's working directory is a panel inside a light band.

## Type scale and line length

| Role | Token or value |
|---|---|
| Interface text | `--font-ui`: Geist, then system faces |
| Code, commands, identifiers | `--font-mono`: Geist Mono, then system faces |
| Homepage heading | `--text-hero`, 40 to 64 pixels |
| Section heading | `--text-h2`, 30 to 44 pixels; `--text-h2-small`, 28 to 40 pixels |
| Lead line | `--text-lead`, 17 to 20 pixels |
| Body | 16 pixels, line height 1.55 |
| Small text, captions | 14 pixels (0.875rem) |
| Eyebrows, badges, status tags | 12 to 13 pixels, never smaller than 12 |

Only Geist and Geist Mono are used for text. Older rules in `service.css`
still name `ui-monospace` and `system-ui` for some labels; they fail
`text_uses_only_the_standard_typefaces` until they read `--font-mono` or
`--font-ui`.

A full line of running text holds at most 80 characters. A reading column is
at most 640 pixels wide (40rem at 16 pixels) and a lead line at most 760
pixels (47.5rem). The `.reading` column is 840 pixels today, about 100
characters a line.

## Spacing scale and section padding

One spacing scale, in pixels: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64. Gaps,
card padding and margins take their values from it.

A section is the page frame (`main`), the footer, and every block inside the
main column that spans the window or paints a band that does. Its top and
bottom padding each take one of these values:

| Window | Allowed section padding, in pixels |
|---|---|
| Desktop, 1440 wide | 0, 32, 40, 48, 64 |
| Phone, 390 wide | 0, 16, 24, 32, 40 |

A fluid value may move between the two, but at 1440 and at 390 it lands on an
allowed value. Band padding is therefore at most 64 pixels on a desktop and
40 on a phone. Today `--band-pad` gives 112 pixels on a desktop, the hero
band 87.84 and 96, the harness strip 30, the Get started introduction 72, and
the introduction band of an inner page 28 on a phone. No stretch of the page
between two pieces of text, pictures, controls or cards is taller than 240
pixels at 1440.

## Containers and the shared left edge

Content is at most `--content-max` wide (1312 pixels) and sits inside the
gutter `--band-gutter`: 64 pixels at 1440, 16 pixels on a phone (the clamp
gives 17.4 today, which the 2 pixel tolerance accepts).

The header brand, the h1 of every page and the footer brand start on one left
edge, within 2 pixels. At 1440 that edge is 64 pixels from the window. A
reading page narrows its column from the right, not by centring it. Today the
inner pages start at 77.6 pixels, because `main` uses a 4vw gutter inside
1400 pixels, and the reading pages start at 300 pixels.

## Scroll budget and the first screen

The owner, September 23, 2026: "improve the design so people don't have to
scroll down so far to get all of the details."

- At 1440 by 900 the first screen shows the page's h1, its lead line and its
  primary task action. Pricing is a separate section below the homepage
  introduction, never a stack of plan cards inside the hero. On Pricing, the
  first screen starts the comparison and shows its first price.
- At 390 by 844 the first screen shows the h1 and the primary action.
- At every window size the first screen shows a primary action. The header's
  action counts, and on a phone it stands beside the menu button.
- At 1440 the homepage and How it works are at most 4,000 pixels tall;
  ordinary pages are at most 2,700 pixels (three screens). A page explicitly
  assigned the `case-study` budget may reach 6,000 pixels. The data cleanup,
  Pi and Gemma 4, and sign-up protection studies use this budget.
- At 390 the limit is twice the desktop budget divided by the desktop
  viewport height, then multiplied by 844 and rounded to the nearest pixel:
  7,502 pixels for the homepage and How it works, 5,064 for an ordinary page,
  and 11,253 for a case study. Both browser checks read the named budget from
  the site map and use this formula.
- Documentation pages, the privacy notice and the terms have no height
  budget. Once one is taller than 2,700 pixels at 1440, it opens with an
  in-page contents list: a `nav` of links to parts of the same page that
  starts in the first screen. The detailed decision red-team report retains
  this existing documentation classification and its introductory contents
  navigation.

The owner, September 26, 2026: "We can increase our scroll length budget,
especially for pages like a case study." The finite 6,000-pixel case-study
limit gives the measured 5,120-pixel sign-up protection study 880 pixels of
room for explanation and evidence. Its measured phone height was 5,972 pixels.
This allowance does not change the homepage or ordinary-page limits. The
site map is `service_web_site_map/v3` and the layout standard is
`service_web_layout_standard/v2`; earlier records are refused.

The live measurements of release 20 that led to these rules, recorded on
September 23, 2026: the homepage was 7,046 pixels at 1440 (7.8 screens) and
11,836 at 390 (14 screens), the price first appeared at 5,001 pixels, the
hero band was 1,249 pixels tall and How it works was 6,144 pixels.

## Buttons, cards, badges and forms

- Give each page one primary task. Its introduction makes that task clear;
  other actions use `.button.secondary`, `.quiet` or `.text-link`. Primary
  controls use `--button` with `--button-ink` and an explicit action label.
- Comparison cards may each have one emphasized choice action for their
  distinct offering. Keep the cards together under a comparison heading,
  give each a clear name and destination, and keep secondary explanations
  visually quieter. These choices serve the page's comparison task; they
  are not permission to style unrelated links as primary actions.
- A shared header, footer and closing section may retain their navigation
  and access actions. Repeating the page's main action near the end is
  allowed. Do not remove useful navigation or hide choices to satisfy a
  whole-page button count.
- A disabled primary button still needs a clear unavailable state. A step
  that cannot run yet uses the quiet style and explains the missing
  prerequisite. It must not resemble an available purchase or execution.
- Buttons are at least 44 pixels tall (48 for the page's own actions) with
  `--radius-button`; fields use `--radius-field`.
- Cards are `--paper` with a 1 pixel `--border`, `--radius-card`, and padding
  from the spacing scale (24 to 32 pixels on a desktop, 16 to 24 on a phone).
  Panels use `--radius-panel`.
- Status tags say what exists: `is-available`, `is-live` and `is-recorded`
  (`--ok` on `--ok-soft`), `is-building` (`--info` on `--info-soft`),
  `is-planned` (`--planned` on `--planned-soft`), with the night pairs on a
  dark band. Only parts that work on the live service say Available now or
  Live.
- Every field has a visible label. Its edge is `--field-edge`, which meets 3
  to 1 against white and the ground.

Check action hierarchy by decision scope: the page introduction, each
comparison card and the shared navigation. Preserve the one-primary-task
limit for ordinary page content. The full-layout checker currently counts
all `.primary` controls in a view together. Keep those findings visible while
its scope checks are reconciled; do not raise the global limit to an arbitrary
button count. Known-wrong controls must still reject unrelated competing
actions, multiple emphasized actions in one card, missing destinations and
hidden choices. Contrast, touch targets, focus, overflow and link checks apply
to every control in every scope.

## Header anatomy

The entries, in order, are the `header` lists of the site map:

| State | Entries |
|---|---|
| Signed out | Baltor mark and name, How it works, Use cases, Library, Pricing, Docs, Sign in, and the primary action Get started (`/get-started`) |
| Signed in | Baltor mark and name, Workspace, Get set up, Library, Docs, Account, Sign out |
| Operator | the signed-in entries, with Administration between Account and Sign out |

The primary action is Get started in every access state. Its label never
switches; the Get started page adapts when account creation is closed.

The markup declares the state of an entry: `data-signed-out` for a visitor,
`data-signed-in` for a signed-in person and an operator, `data-operator` for
an operator alone. An entry marked `hidden` with no state marker is read as an
operator's entry, which is how the Administration link is written today.

- At 1440 and 1024 every entry, Sign in and the primary action sit on one row
  inside the bar.
- At 860 and below the links fold into a menu opened by one visible 44 by 44
  pixel button named "Menu", with `aria-expanded` and
  `aria-controls="main-nav"`; the name and the state sit on the control a
  person touches. Without the page script the footer links every page the
  menu holds. The mark, the primary action and the menu button stay in the
  bar; every other entry is inside the menu, at least 44 pixels tall.
- The header stays in view at every size: it is sticky, or it steps aside
  while the page scrolls down and comes back when it scrolls up. On a phone
  held sideways (844 by 390) the bar is at most 52 pixels tall unless it steps
  aside. The owner's limit is about 12 percent of the screen height; the check
  uses 52 pixels for this screen.
- A link to a part of a page lands with that part below the bar, so each
  target carries a `scroll-margin-top` at least as tall as the bar.

## Footer anatomy

Four groups, each a `nav` whose `aria-label` equals its visible heading, and a
base row. No link stands outside the groups except the brand.

| Group | Links |
|---|---|
| Product | Get started, Get set up, How it works, Library, Pricing, Demonstration, Examples |
| Use cases | Use cases, the three use case pages, Case studies, the four audience pages |
| Documentation | Docs, the six documentation pages, Access and data, Status |
| Company | What Baltor is, Sign in, Privacy notice, Terms of service, Open-source notices |

The base row shows the mark, "Baltor.AI", the year and the operator's postal
line, which the privacy notice publishes.

## Page template

- Every page is a view marked `data-view`, including a page with a packaged
  file of its own, and every page address is in the served address table,
  `WEB_ASSETS` in `web_pages.py`. A new view takes the id of its address
  without the first slash, with each further slash written as a hyphen.
- One h1 per view. A view with alternative states shows one at a time, the
  others inside hidden elements.
- A short lead line: the first paragraph after the h1, one or two sentences.
- Sections under h2 headings that carry an id, so the dated inventory can
  follow them.
- One primary task with the action hierarchy described above; comparison
  choices and shared navigation retain their own controls.
- The title is "Baltor | " and the page title of the site map, and the page
  names `https://baltor.ai` and its address as its canonical address.
- The service writes the title, the page's one-line description from the site
  map (at most 160 characters), the canonical address and the shared-link
  tags into the served page itself, so a search engine and a shared link read
  them before any script runs. A page the site map does not list for search
  engines carries `noindex`. A page with a file of its own gets the same head
  once the site map lists it.
- Every page other than the homepage opens with the white introduction band.

## Hostnames, robots.txt and sitemap.xml

The `hostnames` list of the site map gives the page each hostname shows at its
root address, since September 24, 2026:

| Hostname | Root page |
|---|---|
| `baltor.ai`, `www.baltor.ai`, `app.baltor.ai` | the homepage |
| `docs.baltor.ai` | `/docs` |
| `status.baltor.ai` | `/status` |
| `examples.baltor.ai` | `/examples` |
| `demo.baltor.ai` | `/demo` |
| `deck.baltor.ai` | `/deck` |
| `redteam.baltor.ai` | `/case-studies/decision-red-team`, rendered from its packaged record (September 26, 2026) |

A hostname the list does not name shows the homepage. Every other address
shows its own page on every hostname, and every page names its address on
`https://baltor.ai` as canonical. `/robots.txt` and `/sitemap.xml` are written
from the site map: the sitemap lists each page marked `indexed`, and
robots.txt leaves out the interface routes and each page that is not.

## Pages reached by their address only

The owner, September 26, 2026, asked for a public changelog, feature list and
to-do page that "can be undiscoverable (no page linking to them)". Since that
day `/changelog`, `/features` and `/todo` are pages of the site map with no
place that links to them, that sentence as their reason, and `indexed` false,
so they carry `noindex` and stay out of `sitemap.xml`. Like every page the
site map does not list, `robots.txt` still names them, because the rule that
writes it has no second kind of unlisted page; the owner's words define
undiscoverable as no page linking to them, and no page does. They use the site's
frame, header and footer, open with the introduction band, hold no primary
action of their own and follow the documentation scroll budget with an
in-page contents list.

`status_pages.py` renders them from one packaged record that
`tools/build_public_status_pages.py` writes from the release records, the
Community release records, `CHANGELOG.md`, the site map, the capabilities
builder, the attribute declarations, the client recipes and the roadmap. The
continuation status generator and the records index builder run the same
command, so their `--check` fails while the pages are stale. The roadmap steps,
release lines and `CHANGELOG.md` lines that describe an open security or
privacy weakness, an abuse path, a staff-only route or a private matter of the
owner are named, each with its reason, in the reviewed
[exclusion list](../roadmap/public-status-exclusions.json), with the parts of
the capabilities record that the feature list leaves out, such as the search
backend, which no page names. That list, not a match on words, decides what
those pages leave out for those reasons. A line or
a title that carries an internal term, such as a file name, a revision or a
word the public wording rules refuse, is also left out, and the page says how
many lines it does not repeat.
`tools/test_build_public_status_pages.py` fails when a page, the header, the
footer, the documentation index, `sitemap.xml` or a packaged file links to one
of the three addresses.

## Accessibility

- All text, large text included, meets 4.5 to 1 against its ground.
- Touch targets on a phone are at least 44 by 44 pixels. A link inside a
  sentence is exempt.
- Focus is visible: a 3 pixel outline in `--accent`, `--night-accent` on a
  dark band.
- Colour is never the only sign of a state; every status has words.
- Motion respects the reduced motion preference.

## Responsive rules

The checks measure at five window sizes: 1440 by 900, 1024 by 768, 860 by
900, 390 by 844, and 844 by 390 for a phone held sideways. No page scrolls
sideways at 390. Grids fall to one column when a card would be narrower than
its content.

## Copy rules

- Short sentences in plain words, as the [writing context](../../humanizer-context.md)
  says.
- The full-library price is written "$29 a month". Agent Feeds has a standard
  price of "$4.99 a month" and is free through December 31, 2026, in Eastern
  time. No automatic charge follows that period; paid enrollment requires
  explicit opt-in and is not open yet. The current source collections and
  catalogue feed are distinct from personalized subscriptions still in
  development. A customer page never writes "United States dollars".
- The words terminology.yaml refuses on a surface do not appear there; the
  conformance gate already refuses them.
- `tools/check_hosted_website.mjs` and `tools/check_service_workspace.mjs`
  check the full-library price and measured download unit separately from
  the feed price, free period, consent and availability wording.

The homepage opens with a short outcome-led heading and names the three
audiences beside it. Get started opens the existing account flow; Get set up
opens the connection guide. The separate pricing section presents three
distinct offerings: Agent Feeds, Harness Files, and Overnight / AFK Work.
State the included lower offerings on each card. Use the same names and scope
on the pricing, feeds, library and overnight pages without repeating a full
pricing grid on every page.

Agent Feeds shows its $4.99 standard monthly price, free period and paid
opt-in. Harness Files includes Agent Feeds and the full library at the current
$29 monthly checkout price. Overnight / AFK Work is an included local Preview
at no extra charge with Harness Files. Its card names run limits, task
checkpoints and morning reports, with the customer's own worker and model
access. It is not a paid hosted supervision service. A different proposed
price stays out of a purchase path until billing, access and delivery agree.

Different card treatments identify the offerings; they do not establish
popularity or measured value. Do not add Most popular, Best value or adoption
claims without evidence. Marketing counts distinct files, not packages. Exact
package groupings remain in technical retrieval records and the library's
technical disclosure. An unmeasured file population stays unknown.

`tools/check_offering_launch.mjs` measures header bounds and the three offers at
80, 100 and 125 percent zoom-equivalent desktop layouts, tablet, phone and
landscape sizes, in both actual appearances. It preserves screenshots and
source digests, and rejects a deliberately clipped header, a missing third
offering, pricing cards in the introduction hero, and removed pricing or
consent wording. Preview checks distinguish local tools from hosted execution.
These are headless viewport/density emulations, not a measurement of the
owner's browser session.

## Regression rule

No page, route, header link, footer link or section is removed without a
dated row in the `removed` list of the site map: its date, its kind, its
subject, the header state for a header link, the reason, and who decided.

The dated inventory
[site-inventory-release-20.json](../../artifacts/website-audit-2026-09-23/site-inventory-release-20.json)
records what release 20 served: 16 pages, 24 header entries, 10 footer links
and 32 sections. The rule `nothing_in_an_inventory_is_lost` compares every
inventory with the site map and the served pages. A release that changes the
website adds its own inventory:

```bash
PYTHONPATH=src python tools/test_website_site_map.py --write-inventory \
  artifacts/website-audit-DATE/site-inventory-release-N.json \
  --release "Fly release N" --revision SHA
```

## The checks

```bash
PYTHONPATH=src:tools python -m unittest tools/test_website_site_map.py
PYTHONPATH=src:tools python -m unittest tools/check_website_site_map.py
node tools/check_website_layout.mjs --local NEW_REPORT.json
node tools/check_website_layout.mjs --url https://baltor.ai NEW_REPORT.json
```

The first passes and runs with the other tools tests. The second compares the
served website with the site map and fails on release 20 until the restored
pages merge; its run is saved in
[site-map-check-on-main-243a8811.txt](../../artifacts/website-audit-2026-09-23/site-map-check-on-main-243a8811.txt).
The third and fourth measure the pages in a browser. The state of each check
is in the
[handoff of September 23, 2026](../verification/HANDOFF-SITE-STANDARDS-2026-09-23.md).
