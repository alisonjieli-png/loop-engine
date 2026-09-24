# Review note: Unattended git safety rules

Candidate only. Not approved, staged, served or published.

This note is for the independent review panel. It is never delivered to a harness.

## Method

A composable instruction section plus a local check script for runs that nobody watches. The section forbids pushing, fetching, pulling, force options, `--no-verify`, resets, rebases, amends, stashes, cleans, merges, cherry-picks, whole-tree restores and branch or tag changes. It keeps one local commit per ticket whose message names the ticket key, staged file by file, and no commit for a ticket that needs no change.

`scripts/git_ticket_check.py` turns the rules into checks a small model can run:

- `begin --ticket KEY` records the start commit, the branch, every other reference, the number of HEAD movements, and the files changed or untracked before the ticket (fingerprinting changed tracked files). It refuses a merge, rebase, cherry-pick, revert or bisect in progress, and tracked changes other than the root instruction files `AGENTS.md`, `CLAUDE.md` and `GEMINI.md` and the paths the host lists in `.baltor/unattended-git-rules/host-placed.json` (`unattended_git_host_placed/v1`: a `paths` list of workspace-relative files, or folders ending in `/`). The host writes that list after it places or merges files for the step, for example a settings fragment merged into a tracked `.claude/settings.json`. The model has no option to widen it.
- `verify --ticket KEY [--require-commit | --no-change]` fails with a named code when: the start commit left the history; HEAD moved by anything but a plain commit (amend, reset, rebase, checkout, merge, pull, stash); a remote-tracking reference changed; a branch was created, deleted or rewritten; a tag was created, moved or deleted; the stash changed; more than one commit exists; the commit does not name the whole key; the commit holds `.baltor/` files or files changed before the ticket; a fingerprinted file changed; or a file that was untracked before the ticket is gone, for example after `git clean`. `--require-commit` also needs exactly one commit and no tracked change outside it. `--no-change` needs no commit and no tracked change, for a ticket that needs no change.
- A key counts only as a whole key: no letter, digit, dot, dash or underscore touches it, except a final full stop. So `ABC-7.2: ...` and `ABC-71: ...` do not name ABC-7, and `... for ABC-7.` does.
- A new branch that another worktree has checked out is allowed, because a host that runs steps in parallel creates such branches.
- Every answer is one JSON object with a `next` field that names the real ticket key. A failure always says: do not repair the history, record the ticket as blocked. The section tells the model to save the whole answer in `.baltor/state/unattended-run-rules/KEY-git.json`, which the a14 ticket ledger accepts as evidence.

## Authoring basis and sources

Original text and code, MIT. Repository files at `a1fc7432`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package format.
- `AGENTS.md` of the repository: save work before any command that can discard it, never drop a stash or reset a shared checkout, never rewrite published history.
- `tools/overnight_queue.py`: unattended queue runs that must not block or repeat finished work.

No outside text or code was copied or paraphrased. Git behavior used by the script (reflog subjects such as `commit (amend):`, porcelain paths relative to the repository top, `--git-path` markers, `worktree list --porcelain`) was confirmed with git 2.53.0 on this machine.

## Inputs and outputs

Inputs: a ticket key, an optional workspace root, and the optional host list. Output: one JSON answer, and one state file `.baltor/state/unattended-git-rules/KEY.json` (`unattended_git_ticket_start/v2`, which adds the host list and replaces v1), written atomically without following links.

## Effects

Declared: `reads_fs`, `writes_fs`, `spawns_process`. The script starts local `git` processes with `GIT_OPTIONAL_LOCKS=0`, reads the repository and the host list, and writes the state file. The section tells the model to stage and commit. The tests create repositories and one extra worktree only in temporary folders with an empty git configuration. No network, no model call, no secret.

## Closest existing items

- Scout result: none found.
- Wave 5 a13 settings fragments can deny commands at the permission layer, and a04 `guard_shell_command_allowlist` refuses a command before it runs. This package states the procedure and checks the repository state afterwards; it prevents nothing by itself.
- Wave 5 a12 `check_diff_allowed_paths` judges a diff's paths. This package judges history, references and the one-commit rule.
- Wave 5 a14 `unattended_run_rules`: sequencing and blocker records for the same runs.

## Positive example

For ABC-7: `begin --ticket ABC-7`, edit `src/parse.py`, `git add -- src/parse.py`, `verify --ticket ABC-7` shows `staged: ["src/parse.py"]`, `git commit -m "ABC-7: Keep surrounding spaces out of parsed text"`, then `verify --ticket ABC-7 --require-commit` answers pass with one commit. A ticket that needs no change ends with `verify --ticket ABC-8 --no-change`, which answers pass.

