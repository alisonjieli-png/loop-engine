# Service web assets

Packaged public pages and a same-origin authenticated workspace. The HTTP
adapter serves only the named HTML, stylesheet and script. It never serves
the repository, source inventory, configuration files or internal reports.

Service tokens stay in page memory and are cleared on disconnect. Model
provider keys are not collected. Search, downloads, usage and configured
billing sessions use the real versioned service routes. Downloads check the
selected content digest before saving. No file is executed or automatically
installed into a harness.

The workspace is not an identity provider. Tenant creation and subject binding
remain explicit operator operations. A billing session is not an entitlement.
The service's capability record distinguishes configured behavior from live
provider qualification.

## One call to action, the guide and the waiting list page

The owner, September 23, 2026: "Get Setup" is "a guide on how to get setup and
'get started' is the sign up and registration/pay funnel". So every public
link or button that starts the access journey says "Get started" and opens
`/get-started`, the funnel, in every state; the funnel adapts, so no label
switches. The served funnel accepts an email when registration is open,
offers the configured waiting list when closed, and otherwise offers sign-in.
Its confirmation page clears link tokens from the address, verifies the link,
sets the password and then activates the account. A session change invalidates
a pending confirmation; late replies cannot reconnect a disconnected page.

Two pages keep page links of their own, each by its own name:

- Get set up, the guide, at `/setup`. The older address `/connect` still
  opens it. It is not in the signed-out header: a visitor reaches it from the
  Docs page, the homepage and the footer, and a signed-in person from the
  header. Its first step leads with one panel, chosen from the service's
  capabilities record: account creation when `website.registration_available`
  is true, otherwise a link to the waiting list page when
  `website.waitlist_available` is true, and otherwise the way to reach the
  operator. The operator's panel is also the careful state, so the served
  page shows it until the service answers.
- Request an invitation, the waiting list page, at `/waitlist`. It holds the
  invitation form, a short headline and what happens after you ask. On a
  phone of 390 by 844 pixels the email field and its button stand in the
  first screen.

The browser checks in `tools/check_service_workspace.mjs` read every public
page on three real services and report a second label for the same journey,
a page link under the wrong name or address, an invitation request anywhere
but on the invitation journey, and account creation while registration is
closed. A named check presses the hero action on a service that keeps a list
and finds the email field in the first screen; the old address
`/signup#waiting-list` fails it.

Security and How it works say who can create an account from the same
record. A sentence that says anyone can create an account on Get started
shows when `website.registration_available` is true, a sentence that says the
service is not taking new accounts shows when it is false, and both are served
hidden. The sentences beside them state only what holds in both states: people
sign in with their email address and password, and client tokens come from
the account page. Before September 24, 2026 both pages said that public
account creation was not open and that access came from an operator, beside a
working sign-up. Named checks read nine pages on a service that takes new
accounts and on one that does not. They fail on a sentence that says account
creation is closed, that an operator issues or revokes access, or that names
test tokens, and on one that offers account creation where the service takes
none.

Security explains how review works, at `/security#how-review-works`, and the
pricing line "New vetted additions" links there. The section states the rule
for new items, from `tools/candidate_review/resources/panel.json`, and what
the review record of the first release, `reviews.json` of the starter
catalogue, holds: its date, its three reviewers' lenses, its counts and that
one of its reviewers came from the model family of the items' author. A
browser check reads both records and fails when the page says anything they
do not hold.

A recipe's note may name a file this website serves under `/assets/`, as
the Pi recipe names its extension, `/assets/pi/baltor.ts`. The guide turns
that path into a link that opens the served file in a new tab, keeps the
note's exact words, and adds "Copy the file address", which copies the file's
full address. A note without such a path shows no file action.

The guide's connection check runs the protocol handshake with the page's
token, and it takes a client token, not an email sign-in. A visitor who is not
signed in sees "Sign in to check access". Signed in with an email address, the
guide offers "Create a client token" instead, which opens the account page at
its token panel with the panel loaded, and one line says that the check runs
with a client token.

