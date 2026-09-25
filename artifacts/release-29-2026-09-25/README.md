# Release 29 evidence, September 25, 2026

Fly release 29 of `baltor-pilot` went live at 14:34 UTC from main `e120cdbdc64ee665010ecf76e33561735e726389` after
continuous integration run 36144951643 passed, through deployment run
36148114747. The image is
`sha256:3184e7efeb8e165b2476e97cb73b16ea36ebdffb09a229ff4fb06294d82a61f6`;
the rollback target is release 27. Fly release 28 was the first attempt of the
same revision; its catalogue grant step found the replaced Machine still
starting, so the deploy was run again. The record is
[`pilot-release-29.json`](../architecture-audit-2026-09-19/pilot-release-29.json).

## What a person sees now

- A models, endpoints and can-I-run directory at /models, /endpoints and
  /can-i-run.
- A larger example in the hero: the working directory of the step that finds
  duplicate customers, with five skills from the vetted library.
- No status badge on the pricing card, and a plain answer to whether a team
  can share one account.

## How it was checked

| Check | Result |
|---|---|
| What a person sees: 44 pages at desktop and phone width, light and dark, and 8 hostnames | no problem; 338 links checked |
| The customer's search and download with the homepage digest guard | 8 of 8 |
| The service transport and isolation | 19 of 19 |

Advice: 135 of 135 addresses answer, and the Pi extension matches on all nine
hostnames. The screenshots are kept outside the repository.
