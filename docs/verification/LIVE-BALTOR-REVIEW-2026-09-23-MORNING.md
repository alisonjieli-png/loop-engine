# Live Baltor review, September 23, 2026 morning

Kind: read-only public-service and interface review. Observed at
12:43 to 12:45 UTC, 08:43 to 08:45 United States Eastern time. This report
updates the [September 22 live review](SAAS-LIVE-READINESS-AND-CUSTOMER-JOURNEY-2026-09-22.md)
and [September 23 draft homepage review](DRAFT-HOMEPAGE-UX-REVIEW-2026-09-23.md).
It supplies evidence for the existing roadmap, chiefly S-6.33, S-6.34,
S-6.35, S-6.55 and D-17. It does not create another task authority.

## Current result

The live site has improved materially. The opening demonstration is now below
the message, the phone header is compact, and both the invitation action and
the invitation email field fit in the first phone screen. The earlier
finding that checkout and the customer portal are unavailable is obsolete:
both report available. Public account creation remains closed, and the
pricing page correctly says Invitation only.

The remaining launch work is a complete invited-customer journey, native
material use, accurate introductory copy and documentation, and the named
public destinations. Blog and team pages do not exist at their expected
paths. None of those gaps is resolved by a healthy service response or a
larger count of candidate files.

## Method and release binding

