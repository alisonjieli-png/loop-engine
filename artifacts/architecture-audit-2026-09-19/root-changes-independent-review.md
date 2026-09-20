# Independent review of the current root changes

Review date: 2026-09-19. Reviewer: the independent capability and delivery agent.
Source snapshot recorded at 2026-09-19T16:00:28Z. Branch: `main`. Base revision:
`48cc954322691e492aad69a465ba470a112730e7`.

## Result and limits

Seven independently reproduced defects were reported to the implementing agent.
All seven now reject the original bad case or preserve the originally lost fact.
The highest-risk defect allowed an undeclared external test directory to enter
authorized export verification through a symbolic link. Its recheck now refuses
the link before either execution callback runs.

This is a focused review of an uncommitted, concurrently changing tree, not a
release qualification. The source hashes below identify the closing inspection,
not the earlier failing intermediate bytes. Earlier baseline observations are
preserved below rather than rewritten as successes. The source snapshots of
those intermediate root changes were not separately saved or hashed. Existing
historical audit artifacts were not changed by this review.

No provider call, cloud change, deployment, image publication, commit, or push was
made. The acceptance fixture used scripted answers and an injected project
executor. Export bypass checks mocked the execution callback. The local harness
qualification used a synthetic local broker and a disposable operating-system
sandbox. It did not contact an external model provider.

The real harness still has no observed instruction-loading qualification. The
patch correctly distinguishes placing instruction bytes in the sandbox from a
native client reading and following them. The Pi recipe still disables native
context-file loading. That is a documented, deliberately restricted profile,
not a failure the reviewer asked to bypass.

## Findings and independent rechecks

| Identifier | Priority | Reproduced baseline | Current recheck and owner |
| --- | --- | --- | --- |
| RR-01 | Critical | A valid, approved export without tests acquired an undeclared `tests` symbolic link to an outside directory. The manifest stayed unchanged. The verifier returned success and called both import and test-discovery execution callbacks. | `solution_export.verify_export` rejects the directory symbolic link before any callback. The root now checks both execution-visible directory roots and every entry, and requires all regular files there to be declared. Owning export checks: 21/21. |
| RR-02 | High | A frozen `NodeAssignment` retained a caller-owned list of effects. Appending `writes_fs` after validating a `reason` assignment changed its effective instruction authority. | The constructor copies sequence fields to tuples, validates their members, and requires Boolean model authority. The caller list can change without changing the assignment. Default model authority is false. Owning checks: 14/14. |
| RR-03 | High | A progress listener could rewrite the started event's occurrence identifier. The producer then used the rewritten identity for completion, while the collector had already retained the original identity. The call appeared incomplete. | `AdaptiveRunServices.publish` forwards a deep copy. The producer retains `fixture:model-step:1`; the matched record is completed even when the listener rewrites its copy. |
| RR-04 | High | A result marked solved with an old passing independent report and a newer failing report was labeled `verified`. The label was based on any passing report, not the accepted incumbent. | `outcome_label` now requires the exact accepted-incumbent verification digest, subject, selected result, and unchanged passing independent report. The conflicting old-pass/current-fail fixture now labels `unknown`. A positive exact-binding fixture passes in the owning suite. |
| RR-05 | Medium | A synthetic private-body marker supplied as `prompt_digest` survived into report items even though the report said `bodies_retained=false`. This was a malformed-input privacy bypass, not a demonstrated normal-producer prompt leak. | Malformed nonempty digest metadata is removed and marked invalid. The report is incomplete, counts the invalid event, and training export excludes it even with incomplete and unverified exports enabled. The marker is absent from retained events and report items. |
| RR-06 | Medium | A deviation event was retained but its problems were discarded; the join then produced the same empty deviation information as a call with no deviation. | The collector retains a numeric deviation count without diagnostic prose. A two-problem fixture yields `deviation_count=2`, empty `deviation_problems`, and no private marker in retained data. |
| RR-07 | Medium | The normal started-event producer counted Unicode characters as prompt bytes. A provider-free successful fixture produced seven affected calls; examples were 88,832 reported versus 88,854 UTF-8 bytes, and 94,559 versus 94,576. | The producer counts UTF-8 bytes. The same fixture emits seven events whose counts all equal their UTF-8 lengths. In the closing run, the first event reports 88,861 bytes for 88,839 characters. |

