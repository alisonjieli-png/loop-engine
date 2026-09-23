# Independent review of the second mixed-format candidate batch

Review began September 22, 2026, and final replay finished September 23,
United States Eastern time. This is a read-only review of the
[second mixed-format candidate batch](../../artifacts/harness-intelligence-format-pilot-2026-09-22-wave-2/README.md).
The reviewer did not write the three package methods, scripts or tests. This
record is **not an approval, admission or release decision**. The files remain
candidate-only, with customer distribution rights and native client use still
unqualified.

```text
Candidate delivery trees
├── Join cardinality: skill, audit script, confined input helper
├── ZIP package: skill, metadata audit script, confined input helper
└── Text encoding: skill, audit script, confined input helper
```

## Exact snapshots and checks

The original [failed manifest snapshot](../../artifacts/harness-intelligence-format-pilot-2026-09-22-wave-2/manifest-initial-failed-2026-09-22.json)
has SHA-256
`92d792aa5abe5bbe7c6609fc0d49928fa86917ab91831560411ec86a9cf7715e`.
The [first successor manifest](../../artifacts/harness-intelligence-format-pilot-2026-09-22-wave-2/manifest-successor-overcount-2026-09-22.json)
has SHA-256
`86e6b56d2ce8fb8bafe91622583a9d16f837e31c139f508e24ae8360cdb0c8a4`.
The final reviewed [active manifest](../../artifacts/harness-intelligence-format-pilot-2026-09-22-wave-2/manifest.json)
has SHA-256
`2440dd2123cea394b38609696a9fc7fc82590f698a6f39124eac357c03fdf9bf`.
Its manifest check passed: three logical packages, nine physical delivery
paths, seven distinct delivery body digests and 23 tracked source and support paths
excluding the active manifest. The repeated `confined_input.py` helper
has the same SHA-256, `209f273fcca9249cb2778475f667f821f42a8613d987f20c59df6eb6e1aa9a24`,
as the earlier local candidate pilot. Its three installed copies count as one
distinct body, not three new methods.

The reviewer ran the final command tests, with 38 of 38 passing, and the
manifest mutant tests, with eight of eight passing. The exact manifest check
also passed. These tests establish local behavior for their fixtures, not
customer use or benefit. No unexpected network call, file write or raw secret
output was found in the delivery scripts. The owning runtime must still grant
the exact read effect and supply a stable material snapshot and sandbox.

## Original known-wrong cases and final replay

Each ZIP fixture was created in a disposable temporary directory and passed
to the package command through an absolute approved root and a relative archive
path. The join fixture used two comma-separated files with a single-space key.
The final column reports an independent replay against the current bytes,
in addition to the author's regression tests.

| Case | Original observed result | Final observed result |
|---|---|---|
| `Readme.txt` and `README.txt`, plus separate NFC and NFD spellings of the same name | ZIP passed both collision archives | ZIP failed with `portable_path_collision` |
| `report.txt` and `report.txt.`, singleton `CON`, nested `dir/foo:ads`, `dir/CON.txt`, and a trailing space after `dir/file.txt` | ZIP passed each archive | ZIP failed with `unsafe_entry_path` |
| Unix FIFO, character device and setuid regular metadata | ZIP passed each archive | ZIP failed with `unsupported_special_file_entry` or `privileged_mode_entry` |
| 130,000 unique zero-byte entries in an 11,700,098-byte ZIP, with a 96 MiB process address-space limit | Uncaught `MemoryError` in the standard-library ZIP parser before the 5,000-entry check; no JSON result. A one-entry control passed in the same limit. | Structured `refused`, exit 2, with `entry_signature_prefilter_ambiguous` and unknown entry and expanded-size counts; the one-entry control still passed. |
| 500 distinct names, each with 5,000 `a/` components, in a 10,040,802-byte ZIP | The audit exceeded a five-second timeout despite all declared input ceilings. | Structured `fail` with 500 `entry_path_depth_exceeds_ceiling` findings before the timeout. |
| Both join tables use a single space as their one key value | Join passed, counted zero blank keys and projected one joined row. | Join failed with one blank key per table and zero projected joined rows. |

Both original ZIP resource cases were below the declared archive-byte limit;
the deep-path case was also below the entry-count and expanded-byte limits.
The high-entry case deliberately exceeded the 5,000-entry limit, but the old
parser exhausted memory before checking it. The final signature prefilter
avoids loading that large entry list, and the path-depth cap avoids the costly
parent scan. The text-encoding
script was inspected and its existing tests passed; this review did not find
a new known-wrong case for that script.

## Remaining limitations and disposition

The first successor exposed an ambiguity in its early byte-sequence count. A
valid one-entry ZIP whose `benign.txt` payload was `b'PK\x01\x02' * 5001`
measured 20,122 bytes but was reported as failed for too many entry
signatures. The final replay returned a structured `refused`, exit 2, with
`entry_signature_prefilter_ambiguous`, rather than treating this valid archive
as unsafe. Both entry and expanded-size counts remain unknown. The final
[skill instructions](../../artifacts/harness-intelligence-format-pilot-2026-09-22-wave-2/packages/audit-zip-package/SKILL.md)
describe this possible refusal. A customer can still receive an unknown result
for a valid ZIP with many matching payload bytes. A later admission review
should judge whether this conservative limit is acceptable or whether a
bounded structural count is needed.

The scripts do not establish the provenance of a hard-linked or mounted file,
hold a snapshot against concurrent mutation, or grant file-read authority.
The ZIP command reads central-directory metadata and does not verify payload
checksums, malware status, licences, extraction behavior or executable safety.
The join command measures exact string keys and depends on the caller to set
the required join shape and match rules. The text command does not classify
unusual Unicode separators as carriage-return or line-feed styles. Those
limits require typed caller policy, a sandbox and separate downstream checks.

This review neither approves the packages nor promotes them into the served
catalogue. Exact-byte independent admission, customer distribution rights,
native client discovery and load, observed use, and independently checked task
results remain separate, outstanding facts.
