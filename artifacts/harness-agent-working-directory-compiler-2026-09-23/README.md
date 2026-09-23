# Harness Working Directory Compiler contract drafts

Date: September 23, 2026. Research-only; not runtime-admitted. These artifacts
extend existing record names and do not create a registry, daemon, active
profile, approval or schedule.

## Files

- `native-client-layout-profile-v2.schema.json`: proposed `ClientLayoutProfile`
  record evolution, retaining `native_client_layout_profile/v2`.
- `native-material-install-preview-v2.schema.json`: proposed complete compiler
  plan, retaining the existing preview record family at version 2.
- `fixtures/`: twelve synthetic valid/invalid scenarios.
- `fixture-index.json`: exact fixture byte hashes.
- `build_contract_drafts.py`: reconstructs schemas and fixtures in an empty
  artifact directory; refuses to overwrite existing files.
- `validate_contract_drafts.py`: JSON Schema and limited semantic fixture checks.
- `validation-1.json`: retained failed naming-change validation.
- `failed-name-change-fixtures.zip`: the exact fixtures/index from that failure.
- `validation-2.json`: final successor, all twelve expected outcomes pass.
- `source-inputs.json` and `source-inputs/`: exact read-only source inventory and
  snapshots of the supplied design documents before concurrent corrections.

## Reproduce the final validation

```sh
python3 artifacts/harness-agent-working-directory-compiler-2026-09-23/validate_contract_drafts.py
```

The command reads only artifact files, checks their frozen hashes and prints a
report. It uses installed `jsonschema` 4.26.0, no dependency installation or
network. Do not replace existing saved reports; save a new attempt name.

## What the scenarios establish

| Fixtures | Expected result |
| --- | --- |
| 01–03 | Candidate profile, non-launching preview and correctly typed refusal are valid records |
| 04–05 | Traversal and obsolete record version fail schema validation |
| 06 | Constructor-only evidence cannot support a native-discovery claim |
| 07 | New rendering operation requires an eligible implementation |
| 08 | Installed runtime binding cannot silently differ from the planned binding |
| 09 | A known-bad binding cannot remain eligible for future starts |
| 10 | Multiple files cannot silently claim the same target |
| 11 | Installation rights cannot enlarge worker effects |
| 12 | Required capability omission cannot be accepted |

All client names, versions, executable hashes, evidence and host policy facts
inside fixtures are synthetic. Host qualification booleans are test assumptions
used to isolate the wrong condition. They are not a replacement for existing
`EngineQualification` records or independent admission. No positive native
qualification or launch is asserted by any case.

The semantic checker is deliberately incomplete: it does not resolve real
evidence/approval records, verify package bodies, execute render operations,
verify a native client's capabilities, schedule a watch, or apply filesystem
effects. The schemas are candidate interfaces for review, not production code.
Real paths still need descriptor-relative no-symlink filesystem operations and
platform-specific checks after lexical schema validation.

The first validation failed because the preferred human component name changed
while embedded profile digests still referred to the earlier name. The archived
fixtures preserve that mismatch. The corrected fixtures recompute both the
profile binding and fixture inventory; the failure was not suppressed.
