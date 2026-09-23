# Native package review integration, September 23, 2026

Status: implemented locally in the detached review-integrity worktree. No
provider call, real approval, commit, push, admission or deployment occurred.
The integrating session owns full repository verification and release.

## What changed

The existing review command now accepts `--content-profile native-original`.
It reads original version-three prepared candidates, preserves every file's
identity and uses separate native package criteria. It runs the existing
ReviewPanel, model-engine interfaces, family exclusion, quorum, budget and
ledger. It does not turn packages into Markdown skills.

| Boundary | Implementation |
| --- | --- |
| Candidate input | `NativeCatalogue` accepts `starter_catalogue_candidate_items/v3` and `candidate_intelligence_specifications/v3`, using the factory's exact field sets. |
| Package identity | Existing `CataloguePackage` and `CataloguePackageFile` validate paths, roles, media, file sizes and canonical manifest identity. The reader verifies the complete on-disk inventory and every actual payload. |
| Source identity | The existing source-checking helper checks committed revision, exact current bytes and declared source/LICENSE digests. No source is fetched from the network. |
| Fixed request check | A native immutable request holds manifest plus payloads. The fixed precheck edge verifies that no directly replaced payload differs from that manifest. |
| Native checks | Separate engines cover licence, format/dependencies, executable safety, declared effects, secrets and duplicates. Existing scanner and duplicate engines are reused. |
| Model input | Each text payload gets its own digest-delimited block and the complete file tree is shown. Search text never substitutes for review bytes. |
| Persisted review | Active worker records use version two and serialize reported model identity and explicit review-subject type. The export includes the complete package, item, specification, producer method and source/criteria/instruction binding. The reader reconstructs request identity and binds each decision to its verified call. |

The code remains in `tools/candidate_review` and the existing operator command.
There is no new runtime type, active approval store, service endpoint or
catalogue body format. See the component's
[classification and fixed edges](../../tools/candidate_review/README.md#where-it-sits).

## Eligible material and deliberate refusals

The initial native profile accepts text instructions, native skill metadata,
Python scripts/tools, text references, JSON Schema contracts, strict supporting
JSON data and licence notices for independent review. Python is parsed, never
executed. Imports need standard-library, bundled-source or declared dependency
coverage. Known direct filesystem/network operations are checked against
effects. These static checks do not establish complete behavior or dependency
installation, which remain review and execution-qualification obligations.

A missing helper, extra file, symlink, unsafe path, changed bytes, incomplete
manifest, executable-role mismatch, missing process effect, malformed skill,
unsupported required component or undeclared binary verification produces a
refusal. Hooks, plugin registrations, custom agents and commands are held by
this first profile. The existing plugin's separate native loading evidence
does not create an approval exception here.

Each native payload file is bounded at 256 KiB, each package at 2 MiB, with
the existing 64-file limit. Source files are bounded at 512 KiB and source
inventories at 64 entries. Input metadata files are bounded at 32 MiB and a
review catalogue at 10,000 items. These are explicit worker profile limits,
not claims about universal harness limits. Nothing is truncated for review.

The native duplicate profile uses exact comparison within its declared
population ceiling and selects the existing MinHash engine for larger
populations. If its optional dependency is unavailable, the duplicate kind
is refused. Splitting a population is not permission to omit cross-batch
duplicate comparison.

## Record version and historical impact

The worker's dispatch, call, verdict, run, run-end and panel-review records
advance to version two. This changes the **review worker**, not the live
service's `starter_catalogue_independent_review/v2` approval source or its
currently packaged historical items. Version-one worker ledgers and panel
exports are refused as active resume/admission input. Keep those files and
their exact historical bodies for audit; do not rewrite their fields into the
new version. Historical checks now inspect them as archival evidence and
explicitly prove the current reader refuses them.

Native subjects use `candidate_native_package_review_request/v1`. The existing
`body_sha256` response field names the canonical package document for that
explicit subject type; it never claims to hash a flattened text body. The
manifest binds the complete delivered file inventory. An ordinary starter
body retains its own subject type and digest meaning.

Use a new ledger for this worker version. Old partial verdicts have no
serialized answering-model evidence and cannot be silently carried. Old
interrupted calls require explicit operator reconciliation before restarting
their work. Existing hosted approvals are not silently revoked by this
worker format change.

## Run without model authority first

From the integrating repository, with prepared output inside `artifacts/`:

```bash
PYTHONPATH=src:tools python tools/review_catalogue_candidates.py \
  --content-profile native-original \
  --catalogue artifacts/PREPARED_NATIVE_BATCH \
  --repository . \
  --ledger artifacts/NATIVE_REVIEW_RUN/ledger.jsonl \
  --count 12 --seed FIRST_NATIVE_SAMPLE \
  --call-ceiling 0 --token-ceiling 0 \
  --record artifacts/NATIVE_REVIEW_RUN/review.json \
  --recorded-at 2026-09-23
```

Create the run directory first. The record and catalogue use repository-relative
references. Select the actual count and seed for the frozen batch. Real review
requires the existing explicit model-call flag and declared ceilings. Native
profile selection supplies its own criteria, instructions and per-item
producers; conflicting starter resource overrides are refused.

`--calibrate` currently refuses the starter-body calibration set for this
profile. A native calibration campaign must supply independently known correct
and incorrect complete-package cases through a deliberately versioned extension.
This implementation does not claim the old four-case pilot qualifies native
executable review. Model-review completion also does not install or publish
anything; the existing independent admission and release process remains.

## Evidence and remaining integration work

The [saved checks](../../artifacts/native-package-review-2026-09-23/README.md)
include negative cases and failed predecessors. The final component suite
ran 260 tests with one optional dependency skip, without failures. Nine native
removed-guard controls and all eight prior integrity controls were detected.
All newly authored Python modules pass Ruff. The 12 new complete factory
packages, containing 96 payload files, pass deterministic native prechecks;
**zero have been approved by this task**.

The bare Python 3.11 environment lacked dependencies; the corrected
configuration module imports there, while full native tests still require a
correctly provisioned Python 3.11 environment. The suite passed on Python
3.12.13. No provider integration or native task-completion claim follows from
these offline tests.

Before admission, the integrating session must independently review this
worker change, run composed-tree checks, calibrate the chosen native reviewer
campaign, obtain the required exact-package independent decisions, and use
the existing host manifest and native materialization contracts. Task state
belongs in S-6.40/S-6.44 and the owning roadmap entries, not in a second list.
