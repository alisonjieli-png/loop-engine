# Launch media inventory

Kind: inventory of the existing editable videos and images, checked against
the live sites on October 16, 2026 between 14:25 and 14:55 UTC. It says which
are current, which need refreshing and why, and the exact command that renders
each again. Nothing was rendered for this inventory except the press-kit
screenshots, which are light.

Run the commands from the repository root. Install the pinned tools first:
`npm ci --prefix showcase` (the video exporters need the FFmpeg binaries that
its install step fetches) and, for the launch motion, also
`npm ci --prefix examples/32_creative_arena`. Every exporter refuses an
existing output folder, so give each run a new absolute path. Render one heavy
video at a time on a shared machine, and look at every frame sheet before
publishing.

## Summary

| Item | State on October 16 | Needs |
| --- | --- | --- |
| Launch motion advertisements | Current | Optional: an AgentStudios shot |
| Signed-out product tour | Current, if recorded close to launch | Record again on the gate day |
| Website deck page | Current live; offline renders show older counts | Update the recorded counts before an offline render |
| Deck pitch video and older social draft | The pitch video would show older counts | Refresh the deck counts, then render |
| Original website media | Current | Nothing |
| Share cards | Three current, one headline out of date | Render again |
| Deck card | Old navy mark | Render again |
| Brand marks and icons | Current | Nothing |
| Press-kit screenshots | Current at 14:40 UTC | Capture again on the gate day |

## Launch motion advertisements

Source: [`showcase/marketing/launch91/`](../launch91/README.md), commit
`d1995be6` of October 13, 2026. Six 30-second advertisements (2D, 2.5D and 3D
treatments, each at 1920 by 1080 and 1080 by 1920), an original score, SRT
captions, keyframes and a selected-frame GLB for Blender.

The copy in `timeline.mjs` carries no counts or prices. It names
dontbeameatproxy.si, agentfeeds.si, getagentfoundry.si, agentafk.si and
baltor.ai, and labels AgentAFK as a local preview with no hosted execution.
All five sites answered 200 on October 16, and AgentAFK still describes
itself as a free local public preview, so the advertisements are current. They
predate AgentStudios (live since release 92 on October 14) and do not show the
library count; add a shot in `timeline.mjs` only if the launch wants either.

```bash
node --test showcase/marketing/launch91/test.mjs
node showcase/marketing/launch91/export.mjs /absolute/new/proof-directory proof
node showcase/marketing/launch91/export.mjs /absolute/new/video-directory all
node showcase/marketing/launch91/contact-sheets.mjs /absolute/new/video-directory /absolute/new/contact-sheets
```

The `proof` run makes 30 keyframes without encoding video; check them first.
The `all` run encodes all six videos and is the heavy one. Replace `all` with
`2d`, `2.5d` or `3d` for one treatment.

## Signed-out product tour

Source: [`showcase/marketing/launch91/walkthrough.mjs`](../launch91/walkthrough.mjs).
It records the real public pages of the four `.si` sites in nine chapters of
90 to 120 seconds, with the original score and subtitles, and allows only GET
and HEAD requests to those origins.

Every page and form field the tour drives was present on the live sites on
October 16 (collection search, the reading-profile builder, the AgentFoundry
examples filter, Public Good search, and the AgentAFK task list and download).
A recording shows the interface on the day it is made, so record it again on
the gate day. Its Public Good chapter needs the grants that expire on
October 31 and November 1, 2026 to be renewed if the launch moves later.

```bash
node showcase/marketing/launch91/walkthrough.mjs /absolute/new/tour-directory
```

## Website deck page

Source: `src/loop_engine/core/service_runtime/web_assets/deck.html`, served at
<https://baltor.ai/deck> and `deck.baltor.ai`. Its ten slides tie every number
to a saved record, and `tools/test_deck_page.py` checks that tie.

In a browser the page replaces its recorded counts with the live ones from the
capabilities record, so visitors see 1,560,856 files and 256,380 harness
components. The recorded fallback in the file is the earlier October 9 record:
1,557,669 files and 255,967 components. Any render without the live service,
such as the pitch video below, shows those older numbers. Engineering should
update the recorded counts to the
[current publication record](../../../artifacts/architecture-audit-2026-09-19/catalogue-creative-originals-2026-10-09.json)
through the deck's own source notes and checks before an offline render.

## Deck pitch video and older social draft

Source: [`showcase/marketing/export.mjs`](../export.mjs) and
[`social-ad.html`](../social-ad.html), commit `885ed377` of September 30,
2026. A silent 30-second portrait draft in four scenes, using a real render of
the Ashen Wilds demo, and a two-minute landscape video of the ten deck slides.

The social draft's copy carries no counts or prices and still describes the
live demo: `/demo/ashen-wilds` answered 200, and the arena page still has
every control the exporter uses (only the "Run" choice in the motion list is
filled in by the page script and was not checked by a plain read). The pitch
video renders the packaged deck over loopback with outside requests blocked,
so it would show the older counts above. Refresh the deck's recorded counts
first, then render both:

```bash
node showcase/marketing/export.mjs /absolute/new/pitch-and-social
```

## Original website media

Source: [`showcase/original-previews/`](../../original-previews/README.md),
commit `dcc442e4` of October 11, 2026. Copper Current, a twelve-second silent
procedural loop, and First Light, a twelve-second instrumental cue. Both are
on the AgentStudios homepage with their editable source. They carry no facts
that change with releases, so they are current.

```bash
node showcase/original-previews/export.mjs /absolute/new/original-previews
node showcase/original-previews/music.mjs showcase/original-previews/score.json /absolute/new/first-light.wav
```

## Share cards and the deck card

Sources: `tools/render_share_cards.mjs` and `tools/render_deck_card.mjs`. Both
draw 1200 by 630 cards from the packaged site with no network connection and
read each headline from the page that shows it.

| Card | Card headline | Live page heading on October 16 | State |
| --- | --- | --- | --- |
| `share-card.png` | Give your agents a head start. | Give your agent a head start. | Out of date by one word |
| `share-card-feeds.png` | Give your agent sources it can check. | The same on `/feeds/setup` | Current |
| `share-card-harness-files.png` | Files your harness can pick up and use. | The same on `/harness-files` | Current |
| `share-card-gallery.png` | See what each creative file makes. | The same on `/gallery` | Current |
| `deck-card.png` | The right setup for every step your agent takes. | The same on `/deck` | Current text, but drawn on September 24 with the navy tile the site replaced on September 28 |

```bash
node tools/render_share_cards.mjs
node tools/render_deck_card.mjs
```

Both write into the packaged web assets, so the new cards reach visitors with
the next release. Look at each card before committing it.

## Brand marks and icons

`baltor-mark.svg`, the three icon sizes and the five brand marks are current;
the [press kit](press-kit.md#logo-and-icon-files) lists them. Do not redraw
them.

## Press-kit screenshots

Twelve WebP captures in [`screenshots/`](screenshots/capture-record.json),
taken at 14:40 to 14:42 UTC on October 16. Capture them again on the gate day,
compare, and replace the files only after looking at them:

```bash
node showcase/marketing/launch-2026-10/capture-screenshots.mjs /absolute/new/screenshots
```

## Not launch material

The 26-slide architecture presentation described in
[`showcase/README.md`](../../README.md) is a dated architecture snapshot, not
a product pitch. Leave it out of launch posts.
