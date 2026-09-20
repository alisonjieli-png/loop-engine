# Organization, tests, and delivery audit

Kind: focused architecture audit with reproducible source findings.
Audit date: September 19, 2026. Observations below precede the separately authorized repairs.
Inspected revision: `48cc954322691e492aad69a465ba470a112730e7`, branch `main`,
with existing uncommitted work preserved. No source, deployment, or account
was changed during the evidence collection described here.

The most consequential findings are concrete boundary failures: loading an
empty endpoint permission list grants every endpoint; a remote evaluation
request chooses the server filesystem root used for catalog reads; and export
verification invokes candidate code even after detecting a file digest
mismatch. The container build also masks installation failures and publishes
before its smoke test. Passing component totals do not detect these cases.

This audit covers repository organization, test discovery and assertion
quality, package delivery, container publication, and the connections between
the hosted service and reusable material. It is a bounded contribution to the
larger audit, not a claim that all 587 Python modules have been reviewed.
The [question register](organization-questions.json) contains 83 focused
questions and source hashes. The [coverage record](organization-coverage.json)
lists 55 files with focused semantic inspection, including follow-up repairs.
The initial audit-time hashes cover the original 43 files. Source sections were selected
for the named boundaries; a listed file is not a whole-file correctness claim.

## Architecture frame

The complete governing classification remains:

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

Physical folders, reusable records, services, and test functions do not create
new executable runtime types. The first public serving product does not remove
the requirement to connect the internal task graph, subgraphs, scoped
assignments, independent verification, and reusable solutions.

## Ranked findings

Priority 1 means repair before exposing or relying on the affected boundary.
Priority 2 means a material correctness, qualification, or maintainability gap.
These priorities are this audit's judgment, not an automatically approved plan.

| Finding | Priority | Evidence state | Owning boundary |
|---|---|---|---|
| ORG-F01. Empty endpoint permissions expand during deserialization. | 1 | Reproduced in memory. | `core.service_api.TenantRecord` |
| ORG-F02. Hosted evaluation accepts a caller-selected server filesystem root. | 1 | Real dispatch reproduced; final file read intercepted. | `code_nodes.service_endpoints` |
| ORG-F03. Export verification executes after failed integrity checks. | 1 | Interpreter callback observed after a digest failure. | `code_nodes.solution_export` |
| ORG-F04. Installation failures are masked and image tags publish before acceptance. | 1 | Shell behavior reproduced; workflow order inspected. | Dockerfile and image workflow |
| ORG-F05. Test discovery can silently lose relocated or unregistered suites. | 2 | Nested and unrelated-string canaries reproduced. | `_conformance_scan` |
| ORG-F06. Empty module reports pass; duplicate modules inflate suite totals. | 2 | Aggregate fault injection and source census. | `_self_test` |
| ORG-F07. Dependency and registration detectors miss equivalent source forms. | 2 | Absolute import canary reproduced; registration gaps inspected. | Conformance detectors |
| ORG-F08. Container recipe checks accept root execution and an invalid digest. | 2 | All five checks passed for a deliberately invalid fixture. | Example 28 checker |
| ORG-F09. Generic exports are verified from source, not as installed distributions. | 2 | Source inspection; fresh wheel test remains open. | Standalone export and packaging |
| ORG-F10. Import reachability is being used beyond what it establishes. | 2 | Current static report plus missing public dependency. | Reachability and component reporting |
| ORG-F11. Service delivery remains split across disconnected and transient components. | 2 | Current factories and interfaces inspected. | Hosted service and provisioning |
| ORG-F12. Continuous integration does not visibly collect all relevant integration tests. | 2 | Workflow and entry-point search; local integration check. | Continuous integration |
| ORG-F13. Physical grouping and private imports make safe reorganization harder. | 2 | Directory and import census with scoped examples. | Existing component owners |

### ORG-F01. Empty permissions do not survive a record roundtrip

