# Start here

Loop Engine has one executable runtime, `Loop`. Start with the current
contracts and the owner's recorded requirements. Use dated reports for what
was actually measured, not as instructions to repeat old campaigns.

## Required context

Read [AGENTS.md](../../AGENTS.md), then inspect the branch, revision, dirty
paths, active processes, and known writers. Existing changes are not yours
to discard, commit, or publish without resolving ownership.

Read the
[discrete cognitive or act step Loop node complete explanation](DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-HANDOFF-2026-09-12.md)
in full. Keep the complete phrase and explanation. Then read the
[complete configuration dimension requirement](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md).
The September 13 requirement includes an initial choice and ordered fallback
priorities for every dimension, not just the harness and model.

Read the [flexible composition direction](../architecture/FLEXIBLE-COGNITIVE-AND-ACTION-COMPOSITION.md)
and [grid search guide](../guides/configuration-grid-search-and-optimization.md)
when extending the system. Additional cognitive steps, actions, prompts,
questions, and intelligence are valid directions. The design is not limited
to the smallest workflow or the current dimension inventory.

The [deeper session orientation](CODEX-START-HERE.md) maps current components
and dated evidence. Use the relevant component guide rather than loading
every historical prompt. Read
[reference-source boundaries](REFERENCE-SOURCES.md) before consulting an
older repository.

The [Claude Fable 5.1 review handoff](CLAUDE-FABLE-5.1-REVIEW-HANDOFF-2026-09-13.md)
is the current review entry point for the September 13 cleanup and runtime
changes. It links the exact verification record and preserves known limits.

## Evidence to start from

The
[September 12 configuration report](../verification/CONFIGURATION-AND-NATIVE-INITIALIZATION-2026-09-12.md)
records 70 real Tactical calls, 159/160 case checks in a forty-cell repair
matrix, and nine native Markdown controls. One case failed. These are
bounded component experiments, not a full-system benchmark or proof of
general configuration selection.

The
[September 12 architecture checkpoint](../research/COGNITIVE-STEP-ARCHITECTURE-AND-STATE-2026-09-12.md)
separates runtime mechanisms, failed live recovery, and unresolved Solution
delivery and learning. The earlier
[clean-installation checkpoint](../../artifacts/state-checkpoint-20260912-OtPgn5/README.md)
records 3,839/3,839 checks for its saved source. Later working-tree changes
need their own verification. No historical count establishes today's state.

The [preserved September 8 entry point](START-HERE-SNAPSHOT-2026-09-08.md)
is historical. Its hosted build status, counts, and publishing instructions
do not describe the current working tree.

## Safe local checks

Run these from the repository directory. Commands in this block do not change
the directory for the commands that follow.

```bash
cd /home/username/loop-engine
git status --short --branch
git rev-parse HEAD
git worktree list --porcelain
ps -eo pid=,ppid=,etime=,stat=,comm=

PYTHONPATH=src .venv/bin/python -m loop_engine --self-test
PYTHONPATH=src .venv/bin/python -m loop_engine --conformance
PYTHONPATH=src .venv/bin/python -m loop_engine --repo-conformance --format json

(
  cd examples/25_host_runtime
  PYTHONPATH=../../src ../../.venv/bin/python -m unittest discover -s . -p 'test_*.py'
)

PYTHONPATH=src:devtools .venv/bin/python -m unittest discover \
  -s devtools/embodiment_lab/tests -p 'test_*.py'
```

Start with the owning module's smallest relevant checks before the full
offline suite. Confirm that the repository environment exists before using
it. A clean installation means a fresh distribution installed outside the
source import path, not another run using `PYTHONPATH=src`.

Documentation has separate structure, prose, and terminology checks. See
[Invariants and traps](INVARIANTS-AND-TRAPS.md). Local tests do not establish
hosted continuous-integration status or real provider quality.

## Change and review rules

Add supported ways of running without silently removing another option.
An unavailable or unqualified option needs an explicit refusal and an honest
implementation status. Do not weaken contracts or refresh a failure baseline
to make a check pass.

Use [the component map](../components/README.md) to locate the authoritative
implementation. Keep immutable historical records, failed attempts, and
legacy readers when compatibility requires them. A copied repository, old
solution, or prior test result is not automatically active intelligence.

Finish a bounded change with checks for the behavior, relevant component
tests, conformance, and clean-installation evidence where needed. Name any
remaining required work. Do not claim the complete design works because a
small test passes. Commit and push verified changes to `main` in the same
turn, as the owner's standing instruction of 2026-09-02 requires; keep
another session's in-progress files out of your commit until ownership is
resolved. Do not invoke a provider or repeat an external effect unless the
current request authorizes that action.
