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

Start with the [continuation and first-release plan](CONTINUATION-AND-LAUNCH.md)
and its [generated status artifact](CONTINUATION-STATUS.md). The continuation
track in `roadmap.yaml` takes precedence over the earlier list order and
retains every earlier initiative. Regenerate the status artifact with
`python tools/build_continuation_status.py`; `--check` detects a stale view.

The [development tracker](DEVELOPMENT-TRACKER.md) is the short view of the
same plan: what is being built now, what can start next, what is blocked,
what only the owner can do, the launch gates and the progress of every
delivery package. Its data file `development-tracker.json` feeds the tracker
page. Both are generated from `roadmap.yaml` by
`python tools/build_development_tracker.py`; `--check` detects a stale view.
Never edit either by hand, and never keep task state anywhere else.

The [fabric roadmap](FABRIC-ROADMAP-2026-09-18.md) preserves the earlier
requirements and status history.
