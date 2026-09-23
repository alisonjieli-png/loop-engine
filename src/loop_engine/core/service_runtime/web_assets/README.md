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

## One call to action

Every public link or button that starts the access journey says "Get
started" and opens the Get started page at `/connect`. The addresses
`/get-started` and `/waitlist` open the same page. That page leads with one
panel, chosen from the service's capabilities record: account creation when
`website.registration_available` is true, otherwise the invitation request
form when `website.waitlist_available` is true, and otherwise the way to reach
the operator. The operator's panel is also the careful state, so the served
page shows it until the service answers, and keeps it when the record is
missing or carries a version the page was not written for. The browser checks
in `tools/check_service_workspace.mjs` read every public page on three real
services and report a second label for the same journey, an invitation
request outside that panel, and account creation while registration is closed.

## The design

The public pages follow the design of September 23, 2026: a white header with
the wordmark, five links and the one primary action, and a homepage made of
bands. Each band is set off from the next by a change of ground and a one
pixel rule, and a dark band carries how it works and the closing action.
Every colour, typeface, radius and shadow is a custom property in the token
block at the top of `service.css`, so a change of design edits that block.
Below 860 pixels the header links fold into a menu that a checkbox opens, so
the menu works without the page script and nothing moves when the script runs.

The mark is a placeholder that the owner will replace. It is one file,
`baltor-mark.svg`, used in the header and the footer and as the page icon,
with `favicon-32.png`, `favicon-192.png` and `apple-touch-icon.png` drawn from
it. Replacing those four files changes the mark everywhere.

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

## The homepage demonstration

The homepage shows one step of a task in three parts, in one panel beside the
headline.

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

The same test holds the library count on the homepage to the number of items
in the manifest, and the connection entry to the reviewed Claude Code recipe in
`client-recipes.json`. The page is served with the public address in that
entry. Once the page script has checked the recipe record, it writes the entry
again with the address of the service that serves the page, as the Get started
page shows it.

The six problems, the five steps of how it works and the six kinds of file
each carry a status tag. Only the parts that work on the live service today
say Available now or Live: a narrow context and reviewed expertise, search and
download, and skills. The browser checks fail when any other card says so.
