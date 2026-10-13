# Editable launch motion and a signed-out product tour

Use this recipe to make captioned product advertisements, edit their claims,
or reuse the layered cards and original 3D component sculpture in another
project. The same factual edit has three visual treatments and two compositions.
These are workflow illustrations, not recordings of an agent completing work.
The separate walkthrough records the real public websites.

## What each file gives you

| Source | Consumer use | Main edits |
|---|---|---|
| `timeline.mjs` | A contiguous 30-second edit with product claims and visible limits | Shot titles, descriptions, URLs, timing and accent colors |
| `scene.mjs` and `style.css` | Flat kinetic cards or perspective/parallax cards | Card content, entrance timing, depth, rotation and landscape/portrait layout |
| `world.mjs` | Original rounded geometry, materials, lighting and camera motion | Palette, component spacing, slab labels and camera orbit |
| `audio.mjs` | A deterministic original stereo instrumental bed | Chord frequencies, envelopes, levels and rhythm |
| `export.mjs` | Complete local MP4s, captions, keyframes, a selected-scene GLB and a check record | Choose a treatment or proof-only export |
| `blender-scene.py` | Import the embedded GLB, add a native orbit, save a Blender project and reopen it | Native camera, orbit and studio rendering settings |
| `walkthrough.mjs` | An actual signed-out interface tour longer than 90 seconds | Explicit allowed origins, chapter actions and factual captions |
| `contact-sheets.mjs` | Five decoded movie frames per treatment/composition as PNG previews | Preview dimensions and declared sample frames |
| `test.mjs` | Offline timing, claim-limit, score, source and negative-control checks | Add controls when changing a boundary |

The 2D treatment uses flat translations and line motion. The 2.5D treatment
uses perspective, depth and independent card rotation. The 3D treatment uses
real extruded meshes, materials, lights and a moving perspective camera.
Two aspect ratios are exports of a treatment, not two different capabilities.

## Setup

Use a checkout of Loop Engine with Node 22, Chrome, and the repository's
pinned dependencies. Run these commands from the repository root:

```bash
npm ci --prefix showcase
npm ci --prefix examples/32_creative_arena
node --test showcase/marketing/launch91/test.mjs
node showcase/marketing/launch91/export.mjs /absolute/new/proof-directory proof
```

The existing dependency locks supply Playwright Core 1.62.1, FFmpeg Static
5.3.0, FFprobe Static 3.1.0 and Three.js 0.186.1. The exporter checks the Three.js
version. Chrome defaults to `/opt/google/chrome/chrome`; set `BALTOR_CHROME`
when your installation differs. If these modules are already installed
elsewhere, set `BALTOR_SHOWCASE_MODULES` and `BALTOR_THREE_MODULES` to their
respective `node_modules` directories. No dependency is downloaded by the
exporter itself.

The target's parent directory must exist; the target itself must not. Keep
separate output directories for each attempt. The browser serves the original
source and declared Three.js installation over loopback, blocks outside
requests, and reads no customer account. It uses system Arial/Helvetica
fallbacks, not a fetched or redistributed font. Font substitutions can change
the composition, so rerun the proof on a different machine.

## Render, inspect and revise

The proof produces 30 keyframes across all treatments, five shots and two
compositions, without encoding the videos. Inspect those PNGs and the checks
in `verification.json`. Fix clipping, unreadable labels or misleading copy
before the full export.

```bash
node showcase/marketing/launch91/export.mjs /absolute/new/video-directory all
node showcase/marketing/launch91/contact-sheets.mjs /absolute/new/video-directory /absolute/new/contact-sheets
```

The full export creates six 30-second H.264/AAC MP4 advertisements at 24 frames
per second, in 1920×1080 and 1080×1920. It also writes an original score WAV,
SRT captions, keyframes and a selected-frame GLB. It decodes every video in
full and checks duration, frame count, dimensions, audio, text bounds and
sampled motion. The visible typography makes the advertisements useful when
muted. The music contains no voice, purchased sample or external recording.

For one treatment, replace `all` with `2d`, `2.5d` or `3d`. To preview motion
interactively, use the same loopback asset mappings as `export.mjs` and open
`/?treatment=2.5d&play=1`. The exporter is the supported reproducible entry
point; opening `index.html` with a `file:` URL will not resolve module imports.

