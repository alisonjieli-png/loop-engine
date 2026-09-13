# Review handoff for Claude Fable 5.1

Prepared on September 13, 2026 at the owner's request. This is a local,
hand-authored review guide, not a generated `session_handoff/v1` packet.
The preparing agent did not contact Claude Fable 5.1 or credit it with a
review. The owner subsequently reported arranging that review and clarified
that the configuration dimensions must extend beyond the original list.
Read the [dimension discovery addendum](CONFIGURATION-DIMENSION-DISCOVERY-ADDENDUM-2026-09-13.md)
alongside this handoff. No reviewer findings are assumed. The original archive
remains a fixed pre-clarification snapshot.

## Review scope and authority

Review the current Loop Engine implementation, the complete configuration
dimension requirement, and the legacy compatibility and documentation changes.
Start read-only. Identify concrete defects and the smallest reproduction for
each finding before proposing a change. Do not interpret old campaign plans
or this handoff as permission to call a provider, change shared files, publish,
or repeat an external effect.

The repository is `/home/username/loop-engine`, branch `main`, revision
`0cb7b86cb7f5b1f6a6b1b798da4e0a4a1469e00f`. The branch is one commit ahead of
its configured upstream at preparation time. The working directory contains
substantial preexisting tracked changes and untracked work. A diff against
the commit contains more than this cleanup. Other coding sessions and
background processes exist; their ownership is not inferred from names.
Recheck all of these facts before acting.

Read [AGENTS.md](../../AGENTS.md), the
[Architecture Constitution](../architecture/CONSTITUTION.md),
[architecture.yaml](../../architecture.yaml), and the
[complete configuration dimension requirement](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md).
The owner explicitly requires initial choices and ordered fallback priorities
for every dimension. Do not reduce the requirement to choosing a harness and
model, or describe a documented target as completed runtime behavior.

## Complete behavioral explanation

A discrete cognitive or act step Loop node is an independently governed
instance of the Loop runtime responsible for one clearly defined cognitive
step or action. A cognitive step might interpret information, identify a
missing requirement, compare alternatives, or evaluate a result. An action
might inspect a directory, build software, execute a test, create an artifact,
or send an authorized email.

Each discrete cognitive or act step Loop node receives the context,
instructions, skills, plugins, tools, and working files relevant to its
assignment. Essential information can be supplied directly, while additional
information can remain in centralized storage behind authorized, versioned
references. It does not automatically need the entire task history or every
available tool.

A separately initialized harness process, such as OpenCode, Pi, Codex, or a
custom implementation, can perform the assignment. When explicitly permitted,
another harness can attempt the same assignment after a failure. The
assignment's contracts, permissions, history, and remaining authority persist
across those attempts.

Discrete describes the scope of the assignment, not a restriction to one
attempt, one model call, or one output. A discrete cognitive or act step Loop
node can examine whether an observation matches its expectations, identify a
problem, repair or change its approach, and repeat until its declared
completion conditions are satisfied.

Alternatively, a discrete cognitive or act step Loop node can publish an
initial candidate output and continue working while its continuation
conditions and authority permit. It can produce additional alternatives over
time, including alternatives that are better, worse, or useful under different
circumstances. Consumers must identify exactly which output they used.
Publishing an output does not necessarily mean that the producing assignment
has finished.

For externally consequential actions, continued operation does not authorize
repeated effects. For example, generating alternative email drafts can
continue, but sending an email requires its own authorization and protection
against duplicate delivery.

That complete explanation must remain alongside the full phrase. A shorter
label alone is not an adequate replacement.

## Architecture to preserve

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

The canonical `Loop` remains the only executable runtime. Adapters and passive
configuration records are not graph vertices. There is no new runtime class
for the descriptive phrase. Independent review and candidate promotion remain
separate from execution, selection, scoring, and task acceptance.

## Current changes to inspect

