# Harness Working Directory Compiler: pure preview experiment

September 23, 2026. Detached checkout at
`1920296c00ced18e47992ae05237f4a2923666f0`. **Artifact-only prototype.** No active
source, profile, registry, writer, scheduler or executor changed. It creates no
new library supply or qualified native profile.

## What runs

`preview.py` consumes the existing `CataloguePackage` / `CataloguePackageFile`
objects, complete exact payloads, the existing `ClientLayoutProfile` owner,
declared role/effect restrictions and explicit host-observed workspace states.
One original deterministic engine produces immutable proposed files. The
external Agent Harness adapter has no implementation and returns
`engine_unavailable`; it neither shells out nor silently delegates to Baltor.

The current location owner supplies a skill package's parent directory. The
complete package-relative tree stays beneath that root. All file bytes, roles,
media types and raw digests remain unchanged, including opaque bytes and existing
skill frontmatter. The current one-body installer renderer is not called and no
second frontmatter header is added.

The experiment refuses unsupported declared roles, missing/extra or changed
payloads, unknown entrypoints, target and parent/file collisions, unowned files,
unsafe or missing parent observations, stale expected observations and worker
effects outside the supplied ceiling. An executable package must declare the
canonical process effect. Projected paths retain the existing path bounds.

Pure preview can be computed before installation write authority is present.
Its result reports `required_installation_effects` and `installation_authorized`
separately, with `writes_performed` and `native_qualified` always false. A caller
cannot use the existence of this record as a grant. The actual future writer
must revalidate the scope, permissions and current filesystem before effects.

## What it does not prove

No runtime registry imports this module. The experiment protocol/result names
are private research records, not deployed interfaces. `DraftPackageProfile`
is an experimental wrapper around the old profile data; the active migration
must fold the necessary fields into `ClientLayoutProfile` v2 and remove this
temporary wrapper, rather than create a parallel profile registry.

There is no real filesystem observation: immutable `ExistingState` inputs are
synthetic fixtures or future host-provided observations. The pure comparator
cannot certify their truth or prevent a later symlink race. It does not verify
real package admission, native discovery, plugin/hook semantics, interpreter
availability, dependencies, permissions of external tools, or accepted tasks.
Role support here is a declared mechanical placement restriction, not evidence
of native activation. Current code only demonstrates the existing skill-root
layout; other root instruction, plugin and tool placements require the v2 work.

The preview has no writer or rollback implementation. Existing managed files
can be described by exact expected bytes, but this experiment does not implement
updating them. Shared workspace snapshots and all review/authority decisions
remain owned by existing components. No model or network call occurs.

## Evidence and reproduction

- `known-wrong-before.txt`: tests initially fail because the prototype does not exist.
- `tests-after-1.txt`: first thirteen checks pass.
- `tests-missing-guards-before.txt`: new executable-effect and projected-path checks expose two gaps.
- `tests-after-2.txt`: those repairs pass sixteen checks.
- `preview-write-authority-before.txt`: retained failure before making preview independent of installation write authority.
- `tests-after-3.txt`: final sixteen checks pass.
- `removed-guards-2.json`: seven named negative tests fail when their guard is removed in memory.
- `source-bindings.json`, `design-input.md`, `draft-inputs/`: exact owners, corrected design and the earlier twelve schema-fixture inputs.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src python \
  artifacts/harness-working-directory-compiler-prototype-2026-09-23/test_preview.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src python \
  artifacts/harness-working-directory-compiler-prototype-2026-09-23/check_removed_guards.py
```

Run from the repository root using a qualified repository Python environment.
The recorded run used the integration environment's Python 3.12. Tests operate
entirely on in-memory packages and observations. Saved reports are the only
new files written by the test commands' explicit shell redirection; no proposed
package is installed.

The [implementation decision and patch plan](../../docs/research/HARNESS-WORKING-DIRECTORY-COMPILER-PURE-PREVIEW-PROTOTYPE-2026-09-23.md)
explains why active registration is outside this bounded experiment.