The header, signed out, lists How it works, Library, Pricing and Docs, then
Sign in and "Get started"; signed in, it lists Workspace, Get set up, Library
and Docs, then Account, Administration for an operator, and Sign out. A
comment in the header marks where Use cases goes once that page exists. The
footer holds the brand column and four groups with stable ids,
`footer-product`, `footer-use-cases`, `footer-documentation` and
`footer-company`, with comments that mark where the pages still to come go; a
group shows once it holds a link.

## The design

The public pages follow the design of September 23, 2026: a white header with
the mark, the name, five links and the one primary action, and a homepage made
of bands. Each band is set off from the next by a change of ground and a one
pixel rule, and a dark band carries how it works and the closing action.
Every colour, typeface, radius and shadow is a custom property in the token
block at the top of `service.css`, so a change of design edits that block.
Below 860 pixels the header links fold into a menu behind one visible button
named "Menu", with `aria-expanded` and `aria-controls="main-nav"`. A press
opens and closes it, Escape closes it and returns focus to the button, and
opening a page closes it. Until September 24, 2026 a checkbox clipped to one
pixel under the logo opened the menu without the page script, while the icon a
person touches was hidden from assistive technology. Without the script the
served button still carries its name and its collapsed state, and the footer
links every page the menu holds. The site map check counts the button as a
control of the navigation, not as a header entry.

The header follows the sign-in that the page holds. A visitor who is not signed
in sees Sign in and the one primary action. A signed-in person sees the account
entry, which opens the account page, and Sign out, which ends the sign-in and
opens the sign-in page, and no longer sees Sign in or the invitation action.
The phone menu folds the same entries. The served page is the signed-out state.
An email sign-in lasts as long as the browser tab: once the service has opened
the account, the page keeps the identity provider's access token and its
expiry, and nothing else, in the tab's session storage, so a reload or an
address typed in the same tab opens the account again on the page asked for.
Closing the tab ends it, and signing out, a refused session or another sign-in
removes it. The refresh token is never kept, so a kept sign-in ends when its
access token expires. A service token or client token is never kept. A page
opened by a confirmation link starts from the link and forgets a kept sign-in,
and a confirmation's session is kept only after its new password is set and
the account opened.

The mark is traced from the owner's logo sheet of September 23, 2026:
variation 52, a white husky head in profile on a navy rounded tile. It is one
file, `baltor-mark.svg`, used in the header and the footer and as the page
icon, with `favicon-32.png`, `favicon-192.png` and `apple-touch-icon.png`
drawn from it. Replacing those four files changes the mark everywhere. The
standalone summit mark, variation 23, is kept with the
[brand marks](../../../../../docs/brand/README.md) and is not served.

Every page other than the homepage opens with an introduction band like the
one on the guide: white, the full width of the window, with a rule
under it.

The typefaces are Geist and Geist Mono from version 1.7.2 of the `geist`
package, under the SIL Open Font License 1.1, whose text is in
`THIRD-PARTY-NOTICES.md`. The service serves them itself as `geist.woff2` and
`geist-mono.woff2`. The page policy allows fonts from its own origin only, and
a font host would receive the address of every visitor. A system typeface is
the fallback.

The workspace, account and administration views use the visual language of
the dashboard design: a title card, white cards on the ground, muted card
labels, fact rows divided by rules and pills for states. They show the same
data as before. The sidebar and the example figures of the dashboard design
wait for the account data they would need.

The account page shows recorded usage as a table: one row for each item, with
its number of recorded downloads and the time of the latest, read from the
`items` of the usage record. The table is drawn only from the record version
the page was written for, and an account without downloads sees a sentence
instead of an empty table. The raw record stays under a disclosure for
developers.

## The homepage hero and its demonstrations