[service_api.py](../../src/loop_engine/core/service_api.py), lines 68 to 72,
uses `tuple(value.get("endpoints") or ENDPOINTS)`. An explicitly empty
`TenantRecord.endpoints` serializes as `[]`, then reloads as all six endpoints.
The in-memory probe observed exactly that expansion. This is a permission
change caused by treating an empty value as if it were absent.

The existing roundtrip check at lines 273 to 277 uses the default full
permission set. It cannot discriminate the faulty case. The repair belongs
in the record reader: distinguish absent, empty, null, malformed, and valid
explicit values. A negative test must exercise actual dispatch after reload.

### ORG-F02. A tenant can choose the catalog confinement root

[service_endpoints.py](../../src/loop_engine/code_nodes/service_endpoints.py),
lines 49 to 51, forwards `catalog_root` and `catalog_files` from the solver
specification into `catalog_layer_from_file`. The evaluator at lines 88 to 97
exposes that solver builder to an authenticated request.

[text_conformance.py](../../src/loop_engine/code_nodes/text_conformance.py),
lines 118 to 135, confines the file to the supplied root. That local helper
is not sufficient when the remote caller supplies the root itself. The
real service dispatch returned status 200 and attempted a read at
`/virtual-outside-tenant/probe.json`. The final read was intercepted and
returned `{}`; no outside file or protected content was accessed.

Keep local command-line catalog files supported. The hosted adapter needs a
server-configured catalog access policy or resolver whose permitted scope
cannot be broadened by request data. Test positive tenant-scoped access and
negative root substitution, absolute paths, traversal, symlink escape, and
cross-tenant selection through the hosted dispatch boundary.

### ORG-F03. Integrity failures do not gate export execution

[solution_export.py](../../src/loop_engine/code_nodes/solution_export.py),
lines 347 to 360, appends a failed digest check and continues to
`_run_isolated`. The probe replaced only the interpreter callback and
observed one invocation after the failed check. The returned verdict was
false, but that is too late to prevent candidate effects.

The loaded manifest digest is returned at line 380 without recomputation.
Loaded manifest paths, package names, and isolation values are not subjected
to the typed specification's full validation before they affect reads or
interpreter construction. `_run_isolated`, lines 321 to 323, uses a normal
host subprocess with Python import-isolation flags and a reduced environment.
It does not invoke the declared workspace sandbox boundary.

[solution_export_checks.py](../../src/loop_engine/code_nodes/solution_export_checks.py)
checks that tampering produces a failed result. It does not assert that
tampered code was never executed. The required discriminating assertion is
zero interpreter calls after any pre-execution integrity refusal. Resource
and effect confinement need their own tests; import isolation is not proof
of effect isolation.

### ORG-F04. Image publication happens before sufficient acceptance

[Dockerfile](../../Dockerfile), lines 20 to 22, places `|| true` after the
entire `pip upgrade && pip install && useradd` chain. The harmless equivalent
`false && true && true || true` exits zero. A failed package installation
can therefore be hidden by the image build.

[publish-image.yml](../../.github/workflows/publish-image.yml) runs on push
independently from the test workflow. Its Build and push step updates public
tags before it runs doctor. A later smoke-test failure does not undo those
published tags. Build provenance is also explicitly disabled.

Doctor itself is honest about its scope. In
[cli_operations.py](../../src/loop_engine/cli_operations.py), lines 338 to 387,
it reports configuration validity and explicitly says provider and generated
project execution were not tested. The image workflow accepts a nonempty
dictionary. This is not a hosted-service or solve acceptance test.

Fix failure propagation, build one exact image, run the required offline
acceptance against it, and publish only after its revision has passed the
eligible source checks. This audit made no registry mutation.

### ORG-F05 and ORG-F06. The suite can shrink while remaining green

