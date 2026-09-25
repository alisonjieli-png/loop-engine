# Session handoff, September 25, 2026, afternoon

Kind: dated handoff. It follows the
[September 25 session handoff](SESSION-HANDOFF-2026-09-25.md) of the morning,
whose text stays as it was; its "Next, in order" list is done or replaced by
this one. The [roadmap](../roadmap/roadmap.yaml) remains the task authority,
and the owner's standing rules are in the
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md.

## What the owner asked for since the morning

- "be more aggressive with any fixes, adjustments, pushes, more harness
  component file generation, vetting, deployment", toward 10,000 or 100,000
  United States dollars of monthly recurring revenue within 90 days, and
  "resolve ALL issues"; the owner takes only what engineering truly cannot do.
- A larger hero working directory with more files from the vetted library.
- "YOU CAN ALSO USE CLAUDE CODE, AND CLAUDE CODE AGENTS AND SUB-AGENTS TO
  GENERATE, WE CAN GENERATE AND VET THINGS OURSELF AS WELL".
- The live count of vetted, retrievable components on the website; public and
  private wording rules in one managed place; a faster release path, including
  updates without a full redeploy.

## What is live

| Release | When (UTC) | What changed | Record |
|---|---|---|---|
| Fly release 29 | 14:34 | The models, endpoints and can-I-run directory; the larger hero with five vetted skills; no badge on the pricing card | [pilot-release-29.json](../../artifacts/architecture-audit-2026-09-19/pilot-release-29.json) |
| Fly release 30 | 15:29 | Version 2 provisioning requests with library tiers and the `Baltor-Step-Effects` header, reading files as the default step effect; the live library count on the homepage | [pilot-release-30.json](../../artifacts/architecture-audit-2026-09-19/pilot-release-30.json) |

Release 30 passed the people check (44 pages, 184 views, 338 links) and the
service check (19 of 19). Two of eight catalogue checks failed; the record
explains why it stayed live.

## Two findings of the afternoon

```text
Findings, September 25 afternoon
├── Search offered what download refused
│   ├── search and protocol tools ask with version 2 and may read files
│   ├── the website's download, the Pi extension and the documentation asked with version 1
│   ├── three starter items and every Community item: shown, then refused
│   └── release 31 moves them to version 2; Community is published after it
└── The first catalogue is not two-family Verified
    ├── written with Claude Code; approved September 21 by three reviewers
    │   that did not write it, before the family rule
    ├── the one reviewer whose model is recorded is a Claude model
    ├── the README and the published meaning of Verified claimed two other families
    └── release 31 states the exception everywhere Verified is explained;
        two other families review the 42 items first when they can
```

No family other than Anthropic could review on September 25: the Ollama Cloud
allowance was still spent at 15:50 UTC (probe 5, `glm-5.3`), the Codex limit
lasts until September 29 at 17:24 Eastern, and Tactical failed its
calibration. The first catalogue is therefore the first job for Codex on
September 29 and for Ollama Cloud when its allowance returns.

## Library supply

| Source | State on September 25 afternoon |
|---|---|
| Google lane, 976 candidates from the combined idea grid, reviewed by Claude | 0 approved, 958 rejected, 17 incomplete, 1 refused before review. Blocking reasons: no checkable contract (951), not useful or distinct (730), original rights (400), whole package (188). The idea grid combines data types, tasks and domains mechanically; engineering stops using it as a source. |
| Claude Code lane, `/home/username/baltor-library/claude-code-lane` | 607 candidates written by `claude -p`, planned by one ideation call per batch of 300. They need a reviewer of another family, so they wait for Codex or Ollama Cloud. Batch 2 was paused at about 16:45 UTC, because it draws on the same subscription limit as the release session; `PAUSED.txt` there says how to resume it. |
| Community release 1, `~/baltor-bundles/community-release-1` | 93 items: the 42 of the first catalogue and 51 Community items, with the phone item withdrawn. Publish after release 31 is live with `publish_catalogue.sh community-release-1 4e0484b76924a2d907c7a42bd088ba44b0123f365cf78d3ea8a81d9100f04e9e`, then check retrieval as a customer. |

## Next, in order

1. Release 31: the version 2 clients, the honest Verified meaning, the wording
   rules in one file, and the release 30 record. Then publish Community
   release 1 and check it as a customer.
2. Release 32: the catalogue browser on version 2, with tier labels and its
   browser checks.
3. September 29 after 17:24 Eastern: Codex reviews the first catalogue, then
   the Claude Code lane's candidates. Ollama Cloud joins when its allowance
   returns; the daily probe runs at 06:17 Eastern.
4. The held lines of the morning handoff: the engine selector and staff tools,
   the stack starters, and the move of `http.public_base_url`.

The YC application draft for the owner is private, at
`/home/username/baltor-private/review-2026-09-24/fundraising/YC-APPLICATION-DRAFT-2026-09-25.md`.
