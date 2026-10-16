# Launch audit of baltor.ai, October 16, 2026

The owner asked on October 8, 2026 to "get this ready for launch,
adversarially validate every single page, all marketing language,
nomeclature, ideas, standards, index, documents, how to, test it out,
variations, side by side comparisons". This record covers `https://baltor.ai`
and `https://www.baltor.ai`, read signed out. The brand sites (AgentFeeds,
AgentFoundry, AgentAFK, AgentStudios and the campaign site) and the signed-in
customer journey belong to two other audits of the same day.

Status: every page of the site map was opened, measured and read. Fourteen
defects are fixed in source with tests in the four commits named below. They
reach visitors only with the next application release and edge export. The
open findings are listed by severity with the reason each stays open.

## What was live

The live service was Fly release 93 from
`bdc4595574d1017837286263a901cb59f6eef41c`, as the
[current deployment](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
section records. Its edge Worker served export `6e2fc6fc9885`, 3,278 files.
`/api/v1/health` reported the catalogue release `29a2bc33…` with 256,380
packages holding 1,560,856 distinct files, the population the task named.
The homepage, the library page and Harness Files showed those counts. The
plan prices on the homepage and the pricing page were $9, $49 and $99 a month.
The audit worktree started at public `main` `f2ae304e`.

## Method

All reads were GET or HEAD, from one workstation, between 10:25 and 12:10
Eastern. No form was submitted, no account was created and no credential was
used.

| Pass | Tool | Scope | Result |
|---|---|---|---|
| People check | [`check_live_site_for_people.mjs`](../../tools/check_live_site_for_people.mjs) as it stood at `f2ae304e` | 75 site map pages at 1366 and 390 pixels in light and dark, plus 9 hostname roots: 309 views, 838 links | No problem found |
| Deep crawl | A private Playwright script (Chrome, `playwright-core`) | 101 addresses: the 77 site map pages, 6 model pages, 3 endpoint pages, 6 gallery items, 2 unknown addresses and 7 subdomain roots, at 1440 by 900 and 390 by 844 in light and dark: 390 views | Text, metadata, headings, landmarks, labels, images, contrast in the light desktop view, focus, overflow, console, failed requests, bytes and caching |
| Layout standard | [`check_website_layout.mjs`](../../tools/check_website_layout.mjs) `--url` | Stopped after 13 pages when a footer click timed out on `/demo/ashen-wilds` under machine load; the click works alone | 590 of 630 checks passed |
| Second pass | A private script reusing the new squeezed-text rule | 79 addresses at 1366 and 390 pixels, phone touch targets, 17 signed-out interactions | Below |
| Homepage states | [`check_homepage_selections.mjs`](../../tools/check_homepage_selections.mjs) | Every harness and task state at 1440 and 390 | Below |
| HTTP | A private script | 137 addresses by GET and HEAD, the 2,722 addresses of the model and gallery site maps by HEAD | Below |
| Links | A private script | 1,412 internal and 235 external links, one request each, and 1,985 links to a part of a page | Below |
| Wording | A private scan of the rendered words, titles, descriptions, social tags, alternative text and labels | The rules of [`public_wording_rules.mjs`](../../tools/public_wording_rules.mjs), the owner's rules on "packages", "reviewed", prices and dashes | Below |

The owner rules applied were: the website copy and hero direction, compact
pages and the scroll budgets, a redesign keeps every page, no "reviewed"
counting, marketing language is not a claim, harness and agent optimized
operation, one way in, the current best value and step by step releases.
[`terminology.yaml`](../../terminology.yaml) and
[`humanizer-context.md`](../../humanizer-context.md) gave the vocabulary and
the voice. Legal text was read and flagged, never edited.

## Page inventory

| Kind | Count | How it was covered |
|---|---|---|
| Site map pages | 77: 60 indexed and listed in `/sitemap.xml`, 17 not indexed (old addresses, account pages, staff and unlinked pages) | Opened in every pass; the two `/auth/` pages in the deep crawl only |
| Model directory pages | 2,346 in `/models/sitemap.xml`: 2,147 models, 198 endpoints and `/can-i-run` | All answered HEAD with 200; 9 opened in the browser |
| Gallery item pages | 376 in `/gallery/sitemap.xml` | All answered HEAD with 200; 6 opened in the browser |
| Feeds | 60 files under `/feeds/` beside `/feeds` and `/feeds/setup`, and the three library updates feeds | The collection index and the library updates feed read by GET |
| Discovery documents | `robots.txt`, three site maps, `llms.txt` and three OAuth discovery documents | Read and compared with the site map |
| Hostnames | 9 Baltor hostnames; `www.baltor.ai` answers 301 to `https://baltor.ai/` | Every root opened; every page names its canonical address on `baltor.ai` |
| Error pages | The unknown-address page, for a page and for a documentation address | Opened in the browser |
| Pictures and icons | Four share cards, the deck card, the mark and three favicons | Fetched; the cards were inspected |

## What held

- Every page of the site map opened with a heading and no script error, in
  both appearances and at both widths, and no page scrolled sideways on a
  phone or a desktop.
- 1,412 internal links answered 200. Every link to a part of a page found its
  target in the rendered page. Every address of the model and gallery site
  maps answered 200.
- The canonical address, the Open Graph and card tags, the description and
  the language were present on every site map page, and the canonical address
  of every hostname copy points to `baltor.ai`.
- The page heads carry a strict content policy, `nosniff`, `DENY` framing,
  `no-referrer` and a permissions policy. No public page sets a cookie. HTML is
  compressed with Brotli or Zstandard, and the median page sends 68 KB.
- Sampled text contrast passed in the light desktop view, and the people check
  passed the sampled body and headline in both appearances.
- The sign-up and sign-in forms label their fields and refuse an empty or
  malformed address before anything is sent. The menu opens, Escape closes it
  and returns focus, the appearance button switches the theme, the homepage
  harness buttons repaint the folder, Copy copies the configuration with no
  key in it, the directory search narrows the list, the hardware check answers,
  a random preview changes on request, Public Good search answers and the deck
  moves with the arrow keys.
- Live prices, plan names and the library counts agreed on the homepage, the
  pricing page, the library page and Harness Files.

## Findings

Severity: high blocks a launch or exposes visitors; medium is a visible defect
or a real risk; low is polish. Commits: A is `57805fc3`, B is `d29f084c`, C is
`55b7b400` and D is `1e7951e3`, all on top of `f2ae304e`.

### Fixed in source

| ID | Page | Check | Severity | Evidence | Fixed in | Reason |
|---|---|---|---|---|---|---|
| F1 | `/case-studies/sign-up-protection` | Layout | High | The four steps wrapped one to three letters to a line at every width: 57 characters in 17 lines on a phone and a desktop | A | The list item was a two-column grid, and the step's text fell into the 2rem number column. The number now sits in a gutter. The people check refuses text squeezed below six characters a line |
| F2 | `/case-studies/decision-red-team`, `/models`, `/endpoints`, endpoint pages, `/can-i-run` | Layout, phone | Medium | "the written patterns given to every decision maker" in 24 lines of two letters | A | Table cells inherited `overflow-wrap:anywhere`; they now keep whole words |
| F3 | Documentation tables | Layout, phone | Low | "Compon/ent", "Entitlemen/t", "Handsha/ke" | A | The same inheritance in the documentation view |
| F4 | `/worker`, `/top-mcps` | Metadata | Medium | Browser title "Baltor \| undefined" after the script ran | B | The script's view title table lacked both views; a test now holds the table to the site map |
| F5 | `/deck` | Script | Low | The footer kept "Checking service availability" | B | The deck's one capabilities read now fills it; a test refuses a page whose scripts leave the line alone |
| F6 | `/` | Content | Low | The folder repainted with "└──" on every row | B | The repaint draws the served connectors; the homepage state check refuses a malformed tree |
| F7 | `/docs/serving-and-connections` | Anchors | Low | The "Protocol versions" contents link scrolled to a hidden card with the same id | B | The card's id changed; a test refuses a documentation body that repeats an id of its page |
| F8 | `/status` | Formatting | Low | "Items 256380" | B | Now 256,380 |
| F9 | `/for/designers` | Navigation | Low | The only audience page that led back to "Baltor" | B | It leads back to Use cases like the others |
| F10 | `/public-good`, `/random`, `/random/image`, `/feeds` and the library updates feeds | Wording | Medium | "1,128 distinct useful files in 448 packages", "Source package licence", "256,380 packages and 1,560,856 distinct files" | C | The owner's files-first direction of October 8; now files and harness components |
| F11 | `/random/video`, `/random/music` | Wording | Medium | "Browse reviewed public video previews" in the description, social tags and `/features` | C | The owner's rule against "reviewed" as a qualifier |
| F12 | `/llms.txt`, `/pricing` description | Names | Low | "Agent Feeds is $9 a month … Pro is $49 a month", no Max; "No automatic feed-only charge" | C | Plans are named by their plan names with their prices; a test refuses the old sentence |
| F13 | `/deck` | Facts | Low | Fallback counts 1,557,669 files and 255,967 components | D | The later October 9 record holds the served counts, 1,560,856 and 256,380 |
| F14 | Shared-link pictures | Brand | Low | `share-card.png` said "Give your agents a head start."; `deck-card.png` kept the navy tile and blue colours | D | Redrawn by their renderers from the current headline and mark |

### Open

| ID | Page | Check | Severity | Evidence | Reason it stays open |
|---|---|---|---|---|---|
| O1 | Every page and route | Security | High | `http://baltor.ai/` answers 200 with the full page, so do `/login`, `/get-started`, `/api/v1/health` and `/mcp`; no response carries `Strict-Transport-Security` | A provider step for the coordinating session: Cloudflare's always-HTTPS redirect and HSTS for the zone, or a redirect in the edge Worker. A token sent to `http://baltor.ai/mcp` travels in clear text today |
| O2 | 15 of 48 budgeted pages | Scroll budget | Medium | Desktop and phone heights over budget: `/feeds` 9,305 of 4,000 px, `/public-good` 9,198, `/how-it-works` 6,292, `/gallery` 6,002, `/setup` 5,117 of 2,700, `/harness-files` 4,851, `/feeds/setup` 4,171, `/overnight` 3,951 of 2,700, `/pricing` 2,842, the two directory addresses 2,853, `/dot-context` and `/dot-feedback`, `/connect` like `/setup`, and `/` on a phone only | Needs layout work that compresses without cutting content |
| O3 | 49 pages | Touch targets, phone | Medium | 515 targets below 44 pixels that are not links inside a sentence: text links 21 to 25 pixels tall, documentation side links and Copy buttons 36, the hero's "pi" button 41 wide | A design-standard change across the shared styles |
| O4 | `/directory` | Weight | Medium | 3.2 MB sent on load: eight row files of about 400 KB each | Needs paged or on-demand rows |
| O5 | `/support` | Content | Medium | Only postal mail and the public issue tracker; no support email address. "Add Baltor from ChatGPT" reads as a directory listing | The coordinating session handles the support address. If the ChatGPT directory listing is not published, the sentence should say to add the endpoint as a custom connector |
| O6 | `/privacy`, `/terms` | Legal, flag only | Medium | The privacy notice keeps a waiting list "To invite people in small groups"; the terms say "access to reviewed material"; the privacy markup repeats the id `privacy-contact` | Owner-approved legal text changes only with the owner |
| O7 | 12 page views | Line length | Low | Paragraphs of 83 to 103 characters a line at 1440 pixels | Shared reading-width styles |
| O8 | API and OAuth discovery | HTTP | Low | HEAD answers 404 where GET answers 200 for `/api/v1/health`, `/api/v1/capabilities`, `/api/v1/connect/openapi.json` and the OAuth discovery documents | An application release |
| O9 | Site root | HTTP | Low | `/favicon.ico` and `/.well-known/security.txt` answer 404 | An application release |
| O10 | Assets | Caching | Low | Content-versioned assets (`?v=` and their SHA-256) are cached for 300 seconds | Could be cached for a year as immutable; an application release |
| O11 | `/feeds/sources.json` | Compression | Low | 79 KB sent uncompressed | The edge does not compress `application/feed+json` |
| O12 | Model, endpoint and some gallery pages | Metadata | Low | No `og:image` or card tag | Their renderers write no social picture |
| O13 | Model directory | Data | Low | Test fixtures such as `trl-internal-testing/tiny-Gemma2ForCausalLM` are listed; one licence link answers 404 (`Ornith-1.5-397B`) | The daily directory build |
| O14 | `/public-good` | Content | Low | Four near-identical accessibility items and a Portuguese-only description lead the list | Library content, not page code |
| O15 | Documentation tables | Layout, phone | Low | A third column sits behind horizontal scrolling with no sign that it is there | A design choice to revisit |
| O16 | `/public-good`, `/gallery` | Layout standard | Low | Two primary actions in one view; a band padding of 24 pixels | Shared layout work |
| O17 | Documentation | Wording | Low | The account guide still describes the waiting-list fallback; the usage guide mentions accounts "with an operator grant" | Accurate behavior that the owner's one-way-in wording may want reframed |
| O18 | Unknown-address page | Content | Low | Asks the visitor to "tell the person who runs this service" without a link to Support | The template is shared with other hostnames |
| O19 | Names | Nomenclature | Low | The feature is "Agent Feeds" on baltor.ai and the brand site is AgentFeeds | An owner naming decision |
| O20 | `/endpoints/nano-gpt` | Length | Low | 136,912 pixels tall on a phone | A long model table |
| O21 | 59 pages | Console | Information | "Allow attribute will take precedence over 'allowfullscreen'" from the arena frame | Harmless; the legacy attribute helps older browsers |

## Facts checked against live data

| Statement | Where | Live value | Result |
|---|---|---|---|
| 1,560,856 files in the library | Homepage, library page, Harness Files, the library updates feed | 1,560,856 distinct files, 256,380 packages | Agrees |
| $9, $49 and $99 a month | Homepage, pricing page, setup and audience pages | The pricing page and the README of the web assets | Agrees; Max is shown as a free public preview that is not sold |
| Free through December 31, 2026 (Eastern) | Homepage, pricing, feeds | The pricing page | Agrees |
| Protocol versions 2025-11-25 and 2026-07-28 | `/for/protocol-and-client`, `/app` | `/api/v1/capabilities` | Agrees |
| 42,805 listings from 5 sources | `/directory` | The packaged directory record | Agrees with the page's own record |
| 191 hosted services and 6 local runtimes | `/endpoints` | 198 endpoint addresses in the model site map | Agrees |
| Deck fallback counts | `/deck` without its script | 1,560,856 and 256,380 | Stale, fixed in D |

## Evidence

Six small screenshots are kept outside the repository, in
`~/baltor-private/claude-takeover-20261015-dhycum/ops/launch-audit/`: the
squeezed sign-up steps on live and the same steps from a local service built
with commit A, the decision red team table before and after, a documentation
table on a phone, and the live homepage's first screen. The other screenshots
and the raw measurements were deleted at the end of the audit.

## Not checked

- Signed-in pages, checkout, billing, email links and anything that submits a
  form; the customer-journey audit owns the signed-in path.
- The brand sites and the campaign site; the brand audit owns them.
- Real devices, Safari, Firefox and assistive technology; one headless Chrome
  measured every view.
- Field performance; transfer sizes were measured, not load times on real
  networks.
- Text contrast in the dark appearance beyond the people check's sampled body
  and headline, and the layout standard on the 64 pages after it stopped.
- The model and gallery pages beyond their HEAD status and the 15 opened, and
  the content of the 60 feed files.
- The MCP endpoint and the API beyond their public discovery and health
  answers.
