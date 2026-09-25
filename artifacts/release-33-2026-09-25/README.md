# Release 33 evidence, September 25, 2026

Fly release 33 of `baltor-pilot` went live at 20:13 UTC from main
`88a76a6a5133de344124935c6ee4856693f0b00c` after continuous integration run
36181920081 passed, through deployment run 36184208923. The image is
`sha256:b0c77cc43a8d6075f556d38da3b23a2b5741752976efad65e3e730d3807b0187`;
the rollback target is release 32. The record is
[`pilot-release-33.json`](../architecture-audit-2026-09-19/pilot-release-33.json).

## What a person sees now

- The search panel of the workspace shows the note the service serves:
  search returns references, and fetching a body needs a separate access
  check and may record usage. It no longer names the search backend.

## How it was checked

| Check | Result |
|---|---|
| What a person sees: 44 pages at desktop and phone width, light and dark, and 8 hostnames | no problem; 338 links checked |
| The customer's search and download, with Verified and Community searches and the homepage digest guard | 9 of 9 |
| The service transport and isolation | 19 of 19 |

Advice: 135 of 135 addresses answer, the Pi extension matches on all nine
hostnames, and 216 of 216 detailed browser rules pass on baltor.ai.

The browser suite now runs every night on GitHub. Its first run, started by
hand on this revision (run 36181933005), passed 909 of 909 checks and
detected all 183 removed-guard controls in eleven minutes.

The screenshots are kept outside the repository.
