# Second multi-file candidate batch: successor review

Kind: dated local verification after independent review, September 22, 2026 Eastern time. The [initial QA note](SECOND-MIXED-FORMAT-CANDIDATE-BATCH-QA-2026-09-22.md) is a historical snapshot. The [initial failed manifest](../../artifacts/harness-intelligence-format-pilot-2026-09-22-wave-2/manifest-initial-failed-2026-09-22.json) remains unchanged at SHA-256 `92d792aa5abe5bbe7c6609fc0d49928fa86917ab91831560411ec86a9cf7715e`. The [failed-control record](../../artifacts/harness-intelligence-format-pilot-2026-09-22-wave-2/INITIAL-FAILED-CONTROLS-2026-09-22.md) preserves seven first-run failures or errors and two later failing ZIP controls. It links each known-wrong input to the observed pre-repair result.

The [successor manifest](../../artifacts/harness-intelligence-format-pilot-2026-09-22-wave-2/manifest.json) has SHA-256 `86e6b56d2ce8fb8bafe91622583a9d16f837e31c139f508e24ae8360cdb0c8a4`. It binds 21 source, test, review and historical files, excluding itself, to exact roles and digests. There are still **three logical candidate packages**, **nine physical delivery paths** and **seven distinct delivery body digests**. The three copies of the confinement helper have one identical digest. Neither the historical manifest nor the failed-control report is a file for installation into a harness.

```text
Successor candidate batch
├── Join cardinality skill: empty and whitespace-only keys fail
├── ZIP package skill: portable paths, special modes and resource ceilings
└── Text encoding skill: unchanged after independent review
```

## Repaired candidate behavior

| Boundary | Initial failure | Successor behavior observed locally |
|---|---|---|
| Join keys | A single-space key on both sides joined and passed. | Unicode whitespace-only keys count as blank, never join, and fail. Nonblank key bytes are not normalized. |
| Portable ZIP names | Casefold and Unicode-equivalent entries, trailing-dot aliases, reserved Windows names and unsafe nested components passed. | A conservative policy rejects these paths and collisions, including nested colons, device names, trailing dots and trailing spaces. Distinct Unicode and nested regular entries still pass. |
| ZIP file modes | FIFO, character-device and setuid metadata passed. | Unsupported special types and privileged Unix mode bits fail. |
| ZIP entry count under memory pressure | A 130,000-entry, 11,700,098-byte archive raised uncaught `MemoryError` under a 96 mebibyte address-space limit. | A pre-parser signature count fails the archive with one JSON result before Python builds the entry list. Unknown entry and expanded-size counts remain `null`. |
| Deep ZIP entry paths | A 500-entry, 10,040,802-byte archive with 5,000 segments per name timed out after five seconds. | Entry names over 32 components or fixed byte ceilings fail during a bounded path scan; the same control returns JSON before its five-second deadline. |

The ZIP pre-parser counts the byte signature of a central-directory entry in the bounded archive. Matching bytes can also appear outside the actual central directory, so its early refusal can reject an otherwise valid archive. That is a declared conservative choice for a pre-extraction screen. Passing the metadata screen still does not verify checksums, decompressed bytes, malware safety, source rights, or the behavior of a later extractor. A later extraction needs its own typed authority, sandbox and byte and entry ceilings.

## Checks on the successor bytes

| Check | Observed result | Limit |
|---|---|---|
| Three Python command suites | 37 of 37 passed | Includes the seven initial failures or errors, two later unsafe ZIP cases, and a distinct Unicode positive control. The 130,000-entry test runs the tool under a 96 mebibyte address-space cap; the deep-path test has a five-second deadline. |
| Manifest tests | 7 of 7 passed | Includes stale-byte, missing-file, extra-file, symlink, helper divergence and historical-manifest rewrite controls. |
| Agent Skills reference validator, `skills-ref==0.1.1` | 3 of 3 native folders valid | Format only; does not approve code. |
| Ruff check and format | Passed on batch Python source | Static style only. |
| Exact manifest check | 3 packages, 9 delivery paths, 7 distinct bodies, 21 tracked support and source paths | The manifest is a local candidate record, not a hosted release. |

An independent reviewer requested these repairs; an independent review of the successor exact bytes is still pending. All three packages remain **candidate-only**, with customer distribution rights and native client discovery, load, use and independent task acceptance unproven. The producer cannot approve its own work. The [roadmap](../roadmap/roadmap.yaml) remains the task authority. Offered, fetched, loaded, used and verified are separate facts.