Exact current owning locations include:

- `src/loop_engine/code_nodes/solution_export.py`: `ExportVerificationPolicy`, `_export_file`, `verify_export`.
- `src/loop_engine/core/node_provisioning.py`: `NodeAssignment.__post_init__`.
- `src/loop_engine/core/adaptive_practitioner_records.py`: `AdaptiveRunServices.publish` and the started-event metadata in semantic execution.
- `src/loop_engine/core/model_call_records.py`: `outcome_label`, `learning_records`, `export_training_rows`.
- `src/loop_engine/core/model_call_collection.py`: `LearningEventCollector.__call__` and `report`.

### RR-01 safe reproducer

Run from the repository with `.venv/bin/python`. The only files created are in a
temporary directory. The callback is mocked, so no outside test code executes.
On the failing intermediate source, the return was successful and the callback
count was two. On the corrected source, the exception names the symbolic link
and the callback count is zero.

```python
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch
from loop_engine.code_nodes.solution_export import (
    ExportedFile, ExportVerificationPolicy, SolutionExportError,
    SolutionExportSpec, export_solution, verify_export,
)

with tempfile.TemporaryDirectory(prefix="export-link-review-") as folder:
    base = Path(folder)
    target = base / "export"
    record = export_solution(SolutionExportSpec(
        "audit_pkg", "1.0.0", "Safe review fixture",
        (ExportedFile("__init__.py", "pass\n"),)), str(target))
    outside = base / "outside-tests"
    outside.mkdir()
    (outside / "test_marker.py").write_text("pass\n", encoding="utf-8")
    (target / "tests").symlink_to(outside, target_is_directory=True)
    with patch("loop_engine.code_nodes.solution_export._run_isolated",
               return_value=subprocess.CompletedProcess(
                   [], 0, stdout="ok\n", stderr="")) as runner:
        try:
            result = verify_export(str(target), policy=ExportVerificationPolicy(
                True, record.manifest_digest))
            print({"passed": result.passed, "callbacks": runner.call_count})
        except SolutionExportError as error:
            print({"refused": str(error), "callbacks": runner.call_count})
```

Closing result: `symbolic link refused in exported path 'tests'`; zero callbacks.

### RR-02 mutation control

The minimal discriminating construction is:

```python
from loop_engine.core.node_provisioning import NodeAssignment
effects = ["reads_fs"]
assignment = NodeAssignment("fixture", "reason", "Read a fixture", effects=effects)
effects.append("writes_fs")
assert assignment.effects == ("reads_fs",)
assert assignment.model_calls_authorized is False
```

The baseline also provisioned this assignment against an empty harness catalogue
inside a temporary directory and observed the unwanted write permission in the
instruction file. The fixed constructor prevents that mutation before
provisioning. This establishes immutability of these supplied sequence fields;
it is not independent admission of any catalogue resource.

### RR-03 callback identity control

The unbound `publish` method can be exercised without a provider or full run:

```python
import time
from itertools import count
from types import SimpleNamespace
from loop_engine.core.adaptive_practitioner_records import AdaptiveRunServices
from loop_engine.core.model_call_collection import LearningEventCollector
from loop_engine.core.model_call_records import STARTED, COMPLETED

def listener(event):
    if event.get("event_type") == STARTED:
        event["model_call_occurrence_id"] = "listener-rewritten"

collector = LearningEventCollector(forward_to=listener)
service = SimpleNamespace(
    progress_sequence_source=count(1), progress_sequence=0, run_id="fixture",
    context_owner_loop_id="owner", active_pass_number=1, model_session=None,
    source_inspections=[], project_attempts=[], started_monotonic=time.monotonic(),
    dependencies=SimpleNamespace(progress=collector))
started = AdaptiveRunServices.publish(service, STARTED, step="route")
AdaptiveRunServices.publish(service, COMPLETED, step="route",
    model_call_occurrence_id=started["model_call_occurrence_id"],
    output_digest="a" * 64, output_bytes=1)
assert started["model_call_occurrence_id"] == "fixture:model-step:1"
assert collector.records()[0].completed is True
```