The inspected source was the clean detached checkout at
`abcad4f8`, not the older shared checkout. The current
[deployment map](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
and [release record](../../artifacts/architecture-audit-2026-09-19/pilot-release-18.json)
name Fly release 20, deployed from `f7c89465da6fec28c69afde3ddb2f6423068632a`
at 10:47 UTC, image
`sha256:6eb2aa26dfca3e08ff09013d0c1bda4414115e7b4e65c0ed991e6423edfd4cc4`.
This review did not access the Fly control plane to re-read the running image.

All eight configured hostnames answered 200 for the public home page,
capabilities and health: 24 of 24 GET probes. Their home page bodies matched
at 89,815 bytes with SHA-256
`6aea8df54287382b1ca1aed1ad7dae35d18788b1fc55a5c7dd17eecdca68369e`.
That equals this checkout's `index.html` after substituting Baltor for
`{{SERVICE_NAME}}`. The live logo, 32-pixel icon, stylesheet and page script
also matched this checkout byte for byte. This binds the inspected assets to
the source; it does not identify every running server module.

Evidence: [47 HTTP observations](assets/live-baltor-morning-2026-09-23/http-observations.json),
[11 rendered page and viewport observations](assets/live-baltor-morning-2026-09-23/browser-observations.json),
and [browser inspection script](assets/live-baltor-morning-2026-09-23/inspect.mjs).
Public browsing through the web tool was unavailable, so ordinary HTTPS GET
requests and isolated headless Chromium were used. The browser allowed only
same-origin GET requests, used no saved account and submitted no form.
No protected body, usage record, payment session or model was accessed.

The browser observations found no page script error, unexpected outgoing
request, horizontal overflow or unlabeled visible form control in these 11
views. They are bounded checks, not an accessibility certification,
conversion measurement, field performance study or signed-in journey.

## What changed since the earlier reviews

| Concern | Earlier measured finding | Current live finding | Assessment |
|---|---|---|---|
| Right-hand demonstration | Draft panel 655 by 642 pixels beside the hero | Demonstration spans 1,312 pixels at desktop width and starts at y763 below the opening copy; a smaller explanatory text block remains on the right | The original example-panel interruption is repaired. Keep the evidence labels. |
| Phone header at 390 by 844 | 254 pixels high | 65 pixels high | Repaired. Keyboard Tab reaches the menu control, and Space opens it. |
| Phone hero action | Draft y849 to 900, outside the first screen | y451 to 503 at 390 by 844; y519 to 571 at 320 by 700 | Repaired at both observed sizes. |
| Invitation email field | Draft y1102 | y467 to 515 after following the hero action to `/waitlist` | Repaired. Focus moves to the main region. Submission was not tested here. |
| Access message | Earlier mixed action names | Header and hero consistently say Request an invitation; pricing says Invitation only | Consistent with closed public registration. |
| Billing availability | September 22 capabilities said checkout and portal false | Both true, webhook true | Do not keep reporting that configuration failure. A complete payment and entitlement lifecycle was not tested here. |
| Catalogue storage and search | Older report described image-only bodies and repeated index construction | Health names a store-backed active catalogue; capabilities name one reusable index for each catalogue view | The older serving conclusions need remeasurement against this implementation before they are repeated. This read does not prove large-library capacity. |
| Homepage length | Draft 4,640 desktop and 8,228 phone pixels | 7,025 desktop and 11,830 phone pixels | Opening access is easier, but the full page is longer. This is a measured size increase, not evidence of worse conversion. |

Screenshots: [desktop opening](assets/live-baltor-morning-2026-09-23/home-desktop.png),
[390-pixel opening](assets/live-baltor-morning-2026-09-23/home-phone.png),
[320-pixel opening](assets/live-baltor-morning-2026-09-23/home-small-phone.png),
[full desktop page](assets/live-baltor-morning-2026-09-23/home-desktop-full.png),
[full phone page](assets/live-baltor-morning-2026-09-23/home-phone-full.png),
[opened phone menu](assets/live-baltor-morning-2026-09-23/phone-menu-open.png),
and [invitation destination](assets/live-baltor-morning-2026-09-23/phone-invitation-from-hero.png).

## Improvements for the next website change

| Finding and evidence | Proposed correction and discriminating check | Existing owner |
|---|---|---|
| The main subhead promises a fresh harness where “nothing drifts”; the smaller explanation says the fresh harness is being built. The phone user sees the outcome claim before the limitation. Context selection can also miss information. | Put the current library behavior in the opening sentence, followed by a clearly labeled product direction. Example: “Give your coding agents the material each step needs. Search reviewed guidance, choose an exact version, and download it into your tools. We are building a fresh harness for every step.” Refuse universal no-drift claims in the copy check. Preserve the owner's category line. | S-6.33 and the benefit publication rules |
| The secondary action says See one step work, but the destination records search and download and illustrates the fresh folder. The page correctly labels the folder Being built. | Call the action See search and download until native execution and acceptance are recorded. Check the action against the kinds of evidence its destination actually contains. | S-6.33, D-17-T04 |
| `/docs` starts with Install the local runtime and a serving-dependencies install command. `/connect` says connecting needs nothing installed beside the harness. Both statements concern different customer paths, but the first-time visitor must resolve that distinction. | Lead `/docs` with connecting an existing harness to the hosted library. Put engine installation and operating a service in separate advanced sections. Test that the shortest hosted-customer route never requires installation of the service. | S-6.33 and S-6.34 |
| The signed-out `/app` foregrounds deterministic character hashing, the absence of semantic embeddings and external identity qualification. These explain internals before the visitor has access. `/account` exposes load, refresh and availability controls around sign-in prompts. | Give the signed-out workspace one access action and one public sample reference. Put retrieval implementation details behind an advanced disclosure; show account controls once the relevant identity is available. Keep permission and error information explicit when it affects a user's action. | S-6.33 and D-17 |
| The phone menu is operable as a checkbox named Show the menu. It has a checked state but no expanded state, and the hidden input is a one-pixel box paired with a larger visual label. | Consider a real disclosure button with `aria-expanded` and `aria-controls`; verify keyboard open and close, visible focus, Escape behavior, navigation focus and the actual label hit area. This report does not call the current checkbox inaccessible solely because `aria-expanded` is absent. | S-6.33 and S-6.55 |
| The homepage now takes roughly 14 phone screens. Search, download, per-step material and future behavior recur in several sections. | Retain the opening, a small recorded demonstration, current package examples and price/access. Move deeper future-behavior explanation to How it works and research articles. Compare comprehension and invitation completion; do not use page length alone as the success metric. | S-6.33 and S-6.55 |

The [benefit evidence guide](../guides/launch-benefits-and-evidence.md)
still starts by making reusable solutions the overall promise. That is
inconsistent with the newer owner direction in [AGENTS.md](../../AGENTS.md).
Keep that guide's measurement rules, and update its active positioning to the
frontier harness and efficient accepted-work north star. This is an active
documentation correction for S-6.34, not a rewrite of historical evidence.

Additional screenshots: [pricing](assets/live-baltor-morning-2026-09-23/pricing-desktop.png),
[setup](assets/live-baltor-morning-2026-09-23/connect-phone.png),
[signup status](assets/live-baltor-morning-2026-09-23/signup-phone.png),
[signed-out account](assets/live-baltor-morning-2026-09-23/account-signed-out.png),
[signed-out workspace](assets/live-baltor-morning-2026-09-23/workspace-signed-out.png),
and [documentation](assets/live-baltor-morning-2026-09-23/docs-desktop.png).

## Public routes, blog, team and logo

`/blog`, `/team`, `/about`, `/support`, `/status` and `/demo` return 404.
`/docs` and `/examples` are real client-rendered views, while
`docs.baltor.ai`, `examples.baltor.ai`, `demo.baltor.ai` and
`status.baltor.ai` still serve the identical main homepage. The subdomain
finding remains open in S-6.33. A useful status page needs operational
information and freshness, rather than another copy of the marketing page.
`/terms` returns 404 and the footer says the terms are not published. The
owner's approval requirement for that legal document remains separate from
engineering's authority to build ordinary pages.

For the requested blog and team work, create public route content through
the existing website component. The first research article should show an
actual saved experiment, including a result that did not improve. A second
can show how one multi-file package is selected, laid out, checked and
withdrawn. Article records need a title, actual author or responsible
organization, publication and modification dates, exact source and release
links, and a current-versus-planned label. A team page can explain the
operator, purpose, public source and how to contact the business; named
people, biographies, photos, employee counts and customer endorsements must
come from facts the owner has supplied. Do not invent them to fill cards.
These are proposed additions to S-6.33 and S-6.56, with public proofreading
and route checks before release.

All inspected pages currently share one raw HTML response and initial
metadata; JavaScript changes the title after navigation. No canonical link
was observed. `/robots.txt` and `/sitemap.xml` return 404. That does not prove
search engines cannot index the site. Before publishing a substantial blog,
serve each public article's own title, description and canonical URL in the
response, add a sitemap, and declare the intended indexable routes. Check the
raw response as well as the rendered page. Keep account and private records
out of public article indexes. Route metadata belongs to the existing web
component; it does not require a second publishing stack.

The live header uses a 32-pixel navy tile with a white dog-and-summit
silhouette. Its SVG and 32-pixel icon match the clean source. The roadmap
still identifies it as a placeholder awaiting the owner's final choice.
The recent large concept illustrations are not the live logo. The next logo
review should use real 16-, 20-, 24- and 32-pixel browser renders, on light and
dark tabs, with dedicated simplified geometry where needed. Keep the
full-body illustration for large placements. Legibility of the animal and
summit is the check; a technically valid SVG is insufficient.

## Current service facts and limits

The public health record reports alive and ready. Its active store catalogue
is `c824a1d2e2228d2caf9005057efd1085277393391d65d8a6dbdbf4743aeb6753`
with **43 items** and zero withdrawn items left out at this read. That count
is public runtime evidence, not a count of original candidate packages in
the repository. This review did not authenticate to recheck the release
record's 34 offered and nine withheld items. The live capabilities report
file download by path and UTF-8 text bodies; actual delivery and native
pickup of a multi-file package were not exercised.

Public registration, email signup and account recovery report unavailable.
The public identity configuration still names the Fly hostname for the
callback. The deployment map records the required identity-provider redirect
change before changing that origin. Do not infer a broken current sign-in
from that alone. Invited-account confirmation, personal key issuance,
revocation, download metering, signed-in usage and billing were outside this
read-only review. D-17-T03 and D-17-T04 retain the complete journey proof.

HEAD requests to `/`, `/pricing` and `/api/v1/health` returned 404 while their
GET requests returned 200. This is still a concrete S-6.33/S-6.35 repair.
The source-bound release record is stronger than this review for deployment
and authenticated checks; this review is newer direct evidence for public
availability and the rendered interface. Neither establishes 10,000,
100,000 or one million approved, searchable and natively usable packages.