| Area | Owning files | Scope and limitation |
|---|---|---|
| Reviewed-evidence initial selection | `core/harness_selection_records.py`, `core/harness_selection.py`, `core/harness_selection_checks.py` | Optional deterministic ranking inside the already registered harness set. Fixed model route and declared resource scope. No general configuration optimizer. |
| Response evaluation and permitted recovery | `core/harness_response_evaluation.py`, `core/harness_semantic.py`, `core/harness_fallback.py`, `code_nodes/solution_model_port.py`, `core/model_gateway.py` | Distinguishes structural admission, passed semantic checks, rejected checks, and inconclusive evaluation. Requires trusted host evaluator registration and explicit semantic-fallback permission. |
| Configuration loading | `core/harness_configuration.py` | Strict versioned policy loading and explicit programmatic registration. No automatic historical policy construction or command-line enablement. |
| Input cardinality and historical encodings | `loop/loop_contract.py`, `loop/loop_definition.py`, `loop/spawned_task_checkpoint.py`, their owning checks | Explicit per-input bounds; new definition and checkpoint encodings; exact historical read and round-trip behavior. No silent historical rewrite. |
| Architecture integration | `core/boundary_registry.py`, `architecture_map.py`, `_self_test.py`, root and packaged architecture and terminology files | Uses existing operational-boundary and test registries. New operations remain canonical Loops. |
| Authored-source conformance scope | `nomenclature_conformance.py`, `conformance_report.py`, `forbidden_paths.json` | Scans declared first-party source and documentation, including untracked work. Excludes exact installed dependency roots and pinned reference snapshots rather than walking millions of third-party files. No increased failure baseline. |
| Required configuration dimensions | `docs/architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md`, `architecture.yaml`, agent entry points, `devtools/embodiment_lab/tests/test_configuration_dimensions.py` | Records 25 separate dimensions and their common initial-choice and fallback requirements. Explicitly marked partially implemented. |

Source paths in the table are relative to `src/loop_engine` unless a different
repository-relative path is shown. Read the
[harness selection, evaluation, and recovery guide](../components/core-architecture/HARNESS-FALLBACK.md)
and [record compatibility guide](../components/loop-object/RECORD-COMPATIBILITY.md)
before reviewing those boundaries.

The source baseline before these runtime changes is retained in
`.loop-engine-dev/step-adaptation-20260913-ziLjPa/starting-source.zip`, with
`starting-state.json`. It contains 573 scoped files. The review bundle
includes a source comparison against that baseline where the baseline has
coverage. It does not attribute unrelated dirty changes to this cleanup.

## Current context versus historical material

| Location | Treatment for this review |
|---|---|
| `src/loop_engine`, root contracts, and component guides | Current first-party implementation and authority. Inspect the working-tree bytes, not only the last commit. |
| `devtools/embodiment_lab` and authored files in `embodiments` | Active experiments and explicitly registered adapters. Experimental qualification is narrower than product support. Do not delete them as legacy merely because they are untracked. |
| Installed `embodiments/*/runtime` dependencies and exact pinned `mirrors` snapshots | External implementation or reference material. Not first-party source and not automatically active intelligence. Preserve provenance; do not bulk-import or recursively reformat them. |
| `integrations` | Thin maintained host adapters. Sixteen tracked files at preparation time; not a second Loop runtime. |
| `kaggle`, `benchmarks`, `case-studies`, and `artifacts` | Examples, frozen populations, and dated evidence with different qualification levels. A saved candidate or a local score is not a promoted Solution or an unseen-task result. |
| `checkpoints` | Six tracked historical files. Preserve immutable reports. Its legacy helper is not a current trustworthy snapshot writer. |
| `docs/context/START-HERE-SNAPSHOT-2026-09-08.md` and dated reports | Historical context, with current corrections linked from `START-HERE.md`. Old publication instructions and counts are not current authority. |
| Copied older repositories and work directories | Ownership unresolved. No bulk migration, deletion, or merging. Consult `REFERENCE-SOURCES.md` before using a specific design invariant. |
| `graphify-out/cache/stat-index.json` | One tracked generated cache identified during inventory. Ownership and consumers were not resolved; it was not deleted. |

The cleanup corrected the current entry points, the withdrawn campaign
conclusion, the overbroad OpenCode quarantine wording, and the intelligence
record paths. It retained the original September 8 entry point and marked
the early September 12 vision review as superseded. Existing historical
Run History, benchmark artifacts, and managed records were not rewritten.

## Verification

