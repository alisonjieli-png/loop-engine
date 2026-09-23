# Baltor front-end messaging and design artifact

Kind: dated design input, September 23, 2026. This is a companion for Claude
Code's website canvas and handbook and for [S-6.33](../roadmap/roadmap.yaml).
It describes a proposed visitor experience. It does not change the website or
establish that an in-flight redesign is deployed. The [live visual
review](../verification/LIVE-UI-UX-AND-ACQUISITION-REVIEW-2026-09-22.md),
[draft visual review](../verification/DRAFT-HOMEPAGE-UX-REVIEW-2026-09-23.md),
and [live customer-journey record](../verification/SAAS-LIVE-READINESS-AND-CUSTOMER-JOURNEY-2026-09-22.md)
are the evidence for the observations below.

## The visitor's first decision

A first-time visitor should understand three things before seeing a detailed
workflow: Baltor helps give each focused step the material it needs; a
searchable, reviewed library is available to invited users now; automatic
creation of a fresh harness for every step is still being built. The next
available action is to request an invitation. The page should then explain
how an invited developer connects an existing harness and what the broader
step-by-step design aims to do.

This order serves three readers:

| Reader | First question | Page response |
|---|---|---|
| Developer with an existing harness | What can I use now, and how does it fit my client? | Show the current searchable material, a real selected download, supported connection instructions and the invitation state. |
| Team evaluating shared practice | Can we control sources, versions, permissions and costs? | Show item identity, exact bytes, review state, customer-held model settings and the boundary between available service and planned step execution. |
| Builder of an agentic system | Can a step select just the material it needs? | Show the focused-step design as an illustration; describe native loading and accepted results as future qualification gates until recorded. |

