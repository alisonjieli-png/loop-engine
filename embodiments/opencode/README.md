# OpenCode harness configuration

This directory holds an explicitly selected OpenCode `harness.json` and its
local runtime. Inspect that exact configuration and the
[OpenCode recipe](../../src/loop_engine/core/harness_opencode_recipe.py)
before making a capability or initialization claim. A different OpenCode
integration can have different qualified behavior.

Read [the harness development instructions](../AGENTS.md),
[ASTRA.md](../../ASTRA.md), and
[the layered harness design](../../docs/architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md).
An outer Loop Engine Loop may supervise native harness iteration. Wrapper
composition, native controls, prompts, resources, and fallback policies are
independent choices rather than one fixed stack.

The owning Loop preserves the assignment, remaining authority, cancellation,
Run History, and independent acceptance. Native completion does not by itself
accept the task. Do not turn a development instruction into an automatic
native-tool grant or change a pinned runtime to make a test pass.

See [the harness guide](../HARNESS-GUIDE.md) for shared integration and evidence
boundaries. This page adds documentation only; it does not change the manifest
or qualify a new native-control profile.