[The collection detector](../../src/loop_engine/_conformance_scan.py),
lines 653 to 696, skips nested package paths and every mapped root module.
It also finds collection by matching quoted strings anywhere in the suite
source. Both a nested unregistered suite and a name appearing only as an
unrelated string produced zero findings in safe in-memory canaries.

[The aggregator](../../src/loop_engine/_self_test.py) accepts a module report
with `tests=[]`. Replacing all module reports with that value produced
`passed=1`, `total=1`, and `all_passed=true`. The one remaining check is the
aggregator's own exception-handling canary.

The current registration list has 385 entries and 381 distinct modules.
`ontology.artifacts`, `ontology.catalog`, `ontology.folders`, and
`ontology.ontology_checks` each appear twice. Missing optional adapters also
produce records with both `passed=true` and `not_tested=true`, and these
records count toward the headline total. The extra unavailable field is
useful, but the pass denominator still needs a precise interpretation.

Parse the actual registration structure, resolve nested module identities,
reject duplicate registrations and malformed empty reports, and report
executed checks separately from unavailable adapters. These changes must
precede a broad physical folder migration, or that migration can remove
checks from discovery without being detected.

### ORG-F07. Boundary detectors cover particular spellings

`scan_dependency_direction`, lines 372 to 378, handles `ast.ImportFrom` but
not `ast.Import`. The relative from-import control produced one finding; an
equivalent absolute import produced none. Relative matching also assumes
one particular nesting depth. The current scan reports 73 known wrong-way
imports against a ceiling of 73, not a clean layering result.

`scan_unregistered_boundaries`, lines 542 to 559, compares a module basename
against one concatenated string and recognizes only unaliased direct call
names. Exact module resolution and alias-aware calls need canaries.
The separate source/text/tree caches are keyed only by paths, so a repeated
scan in one process can use old bytes after a file changes.

The repository import guard omits the `loop_engine_devtools` import root
that the independent bootstrap includes. Reference validation imports a
`code_ref` module but does not resolve the final named symbol. These are
specific gaps in individual detectors. They do not establish that every
other repository gate would also miss every possible violating fixture.

### ORG-F08. Container recipe checks do not prove their named properties

[Example 28](../../examples/28_containerized_worker/run.py) returned five
passes for this fixture:

```dockerfile
FROM python:3.12-slim@sha256:invalid
USER 0
ENTRYPOINT ["loop-engine"]
```

The non-root check rejects only the spelling `USER root`. Digest validation
only checks for the substring `@sha256:`. The example's main function also
treats missing base-image pinning as a warning rather than a failure.

The [worker manifest](../../examples/28_containerized_worker/k8s/worker-deployment.yaml)
contains a literal `READINESS_KEY_FROM_SECRET` header. The
[README](../../examples/28_containerized_worker/README.md) tells readers to
replace the image reference and create a tenants Secret, but does not show
how to replace that readiness credential. The guide's stated procedure is
therefore incomplete for authenticated readiness. No cluster was deployed.

### ORG-F09. Generic export packaging and identity need broader checks

Standalone verification inserts the exported `src` directory into
`sys.path`. It does not build or install the export. The generated
`pyproject.toml` includes only `*.json` and `*.yaml` package data although
`ExportedFile` accepts general text resources and nested paths. A package
using a nested HTML template is a concrete proposed canary for the missing
installed-distribution test. This audit did not build that wheel.

The export specification digest also omits container settings, isolation,
and Python requirements. Changing processor allocation and invocation
arguments left the specification digest unchanged while changing the rendered
Job. The complete written-file manifest can still distinguish those bytes;
the narrower specification digest must not be presented as binding all
behavior-affecting settings.

### ORG-F10. Import and inventory records are not execution evidence

[reachability_report.py](../../src/loop_engine/reachability_report.py)
walks every import, including imports inside self-tests. Its current output
is 350 reached modules out of 587, with eight required modules and no required
misses. This establishes a static import closure only.

