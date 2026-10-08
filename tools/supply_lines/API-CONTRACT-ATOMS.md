# Offline API contract atoms

Current factory journals use `api_contract_supply_event/v2`. Resume verifies
each event against its typed retained source record at the exact source-plan
position, the candidate record and file bytes, and recomputed accounting.
Changing the final event's outcome or reserved bytes cannot hide a candidate.
Version-1 event journals remain historical evidence and are not automatically
migrated. Output preflight checks every path, including staging and unlisted
packages, for aliases or special files before generation. Exclusive ownership
of that output tree remains required; this check is not a process sandbox.

`build_library_supply.py api-contracts` extracts independently usable contracts
for decoded parameter bundles, request bodies and response bodies. A harness
can validate a value before passing it to another tool. The existing
`json_schemas` supply line owns the packages, with scope `operation_contracts`.
This command makes candidates, not approved library additions.
Each authorized batch runs once in a canonical Starting Practitioner Loop.
Individual atoms are passive package data, not additional runtimes or model
calls. Preview performs local discovery and writes no run history.

## Inputs and output

Choose named curated sources from `openapi_sources.json`, or use
`--source-mode apis-guru` with names or providers from the existing directory.
Both modes read an existing supply fact cache. The reader makes no network request. It checks cached bytes and
Git blob identity, then uses the existing repository/specification licence
reader. Missing notice evidence is an unresolved source, not evidence that a
notice does not exist. Source observation dates remain unchanged. APIs.guru
uses its existing preferred-version, curated-coverage, licence and notice
readers; the directory listing travels as a fact, not as a blanket licence
for every listed API.

Each candidate contains `contract.schema.json`, synthetic positive and
known-wrong cases, the shared `schema_check.py`, a test, a short use guide and
the required licence/attribution files. The generator checks cases with both
the shared validator and `jsonschema`, then runs the generated package tests.
These checks establish local validation behavior. They do not exercise the API.

The schema's `api_operation_contract_atom/v2` record names the exact source
revision, source digest, a resolvable Path Item pointer and the parent
operation's existing supply job key. Its method, phase, media type and
reference-following rule specify the derived selection. Inherited parameters
merge by location and name, with operation values overriding path-item values.
The logical phase selector is not presented as a literal source pointer.
This is a source relationship,
not a resolved catalogue dependency or permission to run the parent. To
compose a workflow, resolve its operation package separately and bind the
contract's phase and source version. A response schema alone cannot prove
that an operation succeeded or that retrying it is safe.
For Swagger 2, the pointer addresses the existing converter's OpenAPI view.
Its digest and converter identity are explicit. The original bytes keep
their own digest; the package never claims that a converted pointer addresses
the original Swagger document. Earlier private version-1 pilot artifacts keep
their original bytes and their source-binding finding. Rebuild candidates with
version 2 before publication; do not relabel the old records.

The generator resolves local references without cutting away deep constraints.
Cyclic references, unsupported assertion keywords, invalid schemas and cases
without a discriminating check remain private findings. Formats and
readOnly/writeOnly are annotations, not enforced permissions. Parameter
bundles describe decoded values by location, not HTTP serialization.

## Bounded run and recovery

Run from a clean committed checkout with the repository's Python dependencies.
The following is an example for an existing licensed cache; it downloads
nothing:

```sh
PYTHONPATH=src:tools python tools/build_library_supply.py api-contracts \
  --cache-folder /home/username/baltor-library/supply/r4-openapi/2026-10-04 \
  --run-folder /home/username/baltor-private/api-contract-pilot \
  --source workos --source algolia \
  --maximum-atoms 200 --maximum-attempts 1200 \
  --batch-size 300 --maximum-seconds 60
```

Without `--authorize-output-writes`, the command reports the source plan and
writes nothing. Add that flag to generate private candidates. The whole-run
atom and attempt ceilings stay fixed. `--batch-size` and `--maximum-seconds`
bound each invocation; the deadline is checked between bounded atom builds.
Source-cache parsing, plan enumeration and cursor verification precede that
inner deadline. The calling supervisor must bound the whole process if it
requires a total wall-clock ceiling.
`--maximum-candidate-bytes` caps the logical bytes of retained atoms and
candidate files across the run (64 MiB by default). Small run reports and
filesystem block overhead are separate. The workstation's free-space floor
also applies. The frozen source plan records the total enumerable atom
population; the number that will pass the checks stays unknown until processed.

Repeat the same command to continue. The run binds the generator revision and
bytes, source facts and ceilings. A changed binding refuses resume. A file
lock prevents two writers; a chained, flushed event log owns the cursor.
Before advancing, the reader verifies every recorded payload. If a crash
lands a package before its event, the next invocation accepts only identical
bytes. A partial event needs explicit reconciliation; never delete the log to
make a failed run look new. Every invocation keeps its own report.

For an existing shared cache with a nonstandard directory name, supply its
explicit regular path with `--cache-directory`; the reader refuses symlink
aliases. For example, a small AWS-source batch can use the existing directory
cache without downloading or changing it:

```sh
PYTHONPATH=src:tools python tools/build_library_supply.py api-contracts \
  --source-mode apis-guru --source amazonaws.com:accessanalyzer \
  --cache-directory /home/username/baltor-library/supply/caches-2026-10-05-supply5/directory \
  --run-folder /home/username/baltor-private/api-contract-directory-pilot \
  --maximum-source-specifications 1 --maximum-source-bytes 1048576 \
  --maximum-atoms 200 --maximum-attempts 500 --batch-size 100 \
  --maximum-seconds 60 --maximum-candidate-bytes 67108864
```

The source count and cumulative eligible-source-byte limits bound the selected
cohort (25 specifications and 32 MiB by default). Omitted declarations remain
findings. They are not silently considered processed. Select later cohorts
by exact directory names in another frozen run plan; reuse source bodies and
compare candidate semantics across cohorts before publication. Google
Discovery is not an enabled source mode in this command.

`retained/` preserves every attempted source atom with its source binding.
Equivalent schemas point to the retained candidate they reuse. Unsupported
atoms include diagnostics and any normalized schema produced before the
finding. These records are research evidence, not extra served components.

## Counts and further qualification

Reports distinguish attempted source atoms, generated candidates, equivalent
schemas, findings, file placements, distinct payload digests and useful
schema digests. Common validator, test and licence bytes count once. Changing
a title, source date or persona does not create a new schema: the semantic
digest excludes those annotations and retains assertion fields/property names.
Different source relationships remain in the retained records even when
their schema is shared.

Within-run assertion equality is not a complete global semantic comparison.
Before admission, compare the candidates with the active catalogue and run
the existing [qualification](../component_qualification/README.md), including
rights, effects, secret/safety rules, duplicate checks and any requested
sandbox checks. The producer does not approve its own output. The parent
release process owns admission, publication and served-file reconciliation.

Use the measured rate only for this generator and source population. A
twelve-hour million-file target also needs enough distinct licensed source
jobs, qualification capacity and a completed publication. More fields in a
Cartesian product do not provide those things. Word lists can suggest senses
and tasks for later research; this command assigns no frequency ranking and
does not generate files by word, persona or locale permutation.

## Existing work used

The OpenAPI operation generator already owns source pinning, licence checks
and parent job identity. The API component-schema generator supplies the
shared validator and fixture synthesis. `SupplyPackage` owns exact package
bytes and candidate records; existing qualification accepts those records.
This scope adds operation-edge selection and resumable private accounting.
It does not replace the permissive historical raw factory or introduce a new
catalogue, executable graph vertex or publication path.

```sh
PYTHONPATH=src:tools python -m unittest tools.test_api_contract_atoms
```
