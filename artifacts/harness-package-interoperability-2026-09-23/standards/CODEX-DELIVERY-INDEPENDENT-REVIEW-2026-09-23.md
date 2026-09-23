# Independent review of the Codex delivery probe

Reviewer: Codex standards research agent, independently assigned after the
probe and first result were written. Date: September 23, 2026.

## Scope and identity

Reviewed source: `probe_codex_delivery.py`, SHA-256
`94a915f758acde88f84c87b207b52c83f34a4c7e06b4cb8cc7ab4d682f71c8a2`.
Reviewed initial report: `codex-delivery-20260923T134822.json`.
Client: `codex-cli 0.155.1`. Source packet manifest SHA-256:
`e2a2d63911daddc495cef76fa20763aab70acef6a44a6507e6591914158ab8d2`.

The reviewed source was not modified. The reviewer reran it with its output
directory redirected into this review folder and retained the seven native
debug outputs and standard-error messages. No model execution command was
requested. Closed proxy settings were used, as in the author probe; these are
not operating-system network isolation or independently measured network
accounting.

## Findings

**The seven observations reproduce.** Their marker classifications match the
initial report. Every copied project file remained unchanged during this
rerun. Native output is a list of input messages. Inspection confirmed that
the assignment and canary matches occur in user instruction/input text, rather
than merely in filenames or unrelated metadata.

| Control | Independently observed | Interpretation limit |
|---|---|---|
| Native instruction entrypoint | Objective, first action, state identity and output-contract reference appear. | Prompt construction only. No task or output was evaluated. |
| Override file | Override canary appears; all four assignment markers disappear. | Applies to this exact file placement and client version. |
| Pointer-only instruction | All four assignment markers disappear despite auxiliary files remaining. | It does not prove a running model cannot subsequently read those files. |
| Oversized ancestor instruction | Ancestor canary appears; all four step markers disappear. | Demonstrates the combined instruction-budget risk in this setup. |
| Explicit launch input without entrypoint | All four supplied markers appear. | Deliberately tests delivery, not authorization or resolution of conflicting instructions. |
| Reduced instruction budget | Objective appears; first action, state identity and contract reference disappear. | The script's predicate only requires the objective to survive and state identity to disappear; the saved data supports the stronger observed result. |
| Installed skill metadata | Skill description appears; skill body and unrelated Python-file canaries do not. | Discovery is different from activation. An absent file-body canary does not alone prove tool-registration absence. |

All seven standard-error messages warn that helper PATH aliases cannot be
created when the configured home is under `/tmp`. The debug commands still
exit successfully and emit the expected input messages. This warning should
remain attached to the evidence. No script or helper invocation was tested.

## Initial probe hardening findings

These issues do not change the seven observed results, but matter if the
probe is reused as an automated qualification gate:

1. `control_observed` does not incorporate `workspace_unchanged`. The report
   records unchanged files, but a future mutation could coexist with a passing
   control. The author has been asked to include this predicate.
2. The initial source check trusts a colocated manifest and checks only its
   listed files. It does not independently establish the expected manifest
   identity, reject extra files or refuse symlink substitutions. Reuse the
   packet renderer's externally bound verification rather than promoting this
   loop into another production verifier.
3. Project snapshots cover regular file contents under the synthetic project.
   They do not cover permissions, directories, configured home changes,
   system-wide policy or all filesystem writes. State the narrower scope.
4. The source fixture is outside the copied package; its markers were not
   independently bound by the initial probe. A host-held expected fixture and
   manifest binding should qualify both before probing.
5. The `model_calls: 0` field is an assertion based on the selected debug
   command, not a count measured at a provider transport. These observations
   establish constructed input, not a native running session, provider
   integration or acceptance. Separate operating-system process starts should
   not be described as proof of fresh conversation execution.

## Native schema observation

The reviewer independently ran `codex app-server generate-json-schema` in a
temporary configuration. All four schema digests exactly match the author's
record. The recorded properties and required fields match too. No represented
application-server method was invoked.

The initial record's `input_definition: {}` is not evidence that turn input has
no schema. `TurnStartParams.input` is an array referring to
`#/definitions/UserInput`. The review retains the complete generated schema
and that property in `schema-review.json`. Any claim about permitted input
variants must inspect that definition separately.

## Saved review material

- [Independent rerun](independent-codex-review/codex-delivery-20260923T135218.json)
- [Captured command summaries](independent-codex-review/captured-runs.json)
- [Native schema comparison](independent-codex-review/schema-review.json)
- [Complete turn schema](independent-codex-review/TurnStartParams.json)
- Seven `prompt-output-*.json` files and seven `stderr-*.txt` files in the same
  directory preserve the actual inspected debug output.

Outcome: adequate evidence for the narrowly stated input-construction
findings. This review does not approve the task packet for production or
qualify a native task execution.
