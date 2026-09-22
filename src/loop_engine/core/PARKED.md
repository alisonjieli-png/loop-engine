# Parked: the in-process Loop-native execution capability

This folder holds modules of the in-process Loop-native execution path.

1. **What this was.** The in-process solving engine and its supporting machinery: the adaptive practitioner family, the stage and planning machinery, the model campaign and generation clients, the reasoning calls, the evaluation and optimization suites, the Kagale executor support, and the studio server. The serving path, the harness adapters, the catalogue, the provisioning, the accounts, the billing and the records machinery stay live.
2. **The decision.** Owner direction, September 21, 2026: the main line is
   streamlined to harness intelligence, and every executable step delegates to
   a standard harness (OpenCode, Codex, Claude Code, and others) through the
   existing adapter contracts. Recorded in
   `docs/architecture/ADR-HARNESS-FIRST-SERVING-AND-EXECUTION.md` and roadmap
   step S-6.28.
3. **Last working revision on this branch.** `a3bd0f1`, where the full
   self-test passed 6229 of 6229 checks with these suites collected.
4. **Where the working implementation is frozen.**
   `checkpoint/full-capability-2026-09-21`, revision `a3bd0f1`. The
   checkpoint branch keeps passing every suite this branch retired.
5. **How it turns on again.** Not a merge. A recorded owner decision, when a
   large number of users justify a custom engine of our own, implemented
   behind the typed executor interface phase 2 of the decision record creates,
   or restored from the checkpoint branch through the boundary the decision
   record names. The parked suites are registered in
   `suite_collection_exceptions` in `src/loop_engine/forbidden_paths.json`,
   so the "suite never silently shrinks" gate proves the retirement is
   deliberate.

The modules stay in place for now; phase 3 of the decision record removes
them from the main line once the delegated path carries the same guarantees.
Until then they are not collected by the self-test on this branch and are
not part of the serving path.
