# Bounded local overnight queue

This operator invokes the existing `loop-engine solve` command once for each
selected task. It reserves each child's full call allocation before dispatch,
keeps the original queue deadline across restarts and holds uncertain outcomes
for explicit reconciliation. It does not restore provider reasoning or promise
that a task finishes successfully.

## Prerequisites

Install the repository in a Python virtual environment. The queue and morning
report are repository tools, so keep the checkout:

```bash
git clone https://github.com/alisonjieli-png/loop-engine.git
cd loop-engine
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

Configure your model access using [providers and keys](../docs/guides/providers-and-keys.md)
or [custom endpoints](../docs/guides/custom-endpoints.md). Ollama Cloud uses your
existing account; running the queue locally does not require downloading a model.
Inspect the supported settings and credential references without a provider call:

```bash
.venv/bin/python -m loop_engine configure
.venv/bin/python tools/overnight_queue.py --help
```

Use a fixed reviewed checkout, a supported configured model provider and the
existing effect authority. Keep task files and the manifest unchanged during a
queue. Use a fresh, private runs directory for a newly authorized run. A new
directory does not renew a previous run's provider or spending allowance.

The call budget limits invocations, not tokens or money. The Ollama route still
needs a qualified token preflight before a run can claim a strict token ceiling.
No real model execution is established by the queue's offline tests.

## Start and inspect

The manifest contains one absolute task-file path per line. Blank lines and
lines beginning with `#` are ignored. Missing or duplicate tasks refuse before
dispatch. Create each task file with the objective, permitted inputs and the
checks that determine success. Start with one short task before leaving a
long queue unattended. From the reviewed repository root:

```bash
PYTHONPATH=src .venv/bin/python tools/overnight_queue.py /path/to/tasks.txt \
  --runs-dir /path/to/new-private-runs \
  --workspace-root /path/to/private-workspaces \
  --max-calls-per-task 12 --queue-call-budget 24 \
  --task-timeout 600 --grace-seconds 30 --queue-timeout 3600
```

The example's limits are operator-selected allocations, not provider capacities.
After two full 12-call reservations, no third child can start. If only five
calls remain, the next child receives at most five. Unused reservations are
not refunded because the operator does not have complete provider usage.

Repeat the exact invocation with `--status` to inspect state without dispatch.
All original task paths, bytes and limits must match. A plain repeat skips
finished tasks and can continue only while the original deadline and allowance
permit it. Historical, malformed or missing state with existing artifacts
refuses; `--fresh` always refuses.

## Interrupted and unknown work

A reservation is fsynced before the child starts. Local POSIX locking prevents
another queue writer, including while a child retains the inherited lock after
its supervisor dies. Timeout handling signals the owned process group, allows
the declared checkpoint grace period, then kills remaining owned processes.
This local mechanism is not distributed worker fencing.

An interrupted, failed or unrecorded child retains its full allocation. The
queue holds before further dispatch. Inspect provider records, external effects,
the owned child and retained artifacts. Prepare a
`overnight_queue_reconciliation/v1` record containing the exact binding digest,
attempt ID, `retry` or `retire` action, evidence path and SHA-256, external
outcome and the operator confirmation required by
`overnight_queue_state.validate_reconciliation`.

Use the exact original arguments plus `--reconcile RECORD_PATH
--authorize-reconcile`. That invocation checks the evidence and changes only
the queue record; it starts no child and refunds no allocation. A later exact
invocation may retry if authority, time and remaining allowance permit it.
Never repair a corrupt state file by replacing its counters manually.

## Reports and checks

`tools/morning_report.py` reads the v2 attempt projection. Reserved or unknown
attempts are HELD. A finished process still needs independent artifact checks.
Checkpoint summaries do not claim digest verification or provider usage.

```bash
PYTHONPATH=src:tools python3 -m unittest \
  tools.test_overnight_queue tools.test_overnight_queue_state
```

The controls cover remaining allocation, pre-dispatch durability, corrupt and
historical state, changed task bytes and limits, unknown outcomes, child-held
locks, explicit reconciliation, deadlines and owned-process cleanup.
