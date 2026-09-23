# Candidate deterministic tool packages

Prepared September 22, 2026. **Candidate only.** These packages have not been independently approved, added to the catalogue, installed in a native client, or served to a customer. The producer of these files must not approve them.

## Provenance and overlap check

The scripts and skills were written for this pilot from general file-format and digest methods, without copying third-party code or skill text. The repository source observed before writing was revision `a51ac96378ce63cd4504499ea865a22e78168fec`. The root `LICENSE` at that revision declares MIT. Exact package rights and reuse still need independent review before promotion.

The overlap search covered `src/loop_engine`, `tools` and the three existing first-party candidate waves. The closest existing code, `src/loop_engine/core/source_profile.py`, samples CSV and JSON Lines structure but does not enforce complete-file row width or event identity consistency. Existing SHA-256 uses record known files or task-specific sources; this package inventories an arbitrary bounded selected directory. This search establishes distinct intent, not uniqueness across the internet.

## Package contracts

| Package | Input | Output | Effect class | Dependency | Limits and known limitation |
|---|---|---|---|---|---|
| `audit-csv-structure` | Runtime-authorized absolute root, relative UTF-8 CSV or TSV path, delimiter and header mode | `csv_structure_audit/v1` JSON on standard output; input digest, optional header, counts and issue locations | Confined local file read and standard output only | Python 3.10 or later, POSIX no-follow and nonblocking file operations, standard library | Fixed 20,000,000-byte ceiling; headerless default returns no first-row values; checks syntax and shape, not types, meaning or formula injection |
| `audit-jsonl-identities` | Runtime-authorized absolute root, relative UTF-8 JSON Lines path and exact top-level identity key | `jsonl_identity_audit/v1` JSON on standard output; input digest and counts, no event body or identity | Confined local file read and standard output only | Python 3.10 or later, POSIX no-follow and nonblocking file operations, standard library | Fixed 20,000,000-byte and 100,000-line ceilings; bounded record split; Decimal comparison avoids binary-float collapse and extreme exponent parsing yields an invalid-record result |
| `inventory-file-digests` | Runtime-authorized absolute root and optional relative subtree | `file_digest_inventory/v1` JSON on standard output; relative names, sizes, SHA-256 digests, same-digest groups | Confined local file read, directory listing and standard output only | Python 3.10 or later, POSIX no-follow and nonblocking file operations, standard library | Fixed 1,000-file, 50,000,000-byte, 32-level and 5,000-entry ceilings; content is not a consistent snapshot if the tree changes during the scan |

None of these scripts grants read, execute, network, credential, file-write or spending authority. The command-line approved-root value confines access but is not proof that the caller may read it. They must run only after the owning Loop and harness have authorized the precise root, selected relative input and process resource allowance. Python test cases write temporary local fixtures; the packaged tool bodies do not write files. Launch with `python3 -B` and a read-only package source directory so Python itself cannot create bytecode cache files. Each package includes its own identical `scripts/confined_input.py` so it remains standalone when selected.

## Exact files prepared

The digest is SHA-256 of the file bytes after the checks below. Recompute every digest if a reviewer changes any byte. Paths are relative to this note's directory.

