# Continuous integration and the pre-push check

This guide explains what runs when a revision reaches `main`, how the run is
divided so that it finishes in minutes, how to run the same gates on your
machine before you push, how every generated file is regenerated and checked
against the commit, and how a release train goes from cherry-pick to the push
command in one command. The workflow is
[`.github/workflows/ci.yml`](../../.github/workflows/ci.yml). The release
workflow waits for this whole run to pass before it deploys a revision, so
the wall time of this run is part of every release.

## What runs on a push

Every job starts at once. Nothing waits for another job.

| Job | Python | What it runs |
|---|---|---|
| public documentation | 3.12 | Markdown structure, public language, retired words, links, the benchmark registry, the diagrams and the browser checks of the showcase. Unchanged by the September 26, 2026 change. |
| tools tests, shards a to d | 3.10, 3.11, 3.12 | The tools test modules, one of the shards [`tools/ci_test_shards.json`](../../tools/ci_test_shards.json) names per job, twelve jobs in all. |
| runtime checks | 3.10, 3.11, 3.12 | The embodiment lab, the qualification lab, the served site map, the examples and the product solve acceptance. The default-install onboarding proof runs on 3.12, as before. |
| self-test | 3.12 | `python -m loop_engine --self-test`. |
| conformance and hardcoding gates | 3.12 | `python -m loop_engine --conformance`, the development tools self-test and the hardcoding delta gate. |
| component guides match the source | 3.12 | `tools/check_component_guides.py --run-documented-checks`. |
| build the distribution | 3.12 | The wheel and source distribution. Unchanged. |

Before September 26, 2026 one job per Python version ran every check in
sequence. The ten runs before the change took 1,451 to 1,500 seconds of wall
time each when they passed, and the slowest job, the 3.10 job, took a median
of 1,466 seconds. Inside it the tools tests took 522 seconds, the self-test
354 seconds, the hardcoding gate 195 seconds, the component guides 148
seconds and the conformance gates 85 seconds. The numbers are in
[the evidence folder](../../artifacts/ci-speed-2026-09-26/README.md).

Nothing was dropped. Every module still runs on every Python version, in a
shard. Three checks now run once instead of three times: the self-test, the
conformance gates with the hardcoding gate, and the component guides. Their
results do not read the Python version (no version test exists in their
source), and the tools tests and the runtime checks still exercise the
package on 3.10 and 3.11. They run on 3.12 because the service image is
built on Python 3.12.

## The expected time after the change

The next run of `main` measures the new layout. Until then the expectation
comes from arithmetic on the measured step times, with the install step
counted at its old duration of 36 seconds:

- self-test job: 6 seconds checkout, 10 seconds Python, 36 seconds install,
  331 seconds self-test, about 385 seconds in all;
- conformance and hardcoding gates: about 290 seconds;
- the slowest tools test shard, on 3.10: about 190 seconds;
- runtime checks on 3.12: about 175 seconds;
- public documentation: about 120 seconds, as before.

The self-test job sets the wall time, so a passing run should take about six
and a half minutes instead of about twenty-four and a half. A run has twenty
jobs, which is the number the hosting plan runs at once, so two runs that
overlap queue some of their jobs behind the other run's.

## The shard manifest

[`tools/ci_test_shards.json`](../../tools/ci_test_shards.json) names the
shards and where the module timings are recorded, and nothing else.
[`tools/run_test_shard.py`](../../tools/run_test_shard.py) places the modules
when the shards run: every module that
`unittest discover -s tools -p 'test_*.py'` would load, each weighing its
recorded seconds, the heaviest first into the shard with the least estimated
time. A module that no timing record names weighs the median of the recorded
modules. The same checkout always computes the same placement, whatever
order the files are found in.

Until September 27, 2026 the manifest listed every module under its shard,
with the estimated seconds of each shard. Every new test module had to be
added to a list and to a total, and two lines of work that each added a
module conflicted in that file whenever they were merged. Now a new test
module changes no committed file.

```bash
PYTHONPATH=src:tools python tools/run_test_shard.py --list    # shards, module counts, estimated seconds
PYTHONPATH=src:tools python tools/run_test_shard.py --plan    # the whole placement
```

New modules weigh the median until they are timed. To time the modules that
no record names, each alone in its own process, and write a new dated
record that the manifest's pattern picks up:

```bash
PYTHONPATH=src:tools python tools/balance_test_shards.py --measure unmeasured \
  --output artifacts/ci-speed-YYYY-MM-DD/module-times-YYYY-MM-DD.json
```