The [review evidence directory](../../artifacts/fable-review-20260913-p75Wml/README.md)
contains the final check summary, scoped source manifest, and review bundle.
The original working evidence is in
`.loop-engine-dev/step-adaptation-20260913-ziLjPa/`.

The final source suite passed 3,940/3,940 and the fresh Python 3.10 installation
passed 3,905/3,905 against the corrected contract projections. The focused
runtime checks passed 175/175 and the experiment and documentation suite
passed 39/39. The source environment exercised installed optional adapters;
the clean installation did not install all optional integrations. Neither
result establishes hosted continuous-integration status or live model quality.
Use the evidence directory's generated summary for commands, conformance,
source identities, and documentation checks. Earlier attempts remain separate:

- The first package-source copy omitted `runtime/runs/README.md` through an
  overly broad copy exclusion. Its installed suite passed 3,903/3,905 and
  failed the two expected folder-presence checks. The corrected copy preserves
  the authored folder and excludes only exact local evidence locations.
- The corrected package passed 3,905/3,905 and 27/27 conformance gates, but
  still contained a stale terminology projection. The subsequent source suite
  caught that mismatch, passing 3,939/3,940. The missing projection entries
  were synchronized from the authority file before the final reruns.
- The first targeted-check exporter assumed every component returned the same
  report shape. It failed on a list-shaped checkpoint report. The corrected
  exporter retained all 175/175 component results without changing tests.
- An earlier conformance process was interrupted after it entered an installed
  third-party dependency cache. The replacement scan scope is explicit and
  covered by positive and unsafe-path controls.

These are offline checks. No new live Tactical call qualified the new
selection and semantic-recovery implementation. The separate
[70-call configuration report](../verification/CONFIGURATION-AND-NATIVE-INITIALIZATION-2026-09-12.md)
predates those changes. It remains bounded live evidence, not a full-system
benchmark or a learned selection policy.

## Priority review questions

1. Can selection be influenced by unmatched evidence, stale versions, different
   evaluators, unequal population coverage, duplicate trials, or unknown
   measurements? Check the host-attestation boundary. Typed digests and a
   different reviewer label do not independently authenticate a trial.
2. Is every evaluator bound to the actual input-dependent obligation? The
   current trusted callback receives admitted response text. Its subject
   contract and occurrence are recorded, but its expected answer can still
   be incorrectly supplied by the host. Test wrong-task and stale-oracle cases.
3. Do semantic rejection and inconclusive evaluation preserve physical usage,
   remaining deadlines, failure history, exact effect restrictions, and
   registration identity across every attempted harness?
4. Does every allowed historical encoding retain its exact digest and meaning?
   Challenge malformed cardinalities, unsupported versions, multiple input
   ports, changed adapters, and record tampering. Do not weaken the reader to
   make a fabricated historical record load.
5. Does each of the 25 dimensions have an actual owning typed contract,
   initialization path, fallback trigger, compatibility check, and qualified
   observation? Name missing pieces rather than inventing a new central
   configuration store or a second runtime.
6. Are native tools, skills, plugins, hooks, instruction loading, process reuse,
   cancellation, and containment supported by real tests for the exact
   adapter? Brokered text and a Markdown-loading control do not prove those
   mechanisms collectively work.
7. Revisit `core/verifier_execute.py`. Its raw-host subprocess path has not
   been qualified as an untrusted-code sandbox. Process descendants and output
   capture need specific review. Do not use it to justify a containment claim.
8. Keep the old campaign and solution evidence qualified. The original novel
   task report has prompt-and-case contradictions and an inconsistent audit;
   its 10 percent false-acceptance claim was withdrawn. The legacy task
   campaign tooling also needs attempt-retention and evaluator-leakage review.
9. Review `tools/make_checkpoint.py` against the defects documented in
   [the checkpoint guide](../../checkpoints/README.md). Do not run it as a
   trusted writer or overwrite old checkpoints to conceal missing records.
10. Distinguish local mechanism tests from live task quality, continued
    alternative-output production, portable Solution graph replay, and
    independent cross-task learning. The latter capabilities are not
    established by this cleanup.

Report observed defects separately from inferred risks and missing proof.
For each finding, name the source location, exact input or condition,
expected behavior, observed behavior, and a regression check. A proposed
fix remains a candidate until independently reviewed and verified through
Loop Engine.
