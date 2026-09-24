# The deck at /deck, September 24, 2026

Kind: dated evidence. The owner asked on September 24, 2026 for a deck at
`deck.baltor.ai`, with content only from public facts that saved evidence in
this repository backs. Roadmap steps S-6.36 and S-6.100 carry the state.

## What was built

| File | What it is |
|---|---|
| `src/loop_engine/core/service_runtime/web_assets/deck.html` | The page, served at `/deck`: ten slides, the shared header and footer, a description and a large shared-link card. |
| `src/loop_engine/core/service_runtime/web_assets/deck.css` | Its styles, on the site's tokens, typefaces and section padding values. |
| `src/loop_engine/core/service_runtime/web_assets/deck.js` | One slide at a time: arrow keys, Page Up and Page Down, Space, Home and End, a sideways swipe, the controls, an overview of every slide (O), a slide's own address such as `/deck#live`, and full screen (F). Without it every slide shows one after another. |
| `src/loop_engine/core/service_runtime/web_assets/deck-card.png` | The 1200 by 630 picture a shared link shows, drawn by `tools/render_deck_card.mjs`. It carries no number. |
| `tools/test_deck_page.py` | Key-free checks over the packaged page, with known-wrong decks and mutant controls. |
| `tools/deck_checks.mjs` | Browser checks run by `tools/check_service_workspace.mjs`, with removed-guard controls. |

`web_pages.py` serves the page and its three files, and `web_site_map.json`
lists the page and names `deck.baltor.ai` as the hostname that opens it.

## How a number is tied to its record

Every number on a slide, in digits or as a number word, sits in an element
marked `data-fact`. Its `data-evidence` names the saved records, as a
repository path and, for a JSON record, a pointer to the exact value. The
fact's visible source note links each named record. `tools/test_deck_page.py`
fails when:

- a number stands outside every fact, or its fact has no single source note
  that links a record;
- none of the records its fact names contains the number, a record is
  missing, a pointer does not resolve, or the note does not link a record the
  fact names;
- the title, the description or the shared-link text carries a number;
- the page or its script says a retired word, a word of an invitation-only
  service or a runtime word, read with the browser suite's own rules and
  terminology.yaml;
- the served address table, the site map or the hostname table drops the
  deck, or the card is not 1200 by 630.

A number bound to a whole document is checked for presence in that document,
not for its position in it. The 81 numbers on the deck are bound to 25 facts.

## The slides and the source of every fact