A meaningful revision should change the message or composition, not just a
color. The first review corrected AgentAFK's illustrated filename from an
invented JSON name to its actual `baltor-tasks.txt` download and clarified
that the list contains ready task files. The original proof was retained;
the changed edit was rendered again in all six compositions. Keep the same
before/after evidence when you adapt this recipe.

The timeline includes local-preview and access limits. Recheck them against
the real product when editing. A profile does not activate a hosted feed.
A component preview does not prove installation. An AFK task list does not
start a worker, cloud supervisor or adaptive scheduler.

## Reopen the 3D component

With Blender 5.2.1 available, the following creates a native project from
the export's embedded GLB and tests it in a separate process:

```bash
blender --background --factory-startup --threads 2 \
  --python showcase/marketing/launch91/blender-scene.py -- \
  build /absolute/video-directory/foundry-workflow-sculpture.glb \
  /absolute/new/project.blend /absolute/new/build-check.json

blender --background --factory-startup --threads 2 \
  --python showcase/marketing/launch91/blender-scene.py -- \
  reopen /absolute/new/project.blend \
  /absolute/new/reopened.blend /absolute/new/reopen-check.json
```

Each command also writes a PNG beside its new check record. The GLB is a
selected-frame component sculpture. The Blender adapter adds a native orbit
animation and camera; it does not reconstruct the full HTML edit. Edit the
complete video through `timeline.mjs`, `scene.mjs`, `world.mjs` and `style.css`.
The native consumer checks actual meshes, changing transforms, a camera and
embedded images before saving. External GLB resources are refused.

## Record the real interface tour

```bash
node showcase/marketing/launch91/walkthrough.mjs /absolute/new/tour-directory
```

This records the actual public HTTPS pages in a fresh signed-out browser,
including collection filtering, example reading-profile selections, component
filtering, Public Good search and browser-local AFK task-list preparation.
The `/demo/tasks/` paths are visibly illustrative. No worker is executed.
Only GET/HEAD network requests to the four declared origins are allowed.
No authorization token, sign-up, email, checkout or model call is made.

The result includes the continuous raw WebM, a 1080p MP4 with original music
and a default subtitle track, separate SRT captions, chapter screenshots,
the local demo task list and an evidence record. A complete tour must have
nine chapters and a duration between 90 and 120 seconds. Unlike the six short
advertisements, it satisfies the duration of a long-form walkthrough. That
does not prove conversion, task benefit or a fresh customer's installation.

## Recovery and review limits

An existing output path is refused. Keep failed folders and their records;
use a new folder after identifying the cause. Never run two exporters into
one folder. If a dependency or browser cannot start, verify the pinned local
installation rather than removing the network restrictions. If a public page
or request fails during the walkthrough, retain the capture and diagnose it;
do not claim the remaining chapters were recorded.

The source tests and decoder checks do not establish aesthetic quality or
listening quality. Review keyframes and playback before publication. The
initial qualification includes visual review and technical sound-level checks;
it does not claim a human listening session, customer results or native
streaming qualification for earlier website checks.

The recipe renders locally and publishes nothing. Catalogue admission of
source, PNG previews, MP4, WAV, GLB and Blender files is separate. A media type
that the current qualification engine cannot validate remains a candidate,
even when its native decoder passes here. Advertising spend stays with the
owner.

## Provenance and rights

The campaign text, diagrams, geometry, score generator and glue code are
original work in this repository, under its MIT licence. Product names and
logos remain their operator's marks; a code licence does not grant endorsement
rights. No external model, stock footage, music sample or generated image is
included. The recorded interfaces are the operator's public sites. Those
captures are marketing evidence, not permission to relicense underlying
Public Good catalogue material.

Three.js is MIT-licensed. FFmpeg and the other installed tools retain their
own licences; this recipe does not bundle their executables. Preserve
`THIRD-PARTY-NOTICES.md` and any dependency licence when redistributing them.
Generated output records contain exact source hashes. If rendering before
the source commit, their `source_revision` is the checkout base; the file
hashes identify the exact candidate bytes. A delivery manifest must also bind
those unchanged bytes to the reviewed source commit before integration.

Prior work reused: `showcase/marketing/export.mjs` supplied the new-output,
local-only, caption and full-decode pattern; `showcase/tools/media-common.mjs`
supplied the pinned browser/media tool arrangement; the existing creative
arena supplied the pinned Three.js and GLB/Blender route. The old still-fade
pitch is not counted as a newly rendered campaign or an advanced motion engine.