| Path | SHA-256 |
|---|---|
| `audit-csv-structure/SKILL.md` | `a42bdb00d3cb17f49d16335d941dde5cf256b7015406a8d33af80a3a20c8b7a7` |
| `audit-csv-structure/scripts/audit_csv_structure.py` | `70970eb3609ae57d53cce17dbeee98244ba2437d1bcc9f49649e52cfb043e1b0` |
| `audit-csv-structure/scripts/confined_input.py` | `209f273fcca9249cb2778475f667f821f42a8613d987f20c59df6eb6e1aa9a24` |
| `audit-csv-structure/tests/test_audit_csv_structure.py` | `1575801199920ceaa734d2ca9d57812b884e216777b930e100810c75855e5d7c` |
| `audit-jsonl-identities/SKILL.md` | `5c062ad83b0b46b9e13aa5299e54a1ce35e58566ff0245b7442c79f9453a05ad` |
| `audit-jsonl-identities/scripts/audit_jsonl_identities.py` | `60561a7f3ec9fcb7b0cb89d2a56d00c59d46806638d8148d2b6d6af4b9e67f25` |
| `audit-jsonl-identities/scripts/confined_input.py` | `209f273fcca9249cb2778475f667f821f42a8613d987f20c59df6eb6e1aa9a24` |
| `audit-jsonl-identities/tests/test_audit_jsonl_identities.py` | `876dab796fb62263b7c10e4d57874df57ea2fc32436e81dd8b73d39325073f4f` |
| `inventory-file-digests/SKILL.md` | `7f7efdf8b52dfc3875f7caed4c946b907d053c49d6518d57ffc24f0762e014cc` |
| `inventory-file-digests/scripts/inventory_file_digests.py` | `b30c4fb8bba6568331ac06f13fe95bca7691c4fbc15e698e8ae0bb89615e14cd` |
| `inventory-file-digests/scripts/confined_input.py` | `209f273fcca9249cb2778475f667f821f42a8613d987f20c59df6eb6e1aa9a24` |
| `inventory-file-digests/tests/test_inventory_file_digests.py` | `8e5e577156f84e0c8d002a6bd6f15fa0b46ce5cf2301439fba11581651a3df8a` |

## Checks run

Run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s artifacts/harness-intelligence-format-pilot-2026-09-22/tools/audit-csv-structure/tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s artifacts/harness-intelligence-format-pilot-2026-09-22/tools/audit-jsonl-identities/tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s artifacts/harness-intelligence-format-pilot-2026-09-22/tools/inventory-file-digests/tests -v
ruff check artifacts/harness-intelligence-format-pilot-2026-09-22/tools
uvx --from skills-ref agentskills validate artifacts/harness-intelligence-format-pilot-2026-09-22/tools/audit-csv-structure
uvx --from skills-ref agentskills validate artifacts/harness-intelligence-format-pilot-2026-09-22/tools/audit-jsonl-identities
uvx --from skills-ref agentskills validate artifacts/harness-intelligence-format-pilot-2026-09-22/tools/inventory-file-digests
npx markdownlint-cli2 'artifacts/harness-intelligence-format-pilot-2026-09-22/tools/**/*.md'
```

Observed: 40 unit tests passed, including ancestor symlink, traversal, FIFO deadlines, CSV privacy and field-length, decimal precision, large and extreme exponents, many-newline refusal, entry-cap and command-line checks; Ruff passed; all three package directories passed the Agent Skills format validator; Markdown lint reported zero issues. The installed `skills-ref` distribution exposes the validator command as `agentskills` in this environment.

## Holds for independent review

- Recheck the exact bytes, rights, prompt instructions and executable behavior without relying on this producer's assessment. Run a static security scan and native discovery/use probe before any served release.
- Every root and path component is opened through a POSIX descriptor with no-follow flags. Candidate file descriptors also use `O_NONBLOCK` before `fstat` rejects a FIFO or other non-regular file. The inventory test simulates a regular-file classification that becomes a FIFO before open. The scripts refuse an absolute file selector, traversal or symlink. Single-file audits and file hashing compare metadata before and after reading. These controls do not make a concurrently changing tree a consistent snapshot: a writer can change directory entries between listing and opening, and metadata equality is not a proof that file bytes stayed still. Require quiescent task materials or a filesystem snapshot for release qualification.
- A bind mount or hard link can give a file an in-root name without proving its provenance. The owning workspace admission and sandbox must enforce the permitted material set. The same authority check must limit which root the command receives; this script cannot infer authority from the root path string.
- `audit-csv-structure` includes header names in output. `inventory-file-digests` includes relative file names and digests. Protect reports at the input's confidentiality level.
- The three scripts have no measured task benefit, model-selection improvement or customer-use evidence. They count as three candidate packages, not three approved intelligence items.