### RR-04 through RR-06 discriminating inputs

The stale-outcome control deliberately has no exact incumbent binding:

```python
from loop_engine.core.model_call_records import outcome_label
assert outcome_label({
    "solved": True,
    "independent_verification_records": [
        {"status": "passed", "subject_digest": "old"},
        {"status": "failed", "subject_digest": "current"}],
}) == "unknown"
```

The label is a projection of a valid run result, not cryptographic authentication
of an arbitrary caller-created dictionary. The current producer's
`state_evidence.accepted_incumbent`, verification record, evaluation index, and
independent-check report structure were inspected and match the join.

For malformed metadata, start a collector event with a run identifier, step,
positive model-call number, and `prompt_digest="SYNTHETIC_PRIVATE_BODY"`.
The discriminating conditions are marker absence, `complete=false`,
`invalid_metadata_events=1`, and exclusion reason `invalid_metadata` from
`export_training_rows` under an otherwise permissive policy.

For deviation preservation, start one valid call, then add a matching
`model.step.suggested_output_deviation` event with two distinct synthetic problem
strings. Require count two, no retained problem strings, and no strings in the
serialized report. These checks distinguish preserving the fact of a deviation
from retaining its potentially private diagnostic text.

### RR-07 normal-path Unicode control

This uses an existing deterministic fixture, not an external model:

```python
import tempfile
from unittest.mock import patch
from loop_engine.core.adaptive_practitioner_acceptance_checks import (
    _run, _success_answers,
)
from loop_engine.core.adaptive_practitioner_records import AdaptiveRunServices
from loop_engine.core.model_call_records import STARTED

original = AdaptiveRunServices.publish
observed = []
def observe(self, event_type, **fields):
    if event_type == STARTED and isinstance(fields.get("prompt_text"), str):
        body = fields["prompt_text"]
        observed.append((fields.get("prompt_bytes"), len(body.encode("utf-8"))))
    return original(self, event_type, **fields)

with tempfile.TemporaryDirectory(prefix="unicode-review-") as folder:
    with patch.object(AdaptiveRunServices, "publish", observe):
        result = _run("Create a verified result for café and 東京.",
                      _success_answers(), folder)
assert result["solved"] is True
assert len(observed) == 7
assert all(reported == actual for reported, actual in observed)
```

Only lengths were printed or saved by the independent probe. The fixture's
temporary run artifacts were automatically removed.

## Other reviewed boundaries

### Instruction material and native loading

`InstanceInstructionWriter.material_for` verifies staged bytes and returns typed
`InstructionMaterial`. `HarnessProcessRequest` validates those records, names,
and size bounds. `run_harness_process` stages them in the real execution working
directory, and the sandbox exposes them read-only under `/work`.
`GatewayHarnessProcessAdapter` returns the instruction manifest and explicitly
reports `instruction_loading_observed=false`.

The local qualification fixture read `AGENTS.md` itself and verified the sandbox
placement, read-only behavior, cancellation, and restricted host exposure. It
does not qualify Pi or another real client. The Pi command in
`harness_process_relay._recipe` includes `--no-context-files`. A later loading
profile needs an explicit setting, exact native command and client version,
bounded authority, and an observed client-loading check. No qualification claim
should be inferred from the file manifest alone.

### Export authority

Verification defaults to static checks without execution. Executing a trusted
local export requires `ExportVerificationPolicy` with an explicit true flag and
the exact reviewed manifest digest. The command-line parser carries
`--export-manifest-digest`; `run_solution_export` passes it to that policy.
Unsupported manifest versions are refused. Interpreter isolation is explicitly
not described as an operating-system sandbox. The reviewed export API is not a
safe arbitrary untrusted-code execution service. This review did not prove
race-free operation against a concurrent hostile filesystem writer.

### Refactor equivalence