The public solve dependency constructor still omits the harness catalog and
guardrails. The provisioning hook can therefore be imported while returning
`no_catalogue_installed`. Conversely, string-driven facade and registry
dispatch can reach modules a static import walker does not follow. Neither
being in the closure nor being outside it proves real use or universal disuse.

[export_component_inventory.py](../../tools/export_component_inventory.py)
combines computed inventory with fixed narrative findings and historical
states. Those records need explicit evidence dates or current discriminating
checks before they are used to choose development work.

### ORG-F11. The service is not one complete delivery path yet

The HTTP service, in-process provisioning server, and local Spawned Loop
provisioning hook are separate components. The shipped HTTP endpoint list
does not include the provisioning operations or a product Model Context
Protocol endpoint. The default memory store and metering ledger are
in memory. The service constructor provides no durable ledger injection.

The provisioning server checks body digests, but its read response says
`metered=true` without requiring an installed or acknowledged meter.
Metadata offers do not receive the authenticated tenant. The catalog has
references and classification tags but no authoritative qualification
lookup on its normal read path. Its registration method allows metadata
replacement under one identity if the body digest is unchanged.

These findings reinforce the
[earlier local review](../claude-session-review-2026-09-19/README.md). They
do not justify inventing a second store or runtime. Extend the existing
contracts and connect them through the actual public and client paths.

### ORG-F12. Relevant tests need explicit continuous integration ownership

The inspected workflow discovers `tools/test_*.py`, the embodiment tests,
and the qualification laboratory, then runs a declared example list.
There are 13 `test_*.py` files in `examples/25_host_runtime`, but no matching
discovery or example-25 invocation appears in that workflow. The inspected
resource catalog test contains substantive revocation, expected revision,
body disclosure, traversal, and real process-parity checks.

No reference to `integrations/tests/check_integrations.py` appeared in the
inspected workflow and test entry points. That check passed when run here,
reporting four manifests and six skills, but its assertions only parse
manifest JSON, count skills, and reject a small set of strings. It does not
prove manifest paths, host installation, capability authority, or real CLI
compatibility.

Base-wheel acceptance is valuable and already checks package module parity
and exclusion of two local-state directories. It then runs selected
onboarding and Studio checks rather than the full installed self-test or
the new provisioning delivery path. Keep these scope limits visible.

### ORG-F13. Existing interfaces should guide reorganization

`core` contains 362 Python files directly. The layout record distinguishes
README-only conceptual package areas from implementation in core, catalog,
memory, and strings. Moving files without resolving the existing ownership
and import contracts would not complete that separation.

An abstract syntax tree census found 131 private import statements containing
266 imported private symbols. A heuristic that excludes named test functions
and check modules leaves 75 statements and 149 symbols. These are indicators,
not 75 proven architecture violations. Some represent deliberate shared
helpers. Examples include CLI adapters sharing credential helpers and
`task_materials` sharing private source-admission operations.

Classify those relationships before promoting private helpers to interfaces
or moving implementation families. Preserve string-based maps, public
exports, package data, and collection paths. In particular, a count-only
dependency ratchet and a shallow test collector are not enough to qualify
a deep folder reorganization.

## Checks performed and their limits

| Check | Observed result | What it establishes |
|---|---|---|
| Existing read-only conformance scan | 587 files; 73 dependency findings; ceiling 73; `clean=false`. | Declared static checks and tolerated dependency debt. |
| Repository conformance | 587 files; passed; no reported problems. | Its current syntax, class, import, and manifest checks. |
| Architecture contract | Passed. | Its current forbidden class/path and canonical runtime checks. |
| Solve import closure | 350 of 587 reached; 8 required; no required misses. | Static import reachability, including self-test bodies. |
| Provisioning component suite | 8 of 8 passed. | Existing in-memory scenarios, not transport or durable billing. |
| Real endpoint component suite | 4 of 4 passed. | Existing handler fixtures, not caller-controlled root refusal. |
| Integration structure check | 4 manifests and 6 skills; passed. | The narrow assertions described above. |
| Focused failure probes | Permission expansion, caller-selected catalog read, execution after digest failure, incomplete export digest, collection misses, empty-report pass, and invalid recipe pass reproduced. | The exact safe fixtures below. |

