# Worktree audit, September 25, 2026

Kind: dated record for roadmap package D-18, "every branch and worktree
merged, silent merge losses restored". It was taken at 18:50 UTC with the
operator script `/home/username/baltor-private/tools/audit_worktrees.sh`,
which reads each worktree and changes nothing. The full table is kept
outside the repository at
`/home/username/baltor-private/wrap-up/worktree-audit-2026-09-25.txt`.

## What the audit measures

For each worktree it asks whether the checked-out revision is on
`origin/main`. For one that is not, it counts the files that the worktree's
own commits changed and that are missing from main, differ from main, or are
the same. A file that differs is not yet a loss, because main may hold a
newer version; the September 25 repair compared the added lines of each
commit with main to tell the two apart.

## Result

110 worktrees: 78 on main (many with uncommitted leftovers from builds) and
32 whose commits are not ancestors of main.

```text
32 open worktrees, September 25, 2026
├── Paused lines the registry tracks (resume after the weekly limit, October 1)
│   ├── support, help centre and changelog      8 commits, 64 files missing from main
│   ├── stack starters                           5 commits, 262 files missing
│   ├── sample tasks and /try                    2 commits, 51 files missing
│   ├── search engine optimization and blog      4 commits, 28 files missing
│   ├── engine selector and custom harnesses     7 commits, 26 files missing
│   ├── staff protocol server and interface      3 commits, 15 files missing
│   ├── licensed import                          9 commits, 7 files missing
│   ├── referral programme                       1 commit, 4 files missing
│   ├── serving millions of items                4 commits, 1 file missing
│   └── decisions, deck, models, showcase and persona fixes: only differing files
├── Finished research lines with commits not on main
│   └── toolsmith, showcase research, affiliate research (2 files missing),
│       and the component standard landing line (7 commits, 1,611 files the same)
├── Superseded on purpose
│   └── .le-accounts/invite-release: invitations were retired for one way in
├── Restored on September 25
│   └── the review campaign (.le-review-throughput-20260924, .le-prep-7214801):
│       commits 72148011 and 91009c36, now on main as 9830e1f7 and f77a7e93
└── Not in the registry, to review
    ├── .le-integration/round-two                3 commits, 72 files missing, 182 differ
    ├── .le-integration/site-usecases, signup and site-docs
    ├── .le-stakeholder-review-20260924          1 file missing
    ├── .le-decisions-20260924-s2                6 files missing
    ├── .le-persona-fixes-run, run2 and run3, .le-showcase-20260924-verify2
    └── .le-ci-tmp/deck/wt-v2
```

## How to close each one

1. List the commits that are not on main and compare each commit's added
   lines with main, as `72148011` was compared: a line main holds, or holds in
   a newer form, is not lost.
2. Save a worktree with uncommitted changes as a bundle or patch before
   anything else touches it.
3. Port what is missing onto main in its own reviewed commit that names the
   source commit, run the checks that cover it, and push.
4. Record the closed worktree here or in the next dated record, so the next
   audit does not count it again.

A paused line resumes and merges its own work when its agent restarts; the
audit only confirms that the work is still there and tracked.

## Resolved the same evening

The comparison tool is `/home/username/baltor-private/tools/commit_loss_report.sh`.
Its first run counted every line of some files as missing, because `/tmp` is
over its quota and the temporary copy of main's file was empty; it now keeps
its temporary files under `$HOME` and stops on an empty copy.

| Worktree | Finding | Decision |
|---|---|---|
| `.le-stakeholder-review-20260924` | Commit `3a9fe1d6` of that morning: the stakeholder review record and 15 roadmap steps, never on main | Restored. The steps are numbered S-6.181 to S-6.195, because S-6.177 to S-6.180 were taken on main the same day; the record says so. |
| `.le-integration/round-two` | A second round of the first-catalogue review by the same three reviewers: 114 of 123 items approved, against 43 on main | Not restored. Of its 71 extra approvals, the independent panel of September 22, with reviewers of four other families, had reviewed 29 and rejected all 29. |
| `.le-integration/site-usecases`, `signup` and `site-docs` | Work in progress of September 23 | Superseded: the use case pages, the hostname pages, email-first sign-up and the documentation view went live later in other commits. |
| `.le-decisions-20260924-s2` | The step stations and the material station of the paused decisions line: five source files main lacks | Kept with the paused line and added to its registry entry; it merges when that line resumes. |

The round-two result bears on the 42 first-catalogue items served today. They
were approved by the same kind of same-family review, and independent
reviewers rejected every item of that review they examined. Their review by
two other families (roadmap step S-6.178) may therefore withdraw many of
them, and replacements should be ready before it runs.
