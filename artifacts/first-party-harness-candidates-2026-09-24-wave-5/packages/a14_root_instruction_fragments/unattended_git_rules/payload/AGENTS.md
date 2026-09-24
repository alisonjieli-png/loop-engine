# Unattended git safety rules

## Applies when

Nobody is watching this run and you work in a git repository. Each ticket ends with one local commit, or with none when it needs no change.

## Rules

1. The git check command is `python3 -I -B .baltor/unattended-git-rules/scripts/git_ticket_check.py`. It prints one JSON answer with a `next` field.
2. Before you change anything for a ticket, run the git check command with `begin --ticket KEY` and the real ticket key.
3. Never push, fetch or pull, and never add or change a remote.
4. Never use a force option or `--no-verify`, and never run `git reset`, `git rebase`, `git commit --amend`, `git stash`, `git clean`, `git merge`, `git cherry-pick`, `git checkout -- .` or `git restore .`.
5. Stay on the branch you started on. Do not create, switch, rename or delete branches or tags.
6. To undo your own edit, edit the file back. To unstage a file you staged by mistake, run `git restore --staged -- PATH`.
7. Stage only files you changed for this ticket, by name: `git add -- PATH`. Never use `git add -A`, `git add .` or `git commit -a`. Never stage files under `.baltor/`.
8. Before you commit, run the git check command with `verify --ticket KEY`. Its `staged` list must hold every file you changed and nothing else.
9. Commit once, after the ticket's checks pass: `git commit -m "KEY: short summary"`.
10. Then run the git check command with `verify --ticket KEY --require-commit`. Git work is done when it answers `"result": "pass"`.
11. A ticket that needs no change gets no commit. Run the git check command with `verify --ticket KEY --no-change` instead; it must answer `"result": "pass"`.

## If a rule blocks the work

If the ticket needs a forbidden operation, a conflict appears, or the check answers `fail` or `refused`, do not try to repair the history. Leave the repository as it is and follow the answer's `next` field. Save the whole answer in the new file `.baltor/state/unattended-run-rules/KEY-git.json` and record the ticket as blocked with that file as evidence.
