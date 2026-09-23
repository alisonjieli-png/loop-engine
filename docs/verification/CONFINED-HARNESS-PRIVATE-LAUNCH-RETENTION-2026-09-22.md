# Confined harness private launch retention

Kind: bounded offline verification finding. Checked September 22, 2026.
This is evidence for S-6.8 and the existing D-07 and D-13 workspace work in
the [roadmap](../roadmap/roadmap.yaml). The fixture used a disposable
temporary directory, a local fake model broker, no customer credential and
no network or real provider call. It changed no repository source file.

## Observation

The fixture made one [confined harness process](../../src/loop_engine/core/harness_process.py)
request with the installed test command from
[harness process checks](../../src/loop_engine/core/harness_process_checks.py).
It returned `result_ok=True`, `broker_calls=1`. After the call returned, one
`harness-*` directory remained under the declared `work_dir`. It held:

| Relative file | Mode | Observed content class |
|---|---|---|
| `config.json` | `0600` | Model and process configuration, no fixture prompt canary. |
| `task.txt` | `0600` | The private fixture prompt canary. |

The outer fixture's `TemporaryDirectory` removed these bytes when the
verification ended. A separate source and fixture audit also found retained
instruction material and the same run-directory retention after refused and
timed-out runs; this report's directly repeated positive run establishes
success-path retention. Source creates the run directory and private inputs
at [lines 360 to 373](../../src/loop_engine/core/harness_process.py) and
returns without removing it at the end of that function. The broker socket
has a separate temporary-directory lifetime.

This is an **unqualified retention behavior**, not proof that the file
contents leaked to another user. Keeping a task working folder across
attempts is an owner requirement. The open question is whether these private
launch-control files have a declared lifetime, scope and cleanup or resume
purpose. File mode `0600` does not decide that product policy, and repeated
runs can leave additional copies.

## Discriminating next check

Before claiming an ephemeral per-step sandbox, define which bytes are task
materials, retained candidate outputs, immutable Run History, and private
launch-control files. Preserve the first three under their existing
contracts. For success, refused model request, timeout and broker exception,
record the exact post-run state that the chosen retention policy permits.
A known-wrong control should keep an undeclared `task.txt` containing a
private canary and fail; a cleanup implementation that deletes an approved
task artifact should also fail. Test restart and permitted resume separately
before deleting any file needed for that behavior. S-6.8 should bind the
policy to the process lifetime and S-6.24 should explain customer workspace
retention during setup.
