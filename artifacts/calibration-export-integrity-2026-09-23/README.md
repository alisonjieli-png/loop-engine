# Calibration export and eligibility evidence

No provider/model calls or approvals. Production source hashes are in
`source-bindings.json`; the isolated parent checkout is `import-owner-repair`.

- `check_persisted_exclusion.py` and `check_uncalibrated_producer_family.py` preserve
  the independent reviewer's original reproductions. The first uses the now-retired
  export shape; its original before result remains in `persisted-exclusion-before.json`.
- `uncalibrated-producer-before.json` and `uncalibrated-producer-after.json` compare
  the actual two-phase producer-family case.
- `checks-before.txt`: 11 known-wrong assertion failures before repair.
- `tests-first-repair.txt`, `tests-second-repair.txt`, `tests-full-export.txt`,
  `tests-coherent-bypass.txt`: intermediate failures/successors are retained.
- `persisted-exclusion-v3-after.json`: coherent current-format counterexample,
  including complete control verdicts and actual candidate decision; both deletion
  projections still refuse.
- `prompt-binding-before.txt`: independent changed-prompt/recomputed-key case fails
  its new check before the prompt reconstruction repair.
- `tests-prompt-binding-final.txt`: 19 focused checks pass after that repair.
- `tests-component.txt`, `tests-component-final.txt`,
  `tests-component-prompt-final.txt`: component runs at successive frozen stages.
- `tests-combined-final.txt`: requested cross-component combination after final repair.
- `check_removed_guards.py`, `removed-guards.json`, `removed-guards-final.json`:
  fixed in-memory mutations, including the later prompt-binding guard.
- Ruff first/final reports preserve formatting findings and zero introduced diagnostics.

The initial successor was separately frozen as
`/home/username/.le-codex-build/calibration-export-integrity-before-prompt-repair.patch`
(SHA-256 `9c8d4e208ea8cfc3e330e77728e1fb1468c77b8324d1fec0101ed025e0ae0d54`).
The final patch includes the prompt repair and is the one intended for integration.
Do not apply both aggregate patches.