[`tools/test_ci_test_shards.py`](../../tools/test_ci_test_shards.py) checks
that every discovered module is placed in exactly one shard, that the
placement does not depend on discovery order, that the manifest lists no
module, that the workflow runs every shard on every Python version, and
that the pre-push script either runs or declines, with a reason, every step
of the workflow.

## The cached environment

Every test-derived job installs the project through
[`.github/actions/python-environment`](../../.github/actions/python-environment/action.yml).
It restores a virtual environment from the workflow cache when one exists
for the exact interpreter version and the current `pyproject.toml`, links
the checkout into it, and puts it first on the path. A change to
`pyproject.toml` or a new interpreter release rebuilds the environment from
scratch; there is no partial restore. Unpinned dependencies therefore move
only when the environment is rebuilt or the cache expires after a week
without use. The default-install onboarding proof still installs the built
wheel into a fresh environment on 3.12, so a broken new release of a
dependency still surfaces there.

## The pre-push check

[`tools/pre_push_check.sh`](../../tools/pre_push_check.sh) runs the gates of
the workflow that need no browser and no container, all at once, and prints
one table. Each gate gets its own temporary folder under
`$HOME/.le-ci-tmp/pre-push/`, never `/tmp`, and its log stays there.

```bash
tools/pre_push_check.sh                      # every gate
tools/pre_push_check.sh --list               # the gates and the declined steps
tools/pre_push_check.sh --only self-test,tools-shard-a
PY=/path/to/python tools/pre_push_check.sh   # an interpreter other than .venv/bin/python
tools/pre_push_check.sh --tree /path/to/worktree
```

The table shows one row for each gate: `pass`, `FAIL`, or `----` for a gate
that could not run, with the seconds it took and, for a failure, the log path
and the first failed check names. Nothing of your shell environment reaches a
gate except the path, so a local credential cannot turn a test into a live
call. The conformance gate rewrites
`src/loop_engine/architecture_conformance.json`; when the tree was clean at
the start, the script puts the committed copy back afterwards, so a run
leaves a clean tree clean.

The steps copied from the workflow call `python`, as the workflow's runner
provides it. Some machines have only `python3`, and a worktree has no `.venv`
of its own, so on September 27, 2026 two gates exited 127 and looked like
failures of the code. Each run now writes a folder holding `python` and
`python3` that run the chosen interpreter, and puts it first on every gate's
path. A gate that still exits 127 found a command missing from the machine.
Its row says `command not found in the local environment: NOT A CODE
FAILURE`, it counts as not run, and the script exits 3 when nothing failed.

When `PY` is not set, the script uses the tree's `.venv`, then the `.venv`
of the checkout that holds the tree's repository, which is how a worktree
finds the project's dependencies, then `python3` on the path. The last case
is listed as a gap of the run, because a step can then fail on a missing
module; such a failure keeps its `FAIL` row, with a hint under it. A copied
step's `pip install` line is left out when the interpreter has no pip or the
system manages it, because a pre-push check does not install packages into
the interpreter it was given.

### What a local run does not cover

After the table, the script lists everything continuous integration runs
that this run did not, in two groups:

- what this run skipped: a missing `vale`, `lychee`, `node` or `rg`, the
  gates left out by `--only`, a working tree that differs from `HEAD` (the
  gates then checked files a push would not send), and a missing command;
- what a local run never covers: the steps that need Docker or a browser,
  and the Python versions other than the local one.

The last line gives the verdict and says `NOT EQUIVALENT TO CI` whenever
either list is not empty, with both counts, for example
`RESULT: all 18 gates passed; NOT EQUIVALENT TO CI (0 skipped in this run,
5 only in continuous integration; listed above)`. Look at the first count:
zero means that this run covered everything a local run can cover. A step
with nothing to check, such as the public language check when no Markdown
file differs from `origin/main`, is not counted.
[`tools/pre_push_summary.py`](../../tools/pre_push_summary.py) prints the
table and the verdict.

On the development machine the self-test reports one failure that passes
in continuous integration, `removed_key_refresh_pause_is_detected`. The
table shows it by name so that you can tell it from a new failure.

[`tools/git-hooks/pre-push`](../../tools/git-hooks/pre-push) is a hook
template that runs the script before every push. Nothing installs it for
you. To use it in one checkout of your own:

```bash
git config core.hooksPath tools/git-hooks
```

To push once without it, run `PRE_PUSH_CHECK=0 git push`.

## Generated views and the pristine check

