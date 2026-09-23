# Work archive, September 23, 2026

The owner, September 23, 2026: "We need to aggressively get all work committed
and into main, or archived." This record lists what was archived, where, and how
to bring any of it back. Every commit that is not on `main` and every
uncommitted change found in a worktree of this repository was saved before a
worktree or branch was removed.

## What is where

| Archive | Location | Check |
|---|---|---|
| Every reference before the cleanup, including all branches, the stash and every worktree head that is not on `main` | `/home/username/.le-safety/archive-all-refs-20260923.bundle` | `git bundle verify` reports it okay |
| Every reference after the cleanup, including `refs/archive/20260923/*` | `/home/username/.le-safety/archive-all-refs-20260923-after-cleanup.bundle` | `git bundle verify` reports it okay; 76 archive references |
| The uncommitted changes of 40 worktrees (tracked changes as a binary patch, untracked files as a `tar.zst`, with the path, head and status) | `/home/username/.le-safety/worktree-dirty-20260923/<name>/` | Listed in [dirty-snapshots.tsv](../../artifacts/work-archive-2026-09-23/dirty-snapshots.tsv) |
| The whole working folder of the Claude session of September 23 | `/home/username/.le-safety/session-2026-09-23-scratchpad.tar.zst` | Digests in [archive-digests.txt](../../artifacts/work-archive-2026-09-23/archive-digests.txt) |
| Local archive references (kept in the repository's object store, not pushed) | `refs/archive/20260923/worktrees/<name>` and `refs/archive/20260923/branches/<branch>` | Listed in [archive-refs.txt](../../artifacts/work-archive-2026-09-23/archive-refs.txt) |

The bundles and snapshots stay on this machine and are not pushed, because
old branches hold key-shaped test fixtures and private material, and the
repository is public.

## What changed

- 115 worktrees were removed after their state was archived: 33 had a head
  that is not on `main` (each kept as an archive reference), and 29 held
  uncommitted changes (each kept as a snapshot). The full list with heads and
  archive names is [removed-worktrees.json](../../artifacts/work-archive-2026-09-23/removed-worktrees.json).
  No running process used any of them.
- 47 local branches were deleted. The 20 that were not merged into `main` are
  kept as `refs/archive/20260923/branches/<branch>`. Only `main` and
  `checkpoint/full-capability-2026-09-21` remain, as the branch rules require.
- The stash `stash@{0}` (showcase work parked in August) was kept as it is.
- 27 worktrees remain: the shared checkout, the clean checkout of `main` at
  `/home/username/loop-engine-main`, the handoff tree, Codex's active build and
  review worktrees (`/home/username/.le-codex-build/*` and
  `/home/username/.le-codex-review-20260923`, in use by the next session), the
  worktree that holds the Python environment with `mcp` 2.2.0
  (`/home/username/.le-wave2/mcp-revision`), and the fourteen September 23
  line worktrees that the [line register](../../artifacts/handoff-2026-09-23/LINES.md)
  names.
- The shared checkout's uncommitted files were compared with `main`: 172 are
  identical on `main`, 16 are older copies of files `main` has since
  corrected, and the Codex review transfer record and worktree pointer are now
  committed. The business economics note stays in the private folder. The
  checkout itself was not changed; its snapshot is
  `/home/username/.le-safety/worktree-dirty-20260923/loop-engine/`.

## What is not on `main`, and where it is

What each of these holds, and whether it still needs work, is in the
[branch content triage](BRANCH-CONTENT-TRIAGE-2026-09-23.md) and the
[September 23 line register](../../artifacts/handoff-2026-09-23/LINES.md). The
four unfinished September 23 lines are also saved as patches under
`artifacts/handoff-2026-09-23/patches/`.

| Former worktree | Head | Branch | Archive reference (`refs/archive/20260923/worktrees/…`) | Uncommitted files | Snapshot |
|---|---|---|---|---|---|
| `.le-ci-export/7b1e5acf3e1e49891ae906fe9074eefa76de9d30` | `7b1e5acf` | detached | …/le-ci-export_7b1e5acf3e1e49891ae906fe9074eefa76de9d30 | 0 | no |
| `.le-ci-export/e0fcccf` | `e0fcccfb` | detached | on main | 1 | yes |
| `.le-ci-tmp/round-two-mutants` | `7b1e5acf` | detached | …/le-ci-tmp_round-two-mutants | 0 | no |
| `.le-ci-tmp/round-two-review` | `7b1e5acf` | detached | …/le-ci-tmp_round-two-review | 0 | no |
| `.le-consolidation/g1-payments` | `96fda824` | detached | …/le-consolidation_g1-payments | 0 | no |
| `.le-consolidation/g2-website` | `44a4b426` | detached | …/le-consolidation_g2-website | 0 | no |
| `.le-consolidation/g3-intelligence` | `28b7f033` | detached | …/le-consolidation_g3-intelligence | 10 | yes |
| `.le-engines/x1` | `6fceeea2` | detached | on main | 6 | yes |
| `.le-integration/restore-d18-catalogue-pay` | `781b76c9` | detached | …/le-integration_restore-d18-catalogue-pay | 80 | yes |
| `.le-integration/restore-d18-ci-audit-names` | `49a129d4` | detached | …/le-integration_restore-d18-ci-audit-names | 14 | yes |
| `.le-integration/restore-d18-docs` | `ca62214d` | detached | …/le-integration_restore-d18-docs | 0 | no |
| `.le-integration/restore-d18-intel-tree` | `2589d3a9` | detached | …/le-integration_restore-d18-intel-tree | 0 | no |
| `.le-integration/restore-d18-occupation` | `381cc525` | detached | on main | 18 | yes |
| `.le-integration/restore-d18-overnight` | `880371e5` | detached | …/le-integration_restore-d18-overnight | 6 | yes |
| `.le-integration/site-g2ref` | `44a4b426` | detached | …/le-integration_site-g2ref | 0 | no |
| `.le-stabilize/r2-release` | `4e6a228f` | detached | …/le-stabilize_r2-release | 0 | no |
| `.le-wave3/model-use-test` | `1e998176` | detached | …/le-wave3_model-use-test | 0 | no |
| `loop-engine/.claude/worktrees/wf6-campaigns` | `c7cb3e2e` | pay/web-campaigns | …/loop-engine_.claude_worktrees_wf6-campaigns | 0 | no |
| `loop-engine/.claude/worktrees/wf_059b60f1-136-4` | `2296c8fc` | release/catalogue-live | on main | 5 | yes |
| `loop-engine/.claude/worktrees/wf_163570aa-59d-1` | `8d5bb007` | wave3/green-ci | …/loop-engine_.claude_worktrees_wf_163570aa-59d-1 | 0 | no |
| `loop-engine/.claude/worktrees/wf_163570aa-59d-5` | `70168f37` | worktree-wf_163570aa-59d-5 | …/loop-engine_.claude_worktrees_wf_163570aa-59d-5 | 0 | no |
| `loop-engine/.claude/worktrees/wf_163570aa-59d-7` | `664327f9` | worktree-wf_163570aa-59d-7 | …/loop-engine_.claude_worktrees_wf_163570aa-59d-7 | 21 | yes |
| `loop-engine/.claude/worktrees/wf_17b40c64-552-1` | `add9b7ce` | release/carry-approvals | on main | 127 | yes |
| `loop-engine/.claude/worktrees/wf_2c5a17d0-bee-4` | `ade90f0e` | release/catalogue-round-two | on main | 121 | yes |
| `loop-engine/.claude/worktrees/wf_582812c1-fbf-2` | `54c35a89` | wave4/promotion-codes | on main | 1 | yes |
| `loop-engine/.claude/worktrees/wf_90f15b07-bb7-1` | `6329b837` | wave8/overnight-pages | on main | 7 | yes |
| `loop-engine/.claude/worktrees/wf_90f15b07-bb7-2` | `8f7513c8` | wave8/overnight-runnable | on main | 1 | yes |
| `loop-engine/.claude/worktrees/wf_a4d66b9e-235-1` | `e146e56b` | wave7/occupation-tables | on main | 8 | yes |
| `loop-engine/.claude/worktrees/wf_a4d66b9e-235-2` | `6bb1d77c` | wave7/occupation-axis | …/loop-engine_.claude_worktrees_wf_a4d66b9e-235-2 | 0 | no |
| `loop-engine/.claude/worktrees/wf_a9500b52-cd6-1` | `43a2c28c` | pay/billing-customer | …/loop-engine_.claude_worktrees_wf_a9500b52-cd6-1 | 1 | yes |
| `loop-engine/.claude/worktrees/wf_ac2dc435-f2e-1` | `36d8bc7a` | wave2/campaign-pages | …/loop-engine_.claude_worktrees_wf_ac2dc435-f2e-1 | 0 | no |
| `loop-engine/.claude/worktrees/wf_ac2dc435-f2e-12` | `ae4bb6b7` | worktree-wf_ac2dc435-f2e-12 | …/loop-engine_.claude_worktrees_wf_ac2dc435-f2e-12 | 0 | no |
| `loop-engine/.claude/worktrees/wf_ac2dc435-f2e-14` | `6cd5cbce` | worktree-wf_ac2dc435-f2e-14 | …/loop-engine_.claude_worktrees_wf_ac2dc435-f2e-14 | 0 | no |
| `loop-engine/.claude/worktrees/wf_ac2dc435-f2e-15` | `38ab39c5` | worktree-wf_ac2dc435-f2e-15 | …/loop-engine_.claude_worktrees_wf_ac2dc435-f2e-15 | 0 | no |
| `loop-engine/.claude/worktrees/wf_ac2dc435-f2e-16` | `fef00c0d` | worktree-wf_ac2dc435-f2e-16 | …/loop-engine_.claude_worktrees_wf_ac2dc435-f2e-16 | 2 | yes |
| `loop-engine/.claude/worktrees/wf_ac2dc435-f2e-18` | `36d8bc7a` | worktree-wf_ac2dc435-f2e-18 | …/loop-engine_.claude_worktrees_wf_ac2dc435-f2e-18 | 267 | yes |
| `loop-engine/.claude/worktrees/wf_ac2dc435-f2e-2` | `16e1403a` | wave2/waitlist | …/loop-engine_.claude_worktrees_wf_ac2dc435-f2e-2 | 0 | no |
| `loop-engine/.claude/worktrees/wf_ac2dc435-f2e-3` | `046731d9` | wave2/intelligence-organization | …/loop-engine_.claude_worktrees_wf_ac2dc435-f2e-3 | 0 | no |
| `loop-engine/.claude/worktrees/wf_ae05bc07-baf-18` | `0e2ca9b3` | pay/catalogue-release | …/loop-engine_.claude_worktrees_wf_ae05bc07-baf-18 | 0 | no |
| `loop-engine/.claude/worktrees/wf_ae05bc07-baf-21` | `007cf9bb` | pay/container-journey | …/loop-engine_.claude_worktrees_wf_ae05bc07-baf-21 | 0 | no |
| `loop-engine/.claude/worktrees/wf_ae05bc07-baf-23` | `ce9036b6` | pay/accounts | …/loop-engine_.claude_worktrees_wf_ae05bc07-baf-23 | 0 | no |
| `loop-engine/.claude/worktrees/wf_bce6c2d4-baf-1` | `825162df` | wave6/harness-component-intelligence | …/loop-engine_.claude_worktrees_wf_bce6c2d4-baf-1 | 4 | yes |
| `loop-engine/.claude/worktrees/wf_bce6c2d4-baf-2` | `240c1270` | wave6/documentation-content | …/loop-engine_.claude_worktrees_wf_bce6c2d4-baf-2 | 0 | no |
| `loop-engine/.claude/worktrees/wf_bce6c2d4-baf-3` | `6e0ae3e2` | wave6/polish | on main | 3 | yes |
| `loop-engine/.claude/worktrees/wf_cb91ffac-592-1` | `62d86761` | wave9/model-guidance | on main | 7 | yes |
| `loop-engine/.claude/worktrees/wf_cb91ffac-592-2` | `057eccda` | wave9/subdomain-surfaces | on main | 8 | yes |
| `loop-engine/.claude/worktrees/wf_eb5e10dc-951-1` | `fd5eeea1` | wave10/machine-fit | on main | 14 | yes |
| `loop-engine/.claude/worktrees/wf_eb5e10dc-951-2` | `169184a4` | wave10/status-page | on main | 1 | yes |
| `loop-engine/.loop-engine-dev/fabric-readiness-20260913-N8fyhI/compact-snapshot` | `6f062197` | detached | on main | 29 | yes |
| `loop-engine/.loop-engine-dev/fabric-readiness-20260913-N8fyhI/runtime-snapshot` | `d23938bb` | detached | on main | 23 | yes |
| `loop-engine/.loop-engine-dev/fabric-release-20260914-V6F5I6/source` | `1a18e105` | detached | on main | 38 | yes |
| `loop-engine/.loop-engine-dev/ollama-review-preparation-20260913-OFLZBE/latest-snapshot` | `dd49ca34` | detached | on main | 10 | yes |
| `loop-engine/.loop-engine-dev/ollama-review-preparation-20260913-OFLZBE/source-snapshot` | `693ca60a` | detached | on main | 10 | yes |

## How to bring something back

Restore a removed worktree at its archived head:

```bash
git -C /home/username/loop-engine worktree add --detach /home/username/.le-restore/NAME refs/archive/20260923/worktrees/NAME
```

Then put back its uncommitted changes, if it had any:

```bash
cd /home/username/.le-restore/NAME
git apply --3way /home/username/.le-safety/worktree-dirty-20260923/NAME/tracked.patch
tar -I zstd -xf /home/username/.le-safety/worktree-dirty-20260923/NAME/untracked.tar.zst
```

Restore a deleted branch's commits, without making a branch, from
`refs/archive/20260923/branches/BRANCH`. If the local references are ever
lost, fetch from the bundle:
`git fetch /home/username/.le-safety/archive-all-refs-20260923-after-cleanup.bundle 'refs/archive/*:refs/archive/*'`.
