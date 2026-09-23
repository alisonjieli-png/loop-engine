# Second multi-file harness intelligence candidate batch

Kind: dated local candidate verification, September 22, 2026 Eastern time. This is a separate batch under [the wave-two artifact](../../artifacts/harness-intelligence-format-pilot-2026-09-22-wave-2/README.md). It contains **three logical Agent Skill candidates**, **nine physical delivery paths** and **seven distinct delivery body digests**. The remaining ten tracked paths are tests, producer notes, the catalogue and local batch tooling. The [exact manifest](../../artifacts/harness-intelligence-format-pilot-2026-09-22-wave-2/manifest.json) binds 19 source and support paths, excluding itself, to role, byte count and digest. Its SHA-256 is `92d792aa5abe5bbe7c6609fc0d49928fa86917ab91831560411ec86a9cf7715e`.

```text
Three candidate methods
├── Audit join cardinality: SKILL.md + join audit + confined input helper
├── Audit ZIP package: SKILL.md + archive metadata audit + confined input helper
└── Audit text encoding: SKILL.md + encoding audit + confined input helper
```

Each helper file is a byte-identical reuse of the earlier local mixed-format candidate helper at digest `209f273fcca9249cb2778475f667f821f42a8613d987f20c59df6eb6e1aa9a24`. The three physical copies make each skill package self-contained. They add one body digest, not three methods. The new procedures and scripts were written for this batch without copying external procedures. The [candidate catalogue](../../artifacts/harness-intelligence-format-pilot-2026-09-22-wave-2/candidate-items.json) records source and rights state. Customer distribution rights and independent exact-byte approval remain pending.

## Observed checks

| Check | Observed result | Scope |
|---|---|---|
| Python command tests | 27 of 27 passed | Includes positive runs and known-wrong join expansion, blank key, unmatched key, bad header and row; ZIP traversal, duplicate entry, symbolic link, expansion, entry ceiling and invalid archive; invalid text encoding, mixed newline, NUL, long line and path or ceiling refusals. |
| Manifest mutant tests | 6 of 6 passed | Missing or added file, symbolic link, helper divergence and edited-byte stale-manifest rejection. |
| Agent Skills reference validator `skills-ref==0.1.1` | 3 of 3 packages valid | Checks native folder and frontmatter format, not useful or safe execution. |
| Ruff check and format | Passed on the batch Python source | Static style and formatting only. |
| Markdown lint | Eight selected files, zero issues | Batch prose and this verification note only. |
| Local documentation links | 647 repository files, 2,421 local links, zero findings | Local Markdown targets only; remote destinations and dynamic pages were not checked. |
| Exact manifest write then check | 3 packages, 9 delivery paths, 7 unique body digests, 19 tracked files | The manifest is a local candidate inventory, not the active hosted manifest. |

The join script reads two comma-separated tables under a declared root and estimates joined rows without revealing key values. The ZIP script reads metadata and does not extract or decompress anything. The text script reports UTF-8 and newline issues without returning source text. All three use Python 3.11 or later, the standard library, explicit byte ceilings and the reused POSIX no-follow regular-file reader. They write only a bounded JSON response to standard output. They do not use a network, credentials or a model. The owning runtime must separately authorize the read and supply a stable input snapshot and bounded execution.

## Admission and customer-use limit

These are producer-authored candidates. Their author cannot approve them. No independent reviewer has approved the exact package trees, no native client has been observed discovering or invoking them, no hosted customer can retrieve them, and no independent task evaluator has measured benefit. The ZIP result is a metadata screen, not malware detection, checksum verification or safe extraction. The join result measures the declared string keys, not whether the keys share business meaning. The text result checks structural encoding, not content truth or later execution safety. The [roadmap](../roadmap/roadmap.yaml) remains the task authority; this report creates no separate release or approval path.

Before any admission, an independent reviewer must inspect all three delivery files per package, confirm the reused helper's rights and exact digest, replay the known-wrong tests, challenge parser and concurrency edge cases, and then record an approval or rejection against the exact package digest. A selected package must then pass a native client discovery, load and use probe under the client's versioned placement profile. Offered, fetched, loaded, used and verified remain separate facts.
