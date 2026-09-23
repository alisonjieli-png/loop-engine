# Live UI, onboarding and acquisition review, September 22, 2026

Kind: read-only verification and design review. This is input to the existing
[S-6.33 website work](../roadmap/roadmap.yaml), [D-18-T03 invitation journey](../roadmap/roadmap.yaml)
and [D-17-T03 customer journey](../roadmap/roadmap.yaml), not a second task
list. The public site was inspected at about 23:29 to 23:35 United States
Eastern time on September 22, 2026. No form was submitted, account used,
payment started, file downloaded or customer action recorded.

## What was checked

Public `GET` requests and a clean, isolated headless Chromium session loaded
`https://baltor.ai/`, `/connect`, `/signup#waiting-list`, `/waitlist`,
`/pricing`, `/how-it-works`, `/login` and `/account`. The browser followed the
home page links as well as opening the routes directly. Viewports included
320 × 700, 360 × 800, 390 × 844, 768 × 900 and 1440 × 900 pixels. The
connected computer-use browser was unavailable, so this review used an
isolated headless browser with no signed-in profile. The site's JavaScript
raised no page errors in the inspected routes. That is narrower than a full
cross-browser, screen-reader or authenticated customer test.

The home page `GET` returned 200 and SHA-256
`a667c727280b4f7473571f5716cf9f52da81354fd02515bf83e23892abe2e90e`.
The live style and script bytes matched the corresponding repository files at
inspection time: `service.css` SHA-256
`a4ee72416b93d51c3b202485a22eaca1ac7c1ec216f77f628e36a0b12354f2eb`,
`architecture.css` SHA-256
`b7c81af1766d5be70b86e95b912aacb36593e8e7e3317c5cbfa192ceabd791a4`,
and `service.js` SHA-256
`f8cba3abfaafc18c952a71daa2bd17d167a6d4aed8e4af94cd5339284137dfa0`.
The independent [live readiness record](SAAS-LIVE-READINESS-AND-CUSTOMER-JOURNEY-2026-09-22.md)
ties the same home page digest to the successfully deployed `a51ac963`
image. Later local commits were not assumed to be live.

Saved visual evidence:

- [Desktop first viewport](assets/live-ui-ux-review-2026-09-22/home-desktop-1440x900.png)
  and [full desktop page](assets/live-ui-ux-review-2026-09-22/home-desktop-full.png).
- [Mobile first viewport](assets/live-ui-ux-review-2026-09-22/home-mobile-390x844.png)
  and [full mobile page](assets/live-ui-ux-review-2026-09-22/home-mobile-full.png).
- [Mobile destination after the hero waiting-list link](assets/live-ui-ux-review-2026-09-22/signup-waiting-list-mobile.png),
  [actual mobile request form](assets/live-ui-ux-review-2026-09-22/waitlist-mobile.png),
  and [mobile Get started page](assets/live-ui-ux-review-2026-09-22/connect-mobile.png).

## Observed live behavior