No live model call, cloud action, registry publication, customer request,
container build, fresh wheel build, or full self-test rerun was performed
during this audit. The earlier 5,316-check result is historical evidence and
is not claimed as a new result here. The first attempted probe command used
`python`, which is absent in this shell; it did not run. The recorded probes
were then run successfully with `python3`.

## Safe reproducer source and observed results

The following snippets run from the repository with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3`. They do not create
fixture files or read protected data. The filesystem and interpreter
callbacks are intercepted where stated. They test the boundary logic rather
than claiming a live exploit against an operated service.

### Permission and hosted catalog path

```python
import json
from pathlib import Path
from unittest.mock import patch
from loop_engine.core.service_api import TenantRecord, key_digest, ServiceApplication
from loop_engine.core.evaluation_suite import EvaluationCase, EvaluationSuite
from loop_engine.code_nodes.service_endpoints import default_handlers

original = TenantRecord('probe', key_digest('synthetic-key'), 'tenant:probe', ())
restored = TenantRecord.from_dict(original.to_dict())
print(list(original.endpoints), list(restored.endpoints))

app = ServiceApplication(
    (TenantRecord('probe', key_digest('synthetic-key'), 'tenant:probe'),),
    handlers=default_handlers())
suite = EvaluationSuite('probe', '1.0.0', (EvaluationCase('a', 'a', 'a'),))
payload = {'suite': suite.to_dict(), 'solver': {
    'kind': 'text_conformance', 'catalog_root': '/virtual-outside-tenant',
    'catalog_files': ['probe.json']}}
reads = []
real_read = Path.read_text
def intercepted_read(path, *args, **kwargs):
    if str(path) == '/virtual-outside-tenant/probe.json':
        reads.append(str(path))
        return '{}'
    return real_read(path, *args, **kwargs)
with patch.object(Path, 'read_text', intercepted_read):
    status, response = app.handle('POST', '/v1/evaluate', 'synthetic-key',
                                  json.dumps(payload).encode())
print(status, reads, response.get('record_type'))
```

Observed before repair:

```json
{"endpoints_before":[],"endpoints_after":["health","conform","evaluate","usage","memory_write","memory_read"]}
{"status":200,"reads":["/virtual-outside-tenant/probe.json"],"result_type":"service_evaluate_response/v1"}
```

### Export refuses late and omits settings from its specification digest

```python
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from loop_engine.code_nodes import solution_export as export

manifest = {'package_name': 'audit_probe', 'isolation': 'stdlib_only',
            'manifest_digest': 'forged',
            'files': {'src/audit_probe/__init__.py': 'mismatch'}}
executions = []
def intercepted_run(*args):
    executions.append(args[2])
    return export.subprocess.CompletedProcess([], 0, stdout='ok\n', stderr='')
def intercepted_text(path, *args, **kwargs):
    return json.dumps(manifest) if path.name == 'MANIFEST.json' else 'pass\n'
with patch.object(Path, 'is_file', return_value=True), \
     patch.object(Path, 'is_dir', return_value=False), \
     patch.object(Path, 'read_text', intercepted_text), \
     patch.object(Path, 'read_bytes', return_value=b'pass\n'), \
     patch.object(export, '_run_isolated', intercepted_run):
    result = export.verify_export('/virtual-export')
print(result.passed, result.checks[0]['passed'], len(executions),
      result.manifest_digest)
base = export.SolutionExportSpec('audit_probe', '1.0.0', 'probe',
    (export.ExportedFile('__init__.py', 'pass\n'),))
changed = replace(base, container=export.ContainerSpec(
    arguments=('--different',), cpu='4000m'))
print(base.digest == changed.digest,
      export.render_kubernetes_job(base) != export.render_kubernetes_job(changed))
