# Handoff: website design review, September 23, 2026

This is the status of the website design review line, written when the owner
asked for the work to stop. The review itself is in
[the design review record](WEBSITE-DESIGN-REVIEW-2026-09-23.md).

## Where the work is

- Worktree: `/home/username/.le-integration/site-review`, a detached worktree
  at `243a8811` with one commit on top. Nothing was pushed.
- Reference worktrees, detached and unchanged: `/home/username/.le-integration/site-r17ref`
  at `3d2fe4e9` (release 17) and `/home/username/.le-integration/site-g2ref`
  at `44a4b426` (the unmerged website line). Each has two ignored links,
  `.venv` and `showcase/node_modules`.
- Screenshots and tools, outside the repository:
  `/home/username/.le-ci-tmp/site-audit/` (`shots/` holds the 457 PNG files,
  `run/` holds the raw measurements, `view/` holds viewing tiles).

## What is done

1. Full-page PNG files with header and footer crops at 1440 by 900 and 390 by
   844 for 14 addresses and the homepage library section, on live, release 17
   and the website line, plus the website line's eight extra pages, the seven
   other live hostnames, a local control copy of live, and five live pages at
   1920 by 1080.
2. Measurements of links, bands, padding, maximum widths, empty runs, overflow,
   rendered fonts, type, primary buttons, words, dark bands, and button, card
   and badge styles, in `artifacts/website-audit-2026-09-23/metrics.json`.
3. A scroll-depth pass (page height in screens; positions of the first heading,
   first primary action, first price and footer; empty share; band padding),
   added on the coordinator's request, in the same file.
4. `artifacts/website-audit-2026-09-23/screenshots.json`: every PNG with its
   SHA-256 digest, source, width and capture time.
5. The review record with 18 findings ranked by severity, a page-by-page table,
   the scroll-depth table with three changes per page, the release 17
   comparison and the distinct values measured.
6. Two independent second opinions, desktop and phone, compared in the review
   record.

## What is left, in order

1. Re-run the hardcoding delta gate with the two Markdown files present (it was
   run only with the two JSON artifacts present).
2. Capture signed-in views and dark mode, which this review did not cover.
3. Turn the findings into roadmap work under package D-18 (website fixes) and
   carry out the fixes in the website source. This review changed no source.

## Checks run and results

| Check | Result |
|---|---|
| Capture of all pages on four sources | 150 page captures, 0 errors, 457 PNG files |
| Scroll-depth pass | 142 page measurements, 0 errors |
| Every internal link found on every captured page | All answer 200 on live, release 17 and the website line |
| HTTP status of 32 addresses on each source | Table in `metrics.json` (`httpStatus`) |
| Hardcoding delta gate (`--fail-on-new high`) with the two JSON artifacts present | Exit 0; 632 high findings, none new at high |
| `markdownlint-cli2@0.23.2` on the two new Markdown files and the records index | 0 issues in 3 files |
| Vale 3.18.0 with the repository styles on the same three files | 0 errors, 0 warnings |
| `python tools/build_records_index.py --check` after regenerating | Current |

Known failures: none in the checks above. Not run: the full continuous
integration suite, the offline link check (`lychee` is not installed here) and
the hardcoding gate with the Markdown files present.

## Commands to continue

Serve a revision locally with the live-shaped configuration (from the
revision's worktree; the website line needs the environment with the MCP 1.x
library, `/home/username/loop-engine/.venv`, used read only):

```bash
cd /home/username/.le-integration/site-r17ref
PYTHONPATH=src .venv/bin/python /home/username/.le-ci-tmp/site-audit/serve_like_live.py /tmp/base.json
```

Capture, measure and rebuild the artifacts (jobs are in `run/job-*.json`; a
job's `base` must point at a running service):

```bash
cd /home/username/.le-ci-tmp/site-audit
node capture.mjs run/job-live.json
node scrolldepth.mjs run/job-live.json run/depth-live.json
python3 tile.py live
python3 build_artifacts.py
```

Run the hardcoding delta gate:

```bash
cd /home/username/.le-integration/site-review
PYTHONPATH=devtools/src .venv/bin/python -m loop_engine_devtools.cli --hardcoding-audit \
  --allowlist devtools/hardcoding-allowlist.yaml \
  --baseline devtools/hardcoding-ci-baseline.json --fail-on-new high
```

## Live and external effects

- Read-only page loads of `https://baltor.ai` and its hostnames `www`, `app`,
  `docs`, `status`, `examples`, `demo` and `baltor-pilot.fly.dev`, at three
  widths, and single `curl` status reads of 32 addresses. Each page load read
  `/api/v1/capabilities` and `/api/v1/account/identity`, as a visitor's browser
  does. No form was submitted, no account or waiting list entry was created
  and no credential was used.
- Local services on `127.0.0.1` with fixture providers only; all were stopped.
- No push, no deployment, no model call, no spending.
