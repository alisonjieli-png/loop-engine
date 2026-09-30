# Baltor marketing video sources

This exporter creates a thirty-second portrait social draft and a two-minute
landscape video of the current website pitch deck. Both are silent, with visible
copy and separate SRT captions. Frames fade between scenes. The social draft
uses a real render of the original Ashen Wilds demo, not recorded gameplay.

Run from the repository root after installing the existing showcase dependencies:

```bash
node showcase/marketing/export.mjs /absolute/path/to/a/new-output-directory
```

The output directory must not exist. The exporter uses a loopback-only static
server, rejects asset paths outside the packaged website, blocks outside browser
requests and reads no customer account. It reuses the pinned browser and FFmpeg
tools from `showcase/package-lock.json`. No model call or stock-media purchase
is needed. The outputs include editable HTML source references, captured frames,
MP4 files, captions and a digest-bound verification record.

Inspect the frames and play the videos before publishing. The automatic checks
cover text bounds, slide visibility, duration, decoding and format, not conversion
rate or customer benefit. Any music, narration or new external asset needs its
own rights record. Advertising spend stays with the owner. Automatic reference
video recreation and Public Good downloads remain unavailable until their
delivery tasks pass.