```

Observed:

```json
{"verification_passed":false,"digest_check_passed":false,"execution_calls":1,"returned_manifest_digest":"forged"}
{"same_specification_digest":true,"different_job_render":true}
```

### Test and dependency detector canaries

```python
import ast
import importlib
from types import SimpleNamespace
from unittest.mock import patch
from loop_engine import _self_test as suite
from loop_engine import _conformance_scan as scan

with patch.object(importlib, 'import_module', return_value=SimpleNamespace(
        self_test=lambda: {'tests': []})), \
     patch.object(importlib.util, 'find_spec', return_value=object()):
    result = suite.self_test()
print(result['passed'], result['total'], result['all_passed'])

rules = {'dependency_direction_ratchet': {'core -> code_nodes': {}}}
for source in ('from ..code_nodes.solution_records import SolutionCandidate',
               'import loop_engine.code_nodes.solution_records as records'):
    with patch.object(scan, '_py_files', return_value=['core/probe.py']), \
         patch.object(scan, '_source_tree', return_value=ast.parse(source)):
        print(len(scan.scan_dependency_direction('/virtual', rules)))

for files, source in (
    (['core/family/unlisted.py'], ''),
    (['core/never_run.py'], '"core.never_run" # unrelated string')):
    with patch.object(scan, '_py_files', return_value=files), \
         patch.object(scan, '_source_tree', return_value=ast.parse(
             'def self_test(): return {"tests": []}')), \
         patch.object(scan, '_source_text', return_value=source), \
         patch.object(scan.os.path, 'exists', return_value=True):
        print(len(scan.scan_uncollected_self_tests('/virtual', {})))
