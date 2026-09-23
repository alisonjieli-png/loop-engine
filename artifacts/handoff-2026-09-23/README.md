# Handoff folder, September 23, 2026

Everything the September 23 session left for the next one, in one place. Start
with the [session handoff](../../docs/context/SESSION-HANDOFF-2026-09-23.md);
this folder holds what it links.

A session that starts outside this checkout finds the same map at
`/home/username/START-HERE-BALTOR.md`, and Codex's global instructions
(`/home/username/.codex/AGENTS.md`) point Baltor work there. The uncommitted
work in the shared checkout was copied on September 23 at 14:34 UTC to
`/home/username/.le-safety/codex-uncommitted-20260923T1434/`, with the list of
the 15 files that also changed on `main`.

## In this folder (part of the repository)

| Path | What it is |
|---|---|
| `LINES.md` | Every line of work: its commit, where it is (on `main` or a patch), its own handoff file and what remains |
| `patches/` | The four unfinished lines as `git format-patch` files, based on `main` at `243a8811`: sign-up and the Get started funnel, the documentation pages, the use-case pages with status and the hostname map, catalogue round two. Apply with `git am` in a detached worktree |
| `lines/` | The handoff note of each patched line |
| `website-audit/TARGET-SITE-MAP.md` | The decided site map: header, footer groups, hostname pages, the funnel and guide split, scroll budgets |
| `website-audit/*.json` | Live page depth and the 18-size device sweep of release 20 |
| `audit-canvas/` | The website audit canvas as files: seven boards (`*.dc.html`), `canvas.json` and the four first-screen screenshots. The boards are HTML with inline styles and read as design references without the canvas; the canvas itself is <https://claude.ai/artifact/U8VDRBQYdvShmaVVUYM8k4>, which only the owner's login opens |
| `scripts/` | The scripts the session ran: `ci-run-wt.sh` (full CI on an export of a revision), `qa-release.sh` (live checks after a release, run from the released worktree), `depth.mjs`, `sweep.mjs`, `shots.mjs` (page depth, device sweep, first screens), `site_inventory.py` (header, footer and views of any revision), `build_audit_canvas.py` (regenerates the canvas boards) |

The scripts keep this machine's absolute paths. `ci-run-wt.sh` now defaults to
the environment with `mcp` 2.2.0
(`/home/username/.le-wave2/mcp-revision/.venv-mcp2`) and writes its logs to
`/home/username/.le-ci-tmp/ci-logs/<revision>/`. Some line handoff notes name a
copy of these scripts under `/tmp/claude-1000/...`: that session folder is
gone; use the copies here.

## On this machine, outside the repository

| Path | What it is |
|---|---|
| `/home/username/loop-engine-main` | A clean detached checkout of `main` for reading and for starting new worktrees. The shared checkout `/home/username/loop-engine` holds another session's uncommitted work at `385c647`: never reset, stash or overwrite it |
| `/home/username/.le-integration/<line>` | The detached worktree of each line (`r21`, `r22-ui`, `signup`, `round-two`, `library`, `overnight`, `site-inventory`, `site-review`, `site-standards`, `site-docs`, `site-usecases`, `site-guides`, `site-devices`, `site-uat`) and `handoff`, the tree that was pushed |
| `/home/username/.le-ci-tmp/site-audit/` | Screenshots (`shots/`: 457 from the design review; `devices/`: the responsive lab and its contact sheets), the acceptance-test tools (`uat/`: axe-core, Lighthouse, pixelmatch installed), `depth/` and the target site map |
| `/home/username/baltor-bundles/round-two-4be111f` | The catalogue round two bundle (114 items, digest `7f82235475f4e19b3288f0949bda7b87b11fe1273d235b08e54b50143c7383ea`) |
| `/home/username/.le-library/ls1-runs/run-2026-09-23-b/candidates.db` | The 3,251 staged library candidates |
| `/home/username/.le-safety/` | Safety bundles and backups, including `session-2026-09-23-scratchpad.tar.zst`, the whole working folder of the September 23 session |
| `/home/username/baltor-private/handoff-2026-09-23/` | Private material that stays out of this public repository: the handbook (`handbook/baltor-handbook-v7.html`), the seven topic pages, the tracker page, the design canvas files, the logo work with the owner's sheet and the traced marks, and research notes |

## On claude.ai (the owner's login)

| Artifact | Local copy |
|---|---|
| Website audit canvas <https://claude.ai/artifact/U8VDRBQYdvShmaVVUYM8k4> | `audit-canvas/` here |
| Website design canvas <https://claude.ai/artifact/Rtmq5qQByY2656efjRBoN3> | `/home/username/baltor-private/handoff-2026-09-23/design-canvas/` |
| Handbook <https://claude.ai/artifact/NmqrRcuhDj97nvFGztZqQT> | `/home/username/baltor-private/handoff-2026-09-23/handbook/` |
| Seven topic pages (north star, architecture, server, client, engines, front end, operations) | `/home/username/baltor-private/handoff-2026-09-23/topic-pages/` |
| Development tracker <https://claude.ai/artifact/KSN2vSw1niawnEmMK1xHJJ> | `docs/roadmap/DEVELOPMENT-TRACKER.md` in the repository, and `/home/username/baltor-private/handoff-2026-09-23/tracker/` |