The [public writing rules](../../AGENTS.md#public-writing) keep the homepage,
How it works page and shared footer in ordinary words. Those surfaces use
*task*, *each step*, *harness*, *information*, *tools*, *model* and *result*.
The technical runtime classification belongs in the documentation, not in
the public opening message. Numerical cost savings, autonomous overnight
completion and improved task success need matched [benefit
evidence](../guides/launch-benefits-and-evidence.md) before they become
factual customer claims.

## Observed baseline that the design must repair

These are measurements from saved browser sessions, not conversion
measurements. The live session was inspected on September 22, 2026. The
draft session used an isolated local fixture on September 23 and may have
changed since that review.

| Surface | Saved observation | Design consequence |
|---|---|---|
| Live desktop at 1440 × 900 | The right-hand example is 495 × 468 pixels, at x868–1362 and y271–739. The first subsequent section starts at y877. | A search-and-download example is valuable, but it should follow the main explanation instead of occupying the opening argument. |
| Draft desktop at 1440 × 900 | The new five-stage panel is 655 × 642 pixels, at x725–1380 and y145–787. Its split, folder and check stages explicitly say they illustrate a design being built. | Retain the honest stage labels and selected-file picture. Move the demonstration into a later full-width band or materially reduce its opening weight. |
| Live phone at 390 × 844 | The header is 254 pixels tall. The main Get started action begins at y899; the waiting-list text link begins at y1034. | The first action needs to be fully visible without scrolling. |
| Draft phone at 390 × 844 | The header remains 254 pixels tall. Get started begins at y849, just below the first screen. At 320 × 700 it begins at y924. | A shorter header and shorter opening copy are necessary; moving the action by a few pixels is insufficient. |
| Live invitation route | The waiting-list link goes to `/signup#waiting-list`, which requires another click. A direct `/waitlist` visit places the email field at y929 on a 390-pixel phone. | Send the primary action to a page that shows the form directly, then raise the email field into the first phone screen. |
| Draft invitation route | The hero opens `/connect`, which contains the form without another click. On a 390-pixel phone the field starts at y1102 and submit at y1439. | Direct navigation is improved; the landing page still needs a shorter path to the actual form. |

The live [capabilities record](https://baltor.ai/api/v1/capabilities) in the
saved review reported invitation requests available, public registration
closed, checkout closed and customer portal closed. The live library had 43
packaged single-Markdown items, 34 offered to the pilot owner and nine
withheld for undeclared effects in the release record. The search card
demonstrated retrieval and one selected download. No recorded customer
journey had taken those bytes through a native harness and an independently
accepted task result. Current status must be checked again before release
copy is finalized.

## Proposed message hierarchy and copy

The following strings are **copy proposals**, not approved or deployed
website text. Each one should be checked against the actual capabilities
response and the product style guide at release time.

| Position | Proposed text | Status condition |
|---|---|---|
| Small category line | “Better material for each step of your harness.” | An aspiration about the intended use. |
| Main heading | “Give each step a focused harness.” | The design direction, followed immediately by the implementation distinction below. |
| Opening explanation | “Baltor helps your harness find the instructions, skills, tools and reusable code a step needs. Invited users can search and download reviewed material today. Automatic fresh harnesses for each step are in development.” | The middle sentence requires the current served library and access path to remain available. |
| Primary action while registration is closed | “Request an invitation” | Opens the actual invitation form directly while `waitlist_available=true`. |
| Secondary action | “See how it works” | Opens a plain-language explanation with the same current-versus-planned labels. |
| Current demonstration label | “Recorded search and download from the current library” | Show a saved, dated record with the release identity and exact selected item; avoid implying task completion. |
| Future demonstration label | “Illustration of the step-by-step design” | Applies to split, folder and accepted-result stages until a native client run proves each one. |

The opening message should avoid a wall of price, provider-key and harness
definition paragraphs. Place provider custody and pricing near the connection
explanation. Keep one prominent action in the hero. When the public
registration capability changes, select the action from the live capability
state and test every route; a static promise should not outlive the service
state.

## Proposed page and interaction flow

1. **Opening band:** a short category line, the focused-step explanation,
   one prominent invitation action and one quieter explanation link. At
   desktop width the text can span the content column. At phone width the
   action follows the opening sentences directly.
2. **What works today:** a recorded library search, its chosen reference,
   exact version and digest, and the download or connection path. Name the
   client and release tested. The example should show the strongest relevant
   result; loosely related search hits need an explanation or should be
   omitted from the demonstration.
3. **How the design works:** one small task moving through focused steps,
   each with its own selected file set and fresh harness. Label every
   unqualified stage as an illustration. The folder example can contain
   instruction files, a skill, a script and a protocol configuration, but
   the illustration must say that today's served catalogue is still
   single-Markdown items.
4. **Who uses it:** short examples for a developer, a team and an agentic
   system. Present overnight tickets, data cleanup and competition work as
   examples to prove, not customer outcomes that have already occurred.
5. **Get connected:** a concise path for invited users to create a personal
   client key, configure a supported client and search the library. Link to
   the full setup guide for exact commands. Keep local model credentials
   with the customer.
6. **Access and trust:** show invitation-only access, current payment state,
   source and review information, exact file identity and the distinction
   between retrieving material and proving a task result. Place the current
   plan price only where the subscription state is explained accurately.
7. **Closing invitation:** repeat the same primary action and destination.

Alternating ground colors or clear horizontal rules should separate these
bands. The draft review found better separation, yet its full page grew to
4,640 pixels on desktop and 8,228 on phone, compared with 4,389 and 7,873
in the saved live review. Consolidate repeated descriptions of search,
selected downloads and step material as the design moves forward.

The owner proposed a geometric Alaskan racing dog with its front paws
on an ice peak, then rejected the [first SVG explorations](../verification/assets/baltor-logo-concepts-2026-09-23/README.md)
and supplied a frontal husky illustration. The [later browser comparison](../verification/assets/baltor-logo-concepts-2026-09-23/refined-husky/index.html)
preserves the recognizable face mask, two paws and broad summit in four new
raster concepts. The compact fourth concept is the proposed next logo
direction; it still needs a controlled vector redraw and a separate tiny
favicon. The [design notes and exact prompts](../verification/assets/baltor-logo-concepts-2026-09-23/refined-husky/README.md)
state the remaining detail and dark-surface issues. None is a selected or
deployed brand asset.
The owner also rejected the 16- and 32-pixel reductions as too detailed and
blurry. The later [dedicated small-mark comparison](../verification/assets/baltor-logo-concepts-2026-09-23/micro-marks/index.html)
uses separate SVG drawings at those sizes, with a large head and white mask,
one ridge, and paws only in the 32-pixel mark. Small-size recognition must be
judged at actual display size before adopting it.
The subsequent reference board favors a mature, proud profile, a longer
muzzle and a lifted chin. The [latest profile variations](../verification/assets/baltor-logo-concepts-2026-09-23/proud-profile/index.html)
replace the smiling-mask direction with curved, summit and single-cut
small SVG families. This preference supersedes the earlier frontal
mascot recommendation; no variant is approved for production.

## Phone and desktop acceptance

These are **proposed acceptance checks** for S-6.33, with named known-wrong
cases. They do not claim that the current site passes.

| Check | Target and negative control |
|---|---|
| Phone first screen | At 390 × 844, the complete primary action is visible in the first viewport. At 320 × 700, the page has no horizontal overflow and the action remains reachable without an unexpectedly tall header. The saved draft at y849 and y924 must fail the first target. |
| Invitation destination | A visitor follows the primary action once and sees a visible email field in the first 390 × 844 viewport. The former `/signup#waiting-list` extra click and the draft field at y1102 must fail. Submit, confirmation and stored request need a separate end-to-end check. |
| Desktop opening | The focused-harness message is read before the demonstration. The example does not occupy a dominant right-hand column beside the opening explanation. Compare against the saved 655 × 642 draft panel. |
| Evidence distinction | Every illustrated stage says it is illustrative, and every current-library stage identifies the release or saved record. A caption that calls the illustrated result a completed customer task must fail. |
| Capability consistency | Hero, pricing, access and closing invitation follow the same registration and payment state. A page that invites payment while checkout is disabled must fail. |
| Keyboard and assistive use | Compact navigation opens, closes, traps no focus, and exposes link names. Interactive demonstration controls work with keyboard, have visible focus and meaningful labels. Screen-reader behavior requires an actual assistive-technology pass; a local browser check alone does not prove it. |
| Readability and motion | Check color contrast, 200 percent zoom, reduced-motion preference, narrow layout and tap targets. Run at least the saved 320, 390, 768 and 1440 pixel widths after the content and assets are merged. |

The next release review should compare the merged, committed page with the
saved live and draft screenshots, then repeat the checks on every public
hostname named in the [deployment map](../architecture/MVP-CLIENT-SERVER.md#current-deployment).
Click-through and activation remain unknown until a consented measurement
path and a real visitor sample exist. The existing [roadmap](../roadmap/roadmap.yaml)
owns implementation and release decisions.
