# Review artifact relocation

The assistant-created review directory was moved, without deleting its contents, from `/tmp/loop-engine-review-20260908-Phbf3j` to `/home/username/loop-engine/artifacts/project-review-2026-09-08` at the user's request to keep work inside the repository.

The current report is `/home/username/loop-engine/artifacts/project-review-2026-09-08/REVIEW.md`.

Historical command logs, saved run records, and installation scripts retain their original absolute temporary paths. Those strings describe where execution occurred and were not rewritten as if the tests had run elsewhere. Apply this explicit directory-prefix mapping when locating the moved files. The relocated temporary virtual environment is historical build evidence; its absolute launchers are not represented as a portable installation.

The historical `snapshot` and `base-venv` directories now live under `/home/username/loop-engine/artifacts/project-review-2026-09-08/evidence/`. This uses the repository's existing historical-evidence exclusion so copies of the old scanner policy are not mistaken for current source violations. No source-conformance policy was relaxed for the relocation.

The review predates the subsequent harness changes. Its source-check counts and snapshot identities are evidence for the reviewed state, not a validation of later edits.
