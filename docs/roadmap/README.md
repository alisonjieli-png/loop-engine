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

The [fabric roadmap](FABRIC-ROADMAP-2026-09-18.md) preserves the earlier
requirements and status history.