Since September 24, 2026 the hero shows no worked example. The owner asked for
the working directory of each task or subtask, built on demand, with no manual
search and no manual setup, and for links to demonstrations that show a run
start to finish. The hero's figure is the directory of one step: an
instruction file with only that step's context, the skill it needs, its
protocol server settings and reused code, labelled "Example layout", with the
words that the files were placed with no manual search and no manual setup.
What works today stays apart from what is built but not shipped: a person's
agent searches and Baltor places the chosen files, and assembling a directory
for every step is written only as what the local engine is built to do; a
named check refuses a sentence that states it as a current capability. Three
cards follow it: a simple
task at `/demo`, a long task that runs overnight at `/overnight`, and a Kaggle
competition at `/demo/kaggle`.

`tools/test_homepage_demonstration.py` refuses a hero that shows a search, a
reference, a digest or a download again, and a demonstration card that opens a
page this service does not serve. The one-step demonstration that stood beside
the hero until then, splitting the address lines of a customer file, is step 2
of the demonstration at `/demo`; its markup is archived in
`artifacts/website-archive-2026-09-24`. The same test holds the library count
on the homepage to the number of items in
`examples/29_intelligence_service/starter-catalogue/host-release/manifest.json`.

Each step of the two demonstration pages shows its search and its download
under the label "Real results from the library". Their item names,
kinds, licences, sizes and digests must be what a real search of this
release's packaged catalogue returns; moving the catalogue anchor rewrites
every body and so every digest, and `tools/test_showcase_pages.py` then names
each value to change. No step may choose an item that a recorded study found
harmful: the [data cleanup study](../../../../../case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md)
found that `normalize_phone_numbers` made a cheap model clearly worse, and the
test reads the design and results records of each study under `case-studies`.

The six kinds of file, the three use cases and the three demonstrations carry
no status tag.

## Design standards and the site map

The [website design standards](../../../../../docs/guides/website-design-standards.md)
hold the rules these pages follow. Every page, header entry and footer link is
listed in `web_site_map.json` beside `web_pages.py`, and the measured rules in
`web_layout_standard.json`. A page, link or section leaves the website only
with a dated removal row in that record.

## Hostnames, page heads, robots.txt and sitemap.xml

Since September 24, 2026 the service writes each page's own head before any
script runs, from the typed site map (`web_site_map.json`, record
`service_web_site_map/v2`): the title, the one-line description, the
canonical address on `https://baltor.ai`, the Open Graph and card tags a
shared link shows, and `noindex` for a page a search engine may not list. The
title, the description and those tags are taken out of a page's own head
first, so a page with a file of its own, not only a view of `index.html`,
ends with one of each once the site map lists it.

The site map's hostname table decides the page a hostname shows at its root
address: `docs.baltor.ai` the documentation, `status.baltor.ai` the service
status, `examples.baltor.ai` the examples gallery and `demo.baltor.ai` the
demonstration. `baltor.ai`, `www.baltor.ai` and `app.baltor.ai` show the
homepage, and so does a hostname the table does not name. The root serves
exactly what the page's own address serves on that hostname, with a
`baltor-root-address` tag that `service.js` reads to show the view and to send
the homepage links to the canonical hostname. Every other address shows its
own page on every hostname.

`/robots.txt` and `/sitemap.xml` are written from the same record: the
sitemap lists every page marked `indexed` at its canonical address, and
robots.txt leaves out the interface routes and every unlisted page. Both
answer HEAD like GET, with a strong validator. The checks are
`web_surface_checks.py` in the service self-test and
`tools/showcase_page_checks.mjs` in the browser suite.

## The showcase pages

`public-pages.js` and `public-pages.css` serve the pages of September 24,
2026:

- `/demo`, one data cleanup task in five steps. Each step's search results,
  sizes and digests are recorded from this release's library; each step's
  folder is an example layout at the native skill location of the harness the
  reader picks. `tools/test_showcase_pages.py` reruns every search against the
  packaged library and compares the folder roots with
  `tools/install_selected_material.py`.
- `/status`, read by the browser from `/api/v1/health` and
  `/api/v1/capabilities`. It shows readiness, each check, the served catalogue
  release and its item count, whether new accounts and subscriptions are open,
  and when it read them. It keeps no history and shows no uptime figure.
