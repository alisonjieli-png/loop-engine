# Codex review transfer, September 23

This directory records how to integrate the reviewed work without replacing
concurrent changes. The source worktree is
`/home/username/.le-codex-review-20260923`.

Read `docs/context/CODEX-NATIVE-PACKAGES-AND-STATUS-HANDOFF-2026-09-23.md`
inside that worktree first. The existing roadmap remains the task authority.

[The tracked diff](tracked-changes.patch) is against the exact base in
[source-files.json](source-files.json). The JSON also lists new artifact and
report files in the source worktree with their exact hashes. The patch does
not include those untracked files; copy only the reviewed named additions
from that worktree. Do not overwrite existing files without comparing their
ownership and current contents. Reconcile roadmap changes by existing step
identity and regenerate its views against current main.

The diff and files are uncommitted candidate work. No catalogue approval,
production installation, article publication or deployment is implied.
Follow the repository's full exact-tree check and integration process.
