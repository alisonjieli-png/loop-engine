# Original website media examples

Copper Current is a twelve-second silent procedural loop. First Light is a
twelve-second instrumental cue with an original four-bar score. These are
small website demonstrations, not complete films or admitted catalogue items.

All drawing, score and synthesis code is original Baltor work. There are no
stock images, audio samples, third-party fonts, lyrics, model calls or remote
assets. The source and its generated video and audio are covered by the MIT
licence in this folder. Chrome, Playwright and FFmpeg keep their own licences;
their binaries and dependencies are not part of the downloadable source.

## Edit the loop

Open `orbit.html` through a local static server to see the animation, pause it,
or switch to the geometry revision. For example, from this folder:

```bash
python3 -m http.server 8000 --bind 127.0.0.1
```

Then open `http://127.0.0.1:8000/orbit.html`. The scene settings in
`orbit.mjs` control duration, size, ribbon count, winding, radius and camera
tilt. `drawOrbit` draws an exact time without depending on the wall clock.
The revision changes twelve ribbons and three windings to eight ribbons and
two windings, with a different radius. Duration, canvas and palette stay fixed.

## Edit the music

The score in `score.json` records tempo, chord voicings, melody timing and
notes. `music.mjs` synthesizes every voice from mathematics and deterministic
noise. Node.js 20 or later is sufficient to render a new stereo PCM file:

```bash
node music.mjs score.json first-light.wav
```

The command refuses an existing output file. The production revision moves
tonal notes up two semitones and reduces melody gain by about 3 dB. The rhythm,
percussion and twelve-second duration stay fixed. A changed key is a variation
of this cue, not another independent capability.

## Reproduce the previews

The complete source archive keeps this folder under `showcase/` and includes
the existing `showcase/tools/media-common.mjs` helper and pinned dependency
metadata. Use an installed Chrome or Chromium, Node.js 20 or later, and the
dependency versions in `showcase/package-lock.json`. The prototype used
FFmpeg 7.0.2 and ffprobe 4.0.2. Dependencies and renderer binaries are external
requirements, not included source files.

From the archive root, after providing those dependencies in `showcase`:

```bash
node showcase/original-previews/export.mjs /absolute/path/to/new-output
```

`LOOP_SHOWCASE_BROWSER`, `FFMPEG_PATH` and `FFPROBE_PATH` can name installed
executables. The exporter renders original and revised clips, checks complete
decoding, exact loop closure, dimensions, durations, byte bounds, musical
structure, repeatability and decoded audio peak headroom. A run may take two
CPU cores; use an external two-core, 2 GiB, ten-minute resource limit. It
refuses an existing output folder and requests no external assets.

The image uses Canvas2D, not a hardware-GPU benchmark. The MP4 is 960 by 540
at 24 frames per second, without audio. The MP3 is stereo at 44.1 kHz; codec
padding can make its container duration slightly longer than the twelve-second
score. File checks do not establish artistic quality. Publishing a generated
preview in Baltor requires a separate review of the actual media and source
rights.
