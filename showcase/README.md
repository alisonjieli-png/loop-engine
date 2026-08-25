# Loop Engine showcase

This folder contains the editable source for the 26-slide Loop Engine
architecture presentation. The browser player, video, captions, PowerPoint,
and PDF read from the same slide data in `showcase-data.js`.

The slides separate the architecture contract from current implementation
status. The public Static Architecture view contains exactly three groups:
Intelligence Search and Retrieval, Web Research, and Custom Plugins.
Self-improvement appears only as a Practitioner task profile. Read the
[architecture drift audit](../docs/architecture/LOOP-ENGINE-ARCHITECTURE-DRIFT-AUDIT-2026-08-25.md)
before using the presentation as an implementation guide.

## View the presentation

Run this command from the repository root:

```bash
python3 -m http.server 8082 --directory showcase
```

Open <http://127.0.0.1:8082>. The player provides play, pause, previous,
next, restart, timeline scrubbing, four speed settings, keyboard navigation,
slide selection, captions, and reduced motion.

## Install export tools

Node.js 20 or newer is required.

```bash
cd showcase
npm ci
```

Keep the local server running while exporting or testing.

## Export files

Create the MP4, WebM, poster, contact sheet, and media evidence file:

```bash
npm run record
```

Create the editable PowerPoint. This command requires LibreOffice with its
Python UNO module:

```bash
python3 build-powerpoint.py
```

Create the PDF:

```bash
npm run export:pdf
```

Create the timed SRT captions:

```bash
npm run export:captions
```

`npm run package` creates the fixed-allowlist manifest, verifies every listed
size and SHA-256 digest, and creates the ZIP. The package excludes installed
dependencies, temporary files, and the raw browser recording.

## Generated artifact names

Exports write these files under `assets/`:

- `loop-engine-architecture.mp4`
- `loop-engine-architecture.webm`
- `loop-engine-showcase.pptx`
- `loop-engine-showcase.pdf`
- `loop-engine-showcase.srt`
- `poster.png`
- `contact-sheet.png`
- `powerpoint-montage.png`
- `media-evidence.json`
- `powerpoint-verification.json`
- `loop-engine-showcase-complete.zip`, after manifest-based packaging

These files are not complete until the matching export command succeeds. The
source repository may contain none of them between revisions.

## Verify the source and player

With the server running:

```bash
cd showcase
npm test
python3 -m py_compile build-powerpoint.py
node --check showcase-data.js
node --check render.js
node --check player.js
node --check verify-powerpoint.mjs
```

The browser tests check all 26 slides, the controls, 1920 by 1080 and 1280 by
720 layouts, text clipping, console errors, and any media files that are
present. The video exporter also performs a complete decode check before it
publishes an MP4 or WebM file. PowerPoint verification checks 26 slides, 26
notes pages, native editable shapes, slide bounds, a 26-page render, and a
26-frame montage.
