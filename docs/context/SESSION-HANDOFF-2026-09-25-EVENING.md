# Session handoff, September 25, 2026, evening

Kind: dated handoff. It follows the
[September 25 afternoon handoff](SESSION-HANDOFF-2026-09-25-AFTERNOON.md),
whose text stays as it was; its first two next steps are done. The
[roadmap](../roadmap/roadmap.yaml) remains the task authority, and the owner's
standing rules are in the
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md.

## What went live since the afternoon

| When (UTC) | What changed | Record |
|---|---|---|
| 16:29 | Fly release 31: the website's download and the Pi extension ask like search does, tier labels on search results, the honest meaning of Verified, the wording rules in one file | [pilot-release-31.json](../../artifacts/architecture-audit-2026-09-19/pilot-release-31.json) |
| 16:38 | The first Community catalogue release, without a redeploy: 93 items, 51 of them Community, the phone skill withdrawn; the homepage count reads 93 | [Community release evidence](../../artifacts/community-release-2026-09-25/README.md) |
| 17:57 | Fly release 32: the signed-in catalogue browser lists Community items with their labels (S-6.177); people check 44 pages and 338 links, catalogue 9 of 9, service 19 of 19 | [pilot-release-32.json](../../artifacts/architecture-audit-2026-09-19/pilot-release-32.json) |

## What the evening found

```text
Findings, September 25 evening
├── A catalogue release reaches the running service within 60 seconds
│   └── a check run inside that window sees the previous release
├── The catalogue check knew only the starter review record
│   └── it now asks each query narrowed to Verified and with the account's
│       own setting, where every other hit must be labelled Community
├── The browser suite does not run in continuous integration
│   ├── its homepage count check failed from release 30 until release 32
│   └── only the local preflight runs it; a nightly run is proposed
└── The hourly release train no longer redeploys a revision that changes
    only artifacts, documents or check tools
```

## Next, in order

1. Close the open worktrees in the
   [worktree audit](WORKTREE-AUDIT-2026-09-25.md), starting with those no line
   tracks. On September 25 the review campaign's commits `72148011` and
   `91009c36` were found outside main and restored as `9830e1f7` and
   `f77a7e93`: a Claude session limit now stops its quota group, a
   calibration-only run selects no candidate, and a verdict from an unnamed
   reviewer leaves the item out.
2. An attribution adapter for the Claude Code lane
   (`/home/username/baltor-library/claude-code-lane`, 607 candidates), after
   `tools/native_proposals_from_overnight_candidates.py`: lane, model, the
   declared family `anthropic`, the idea record of each candidate as a
   committed source, and the file kind. Only skills and instruction files have
   qualified native placements today; the other kinds wait for theirs.
3. September 29 after 17:24 Eastern: Codex reviews the 42 first-catalogue items
   (S-6.178), then the Claude Code lane. Ollama Cloud joins when its allowance
   returns; the daily probe runs at 06:17 Eastern.
4. A nightly run of the browser suite on main that reports failures without
   gating a deploy (S-6.180).
5. The held lines of the morning handoff: the engine selector and staff
   tools, the stack starters, and the move of `http.public_base_url`.