| Slide | Facts | Source records |
|---|---|---|
| Cover | The owner's category line; the five harnesses Baltor sets up. No number. | `terminology.yaml`, the site's hero |
| The problem | The customer problems in the owner's words. No number. | `AGENTS.md` north star, `README.md` |
| What Baltor is | The kinds of harness file; keys stay with the customer; review before serving; one harness for each step is not open yet. No number. | `README.md`, `AGENTS.md` |
| How it works | Search returns references, a step downloads what it chose, access and digest are checked, the download is recorded. An SVG sequence diagram. No number. | `README.md`, `docs/guides/service-searching-and-retrieving.md`, `docs/guides/service-usage-and-what-you-pay-for.md` |
| Live today | Release 24 on September 24, 2026, release 23 kept for rollback; public sign-up since September 24, 2026; connection entries for 5 harnesses, Pi with Gemma 4 checked end to end on September 23, 2026; 43 reviewed skills, each approved by three independent reviewers; 7 of 7 catalogue checks; browser 163 of 163, addresses 120 of 120, service 19 of 19, sign-up journeys 11 of 11, staff dashboard 10 of 12 | `artifacts/architecture-audit-2026-09-19/pilot-release-24.json`, `docs/architecture/MVP-CLIENT-SERVER.md`, `src/loop_engine/core/service_runtime/web_assets/client-recipes.json`, `examples/29_intelligence_service/starter-catalogue/reviews.json` |
| Measured in the open | 225 of 400 requests over 72 steps; 0.842 against 0.991 on phone numbers; better in 0 of 4 families, worse in 1; 45 to 446 percent more prompt tokens | `case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md` |
| The library plan | 43 live; 10,000 then 100,000 approved packages, then 100 to 1,000 a day; millions of licence-cleared files as the aim. Measured: 43 of 49 approved in the first round; 0 of 30 in the first panel run, 658.5 seconds; 56 of 75 wave 5 packages passed the pre-checks; 3,251 outside candidates staged from 4,790, 187 as outlines only | `pilot-release-24.json`, `AGENTS.md`, `docs/roadmap/roadmap.yaml` (S-6.40, S-6.69), `docs/research/MILLION-HARNESS-SUPPLY-NEXT-STEPS-2026-09-23.md`, `reviews.json`, `artifacts/candidate-review-pilot-2026-09-22/README.md`, `artifacts/first-party-harness-candidates-2026-09-24-wave-5/README.md`, `artifacts/library-ingestion-2026-09-23/README.md` |
| Business model | Baltor Pro, $29 a month; the first 10 accounts free each month; live payments since September 21, 2026; comparable entry plans cost $19 to $29 a month | `README.md`, `artifacts/release-24-2026-09-24/README.md`, `account_policy.py`, `AGENTS.md`, `docs/guides/billing-setup-and-pricing.md` |
| Why now | Agent Skills an open standard since December 18, 2025, more than 40 client products listed; AGENTS.md and the Model Context Protocol with the Agentic AI Foundation; SkillsBench 33.9 to 50.5 percent on 87 tasks, self-written skills 8.1 to 11.5 points below none; 157 malicious of 98,380 skills from two registries | `docs/research/AGENT-HARNESS-RUNTIME-PROTOCOL-ONTOLOGY-LANDSCAPE-2026-09-14.md`, `docs/research/HARNESS-PROVISIONING-STANDARDS-2026-09-18.md`, `docs/research/HARNESS-WORKING-DIRECTORY-SYSTEMS-PRIOR-ART-2026-09-24.md`, `docs/research/FIRST-PARTY-TEN-THOUSAND-HARNESS-PACKAGES-2026-09-22.md`, `docs/research/HARNESS-AND-LIBRARY-PLAN-2026-09-22.md` |
| Contact | Baltor.AI, 1428 Bryn Mawr St, Saxton, PA 16678, United States | `docs/legal/PRIVACY-NOTICE.md` |

## What the fact check changed

The brief listed "independent review from three model families" for the live
slide, and `README.md` says each of the 43 skills was approved by reviewers
from model families other than the one that wrote it. The review record,
`reviews.json`, names the model of reviewer one only, and the multi-family
panel is roadmap step S-6.63, still proposed. The deck therefore says three
independent reviewers, none of them the item's author. The README sentence
needs the same correction.

Nothing private was copied. The Y Combinator package outside the repository
was read for its outline only; no revenue, projection, customer or unapproved
claim is on the deck, and it has no team or funding slide.

## Checks

| Check | Result |
|---|---|
| `tools/test_deck_page.py` | 17 of 17 |
| `tools/test_website_site_map.py` | 15 of 15 |
| Browser suite, `service-workspace-browser-deck-4.json` | see the successor record below |
| Browser suite, `service-workspace-browser-deck-3.json` | 707 of 707, 135 of 135 removed-guard controls detected, on 7b81822b |
| Hardcoding gate on an export of the commit | exit 0, no new high finding |
| markdownlint, the CI scope | 0 issues |

Two failed runs are kept beside their successors:

- `service-workspace-browser-deck-1.json`: 701 of 702. The phone check counted
  the 13 pixel eyebrow labels as body text; the design standards set eyebrows
  at 12 to 13 pixels, so the check now leaves them out, as it leaves out the
  source notes.
- `service-workspace-browser-deck-2.json`: 179 of 180. The page crashed on
  `/terms`. Inferred cause: the shared `/tmp` had reached its quota, since a
  shell write there failed with a quota error in the same minute. Later runs
  keep their temporary files under the home folder.

Screenshots of every slide at 1440 by 900 and at 390 wide sit beside each
report as `service-workspace-browser-deck-N-deck-1440-NN-slide.png` and
`-deck-390-NN-slide.png`. The repository ignores pictures under `artifacts/`,
so they stay in the working tree that ran the check.
