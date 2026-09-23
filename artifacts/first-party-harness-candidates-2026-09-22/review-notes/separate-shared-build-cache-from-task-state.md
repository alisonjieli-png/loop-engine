# Candidate review: separate shared build cache from task state

Status: candidate only. Independent review and native-client checks have not occurred.

- Original basis: First-party classification method drafted for this batch from ordinary build reproducibility and isolation concerns; no external instruction text copied. The [Agent Skills specification](https://agentskills.io/specification) informed the file format only.
- Applicability: Build engineer, agent-platform engineer, team running parallel coding agents; multi-worktree or sandboxed projects; model independent.
- Search phrasing: Parallel worktrees reuse dependencies but task outputs leak across agents.
- Search phrasing: Check whether a reused build entry came from a trusted producer.
- Conceptual input: `WorkerBoundary[]`, `PathAccess[]`, `CacheKeyDefinition[]`, and `BuildInput[]`.
- Conceptual output: `StateSharingAssessment` with path classes, key dependencies, failure probes, and unresolved risks.
- Effects: Read-only design review; no mount, cache deletion, build, or credential access.
- Good case: Several workers share an immutable dependency store keyed by lockfile and toolchain while keeping generated task outputs private.
- Known-wrong case: Workers share a writable build directory keyed only by repository name; one worker's generated output appears in another worker's green build. A second case uses a correct content key but lets an untrusted worker populate the first entry, which the other workers then treat as trusted because the entry is immutable.
- Overlap search: Compared with starter bodies `review_shared_state_for_ordering_defects.md`, `pin_dependency_versions_and_verify_them.md`, and `write_a_pinned_container_and_batch_job.md`. This candidate focuses on path classification and cross-worker cache-key correctness, not general race review or container construction.
- Limitations: A document review cannot prove filesystem isolation. The proposed policy needs an authorized implementation and adversarial cross-worker test.
