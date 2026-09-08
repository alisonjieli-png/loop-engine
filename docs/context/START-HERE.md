# Start here

You are working in Loop Engine. This page is the short current picture: what
the repository is, what is green today, what is not, and the first hour of
work. Two companion pages carry the detail:

- [Invariants and traps](INVARIANTS-AND-TRAPS.md): what the machine refuses,
  and the mistakes that have already cost real time here.
- [Ways of running](WAYS-OF-RUNNING.md): every setting that exists today, what
  it changes, and how to add another without removing one.
- [Everything learned, 2026-09-08](EVERYTHING-LEARNED-2026-09-08.md): what the
  last round of work measured, the defects only running found, what this
  project's real problem turned out to be, and what is still unknown. Start
  here if you want the numbers rather than the rules.

The longer orientation, reading order, and component map stay in
[CODEX-START-HERE.md](CODEX-START-HERE.md). Read that when you need depth.
Read this page first.

## What this is, in three sentences

Loop Engine runs open-ended tasks through one runtime object called a Loop.
Everything executable is a Loop: roles (Practitioner, Intelligence, Solution),
run modes, step profiles, budgets and permissions are fields on it, never
subclasses and never a second runtime. Work is judged by evidence the engine
itself produced, so a model saying it succeeded is never the reason a run is
recorded as succeeding.

## State on 2026-09-08, at commit `5d4e7c4`

| Check | Result |
|---|---|
| `--self-test` | 3,412 of 3,412, on Python 3.10, 3.11 and 3.12 |
| `--conformance` | all gates pass |
| `--repo-conformance` | passes |
| `examples/25_host_runtime` unit tests | 140 of 140 |
| GitHub job: public documentation | passes |
| GitHub job: build the distribution | passes |
| GitHub job: suite and conformance gates | fails, at one gate only |

The one failing gate is the hardcoding delta. It reports 260 blocking findings
that predate this work, and it has failed on every push since 2026-09-05. The
self-test and conformance steps inside that same job pass. Nothing else on
`main` is red.

Do not try to make that gate pass by adding allowlist entries or refreshing
the baseline. The findings were measured, not guessed: 163 sit in
`src/loop_engine/core`, 51 are URL literals inside two generated files under
`docs/research/`, 20 sit inside test fixture bodies, and the rest are
scattered. The dominant shape is a record type or status compared as an inline
literal, so the real fix is a schema version registry and enum references at
the comparison sites. That is a project, and it is written up in
[the improvement plan](../implementation/IMPROVEMENT-PLAN-2026-09-07.md),
section 6.

## The rule that shapes every change

Add ways of running. Do not remove them.

The owner's standing instruction is that the engine should support many
configurations, patterns and architectures at once. When a review says a path
is broken, the answer is a typed refusal plus a specified build-out, or a new
policy with the old behavior as the default. It is not deletion. If you find
yourself removing an option to make something simpler, stop and add a setting
instead.

## The first hour

1. Read [AGENTS.md](../../AGENTS.md). It is short and it governs.
2. Check who else is writing here:

   ```bash
   git -C /home/username/loop-engine status --porcelain
   git -C /home/username/loop-engine log --oneline -5
   ps -eo pid,etime,cmd | grep -E 'codex|claude' | grep -v grep
   ```

   Another agent commits into this same checkout. Stage explicit paths. Never
   use `git add -A`. Never discard a change you did not make.
3. Run the gates before you change anything, so you know what was already
   broken. The commands are in the next section.
4. Read [the improvement plan](../implementation/IMPROVEMENT-PLAN-2026-09-07.md).
   It lists every open item with the file it touches, the check that proves
   it, and a status. Items marked `decision` need the owner, not you.
5. Read [the review](../verification/CODE-REVIEW-2026-09-07.md) if you are
   fixing a numbered finding. Every finding there was reproduced by running
   code, and the probe that reproduces it is named.

## Commands

Use the repository virtual environment. It is Python 3.10. The system
`python3` is 3.14 and does not have the package installed, so a bare
`python3` will fail in a way that looks like a missing module.

```bash
cd /home/username/loop-engine

# the complete offline suite, about twenty minutes, no provider is called
PYTHONPATH=src .venv/bin/python -m loop_engine --self-test

# the zero-tolerance architecture gates, about one minute
PYTHONPATH=src .venv/bin/python -m loop_engine --conformance

# repository structure
PYTHONPATH=src .venv/bin/python -m loop_engine --repo-conformance --format json

# the host runtime examples, about one minute
cd examples/25_host_runtime && PYTHONPATH=../../src \
  ../../.venv/bin/python -m unittest discover -s . -p 'test_*.py'

# the development assurance canaries and the hardcoding delta gate
PYTHONPATH=devtools/src .venv/bin/python -m loop_engine_devtools.cli --self-test
PYTHONPATH=devtools/src .venv/bin/python -m loop_engine_devtools.cli \
  --hardcoding-audit --allowlist devtools/hardcoding-allowlist.yaml \
  --baseline devtools/hardcoding-ci-baseline.json --fail-on-new high
```

To run one module's checks while you work, which is much faster than the full
suite:

```bash
PYTHONPATH=src .venv/bin/python -c \
  "from loop_engine.loop import recursive_loop as m; r = m.self_test(); \
   print(r['passed'], '/', r['total']); \
   print([t['test'] for t in r['tests'] if not t['passed']])"
```

## Finishing a change

A change is finished when all of this is true.

- The module's own checks pass, and you added a check for what you changed.
- `--self-test` and `--conformance` pass.
- The documentation checks pass if you touched any Markdown. They are three
  separate checks with different scopes, described in
  [Invariants and traps](INVARIANTS-AND-TRAPS.md).
- You ran the gates yourself and quoted the numbers. Do not report completion
  from intent, from file presence, or from a narrow test.
- The commit and push went to `main`. There are no feature branches here.

## What to be careful about claiming

This repository has a habit of recording evidence carefully, and reports here
are expected to separate what was observed from what was inferred and what is
not established. Two specific cautions:

- A green local suite is not a green build. Cite the GitHub run for your
  commit, because `main` has been failing one gate since 2026-09-05 and a
  report that only quotes local counts hides that.
- A module with passing self-tests and no caller is proven correct and inert.
  Before claiming a capability works, check that a live path reaches it:

  ```bash
  PYTHONPATH=src .venv/bin/python -c \
    "from loop_engine.reachability_report import reachability_report; \
     print(reachability_report('solve_path'))"
  ```