- `/examples`, the gallery: the demonstration, the case studies and the first
  search a reader can try in the workspace.
- Three case studies under `/case-studies/`, each naming its evidence files in
  `data-evidence`. Every number a case study shows must be a number of those
  files.
- The four audience pages under `/for/`.

## The directory page

`directory.html` is the free public directory of Model Context Protocol
servers and agent APIs, served at `/directory` and `/mcp-directory`. It stands
on its own outside the one-page app, in the same design: it loads
`service.css`, `architecture.css` and its own `directory.css`, and its script
`directory.js` drives the search, the category chips, the filters, the
listing detail, the appearance button and the status line.

`tools/build_mcp_directory.py` writes `directory/manifest.json`, the eight row
files beside it and the generated regions of the page: the header and footer
copied from `index.html`, the facts line, the category chips, the first forty
rows and the structured data. The rest of the page is written by hand. The
script draws only the rows in view, so the list scrolls through tens of
thousands of rows. Each row carries a `commercial_relationship` from
`../commercial_relationship.py`; every row ships with the relationship none,
and the order, the filters and the search never read it.

Listings other publishers wrote carry `data-listing-text`. The word rules of
`tools/check_service_workspace.mjs` leave that text out through
`tools/listing_text.mjs` and read the rest of the page and its files.
`tools/directory_browser_checks.mjs` holds the page's browser checks.
`tools/mcp_directory/SOURCES.md` records the sources and their terms.

## Customer documentation

The versioned `documentation-index.json` supplies the four sections and seven
entries at `/docs`. Six bodies are built from the customer Markdown guides;
the setup entry opens `/setup`. `documentation.js` validates the index and
rebuilds each body's allowed markup. `documentation.css` provides the index,
page navigation and contents list using the website's design tokens.

Use [the documentation maintenance guide](../../../../../docs/guides/website-documentation-view.md)
for source ownership, rebuilding, route checks and browser acceptance. The
bodies and index are public static files; they contain no account credentials.

## The deck

`deck.html` is the deck the owner asked for on September 24, 2026, served at
`/deck` with `deck.css`, `deck.js` and the shared-link picture
`deck-card.png`, which `tools/render_deck_card.mjs` draws. The site map lists
the page and opens it at the root of `deck.baltor.ai` once the service routes
that hostname. It carries a copy of the shared header and footer, so a change
to either is a change to this page too; the site map checks name any
difference.

Every number on a slide sits in an element marked `data-fact`, whose
`data-evidence` names the saved records the number comes from and whose source
note links them. `tools/test_deck_page.py` fails when a number stands outside a
fact, when no named record contains it, or when the page names a retired word,
a word of an invitation-only service or a runtime word. The browser checks in
`tools/deck_checks.mjs` read the rendered page the same way and drive the deck
with the keyboard, a swipe and the overview. Without the page script every
slide shows one after another.

## The model directory pages

`/models`, `/endpoints` and `/can-i-run`, and one page for each model at
`/models/<slug>` and each endpoint at `/endpoints/<slug>`, are rendered by the
service from the packaged records in `model-directory/`, not written by hand.
The transport, `http.py`, asks `model_directory_pages.render` for them before
the served address table, and `model-directory/page.html` is their template.
Their header and footer are the ones `index.html` serves, copied through
`web_chrome.py`, and `web_pages` writes the three list pages' head from the
site map as it does for every page. Only the two compact indexes, `model-directory.css` and
`model-directory.js` are served as files; `models.json`, `endpoints.json`,
`hardware.json` and `manifest.json` stay inside the service.

`tools/build_model_directory.py` writes the records daily from the sources
in `tools/model_directory/SOURCES.md`. Every row keeps each source address and
the day it was read, and carries a `commercial_relationship` of kind none
that no order, filter or hardware fit reads. `model_directory_fit.py` holds the
memory formula, which the page script repeats and
`tools/model_directory_browser_checks.mjs` compares for every hardware preset.