| Surface | Observation |
|---|---|
| Desktop home, 1440 × 900 | The hero has a 742-pixel copy column and a 495-pixel example panel. The panel occupies horizontal position 868–1362 and vertical position 271–739. The blue **Get started** button starts at vertical position 628; the **Join the waiting list** text link starts at 763. The next section starts at 877, almost one screen down. |
| Mobile home, 390 × 844 | The header is 254 pixels tall because its six navigation links wrap across two rows under the brand and sign-in controls. The headline starts at 392, the **Get started** button at 899, the waiting-list text link at 1034, and the example panel at 1161. Neither action appears in the first screen. At 320 × 700, the same actions start at 974 and 1171. No horizontal overflow was measured at any inspected width. |
| Waiting-list path | Clicking the home page's **Join the waiting list** link opens `/signup#waiting-list` at a scrolled account-status notice. The actual form is absent there; a second **Ask for an invitation** click opens `/waitlist`, where the form is visible. On 390 × 844, the direct `/waitlist` email field begins at 929 and its submit button at 1168, both below the first screen. No submission was tested. |
| Get started path | The prominent hero button opens `/connect`, an installation and connection guide. At 390 × 844 its waiting-list action is in step three at vertical position 4642, after substantial setup content. The guide is useful to an invited developer but is a long route for a visitor who cannot obtain an account today. |
| Access and payment | The live [capabilities response](https://baltor.ai/api/v1/capabilities) says `registration_available=false`, `waitlist_available=true`, `access_profile=operator_provisioned`, `checkout=false` and `portal=false`. The live [identity configuration](https://baltor.ai/api/v1/account/identity) says `email_signup_enabled=false`. The visible pricing page correctly says payment is not open. `/login` shows email/password and operator-token forms; no sign-in was attempted. |
| Home page content | The right-hand panel shows a real search, three returned skill references, one selected download and a digest check. The first result directly matches the phone-number query. The other two are address splitting and malformed-value detection; their relationship to phone-number formatting is not explained. The panel demonstrates retrieval, not a fresh harness process, selected working-directory files, or an accepted task result. The lower **How it works** section identifies its wider workflow as still being built. |
| Page structure | The full desktop home page is 4389 pixels tall; mobile is 7873 pixels. Most of the first several desktop sections sit on a white ground with similar white cards and subtle rules. More distinct pale bands appear later. The page repeats the ideas of material for each step, search, selected downloads and connection settings across the hero, three-step strip, four-things section and six-benefits section. |

The served markup and routes support those observations: the hero, example
panel and actions are in
[`index.html`](../../src/loop_engine/core/service_runtime/web_assets/index.html),
line 27;
the dynamic waiting-list action still points to `/signup#waiting-list` in
[`service.js`](../../src/loop_engine/core/service_runtime/web_assets/service.js),
line 36;
the actual form is in the separate
[`/waitlist` view](../../src/loop_engine/core/service_runtime/web_assets/index.html),
line 101;
and the 900-pixel and 760-pixel layout changes are in
[`service.css`](../../src/loop_engine/core/service_runtime/web_assets/service.css),
line 6, and
[`architecture.css`](../../src/loop_engine/core/service_runtime/web_assets/architecture.css),
line 61.

## Interpretation and suggested S-6.33 repair

These are design inferences from the observed page, not conversion data. The
owner's earlier concern about the right-hand example is supported by the
render: it takes about two fifths of the hero width and looks like a terminal
workflow even though the actual differentiator is a focused, separately
started harness with only the selected context for each step. The panel's
facts are useful proof of today's retrieval path; its position makes that
partial path the first visual explanation of the whole product. Move that
recorded search below the opening message as a full-width **What works today**
example. If the hero shows the intended per-step process, mark the unqualified
steps as a product design until a native client has loaded material and
finished a checked step. Do not imply that the visual itself is a completed
customer run.

The highest-friction acquisition defect is the waiting-list route. While
registration is closed and the waiting list is open, use one prominent
**Request an invitation** action and send it directly to `/waitlist`; make
**See how it works** or **Install the free tool** secondary. The same action
should be consistent in the hero, pricing and closing area. When the
capabilities change, the action can switch to account creation, but the
current live state must continue to show invitation-only access and payment
closed. A named browser check should click the live primary action and find a
visible email field without an intervening page or click; the known-wrong
`/signup#waiting-list` route must fail it.

On mobile, reduce the header height and put the primary action before the
additional positioning, pricing and provider-key paragraphs. Keep the six
destinations accessible through a keyboard-usable compact menu. A useful
acceptance target is that at 390 × 844 the main action is wholly visible in
the first viewport and that at 320 pixels the page has no horizontal scroll.
For a paid-traffic destination, the `/waitlist` email field should also be
visible without scrolling on a normal phone viewport. These are proposed
layout targets, not measured conversion improvements.

The opening message should say in plain language why a new, focused harness
helps each step, then distinguish the current searchable-file service from
the still-in-development automatic step orchestration. The live page instead
defines the word *harness* and repeats the category line while the unique
process choice remains invisible. A short task-to-steps illustration could
show a planning step receiving requirements, a build step receiving selected
tools and code, and a review step receiving the result and checks. Label it
as an illustration. Keep the genuine search-and-digest receipt below it with
its source and date.

The existing [S-6.33 record](../roadmap/roadmap.yaml) already names the
single-action, section-separation and richer-demo problems and says a local
hero repair and another detached redesign are in progress. This review
therefore supplies a **live baseline and discriminating checks** for that
work, rather than proposing a separate implementation queue. The complete
revised page needs another read-only visual pass at desktop and phone sizes,
followed by the existing first-time visitor and native-client tests.

## Acquisition gate and limits

Sending paid traffic to a checkout journey would currently be misleading:
public account creation and checkout are off, and the [customer-journey
record](SAAS-LIVE-READINESS-AND-CUSTOMER-JOURNEY-2026-09-22.md) has no
first-time user, native loaded-and-used step, or paid entitlement proof. A
small invitation campaign could be considered only after the direct form
path, request storage and operator follow-up are checked end to end under
D-18-T03. The public site says it runs no analytics or advertising scripts;
the current waitlist request sends only `email` and `note`, with no campaign
field ([`service.js`](../../src/loop_engine/core/service_runtime/web_assets/service.js),
line 261). Thus this review did not measure click-through,
form completion, activation or acquisition cost. If campaign measurement is
added, define minimal first-party counts and update the approved privacy
notice as needed before collecting new data.

The observed behavior says nothing about whether a real visitor prefers the
proposed layout or copy. It does not establish accessibility with a screen
reader, performance on a slow connection, delivery of an invitation email,
onboarding without help, or the commercial value of the current library.