Before the subsequent intentional current-only import cleanup, abstract-syntax
comparison against the base revision found the nine extracted observation
helpers unchanged: `_stage_for`, `_stage_degraded`, `_stage_event`,
`_observe_stage`, `_grade_stage`, `_record_stage_execution`,
`_observed_response_shape`, `_record_stage_packet_exposure`, and
`_record_stage_assistance_decision`. `ADAPTIVE_CAPABILITIES` was also unchanged.
A symbol-table check found no unresolved extracted global reference outside
builtins. The three extracted export-template string values were byte-equal to
their prior values. These are bounded equivalence checks, not proof that the
preexisting behavior was correct.

The latest owner direction removes the need to retain forwarding imports.
Current-only imports are appropriate; interface-version and capability
handshakes must remain. This review does not defend a facade merely because it
was present before extraction.

### Public solve provisioning

The reviewed provisioning catalogue is passive Harness Intelligence reference
distribution, not proof of executable Code Intelligence admission. A resource
tag, retrieval result, or offered reference cannot grant execution, promotion,
or model authority. The other implementation agent is now changing public
solve provisioning and exact configuration binding. Those later changes need
their own closing tests and source hashes; they are not covered by this earlier
`solve_runtime.py` hash.

## Executed checks

The closing owning-module run had these actual test-row counts:

| Owning module | Passed / executed |
| --- | --- |
| `core.node_provisioning` | 14 / 14 |
| `core.model_call_records` | 10 / 10 |
| `core.model_call_collection` | 8 / 8 |
| `core.instance_instructions` | 9 / 9 |
| `core.harness_semantic` | 22 / 22 |
| `core.harness_process_checks.self_test` | 11 / 11 |
| `code_nodes.solution_export` | 21 / 21 |
| `code_nodes.solve_runtime` | 19 / 19 |

`solve_runtime.self_test` supplies a `tests` array without aggregate fields; the
19/19 count comes from its actual Boolean rows, not missing aggregate defaults.
The separately executed local
`harness_process_checks.qualification_checks` passed 21/21 in approximately 7.8
seconds. These checks and the seven independent controls are component and
contract evidence. No full-system benchmark or frozen release suite was run by
this independent review.

## Pre-launch current-only cleanup targets

The owner explicitly requires current implementations without active legacy
compatibility scaffolding. Preserve immutable historical artifacts and current
versioned contracts; refuse unsupported versions rather than guessing a
migration. The following active paths were identified and reported for scoped
cleanup. This table is a task list, not a claim that all were removed here.

| Target | Active compatibility behavior to retire | Needed boundary check |
| --- | --- | --- |
| `loop/loop_definition.py` | `_record_encoding`, `_legacy_output_fields`, v1 and v2 readers, old input/output field branches, and `from_runtime(..., compatibility=True)` adaptation. Active callers include `recursive_loop.py`, `loop_handoff.py`, and `adaptive_host_verification.py`. | Current records round-trip; old versions and wrong role/mode contracts refuse. |
| `code_nodes/solution_compiler.py` | `_spec_from_dict` falls back from the current graph record to an older solution-spec shape and `allowed_modes`. | Only the declared current graph input is admitted. |
| `core/product_outcome_store.py` | `PRODUCT_OUTCOME_RECORD_TYPES` accepts `solve_outcome/v3` through `v6`, with weaker conditional requirements for older types. | Current `solve_outcome/v6` producer persists and reads; every earlier type refuses. |
| `memory/storage/repository.py` | Forwarding facade for learning-cycle implementation and records, with delegated self-test. Active callers occur in the command-line operations, main command, and core engine proof. | Callers use the owning modules; the actual learning-cycle checks remain collected exactly once. |
| `core/task_fingerprint.py` | `from_legacy_serialized` and string fallback in `parse_task_fingerprint`. | Current structured fingerprint accepted; old string records refuse. |
| `catalog/versioning.py` | `_restored_revision` reconstructs older inline metadata when the payload is not current `catalog_record_revision/v2`. | Current revision payload restoration works; unsupported payloads fail explicitly. |
| `ontology/loop_node.py`, `node/loop_node/__init__.py`, `ontology/records.py`, `ontology/artifacts.py` | Legacy Loop-node migration reader, forwarding namespace, and obsolete kind migration. | Current canonical Loop definitions work; unsupported historical kinds do not enter active runtime. |
| `core/saas_routes.py`, `core/user_feedback_intelligence.py` | `strings` and `string` route aliases, the old pillar alias, and `solution_component` scope adaptation. | Only documented current routes and scopes are accepted. |
| `core/run_history.py` | `usage_log` synthesis in `from_ledger` and `extend_from_ledger` for histories lacking explicit provider events. | Current provider events preserve accounting; missing accounting remains unknown. |
| `_self_test.py` | Flat `{name: bool}` report admission is retained as a legacy shape. | Only a nonempty recognized `tests` array counts as a suite; optional unavailable records remain explicitly not tested. |

