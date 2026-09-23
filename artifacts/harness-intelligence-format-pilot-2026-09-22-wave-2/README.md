# Second mixed-format harness intelligence candidate batch

This September 22, 2026 batch contains three distinct, original, multi-file Agent Skill candidates. They are **candidate-only**. No item is in the hosted catalogue, approved for customer distribution, or qualified through native client invocation. The [logical candidate catalogue](candidate-items.json) lists each method once. The [exact tree manifest](manifest.json) binds every delivery, test, note and local support file to a role, size and digest.

```text
Candidate batch
├── audit-join-cardinality
│   ├── SKILL.md: activation and use instructions
│   ├── scripts/audit_join_cardinality.py: bounded read-only procedure
│   └── scripts/confined_input.py: reused local confinement helper
├── audit-zip-package
│   ├── SKILL.md: activation and use instructions
│   ├── scripts/audit_zip_package.py: bounded metadata inspection
│   └── scripts/confined_input.py: reused local confinement helper
└── audit-text-encoding
    ├── SKILL.md: activation and use instructions
    ├── scripts/audit_text_encoding.py: bounded read-only procedure
    └── scripts/confined_input.py: reused local confinement helper
```

Tests and producer notes live outside these three delivery trees. The confinement helper comes byte-for-byte from the earlier local candidate pilot. Reusing that code reduces duplicated implementation work but adds only one distinct body digest across the three logical packages. Neither the helper nor the new scripts have an independent approval decision.

The [initial failed manifest](manifest-initial-failed-2026-09-22.json) and [failed controls](INITIAL-FAILED-CONTROLS-2026-09-22.md) preserve the independent review findings before the ZIP path and resource repair and the blank-key repair. They are historical evidence, not installable skill files. The current `manifest.json` is the successor inventory and includes both records by exact digest.

The [first successor manifest](manifest-successor-overcount-2026-09-22.json) and [second review finding](SECOND-REVIEW-OVERCOUNT-2026-09-22.md) preserve a valid ZIP that the conservative byte-signature prefilter initially mislabeled as a failure. The current script returns a structured unknown-screening refusal for that case. Both old manifests remain historical evidence, and the current manifest binds them without making them delivery files.

Each command uses Python 3.11 or later with the standard library, a declared absolute materials root, a relative path, fixed resource ceilings and a no-follow regular-file read. They output bounded JSON to standard output and have no write, network, model or secret capability. The owning runtime still supplies typed file-read authority, a stable input snapshot and a sandbox. The scripts do not grant their own authority.

Run local candidate checks:

```bash
python3 -B -m unittest discover -s artifacts/harness-intelligence-format-pilot-2026-09-22-wave-2/tests -p 'test_*.py'
python3 -B artifacts/harness-intelligence-format-pilot-2026-09-22-wave-2/test_make_manifest.py
python3 -B artifacts/harness-intelligence-format-pilot-2026-09-22-wave-2/make_manifest.py --check
```

The exact manifest counts physical package files separately from logical methods. Three copies of the confinement helper are required for self-contained installation, but they are not three new methods. Any change to a script, instruction file or helper invalidates the current manifest and would require fresh independent review of the complete delivery tree. The [verification note](../../docs/verification/SECOND-MIXED-FORMAT-CANDIDATE-BATCH-QA-2026-09-22.md) records observed checks and limits.
