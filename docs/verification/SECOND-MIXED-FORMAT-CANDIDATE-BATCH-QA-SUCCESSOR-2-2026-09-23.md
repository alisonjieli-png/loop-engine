# Second multi-file candidate batch: second successor

Kind: dated local candidate verification, September 23, 2026 Eastern time, for the September 22 batch. The [initial QA note](SECOND-MIXED-FORMAT-CANDIDATE-BATCH-QA-2026-09-22.md) and [first successor note](SECOND-MIXED-FORMAT-CANDIDATE-BATCH-QA-SUCCESSOR-2026-09-22.md) remain historical records. The exact initial failed manifest is SHA-256 `92d792aa5abe5bbe7c6609fc0d49928fa86917ab91831560411ec86a9cf7715e`; the first successor manifest is SHA-256 `86e6b56d2ce8fb8bafe91622583a9d16f837e31c139f508e24ae8360cdb0c8a4`. Both snapshots remain in the [batch artifact](../../artifacts/harness-intelligence-format-pilot-2026-09-22-wave-2/README.md) beside their failed-control notes.

Independent review of the first successor found one valid ZIP that was incorrectly called a failure: a single entry carried the byte sequence `PK\x01\x02` 5,001 times in its payload. The raw-signature prefilter counted member bytes along with actual directory records, returned `entry_signature_count_exceeds_ceiling`, and could not know the entry count. The [second review record](../../artifacts/harness-intelligence-format-pilot-2026-09-22-wave-2/SECOND-REVIEW-OVERCOUNT-2026-09-22.md) preserves the reproducer and the pre-repair failed test.

The current [second successor manifest](../../artifacts/harness-intelligence-format-pilot-2026-09-22-wave-2/manifest.json) has SHA-256 `2440dd2123cea394b38609696a9fc7fc82590f698a6f39124eac357c03fdf9bf`. It binds 23 source, test, producer-note and historical paths, excluding itself. There are still **three logical candidate packages**, **nine physical delivery paths** and **seven distinct delivery body digests**. Historical snapshots and tests are not installable skill files.

```text
Current candidates
├── Join cardinality: whitespace-only keys fail without joining
├── ZIP metadata screen: portable paths and special modes checked
│   └── Ambiguous high raw-signature count: refused, with no safety verdict
└── Text encoding: bounded structural audit
```

The ZIP prefilter still prevents Python from building a very large entry list. When raw signature matches exceed its ceiling, the script now returns `status=refused`, exit 2, reason `entry_signature_prefilter_ambiguous`, and unknown entry and expanded-size counts. It does **not** label the archive invalid, unsafe or proven to exceed the entry-count limit. Both the valid one-entry payload and the independent 130,000-entry resource control take this conservative path. The earlier portable-path, privileged-mode, deep-path and whitespace-key repairs remain in place. ZIP content checksums, decompressed bytes, malware safety and later extractor behavior remain outside this metadata screen.

## Checks on current exact bytes

| Check | Observed result | Limit |
|---|---|---|
| Three Python command suites | 38 of 38 passed | Includes a valid one-entry signature-payload refusal, the 130,000-entry control under a 96 mebibyte address-space cap, the deep-path five-second control, and positive and known-wrong path, mode, join and text cases. |
| Manifest tests | 8 of 8 passed | Includes stale-byte and tree mutants and protects both frozen historical manifests. |
| Exact manifest check | 3 packages, 9 delivery paths, 7 distinct delivery bodies, 23 tracked paths | Local candidate inventory only. |

The [independent exact-byte rereview](SECOND-MIXED-FORMAT-INDEPENDENT-QA-2026-09-22.md) replayed the saved wrong cases on this second successor and found bounded fail or refusal behavior. Customer distribution rights, formal admission, native harness discovery and use probes, and independent task acceptance remain open. The producer cannot approve these packages. No item is hosted or offered to a customer. The [roadmap](../roadmap/roadmap.yaml) remains the task authority, and offered, fetched, loaded, used and verified remain separate facts.