Current compatibility and capability handshakes are not legacy readers. Customer
legacy-code analysis in housekeeping is also a present-day candidate-ingestion
feature, not a product backward-compatibility shim. Neither should be removed
merely because the word compatibility or legacy occurs in its source.

## Exact focused source coverage and closing hashes

Each listed file received focused semantic inspection. This does not assert
whole-file correctness. Paths are repository-relative. Hashes were collected
after the seven fixes and before the next bounded cleanup assignment.

```text
c84a0a059d4e9be2b5342c2ed07c1b70c0afd9e50f993c18a7ab91e5af39d42f  src/loop_engine/core/node_provisioning.py
098554c0a7dd59ef2b1c195dd79747b7730bf2f449b2c6ecf57a67ad229c92ff  src/loop_engine/core/model_call_records.py
36d798f1f6895e4f3078e239ae53357926faee08a4de775ba8b2971a2b9b5c0b  src/loop_engine/core/model_call_collection.py
6b24d5f4c9a82235aaac93627d14c614d0efba3c87d089201660061f291c0f9e  src/loop_engine/core/adaptive_practitioner_records.py
19345589a72232ee2dfac8d5444c8411cd735929e42fe8a609637dac2efbff2c  src/loop_engine/core/adaptive_practitioner_validation.py
e10e48d28cdbf8d39c328648e4e8ec90221b32d7665587af4b21df93eac982d3  src/loop_engine/core/practitioner_runtime/__init__.py
3ddcd6f859583bd446acb4be039f8d6322a148d174d29a1513f95ff009eac2b1  src/loop_engine/core/practitioner_runtime/capabilities.py
2f35d7f42b3d227e4c10fc750a05f697ffee8d0e10f77f449b796f4b9208c239  src/loop_engine/core/practitioner_runtime/observations.py
9f0d9d11793c41473b2c6012150861d5510ec3244b5477c7c29f940a91bbb710  src/loop_engine/core/practitioner_runtime/README.md
ba60ead8e3cea2c327f1847cfceda0384859b6cf8d686174647b4835d3353a6f  src/loop_engine/core/instance_instructions.py
22dca8072c5731cfc8de1d6a9d23317f1ffa91416ea6f1e20a081859d6a3469b  src/loop_engine/core/harness_process.py
1c8825d227e08ca93d6b396fbc6e451fd3eb3df657b63f1d2426b0884ed6c50e  src/loop_engine/core/harness_process_checks.py
d558aa01c2483ec87399b5f5fad6a523049c8197649847ef50c13f0cb6c7c7e8  src/loop_engine/core/harness_semantic.py
4b5d615be1d31122c0d81cd503bdc1db3ff30b270dd2f48187127f1a63a05428  src/loop_engine/core/harness_process_relay.py
13cef4fc5d6447b25f18726e519e58171056c363ee3f7394d813990f94b3efc7  src/loop_engine/core/harness_responses_recipes.py
37a5421ac383b0b74f917027d91e6649b7a931fcd81ad8443f8081b6ec4834f0  src/loop_engine/code_nodes/solve_runtime.py
e00ce9cd5ea6203539f7639f75b09711622d05605f447b297715b02ad5395277  src/loop_engine/code_nodes/solution_export.py
5858ed7a3f433a957ebda47266ad8f6d02256a703741a0d962690d8d3b31dda6  src/loop_engine/code_nodes/solution_export_checks.py
edaa6da1920cc6b87a16c9bc4c8d9ef4b363ed171cde4fb09ae45c20a8b0f570  src/loop_engine/strings/solution_export_templates.py
d1181a4a5eafeecca7e28a6261b08d8a070c6a4243d54ab0f858c9442c3a6d40  src/loop_engine/cli_operations.py
29cc32fb3a450d7d6748af4f2193915c587a23a73a1b1e3fb00d1106f0eb99ad  src/loop_engine/__main__.py
170aa4f876d00a4201674dd4c3879e89657e4b209eee981d3244fc45397fd3d6  src/loop_engine/core/adaptive_practitioner_scope.py
49c81f0653217c0cdd93e0451abebceb2334f233d966ddba5fe6122b4f2c107e  src/loop_engine/core/adaptive_practitioner_result.py
8b4a6f809c035839ea2f45e8d102a763599465e02bb99bcc021ca17c269ac6b3  src/loop_engine/core/adaptive_practitioner_verification.py
d210c25edf0d42fe36d3838755c58df25c889336e105f03e2c05bdded50c2a5a  src/loop_engine/core/adaptive_practitioner_acceptance_checks.py
```

