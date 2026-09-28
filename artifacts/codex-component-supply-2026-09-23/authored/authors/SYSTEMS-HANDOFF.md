# Six original systems tool packages

Candidate-only supply. Canonical preparation tooling is the integration checkout
at `231f51bb1facab517fbe915b08ea9ac85f913347`. Claude owns deployments. This
work changed no application source, commit, deployment, catalogue approval or
served manifest, and made no separate provider/model call.

## Payloads

The six package IDs are the keys of `systems-metadata.json`. Each has eight
payload files: an instruction brief, one standard-library Python tool, input
and output schemas, an input and output example, verification cases and the
repository MIT notice. Only those six explicit IDs are packages. This `authors`
directory contains preparation and evidence material, not a seventh package.

| ID | Distinct work method |
| --- | --- |
| `compare_file_inventories` | Exact supplied-path and metadata differences; no rename guessing or file reads |
| `resolve_selected_dependency_closure` | Reachable exact-ID closure, missing-reference refusal and reported cycles |
| `assign_digest_shards` | Whole SHA-256 UTF-8 digest modulo a fixed bucket count |
| `validate_event_precedence` | Strict before/after constraints on a unique event sequence |
| `apply_nonoverlapping_text_edits` | Simultaneous original-codepoint edits with optional exact source digest |
| `detect_portable_path_collisions` | Explicit NFC/casefold model with duplicate and parent-file collision reports |

`systems-frozen-manifest.json` binds all 48 payload files. They contain 43
distinct byte digests because the six licence notices share their bytes. There
are six logical candidates, zero approvals and zero served packages.

## Authoring and verification

Contracts and acceptance cases were written before the scripts; the record is
`contracts-first.json`. Two schema edge cases were tightened before code was
written: ID control characters and exact digest length. Earlier schema bytes
remain in `systems-contracts-initial`.

The candidate programs consume one bounded UTF-8 JSON document from standard
input and return one JSON line. They reject duplicate keys, nonfinite numbers,
unknown fields, excessive nesting and invalid Unicode scalar data. Exact
integral decimal/scientific spellings are accepted without binary rounding.
Inputs are limited to 64 KiB and outputs to 128 KiB including the newline.

Author verification used Bubblewrap with network namespaces disabled, an empty
environment, read-only system/tool/input mounts, no task workspace or credentials,
2 CPU seconds, 256 MiB memory and a 4-second outer deadline. The final result is
80 passing cases and seven detected mutants in
`../../verification/systems-final-sandbox.json`. All candidate execution occurred
under that sandbox. The first verifier attempt incorrectly treated the canonical
runner's stdout bytes as a string; its reporting error is retained separately.

The first full run passed 79 cases but missed a mutation that treated `a` as a
parent of `ab/x`. One packaged fixture was added; the original fixture file is
preserved as `systems-path-cases-before-prefix-control.json`. No tool algorithm
was changed to fix that test-coverage gap, and no guard was weakened.

A separate agent authored 64 cases before reading implementations. All passed,
then its static effects/usefulness review found no additional material issue.
The successor report
`../../verification/independent-semantic-qa/systems-independent-successor-2.json`
binds every current payload byte, including the added fixture. This semantic QA
is not the independent admission process and grants no publication authority.

## Reuse and limits

`systems-duplication-review.json` records the 80 prior skill identities, nine
mixed-format population manifests, the twelve prior native methods and the
prepared MiniMax method. Closest overlaps are documented. The existing file
inventory tool reads files and computes hashes; this new method compares supplied
inventory records. The existing SCC tool is not a selected dependency resolver.
The instruction skill about prerequisite order does not implement this exact
sequence contract. None of these candidates copies the complete compiler.

The common JSON framing adapts first-party bounded framing under the repository
licence. The six work methods are original Codex/OpenAI-family implementations,
method identity `codex_original_working_directory_components/v1`. The MIT notice
does not establish rights to any third-party material, and no such material was
copied into these payloads.

Unicode collision examples were qualified using the system interpreter's
Unicode database 16.0.0. Results expose that runtime version, and the request can
require an exact version. The abstract comparison model does not certify Windows,
macOS or Linux filesystem behavior. Schema validity, CLI execution, native harness
loading and accepted customer work remain different evidence levels.
