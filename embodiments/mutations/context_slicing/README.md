# context slicing

Status: `planned`.

Compare delivered context, omissions, latency and downstream correctness, using the same model and task.

Declared arms: `bounded_push`, `horizons`, `scoped_pull_on_miss`.

The manifest describes the experiment; it does not grant authority or silently change a run. Preserve the population, evaluator and non-target axes. Report failed, cancelled and unavailable arms with their exact denominators. Results from the trusted deterministic backend establish mechanics only.

See [mutation policy](../README.md) and [embodiment catalog](../../README.md).