The compatibility-target inspection additionally covered the exact functions
named in the cleanup table. Its purpose was to identify scoped next work, not
to establish those files' complete behavior. Other agents own the final source
inventory, architecture map, launch gates, and release-state records.

## Subsequent bounded implementation: current-only outcomes and test reports

After the independent review was saved, the owner explicitly assigned this
reviewer a separate implementation tranche. The changes in this section are
therefore self-tested implementation, not independent review of another
agent's work. They do not change the snapshot hashes or original observations
above.

### Implemented boundaries

- `_self_test._module_test_records` no longer accepts a flat Boolean dictionary
  as a test suite. It requires a nonempty recognized test-record sequence.
- The full aggregate report is `loop_engine_self_test/v2`. Every folded row has
  a fully qualified `owner_module` assigned by the engine, overriding any
  producer value. This includes executed tests, module exceptions, missing
  dependencies, and unavailable optional adapters. The aggregator's own checks
  belong to `loop_engine._self_test`.
- Optional adapters still retain their actual missing dependencies and reason,
  have `passed=null`, and are excluded from the executed denominator. They are
  not converted to passing or failing executions.
- Product outcome storage and product outcome references accept only
  `solve_outcome/v6`. Questions, model-call accounting, and action and stage
  vector projections are always required. Missing accounting does not become
  zero. Reference loading no longer coerces a nonempty string into Boolean
  `solved=true`.
- Current fixtures now emit current outcomes. Tests retain explicit refusal
  of unsupported older and future versions. The solve integration agent owns
  the corresponding `solve_request_adaptation.py` test change.
- The version-controlled `memory/storage/repository.py` forwarding facade was
  removed. Its active callers import `learning_cycle`, `learning_records`, or
  `learning_cycle_checks` directly. The owning learning checks are directly
  registered once in the aggregate. `core_engine_proof` also invokes them as
  part of its separately named integration proof; this is an indirect
  invocation, not another registration of all 17 test rows.

No historical report bytes, immutable run bundle, map, or generated inventory
was changed. The removed facade remains recoverable from repository history.
Current documentation and map regeneration remain with the root agent.

### Verification

| Executed check | Result |
| --- | --- |
| `_conformance_test.self_test` | 28/28 |
| `core.run_history_checks.self_test` | 48/48 |
| `memory.storage.learning_cycle_checks.self_test` | 17/17 |
| `code_nodes.loop_report.self_test` | 14/14 |
| `code_nodes.run_playback.self_test` | 7/7 |
| `core.studio_server.self_test` | 20/20 |
| `tools/test_task_campaign.py` | 22/22 |
| `examples/25_host_runtime/test_generalization_probe.py` | 29/29 |
| `code_nodes.core_engine_proof.learning_cycle_proof` | passed |
| Current Studio saved-run fixture in a temporary directory | v6 outcome; intact event chain |
| Five-step command with temporary run and learning directories | exit zero; zero provider calls; one candidate listed afterward |
| `git diff --check` | passed |