Sixteen committed paths are generated from other files: the packaged copies
of the architecture and terminology contracts, the semantic dictionary, the
architecture map and diagrams, the served documentation pages, the starter
catalogue release folder, the red team record, the development tracker, the
continuation status, the records index, the public status pages and the
conformance manifest. Continuous integration rebuilds most of them in a test
or a gate and fails when the committed copy differs.
[`tools/regenerate_all.py`](../../tools/regenerate_all.py) holds the one
list, in the order in which one view reads what another writes, and runs
every builder:

```bash
PYTHONPATH=src:tools python tools/regenerate_all.py            # regenerate and report what changed
PYTHONPATH=src:tools python tools/regenerate_all.py --check    # report, then put every output back
PYTHONPATH=src:tools python tools/regenerate_all.py --list     # each view and the check that compares it
PYTHONPATH=src:tools python tools/regenerate_all.py --pristine # regenerate an export of HEAD
```

It runs the fast views a second time and fails when the second run changes
anything, so a builder whose inputs changed after it ran is named instead of
being committed stale. It also fails when a builder writes a file that the
list does not name.

The pristine check answers a different question: is the commit itself
current? It exports `HEAD` with `git archive` into a folder under
`$HOME/.le-ci-tmp/pristine/`, never the working tree, regenerates every view
there with the export's own builders, and fails when anything differs from
the commit, with the differences in a report beside the export. On
September 27, 2026 the second release train passed every local check and
failed in continuous integration, because the status pages had been
regenerated in the working tree before a later commit added a release
record, and the regenerated copy was never committed. The pre-push check runs
the pristine check as a local gate, `pristine-tree`. When the tree is clean
and the conformance gate runs, the export leaves out the slow conformance
manifest, and the `pristine-manifest` row compares the manifest that the
conformance gate wrote with the committed one instead.

## The release train

[`tools/release_train.py`](../../tools/release_train.py) builds a release
train in one command, in a worktree with no uncommitted changes to tracked
files, on `main` or a detached `HEAD`:

```bash
python tools/release_train.py --worktree /path/to/train \
  --trailer "Co-Authored-By: Name <address>" COMMIT COMMIT ...
```

1. It cherry-picks each commit with `-x`, in the order given, and skips a
   commit already on the train.
2. On a conflict it resolves only what a rule can resolve. A generated file
   takes the train's side, because the next step rebuilds it. The shard
   manifest takes the side that names shards only, when the other side still
   lists modules. A YAML file where both sides appended whole entries to the
   same list keeps the train's entries, then the picked commit's; it is
   refused when a side changes a line that was already there, when a side
   is not made of whole list entries, when the result does not parse, or
   when an identifier (`finding_id` or `id`) repeats. Any other conflict
   stops the train: the conflict stays in place, and the script names the
   files and prints the command that continues with the commits still to
   pick.
3. It regenerates every view with the train's own
   `tools/regenerate_all.py` and commits what changed as one final commit,
   "Regenerate generated views".
4. It runs the train's own pre-push check, which includes the pristine
   check, and repeats its result line. With `--skip-gates` it runs only the
   pristine check, and the result says that it is not equivalent to
   continuous integration.
5. It prints the exact push command and the release commands of the guarded
   workflow [`.github/workflows/fly-pilot.yml`](../../.github/workflows/fly-pilot.yml):
   wait for continuous integration on the exact revision, switch the
   deployment setting on for the run and off again afterwards, read it back,
   then run the live checks and record the release.

The script never pushes, never changes a repository setting and never
starts a workflow. It exits 0 when the train is ready, 1 when a gate or the
pristine check failed, and 2 when it stopped.

## Decisions and their reasons

- The self-test, the conformance gates and the component guides run once,
  on 3.12. None reads the Python version, the other jobs keep 3.10 and 3.11
  covered, and 3.12 is the service image's version.
- Four shards, not five. The self-test job sets the wall time, so a fifth
  shard would shorten nothing and would take the run past the twenty jobs
  the hosting plan runs at once.
- The cheap runtime checks stay on every version. They cost about a minute
  and exercise the installed package end to end, which is the cross-version
  evidence the once-only gates no longer give.
- Runs are not cancelled when a newer push arrives. The release workflow
  needs a passing run for the exact revision it releases, and the owner
  wants any checked revision of `main` to be releasable.

## Not yet measured

The wall time of the new layout is an expectation from arithmetic until the
next run of `main` records it. The gain of the environment cache over the
old install step is not measured either; the arithmetic above counts the
install at its old duration.