```

Observed: empty aggregation `1, 1, true`; relative import `1` finding;
absolute import `0`; nested uncollected suite `0`; unrelated-string suite `0`.

The Docker shell canary was `sh -c 'false && true && true || true'`; it
returned zero. The recipe canary called `check_dockerfile` from example 28
on the three-line invalid Dockerfile shown above; all five checks returned
`passed=true`. No container was built.

## Focused file inspection list

The following exact files were inspected. The question register preserves
their audit-time hashes. The package-wide syntax/import census and existing
conformance traversal are additional mechanical coverage, not a semantic
review of every traversed file.

- `AGENTS.md`
- `ASTRA.md`
- `pyproject.toml`
- `.github/workflows/ci.yml`
- `.github/workflows/publish-image.yml`
- `Dockerfile`
- `.dockerignore`
- `devtools/AGENTS.md`
- `devtools/README.md`
- `docs/architecture/FOLDER-DEPTH-AND-THE-FLAT-CORE-2026-09-18.md`
- `docs/architecture/REPOSITORY-LAYOUT-AND-RECORD-KINDS-2026-09-18.md`
- `src/loop_engine/__init__.py`
- `src/loop_engine/_self_test.py`
- `src/loop_engine/_conformance_scan.py`
- `src/loop_engine/repository_conformance.py`
- `src/loop_engine/architecture_contract.py`
- `src/loop_engine/reachability_report.py`
- `src/loop_engine/backend_isolation.py`
- `src/loop_engine/structure_review.py`
- `src/loop_engine/cli_operations.py`
- `src/loop_engine/core/api_quality.py`
- `src/loop_engine/core/service_api.py`
- `src/loop_engine/core/provisioning_server.py`
- `src/loop_engine/core/harness_intelligence.py`
- `src/loop_engine/core/spawned_provisioning.py`
- `src/loop_engine/core/boundary_registry.py`
- `src/loop_engine/core/evaluation_suite.py`
- `src/loop_engine/core/task_materials.py`
- `src/loop_engine/core/provider_failure_classes.py`
- `src/loop_engine/code_nodes/service_endpoints.py`
- `src/loop_engine/code_nodes/solve_runtime.py`
- `src/loop_engine/code_nodes/text_conformance.py`
- `src/loop_engine/code_nodes/solution_export.py`
- `src/loop_engine/code_nodes/solution_export_checks.py`
- `tools/export_component_inventory.py`
- `examples/28_containerized_worker/run.py`
- `examples/28_containerized_worker/README.md`
- `examples/28_containerized_worker/k8s/worker-deployment.yaml`
- `examples/28_containerized_worker/k8s/solution-job.yaml`
- `examples/25_host_runtime/test_intelligence_resource_catalog.py`
- `integrations/README.md`
- `integrations/architecture.yaml`
- `integrations/tests/check_integrations.py`

## Proposed repair order

Repair authority widening, remote filesystem scope, integrity-before-execution,
and image failure/publication ordering first. Strengthen their owning checks
with the exact counterexamples, including mutants that remove the protection.
Then repair test discovery and count semantics before moving folders. Connect
the actual hosted delivery and client use path through existing contracts,
and qualify the exact installed package and image that will be delivered.

Keep completed fixes, observed integration, independent qualification, and
publication as separate statuses. Source imports, record presence, diagrams,
and passing narrow fixtures do not establish the full first release.

## Authorized service and delivery repairs after the audit

The owner subsequently authorized implementation. The pre-repair observations
above and the question register's original source hashes remain historical.
The following changes were made without a commit, push, deployment, or image
publication:

- `TenantRecord.from_dict` preserves explicit empty endpoint permissions and
  rejects malformed serialized permission collections. Omitted permissions
  retain the existing default.
- Hosted evaluation rejects request-selected catalog roots. A typed
  `ServiceCatalogScope` configured at handler construction binds each catalog
  directory to one authenticated tenant. The default has no file-catalog
  grant. Absolute paths, traversal, cross-tenant access, escaping symlinks,
  and malformed references are refused. Local solver file specifications
  continue to work through their existing reader.
- The Docker installation chain no longer suppresses a failed installation.
- The image workflow requires a successful trusted continuous integration
  run for the exact current main revision, builds without publishing, verifies
  the local image's configuration and service suites with external networking
  disabled, rechecks main, then pushes that same image without rebuilding it.
- Example 28's existing recipe checks now reject numeric root users, invalid
  digests, missing digests, and masked installation failures. Four explicit
  rejection controls run with the example.

Observed verification: service boundary 7 of 7 checks; real endpoint boundary
8 of 8 checks; example 28 passed its recipes and four rejection controls.
Nine offline workflow policy scenarios passed using the exact workflow
JavaScript with synthetic repository and continuous integration responses.
These cover trusted and untrusted runs, failed checks, wrong revisions,
pull-request runs, superseded main, and manual dispatch with and without
eligible checks. No real hosted workflow run is claimed.

The following in-memory mutants were rejected by the owning checks:

| Removed or changed protection | Discriminating result |
|---|---|
| Restore empty-permission defaulting. | Both new permission-reader checks fail. |
| Accept request-selected catalog_root. | Hosted catalog refusal check fails. |
| Remove the tenant equality when selecting a catalog scope. | Cross-tenant refusal check fails. |
| Remove catalog reference list validation. | Malformed reference refusal check fails. |
| Remove duplicate catalog-scope validation. | Scope-configuration check fails. |
| Allow a traversal reference. | Confined-reference check fails. |
| Omit custom catalog loading. | Configured hosted/local catalog behavior check fails. |
| Ignore the continuous integration conclusion. | Failed-run workflow policy scenario admits the mutant and detects the regression. |
| Remove the final main-revision guard. | Superseded-revision scenario detects the regression. |
| Enable push during the build or move publication before verification. | Workflow order and build-mode checks detect both regressions. |
| Restore shell failure suppression. | The actual installation chain with a synthetic failing Python command exits 23; the masked mutant exits zero. |

One initial malformed-reference test was not discriminating: a string naming
a nonexistent file still failed after list validation was removed. The test
was corrected to use a real one-character fixture name, so treating that
string as an iterable would wrongly succeed. The revised test kills the
mutant. The first workflow test harness also assumed every workflow step had
a name; handling the unnamed checkout step repaired that diagnostic harness,
after which all nine policy cases passed. Neither correction weakened a
product check.

Build provenance attestation, an actual image build, deployed readiness,
durable service stores, full client delivery, and the standalone-export
findings remain separate work. Changing the workflow source is not evidence
that an image has been built or published successfully.

## Authorized test collection and report repairs

The parent session subsequently assigned the test-discovery repairs to this
audit owner. The actual folded list now contains 387 unique modules. Four
duplicate ontology registrations were removed. Six previously unregistered
suites were added: the parallel runner and the five catalog store adapters.
The two DuckDB adapter suites retain explicit optional-dependency handling.
The existing uncommitted model-call collector registration was preserved.

The collection detector now parses the actual registration assignment and
inventories root and nested module definitions. It recognizes only a thin
facade that imports and directly returns another self-test as an indirect
suite alias. This preserves the existing parameter-boundary and learning-cycle
facades without counting their tests twice. An unrelated quoted name is not
registration. Duplicate declarations are refused.

Module reports must contain a nonempty sequence of named test records with
Boolean executed outcomes. Recognized optional-adapter records retain the
missing-dependency evidence and become `passed=null`. They are excluded from
executed pass/fail totals, with separate reported and not-tested counts.
The command-line summary preserves their reasons and does not list them as
failures. The parent's newly added export-manifest parser argument was left
intact in the shared command-line module.

The dependency detector now resolves ordinary imports, from-imports, aliases,
and relative imports at the importing file's actual nesting depth. Its current
live dependency count remains 73. The collection detector reports no missing
suites. The owning conformance test passed 24 of 24 checks.

Eight focused in-memory mutants were rejected: empty test reports accepted,
truthy non-Boolean results accepted, optional checks counted as executed,
nested suites ignored, root suites ignored, duplicate module registration
accepted, ordinary absolute imports ignored, and unrelated quoted names
counted as registration. A mutation-harness attempt initially copied function
globals, which bypassed the detector fixture's patched reader and produced a
FileNotFoundError for its virtual path. Binding the mutant to the live module
namespace corrected the diagnostic harness; all eight discriminating checks
then rejected their intended mutants.

The scanner suite initially passed four of five checks. Its live-tree check
reported two concurrently edited graph modules above the existing size cap:
`solution_canvas.py` at 957 lines and `solution_graph.py` at 805 lines. This
owner neither modified those files nor increased their size allowance. The
parent session assigned the module splits to the graph owner. The full-suite
run during these edits is diagnostic, not qualification of a frozen snapshot.

That diagnostic completed in 355.283 seconds: 5,424 of 5,426 executed checks
passed, with 15 optional optimizer controls separately reported as not tested.
The missing optional packages were `optuna` and `cmaes`; every skipped control
kept its reason. The two failures were the live size-cap check and combined
conformance, which reported the same two oversized modules plus one
unclassified file from concurrent work. No service-boundary or aggregate
report-compatibility failure appeared. The parent session will qualify a
frozen export after all writers finish; this result does not replace that gate.

Additional files inspected during these repairs:

- `src/loop_engine/_conformance_test.py`
- `src/loop_engine/__main__.py`
- `src/loop_engine/architecture_map.py`
- `src/loop_engine/catalog/conformance.py`
- `src/loop_engine/catalog/stores/package_jsonl.py`
- `src/loop_engine/catalog/stores/in_memory.py`
- `src/loop_engine/catalog/stores/duckdb_files.py`
- `src/loop_engine/parameter_boundary.py`
- `src/loop_engine/memory/storage/repository.py`
- `src/loop_engine/parallel_runner.py`
- `src/loop_engine/generation/search_optuna_checks.py`
- `docs/architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md`
