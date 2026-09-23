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
light band. Today the homepage has two dark bands, How it works and the
closing action, so it fails `dark_bands_stay_within_the_limit`.

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
  one primary action. On the homepage and on Pricing it also shows the price.
- At 390 by 844 the first screen shows the h1 and the primary action.
- At every window size the first screen shows a primary action. The header's
  action counts, and on a phone it stands beside the menu button.
- At 1440 the homepage and How it works are at most 4,000 pixels tall, and
  every other page at most 2,700 pixels (three screens). At 390 a page is at
  most twice its desktop budget in screens of 844 pixels: 7,502 pixels for the
  homepage and How it works, 5,064 for any other page.
- Documentation pages, the privacy notice and the terms have no height
  budget. Once one is taller than 2,700 pixels at 1440, it opens with an
  in-page contents list: a `nav` of links to parts of the same page that
  starts in the first screen.

The live measurements of release 20 that led to these rules, recorded on
September 23, 2026: the homepage was 7,046 pixels at 1440 (7.8 screens) and
11,836 at 390 (14 screens), the price first appeared at 5,001 pixels, the
hero band was 1,249 pixels tall and How it works was 6,144 pixels.

## Buttons, cards, badges and forms

- One primary action per view. A primary action is `.button.primary` or
  `button.primary`, on `--button` with `--button-ink`. The same action
  repeated (the same words to the same address) counts once. A disabled
  primary button still counts, so a step that cannot run yet uses the quiet
  style. Other actions are `.button.secondary`, `.quiet` or `.text-link`.
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
- At 860 and below the links fold into a menu opened by a 44 by 44 pixel
  button. A checkbox opens it, so it works without the page script. The mark,
  the primary action and the menu button stay in the bar; every other entry is
  inside the menu, at least 44 pixels tall.
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
| Product | Get started, Get set up, How it works, Library, Pricing, First example |
| Use cases | Use cases, the four benefit pages and the four audience pages |
| Documentation | Docs, the six documentation pages, Access and data, Status |
| Company | What Baltor is, Request an invitation, Sign in, Privacy notice, Terms of service, Open-source notices |

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
- One primary action.
- The title is "Baltor | " and the page title of the site map, and the page
  names `https://baltor.ai` and its address as its canonical address.
- Every page other than the homepage opens with the white introduction band.

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
- The price is written "$29 a month". A customer page never writes "United
  States dollars".
- The words terminology.yaml refuses on a surface do not appear there; the
  conformance gate already refuses them.
- `tools/check_hosted_website.mjs` and `tools/check_service_workspace.mjs`
  still expect the words "29 United States dollars". They change in the same
  change as the copy.

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
