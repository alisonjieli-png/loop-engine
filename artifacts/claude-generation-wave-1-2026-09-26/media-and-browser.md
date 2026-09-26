# Claude generation wave 1: media-and-browser cohort

Date: September 26, 2026. Producer: `claude_code.session`, family `anthropic`, method
`claude_code_direct_authoring/v1`. Every package is a candidate. None is approved here; the
independent review belongs to another model family, through the same prechecks and screening
call as every other package.

## Counts

| Measure | Value |
|---|---|
| Packages written | 37 |
| Skills | 34 |
| Instruction files (`AGENTS.md` with `CLAUDE.md`) | 3 |
| Payload files | 128 |
| Packages passing the deterministic prechecks | 37 |
| Packages refused by the prechecks | 0 |
| Packages left out | 0 |
| Largest similarity between two packages (five-word shingles) | 0.069 |

Domains: ffmpeg command building and checking, loudness, subtitles and timecode, edit decision
lists, colour lookup tables, image headers, batch resizing, photo metadata, SVG safety, sprite
atlases, glTF and OBJ models, Blender renders and scripting rules, render manifests, frame
sequences, scene templates, a media processing graph, an asset licence register, and browser
control (Playwright selectors, test lint, network recordings, screenshot comparison).

## Where the material is

The package bodies stay outside this repository.

- Candidate catalogue: `/home/username/baltor-library/claude-wave-1/media-and-browser/candidates`
  (`starter_catalogue_candidate_items/v3`, source revision
  `c3db340877001fe07f0a835e3b91b7d55c8f8ca8`).
- Cohort record with the package list, digests, changes and limits:
  `/home/username/baltor-library/claude-wave-1/media-and-browser/COHORT-RECORD.md`.

## Tests

- Every script package has a `scripts/test_*.py` that includes its known-wrong case and a run of
  the script as a process. All 34 test files passed offline under Python 3.10.20 and again under
  Python 3.14.4 with Pillow 12.1.1, each in its own subprocess with a 120 second limit.
- The prechecks command of `artifacts/review-throughput-2026-09-24/community_campaign.py` over the
  catalogue: 37 items, 0 refused, no findings.
- Not run: no ffmpeg, ffprobe or Blender binary is installed on the authoring machine, so built
  commands were checked but not executed, and the Playwright browser run was not executed.