## Known-wrong example

The model commits, then runs `git commit --amend`. `verify` exits 1 with `head_moved_by_other_command`, because the HEAD movement log gained a `commit (amend):` entry (`test_amended_commit_is_refused`). The tests also refuse: a second commit; a missing, similar or longer dotted key (ABC-71 and ABC-7.2 for ABC-7); a reset to older history; a moved remote-tracking reference; a new branch and a new tag; a deleted branch and a moved tag; a stash; a commit made with `git add -A` that holds `.baltor/` files; a discarded or committed earlier change; `git clean` removing an owner's untracked draft; a commit or a change under `--no-change`; a missing commit under `--require-commit`; a tree changed before the ticket that the host did not list; the removed `--allow-changed` option; an unusable host list (a path with `..`, the whole workspace, a path under `.baltor/`, an absolute path, a number, a wrong record type); a merge in progress; and bad input.

## Harness placement and verification state

- `AGENTS.md` is composed into the step's root `AGENTS.md` for codex, opencode and pi (observed), goose (documented in `docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md` of the shared checkout) and kimi_cli (unverified).
- Claude Code gets `CLAUDE.md` holding `@AGENTS.md` (file observed, import documented). Gemini CLI gets `GEMINI.md`, a byte copy (documented).
- The script and `LICENSE` go to `.baltor/unattended-git-rules/`. The host writes `host-placed.json` there per step; it is not a package file. Tests are not placed.
- Not observed: any harness following the section or running the script, and a compiler writing the host list. The host must bind a trusted `python3`, because an earlier independent review showed that one found first on `PATH` can be replaced.

## Customer requests

- "I let an agent commit overnight. How do I make sure it never force-pushes or rewrites history?"
- "One commit per ticket with the ticket number in the message, checked automatically."
- "Catch an agent that ran git reset, stash or clean while I was asleep."

## Limits

- The check detects after the fact; it cannot undo a push. A push to a URL, or to a remote without tracking references, leaves no local trace and is not detected; use settings and hooks (a13, a04) to prevent it. A commit made with `--no-verify` also leaves no trace.
- An amend is detected through the HEAD movement log. A disabled log, or one expired on purpose, removes that signal.
- Fast-forward moves of other branches and new branches that another worktree has checked out are allowed, because other worktrees may work at the same time. So a branch this ticket creates and checks out in a new worktree is not detected. A tag another session creates during the ticket, or another worktree's stash, fails the ticket.
- Files that were untracked before the ticket are checked for removal only, not fingerprinted, because test caches rewrite them. Files that git ignores are not recorded, so `git clean -x` on ignored files is not detected.
- Without a host list, a host that merges into tracked files makes every ticket refuse with `tree_not_clean`; that is safe but blocks the night.
- Tested with git 2.53.0 and Python 3.14 and 3.10 on Linux only. No other git version was run.
- No measurement shows that the section improves outcomes.

## Pre-check history

Every command output is kept in `review/PRECHECKS.txt`, and every checker report in `review/precheck-*.json`; the newest report is the gate record.

- Generation rounds (2026-09-23): fill and check passed with no warning for package digests `5041b147` and `5c7ece5b`; 20 tests on Python 3.14 and 3.10; 9 of 9 mutants caught.
- Independent critic (2026-09-23, recommendation repair): begin refused every ticket when the host had merged into a tracked settings file; `git clean` of an owner's untracked file passed; new branches and tags passed although rule 5 forbids them; a ticket with no change could never pass rule 10; `T-1.2` counted as naming `T-1`.
- Repair (2026-09-24): the host list replaces `--allow-changed`; removed untracked files, new branches and new tags fail; `--no-change` and rule 11 give the no-change path; whole-key matching; the blocking section saves the answer in the ticket ledger's folder. The repairer also made state folder creation safe when two commands create it at once, and answers any file system error as JSON. All ten of the critic's scenarios were replayed: the five named problems now fail or pass as intended, the detached HEAD and subfolder runs still pass, and `--no-verify` still passes (listed under Limits).
- Repair checks: the first repair check passed (digest `fae8fa84`, 30 tests). A mutation run then showed that no test covered host list paths in a workspace below the repository top, so `test_host_list_in_a_workspace_below_the_repository_top` was added; its first version expected the wrong pre-existing list and failed on the correct script, and was corrected. 11 of 11 mutants of this package are caught by their named tests (37 of 37 across the assignment), and 12 of the repaired tests fail against the predecessor payload. The final fill and check are recorded in `review/PRECHECKS.txt`.
