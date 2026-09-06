# Review work from an exported ticket

This example reads a local `exported_ticket/v1` record, stages the authored
JavaScript clamp project, and returns a diff with independently checked gate
results. It is a local integration fixture. It does not fetch Jira tickets,
schedule a night, alter an existing repository, push a branch, or update Jira.

## Inspect before running

From the source checkout with Loop Engine installed:

```bash
python examples/25_host_runtime/exported_ticket_pilot.py
```

The default prints the plan without creating a workspace, running commands,
discovering a provider, or making a model call. The supplied
[`exported-ticket.fixture.json`](exported-ticket.fixture.json) contains the
task and provenance, not permissions. The host separately fixes the editable
file, allowed effects, tests, and runtime image.

## Run the authored fixture

Use an existing configured model route with the exact model and source-backed
output capacity. Pull the pinned Node image described in the
[host example](README.md#run) before starting. The work directory must be new.

```bash
python examples/25_host_runtime/exported_ticket_pilot.py \
  --work-dir /absolute/new/ticket-pilot \
  --authorize-model-calls \
  --allow-source-to-model \
  --allow-workspace-writes \
  --allow-sandbox-commands
```

These flags authorize model disclosure, source replacement, and fixed sandbox
commands for this fixture. They do not approve publication or other projects.
The default route is `cloud.default`, model `deepseek-v4-flash:0731`; use
`--model-route` and `--model-id` together for another configured route.
The example imposes no call, pass, total-token, or monetary ceiling. Provider
capacity, runtime supervision, and container limits still apply.

Only `clamp.mjs` can be replaced. The host requires its current digest and
keeps the ticket, original source, package configuration, tests, and audit
program unchanged. Commands run in the pinned Node container with no network
and a read-only workspace. The primary repository suite and the additional
completion audit are distinct fixed gates. Ticket prose cannot change them.

## Review the result

The new work directory contains the staged project, frozen manifest, gate
observations, Run History, `review.diff`, and `review.json`. A report is
`REVIEW_READY` only when the solve succeeds and the current source has both
required passing gates. Otherwise it remains `UNVERIFIED_REVIEW`.

Reopen a report without starting a model:

```bash
python examples/25_host_runtime/exported_ticket_pilot.py \
  --inspect-report /absolute/existing/ticket-pilot
```

Inspection checks the report, source, diff, manifest, and gate identities.
Changed bytes invalidate the review. Apply any accepted diff through the
original repository's own review process; this example does not apply it.

## Evidence and next integration boundary

The example's unit tests use labeled injected command results. They cover
missing authority, stale source, changed protected files, malformed gate
output, incomplete reviews, and changed report artifacts. They are not model
performance evidence.

```bash
python -m unittest discover \
  -s examples/25_host_runtime -p test_exported_ticket_pilot.py
```

See the [current verification report](../../docs/verification/ADAPTIVE-COMPLETION-AND-PUBLICATION-2026-09-06.md)
for separately recorded real-container checks and remaining live tests.
A production Overnight adapter must supply its own isolated worktrees,
protected repository gates, ticket export policy, durable effect handling,
and morning review. Keep those policies in the host and use the same
[Loop embedding contract](../../docs/guides/embedding-loop-engine.md).
