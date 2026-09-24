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
Below 860 pixels the header links fold into a menu that a checkbox opens, so
the menu works without the page script and nothing moves when the script runs.

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

## The homepage demonstration

The opening message says why a fresh harness for each step helps, and the
words beside it say what works today and what is being built. Below them, at
the full width of the page, the homepage shows one step of a task in three
parts.

- Recorded parts: the search and the download, under the label "Recorded from
  this release's library". Their item names, kinds, licences, sizes and
  digests must be what a real search of this release's packaged catalogue
  returns, in
  `examples/29_intelligence_service/starter-catalogue/host-release/manifest.json`.
  Moving the catalogue anchor rewrites every body and so every digest. After
  such a release `tools/test_homepage_demonstration.py` fails and names each
  value to change in `index.html`. The browser checks compare the same values
  with the manifest.
- The folder of the step, under its own label "Being built": a fresh harness
  that holds only the files of the step. It places the downloaded skill and
  shows files that are not Markdown, because harness material is any file a
  harness reads.

The step splits the address lines of a customer file with
`split_address_lines_into_components`. It showed `normalize_phone_numbers`
until September 23, 2026, which the
[data cleanup study](../../../../../case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md)
found made a cheap model clearly worse on its population. The same test fails
when the step chooses an item that a recorded study found harmful; it reads the
design and results records of each study under `case-studies`.

The same test holds the library count on the homepage to the number of items
in the manifest, and the connection entry to the reviewed Claude Code recipe in
`client-recipes.json`. The page is served with the public address in that
entry. Once the page script has checked the recipe record, it writes the entry
again with the address of the service that serves the page, as the guide
page shows it.

The six problems, the five steps of how it works and the six kinds of file
each carry a status tag. Only the parts that work on the live service today
say Available now or Live: a narrow context and reviewed expertise, search and
download, and skills. The browser checks fail when any other card says so.

## Design standards and the site map

The [website design standards](../../../../../docs/guides/website-design-standards.md)
hold the rules these pages follow. Every page, header entry and footer link is
listed in `web_site_map.json` beside `web_pages.py`, and the measured rules in
`web_layout_standard.json`. A page, link or section leaves the website only
with a dated removal row in that record.

## Customer documentation

The versioned `documentation-index.json` supplies the four sections and seven
entries at `/docs`. Six bodies are built from the customer Markdown guides;
the setup entry opens `/setup`. `documentation.js` validates the index and
rebuilds each body's allowed markup. `documentation.css` provides the index,
page navigation and contents list using the website's design tokens.

Use [the documentation maintenance guide](../../../../../docs/guides/website-documentation-view.md)
for source ownership, rebuilding, route checks and browser acceptance. The
bodies and index are public static files; they contain no account credentials.
