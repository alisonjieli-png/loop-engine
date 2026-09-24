# Build Permission-Scoped Lexical Index

## Task
Implement a deterministic, in-memory lexical indexer that supports tenant-scoped querying, Unicode normalization (NFKC), and specific ranking heuristics.

## First Action
1. Define the JSON input schema to enforce strict types (rejecting booleans where integers are expected).
2. Implement the Unicode NFKC + casefold normalization pipeline.
3. Implement the ranking algorithm: `(distinct_matches, total_matches, doc_id)`.

## Helper Invocation
The tool is invoked via `python3 tools/build_permission_scoped_lexical_index.py`. It reads a single JSON object from `stdin` (max 1MiB) and writes a single JSON object to `stdout`.

## Contract & Refusal Rules
- **Refusal**: If the input contains duplicate keys, non-finite numbers, or booleans in integer fields, return a `refused` object with a stable error code.
- **Tenant Scope**: A query must only return documents where `doc.tenant_id == query.tenant_id`.
- **Abstention**: If the number of distinct query terms found in a document is less than `min_distinct_matches`, the document is excluded.
- **Digest**: The `corpus_digest` is a hash of the sorted list of `(doc_id, source_hash)` pairs. If the corpus changes, the digest must change.
- **Ranking**:
    1. Primary: Count of distinct query terms matched.
    2. Secondary: Total count of all query term occurrences.
    3. Tertiary: Lexical ascending order of `doc_id`.

## Constraints
- Python 3.10+ standard library only.
- No `eval`, `exec`, or dynamic imports.
- No filesystem mutation or network calls.
- Max input size: 1MiB.