Five in-memory mutants were killed without editing the source tree:

1. Restoring flat Boolean report admission failed
   `module_reports_refuse_empty_unrecognized_and_non_boolean_results`.
2. Preserving the producer's forged `owner_module` failed
   `folded_test_ownership_is_engine_assigned_for_executed_and_unavailable_checks`.
3. Accepting unsupported product-reference versions failed
   `product_outcome_references_refuse_old_versions_and_truthy_non_booleans`.
4. Restoring truthy coercion in `_product_outcome_ref` failed
   `loaded_product_outcome_reference_does_not_coerce_boolean_authority`.
5. An independent pure validation control rejected v3, v4, v5, and v7. Replacing
   `_validate_product_outcome` with a reader that validated a v6 copy but returned
   the original version admitted all four and failed that control.

The corresponding refusal and ownership fixtures are retained in
`_conformance_test.py` and `run_history_checks.py`. The full aggregate has not
been rerun for this moving implementation tranche. The root agent owns the
frozen final suite and map checks.

### Paths changed in this implementation tranche

```text
src/loop_engine/_self_test.py
src/loop_engine/_conformance_test.py
src/loop_engine/core/product_outcome_store.py
src/loop_engine/core/run_history_checks.py
src/loop_engine/core/studio_server.py
src/loop_engine/code_nodes/core_engine_proof.py
src/loop_engine/code_nodes/loop_report.py
src/loop_engine/code_nodes/run_playback.py
src/loop_engine/cli_operations.py
src/loop_engine/__main__.py
src/loop_engine/memory/storage/repository.py [deleted]
tools/create_studio_acceptance_fixture.py
tools/test_task_campaign.py
examples/25_host_runtime/test_generalization_probe.py
artifacts/architecture-audit-2026-09-19/root-changes-independent-review.md
```

## Subsequent bounded implementation: local provisioning protocol

Source checkpoint: 2026-09-19T16:30:24Z. This is implementation evidence from
the implementing agent, not independent qualification by another reviewer.
The domain policy and metering implementation belongs to the funding and
delivery agent. Its current server implementation was used without replacing
its authority decisions in the connected checks.

### Delivered behavior and limits

`core/provisioning_mcp.py` provides `ProvisioningMcpTransport` over real
official-package client and server JSON-RPC session streams. The client calls
initialize, tools/list, and tools/call. Requests cross JSON serialization before
the low-level server receives them. A host binds the credential outside the
message stream. Tool arguments cannot override credentials, server paths,
policies, body readers, or the domain contract version.

The declared supported profile is exactly `2025-11-25`, observed with installed
Python distribution `mcp==1.29.1`. The constructor and actual initialization
reject unsupported profiles, including `2026-07-28`. This is not a claim of
current-spec or hosted interoperability. The official lifecycle defines
initialization and protocol agreement before normal operations; the adapter
keeps that agreement explicit rather than silently treating a rejected
initialization as permission to call tools.
[Protocol lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle).

The in-process stream pair is a documented custom transport shape, not an
HTTP endpoint. The protocol specification permits custom bidirectional
transports that preserve its message format and lifecycle. These tests exercise
actual protocol machinery, not a direct function standing in for a client.
[Protocol transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports).

This adapter does not implement hosted OAuth, protected-resource metadata,
authorization-server discovery, HTTP origin checks, or a browser/customer
onboarding flow. Those need a separately qualified hosted transport. The
official authorization specification distinguishes HTTP authorization from
local and alternative-transport credential handling.
[Protocol authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization).
All three sources were accessed 2026-09-19.

The four tools delegate to the existing `ProvisioningServer` for discovery,
list, manifest, and read. The server remains the sole authority for exact tenant
grants, qualification, revocation, integrity, and acknowledged metering. Every
domain invocation runs through a canonical Loop with the registered
`practitioner.code_execution@1.0.0` profile. Credentials and bodies do not enter
Loop events. No alternative runtime or store was added.

