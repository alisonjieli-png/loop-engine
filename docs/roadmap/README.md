# Roadmap

Kind: the plan a loop can walk.

`roadmap.yaml` is the machine-readable authority: requirements, the
component tree, and steps with their verification, adversarial check,
evidence, and status. The Markdown record beside it mirrors the plan for
readers and carries the dated status log. Statuses are proposed, ready,
building, offline_verified, live_qualified, published, blocked, and
superseded.

What does not belong here: results (see `../verification/`), design
decisions (see `../architecture/`), and research (see `../research/`).

Use the [delivery and business plan](DELIVERY-SEQUENCE.md) for the current
linear order, customer acceptance gates and supported distribution choices.
It points to existing roadmap steps rather than maintaining another status list.

Start with the [continuation and first-release plan](CONTINUATION-AND-LAUNCH.md)
and its [generated status artifact](CONTINUATION-STATUS.md). The continuation
track in `roadmap.yaml` takes precedence over the earlier list order and
retains every earlier initiative. Regenerate the status artifact with
`python tools/build_continuation_status.py`; `--check` detects a stale view.

The [development tracker](DEVELOPMENT-TRACKER.md) is the short view of the
same plan: recorded work in progress, what can start next, what is blocked,
what only the owner can do, the launch gates and the progress of every
delivery package. Its data file `development-tracker.json` feeds the tracker
page. Both are generated from `roadmap.yaml` by
`python tools/build_development_tracker.py`; `--check` detects a stale view.
Never edit either by hand, and never keep task state anywhere else.

The tracker also renders the ordered subtask checklist from each owning step's
`subtasks` and `continuation.execution_order`. Every subtask names its procedure,
dependencies, acceptance, evidence, comment and next action. Its completion
status is explicit: an offline check, a publication and live qualification do
not substitute for each other. Missing evidence, dependency cycles and a
completed subtask with an unfinished prerequisite fail generation. The JSON
view uses `development_tracker/v2`; no separate task database owns this state.

Both generated views use the same ordered subtask selection. The first task
whose required dependencies meet their declared completion scope is eligible
unless it is complete, blocked or superseded. The command
`python tools/build_continuation_status.py --next` returns that one identifier in
`subtasks`, or an empty list when no recorded subtask is eligible. It uses the
parent `launch` and `improvement` lists only when the roadmap has no subtasks;
blocked subtasks never trigger a parent fallback. Selection grants no effects.

Recorded statuses and planning windows are not live worker telemetry. A
`building` status does not establish that a process is running, and a planned
end time does not establish completion. Current worker ownership and operation
results belong in the coordination and evidence records.

The [fabric roadmap](FABRIC-ROADMAP-2026-09-18.md) preserves the earlier
requirements and status history.
