# The 5 PM run

```text
intake  ->  gameplan  ->  attempt  ->  verify  ->  morning report
```

Two tools, both runnable now:

| tool | does |
|---|---|
| `tools/session_intake.py` | reads the day's Claude Code transcripts, proposes candidates with evidence |
| `tools/overnight.py` | plans each candidate, attempts it on its own branch, verifies with the project's own gate |

## Project verification commands

A `failing_gate` candidate records a command that exited non-zero, such as
`npx biome check ...`, `pytest`, or `tsc`. The runner compares that command's
result before and after an attempt. A zero exit is evidence for the command's
checks, not proof that every task requirement is met or that the command is
safe to execute. Transcript discovery does not grant execution permission.

Read the [integration review](verification/ASTRA-INTEGRATION-REVIEW-2026-09-13.md)
and [native session limits](opencode-step-instances.md) before enabling host
execution. Working directories, environment allowlists, and file restoration
do not provide an operating-system sandbox.

This is why intake ranks gates above everything else. A candidate with no
executable gate can still be analysed, but it cannot be verified, and the
run says so instead of implying otherwise.

## What intake counts as a candidate

The strongest signal is **a gate command that failed and was never
subsequently seen succeeding in that session**. It is strong because it is
observed rather than inferred: the transcript records the exit, not an
opinion about it. A command that failed and later passed is a thread the
engineer already closed.

Assistant prose is deliberately **not** read. It is the least reliable
content in the file: it asserts outcomes it did not verify, and a candidate
built from it inherits that. Every signal comes from tool results or the
engineer's own words.

### Ranking was corrected by its first real run

The first scan of real transcripts returned three genuine lint failures
alongside a `cat` of a missing path and a timed-out version-probe loop.
"Failed once and never succeeded" catches *looking around* as readily as it
catches *broken*. The distinguishing question is not how often a command
failed. It is whether anyone would care that it did. Hence `_GATE`, and
hence a one-off non-gate failure is dropped rather than ranked low: a
candidate list padded with exploration teaches the morning reviewer to skim,
and then the real ones get skimmed too.

Timeouts are excluded outright. A timeout says the command was slow, not
that the code is wrong.

## What the run never does

- **No commit, no push, no merge.** Each attempt is a branch cut from the
  recorded commit, in its own worktree under `~/.loop-engine/worktrees`.
- **Never moves the engineer's checkout.** The attempt runs in a separate
  worktree, so uncommitted changes in the checkout are neither touched nor
  carried into the attempt. By default a dirty tree does not stop the run.
  Pass `--require-clean-tree` to skip a candidate whose repository has
  modified tracked files; untracked files never count, because running the
  gate itself creates them.
- **Keeps failed attempts.** A branch that never reached a passing gate is
  reported as an unfinished attempt, not deleted. A failed attempt with a
  real error in it is worth more to a morning reviewer than silence. Nothing
  is removed unless you pass `--prune-worktrees`, described below.
- **Reports an empty night honestly.** If nothing unresolved was observed,
  it says so. A night spent on invented work is worse than a night idle.

## What an unattended run is allowed to do

Every widening is a flag, and every flag is off by default.

| flag | without it | with it |
|---|---|---|
| `--allow-transcript-gates` | commands harvested from transcripts are planned and reported, never executed | they are executed, unattended, with a shell |
| `--allow-compound-gates` | a harvested command containing `\|`, `&&`, `;`, `$(` or a backtick is reported as `compound_command` and never attempted | it is ranked and attempted like any gate |
| `--gate-env NAME` | a gate sees only `PATH`, `HOME`, `LANG`, `TERM` and `TMPDIR` | it also sees `NAME`; repeat the flag for more |
| `--gate-inherit-env` | as above | the gate sees the whole operator environment, as earlier versions did |
| `--require-clean-tree` | a repository with modified tracked files is attempted from its committed `HEAD` | such a candidate is skipped, with the reason in the report |
| `--prune-worktrees` | no worktree is ever removed | worktrees that `git worktree list` registers, under `~/.loop-engine/worktrees` and older than `--keep-days` (default 3), are removed with `git worktree remove` and their branches with `git branch -d`; both refuse unfinished work, and the report lists what was refused and why |
| `--prune-force` | as above | with `--prune-worktrees`, removal is forced and branches are deleted with `-D`, as earlier versions did |
| `--max-model-calls N` | one path may make `--step-model-calls` (default 4) calls per planned step, counted across the whole path | the path's ceiling is `N`; `0` keeps only the per-step ceiling |

A `--gate` typed on the command line is the operator's own choice: it runs
without `--allow-transcript-gates`, and a compound one runs without
`--allow-compound-gates`.

The gate's process environment is built from nothing, by name. A gate that
needs a variable the allowlist does not carry fails in the "gate before"
probe, and the report shows its output, so the fix is one `--gate-env`.

The model-call ceiling is one object shared by every step of a path, charged
after each step. Earlier versions gave each step a fresh ceiling of four,
compared against a counter that restarted at zero, so nothing bounded what a
path spent over a night.

## Running it

```bash
python3 tools/overnight.py --dry-run --max-tasks 3
```

```bash
OLLAMA_API_KEY=... XDG_DATA_HOME=/some/fresh/dir \
  python3 tools/overnight.py --max-tasks 3 --allow-transcript-gates
```

```bash
OLLAMA_API_KEY=... python3 tools/overnight.py --gate "pytest -q" --workspace /path/to/repo
```

The report lands in `~/.loop-engine/overnight/<date>.json`. It records the
policy the run used (flag values, and the names but never the values of the
environment variables gates were given), and for each candidate the plan, the
outcome, and what pruning removed, kept or refused.