An error response makes no claim that billing did not occur. Its
`metering_status=not_asserted` preserves uncertainty. A successful metered body
retains the server's exact committed acknowledgment and its stated durability.
The reference acknowledgment is explicitly volatile. There is no automatic
retry after a failed or cancelled operation. A synchronous host callback may
finish after the client cancels; cancellation is not proof of no commitment.

### Retained failure observations

1. The installed official server session accepts `notifications/initialized`
   even without a prior successful initialize. A transport that only rejects
   the version on initialize therefore has a lifecycle bypass. The adapter now
   independently requires a valid exact-profile initialization and its
   initialized notification. An unsupported initialize followed by a forged
   notification and a tool call yields protocol errors and zero domain Loop
   events.
2. An initial timeout-only check did not exercise a real cancellation
   notification. It was replaced with a check that observes the actual request
   identifier and sends `notifications/cancelled` while the local meter is in
   flight. That stronger test reproduced `AssertionError: Request already
   responded to` after a shielded synchronous callback completed. The adapter
   now delivers pending cancellation before constructing a second response.
   Removing that checkpoint still reproduces an exception group and kills the
   mutant.

### Closing checks

| Suite or control | Observed result |
| --- | --- |
| Actual local provisioning protocol | 19/19 |
| Current `ProvisioningServer` integration | 40/40 |
| Existing `mcp_adapter` | 21/21 |
| Existing `mcp_sdk_transport`, including its local standard-input/standard-output server | 7/7 |
| Handshake guard removal mutant | killed by five named protocol checks |
| Canonical Loop bypass mutant | killed by exact registered-runtime observation |
| Failed-domain-call retry mutant | killed by two observed uncertain-meter attempts instead of one |
| Pending cancellation checkpoint removal mutant | killed by the reproduced exception group |
| Restored transport after all mutants | 19/19 |
| `git diff --check` | passed |

The protocol checks include valid calls, wrong key, unsupported initialization,
forged lifecycle notification, revoked grant in an open session, unauthorized
candidate and private metadata, metadata-only body refusal, credential/version
argument injection, unknown tool, request-size limit, absent and unknown meter
acknowledgment, explicit unmetered grant, and actual cancellation. The tests
assert that keys and body bytes are absent from execution events and that the
observed role/profile/relationship matches the boundary registration.

The final protocol report explicitly records zero provider calls, zero network
connections, `remote_http_supported=false`, `oauth_supported=false`, and
`hosted_authorization_qualified=false`. The separate existing transport suite
starts its own local process; it does not contact a provider.

At the local boundary-registry check, 9/11 passed. The two failures were exact
symbol resolution for the new implementation and test module, because the root
agent had not yet regenerated its architecture-map inventory. The runtime
ontology assertion in the connected protocol test passed. The registry failures
remain reported pending integration rather than counted as passes here.

Reproduce the owning protocol suite from the repository:

```bash
.venv/bin/python -c 'import json; from loop_engine.core.provisioning_mcp_checks import self_test; report = self_test(); print(json.dumps(report, indent=2)); assert report["all_passed"]'
```

The mutations were applied only to in-memory Python functions and restored
after each check. No runtime source mutation, provider call, cloud operation,
payment, publication, or historical-artifact rewrite occurred during them.

### Changed paths and closing hashes

This tranche added `core/provisioning_mcp.py` and
`core/provisioning_mcp_checks.py`, added their operational row and exact ontology
binding in `core/boundary_registry.py`, and registered the owning checks in
`_self_test.py`. This report was appended. It did not change the main command or
command-line operations. The root agent owns map and final frozen-suite work.

```text
f7d4d17a546b90dc868af9341fc099e779c3c2093feb88ac59c1ef7c3b633360  src/loop_engine/core/provisioning_mcp.py
f023e494dde60db5f62cf4514fcc33a017975fe934d6d828936a611f324198dd  src/loop_engine/core/provisioning_mcp_checks.py
c1babd5c6dfd3d18d35d4ab7e139d87cdc4b9eefd0e1f57c8372e3d0a9beb2a6  src/loop_engine/core/provisioning_server.py [integration dependency, not edited by this agent]
```
