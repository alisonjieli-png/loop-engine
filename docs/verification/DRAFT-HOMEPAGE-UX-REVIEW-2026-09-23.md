# Draft homepage visual review, September 23, 2026

Kind: read-only review of the **in-flight** S-6.33 redesign in
`/home/username/.le-wave3/landing-redesign`, compared with the
[saved live baseline](LIVE-UI-UX-AND-ACQUISITION-REVIEW-2026-09-22.md).
This is design input to [S-6.33](../roadmap/roadmap.yaml), not a release
decision or a second task list. The draft worktree was not edited. No form
was submitted, account used, payment started or external provider called.

## Observed snapshot and method

The draft worktree was at revision `a51ac96` plus uncommitted changes. The
rendered source file digests were `index.html`
`85fc5d64831531eb67fc8d9e499d7ce4b2dbbf996b93a0febfe6b17c1e32cc39`,
`architecture.css`
`731d0b00717b8ceb1928381e35c33307d751212d20d7f650c6b4516aedeeb48c`,
and `service.js`
`742b7970c9c5d880468ff77f48319eeb6b9cc55eefa114841d782f34f0025acb`.
The bytes were unchanged when checked after the browser pass. A real local
service fixture served those assets over loopback with waiting-list access
open and public registration closed. Isolated headless Chrome rendered
1440 × 900, 390 × 844 and 320 × 700 viewports. All requests outside the
local fixture were blocked. The inspected pages raised no JavaScript page
errors and had no horizontal overflow. The local fixture is not the live
deployment or an identity-provider test.

Saved evidence: [measurements](assets/draft-homepage-ux-2026-09-23/measurements.json),
[desktop hero](assets/draft-homepage-ux-2026-09-23/home-desktop-1440x900.png),
[desktop full page](assets/draft-homepage-ux-2026-09-23/home-desktop-1440x900-full.png),
[mobile hero](assets/draft-homepage-ux-2026-09-23/home-mobile-390x844.png),
[mobile full page](assets/draft-homepage-ux-2026-09-23/home-mobile-390x844-full.png),
[mobile Get started destination](assets/draft-homepage-ux-2026-09-23/get-started-mobile-390x844.png),
and [folder stage](assets/draft-homepage-ux-2026-09-23/home-desktop-folder-stage.png).

## Findings against the live baseline

| Concern | Draft observation | Assessment for S-6.33 |
|---|---|---|
| Owner's right-hand example concern | The old search card has become a five-stage dark panel at x725–1380 and y145–787 on desktop, **655 × 642 pixels**. The saved live card was 495 × 468 pixels. The new panel shows the intended step folder and explains multiple native file types, but it is larger and still sits beside the opening copy. | The right-hand weight and left-to-right interruption remain. Consider making the opening message full-width and placing the demonstration in the next band, while keeping the stage labels. |
| Product distinction in the hero | The broad headline, “Supercharge your developers and AI agents,” and the long positioning, price and model-key paragraphs remain. The fresh-harness-per-step point appears in a small note near the bottom of the panel's first stage, after a visitor has noticed and operated the panel. | Put the focused fresh harness and selected material into the main opening sentence. Move supporting price, key and harness-definition details below the primary action. |
| First action | At desktop width the **Get started** button is at y573–624, visible in the first 900 pixels. At 390 × 844 it is at y849–900, entirely below the first screen; at 320 × 700 it starts at y924. | The mobile first-viewport target from the live review is still unmet. Shorter hero copy and a shorter header should bring the action into view. |
| Mobile navigation | The header remains 254 pixels tall at 390 and 320 pixels because six navigation links occupy two rows under brand, appearance and sign-in. All links remain visible and are ordinary keyboard-focusable links. | A compact, keyboard-usable menu can save substantial space. Its behavior still needs a keyboard and screen-reader check once built. |
| Invitation route | The hero action opens `/connect`. With waiting-list access open, that page contains the form without another click. A direct `/waitlist` visit also shows it. At 390 × 844, the email field starts at y1102 and submit button at y1439; the invitation card begins below the first screen. | The former `/signup#waiting-list` extra-click problem is repaired in this draft, but the actual form is still too low for a phone visitor arriving from the hero or a campaign. |
| Evidence labeling | Radio stages **Split**, **Folder** and **Check** say “Illustration of the design being built.” **Search** and **Download** say “Recorded from this release's library.” Their legend repeats the distinction. Desktop stage changes kept the panel at 480 pixels high; a focused radio moved to the next stage with ArrowRight. The draft's six local demonstration checks passed. | This is clearer than the old example. The recorded checks establish consistency with the local packaged library, not that a native harness loaded files or finished the illustrated task. Retain the labels and avoid presenting the four illustrative check outputs as a completed customer run. |
| Page flow | Alternating ground, white, tinted and night bands make sections easier to distinguish. The full draft is 4,640 pixels tall on desktop and 8,228 on mobile, against 4,389 and 7,873 in the saved live review. The first subsequent band begins at y863 desktop and y1865 mobile. | Section separation improves, but the first screen remains almost entirely hero and demonstration. Repeated explanations of search, selected downloads and step material remain lower on the page. |

The visible copy in the new panel says today's download is one Markdown file
and that multi-file packages and the fresh per-step harness are still being
built. That distinction matters because the folder stage shows `AGENTS.md`,
`CLAUDE.md`, `SKILL.md`, a Python script, a protocol configuration and a lock
file. It is an illustration of the target behavior, not an offered package
or an observed customer result. The six local checks in
`tools/test_homepage_demonstration.py` passed in the draft worktree; they do
not make the overall step native-client proof.

## Specific next pass

For S-6.33, keep the explicit recorded-versus-illustrated labels and the
direct form path. Make the fresh, focused harness the first explanation;
reduce the desktop panel's dominance or move it below the opening copy;
bring the primary action wholly inside 390 × 844; compact the mobile header;
and move the invitation email field into the first phone viewport of the
Get started page. Re-run the same viewports and follow the hero action to
the visible field. Preserve the draft and its failures until a successor
is checked.

This review does not measure conversion, screen-reader behavior, a real
waitlist submission, identity-provider delivery, or the live site's later
state. The draft may change while Claude Code continues working.
