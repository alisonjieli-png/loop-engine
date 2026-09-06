# The 5 PM run

    intake  ->  gameplan  ->  attempt  ->  verify  ->  morning report

Two tools, both runnable now:

| tool | does |
|---|---|
| `tools/session_intake.py` | reads the day's Claude Code transcripts, proposes candidates with evidence |
| `tools/overnight.py` | plans each candidate, attempts it on its own branch, verifies with the project's own gate |

## The verification oracle is free

Every overnight system has to answer "how do I know I fixed it?" This one
does not have to guess. A `failing_gate` candidate **is** a command the
engineer ran that exited non-zero — `npx biome check ...`, `pytest`, `tsc`.
That command is the acceptance test: already written, already trusted by the
person who will read the report in the morning. The night's job is to make
it exit zero, and there is no ambiguity about what success means.

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
content in the file — it asserts outcomes it did not verify, and a candidate
built from it inherits that. Every signal comes from tool results or the
engineer's own words.

### Ranking was corrected by its first real run

The first scan of real transcripts returned three genuine lint failures
alongside a `cat` of a missing path and a timed-out version-probe loop.
"Failed once and never succeeded" catches *looking around* as readily as it
catches *broken*. The distinguishing question is not how often a command
failed — it is whether anyone would care that it did. Hence `_GATE`, and
hence a one-off non-gate failure is dropped rather than ranked low: a
candidate list padded with exploration teaches the morning reviewer to skim,
and then the real ones get skimmed too.

Timeouts are excluded outright. A timeout says the command was slow, not
that the code is wrong.

## What the run never does

- **No commit, no push, no merge.** Each attempt is a branch cut from the
  recorded commit.
- **Refuses a dirty tree.** If the engineer left uncommitted changes, the
  candidate is skipped rather than branched from, so nothing of theirs moves.
- **Keeps failed attempts.** A branch that never reached a passing gate is
  reported as an unfinished attempt, not deleted. A failed attempt with a
  real error in it is worth more to a morning reviewer than silence.
- **Reports an empty night honestly.** If nothing unresolved was observed,
  it says so. A night spent on invented work is worse than a night idle.

## Running it

```bash
python3 tools/overnight.py --dry-run --max-tasks 3
```

```bash
OLLAMA_API_KEY=... XDG_DATA_HOME=/some/fresh/dir python3 tools/overnight.py --max-tasks 3
```

The report lands in `~/.loop-engine/overnight/<date>.json`.
